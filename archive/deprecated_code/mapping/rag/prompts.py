import json
from pathlib import Path
from typing import Dict, Optional, List, Any

from biomapper.schemas.rag_schema import PromptTemplate


class PromptManager:
    """Manages RAG prompts with optional Langfuse integration."""

    DEFAULT_PROMPTS = Path(__file__).parent / "data" / "default_prompts.json"

    def __init__(self) -> None:
        self.prompts: Dict[str, PromptTemplate] = {}
        self._load_default_prompts()

    def _load_default_prompts(self) -> None:
        """Load default prompts from JSON file."""
        if not self.DEFAULT_PROMPTS.exists():
            return

        with open(self.DEFAULT_PROMPTS) as f:
            prompts_data = json.load(f)

        for name, data in prompts_data.items():
            self.prompts[name] = PromptTemplate(
                name=name,
                template=data["template"],
                version=data["version"],
                metrics=data.get("metrics"),
            )

    def get_prompt(self, name: str) -> Optional[PromptTemplate]:
        """Get a prompt template by name."""
        return self.prompts.get(name)

    def add_prompt(self, prompt: PromptTemplate) -> None:
        """Add a new prompt template."""
        self.prompts[prompt.name] = prompt

    def update_metrics(self, name: str, metrics: Dict[str, float]) -> None:
        """Update metrics for a prompt template."""
        if prompt := self.prompts.get(name):
            prompt.metrics = metrics

    def format_mapping_prompt(
        self, query: str, relevant_compounds: List[Dict[str, Any]]
    ) -> str:
        """Format mapping prompt with query and relevant compounds.

        Args:
            query: The query being mapped
            relevant_compounds: List of relevant compound information

        Returns:
            str: The formatted prompt
        """
        base_prompt = (
            "Given a query about chemical compounds and a list of relevant compounds, "
            "generate a comprehensive response that addresses the query using the provided information."
        )

        prompt = f"{base_prompt}\n\nQuery: {query}\n\nRelevant Compounds:\n"

        # Format context from relevant compounds
        context = "\n".join(
            f"- {doc.get('content', '')} (ID: {doc.get('metadata', {}).get('id', 'unknown')})"
            for doc in relevant_compounds
        )

        return f"{prompt}{context}\n\nResponse:"
