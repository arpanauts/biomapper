"""Tests for LLM provider interfaces and API integration."""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any
from datetime import datetime

from actions.utils.llm_providers import (
    LLMProvider,
    OpenAIProvider,
    AnthropicProvider,
    GeminiProvider,
    LLMProviderFactory,
    LLMProviderManager,
    LLMResponse,
    LLMUsageMetrics
)


class TestLLMResponse:
    """Test LLM response data models."""
    
    def test_llm_usage_metrics_creation(self):
        """Test LLMUsageMetrics model creation and validation."""
        
        metrics = LLMUsageMetrics(
            provider="openai",
            model="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_estimate=0.002,
            request_id="req_123"
        )
        
        assert metrics.provider == "openai"
        assert metrics.model == "gpt-4"
        assert metrics.prompt_tokens == 100
        assert metrics.completion_tokens == 50
        assert metrics.total_tokens == 150
        assert metrics.cost_estimate == 0.002
        assert metrics.request_id == "req_123"
        assert isinstance(metrics.timestamp, datetime)
    
    def test_llm_response_creation(self):
        """Test LLMResponse model creation and validation."""
        
        usage = LLMUsageMetrics(
            provider="anthropic",
            model="claude-3-5-sonnet",
            prompt_tokens=200,
            completion_tokens=150
        )
        
        response = LLMResponse(
            content="This is a test response about protein mapping.",
            usage=usage,
            success=True,
            provider_response={"id": "msg_123", "type": "message"}
        )
        
        assert response.content == "This is a test response about protein mapping."
        assert response.usage.provider == "anthropic"
        assert response.success is True
        assert response.error_message is None
        assert response.provider_response["id"] == "msg_123"
    
    def test_llm_response_error_handling(self):
        """Test LLMResponse with error conditions."""
        
        usage = LLMUsageMetrics(provider="gemini", model="gemini-1.5-flash")
        
        error_response = LLMResponse(
            content="",
            usage=usage,
            success=False,
            error_message="API rate limit exceeded"
        )
        
        assert error_response.content == ""
        assert error_response.success is False
        assert error_response.error_message == "API rate limit exceeded"


class TestLLMProviderBase:
    """Test base LLM provider functionality."""
    
    def test_llm_provider_is_abstract(self):
        """Test that LLMProvider cannot be instantiated directly."""
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            LLMProvider()
    
    def test_llm_provider_subclass_requirements(self):
        """Test that subclasses must implement required methods."""
        
        class IncompleteProvider(LLMProvider):
            def get_provider_name(self) -> str:
                return "incomplete"
            # Missing generate_analysis method
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteProvider()
    
    def test_format_data_for_prompt(self):
        """Test data formatting for prompt inclusion."""
        
        class TestProvider(LLMProvider):
            async def generate_analysis(self, prompt: str, data: Dict[str, Any]) -> LLMResponse:
                return LLMResponse(content="test", usage=LLMUsageMetrics(provider="test", model="test"))
            
            def get_provider_name(self) -> str:
                return "test"
        
        provider = TestProvider()
        
        # Test normal data formatting
        test_data = {
            "protein_ids": ["P12345", "Q9Y6R4"],
            "statistics": {"total": 2, "matched": 1},
            "metadata": {"source": "test"}
        }
        
        formatted = provider._format_data_for_prompt(test_data)
        
        assert "P12345" in formatted
        assert "Q9Y6R4" in formatted
        assert "statistics" in formatted
        assert "metadata" in formatted
        
        # Test with problematic data
        problematic_data = {
            "datetime": datetime.now(),
            "complex_object": object()
        }
        
        # Should not raise exception
        formatted_problematic = provider._format_data_for_prompt(problematic_data)
        assert isinstance(formatted_problematic, str)


@pytest.mark.asyncio
class TestOpenAIProvider:
    """Test OpenAI provider implementation."""
    
    def test_openai_provider_initialization(self):
        """Test OpenAI provider initialization."""
        
        # Test with explicit API key
        provider = OpenAIProvider(api_key="test_key", model="gpt-4-turbo", timeout=30.0)
        assert provider.api_key == "test_key"
        assert provider.model == "gpt-4-turbo"
        assert provider.timeout == 30.0
        assert provider.get_provider_name() == "openai"
    
    def test_openai_provider_environment_key(self):
        """Test OpenAI provider with environment variable."""
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'env_key'}):
            provider = OpenAIProvider()
            assert provider.api_key == "env_key"
    
    async def test_openai_generate_analysis_success(self):
        """Test successful OpenAI analysis generation."""
        
        provider = OpenAIProvider(api_key="test_key")
        
        # Mock successful API response
        mock_response_data = {
            "choices": [{"message": {"content": "Analysis of protein mapping results..."}}],
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 300,
                "total_tokens": 450
            },
            "id": "chatcmpl-123"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await provider.generate_analysis(
                "Analyze protein mapping data",
                {"proteins": ["P12345", "Q9Y6R4"], "match_rate": 0.85}
            )
            
            assert result.success is True
            assert "protein mapping results" in result.content.lower()
            assert result.usage.provider == "openai"
            assert result.usage.prompt_tokens == 150
            assert result.usage.completion_tokens == 300
            assert result.usage.total_tokens == 450
            assert result.usage.request_id == "chatcmpl-123"
    
    async def test_openai_generate_analysis_no_api_key(self):
        """Test OpenAI provider without API key."""
        
        # Ensure no API key from environment variable
        with patch.dict(os.environ, {}, clear=True):
            provider = OpenAIProvider(api_key=None)
            
            result = await provider.generate_analysis(
                "Test prompt",
                {"test": "data"}
            )
            
            assert result.success is False
            assert "API key not provided" in result.error_message
            assert result.content == ""
    
    async def test_openai_generate_analysis_api_error(self):
        """Test OpenAI provider with API error."""
        
        provider = OpenAIProvider(api_key="test_key")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("API connection failed")
            )
            
            result = await provider.generate_analysis(
                "Test prompt",
                {"test": "data"}
            )
            
            assert result.success is False
            assert "API connection failed" in result.error_message
            assert result.content == ""
    
    async def test_openai_prompt_construction(self):
        """Test proper prompt construction for OpenAI."""
        
        provider = OpenAIProvider(api_key="test_key")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Test response"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
            }
            mock_response.raise_for_status.return_value = None
            
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            await provider.generate_analysis(
                "Analyze biomapper results",
                {"strategy": "protein_mapping", "results": [{"id": "P12345"}]}
            )
            
            # Verify API call structure
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            
            assert call_args[1]["json"]["model"] == "gpt-4"
            assert call_args[1]["json"]["temperature"] == 0.1
            assert call_args[1]["json"]["max_tokens"] == 4000
            
            messages = call_args[1]["json"]["messages"]
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert "biomapper results analyst" in messages[0]["content"].lower()
            assert messages[1]["role"] == "user"
            assert "Analyze biomapper results" in messages[1]["content"]


@pytest.mark.asyncio
class TestAnthropicProvider:
    """Test Anthropic provider implementation."""
    
    def test_anthropic_provider_initialization(self):
        """Test Anthropic provider initialization."""
        
        provider = AnthropicProvider(api_key="test_key", model="claude-3-5-sonnet-20241022")
        assert provider.api_key == "test_key"
        assert provider.model == "claude-3-5-sonnet-20241022"
        assert provider.get_provider_name() == "anthropic"
    
    async def test_anthropic_generate_analysis_success(self):
        """Test successful Anthropic analysis generation."""
        
        provider = AnthropicProvider(api_key="test_key")
        
        mock_response_data = {
            "content": [{"text": "Comprehensive analysis of biological mapping strategy..."}],
            "usage": {
                "input_tokens": 200,
                "output_tokens": 400
            },
            "id": "msg_123"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await provider.generate_analysis(
                "Analyze metabolite mapping results",
                {"metabolites": ["HMDB0000001", "HMDB0000002"], "confidence": [0.9, 0.8]}
            )
            
            assert result.success is True
            assert "biological mapping strategy" in result.content.lower()
            assert result.usage.provider == "anthropic"
            assert result.usage.prompt_tokens == 200
            assert result.usage.completion_tokens == 400
            assert result.usage.total_tokens == 600  # Should sum input + output tokens
    
    async def test_anthropic_api_structure(self):
        """Test Anthropic API call structure."""
        
        provider = AnthropicProvider(api_key="test_key")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "content": [{"text": "Test response"}],
                "usage": {"input_tokens": 10, "output_tokens": 5}
            }
            mock_response.raise_for_status.return_value = None
            
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            await provider.generate_analysis(
                "Test prompt",
                {"test": "data"}
            )
            
            # Verify API call structure
            call_args = mock_post.call_args
            
            # Check headers
            headers = call_args[1]["headers"]
            assert "x-api-key" in headers
            assert headers["x-api-key"] == "test_key"
            assert headers["anthropic-version"] == "2023-06-01"
            
            # Check payload
            payload = call_args[1]["json"]
            assert payload["max_tokens"] == 4000
            assert payload["temperature"] == 0.1
            assert len(payload["messages"]) == 1
            assert payload["messages"][0]["role"] == "user"


@pytest.mark.asyncio
class TestGeminiProvider:
    """Test Google Gemini provider implementation."""
    
    def test_gemini_provider_initialization(self):
        """Test Gemini provider initialization."""
        
        provider = GeminiProvider(api_key="test_key", model="gemini-1.5-flash")
        assert provider.api_key == "test_key"
        assert provider.model == "gemini-1.5-flash"
        assert provider.get_provider_name() == "gemini"
    
    async def test_gemini_generate_analysis_success(self):
        """Test successful Gemini analysis generation."""
        
        provider = GeminiProvider(api_key="test_key")
        
        mock_response_data = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Detailed analysis of chemical mapping procedures..."}]
                }
            }],
            "usageMetadata": {
                "promptTokenCount": 120,
                "candidatesTokenCount": 280,
                "totalTokenCount": 400
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await provider.generate_analysis(
                "Analyze chemical test mapping",
                {"tests": ["glucose", "cholesterol"], "loinc_codes": ["2345-7", "2093-3"]}
            )
            
            assert result.success is True
            assert "chemical mapping procedures" in result.content.lower()
            assert result.usage.provider == "gemini"
            assert result.usage.prompt_tokens == 120
            assert result.usage.completion_tokens == 280
            assert result.usage.total_tokens == 400
    
    async def test_gemini_api_structure(self):
        """Test Gemini API call structure."""
        
        provider = GeminiProvider(api_key="test_key", model="gemini-1.5-flash")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "candidates": [{"content": {"parts": [{"text": "Test response"}]}}],
                "usageMetadata": {"totalTokenCount": 15}
            }
            mock_response.raise_for_status.return_value = None
            
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            await provider.generate_analysis("Test", {"data": "test"})
            
            # Verify URL construction
            call_args = mock_post.call_args
            url = call_args[0][0]  # First positional argument is URL
            assert "models/gemini-1.5-flash:generateContent" in url
            assert "key=test_key" in url
            
            # Verify payload structure
            payload = call_args[1]["json"]
            assert "contents" in payload
            assert len(payload["contents"]) == 1
            assert "parts" in payload["contents"][0]
            assert payload["generationConfig"]["temperature"] == 0.1
            assert payload["generationConfig"]["maxOutputTokens"] == 4000
    
    async def test_gemini_malformed_response_handling(self):
        """Test Gemini provider handling of malformed responses."""
        
        provider = GeminiProvider(api_key="test_key")
        
        # Test response missing expected structure
        malformed_response_data = {
            "candidates": [],  # Empty candidates
            "usageMetadata": {}
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = malformed_response_data
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await provider.generate_analysis("Test", {"data": "test"})
            
            assert result.success is True  # Should not fail
            assert result.content == ""    # But content should be empty


class TestLLMProviderFactory:
    """Test LLM provider factory functionality."""
    
    def test_create_openai_provider(self):
        """Test creating OpenAI provider via factory."""
        
        provider = LLMProviderFactory.create_provider(
            "openai",
            api_key="test_key",
            model="gpt-4-turbo"
        )
        
        assert isinstance(provider, OpenAIProvider)
        assert provider.api_key == "test_key"
        assert provider.model == "gpt-4-turbo"
    
    def test_create_anthropic_provider(self):
        """Test creating Anthropic provider via factory."""
        
        provider = LLMProviderFactory.create_provider(
            "anthropic",
            api_key="test_key",
            model="claude-3-5-sonnet-20241022"
        )
        
        assert isinstance(provider, AnthropicProvider)
        assert provider.api_key == "test_key"
        assert provider.model == "claude-3-5-sonnet-20241022"
    
    def test_create_gemini_provider(self):
        """Test creating Gemini provider via factory."""
        
        provider = LLMProviderFactory.create_provider(
            "gemini",
            api_key="test_key",
            model="gemini-1.5-flash"
        )
        
        assert isinstance(provider, GeminiProvider)
        assert provider.api_key == "test_key"
        assert provider.model == "gemini-1.5-flash"
    
    def test_create_provider_with_defaults(self):
        """Test creating providers with default models."""
        
        # Test OpenAI defaults
        openai_provider = LLMProviderFactory.create_provider("openai", api_key="test")
        assert openai_provider.model == "gpt-4"
        
        # Test Anthropic defaults
        anthropic_provider = LLMProviderFactory.create_provider("anthropic", api_key="test")
        assert anthropic_provider.model == "claude-3-5-sonnet-20241022"
        
        # Test Gemini defaults
        gemini_provider = LLMProviderFactory.create_provider("gemini", api_key="test")
        assert gemini_provider.model == "gemini-1.5-flash"
    
    def test_create_unknown_provider(self):
        """Test creating unknown provider raises error."""
        
        with pytest.raises(ValueError, match="Unknown provider: unknown"):
            LLMProviderFactory.create_provider("unknown")
    
    def test_get_available_providers(self):
        """Test getting list of available providers."""
        
        providers = LLMProviderFactory.get_available_providers()
        
        assert "openai" in providers
        assert "anthropic" in providers
        assert "gemini" in providers
        assert len(providers) == 3


@pytest.mark.asyncio
class TestLLMProviderManager:
    """Test LLM provider manager with fallback functionality."""
    
    def test_provider_manager_initialization(self):
        """Test provider manager initialization."""
        
        provider_configs = [
            {"provider": "openai", "api_key": "openai_key"},
            {"provider": "anthropic", "api_key": "anthropic_key"},
            {"provider": "gemini", "api_key": "gemini_key"}
        ]
        
        manager = LLMProviderManager(provider_configs)
        assert len(manager.providers) == 3
        assert isinstance(manager.providers[0], OpenAIProvider)
        assert isinstance(manager.providers[1], AnthropicProvider)
        assert isinstance(manager.providers[2], GeminiProvider)
    
    def test_provider_manager_with_invalid_config(self):
        """Test provider manager handles invalid configurations."""
        
        provider_configs = [
            {"provider": "openai", "api_key": "valid_key"},
            {"provider": "invalid_provider", "api_key": "key"},  # Invalid
            {"provider": "anthropic", "api_key": "valid_key"}
        ]
        
        with patch('actions.utils.llm_providers.logger.warning') as mock_warning:
            manager = LLMProviderManager(provider_configs)
            
            # Should only create valid providers
            assert len(manager.providers) == 2
            assert isinstance(manager.providers[0], OpenAIProvider)
            assert isinstance(manager.providers[1], AnthropicProvider)
            
            # Should log warning about invalid provider
            mock_warning.assert_called()
    
    async def test_generate_analysis_with_fallback_success_first(self):
        """Test successful analysis with first provider."""
        
        # Mock successful first provider
        mock_provider1 = Mock()
        mock_provider1.generate_analysis = AsyncMock(return_value=LLMResponse(
            content="Successful analysis from first provider",
            usage=LLMUsageMetrics(provider="mock1", model="test"),
            success=True
        ))
        mock_provider1.get_provider_name.return_value = "mock1"
        
        mock_provider2 = Mock()
        mock_provider2.get_provider_name.return_value = "mock2"
        
        manager = LLMProviderManager([])
        manager.providers = [mock_provider1, mock_provider2]
        
        result = await manager.generate_analysis_with_fallback(
            "Analyze protein data",
            {"proteins": ["P12345"]}
        )
        
        assert result.success is True
        assert "first provider" in result.content
        mock_provider1.generate_analysis.assert_called_once()
        # Second provider should not be called
        assert not hasattr(mock_provider2, 'generate_analysis') or not mock_provider2.generate_analysis.called
    
    async def test_generate_analysis_with_fallback_to_second(self):
        """Test fallback to second provider when first fails."""
        
        # Mock failing first provider
        mock_provider1 = Mock()
        mock_provider1.generate_analysis = AsyncMock(return_value=LLMResponse(
            content="",
            usage=LLMUsageMetrics(provider="mock1", model="test"),
            success=False,
            error_message="API error"
        ))
        mock_provider1.get_provider_name.return_value = "mock1"
        
        # Mock successful second provider
        mock_provider2 = Mock()
        mock_provider2.generate_analysis = AsyncMock(return_value=LLMResponse(
            content="Successful analysis from fallback provider",
            usage=LLMUsageMetrics(provider="mock2", model="test"),
            success=True
        ))
        mock_provider2.get_provider_name.return_value = "mock2"
        
        manager = LLMProviderManager([])
        manager.providers = [mock_provider1, mock_provider2]
        
        result = await manager.generate_analysis_with_fallback(
            "Analyze metabolite data",
            {"metabolites": ["HMDB0000001"]}
        )
        
        assert result.success is True
        assert "fallback provider" in result.content
        mock_provider1.generate_analysis.assert_called_once()
        mock_provider2.generate_analysis.assert_called_once()
    
    async def test_generate_analysis_all_providers_fail(self):
        """Test behavior when all providers fail."""
        
        # Mock all providers failing
        mock_provider1 = Mock()
        mock_provider1.generate_analysis = AsyncMock(return_value=LLMResponse(
            content="",
            usage=LLMUsageMetrics(provider="mock1", model="test"),
            success=False,
            error_message="First provider error"
        ))
        mock_provider1.get_provider_name.return_value = "mock1"
        
        mock_provider2 = Mock()
        mock_provider2.generate_analysis = AsyncMock(return_value=LLMResponse(
            content="",
            usage=LLMUsageMetrics(provider="mock2", model="test"),
            success=False,
            error_message="Second provider error"
        ))
        mock_provider2.get_provider_name.return_value = "mock2"
        
        manager = LLMProviderManager([])
        manager.providers = [mock_provider1, mock_provider2]
        
        result = await manager.generate_analysis_with_fallback(
            "Analyze data",
            {"data": "test"}
        )
        
        assert result.success is False
        assert "All providers failed" in result.error_message
        assert "Second provider error" in result.error_message
    
    async def test_generate_analysis_with_exceptions(self):
        """Test handling of exceptions during provider calls."""
        
        # Mock provider that raises exception
        mock_provider1 = Mock()
        mock_provider1.generate_analysis = AsyncMock(side_effect=Exception("Connection timeout"))
        mock_provider1.get_provider_name.return_value = "mock1"
        
        # Mock successful fallback provider
        mock_provider2 = Mock()
        mock_provider2.generate_analysis = AsyncMock(return_value=LLMResponse(
            content="Recovery successful",
            usage=LLMUsageMetrics(provider="mock2", model="test"),
            success=True
        ))
        mock_provider2.get_provider_name.return_value = "mock2"
        
        manager = LLMProviderManager([])
        manager.providers = [mock_provider1, mock_provider2]
        
        result = await manager.generate_analysis_with_fallback(
            "Analyze data",
            {"data": "test"}
        )
        
        assert result.success is True
        assert "Recovery successful" in result.content


class TestBiologicalDataIntegration:
    """Test LLM providers with biological data patterns."""
    
    @pytest.mark.asyncio
    async def test_protein_mapping_analysis(self):
        """Test LLM analysis of protein mapping data."""
        
        provider = OpenAIProvider(api_key="test_key")
        
        protein_data = {
            "strategy_name": "protein_uniprot_mapping",
            "total_proteins": 1000,
            "matched_proteins": 850,
            "edge_cases": ["Q6EMK4"],  # Known problematic identifier
            "match_methods": {
                "exact_match": 650,
                "fuzzy_match": 150,
                "historical_api": 50
            },
            "confidence_distribution": {
                "high": 700,
                "medium": 100,
                "low": 50
            }
        }
        
        mock_response_data = {
            "choices": [{"message": {"content": "Protein mapping analysis shows 85% success rate with Q6EMK4 requiring special handling..."}}],
            "usage": {"prompt_tokens": 200, "completion_tokens": 150, "total_tokens": 350}
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await provider.generate_analysis(
                "Analyze protein mapping results with focus on edge cases",
                protein_data
            )
            
            assert result.success is True
            assert "Q6EMK4" in result.content  # Should handle edge case identifier
            assert "protein mapping" in result.content.lower()
    
    @pytest.mark.asyncio
    async def test_metabolite_mapping_analysis(self):
        """Test LLM analysis of metabolite mapping data."""
        
        provider = AnthropicProvider(api_key="test_key")
        
        metabolite_data = {
            "strategy_name": "metabolite_hmdb_mapping",
            "total_metabolites": 500,
            "hmdb_matches": 400,
            "inchikey_matches": 450,
            "cas_matches": 300,
            "semantic_matches": 50,
            "confidence_scores": [0.95, 0.85, 0.75, 0.65],
            "problematic_compounds": ["stereoisomers", "tautomers"]
        }
        
        mock_response_data = {
            "content": [{"text": "Metabolite mapping achieved 90% HMDB coverage with stereoisomer challenges noted..."}],
            "usage": {"input_tokens": 180, "output_tokens": 220}
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await provider.generate_analysis(
                "Analyze metabolite mapping with emphasis on chemical structure challenges",
                metabolite_data
            )
            
            assert result.success is True
            assert "HMDB" in result.content
            assert "stereoisomer" in result.content.lower()
    
    @pytest.mark.asyncio 
    async def test_chemistry_loinc_analysis(self):
        """Test LLM analysis of clinical chemistry LOINC mapping."""
        
        provider = GeminiProvider(api_key="test_key")
        
        chemistry_data = {
            "strategy_name": "chemistry_loinc_mapping",
            "total_tests": 200,
            "loinc_matches": 150,
            "fuzzy_matches": 30,
            "vendor_harmonization": {
                "quest": 80,
                "labcorp": 85,
                "mayo": 90
            },
            "test_categories": ["glucose", "cholesterol", "hemoglobin"],
            "method_variations": ["enzymatic", "spectrophotometric", "immunoassay"]
        }
        
        mock_response_data = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Clinical chemistry mapping shows 75% LOINC coverage with vendor harmonization challenges..."}]
                }
            }],
            "usageMetadata": {"totalTokenCount": 300}
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await provider.generate_analysis(
                "Analyze clinical chemistry LOINC mapping with vendor standardization focus",
                chemistry_data
            )
            
            assert result.success is True
            assert "LOINC" in result.content
            assert "clinical chemistry" in result.content.lower()
            assert "vendor" in result.content.lower()