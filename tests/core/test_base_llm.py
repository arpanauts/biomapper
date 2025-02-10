"""Tests for LLM base classes."""
import pytest
from pydantic import ValidationError
from typing import Dict, Any, Optional, List, Union

from biomapper.core.base_llm import (
    LLMConfig,
    InsightType,
    AnalysisResult,
    BaseLLMAnalyzer,
    LLMError,
)
from biomapper.core.base_spoke import SPOKEEntity, SPOKERelation


class MockLLMAnalyzer(BaseLLMAnalyzer):
    """Test implementation of BaseLLMAnalyzer."""
    
    async def analyze_results(
        self,
        query_results: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        return AnalysisResult(
            entities=[
                SPOKEEntity(
                    input_id="TEST:1",
                    spoke_id="SPOKE:1",
                    node_type="Compound",
                    node_label="Test Compound",
                    confidence=1.0
                )
            ],
            relationships=[
                SPOKERelation(
                    source_id="SPOKE:1",
                    target_id="SPOKE:2",
                    relation_type="ASSOCIATES_WITH"
                )
            ],
            insights=[
                InsightType(
                    category="pathway_enrichment",
                    description="Test pathway enrichment",
                    evidence=["Test evidence"],
                    confidence=0.8
                )
            ],
            confidence_scores={"pathway_analysis": 0.9}
        )

    async def generate_prompts(
        self,
        analysis_type: str,
        data: Dict[str, Any],
        template_vars: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        return [f"Analyze {analysis_type} for given data"]

    async def process_response(
        self,
        response: Union[str, Dict[str, Any]],
        analysis_type: str
    ) -> InsightType:
        return InsightType(
            category=analysis_type,
            description="Test insight",
            evidence=["Test"],
            confidence=0.9
        )


@pytest.fixture
def llm_config() -> LLMConfig:
    """Fixture for test LLM configuration."""
    return LLMConfig(
        model_name="test-model",
        temperature=0.7,
        max_tokens=1000,
        timeout=30
    )


@pytest.fixture
def insight_data() -> Dict[str, Any]:
    """Fixture for valid insight data."""
    return {
        "category": "pathway_enrichment",
        "description": "Test pathway enrichment",
        "evidence": ["Evidence 1", "Evidence 2"],
        "confidence": 0.85,
        "metadata": {"source": "test"}
    }


@pytest.fixture
def analysis_result_data() -> Dict[str, Any]:
    """Fixture for valid analysis result data."""
    return {
        "entities": [
            {
                "input_id": "TEST:1",
                "spoke_id": "SPOKE:1",
                "node_type": "Compound",
                "node_label": "Test",
                "confidence": 1.0
            }
        ],
        "relationships": [
            {
                "source_id": "SPOKE:1",
                "target_id": "SPOKE:2",
                "relation_type": "ASSOCIATES_WITH"
            }
        ],
        "insights": [
            {
                "category": "pathway_enrichment",
                "description": "Test insight",
                "evidence": ["Test evidence"],
                "confidence": 0.8
            }
        ],
        "confidence_scores": {
            "analysis": 0.9
        }
    }


class TestLLMConfig:
    """Tests for LLMConfig."""
    
    def test_valid_config(self, llm_config):
        """Test valid configuration creation."""
        assert llm_config.model_name == "test-model"
        assert llm_config.temperature == 0.7
        assert llm_config.max_tokens == 1000
        assert llm_config.timeout == 30

    def test_invalid_temperature(self):
        """Test temperature validation."""
        with pytest.raises(ValidationError) as exc:
            LLMConfig(
                model_name="test",
                temperature=2.5,
                max_tokens=1000
            )
        assert "temperature" in str(exc.value)

    def test_invalid_max_tokens(self):
        """Test max_tokens validation."""
        with pytest.raises(ValidationError) as exc:
            LLMConfig(
                model_name="test",
                temperature=0.7,
                max_tokens=-1
            )
        assert "max_tokens" in str(exc.value)

    def test_config_immutable(self, llm_config):
        """Test that config is immutable."""
        with pytest.raises(Exception):
            llm_config.temperature = 0.5


class TestInsightType:
    """Tests for InsightType."""
    
    def test_valid_insight(self, insight_data):
        """Test valid insight creation."""
        insight = InsightType(**insight_data)
        assert insight.category == "pathway_enrichment"
        assert insight.description == "Test pathway enrichment"
        assert len(insight.evidence) == 2
        assert insight.confidence == 0.85

    def test_invalid_confidence(self, insight_data):
        """Test confidence validation."""
        insight_data["confidence"] = 1.5
        with pytest.raises(ValidationError) as exc:
            InsightType(**insight_data)
        assert "confidence" in str(exc.value)

    def test_default_values(self):
        """Test insight default values."""
        insight = InsightType(
            category="test",
            description="test description"
        )
        assert insight.evidence == []
        assert insight.confidence == 1.0
        assert insight.metadata == {}


class TestAnalysisResult:
    """Tests for AnalysisResult."""
    
    def test_valid_result(self, analysis_result_data):
        """Test valid result creation."""
        result = AnalysisResult(**analysis_result_data)
        assert len(result.entities) == 1
        assert len(result.relationships) == 1
        assert len(result.insights) == 1
        assert isinstance(result.insights[0], InsightType)

    def test_empty_result(self):
        """Test result with minimal data."""
        result = AnalysisResult()
        assert result.entities == []
        assert result.relationships == []
        assert result.insights == []
        assert result.confidence_scores == {}
        assert result.metadata == {}


class TestBaseLLMAnalyzer:
    """Tests for BaseLLMAnalyzer."""
    
    @pytest.mark.asyncio
    async def test_mock_analyzer(self):
        """Test mock implementation of BaseLLMAnalyzer."""
        analyzer = MockLLMAnalyzer()
        result = await analyzer.analyze_results(
            {"test": "data"},
            {"context": "test"}
        )
        
        assert isinstance(result, AnalysisResult)
        assert len(result.entities) == 1
        assert len(result.relationships) == 1
        assert len(result.insights) == 1
        assert result.confidence_scores["pathway_analysis"] == 0.9

    @pytest.mark.asyncio
    async def test_prompt_generation(self):
        """Test prompt generation."""
        analyzer = MockLLMAnalyzer()
        prompts = await analyzer.generate_prompts(
            "test_analysis",
            {"data": "test"},
            {"var": "test"}
        )
        assert len(prompts) == 1
        assert "test_analysis" in prompts[0]

    @pytest.mark.asyncio
    async def test_response_processing(self):
        """Test response processing."""
        analyzer = MockLLMAnalyzer()
        insight = await analyzer.process_response(
            "Test response",
            "test_analysis"
        )
        assert isinstance(insight, InsightType)
        assert insight.category == "test_analysis"
        assert insight.confidence == 0.9


def test_llm_error():
    """Test LLMError exception."""
    with pytest.raises(LLMError) as exc:
        raise LLMError("Test error")
    assert str(exc.value) == "Test error"
