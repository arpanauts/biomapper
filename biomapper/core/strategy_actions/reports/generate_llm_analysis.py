"""Generate LLM-powered analysis reports from progressive mapping results."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field

from biomapper.core.standards.base_models import ActionParamsBase
from biomapper.core.standards.context_handler import UniversalContext
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.utils.llm_providers import (
    LLMProviderFactory, 
    LLMProviderManager, 
    LLMResponse
)
from biomapper.core.strategy_actions.utils.llm_prompts import (
    BiomapperAnalysisPrompts,
    ProgressiveAnalysisTemplates
)

logger = logging.getLogger(__name__)


class LLMAnalysisParams(ActionParamsBase):
    """Parameters for LLM analysis generation."""
    
    provider: str = Field("openai", description="LLM provider: openai, anthropic, gemini")
    model: str = Field("gpt-4", description="Specific model to use")
    custom_system_prompt: Optional[str] = Field(None, description="Custom analysis prompt")
    output_format: List[str] = Field(["summary", "flowchart"], description="Output types to generate")
    include_recommendations: bool = Field(True, description="Include optimization recommendations")
    output_directory: str = Field(..., description="Directory for generated files")
    
    # Advanced options
    fallback_providers: List[str] = Field([], description="Fallback providers if primary fails")
    entity_type: str = Field("protein", description="Entity type being analyzed: protein, metabolite, chemistry")
    analysis_focus: List[str] = Field([], description="Specific areas to focus analysis on")
    biological_context: Optional[str] = Field(None, description="Additional biological context")
    
    # Data source keys (following 2025 standards)
    progressive_stats_key: str = Field("progressive_stats", description="Key for progressive statistics in context")
    mapping_results_key: str = Field("mapping_results", description="Key for mapping results in context")
    strategy_name: str = Field("", description="Name of the strategy being analyzed")


class LLMAnalysisResult(BaseModel):
    """Result of LLM analysis generation."""
    
    success: bool = Field(True, description="Whether the action succeeded")
    message: str = Field("", description="Success or error message")
    generated_files: List[str] = Field([], description="List of generated file paths")
    analysis_metadata: Dict[str, Any] = Field({}, description="LLM usage and analysis metadata")
    summary_content: Optional[str] = Field(None, description="Generated summary content")
    flowchart_content: Optional[str] = Field(None, description="Generated mermaid flowchart")
    data: Dict[str, Any] = Field({}, description="Additional data")


@register_action("GENERATE_LLM_ANALYSIS")
class GenerateLLMAnalysisAction(TypedStrategyAction[LLMAnalysisParams, LLMAnalysisResult]):
    """Generate LLM-powered analysis reports from progressive mapping results."""
    
    def get_params_model(self) -> type[LLMAnalysisParams]:
        return LLMAnalysisParams
    
    def get_result_model(self) -> type[LLMAnalysisResult]:
        return LLMAnalysisResult
    
    async def execute_typed(
        self,
        params: LLMAnalysisParams,
        context: Dict[str, Any],
        **kwargs
    ) -> LLMAnalysisResult:
        """Execute LLM analysis generation."""
        
        try:
            # Use standardized context handling
            ctx = UniversalContext.wrap(context)
            
            # Extract data from context
            datasets = ctx.get_datasets()
            progressive_stats = datasets.get(params.progressive_stats_key) or ctx.get(params.progressive_stats_key, {})
            mapping_results = datasets.get(params.mapping_results_key) or ctx.get(params.mapping_results_key, [])
            
            # Validate input data
            if not progressive_stats and not mapping_results:
                return LLMAnalysisResult(
                    input_identifiers=current_identifiers,
                    output_identifiers=current_identifiers,
                    output_ontology_type=current_ontology_type,
                    details={"error": "No progressive stats or mapping results found in context"}
                )
            
            # Setup output directory
            output_dir = Path(params.output_directory)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create LLM provider manager with fallbacks
            provider_configs = []
            
            # Primary provider
            provider_configs.append({
                "provider": params.provider,
                "model": params.model
            })
            
            # Add fallback providers
            for fallback_provider in params.fallback_providers:
                fallback_config = {"provider": fallback_provider}
                if fallback_provider == "openai":
                    fallback_config["model"] = "gpt-4"
                elif fallback_provider == "anthropic":
                    fallback_config["model"] = "claude-3-5-sonnet-20241022"
                elif fallback_provider == "gemini":
                    fallback_config["model"] = "gemini-1.5-flash"
                provider_configs.append(fallback_config)
            
            llm_manager = LLMProviderManager(provider_configs)
            
            # Prepare analysis context
            analysis_context = ProgressiveAnalysisTemplates.create_analysis_context(
                progressive_stats=progressive_stats,
                mapping_results=mapping_results,
                strategy_name=params.strategy_name or "Unknown Strategy",
                entity_type=params.entity_type
            )
            
            # Generate outputs based on requested formats
            generated_files = []
            analysis_metadata = {
                "timestamp": datetime.now().isoformat(),
                "provider": params.provider,
                "model": params.model,
                "entity_type": params.entity_type,
                "strategy_name": params.strategy_name,
                "llm_usage": []
            }
            
            summary_content = None
            flowchart_content = None
            
            # Generate summary report
            if "summary" in params.output_format:
                summary_content, summary_metadata = await self._generate_summary_report(
                    llm_manager=llm_manager,
                    analysis_context=analysis_context,
                    params=params,
                    output_dir=output_dir
                )
                if summary_content:
                    summary_file = output_dir / "mapping_summary.md"
                    generated_files.append(str(summary_file))
                    analysis_metadata["llm_usage"].append(summary_metadata)
            
            # Generate mermaid flowchart
            if "flowchart" in params.output_format:
                flowchart_content, flowchart_metadata = await self._generate_mermaid_flowchart(
                    llm_manager=llm_manager,
                    analysis_context=analysis_context,
                    params=params,
                    output_dir=output_dir
                )
                if flowchart_content:
                    flowchart_file = output_dir / "strategy_flowchart.mermaid"
                    generated_files.append(str(flowchart_file))
                    analysis_metadata["llm_usage"].append(flowchart_metadata)
            
            # Generate metadata file
            metadata_file = output_dir / "analysis_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(analysis_metadata, f, indent=2, default=str)
            generated_files.append(str(metadata_file))
            
            # Store results in context for downstream actions
            ctx.set("llm_analysis_files", generated_files)
            ctx.set("llm_analysis_metadata", analysis_metadata)
            
            return LLMAnalysisResult(
                success=True,
                message="LLM analysis completed successfully",
                generated_files=generated_files,
                analysis_metadata=analysis_metadata,
                summary_content=summary_content,
                flowchart_content=flowchart_content,
                data={
                    "files_generated": len(generated_files),
                    "output_directory": str(output_dir),
                    "total_llm_requests": len(analysis_metadata.get("llm_usage", []))
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error generating LLM analysis: {e}", exc_info=True)
            return LLMAnalysisResult(
                success=False,
                message=f"Error generating LLM analysis: {str(e)}",
                data={"error": str(e)}
            )
    
    async def _generate_summary_report(
        self,
        llm_manager: LLMProviderManager,
        analysis_context: Dict[str, Any],
        params: LLMAnalysisParams,
        output_dir: Path
    ) -> tuple[Optional[str], Dict[str, Any]]:
        """Generate summary analysis report."""
        
        try:
            # Get appropriate prompt
            if params.custom_system_prompt:
                prompt = params.custom_system_prompt
            else:
                prompt = BiomapperAnalysisPrompts.get_analysis_prompt("universal")
                
                # Customize prompt based on parameters
                customizations = {
                    "entity_type": params.entity_type,
                    "focus_areas": params.analysis_focus,
                    "biological_context": params.biological_context
                }
                prompt = BiomapperAnalysisPrompts.customize_prompt(prompt, customizations)
            
            # Add recommendation requirement
            if params.include_recommendations:
                prompt += "\n\nIMPORTANT: Include specific, actionable optimization recommendations."
            
            # Generate analysis
            response = await llm_manager.generate_analysis_with_fallback(prompt, analysis_context)
            
            if response.success and response.content:
                # Write summary to file
                summary_file = output_dir / "mapping_summary.md"
                
                # Add header with metadata
                header = f"""# Biomapper Analysis Report

**Strategy:** {analysis_context.get('strategy_name', 'Unknown')}  
**Entity Type:** {params.entity_type.title()}  
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Provider:** {response.usage.provider} ({response.usage.model})

---

"""
                
                full_content = header + response.content
                
                with open(summary_file, 'w') as f:
                    f.write(full_content)
                
                self.logger.info(f"Generated summary report: {summary_file}")
                return full_content, response.usage.model_dump()
            else:
                self.logger.error(f"Failed to generate summary: {response.error_message}")
                return None, {"error": response.error_message}
                
        except Exception as e:
            self.logger.error(f"Error generating summary report: {e}")
            return None, {"error": str(e)}
    
    async def _generate_mermaid_flowchart(
        self,
        llm_manager: LLMProviderManager,
        analysis_context: Dict[str, Any],
        params: LLMAnalysisParams,
        output_dir: Path
    ) -> tuple[Optional[str], Dict[str, Any]]:
        """Generate mermaid flowchart."""
        
        try:
            prompt = BiomapperAnalysisPrompts.get_analysis_prompt("mermaid")
            
            # Add entity-specific guidance
            entity_guidance = {
                "protein": "Include protein identifier types (UniProt, Ensembl, gene symbols) in flowchart nodes.",
                "metabolite": "Include metabolite identifier types (HMDB, KEGG, InChIKey) in flowchart nodes.",
                "chemistry": "Include chemistry identifier types (LOINC, test names) in flowchart nodes."
            }
            
            if params.entity_type in entity_guidance:
                prompt += f"\n\n{entity_guidance[params.entity_type]}"
            
            # Generate flowchart
            response = await llm_manager.generate_analysis_with_fallback(prompt, analysis_context)
            
            if response.success and response.content:
                # Extract mermaid code from response
                content = response.content.strip()
                
                # Find mermaid code block
                if "```mermaid" in content:
                    start = content.find("```mermaid") + 10
                    end = content.find("```", start)
                    if end != -1:
                        mermaid_code = content[start:end].strip()
                    else:
                        mermaid_code = content[start:].strip()
                elif "graph " in content or "flowchart " in content:
                    # Raw mermaid code without code blocks
                    mermaid_code = content
                else:
                    # Wrap in mermaid if needed
                    mermaid_code = content
                
                # Write flowchart to file
                flowchart_file = output_dir / "strategy_flowchart.mermaid"
                
                with open(flowchart_file, 'w') as f:
                    f.write(mermaid_code)
                
                self.logger.info(f"Generated mermaid flowchart: {flowchart_file}")
                return mermaid_code, response.usage.model_dump()
            else:
                self.logger.error(f"Failed to generate flowchart: {response.error_message}")
                return None, {"error": response.error_message}
                
        except Exception as e:
            self.logger.error(f"Error generating mermaid flowchart: {e}")
            return None, {"error": str(e)}


# Support for Gemini collaboration via MCP
async def collaborate_with_gemini_for_analysis(
    progressive_stats: Dict[str, Any],
    mapping_results: List[Any],
    strategy_name: str,
    output_dir: str
) -> Dict[str, Any]:
    """Collaborate with Gemini via MCP for enhanced analysis."""
    
    try:
        # Create analysis context
        analysis_context = ProgressiveAnalysisTemplates.create_analysis_context(
            progressive_stats=progressive_stats,
            mapping_results=mapping_results,
            strategy_name=strategy_name,
            entity_type="protein"  # Default, can be customized
        )
        
        # Setup LLM action parameters
        params = LLMAnalysisParams(
            provider="gemini",
            model="gemini-1.5-flash",
            output_format=["summary", "flowchart"],
            include_recommendations=True,
            output_directory=output_dir,
            strategy_name=strategy_name,
            entity_type="protein",
            fallback_providers=["openai", "anthropic"]
        )
        
        # Create and execute action
        action = GenerateLLMAnalysisAction()
        
        # Mock context with required data
        mock_context = {
            "progressive_stats": progressive_stats,
            "mapping_results": mapping_results
        }
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context
        )
        
        return {
            "success": True,
            "generated_files": result.generated_files,
            "analysis_metadata": result.analysis_metadata,
            "summary_content": result.summary_content,
            "flowchart_content": result.flowchart_content
        }
        
    except Exception as e:
        logger.error(f"Error in Gemini collaboration: {e}")
        return {
            "success": False,
            "error": str(e)
        }