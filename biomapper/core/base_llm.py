"""Base classes for LLM integration in biomapper."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field

from .base_spoke import SPOKEEntity, SPOKERelation


class LLMConfig(BaseModel):
    """Configuration for LLM analysis."""
    
    model_name: str = Field(
        "gpt-4",
        description="Name of the LLM model to use"
    )
    temperature: float = Field(
        0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for LLM sampling"
    )
    max_tokens: int = Field(
        1000,
        gt=0,
        description="Maximum tokens in LLM response"
    )
    timeout: int = Field(
        30,
        gt=0,
        description="Request timeout in seconds"
    )
    
    class Config:
        """Pydantic config."""
        frozen = True


class InsightType(BaseModel):
    """Structured insight from LLM analysis."""
    
    category: str = Field(..., description="Category of insight")
    description: str = Field(..., description="Detailed description")
    evidence: List[str] = Field(
        default_factory=list,
        description="Supporting evidence"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class AnalysisResult(BaseModel):
    """Results of LLM analysis."""
    
    entities: List[SPOKEEntity] = Field(
        default_factory=list,
        description="Analyzed SPOKE entities"
    )
    relationships: List[SPOKERelation] = Field(
        default_factory=list,
        description="Discovered relationships"
    )
    insights: List[InsightType] = Field(
        default_factory=list,
        description="Analysis insights"
    )
    confidence_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Confidence scores for insights"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional analysis metadata"
    )
    
    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True


class BaseLLMAnalyzer(ABC):
    """Base class for LLM analysis of SPOKE results."""
    
    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        """Initialize the analyzer.
        
        Args:
            config: Optional configuration object
        """
        self.config = config or LLMConfig()
    
    @abstractmethod
    async def analyze_results(
        self,
        query_results: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """Analyze SPOKE query results using LLM.
        
        Args:
            query_results: Raw SPOKE query results
            context: Optional additional context
            
        Returns:
            Analysis results with insights
            
        Raises:
            LLMError: If analysis fails
        """
        pass

    @abstractmethod
    async def generate_prompts(
        self,
        analysis_type: str,
        data: Dict[str, Any],
        template_vars: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Generate prompts for LLM analysis.
        
        Args:
            analysis_type: Type of analysis to perform
            data: Data to analyze
            template_vars: Optional variables for prompt templates
            
        Returns:
            List of generated prompts
            
        Raises:
            ValueError: If analysis_type is invalid
            LLMError: If prompt generation fails
        """
        pass

    @abstractmethod
    async def process_response(
        self,
        response: Union[str, Dict[str, Any]],
        analysis_type: str
    ) -> InsightType:
        """Process raw LLM response into structured insight.
        
        Args:
            response: Raw LLM response
            analysis_type: Type of analysis performed
            
        Returns:
            Structured insight from response
            
        Raises:
            ValueError: If response format is invalid
            LLMError: If processing fails
        """
        pass


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass
