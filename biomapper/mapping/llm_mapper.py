"""Base LLM integration for biomapper."""

from typing import Dict, List, Optional, TYPE_CHECKING

import time
import os

from langfuse import Langfuse
from openai import OpenAI

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam

from ..schemas.llm_schema import (
    LLMMatch,
    LLMMapperResult,
    LLMMapperMetrics,
    MatchConfidence,
)


class LLMMapper:
    """Base class for LLM-based ontology mapping."""

    def __init__(
        self,
        model: str = "gpt-4",
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ):
        """Initialize the LLM mapper."""
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Initialize OpenAI client
        self.client = OpenAI()

        # Initialize Langfuse
        self.langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )

    def _create_system_prompt(self) -> str:
        """Create the system prompt for ontology mapping."""
        return (
            "You are an expert at mapping chemical and biological terms to ontologies. "
            "Your task is to find the most appropriate ontology term for a given input. "
            "Consider synonyms, related terms, and the hierarchical structure of the ontology."
        )

    def _estimate_cost(self, tokens_used: int) -> float:
        """Estimate the cost of the API call in USD."""
        # GPT-4 pricing (as of 2023)
        return tokens_used * 0.00003  # $0.03 per 1000 tokens

    def map_term(
        self,
        term: str,
        target_ontology: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> LLMMapperResult:
        """Map a single term using the LLM.

        Args:
            term: Input term to map
            target_ontology: Optional target ontology identifier
            metadata: Optional metadata to include

        Returns:
            LLMMapperResult containing matches and metrics
        """
        start_time = time.time()

        # Create messages
        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": self._create_system_prompt()},
            {"role": "user", "content": f"Map the following term: {term}"},
        ]

        if target_ontology:
            messages.append(
                {"role": "user", "content": f"Target ontology: {target_ontology}"}
            )

        # Make API call
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        # Calculate metrics
        end_time = time.time()
        latency = (end_time - start_time) * 1000  # Convert to ms
        tokens_used = response.usage.total_tokens if response.usage else 0

        # Process response into matches
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise ValueError("No content in LLM response")

        matches = [
            LLMMatch(
                target_id="example_id",
                target_name=content,
                confidence=MatchConfidence.MEDIUM,
                score=0.8,
                reasoning="Based on LLM response",
                metadata=metadata or {},
            )
        ]

        # Create result
        return LLMMapperResult(
            query_term=term,
            matches=matches,
            best_match=matches[0] if matches else None,
            metrics=LLMMapperMetrics(
                latency_ms=latency,
                tokens_used=tokens_used,
                provider="openai",
                model=self.model,
                cost=self._estimate_cost(tokens_used),
            ),
            trace_id=self.langfuse.trace(name="llm_mapping").id,
        )
