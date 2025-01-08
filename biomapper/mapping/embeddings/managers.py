"""Embedding model management for compound mapping."""
from abc import ABC, abstractmethod
from typing import List, Optional, cast
import torch
from transformers import AutoModel, AutoTokenizer  # type: ignore


class EmbeddingManager(ABC):
    """Abstract base class for embedding managers."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings."""
        pass


class HuggingFaceEmbeddingManager(EmbeddingManager):
    """Manages embeddings using HuggingFace models."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-mpnet-base-v2",
        device: Optional[str] = None,
    ):
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(self.device)
        self.model.eval()

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string."""
        # Tokenize input
        inputs = self.tokenizer(
            text, return_tensors="pt", padding=True, truncation=True, max_length=512
        )

        # Move tensors to device
        device_inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**device_inputs)
            # Use CLS token embedding
            embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()

        return cast(List[float], embedding[0].tolist())

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings."""
        # Tokenize inputs and get dictionary of tensors
        inputs = self.tokenizer(
            texts, return_tensors="pt", padding=True, truncation=True, max_length=512
        )

        # Convert inputs to device if it's not already a dictionary
        if not isinstance(inputs, dict):
            inputs = dict(inputs)
        device_inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**device_inputs)
            # Use CLS token embeddings for each text in batch
            embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()

        return cast(List[List[float]], embeddings.tolist())


class OpenAIEmbeddingManager(EmbeddingManager):
    """Manages embeddings using OpenAI's API."""

    def __init__(
        self, api_key: Optional[str] = None, model: str = "text-embedding-ada-002"
    ):
        try:
            import openai
        except ImportError:
            raise ImportError(
                "OpenAI package not found. Install with 'pip install openai'"
            )

        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string."""
        response = self.client.embeddings.create(model=self.model, input=text)
        return response.data[0].embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings."""
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [data.embedding for data in response.data]
