"""
Unit tests for the LLM mapper component of the MVP0 pipeline.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from biomapper.mvp0_pipeline.llm_mapper import select_best_cid_with_llm, LLMChoice
from biomapper.schemas.mvp0_schema import LLMCandidateInfo, PubChemAnnotation


@pytest.fixture
def sample_candidates():
    """Fixture providing sample candidate data for testing."""
    return [
        LLMCandidateInfo(
            cid=5793,
            qdrant_score=0.95,
            annotations=PubChemAnnotation(
                cid=5793,
                title="Glucose",
                iupac_name="(2R,3S,4R,5R)-2,3,4,5,6-Pentahydroxyhexanal",
                molecular_formula="C6H12O6",
                synonyms=["D-Glucose", "Dextrose", "Grape sugar"],
                description="A primary source of energy for living organisms."
            )
        ),
        LLMCandidateInfo(
            cid=107526,
            qdrant_score=0.88,
            annotations=PubChemAnnotation(
                cid=107526,
                title="beta-D-Glucopyranose",
                molecular_formula="C6H12O6",
                synonyms=["beta-D-glucose"],
                description="The beta-anomeric form of D-glucopyranose."
            )
        )
    ]


@pytest.mark.asyncio
async def test_select_best_cid_with_llm_no_api_key():
    """Test that function returns error when no API key is provided."""
    candidates = [
        LLMCandidateInfo(
            cid=12345,
            qdrant_score=0.9,
            annotations=PubChemAnnotation(cid=12345, title="Test Compound")
        )
    ]
    
    with patch.dict('os.environ', {}, clear=True):
        result = await select_best_cid_with_llm("test compound", candidates)
        
    assert result.selected_cid is None
    assert result.error_message is not None
    assert "API key" in result.error_message


@pytest.mark.asyncio
async def test_select_best_cid_with_llm_no_candidates():
    """Test that function returns error when no candidates are provided."""
    result = await select_best_cid_with_llm("test compound", [])
    
    assert result.selected_cid is None
    assert result.error_message == "No candidates provided to LLM for decision."


@pytest.mark.asyncio
async def test_select_best_cid_with_llm_successful_response(sample_candidates):
    """Test successful LLM response parsing."""
    # Mock the Anthropic client
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(text=json.dumps({
            "selected_cid": 5793,
            "confidence": 0.95,
            "rationale": "Direct title match with 'Glucose'"
        }))
    ]
    
    with patch('biomapper.mvp0_pipeline.llm_mapper.AsyncAnthropic') as mock_anthropic:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client
        
        result = await select_best_cid_with_llm(
            "glucose", 
            sample_candidates,
            anthropic_api_key="test_key"
        )
        
    assert result.selected_cid == 5793
    assert result.llm_confidence == 0.95
    assert "Direct title match" in result.llm_rationale
    assert result.error_message is None


@pytest.mark.asyncio
async def test_select_best_cid_with_llm_no_match(sample_candidates):
    """Test LLM response when no good match is found."""
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(text=json.dumps({
            "selected_cid": None,
            "confidence": 0.0,
            "rationale": "No suitable match found"
        }))
    ]
    
    with patch('biomapper.mvp0_pipeline.llm_mapper.AsyncAnthropic') as mock_anthropic:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client
        
        result = await select_best_cid_with_llm(
            "unknown_compound", 
            sample_candidates,
            anthropic_api_key="test_key"
        )
        
    assert result.selected_cid is None
    assert result.llm_confidence == 0.0
    assert "No suitable match" in result.llm_rationale
    assert result.error_message is None


@pytest.mark.asyncio
async def test_select_best_cid_with_llm_api_error(sample_candidates):
    """Test error handling when API call fails."""
    with patch('biomapper.mvp0_pipeline.llm_mapper.AsyncAnthropic') as mock_anthropic:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("API Error"))
        mock_anthropic.return_value = mock_client
        
        result = await select_best_cid_with_llm(
            "glucose", 
            sample_candidates,
            anthropic_api_key="test_key"
        )
        
    assert result.selected_cid is None
    assert result.error_message is not None
    assert "API error" in result.error_message


@pytest.mark.asyncio
async def test_select_best_cid_with_llm_invalid_json_response(sample_candidates):
    """Test error handling when LLM returns invalid JSON."""
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(text="This is not valid JSON")
    ]
    
    with patch('biomapper.mvp0_pipeline.llm_mapper.AsyncAnthropic') as mock_anthropic:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client
        
        result = await select_best_cid_with_llm(
            "glucose", 
            sample_candidates,
            anthropic_api_key="test_key"
        )
        
    assert result.selected_cid is None
    assert result.error_message is not None
    assert "Failed to parse" in result.error_message


@pytest.mark.asyncio
async def test_select_best_cid_with_llm_string_confidence(sample_candidates):
    """Test handling of string confidence values."""
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(text=json.dumps({
            "selected_cid": 5793,
            "confidence": "high",
            "rationale": "Strong match"
        }))
    ]
    
    with patch('biomapper.mvp0_pipeline.llm_mapper.AsyncAnthropic') as mock_anthropic:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client
        
        result = await select_best_cid_with_llm(
            "glucose", 
            sample_candidates,
            anthropic_api_key="test_key"
        )
        
    assert result.selected_cid == 5793
    assert result.llm_confidence == 0.9  # "high" maps to 0.9
    assert result.error_message is None


@pytest.mark.asyncio
async def test_llm_choice_model():
    """Test the LLMChoice Pydantic model."""
    # Test valid creation
    choice = LLMChoice(
        selected_cid=12345,
        llm_confidence=0.85,
        llm_rationale="Test rationale"
    )
    assert choice.selected_cid == 12345
    assert choice.llm_confidence == 0.85
    assert choice.llm_rationale == "Test rationale"
    assert choice.error_message is None
    
    # Test with error
    error_choice = LLMChoice(error_message="Test error")
    assert error_choice.selected_cid is None
    assert error_choice.llm_confidence is None
    assert error_choice.llm_rationale is None
    assert error_choice.error_message == "Test error"
    
    # Test confidence validation
    with pytest.raises(ValueError):
        LLMChoice(llm_confidence=1.5)  # Above 1.0
    
    with pytest.raises(ValueError):
        LLMChoice(llm_confidence=-0.1)  # Below 0.0