# AIDL Integration with Biomapper

This document outlines a comprehensive integration plan between the Biomapper biological data harmonization toolkit and AIDL (Full-Stack Agent Infrastructure) for enhanced AI-powered biological data analysis.

## Overview

The integration enables biomapper strategies to leverage AIDL's agent system for intelligent biological data analysis, interpretation, and decision-making within the existing YAML-based workflow framework.

## Architecture Integration

### Biomapper + AIDL Flow
```
Biomapper Strategy → AIDL Action → Agent Session → DAG Workflow → Persistent Results
                                     ↓
                              MCP Servers (RTX-KG2, PubChem, etc.)
                                     ↓
                              Custom Biomapper Tools
```

### Key Components

1. **AIDL Actions**: New biomapper action types that interface with AIDL agents
2. **Session Persistence**: Leverage AIDL's DAG-based conversation tracking
3. **Custom Tools**: Biomapper functions exposed as AIDL tools
4. **MCP Integration**: External knowledge sources via MCP servers

## Implementation Plan

### 1. Dependency Setup

Add AIDL to `pyproject.toml`:
```toml
[tool.poetry.dependencies]
aidl = {git = "https://github.com/Center-For-Human-Healthspan-at-the-Buck/aidl.git", branch = "main"}
```

Environment variables in `.env`:
```bash
# AIDL Integration
SUPABASE_URL=https://supabase.nathanpricelab.com/
SUPABASE_KEY=<anon_key>
OPENAI_API_KEY=<key>
AIDL_USER=biomapper@buckinstitute.org
AIDL_PASSWORD=<secure_password>
```

### 2. Core AIDL Actions

#### AIDL_AGENT_EXECUTE Action
```python
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from pydantic import BaseModel
import aidl
from typing import List, Dict, Optional

class AIDLAgentParams(BaseModel):
    agent_slug: str
    prompt: str
    session_title: str = "Biomapper Analysis Session"
    mcp_servers: List[str] = ["exa_ai_mcp"]
    tools: List[str] = []
    persist_session: bool = True
    context_variables: Dict[str, str] = {}

@register_action("AIDL_AGENT_EXECUTE")
class ExecuteAIDLAgent(TypedStrategyAction[AIDLAgentParams, ActionResult]):
    """Execute an AIDL agent within a biomapper strategy workflow"""
    
    async def execute_typed(self, params: AIDLAgentParams, context: Dict) -> ActionResult:
        # Initialize AIDL with hosted Supabase
        await aidl.init_supabase_client()
        user_id = (await aidl.sign_in(
            os.getenv("AIDL_USER"), 
            os.getenv("AIDL_PASSWORD")
        )).user_id
        
        # Create session for workflow tracking
        session_id = None
        if params.persist_session:
            session = await aidl.create_session(aidl.SessionCreateModel(
                title=f"{params.session_title} - {context.get('strategy_name', 'unknown')}",
                user_id=user_id
            ))
            session_id = session.id
        
        # Format prompt with context data
        formatted_prompt = params.prompt.format(**context, **params.context_variables)
        
        # Execute agent
        result = await aidl.run_agent(
            slug=params.agent_slug,
            messages=[{"role": "user", "content": formatted_prompt}],
            session_id=session_id,
            user_id=user_id
        )
        
        # Store results in context
        context['aidl_output'] = result.final_output
        context['aidl_session_id'] = session_id
        context['aidl_metadata'] = {
            "agent_slug": params.agent_slug,
            "session_id": session_id,
            "total_tokens": getattr(result, 'total_tokens', None)
        }
        
        return ActionResult(
            success=True,
            data={
                "output": result.final_output,
                "session_id": session_id,
                "agent_slug": params.agent_slug
            }
        )
```

#### AIDL_AGENT_CREATE Action
```python
class AIDLAgentCreateParams(BaseModel):
    slug: str
    name: str
    instructions: str
    mcp_servers: List[str] = []
    tools: List[str] = []
    handoffs: List[str] = []

@register_action("AIDL_AGENT_CREATE")
class CreateAIDLAgent(TypedStrategyAction[AIDLAgentCreateParams, ActionResult]):
    """Create a new AIDL agent dynamically within a strategy"""
    
    async def execute_typed(self, params: AIDLAgentCreateParams, context: Dict) -> ActionResult:
        await aidl.init_supabase_client()
        user_id = (await aidl.sign_in(
            os.getenv("AIDL_USER"), 
            os.getenv("AIDL_PASSWORD")
        )).user_id
        
        # Check if agent exists
        agents = await aidl.get_agents()
        if params.slug not in [agent.slug for agent in agents]:
            agent = await aidl.create_agent(
                aidl.AgentCreateModel(
                    slug=params.slug,
                    name=params.name,
                    instructions=params.instructions,
                    handoffs=params.handoffs,
                    mcp_servers=params.mcp_servers,
                    tools=params.tools,
                    user_id=user_id,
                )
            )
            context['created_agent'] = agent.slug
        
        return ActionResult(success=True, data={"agent_slug": params.slug})
```

### 3. Biomapper Tools for AIDL Agents

Create biomapper-specific tools in AIDL's tool system:

#### File: `src/aidl/tools/biomapper_harmonize/__init__.py`
```python
async def biomapper_harmonize(identifier: str, source_namespace: str, target_namespace: str):
    """
    Harmonize biological identifier using biomapper's mapping system
    
    Args:
        identifier: The biological identifier to harmonize
        source_namespace: Source identifier namespace (e.g., 'gene_symbol')
        target_namespace: Target identifier namespace (e.g., 'uniprot')
    
    Returns:
        Harmonized identifiers and mapping metadata
    """
    from biomapper_client import BiomapperClient
    
    client = BiomapperClient()
    result = await client.execute_strategy(
        "UNIPROT_RESOLUTION",
        parameters={
            "identifier": identifier,
            "source_ns": source_namespace,
            "target_ns": target_namespace
        }
    )
    return result

async def biomapper_metabolite_match(metabolite_name: str, databases: List[str] = None):
    """
    Match metabolite names using biomapper's metabolomics tools
    
    Args:
        metabolite_name: Name of the metabolite to match
        databases: List of databases to search (default: all available)
    
    Returns:
        Matched metabolite identifiers and confidence scores
    """
    from biomapper_client import BiomapperClient
    
    client = BiomapperClient()
    result = await client.execute_strategy(
        "SEMANTIC_METABOLITE_MATCH",
        parameters={
            "query": metabolite_name,
            "databases": databases or ["pubchem", "hmdb", "kegg"]
        }
    )
    return result
```

### 4. YAML Strategy Examples

#### AI-Enhanced Metabolomics Analysis
```yaml
name: AI_ENHANCED_METABOLOMICS_ANALYSIS
description: Use AIDL agents for intelligent metabolite analysis and matching
parameters:
  data_file: "${DATA_DIR}/metabolites.tsv"
  output_dir: "${OUTPUT_DIR}"

steps:
  # Load initial data
  - name: load_metabolites
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.data_file}"
        identifier_column: metabolite_name
        output_key: metabolites

  # Create specialized metabolomics agent
  - name: create_metabolomics_agent
    action:
      type: AIDL_AGENT_CREATE
      params:
        slug: "metabolomics_researcher"
        name: "Metabolomics Research Agent"
        instructions: |
          You are a metabolomics research specialist. Analyze metabolite datasets 
          for biological significance, suggest optimal matching strategies, and 
          recommend relevant databases. Use available MCP servers for literature 
          search and biomapper tools for identifier harmonization.
        mcp_servers: ["rtx_kg2", "exa_ai_mcp"]
        tools: ["biomapper_harmonize", "biomapper_metabolite_match"]

  # AI-powered analysis
  - name: ai_metabolite_analysis
    action:
      type: AIDL_AGENT_EXECUTE
      params:
        agent_slug: "metabolomics_researcher"
        prompt: |
          Analyze these metabolites for biological significance:
          
          Metabolites: {current_identifiers}
          
          Tasks:
          1. Identify the metabolite types and classes
          2. Suggest optimal matching strategies
          3. Recommend relevant databases
          4. Highlight any potential issues or ambiguities
          5. Propose downstream analysis approaches
          
          Provide structured recommendations.
        session_title: "Metabolomics Analysis"
        persist_session: true

  # Execute AI-recommended matching
  - name: execute_ai_recommendations
    action:
      type: SEMANTIC_METABOLITE_MATCH
      params:
        input_key: metabolites
        strategy_hints: "${aidl_output}"
        confidence_threshold: 0.8

  # Generate AI-enhanced report
  - name: generate_enhanced_report
    action:
      type: AIDL_AGENT_EXECUTE
      params:
        agent_slug: "metabolomics_researcher"
        prompt: |
          Generate a comprehensive analysis report based on:
          
          Original metabolites: {metabolites}
          Matching results: {current_identifiers}
          Statistics: {statistics}
          
          Include:
          - Executive summary
          - Matching success rates
          - Biological insights
          - Quality assessment
          - Recommendations for follow-up
        context_variables:
          metabolites: "${metabolites}"
          statistics: "${statistics}"

  # Export results
  - name: export_results
    action:
      type: EXPORT_DATASET
      params:
        output_file: "${parameters.output_dir}/ai_enhanced_results.tsv"
        format: tsv
        include_metadata: true
```

#### Multi-Agent Gene Analysis Workflow
```yaml
name: MULTI_AGENT_GENE_ANALYSIS
description: Collaborative AI agents for comprehensive gene analysis

steps:
  # Create specialist agents
  - name: create_gene_curator
    action:
      type: AIDL_AGENT_CREATE
      params:
        slug: "gene_curator"
        name: "Gene Curation Specialist"
        instructions: "Expert in gene nomenclature, curation, and identifier harmonization"
        tools: ["biomapper_harmonize"]
        handoffs: ["pathway_analyst"]

  - name: create_pathway_analyst
    action:
      type: AIDL_AGENT_CREATE
      params:
        slug: "pathway_analyst"
        name: "Pathway Analysis Expert"
        instructions: "Specialized in biological pathway analysis and functional enrichment"
        mcp_servers: ["rtx_kg2"]
        handoffs: ["report_generator"]

  # Workflow execution with agent handoffs
  - name: gene_curation
    action:
      type: AIDL_AGENT_EXECUTE
      params:
        agent_slug: "gene_curator"
        prompt: "Curate and harmonize these genes: {current_identifiers}"

  # Results automatically handed off to pathway_analyst
  # Final report generation occurs through agent handoff system
```

### 5. MCP Server Integration

AIDL agents can access external knowledge through MCP servers:

#### RTX-KG2 Knowledge Graph
- Biomedical knowledge queries
- Drug-disease associations
- Gene-pathway relationships

#### PubChem Integration
- Chemical structure searches
- Metabolite property lookup
- Chemical similarity analysis

#### Literature Search (Exa)
- Research paper retrieval
- Citation analysis
- Current research trends

### 6. Session and Workflow Management

#### DAG-Based Conversation Tracking
- Each biomapper strategy creates an AIDL session
- Agent interactions form a directed acyclic graph
- Support for branching workflows and parallel analysis
- Persistent storage of all interactions

#### Benefits
- **Traceability**: Full audit trail of AI decision-making
- **Reproducibility**: Sessions can be replayed and analyzed
- **Collaboration**: Multiple users can interact with the same analysis
- **Debugging**: Step-by-step workflow inspection

### 7. Integration Testing

#### Unit Tests
```python
# tests/unit/core/strategy_actions/test_aidl_actions.py
import pytest
from biomapper.core.strategy_actions.aidl_agent import ExecuteAIDLAgent

@pytest.mark.asyncio
async def test_aidl_agent_execute():
    """Test AIDL agent execution within biomapper context"""
    # Mock AIDL components
    # Test agent creation and execution
    # Verify context updates
    pass
```

#### Integration Tests
```python
# tests/integration/test_aidl_integration.py
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_aidl_workflow():
    """Test complete AIDL-enhanced metabolomics workflow"""
    # Execute full strategy with AIDL agents
    # Verify results and session persistence
    pass
```

### 8. Configuration and Deployment

#### Environment Setup
- Hosted Supabase eliminates local database requirements
- OpenAI API key required for agent functionality
- Optional: Custom MCP servers for specialized domains

#### Security Considerations
- Secure credential management via environment variables
- User authentication through AIDL's auth system
- Audit logging of all agent interactions

### 9. Performance and Scalability

#### Optimizations
- Agent session reuse for multi-step workflows
- Parallel agent execution where appropriate
- Caching of frequently-used agent responses

#### Monitoring
- Track agent usage and costs
- Monitor session performance
- Log agent decision paths for analysis

### 10. Future Enhancements

#### Advanced Features
- Custom agent training on biomapper-specific tasks
- Integration with additional MCP servers
- Real-time collaboration through web UI
- Advanced workflow orchestration

#### Research Applications
- Automated literature review and synthesis
- Hypothesis generation from biological data
- Intelligent quality control and validation
- Predictive analysis and recommendations

## Benefits of Integration

1. **Enhanced Intelligence**: AI-powered analysis and decision-making
2. **Flexibility**: Dynamic agent creation for specific tasks
3. **Persistence**: Full audit trail and reproducible workflows
4. **Extensibility**: Easy addition of new AI capabilities
5. **Collaboration**: Multi-user and multi-agent workflows
6. **Knowledge Integration**: Access to external knowledge sources

## Getting Started

1. Set up environment variables for AIDL integration
2. Add AIDL dependency to biomapper
3. Implement core AIDL actions
4. Create biomapper-specific tools for AIDL
5. Design YAML strategies incorporating AI agents
6. Test integration with sample datasets

This integration transforms biomapper from a deterministic data processing pipeline into an intelligent, adaptive biological analysis platform powered by AI agents.