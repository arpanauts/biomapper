"""LLM provider abstraction for biomapper analysis generation."""

import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LLMUsageMetrics(BaseModel):
    """Metrics for LLM usage tracking."""
    
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_estimate: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: Optional[str] = None


class LLMResponse(BaseModel):
    """Standardized LLM response format."""
    
    content: str
    usage: LLMUsageMetrics
    success: bool = True
    error_message: Optional[str] = None
    provider_response: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "", timeout: float = 60.0):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def generate_analysis(self, prompt: str, data: Dict[str, Any]) -> LLMResponse:
        """Generate analysis from prompt and data."""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name."""
        pass
    
    def _format_data_for_prompt(self, data: Dict[str, Any]) -> str:
        """Format data dictionary for inclusion in prompt."""
        try:
            return json.dumps(data, indent=2, default=str)
        except Exception as e:
            self.logger.warning(f"Error formatting data: {e}")
            return str(data)


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4", timeout: float = 60.0):
        super().__init__(api_key or os.getenv("OPENAI_API_KEY"), model, timeout)
        self.base_url = "https://api.openai.com/v1"
    
    def get_provider_name(self) -> str:
        return "openai"
    
    async def generate_analysis(self, prompt: str, data: Dict[str, Any]) -> LLMResponse:
        """Generate analysis using OpenAI API."""
        if not self.api_key:
            return LLMResponse(
                content="",
                usage=LLMUsageMetrics(provider="openai", model=self.model),
                success=False,
                error_message="OpenAI API key not provided"
            )
        
        formatted_data = self._format_data_for_prompt(data)
        full_prompt = f"{prompt}\n\nData:\n{formatted_data}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a biomapper results analyst specializing in biological identifier mapping strategies."
                },
                {
                    "role": "user", 
                    "content": full_prompt
                }
            ],
            "temperature": 0.1,  # Low temperature for consistent analysis
            "max_tokens": 4000
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                
                return LLMResponse(
                    content=result["choices"][0]["message"]["content"],
                    usage=LLMUsageMetrics(
                        provider="openai",
                        model=self.model,
                        prompt_tokens=result.get("usage", {}).get("prompt_tokens", 0),
                        completion_tokens=result.get("usage", {}).get("completion_tokens", 0),
                        total_tokens=result.get("usage", {}).get("total_tokens", 0),
                        request_id=result.get("id")
                    ),
                    provider_response=result
                )
                
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            return LLMResponse(
                content="",
                usage=LLMUsageMetrics(provider="openai", model=self.model),
                success=False,
                error_message=str(e)
            )


class AnthropicProvider(LLMProvider):
    """Anthropic provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022", timeout: float = 60.0):
        super().__init__(api_key or os.getenv("ANTHROPIC_API_KEY"), model, timeout)
        self.base_url = "https://api.anthropic.com/v1"
    
    def get_provider_name(self) -> str:
        return "anthropic"
    
    async def generate_analysis(self, prompt: str, data: Dict[str, Any]) -> LLMResponse:
        """Generate analysis using Anthropic API."""
        if not self.api_key:
            return LLMResponse(
                content="",
                usage=LLMUsageMetrics(provider="anthropic", model=self.model),
                success=False,
                error_message="Anthropic API key not provided"
            )
        
        formatted_data = self._format_data_for_prompt(data)
        full_prompt = f"{prompt}\n\nData:\n{formatted_data}"
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": 4000,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": full_prompt
                }
            ]
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                
                return LLMResponse(
                    content=result["content"][0]["text"],
                    usage=LLMUsageMetrics(
                        provider="anthropic",
                        model=self.model,
                        prompt_tokens=result.get("usage", {}).get("input_tokens", 0),
                        completion_tokens=result.get("usage", {}).get("output_tokens", 0),
                        total_tokens=(
                            result.get("usage", {}).get("input_tokens", 0) + 
                            result.get("usage", {}).get("output_tokens", 0)
                        ),
                        request_id=result.get("id")
                    ),
                    provider_response=result
                )
                
        except Exception as e:
            self.logger.error(f"Anthropic API error: {e}")
            return LLMResponse(
                content="",
                usage=LLMUsageMetrics(provider="anthropic", model=self.model),
                success=False,
                error_message=str(e)
            )


class GeminiProvider(LLMProvider):
    """Google Gemini provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash", timeout: float = 60.0):
        super().__init__(api_key or os.getenv("GEMINI_API_KEY"), model, timeout)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    def get_provider_name(self) -> str:
        return "gemini"
    
    async def generate_analysis(self, prompt: str, data: Dict[str, Any]) -> LLMResponse:
        """Generate analysis using Gemini API."""
        if not self.api_key:
            return LLMResponse(
                content="",
                usage=LLMUsageMetrics(provider="gemini", model=self.model),
                success=False,
                error_message="Gemini API key not provided"
            )
        
        formatted_data = self._format_data_for_prompt(data)
        full_prompt = f"{prompt}\n\nData:\n{formatted_data}"
        
        # Use generation endpoint for Gemini
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": full_prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 4000,
                "topP": 0.8,
                "topK": 10
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                # Extract content from Gemini response format
                content = ""
                if "candidates" in result and result["candidates"]:
                    candidate = result["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        content = candidate["content"]["parts"][0].get("text", "")
                
                # Extract usage metadata if available
                usage_metadata = result.get("usageMetadata", {})
                
                return LLMResponse(
                    content=content,
                    usage=LLMUsageMetrics(
                        provider="gemini",
                        model=self.model,
                        prompt_tokens=usage_metadata.get("promptTokenCount", 0),
                        completion_tokens=usage_metadata.get("candidatesTokenCount", 0),
                        total_tokens=usage_metadata.get("totalTokenCount", 0)
                    ),
                    provider_response=result
                )
                
        except Exception as e:
            self.logger.error(f"Gemini API error: {e}")
            return LLMResponse(
                content="",
                usage=LLMUsageMetrics(provider="gemini", model=self.model),
                success=False,
                error_message=str(e)
            )


class LLMProviderFactory:
    """Factory for creating LLM providers."""
    
    _providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider, 
        "gemini": GeminiProvider
    }
    
    @classmethod
    def create_provider(
        self, 
        provider: str, 
        api_key: Optional[str] = None, 
        model: Optional[str] = None,
        timeout: float = 60.0
    ) -> LLMProvider:
        """Create an LLM provider instance."""
        if provider not in self._providers:
            raise ValueError(f"Unknown provider: {provider}. Available: {list(self._providers.keys())}")
        
        provider_class = self._providers[provider]
        
        # Use provider-specific default models if not specified
        if model is None:
            if provider == "openai":
                model = "gpt-4"
            elif provider == "anthropic":
                model = "claude-3-5-sonnet-20241022"
            elif provider == "gemini":
                model = "gemini-1.5-flash"
        
        return provider_class(api_key=api_key, model=model, timeout=timeout)
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available provider names."""
        return list(cls._providers.keys())


class LLMProviderManager:
    """Manager for handling multiple LLM providers with fallbacks."""
    
    def __init__(self, providers: List[Dict[str, Any]]):
        """Initialize with list of provider configurations."""
        self.providers = []
        for config in providers:
            try:
                provider = LLMProviderFactory.create_provider(**config)
                self.providers.append(provider)
            except Exception as e:
                logger.warning(f"Failed to initialize provider {config}: {e}")
    
    async def generate_analysis_with_fallback(
        self, 
        prompt: str, 
        data: Dict[str, Any]
    ) -> LLMResponse:
        """Generate analysis with automatic fallback to other providers."""
        last_error = None
        
        for provider in self.providers:
            try:
                response = await provider.generate_analysis(prompt, data)
                if response.success:
                    logger.info(f"Successfully generated analysis using {provider.get_provider_name()}")
                    return response
                else:
                    last_error = response.error_message
                    logger.warning(f"Provider {provider.get_provider_name()} failed: {last_error}")
            except Exception as e:
                last_error = str(e)
                logger.error(f"Error with provider {provider.get_provider_name()}: {e}")
        
        # All providers failed
        return LLMResponse(
            content="",
            usage=LLMUsageMetrics(provider="fallback", model="none"),
            success=False,
            error_message=f"All providers failed. Last error: {last_error}"
        )