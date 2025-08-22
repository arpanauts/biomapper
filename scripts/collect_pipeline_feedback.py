#!/usr/bin/env python3
"""
Feedback Collection and Monitoring System for Metabolomics Pipeline

Aggregates expert review decisions, identifies systematic issues,
and generates weekly reports for threshold adjustment.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import glob

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FeedbackMetrics:
    """Metrics collected from expert review feedback."""
    
    total_reviewed: int
    accept_count: int
    reject_count: int
    needs_info_count: int
    
    false_positive_count: int
    false_negative_count: int
    
    avg_confidence_accepted: float
    avg_confidence_rejected: float
    
    review_time_hours: float
    reviewer_agreement_rate: float
    
    systematic_issues: List[str]
    threshold_recommendations: Dict[str, float]


class FeedbackCollector:
    """Collects and analyzes feedback from expert reviews."""
    
    def __init__(self, feedback_dir: str = "/tmp/metabolomics_feedback"):
        self.feedback_dir = Path(feedback_dir)
        self.feedback_dir.mkdir(exist_ok=True)
        
        self.aggregated_data = []
        self.systematic_issues = []
        self.threshold_performance = {}
        
    def collect_review_files(self, review_pattern: str = "*review*.csv") -> List[Path]:
        """Collect all review CSV files."""
        
        review_files = list(self.feedback_dir.glob(review_pattern))
        logger.info(f"Found {len(review_files)} review files to process")
        
        return sorted(review_files)
    
    def parse_review_file(self, file_path: Path) -> pd.DataFrame:
        """Parse a single review CSV file."""
        
        try:
            df = pd.read_csv(file_path)
            
            # Required columns for processing
            required_cols = [
                'metabolite_id', 'confidence_score', 
                'reviewer_decision', 'reviewer_name'
            ]
            
            if all(col in df.columns for col in required_cols):
                # Only keep reviewed items
                reviewed = df[df['reviewer_decision'].notna()].copy()
                reviewed['review_file'] = file_path.name
                reviewed['review_date'] = pd.to_datetime(
                    df['review_date'], 
                    errors='coerce'
                ).fillna(datetime.now())
                
                logger.info(f"Parsed {len(reviewed)} reviewed items from {file_path.name}")
                return reviewed
            else:
                logger.warning(f"Missing required columns in {file_path.name}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return pd.DataFrame()
    
    def aggregate_feedback(self, review_files: List[Path]) -> pd.DataFrame:
        """Aggregate feedback from multiple review files."""
        
        all_reviews = []
        
        for file_path in review_files:
            reviews = self.parse_review_file(file_path)
            if not reviews.empty:
                all_reviews.append(reviews)
        
        if all_reviews:
            aggregated = pd.concat(all_reviews, ignore_index=True)
            logger.info(f"Aggregated {len(aggregated)} total reviews")
            return aggregated
        else:
            logger.warning("No reviews to aggregate")
            return pd.DataFrame()
    
    def analyze_decision_patterns(self, reviews_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze patterns in review decisions."""
        
        if reviews_df.empty:
            return {}
        
        patterns = {
            'decision_distribution': reviews_df['reviewer_decision'].value_counts().to_dict(),
            'confidence_by_decision': {},
            'stage_performance': {},
            'metabolite_class_issues': {}
        }
        
        # Confidence analysis by decision
        for decision in ['accept', 'reject', 'needs_more_info']:
            decision_data = reviews_df[reviews_df['reviewer_decision'] == decision]
            if not decision_data.empty:
                patterns['confidence_by_decision'][decision] = {
                    'mean': decision_data['confidence_score'].mean(),
                    'std': decision_data['confidence_score'].std(),
                    'min': decision_data['confidence_score'].min(),
                    'max': decision_data['confidence_score'].max(),
                    'count': len(decision_data)
                }
        
        # Stage performance (if stage column exists)
        if 'matched_stage' in reviews_df.columns:
            for stage in reviews_df['matched_stage'].unique():
                stage_data = reviews_df[reviews_df['matched_stage'] == stage]
                accept_rate = (stage_data['reviewer_decision'] == 'accept').mean()
                patterns['stage_performance'][stage] = {
                    'accept_rate': accept_rate,
                    'total_reviewed': len(stage_data)
                }
        
        return patterns
    
    def identify_systematic_issues(self, reviews_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Identify systematic issues from review patterns."""
        
        issues = []
        
        if reviews_df.empty:
            return issues
        
        # Issue 1: High confidence rejections (potential false positives)
        high_conf_rejects = reviews_df[
            (reviews_df['reviewer_decision'] == 'reject') & 
            (reviews_df['confidence_score'] >= 0.80)
        ]
        
        if len(high_conf_rejects) > 0:
            issues.append({
                'type': 'high_confidence_false_positives',
                'severity': 'high',
                'count': len(high_conf_rejects),
                'examples': high_conf_rejects[['metabolite_id', 'confidence_score']].head(5).to_dict('records'),
                'recommendation': 'Review Stage 2 fuzzy matching algorithm'
            })
        
        # Issue 2: Low confidence accepts (potential threshold too low)
        low_conf_accepts = reviews_df[
            (reviews_df['reviewer_decision'] == 'accept') & 
            (reviews_df['confidence_score'] < 0.70)
        ]
        
        if len(low_conf_accepts) > 0:
            issues.append({
                'type': 'low_confidence_accepts',
                'severity': 'medium',
                'count': len(low_conf_accepts),
                'examples': low_conf_accepts[['metabolite_id', 'confidence_score']].head(5).to_dict('records'),
                'recommendation': 'Consider raising auto-reject threshold'
            })
        
        # Issue 3: High "needs more info" rate
        needs_info_rate = (reviews_df['reviewer_decision'] == 'needs_more_info').mean()
        
        if needs_info_rate > 0.20:
            issues.append({
                'type': 'high_uncertainty_rate',
                'severity': 'medium',
                'rate': needs_info_rate,
                'recommendation': 'Improve reference database coverage'
            })
        
        # Issue 4: Reviewer disagreement (if multiple reviewers)
        if 'reviewer_name' in reviews_df.columns:
            metabolites_multi_review = reviews_df.groupby('metabolite_id')['reviewer_name'].nunique()
            multi_reviewed = metabolites_multi_review[metabolites_multi_review > 1].index
            
            disagreements = []
            for metabolite in multi_reviewed:
                decisions = reviews_df[reviews_df['metabolite_id'] == metabolite]['reviewer_decision'].unique()
                if len(decisions) > 1:
                    disagreements.append(metabolite)
            
            if disagreements:
                issues.append({
                    'type': 'reviewer_disagreement',
                    'severity': 'high',
                    'count': len(disagreements),
                    'metabolites': disagreements[:5],
                    'recommendation': 'Clarify review guidelines for edge cases'
                })
        
        return issues
    
    def calculate_threshold_recommendations(self, reviews_df: pd.DataFrame) -> Dict[str, float]:
        """Calculate recommended threshold adjustments based on feedback."""
        
        recommendations = {}
        
        if reviews_df.empty:
            return recommendations
        
        # Calculate optimal auto-accept threshold
        # Find confidence where 95% of accepts are above
        accepts = reviews_df[reviews_df['reviewer_decision'] == 'accept']['confidence_score']
        if not accepts.empty:
            optimal_accept = accepts.quantile(0.05)  # 95% above this
            recommendations['auto_accept_threshold'] = round(optimal_accept, 2)
        
        # Calculate optimal auto-reject threshold  
        # Find confidence where 95% of rejects are below
        rejects = reviews_df[reviews_df['reviewer_decision'] == 'reject']['confidence_score']
        if not rejects.empty:
            optimal_reject = rejects.quantile(0.95)  # 95% below this
            recommendations['auto_reject_threshold'] = round(optimal_reject, 2)
        
        # Stage-specific recommendations
        if 'matched_stage' in reviews_df.columns:
            for stage in [1, 2, 3]:
                stage_str = str(stage)
                stage_data = reviews_df[reviews_df['matched_stage'] == stage_str]
                
                if not stage_data.empty:
                    # Find threshold where false positive rate < 5%
                    stage_accepts = stage_data[stage_data['reviewer_decision'] == 'accept']
                    if not stage_accepts.empty:
                        stage_threshold = stage_accepts['confidence_score'].quantile(0.10)
                        recommendations[f'stage_{stage}_threshold'] = round(stage_threshold, 2)
        
        return recommendations
    
    def generate_weekly_report(self) -> Dict[str, Any]:
        """Generate comprehensive weekly feedback report."""
        
        # Collect all review files from past week
        review_files = self.collect_review_files()
        
        if not review_files:
            logger.warning("No review files found for weekly report")
            return {}
        
        # Aggregate feedback
        all_reviews = self.aggregate_feedback(review_files)
        
        if all_reviews.empty:
            logger.warning("No reviews to analyze")
            return {}
        
        # Analyze patterns
        decision_patterns = self.analyze_decision_patterns(all_reviews)
        systematic_issues = self.identify_systematic_issues(all_reviews)
        threshold_recommendations = self.calculate_threshold_recommendations(all_reviews)
        
        # Calculate key metrics
        metrics = FeedbackMetrics(
            total_reviewed=len(all_reviews),
            accept_count=len(all_reviews[all_reviews['reviewer_decision'] == 'accept']),
            reject_count=len(all_reviews[all_reviews['reviewer_decision'] == 'reject']),
            needs_info_count=len(all_reviews[all_reviews['reviewer_decision'] == 'needs_more_info']),
            
            false_positive_count=len(all_reviews[
                (all_reviews['reviewer_decision'] == 'reject') & 
                (all_reviews['confidence_score'] >= 0.80)
            ]),
            false_negative_count=len(all_reviews[
                (all_reviews['reviewer_decision'] == 'accept') & 
                (all_reviews['confidence_score'] < 0.70)
            ]),
            
            avg_confidence_accepted=all_reviews[
                all_reviews['reviewer_decision'] == 'accept'
            ]['confidence_score'].mean() if any(all_reviews['reviewer_decision'] == 'accept') else 0,
            
            avg_confidence_rejected=all_reviews[
                all_reviews['reviewer_decision'] == 'reject'
            ]['confidence_score'].mean() if any(all_reviews['reviewer_decision'] == 'reject') else 0,
            
            review_time_hours=len(all_reviews) * 4 / 60,  # 4 minutes per item estimate
            reviewer_agreement_rate=0.85,  # Placeholder - calculate if multiple reviewers
            
            systematic_issues=[issue['type'] for issue in systematic_issues],
            threshold_recommendations=threshold_recommendations
        )
        
        # Create report
        report = {
            'report_date': datetime.now().isoformat(),
            'period': 'weekly',
            'files_processed': len(review_files),
            
            'summary_metrics': {
                'total_reviewed': metrics.total_reviewed,
                'accept_rate': metrics.accept_count / metrics.total_reviewed if metrics.total_reviewed > 0 else 0,
                'reject_rate': metrics.reject_count / metrics.total_reviewed if metrics.total_reviewed > 0 else 0,
                'needs_info_rate': metrics.needs_info_count / metrics.total_reviewed if metrics.total_reviewed > 0 else 0,
                'false_positive_rate': metrics.false_positive_count / metrics.total_reviewed if metrics.total_reviewed > 0 else 0,
                'estimated_review_hours': metrics.review_time_hours
            },
            
            'decision_patterns': decision_patterns,
            'systematic_issues': systematic_issues,
            'threshold_recommendations': threshold_recommendations,
            
            'action_items': self._generate_action_items(metrics, systematic_issues)
        }
        
        return report
    
    def _generate_action_items(self, metrics: FeedbackMetrics, issues: List[Dict]) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        
        actions = []
        
        # Check false positive rate
        if metrics.total_reviewed > 0:
            fp_rate = metrics.false_positive_count / metrics.total_reviewed
            if fp_rate > 0.05:
                actions.append(f"URGENT: False positive rate ({fp_rate:.1%}) exceeds 5% target - raise thresholds")
        
        # Check systematic issues
        high_severity_issues = [i for i in issues if i.get('severity') == 'high']
        if high_severity_issues:
            actions.append(f"Address {len(high_severity_issues)} high-severity systematic issues")
        
        # Check threshold adjustments
        if metrics.threshold_recommendations:
            actions.append("Consider threshold adjustments based on recommendations")
        
        # Check review workload
        if metrics.review_time_hours > 4:
            actions.append(f"Review workload high ({metrics.review_time_hours:.1f} hours) - consider automation")
        
        return actions
    
    def save_report(self, report: Dict[str, Any]) -> str:
        """Save weekly report to JSON file."""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.feedback_dir / f"weekly_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Report saved to {report_file}")
        return str(report_file)
    
    def print_report_summary(self, report: Dict[str, Any]) -> None:
        """Print human-readable report summary."""
        
        print("\n" + "="*60)
        print("METABOLOMICS PIPELINE WEEKLY FEEDBACK REPORT")
        print("="*60)
        
        print(f"\nReport Date: {report['report_date']}")
        print(f"Files Processed: {report['files_processed']}")
        
        metrics = report['summary_metrics']
        print("\n--- Review Summary ---")
        print(f"Total Reviewed: {metrics['total_reviewed']}")
        print(f"Accept Rate: {metrics['accept_rate']:.1%}")
        print(f"Reject Rate: {metrics['reject_rate']:.1%}")
        print(f"Needs Info Rate: {metrics['needs_info_rate']:.1%}")
        print(f"False Positive Rate: {metrics['false_positive_rate']:.1%}")
        print(f"Estimated Review Time: {metrics['estimated_review_hours']:.1f} hours")
        
        if report['systematic_issues']:
            print("\n--- Systematic Issues Identified ---")
            for issue in report['systematic_issues']:
                print(f"• {issue['type']} (Severity: {issue['severity']})")
                print(f"  Count: {issue.get('count', 'N/A')}")
                print(f"  Recommendation: {issue['recommendation']}")
        
        if report['threshold_recommendations']:
            print("\n--- Threshold Recommendations ---")
            for param, value in report['threshold_recommendations'].items():
                print(f"• {param}: {value}")
        
        if report['action_items']:
            print("\n--- Action Items ---")
            for i, action in enumerate(report['action_items'], 1):
                print(f"{i}. {action}")


def create_sample_feedback_data():
    """Create sample feedback data for testing."""
    
    feedback_dir = Path("/tmp/metabolomics_feedback")
    feedback_dir.mkdir(exist_ok=True)
    
    # Create sample review file
    sample_reviews = pd.DataFrame({
        'metabolite_id': ['MET_001', 'MET_002', 'MET_003', 'MET_004', 'MET_005'],
        'matched_name': ['Glucose', 'Cholesterol', 'Alanine', 'Citrate', 'Unknown'],
        'confidence_score': [0.92, 0.78, 0.65, 0.83, 0.71],
        'matched_stage': ['1', '2', '3', '2', '3'],
        'reviewer_decision': ['accept', 'accept', 'reject', 'accept', 'needs_more_info'],
        'reviewer_name': ['JD', 'JD', 'JD', 'JD', 'JD'],
        'reviewer_comments': [
            'Clear match', 
            'Fuzzy match but acceptable',
            'Wrong metabolite class',
            'Good match',
            'Need structure verification'
        ],
        'review_date': datetime.now().strftime('%Y-%m-%d'),
        'final_confidence_score': [0.95, 0.80, 0.40, 0.85, 0.70]
    })
    
    sample_file = feedback_dir / "sample_review_complete.csv"
    sample_reviews.to_csv(sample_file, index=False)
    logger.info(f"Created sample feedback file: {sample_file}")
    
    return sample_file


def main():
    """Run feedback collection and generate report."""
    
    # Initialize collector
    collector = FeedbackCollector()
    
    # Create sample data for demonstration
    sample_file = create_sample_feedback_data()
    
    # Generate weekly report
    report = collector.generate_weekly_report()
    
    if report:
        # Save report
        report_file = collector.save_report(report)
        
        # Print summary
        collector.print_report_summary(report)
        
        print(f"\n✓ Full report saved to: {report_file}")
        
        # Check if phase advancement is recommended
        if report['summary_metrics'].get('false_positive_rate', 1.0) < 0.05:
            print("\n✓ Pipeline performing well - consider advancing to next phase")
        else:
            print("\n⚠ Review systematic issues before phase advancement")
    else:
        print("\n⚠ No feedback data available for report generation")
        print("   Ensure review CSV files are placed in /tmp/metabolomics_feedback/")


if __name__ == "__main__":
    main()