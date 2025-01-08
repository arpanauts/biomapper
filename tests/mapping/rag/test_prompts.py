"""Tests for the PromptManager."""
from biomapper.schemas.rag_schema import PromptTemplate
from typing import Dict, Any


def test_load_default_prompts(
    prompt_manager: Any, sample_prompts: Dict[str, Any]
) -> None:
    """Test loading default prompts."""
    assert "test_prompt" in prompt_manager.prompts
    prompt = prompt_manager.prompts["test_prompt"]
    assert prompt.template == sample_prompts["test_prompt"]["template"]
    assert prompt.version == sample_prompts["test_prompt"]["version"]


def test_get_prompt(prompt_manager: Any) -> None:
    """Test getting a prompt by name."""
    prompt = prompt_manager.get_prompt("test_prompt")
    assert prompt is not None
    assert isinstance(prompt, PromptTemplate)
    assert prompt.name == "test_prompt"


def test_get_nonexistent_prompt(prompt_manager: Any) -> None:
    """Test getting a nonexistent prompt returns None."""
    prompt = prompt_manager.get_prompt("nonexistent")
    assert prompt is None


def test_add_prompt(prompt_manager: Any) -> None:
    """Test adding a new prompt."""
    new_prompt = PromptTemplate(
        name="new_prompt", template="New template", version="1.0"
    )
    prompt_manager.add_prompt(new_prompt)

    retrieved = prompt_manager.get_prompt("new_prompt")
    assert retrieved is not None
    assert retrieved.template == "New template"


def test_update_metrics(prompt_manager: Any) -> None:
    """Test updating prompt metrics."""
    metrics = {"accuracy": 0.95, "latency": 100}
    prompt_manager.update_metrics("test_prompt", metrics)

    prompt = prompt_manager.get_prompt("test_prompt")
    assert prompt.metrics == metrics
