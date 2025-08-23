"""
HMDB Vector Matching using Qdrant and FastEmbed for Stage 4 of progressive metabolite mapping.

This action leverages pre-computed HMDB embeddings stored in Qdrant to find similar metabolites
based on semantic similarity of names and descriptions.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import warnings

import numpy as np
from pydantic import BaseModel, Field, validator

from actions.typed_base import TypedStrategyAction
from actions.registry import register_action

logger = logging.getLogger(__name__)


class HMDBVectorMatchParams(BaseModel):
    """Parameters for HMDB vector matching using Qdrant."""
    
    # Standard parameter names (PARAMETER_NAMING_STANDARD.md compliant)
    input_key: str = Field(
        ...,
        description="Key for unmapped metabolites from previous stages"
    )
    output_key: str = Field(
        ...,
        description="Key for vector-matched metabolites"
    )
    
    # Optional for backward compatibility
    unmatched_key: Optional[str] = Field(
        None,
        description="Key for still unmapped after vector matching"
    )
    
    # Column specifications
    identifier_column: str = Field(
        "BIOCHEMICAL_NAME",
        description="Column containing metabolite names/identifiers"
    )
    
    # Vector search parameters
    threshold: float = Field(
        0.75,
        ge=0.0, le=1.0,
        description="Minimum similarity score for accepting matches"
    )
    top_k: int = Field(
        5,
        description="Number of top candidates to retrieve per query"
    )
    
    # Qdrant configuration
    collection_name: str = Field(
        "hmdb_metabolites",
        description="Qdrant collection name"
    )
    qdrant_path: str = Field(
        "/home/ubuntu/biomapper/data/qdrant_storage",
        description="Path to Qdrant storage"
    )
    
    # Embedding configuration
    embedding_model: str = Field(
        "sentence-transformers/all-MiniLM-L6-v2",
        description="FastEmbed model name"
    )
    
    # LLM validation (optional)
    enable_llm_validation: bool = Field(
        False,
        description="Enable LLM validation for high-confidence matches"
    )
    llm_confidence_threshold: float = Field(
        0.85,
        description="Minimum LLM confidence for accepting matches"
    )
    max_llm_calls: int = Field(
        20,
        description="Maximum LLM calls to control costs"
    )
    
    # Performance
    batch_size: int = Field(
        32,
        description="Batch size for embedding generation"
    )
    
    # Backward compatibility
    dataset_key: Optional[str] = Field(None, description="Deprecated - use input_key")
    output_dataset: Optional[str] = Field(None, description="Deprecated - use output_key")
    
    @validator('input_key', always=True)
    def handle_input_backward_compatibility(cls, v, values):
        """Handle backward compatibility for input_key parameter."""
        if v is None and 'dataset_key' in values and values['dataset_key'] is not None:
            warnings.warn(
                "Parameter 'dataset_key' is deprecated and will be removed in v3.0. "
                "Please use 'input_key' instead.",
                DeprecationWarning,
                stacklevel=2
            )
            return values['dataset_key']
        return v
    
    @validator('output_key', always=True)
    def handle_output_backward_compatibility(cls, v, values):
        """Handle backward compatibility for output_key parameter."""
        if v is None and 'output_dataset' in values and values['output_dataset'] is not None:
            warnings.warn(
                "Parameter 'output_dataset' is deprecated and will be removed in v3.0. "
                "Please use 'output_key' instead.",
                DeprecationWarning,
                stacklevel=2
            )
            return values['output_dataset']
        return v


class HMDBVectorMatchResult(BaseModel):
    """Result of HMDB vector matching."""
    
    success: bool
    message: str
    matched_count: int
    unmatched_count: int
    average_similarity: float
    confidence_distribution: Dict[str, int]
    llm_calls_made: int = 0
    error: Optional[str] = None


@register_action("HMDB_VECTOR_MATCH")
class HMDBVectorMatchAction(TypedStrategyAction[HMDBVectorMatchParams, HMDBVectorMatchResult]):
    """
    Stage 4 metabolite matching using HMDB vector embeddings stored in Qdrant.
    
    This action uses pre-computed HMDB metabolite embeddings to find similar
    metabolites based on semantic similarity of names and descriptions.
    
    Features:
    - FastEmbed for efficient embedding generation
    - Qdrant vector database for similarity search
    - Optional LLM validation for high-confidence matches
    - Batch processing for performance
    - Standard parameter naming compliance
    """
    
    def __init__(self, db_session: Any = None):
        """Initialize the action."""
        super().__init__(db_session)
        self.qdrant_client = None
        self.embedding_model = None
        self.openai_client = None
    
    def get_params_model(self) -> type[HMDBVectorMatchParams]:
        """Return the params model class."""
        return HMDBVectorMatchParams
    
    def get_result_model(self) -> type[HMDBVectorMatchResult]:
        """Return the result model class."""
        return HMDBVectorMatchResult
    
    def _initialize_qdrant(self, params: HMDBVectorMatchParams) -> None:
        """Initialize Qdrant client."""
        if self.qdrant_client is None:
            try:
                from qdrant_client import QdrantClient
                
                # Connect to local Qdrant storage
                self.qdrant_client = QdrantClient(path=params.qdrant_path)
                
                # Verify collection exists
                collections = self.qdrant_client.get_collections()
                collection_names = [c.name for c in collections.collections]
                
                if params.collection_name not in collection_names:
                    raise ValueError(
                        f"Collection '{params.collection_name}' not found. "
                        f"Available collections: {collection_names}"
                    )
                
                logger.info(f"Connected to Qdrant collection: {params.collection_name}")
                
            except ImportError:
                raise ImportError(
                    "Qdrant client not found. Please install with: "
                    "pip install qdrant-client"
                )
    
    def _initialize_embedding_model(self, params: HMDBVectorMatchParams) -> None:
        """Initialize FastEmbed model."""
        if self.embedding_model is None:
            try:
                from fastembed import TextEmbedding
                
                # Initialize FastEmbed model
                self.embedding_model = TextEmbedding(model_name=params.embedding_model)
                logger.info(f"Initialized FastEmbed model: {params.embedding_model}")
                
            except ImportError:
                raise ImportError(
                    "FastEmbed not found. Please install with: "
                    "pip install fastembed"
                )
    
    def _initialize_llm_client(self) -> None:
        """Initialize OpenAI client for LLM validation."""
        if self.openai_client is None:
            try:
                import openai
                
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    logger.warning("OPENAI_API_KEY not set - LLM validation disabled")
                    return
                
                self.openai_client = openai.OpenAI(api_key=api_key)
                logger.info("Initialized OpenAI client for LLM validation")
                
            except ImportError:
                logger.warning("OpenAI library not found - LLM validation disabled")
    
    def _generate_embeddings(
        self,
        texts: List[str],
        batch_size: int
    ) -> List[List[float]]:
        """Generate embeddings for metabolite names using FastEmbed."""
        embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Generate embeddings
            batch_embeddings = list(self.embedding_model.embed(batch))
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    def _search_similar_metabolites(
        self,
        query_embedding: List[float],
        collection_name: str,
        top_k: int,
        threshold: float
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Search for similar metabolites in Qdrant."""
        from qdrant_client.models import PointStruct
        
        # Search in Qdrant
        search_result = self.qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=top_k,
            score_threshold=threshold
        )
        
        # Extract results
        results = []
        for hit in search_result:
            payload = hit.payload if hasattr(hit, 'payload') else {}
            score = hit.score if hasattr(hit, 'score') else 0.0
            results.append((payload, float(score)))
        
        return results
    
    async def _validate_with_llm(
        self,
        source_name: str,
        candidate_name: str,
        candidate_info: Dict[str, Any],
        similarity_score: float,
        confidence_threshold: float
    ) -> Tuple[bool, float, str]:
        """Validate match using LLM for high-confidence verification."""
        if not self.openai_client:
            return False, 0.0, "LLM client not initialized"
        
        # Build prompt
        prompt = f"""Determine if these metabolites are the same compound:

Source Metabolite: {source_name}

Candidate Match:
- Name: {candidate_name}
- HMDB ID: {candidate_info.get('hmdb_id', 'Unknown')}
- Description: {candidate_info.get('description', 'No description')[:200]}
- Synonyms: {', '.join(candidate_info.get('synonyms', [])[:5])}
- Vector Similarity: {similarity_score:.3f}

Are these the same metabolite? Respond with:
1. YES/NO
2. Confidence (0-1)
3. Brief reasoning (1 sentence)

Format: YES|0.95|Both refer to the same glucose metabolite."""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a biochemistry expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=100
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            parts = content.split("|", 2)
            
            if len(parts) >= 3:
                decision = parts[0].strip().upper()
                confidence = float(parts[1].strip())
                reasoning = parts[2].strip()
                
                is_match = decision == "YES" and confidence >= confidence_threshold
                return is_match, confidence, reasoning
            
        except Exception as e:
            logger.error(f"LLM validation error: {e}")
        
        return False, 0.0, "LLM validation failed"
    
    async def execute(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        action_params: Dict[str, Any],
        source_endpoint: Any,
        target_endpoint: Any,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute with backward compatibility wrapper."""
        # Convert parameters to typed model
        try:
            params = HMDBVectorMatchParams(**action_params)
        except Exception as e:
            logger.error(f"Invalid action parameters: {e}")
            return {
                "output_identifiers": [],
                "details": {"error": f"Invalid parameters: {str(e)}"}
            }
        
        # Call the typed implementation
        try:
            result = await self.execute_typed(params, context)
            # Convert result to dict
            return result.dict() if hasattr(result, 'dict') else {}
        except Exception as e:
            logger.error(f"Error executing action: {e}", exc_info=True)
            return {
                "output_identifiers": [],
                "details": {"error": f"Execution error: {str(e)}"}
            }
    
    async def execute_typed(
        self,
        params: HMDBVectorMatchParams,
        context: Dict[str, Any]
    ) -> HMDBVectorMatchResult:
        """Execute HMDB vector matching for Stage 4."""
        try:
            # Initialize clients
            self._initialize_qdrant(params)
            self._initialize_embedding_model(params)
            
            if params.enable_llm_validation:
                self._initialize_llm_client()
            
            # Get datasets from context
            datasets = context.get("datasets", {})
            
            # Get unmapped metabolites
            unmapped = datasets.get(params.input_key)
            if unmapped is None or (hasattr(unmapped, 'empty') and unmapped.empty):
                return HMDBVectorMatchResult(
                    success=True,
                    message="No unmapped metabolites to process",
                    matched_count=0,
                    unmatched_count=0,
                    average_similarity=0.0,
                    confidence_distribution={},
                    llm_calls_made=0
                )
            
            # Extract metabolite names
            metabolite_names = unmapped[params.identifier_column].tolist()
            logger.info(f"Stage 4: Processing {len(metabolite_names)} unmapped metabolites")
            
            # Generate embeddings for unmapped metabolites
            logger.info("Generating embeddings for unmapped metabolites...")
            query_embeddings = self._generate_embeddings(
                metabolite_names,
                params.batch_size
            )
            
            # Search for similar metabolites
            matched = []
            still_unmatched = []
            total_similarity = 0.0
            llm_calls = 0
            confidence_dist = {
                "high_0.9+": 0,
                "medium_0.8-0.9": 0,
                "low_0.7-0.8": 0,
                "vector_only": 0
            }
            
            for idx, (name, embedding) in enumerate(zip(metabolite_names, query_embeddings)):
                # Search in Qdrant
                candidates = self._search_similar_metabolites(
                    embedding,
                    params.collection_name,
                    params.top_k,
                    params.threshold
                )
                
                if not candidates:
                    still_unmatched.append(unmapped.iloc[idx].to_dict())
                    continue
                
                # Get best candidate
                best_candidate, best_score = candidates[0]
                
                # Optional LLM validation
                if params.enable_llm_validation and llm_calls < params.max_llm_calls:
                    is_valid, llm_confidence, reasoning = await self._validate_with_llm(
                        name,
                        best_candidate.get('name', ''),
                        best_candidate,
                        best_score,
                        params.llm_confidence_threshold
                    )
                    llm_calls += 1
                    
                    if not is_valid:
                        still_unmatched.append(unmapped.iloc[idx].to_dict())
                        continue
                    
                    final_confidence = (best_score + llm_confidence) / 2
                else:
                    final_confidence = best_score
                    reasoning = "Vector similarity match"
                
                # Create match record
                match_record = unmapped.iloc[idx].to_dict()
                match_record.update({
                    'matched_name': best_candidate.get('name', ''),
                    'matched_hmdb_id': best_candidate.get('hmdb_id', ''),
                    'match_confidence': final_confidence,
                    'vector_similarity': best_score,
                    'match_method': 'hmdb_vector',
                    'match_stage': 4,
                    'match_reasoning': reasoning
                })
                
                matched.append(match_record)
                total_similarity += best_score
                
                # Update confidence distribution
                if final_confidence >= 0.9:
                    confidence_dist["high_0.9+"] += 1
                elif final_confidence >= 0.8:
                    confidence_dist["medium_0.8-0.9"] += 1
                elif final_confidence >= 0.7:
                    confidence_dist["low_0.7-0.8"] += 1
                else:
                    confidence_dist["vector_only"] += 1
            
            # Convert to DataFrames
            import pandas as pd
            matched_df = pd.DataFrame(matched) if matched else pd.DataFrame()
            unmatched_df = pd.DataFrame(still_unmatched) if still_unmatched else pd.DataFrame()
            
            # Store results in context
            datasets[params.output_key] = matched_df
            if params.unmatched_key:
                datasets[params.unmatched_key] = unmatched_df
            
            # Calculate statistics
            avg_similarity = total_similarity / len(matched) if matched else 0.0
            
            # Update progressive statistics
            statistics = context.get('statistics', {})
            statistics['stage_4_hmdb_vector'] = {
                'matched': len(matched),
                'unmatched': len(still_unmatched),
                'average_similarity': avg_similarity,
                'confidence_distribution': confidence_dist,
                'llm_calls': llm_calls
            }
            context['statistics'] = statistics
            
            logger.info(
                f"Stage 4 Complete: {len(matched)} matched via HMDB vectors, "
                f"{len(still_unmatched)} still unmatched"
            )
            
            return HMDBVectorMatchResult(
                success=True,
                message=f"Successfully matched {len(matched)} metabolites using HMDB vectors",
                matched_count=len(matched),
                unmatched_count=len(still_unmatched),
                average_similarity=avg_similarity,
                confidence_distribution=confidence_dist,
                llm_calls_made=llm_calls
            )
            
        except Exception as e:
            logger.error(f"Error in HMDB vector matching: {str(e)}")
            return HMDBVectorMatchResult(
                success=False,
                message=f"HMDB vector matching failed: {str(e)}",
                matched_count=0,
                unmatched_count=0,
                average_similarity=0.0,
                confidence_distribution={},
                error=str(e)
            )