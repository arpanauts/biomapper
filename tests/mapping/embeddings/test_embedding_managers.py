"""Tests for embedding managers."""
import pytest
import torch
from unittest.mock import Mock, patch
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    pass

from biomapper.mapping.embeddings.managers import (
    HuggingFaceEmbeddingManager,
    OpenAIEmbeddingManager,
)


@pytest.fixture
def mock_tokenizer() -> Mock:
    """Mock HuggingFace tokenizer that returns a dictionary of PyTorch tensors."""
    tokenizer = Mock()

    # Create a real dictionary of tensors for both return_value and __call__
    tensor_dict: Dict[str, torch.Tensor] = {
        "input_ids": torch.zeros((2, 10), dtype=torch.long),
        "attention_mask": torch.ones((2, 10), dtype=torch.long),
    }

    # Ensure both direct calls and __call__ return the dictionary
    tokenizer.return_value = tensor_dict
    tokenizer.__call__ = Mock(return_value=tensor_dict)  # type: ignore[method-assign]

    return tokenizer


@pytest.fixture
def mock_model() -> Mock:
    """Mock HuggingFace model returning a dummy hidden state."""
    model = Mock()
    # Return hidden state with batch size of 2 for batch test
    model.return_value = Mock(
        last_hidden_state=torch.zeros((2, 10, 768), dtype=torch.float)
    )
    model.to = Mock(return_value=model)
    return model


def test_huggingface_embed_text(mock_tokenizer: Mock, mock_model: Mock) -> None:
    """Test HuggingFace text embedding."""
    with patch(
        "transformers.AutoTokenizer.from_pretrained", return_value=mock_tokenizer
    ), patch("transformers.AutoModel.from_pretrained", return_value=mock_model):
        manager = HuggingFaceEmbeddingManager()
        embedding = manager.embed_text("test text")

        assert isinstance(embedding, list)
        assert len(embedding) == 768


def test_huggingface_embed_batch(mock_tokenizer: Mock, mock_model: Mock) -> None:
    """Test HuggingFace batch embedding."""
    with patch(
        "transformers.AutoTokenizer.from_pretrained", return_value=mock_tokenizer
    ), patch("transformers.AutoModel.from_pretrained", return_value=mock_model):
        manager = HuggingFaceEmbeddingManager()
        embeddings = manager.embed_batch(["text 1", "text 2"])

        assert isinstance(embeddings, list)
        assert len(embeddings) == 2
        assert len(embeddings[0]) == 768


def test_openai_embed_text() -> None:
    """Test OpenAI text embedding."""
    mock_client = Mock()
    mock_client.embeddings.create.return_value.data = [Mock(embedding=[0.1] * 1536)]

    with patch("openai.OpenAI", return_value=mock_client):
        manager = OpenAIEmbeddingManager(api_key="test")
        embedding = manager.embed_text("test text")

        assert isinstance(embedding, list)
        assert len(embedding) == 1536


def test_openai_embed_batch() -> None:
    """Test OpenAI batch embedding."""
    mock_client = Mock()
    mock_client.embeddings.create.return_value.data = [
        Mock(embedding=[0.1] * 1536),
        Mock(embedding=[0.2] * 1536),
    ]

    with patch("openai.OpenAI", return_value=mock_client):
        manager = OpenAIEmbeddingManager(api_key="test")
        embeddings = manager.embed_batch(["text 1", "text 2"])

        assert isinstance(embeddings, list)
        assert len(embeddings) == 2
        assert len(embeddings[0]) == 1536


def test_openai_no_api_key() -> None:
    """Test OpenAI manager without API key."""
    with patch("openai.OpenAI") as mock_openai:
        OpenAIEmbeddingManager()
        mock_openai.assert_called_with(api_key=None)
