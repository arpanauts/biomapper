"""Multi-provider RAG implementation for biomapper."""

from typing import Dict, List, Optional, Any

import pandas as pd
from pydantic import BaseModel

from .rag_mapper import RAGMapper
from ..schemas.llm_schema import LLMMatch, LLMMapperResult, MatchConfidence
from ..schemas.provider_schemas import (
    ProviderType,
    ProviderConfig,
)


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


class MultiProviderMapper(RAGMapper):
    """Multi-provider RAG mapper with cross-reference resolution."""

    def __init__(
        self,
        providers: Dict[ProviderType, ProviderConfig],
        model: str = "gpt-4",
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ):
        """Initialize multi-provider mapper.

        Args:
            providers: Dictionary of provider configurations
            model: OpenAI model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens per request
        """
        # Get first available data path to use as compounds path
        compounds_path = next(
            (config.data_path for config in providers.values() if config.data_path),
            None,
        )
        if not compounds_path:
            raise ValueError("At least one provider must have a valid data_path")

        # Initialize base with first provider's data path
        super().__init__(
            compounds_path=compounds_path,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        self.providers = providers
        self.knowledge_bases: Dict[ProviderType, pd.DataFrame] = {}

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

        # Initialize DSPy predictor with multi-provider signature
        self.predictor = self._initialize_predictor()

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
        # This is a simplified implementation
        # In practice, you'd want to use the xrefs field and proper ID matching
        kb = self.knowledge_bases[provider]
        mask = kb["text"].str.contains(match.target_name, case=False, regex=False)
        results = []

        for _, row in kb[mask].iterrows():
            results.append(
                LLMMatch(
                    target_id=row.get("id", ""),
                    target_name=row.get("name", ""),
                    confidence=MatchConfidence.MEDIUM,
                    score=0.7,
                    reasoning=f"Cross-reference match from {provider}",
                    metadata={"provider": provider.value},
                )
            )

        return results

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
        # Start tracing with fixed ID for testing
        trace = self.langfuse.trace(
            name=f"multi_provider_map_term_{term}", id=metadata.get("trace_id")
        )
        initial_result = None

        try:
            # Get contexts from all relevant providers
            contexts = self._retrieve_multi_context(term, target_providers)

            # Run prediction
            prediction = self.predictor(
                contexts=contexts,
                query=term,
                target_providers=target_providers or list(self.providers.keys()),
            )

            # Process initial matches
            initial_result = self._process_predictor_output(
                output=prediction.matches,
                query_term=term,
                latency=prediction.latency,
                tokens_used=prediction.tokens_used,
            )

            # Set trace ID in result
            initial_result.trace_id = trace.id

            # Resolve cross-references
            xref_results = self._resolve_cross_references(
                initial_result.matches, target_providers or list(self.providers.keys())
            )

            # Update matches with cross-reference information
            if xref_results:
                best_result = xref_results[0]
                initial_result.matches = [best_result.primary_match]
                initial_result.best_match = best_result.primary_match

                # Add cross-reference matches
                for provider_matches in best_result.xrefs.values():
                    initial_result.matches.extend(provider_matches)

            # Update trace status to completed
            trace.update(status="completed")

            return initial_result
        except Exception as e:
            # Update trace status to failed on error and re-raise
            trace.update(status="failed", error=str(e))
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
