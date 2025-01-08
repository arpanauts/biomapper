"""Multi-provider RAG implementation for biomapper."""

from typing import Dict, List, Optional, Any

import pandas as pd
from pydantic import BaseModel
from langfuse.decorators import langfuse_context

from .rag import RAGCompoundMapper
from ..schemas.rag_schema import LLMMapperResult, RAGMetrics, Match
from ..schemas.llm_schema import LLMMatch, MatchConfidence
from ..schemas.provider_schemas import (
    ProviderType,
    ProviderConfig,
)
from ..schemas.store_schema import VectorStoreConfig


class MultiProviderSignatureBase:
    """DSPy signature for multi-provider mapping."""

    contexts: Dict[str, str]
    query: str
    target_providers: List[str]
    matches: List[Dict[str, Any]]


class CrossReferenceResult(BaseModel):
    """Result of cross-reference resolution."""

    primary_match: LLMMatch
    xrefs: Dict[ProviderType, List[LLMMatch]]
    confidence: float


class MultiProviderMapper(RAGCompoundMapper):
    """Multi-provider RAG mapper with cross-reference resolution."""

    def __init__(
        self,
        providers: Dict[ProviderType, ProviderConfig],
        langfuse_key: Optional[str] = None,
        store_config: Optional[VectorStoreConfig] = None,
    ):
        """Initialize multi-provider mapper.

        Args:
            providers: Dictionary of provider configurations
            langfuse_key: Optional Langfuse API key for monitoring
            store_config: Optional vector store configuration
        """
        # Initialize base RAG mapper
        super().__init__(langfuse_key=langfuse_key, store_config=store_config)

        self.providers = providers
        self.knowledge_bases: Dict[ProviderType, pd.DataFrame] = {}
        self._initialize_predictor()

        # Load knowledge bases for each provider
        for provider_type, config in providers.items():
            if config.data_path is None:
                continue
            df = pd.read_csv(config.data_path, sep="\t")

            # Apply provider-specific preprocessing
            if provider_type == ProviderType.CHEBI:
                df = self._preprocess_chebi(df)
            elif provider_type == ProviderType.UNICHEM:
                df = self._preprocess_unichem(df)
            elif provider_type == ProviderType.REFMET:
                df = self._preprocess_refmet(df)

            self.knowledge_bases[provider_type] = df

    def _load_provider_kb(
        self, provider: ProviderType, config: ProviderConfig
    ) -> pd.DataFrame:
        """Load and process provider-specific knowledge base.

        Args:
            provider: Provider type
            config: Provider configuration

        Returns:
            Processed knowledge base DataFrame
        """
        if config.data_path is None:
            return pd.DataFrame()

        df = pd.read_csv(config.data_path, sep="\t")

        # Apply provider-specific preprocessing
        if provider == ProviderType.CHEBI:
            df = self._preprocess_chebi(df)
        elif provider == ProviderType.UNICHEM:
            df = self._preprocess_unichem(df)
        elif provider == ProviderType.REFMET:
            df = self._preprocess_refmet(df)

        return df

    def _preprocess_chebi(self, df: pd.DataFrame) -> pd.DataFrame:
        """Preprocess ChEBI data."""
        df["text"] = df.apply(
            lambda row: (
                f"ID: {row.get('chebi_id', '')} | "
                f"Name: {row.get('name', '')} | "
                f"Definition: {row.get('definition', '')} | "
                f"Formula: {row.get('formula', '')} | "
                f"Synonyms: {', '.join(row.get('synonyms', []))}"
            ),
            axis=1,
        )
        return df

    def _preprocess_unichem(self, df: pd.DataFrame) -> pd.DataFrame:
        """Preprocess UniChem data."""
        df["text"] = df.apply(
            lambda row: (
                f"ID: {row.get('unichem_id', '')} | "
                f"Name: {row.get('name', '')} | "
                f"Source: {row.get('source_name', '')}"
            ),
            axis=1,
        )
        return df

    def _preprocess_refmet(self, df: pd.DataFrame) -> pd.DataFrame:
        """Preprocess RefMet data."""
        df["text"] = df.apply(
            lambda row: (
                f"ID: {row.get('refmet_id', '')} | "
                f"Name: {row.get('name', '')} | "
                f"Systematic Name: {row.get('systematic_name', '')} | "
                f"Formula: {row.get('formula', '')} | "
                f"Class: {row.get('main_class', '')}"
            ),
            axis=1,
        )
        return df

    def _initialize_predictor(self) -> None:
        """Initialize the prediction components."""
        from dspy import Predict  # type: ignore

        self.predictor = Predict(MultiProviderSignatureBase)

    def _process_predictor_output(
        self, output: Any, *, query_term: str, latency: float, tokens_used: int
    ) -> Any:
        """Process the output from the predictor.

        Args:
            output: Raw output from predictor
            query_term: The query term being processed
            latency: Processing latency in seconds
            tokens_used: Number of tokens used

        Returns:
            Processed output
        """
        # Process the output and track metrics
        if self.metrics:
            metrics = RAGMetrics(
                retrieval_latency_ms=0.0,  # No retrieval in this case
                generation_latency_ms=latency * 1000,  # Convert to ms
                total_latency_ms=latency * 1000,  # Convert to ms
                tokens_used=tokens_used,
            )
            self.metrics.record_metrics(metrics)
        return output

    def _retrieve_multi_context(
        self, query: str, providers: Optional[List[ProviderType]] = None, k: int = 3
    ) -> Dict[ProviderType, str]:
        """Retrieve context from multiple providers.

        Args:
            query: Search query
            providers: List of providers to query (None for all)
            k: Number of results per provider

        Returns:
            Dictionary of provider contexts
        """
        contexts = {}
        target_providers = providers or list(self.providers.keys())

        for provider in target_providers:
            if provider in self.knowledge_bases:
                kb = self.knowledge_bases[provider]
                mask = kb["text"].str.contains(query, case=False, regex=False)
                results = kb[mask].head(k)
                contexts[provider] = "\n".join(results["text"].tolist())

        return contexts

    def _resolve_cross_references(
        self, matches: List[LLMMatch], providers: List[ProviderType]
    ) -> List[CrossReferenceResult]:
        """Resolve cross-references between matches.

        Args:
            matches: List of matches to resolve
            providers: List of providers to consider

        Returns:
            List of resolved cross-references
        """
        results = []

        for match in matches:
            xrefs = {}
            confidence = match.score

            # Find cross-references in each provider
            for provider in providers:
                if provider in self.knowledge_bases:
                    provider_xrefs = self._find_xrefs(match, provider)
                    if provider_xrefs:
                        xrefs[provider] = provider_xrefs
                        # Adjust confidence based on cross-reference support
                        confidence *= 1.1

            results.append(
                CrossReferenceResult(
                    primary_match=match, xrefs=xrefs, confidence=min(confidence, 1.0)
                )
            )

        return sorted(results, key=lambda x: x.confidence, reverse=True)

    def _find_xrefs(self, match: LLMMatch, provider: ProviderType) -> List[LLMMatch]:
        """Find cross-references for a match in a specific provider.

        Args:
            match: Match to find cross-references for
            provider: Provider to search in

        Returns:
            List of cross-reference matches
        """
        kb = self.knowledge_bases[provider]

        # Verify required columns exist
        required_cols = {"id", "name", "text"}
        missing_cols = required_cols - set(kb.columns)
        if missing_cols:
            return []  # Silently return empty list if columns are missing

        # Try exact ID match first
        id_mask = kb["id"] == match.target_id
        if id_mask.any():
            results = []
            for _, row in kb[id_mask].iterrows():
                results.append(
                    LLMMatch(
                        target_id=str(row["id"]),
                        target_name=str(row["name"]),
                        confidence=MatchConfidence.HIGH,
                        score=0.9,
                        reasoning=f"Exact ID match from {provider}",
                        metadata={"provider": provider.value},
                    )
                )
            return results

        # Fall back to text search if no ID match
        try:
            text_mask = kb["text"].str.contains(
                match.target_name, case=False, regex=False
            )
            if not text_mask.any():
                return []

            results = []
            for _, row in kb[text_mask].iterrows():
                results.append(
                    LLMMatch(
                        target_id=str(row["id"]),
                        target_name=str(row["name"]),
                        confidence=MatchConfidence.MEDIUM,
                        score=0.7,
                        reasoning=f"Text match from {provider}",
                        metadata={"provider": provider.value},
                    )
                )
            return results

        except (AttributeError, KeyError):
            return []  # Handle any pandas errors gracefully

    def _map_term_with_providers(
        self,
        term: str,
        target_providers: Optional[List[ProviderType]] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> LLMMapperResult:
        """Map a term using multiple providers.

        Args:
            term: Term to map
            target_providers: Optional list of target providers
            metadata: Optional metadata

        Returns:
            Mapping result with cross-references
        """
        metadata = metadata or {}
        # Get trace_id from metadata
        trace_id = metadata.get("trace_id")
        initial_result = None

        try:
            # Start tracing with fixed ID for testing
            if trace_id and self.tracker.client:
                langfuse_context.update_current_trace(id=trace_id)

            # Get contexts from all relevant providers
            contexts = self._retrieve_multi_context(term, target_providers)

            # Run prediction
            prediction = self.predictor(
                contexts=contexts,
                query=term,
                target_providers=target_providers,
            )
            latency_ms = prediction.latency if hasattr(prediction, "latency") else 0.0

            # Convert prediction matches to Match objects
            matches = []
            for match in prediction.matches:
                matches.append(
                    Match(
                        id=match.target_id,
                        name=match.target_name,
                        confidence=str(match.score),
                        reasoning=match.reasoning or "",
                        target_name=match.target_name,
                        target_id=match.target_id,
                        metadata=match.metadata or {},
                    )
                )

            # Create initial result
            initial_result = LLMMapperResult(
                query_term=term,
                best_match=matches[0]
                if matches
                else Match(
                    id="",
                    name="",
                    confidence="0.0",
                    reasoning="No match found",
                    target_name="",
                    target_id="",
                ),
                matches=matches,
                trace_id=trace_id,
                metrics={
                    "confidence": float(matches[0].confidence) if matches else 0.0,
                    "latency_ms": latency_ms,
                },
            )

            # Resolve cross-references
            if initial_result and target_providers:
                # Convert Match objects back to LLMMatch for cross-reference resolution
                llm_matches: List[LLMMatch] = []
                for match in initial_result.matches:
                    if match.target_id and match.target_name:
                        llm_matches.append(
                            LLMMatch(
                                target_id=match.target_id,
                                target_name=match.target_name,
                                confidence=MatchConfidence.HIGH
                                if float(match.confidence) > 0.8
                                else MatchConfidence.LOW,
                                score=float(match.confidence),
                                reasoning=match.reasoning or "",
                                metadata={
                                    k: str(v) for k, v in (match.metadata or {}).items()
                                },
                            )
                        )

                if (
                    llm_matches
                ):  # Only resolve cross-references if we have valid matches
                    xrefs = self._resolve_cross_references(
                        llm_matches,
                        target_providers,
                    )

                    if xrefs:
                        # Convert CrossReferenceResult to Match objects
                        xref_matches = []
                        for xref in xrefs:
                            for provider_matches in xref.xrefs.values():
                                for match in provider_matches:
                                    if match.target_id and match.target_name:
                                        xref_matches.append(
                                            Match(
                                                id=match.target_id,
                                                name=match.target_name,
                                                confidence=str(match.score),
                                                reasoning=match.reasoning or "",
                                                target_name=match.target_name,
                                                target_id=match.target_id,
                                                metadata={
                                                    k: str(v)
                                                    for k, v in (
                                                        match.metadata or {}
                                                    ).items()
                                                },
                                            )
                                        )
                        initial_result.matches = (
                            xref_matches  # Replace matches instead of extending
                        )

            return initial_result
        except Exception as e:
            if trace_id and self.tracker.client:
                self.tracker.record_error(trace_id, str(e))
            raise

    def map_term(
        self,
        term: str,
        target_ontology: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> LLMMapperResult:
        """Map a term using the specified target ontology.

        Args:
            term: Term to map
            target_ontology: Optional target ontology
            metadata: Optional metadata

        Returns:
            Mapping result
        """
        # Convert target_ontology to target_providers
        target_providers = None
        if target_ontology:
            try:
                provider_type = ProviderType(target_ontology)
                target_providers = [provider_type]
            except ValueError:
                # If target_ontology is not a valid ProviderType, pass it through
                pass

        return self._map_term_with_providers(term, target_providers, metadata)
