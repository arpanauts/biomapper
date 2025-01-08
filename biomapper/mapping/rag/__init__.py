from typing import Optional

from biomapper.mapping.rag.store import ChromaCompoundStore
from biomapper.mapping.rag.prompts import PromptManager
from biomapper.utils.optimization import DSPyOptimizer
from biomapper.schemas.store_schema import VectorStoreConfig
from biomapper.schemas.rag_schema import LLMMapperResult, Match, RAGMetrics
from biomapper.monitoring.langfuse_tracker import LangfuseTracker
from biomapper.monitoring.metrics import MetricsTracker
from biomapper.monitoring.traces import TraceManager
from biomapper.mapping.embeddings.managers import HuggingFaceEmbeddingManager

import time
import os


class RAGCompoundMapper:
    """Main interface for RAG-based compound mapping."""

    def __init__(
        self,
        langfuse_key: Optional[str] = None,
        store_config: Optional[VectorStoreConfig] = None,
    ) -> None:
        # Initialize monitoring
        load_env = os.getenv("ENVIRONMENT") == "development"
        self.tracker = LangfuseTracker(load_env=load_env)
        self.metrics = MetricsTracker(self.tracker)
        self.traces = TraceManager(self.tracker)

        # Initialize RAG components
        self.store = ChromaCompoundStore(store_config)
        self.prompt_manager = PromptManager()
        self.optimizer = DSPyOptimizer()
        self.embedding_manager = HuggingFaceEmbeddingManager()

    def map_compound(self, query: str) -> LLMMapperResult:
        """Map compound with monitoring."""
        trace_id = self.tracker.trace_mapping(query)

        start_time = time.time()
        try:
            # Do mapping
            result = self._do_mapping(query, trace_id)

            # Record metrics
            if result.metrics:
                metrics = RAGMetrics(
                    retrieval_latency_ms=result.metrics.get("retrieval_latency", 0),
                    generation_latency_ms=result.metrics.get("generation_latency", 0),
                    total_latency_ms=time.time() - start_time,
                    tokens_used=int(result.metrics.get("tokens_used", 0)),
                )
                self.metrics.record_metrics(metrics, trace_id)

            return result

        except Exception as e:
            if trace_id:
                self.tracker.record_error(trace_id, str(e))

            return LLMMapperResult(
                query_term=query,
                matches=[],
                best_match=Match(id="", name="", confidence="0.0", reasoning=str(e)),
                metrics={
                    "latency_ms": 0.0,
                    "tokens_used": 0.0,
                    "provider": 0.0,
                    "model": 0.0,
                    "cost": 0.0,
                },
                trace_id=trace_id or "",
                error=str(e),
            )

    def _do_mapping(
        self, query: str, trace_id: Optional[str] = None
    ) -> LLMMapperResult:
        """Internal method to perform the actual mapping.

        Args:
            query: The compound name or description to map
            trace_id: Optional trace ID for monitoring

        Returns:
            LLMMapperResult containing the mapping results and metrics
        """
        start_time = time.time()
        matches = []

        try:
            # Get relevant documents from vector store
            query_embedding = self.embedding_manager.embed_text(query)
            docs = self.store.get_relevant_compounds(query_embedding)

            # Convert CompoundDocument objects to dictionaries
            doc_dicts = [
                {"content": doc.content, "metadata": doc.metadata} for doc in docs
            ]

            # Generate mapping prediction
            compiler = self.optimizer.get_compiler()
            if compiler is None:
                raise ValueError("Failed to get DSPy compiler")

            prompt = self.prompt_manager.format_mapping_prompt(query, doc_dicts)
            prediction = compiler(
                query=query,
                context=prompt,
            )

            # Process matches
            for match_data in prediction.matches:
                match = Match(
                    id=match_data.id,
                    name=match_data.name,
                    confidence=str(match_data.confidence),
                    reasoning=match_data.reasoning,
                )
                matches.append(match)

            # Calculate metrics
            tokens_used = getattr(prediction, "tokens_used", 0)
            latency_ms = (time.time() - start_time) * 1000

            return LLMMapperResult(
                query_term=query,
                matches=matches,
                best_match=matches[0]
                if matches
                else Match(
                    id="", name="", confidence="0.0", reasoning="No matches found"
                ),
                metrics={
                    "latency_ms": latency_ms,
                    "tokens_used": float(tokens_used),
                    "provider": 1.0,  # rag
                    "model": 1.0,  # compound_mapper
                    "cost": 0.0,
                },
                trace_id=trace_id or "",
            )

        except Exception as e:
            # Return empty result with error
            return LLMMapperResult(
                query_term=query,
                matches=[],
                best_match=Match(id="", name="", confidence="0.0", reasoning=str(e)),
                metrics={
                    "latency_ms": 0.0,
                    "tokens_used": 0.0,
                    "provider": 0.0,
                    "model": 0.0,
                    "cost": 0.0,
                },
                trace_id=trace_id or "",
                error=str(e),
            )
