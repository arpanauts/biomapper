"""
Expert Review Flagging Logic for Biological Validation

Implements column-based flagging system that identifies matches requiring
expert review based on confidence scores and biological criteria.
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class FlaggingCategory(Enum):
    """Categories for expert review flagging."""
    
    AUTO_ACCEPT = "auto_accept"           # High confidence, automatic acceptance
    AUTO_REJECT = "auto_reject"           # Very low confidence, automatic rejection
    EXPERT_REVIEW = "expert_review"       # Medium confidence, needs expert review
    STRUCTURAL_CONFLICT = "structural_conflict"  # Chemical structure conflicts
    AMBIGUOUS_MATCH = "ambiguous_match"   # Multiple similar confidence matches
    EDGE_CASE = "edge_case"              # Known problematic patterns


@dataclass
class FlaggingDecision:
    """Single flagging decision with rationale."""
    
    metabolite_id: str
    category: FlaggingCategory
    confidence_score: float
    flagging_reason: str
    matched_name: Optional[str] = None
    alternative_matches: List[str] = None
    requires_action: bool = True
    priority: int = 1  # 1=high, 2=medium, 3=low
    estimated_review_time: int = 5  # minutes
    

@dataclass
class FlaggingBatch:
    """Batch of flagging decisions for expert review."""
    
    batch_id: str
    creation_date: str
    total_flagged: int
    decisions: List[FlaggingDecision]
    estimated_total_time: int
    flagging_summary: Dict[str, int]
    

class ExpertReviewFlagger:
    """
    Column-based expert review flagging system.
    
    Implements simplified approach that adds flagging columns to results
    without requiring complex web dashboard infrastructure.
    """
    
    def __init__(self,
                 auto_accept_threshold: float = 0.85,
                 auto_reject_threshold: float = 0.75, 
                 max_flagging_rate: float = 0.15,
                 enable_structural_validation: bool = True):
        """
        Initialize expert review flagger.
        
        Args:
            auto_accept_threshold: Confidence threshold for automatic acceptance
            auto_reject_threshold: Confidence threshold for automatic rejection
            max_flagging_rate: Maximum proportion of results to flag for review
            enable_structural_validation: Enable chemical structure validation
        """
        self.auto_accept_threshold = auto_accept_threshold
        self.auto_reject_threshold = auto_reject_threshold
        self.max_flagging_rate = max_flagging_rate
        self.enable_structural_validation = enable_structural_validation
        
        # Known edge case patterns
        self.edge_case_patterns = {
            "deprecated_ids": ["HMDB00000", "CHEBI:0000"],
            "ambiguous_names": ["glucose", "water", "acetate"],
            "structural_conflicts": ["isomers", "stereoisomers"]
        }
        
        # Review time estimates by category
        self.review_time_estimates = {
            FlaggingCategory.EXPERT_REVIEW: 5,      # 5 minutes average
            FlaggingCategory.STRUCTURAL_CONFLICT: 10, # 10 minutes for structure checks
            FlaggingCategory.AMBIGUOUS_MATCH: 8,     # 8 minutes for disambiguation
            FlaggingCategory.EDGE_CASE: 3           # 3 minutes for known issues
        }
    
    def flag_results_for_review(self, 
                               pipeline_results: pd.DataFrame,
                               confidence_column: str = "confidence_score",
                               metabolite_id_column: str = "metabolite_id") -> pd.DataFrame:
        """
        Add expert review flagging columns to pipeline results.
        
        Args:
            pipeline_results: DataFrame with pipeline mapping results
            confidence_column: Column containing confidence scores
            metabolite_id_column: Column containing metabolite identifiers
            
        Returns:
            DataFrame with added flagging columns
        """
        logger.info(f"Applying expert review flagging to {len(pipeline_results)} results...")
        
        # Create copy to avoid modifying original
        flagged_results = pipeline_results.copy()
        
        # Generate flagging decisions for each result
        flagging_decisions = []
        for _, row in pipeline_results.iterrows():
            decision = self._make_flagging_decision(row, confidence_column, metabolite_id_column)
            flagging_decisions.append(decision)
        
        # Apply rate limiting to control review workload
        flagging_decisions = self._apply_rate_limiting(flagging_decisions)
        
        # Add flagging columns
        flagged_results = self._add_flagging_columns(flagged_results, flagging_decisions)
        
        # Generate flagging summary
        summary = self._generate_flagging_summary(flagging_decisions)
        logger.info(f"Flagging complete: {summary}")
        
        return flagged_results
    
    def _make_flagging_decision(self, 
                               row: pd.Series,
                               confidence_column: str,
                               metabolite_id_column: str) -> FlaggingDecision:
        """Make flagging decision for single result."""
        
        confidence_score = row.get(confidence_column, 0.0)
        metabolite_id = row.get(metabolite_id_column, "unknown")
        matched_name = row.get("matched_name", "")
        
        # Apply decision logic in priority order
        
        # 1. Check for edge cases first
        if self._is_edge_case(metabolite_id, matched_name):
            return FlaggingDecision(
                metabolite_id=metabolite_id,
                category=FlaggingCategory.EDGE_CASE,
                confidence_score=confidence_score,
                flagging_reason="Known edge case pattern detected",
                matched_name=matched_name,
                priority=2,
                estimated_review_time=self.review_time_estimates[FlaggingCategory.EDGE_CASE]
            )
        
        # 2. Check for structural conflicts
        if self.enable_structural_validation and self._has_structural_conflict(row):
            return FlaggingDecision(
                metabolite_id=metabolite_id,
                category=FlaggingCategory.STRUCTURAL_CONFLICT,
                confidence_score=confidence_score,
                flagging_reason="Chemical structure validation failed",
                matched_name=matched_name,
                priority=1,  # High priority
                estimated_review_time=self.review_time_estimates[FlaggingCategory.STRUCTURAL_CONFLICT]
            )
        
        # 3. Check for ambiguous matches
        if self._is_ambiguous_match(row):
            return FlaggingDecision(
                metabolite_id=metabolite_id,
                category=FlaggingCategory.AMBIGUOUS_MATCH,
                confidence_score=confidence_score,
                flagging_reason="Multiple matches with similar confidence",
                matched_name=matched_name,
                alternative_matches=self._extract_alternative_matches(row),
                priority=2,
                estimated_review_time=self.review_time_estimates[FlaggingCategory.AMBIGUOUS_MATCH]
            )
        
        # 4. Apply confidence-based thresholds
        if confidence_score >= self.auto_accept_threshold:
            return FlaggingDecision(
                metabolite_id=metabolite_id,
                category=FlaggingCategory.AUTO_ACCEPT,
                confidence_score=confidence_score,
                flagging_reason=f"High confidence ({confidence_score:.3f} >= {self.auto_accept_threshold})",
                matched_name=matched_name,
                requires_action=False,
                priority=3,
                estimated_review_time=0
            )
        
        elif confidence_score < self.auto_reject_threshold:
            return FlaggingDecision(
                metabolite_id=metabolite_id,
                category=FlaggingCategory.AUTO_REJECT,
                confidence_score=confidence_score,
                flagging_reason=f"Low confidence ({confidence_score:.3f} < {self.auto_reject_threshold})",
                matched_name=matched_name,
                requires_action=False,
                priority=3,
                estimated_review_time=0
            )
        
        else:
            # Medium confidence - needs expert review
            return FlaggingDecision(
                metabolite_id=metabolite_id,
                category=FlaggingCategory.EXPERT_REVIEW,
                confidence_score=confidence_score,
                flagging_reason=f"Medium confidence ({confidence_score:.3f}) requires validation",
                matched_name=matched_name,
                priority=2,
                estimated_review_time=self.review_time_estimates[FlaggingCategory.EXPERT_REVIEW]
            )
    
    def _is_edge_case(self, metabolite_id: str, matched_name: str) -> bool:
        """Check if result represents a known edge case."""
        
        metabolite_id = str(metabolite_id).lower()
        matched_name = str(matched_name).lower()
        
        # Check deprecated ID patterns
        for pattern in self.edge_case_patterns["deprecated_ids"]:
            if pattern.lower() in metabolite_id:
                return True
        
        # Check ambiguous name patterns (only if it's the exact name, not substring)
        for pattern in self.edge_case_patterns["ambiguous_names"]:
            if pattern.lower() == matched_name.strip():
                return True
        
        # Check for specific problematic patterns
        edge_patterns = [
            "obsolete", "deprecated", "unknown", "unspecified",
            "mixture", "complex", "undefined"
        ]
        
        for pattern in edge_patterns:
            if pattern in metabolite_id or pattern in matched_name:
                return True
        
        return False
    
    def _has_structural_conflict(self, row: pd.Series) -> bool:
        """Check for chemical structure validation conflicts."""
        
        if not self.enable_structural_validation:
            return False
        
        # Check for molecular formula conflicts
        source_formula = row.get("source_molecular_formula", "")
        matched_formula = row.get("matched_molecular_formula", "")
        
        if source_formula and matched_formula and source_formula != matched_formula:
            # Allow for hydration differences (common in databases)
            if not self._formulas_compatible(source_formula, matched_formula):
                return True
        
        # Check for InChIKey conflicts (first 14 characters for connectivity)
        source_inchikey = row.get("source_inchikey", "")
        matched_inchikey = row.get("matched_inchikey", "")
        
        if source_inchikey and matched_inchikey:
            # Compare connectivity layers (first 14 characters)
            source_connectivity = source_inchikey[:14]
            matched_connectivity = matched_inchikey[:14]
            if source_connectivity != matched_connectivity:
                return True
        
        return False
    
    def _formulas_compatible(self, formula1: str, formula2: str) -> bool:
        """Check if molecular formulas are compatible (allow hydration differences)."""
        
        # Simple heuristic: allow for water molecule differences
        # More sophisticated validation would use proper molecular formula parsing
        
        if formula1 == formula2:
            return True
        
        # Common compatible differences
        compatible_pairs = [
            ("H2O", ""),  # Hydrated vs anhydrous
            ("Na", "H"),  # Sodium salt vs free acid
            ("K", "H"),   # Potassium salt vs free acid
        ]
        
        for addition, subtraction in compatible_pairs:
            # Check if adding/subtracting makes formulas equivalent
            # Simplified check - real implementation would need proper parsing
            if addition in formula1 and subtraction in formula2:
                return True
            if addition in formula2 and subtraction in formula1:
                return True
        
        return False
    
    def _is_ambiguous_match(self, row: pd.Series) -> bool:
        """Check if result has multiple similar-confidence matches."""
        
        # Check for multiple matches in alternative_matches column
        alternatives = row.get("alternative_matches", [])
        if isinstance(alternatives, str):
            # Handle comma-separated string format
            alternatives = [alt.strip() for alt in alternatives.split(",") if alt.strip()]
        elif not isinstance(alternatives, list):
            alternatives = []
        
        # If there are multiple alternatives with similar confidence, flag it
        if len(alternatives) >= 2:
            confidence_score = row.get("confidence_score", 0.0)
            
            # Check if alternatives have confidence scores within 0.1 of primary match
            for alt in alternatives[:3]:  # Check first 3 alternatives
                alt_confidence = self._extract_confidence_from_alternative(alt)
                if alt_confidence is not None and abs(confidence_score - alt_confidence) < 0.1:
                    return True
        
        return False
    
    def _extract_confidence_from_alternative(self, alternative_match: str) -> Optional[float]:
        """Extract confidence score from alternative match string."""
        
        # Handle format like "compound_name (confidence: 0.85)"
        if "confidence:" in alternative_match:
            try:
                confidence_part = alternative_match.split("confidence:")[1]
                confidence_str = confidence_part.split(")")[0].strip()
                return float(confidence_str)
            except (IndexError, ValueError):
                pass
        
        return None
    
    def _extract_alternative_matches(self, row: pd.Series) -> List[str]:
        """Extract list of alternative matches from row."""
        
        alternatives = row.get("alternative_matches", [])
        if isinstance(alternatives, str):
            return [alt.strip() for alt in alternatives.split(",") if alt.strip()]
        elif isinstance(alternatives, list):
            return alternatives[:5]  # Limit to first 5
        else:
            return []
    
    def _apply_rate_limiting(self, decisions: List[FlaggingDecision]) -> List[FlaggingDecision]:
        """Apply rate limiting to control expert review workload."""
        
        # Count decisions requiring expert review
        review_decisions = [d for d in decisions if d.requires_action and 
                          d.category in [FlaggingCategory.EXPERT_REVIEW, 
                                       FlaggingCategory.STRUCTURAL_CONFLICT,
                                       FlaggingCategory.AMBIGUOUS_MATCH]]
        
        total_results = len(decisions)
        max_flagged = int(total_results * self.max_flagging_rate)
        
        if len(review_decisions) <= max_flagged:
            # Under limit, no changes needed
            return decisions
        
        logger.warning(f"Review workload exceeds limit: {len(review_decisions)} > {max_flagged}")
        logger.warning("Applying rate limiting based on priority and confidence")
        
        # Sort by priority (1=high) and confidence (desc for ties)
        review_decisions.sort(key=lambda d: (d.priority, -d.confidence_score))
        
        # Keep top priority decisions, convert others to auto-accept/reject
        modified_decisions = decisions.copy()
        decisions_to_modify = review_decisions[max_flagged:]
        
        for decision in decisions_to_modify:
            # Find original decision and modify
            for i, orig_decision in enumerate(modified_decisions):
                if orig_decision.metabolite_id == decision.metabolite_id:
                    # Convert to auto-accept if confidence >= 0.80, otherwise auto-reject
                    if decision.confidence_score >= 0.80:
                        new_category = FlaggingCategory.AUTO_ACCEPT
                        new_reason = f"Rate-limited: converted to auto-accept (conf={decision.confidence_score:.3f})"
                    else:
                        new_category = FlaggingCategory.AUTO_REJECT
                        new_reason = f"Rate-limited: converted to auto-reject (conf={decision.confidence_score:.3f})"
                    
                    modified_decisions[i] = FlaggingDecision(
                        metabolite_id=decision.metabolite_id,
                        category=new_category,
                        confidence_score=decision.confidence_score,
                        flagging_reason=new_reason,
                        matched_name=decision.matched_name,
                        requires_action=False,
                        priority=3,
                        estimated_review_time=0
                    )
                    break
        
        # Log rate limiting impact
        final_review_count = len([d for d in modified_decisions if d.requires_action])
        logger.info(f"Rate limiting: {len(review_decisions)} -> {final_review_count} flagged for review")
        
        return modified_decisions
    
    def _add_flagging_columns(self, 
                             results_df: pd.DataFrame, 
                             decisions: List[FlaggingDecision]) -> pd.DataFrame:
        """Add expert review flagging columns to results DataFrame."""
        
        # Create flagging information columns
        flagged_df = results_df.copy()
        
        # Initialize columns
        flagged_df["expert_review_flag"] = False
        flagged_df["flagging_category"] = "auto_accept" 
        flagged_df["flagging_reason"] = ""
        flagged_df["review_priority"] = 3
        flagged_df["estimated_review_time_minutes"] = 0
        flagged_df["requires_expert_action"] = False
        flagged_df["alternative_matches_flagged"] = ""
        flagged_df["flagging_date"] = datetime.now().isoformat()
        
        # Apply decisions to corresponding rows
        metabolite_id_column = None
        for col in ["metabolite_id", "id", "identifier"]:
            if col in flagged_df.columns:
                metabolite_id_column = col
                break
        
        if not metabolite_id_column:
            logger.warning("No metabolite ID column found, using row index for flagging")
            
        decision_lookup = {d.metabolite_id: d for d in decisions}
        
        for idx, row in flagged_df.iterrows():
            if metabolite_id_column:
                metabolite_id = row[metabolite_id_column]
            else:
                metabolite_id = f"row_{idx}"
            
            decision = decision_lookup.get(metabolite_id)
            if not decision:
                continue
            
            # Update flagging columns
            flagged_df.at[idx, "expert_review_flag"] = decision.requires_action
            flagged_df.at[idx, "flagging_category"] = decision.category.value
            flagged_df.at[idx, "flagging_reason"] = decision.flagging_reason
            flagged_df.at[idx, "review_priority"] = decision.priority
            flagged_df.at[idx, "estimated_review_time_minutes"] = decision.estimated_review_time
            flagged_df.at[idx, "requires_expert_action"] = decision.requires_action
            
            if decision.alternative_matches:
                flagged_df.at[idx, "alternative_matches_flagged"] = "; ".join(decision.alternative_matches)
        
        return flagged_df
    
    def _generate_flagging_summary(self, decisions: List[FlaggingDecision]) -> Dict[str, Any]:
        """Generate summary of flagging decisions."""
        
        summary = {
            "total_processed": len(decisions),
            "requires_review": sum(1 for d in decisions if d.requires_action),
            "auto_accepted": sum(1 for d in decisions if d.category == FlaggingCategory.AUTO_ACCEPT),
            "auto_rejected": sum(1 for d in decisions if d.category == FlaggingCategory.AUTO_REJECT),
            "expert_review": sum(1 for d in decisions if d.category == FlaggingCategory.EXPERT_REVIEW),
            "structural_conflicts": sum(1 for d in decisions if d.category == FlaggingCategory.STRUCTURAL_CONFLICT),
            "ambiguous_matches": sum(1 for d in decisions if d.category == FlaggingCategory.AMBIGUOUS_MATCH),
            "edge_cases": sum(1 for d in decisions if d.category == FlaggingCategory.EDGE_CASE),
            "estimated_total_review_time": sum(d.estimated_review_time for d in decisions if d.requires_action)
        }
        
        # Calculate rates
        if summary["total_processed"] > 0:
            summary["review_rate"] = summary["requires_review"] / summary["total_processed"]
            summary["acceptance_rate"] = summary["auto_accepted"] / summary["total_processed"]
        else:
            summary["review_rate"] = 0.0
            summary["acceptance_rate"] = 0.0
        
        return summary
    
    def create_expert_review_batch(self, 
                                  flagged_results: pd.DataFrame,
                                  batch_size: int = 50) -> List[FlaggingBatch]:
        """
        Create batches of results for expert review.
        
        Args:
            flagged_results: DataFrame with flagging columns
            batch_size: Maximum number of items per batch
            
        Returns:
            List of FlaggingBatch objects for review
        """
        logger.info("Creating expert review batches...")
        
        # Get results requiring review
        review_results = flagged_results[flagged_results["requires_expert_action"] == True].copy()
        
        if len(review_results) == 0:
            logger.info("No results require expert review")
            return []
        
        # Sort by priority and confidence
        review_results = review_results.sort_values([
            "review_priority", "confidence_score"
        ], ascending=[True, False])
        
        # Create batches
        batches = []
        for i in range(0, len(review_results), batch_size):
            batch_data = review_results.iloc[i:i+batch_size]
            
            # Create flagging decisions for this batch
            decisions = []
            for _, row in batch_data.iterrows():
                metabolite_id = row.get("metabolite_id", f"unknown_{i}")
                decision = FlaggingDecision(
                    metabolite_id=metabolite_id,
                    category=FlaggingCategory(row["flagging_category"]),
                    confidence_score=row.get("confidence_score", 0.0),
                    flagging_reason=row["flagging_reason"],
                    matched_name=row.get("matched_name"),
                    alternative_matches=row["alternative_matches_flagged"].split("; ") if row["alternative_matches_flagged"] else [],
                    priority=row["review_priority"],
                    estimated_review_time=row["estimated_review_time_minutes"]
                )
                decisions.append(decision)
            
            # Create batch
            batch_id = f"batch_{len(batches)+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            total_time = sum(d.estimated_review_time for d in decisions)
            
            category_counts = {}
            for decision in decisions:
                category_counts[decision.category.value] = category_counts.get(decision.category.value, 0) + 1
            
            batch = FlaggingBatch(
                batch_id=batch_id,
                creation_date=datetime.now().isoformat(),
                total_flagged=len(decisions),
                decisions=decisions,
                estimated_total_time=total_time,
                flagging_summary=category_counts
            )
            
            batches.append(batch)
        
        logger.info(f"Created {len(batches)} expert review batches")
        logger.info(f"Total items for review: {sum(b.total_flagged for b in batches)}")
        logger.info(f"Estimated total review time: {sum(b.estimated_total_time for b in batches)} minutes")
        
        return batches
    
    def export_flagged_results_for_review(self, 
                                        flagged_results: pd.DataFrame,
                                        output_path: str = "/tmp/expert_review_export.csv") -> str:
        """
        Export flagged results to CSV for expert review in external tools.
        
        Creates a simplified CSV that researchers can review in Excel, R, or Python.
        """
        logger.info(f"Exporting flagged results for expert review to {output_path}")
        
        # Select columns relevant for expert review
        review_columns = [
            "metabolite_id", 
            "matched_name",
            "confidence_score",
            "expert_review_flag",
            "flagging_category", 
            "flagging_reason",
            "review_priority",
            "alternative_matches_flagged",
            "estimated_review_time_minutes"
        ]
        
        # Add any additional columns that exist in the dataframe
        additional_columns = [
            "source_name", "matched_database", "molecular_formula",
            "inchikey", "smiles", "stage_matched"
        ]
        
        for col in additional_columns:
            if col in flagged_results.columns:
                review_columns.append(col)
        
        # Select available columns
        available_columns = [col for col in review_columns if col in flagged_results.columns]
        export_df = flagged_results[available_columns].copy()
        
        # Add reviewer columns for decision tracking
        export_df["reviewer_name"] = ""
        export_df["reviewer_decision"] = ""  # accept, reject, needs_more_info
        export_df["reviewer_comments"] = ""
        export_df["review_date"] = ""
        export_df["final_confidence_score"] = export_df.get("confidence_score", 0.0)
        
        # Sort by priority for easier review
        export_df = export_df.sort_values([
            "review_priority", "confidence_score"
        ], ascending=[True, False])
        
        # Export to CSV
        export_df.to_csv(output_path, index=False)
        
        # Create review instructions file
        instructions_path = output_path.replace(".csv", "_instructions.md")
        self._create_review_instructions(instructions_path, export_df)
        
        logger.info(f"Exported {len(export_df)} results for expert review")
        logger.info(f"Review instructions saved to {instructions_path}")
        
        return output_path
    
    def _create_review_instructions(self, instructions_path: str, export_df: pd.DataFrame) -> None:
        """Create review instructions for experts."""
        
        instructions = f"""# Expert Review Instructions

## Overview
This file contains {len(export_df)} metabolite mappings that require expert validation.

## Review Process

1. **Open the CSV file** in Excel, R, or your preferred data analysis tool
2. **Review each flagged mapping** based on biological knowledge
3. **Fill in the reviewer columns**:
   - `reviewer_name`: Your name/initials
   - `reviewer_decision`: One of: accept, reject, needs_more_info
   - `reviewer_comments`: Explanation for your decision
   - `review_date`: Date of review (YYYY-MM-DD format)
   - `final_confidence_score`: Your confidence score (0.0-1.0)

## Flagging Categories

- **expert_review**: Medium confidence requiring validation
- **structural_conflict**: Chemical structure validation failed  
- **ambiguous_match**: Multiple similar-confidence matches
- **edge_case**: Known problematic patterns

## Review Priority

- **Priority 1 (High)**: Structural conflicts requiring immediate attention
- **Priority 2 (Medium)**: Standard expert review cases
- **Priority 3 (Low)**: Edge cases with known workarounds

## Decision Guidelines

### Accept
- Chemical structure matches or is compatible
- Biological context is appropriate
- Confidence score is reasonable for match quality

### Reject  
- Clear chemical structure mismatch
- Inappropriate biological context
- Confidence score overestimates match quality

### Needs More Info
- Insufficient information to make decision
- Requires additional database lookup
- Need clarification on biological context

## Return Process

1. Save the completed CSV file
2. Email to: [your_email@example.com]
3. Subject: "Expert Review Complete - [filename]"

## Questions?
Contact [support_contact] for assistance.

## Statistics

- Total flagged: {len(export_df):,}
- High priority: {len(export_df[export_df['review_priority'] == 1]):,}
- Medium priority: {len(export_df[export_df['review_priority'] == 2]):,}
- Low priority: {len(export_df[export_df['review_priority'] == 3]):,}
- Estimated review time: {export_df['estimated_review_time_minutes'].sum():,} minutes
"""
        
        with open(instructions_path, 'w') as f:
            f.write(instructions)