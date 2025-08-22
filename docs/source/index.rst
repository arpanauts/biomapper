BioMapper Documentation
=======================

BioMapper is a general-purpose plugin- and strategy-based orchestration framework, with its first application in biological data harmonization. Architecturally, it blends elements of workflow engines (Nextflow, Snakemake, Kedro, Dagster) with a lightweight service-oriented API and a plugin registry backed by a unified UniversalContext. Its standout differentiator is an AI-native developer experience: CLAUDE.md, .claude/ scaffolding, custom slash commands, and the BioSherpa guide.  This potentially makes it the first open-source bioinformatics orchestration platform with built-in LLM-assisted contributor workflows.

The result is a platform that is modular, extensible, and uniquely AI-augmented, well-positioned for long-term ecosystem growth. Built on a self-registering action system and YAML-based workflow definitions, it features a modern src-layout architecture with comprehensive test coverage and 2025 standardizations for production reliability.

🎯 **Key Features**
-------------------

* **Self-registering action system** - Actions automatically register via decorators
* **Type-safe parameters** - Pydantic models provide validation and IDE support  
* **YAML workflow definition** - Declarative strategies without coding
* **Real-time progress tracking** - SSE events for long-running jobs
* **Extensible architecture** - Easy to add new actions and entity types
* **AI-ready design** - Built for integration with Claude Code and LLM assistance

🚀 **Quick Start**
------------------

.. code-block:: bash

   # Install with Poetry
   poetry install --with dev,docs,api
   poetry shell
   
   # Start the API server
   cd biomapper-api && poetry run uvicorn app.main:app --reload --port 8000
   
   # Or use the CLI (from root directory)
   poetry run biomapper --help
   poetry run biomapper health

.. code-block:: python

   # Python client usage
   from src.client.client_v2 import BiomapperClient
   
   client = BiomapperClient(base_url="http://localhost:8000")
   result = client.run("test_metabolite_simple", parameters={
       "input_file": "/data/metabolites.csv",
       "output_dir": "/tmp/results"
   })
   print(f"Success: {result.success}")  # StrategyResult object

🏗️ **Architecture**
--------------------

BioMapper follows a modern microservices architecture with clear separation of concerns:

**Core Design:**

* **YAML Strategies** - Declarative configs defining pipelines of actions
* **Action Registry** - Self-registering via decorators; plug-and-play extensibility
* **UniversalContext** - Normalizes state access across heterogeneous action types
* **Pydantic Models (v2)** - Typed parameter models per action category
* **Progressive Mapping** - Iterative enrichment stages (65% → 80% coverage)

**Comparison to Known Patterns:**

* **Similar to:** Nextflow & Snakemake (declarative pipelines), Kedro (typed configs + reproducibility), Dagster (observability and orchestration)
* **Different from:** Heavy orchestrators (Airflow, Beam) — BioMapper is lighter, service/API-first, domain-agnostic, and tailored for interactive workflows
* **Unique:** Combines API service with strategy-based pipeline engine; domain-specific operations first (bio), but extensible beyond

**Three-Layer Design:**

1. **Client Layer** - Python client library (``src.client.client_v2``) for programmatic access
2. **API Layer** - FastAPI service with SQLite job persistence and SSE progress tracking
3. **Core Layer** - Self-registering actions with strategy execution engine

The system uses a **registry pattern** where actions self-register via ``@register_action`` decorators, a **strategy pattern** for YAML-based workflow configuration, and a **pipeline pattern** for data flow through shared execution context. Actions are organized by biological entity (proteins, metabolites, chemistry) and automatically discovered at runtime.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started
   
   guides/quickstart
   guides/installation

.. toctree::
   :maxdepth: 2
   :caption: User Guide
   
   usage
   configuration
   api_client

.. toctree::
   :maxdepth: 2
   :caption: Actions Reference
   
   actions/index
   actions/hmdb_vector_match
   actions/sync_to_google_drive
   actions/parse_composite_identifiers
   actions/metabolite_fuzzy_string_match
   actions/metabolite_rampdb_bridge
   actions/progressive_semantic_match

.. toctree::
   :maxdepth: 2
   :caption: Workflows
   
   workflows/metabolomics_pipeline

.. toctree::
   :maxdepth: 2
   :caption: Integrations
   
   integrations/google_drive
   integrations/rampdb_integration

.. toctree::
   :maxdepth: 2
   :caption: Examples
   
   examples/real_world_cases

.. toctree::
   :maxdepth: 2
   :caption: Performance
   
   performance/optimization_guide

.. toctree::
   :maxdepth: 2
   :caption: API Reference
   
   api/index
   architecture/index

.. toctree::
   :maxdepth: 1
   :caption: Development
   
   development/creating_actions
   development/testing
   development/contributing

.. toctree::
   :maxdepth: 2
   :caption: AI-Assisted Development
   
   ai_assistance/index
   ai_assistance/framework_triad
   ai_assistance/framework_triggering
   ai_assistance/slash_commands
   ai_assistance/examples

🤖 **AI Integration**
----------------------

BioMapper features an AI-native developer experience that sets it apart from traditional orchestration frameworks:

**Current AI Features:**

* **CLAUDE.md** - Project "constitution" providing role-defining guidance for AI agents
* **.claude/ folder** - Structured agent configs and scaffolding
* **BiOMapper Framework Triad** - Three automatic isolation frameworks for safe development
* **Hook System** - Automatic TDD enforcement and validation
* **Type-safe actions** - Enable better code completion and error detection
* **Self-documenting** - Pydantic models include descriptions

**BiOMapper Framework Triad:**

The system includes three complementary frameworks that automatically activate based on natural language:

* **🔒 Surgical:** Fix internal action logic while preserving all external interfaces. Automatically activates when you describe counting, calculation, or statistics issues.
* **🔄 Circuitous:** Repair pipeline orchestration and parameter flow. Automatically activates when you describe parameters not passing between steps or substitution failures.
* **🔗 Interstitial:** Ensure 100% backward compatibility during interface evolution. Automatically activates when you describe compatibility issues or parameter changes breaking existing code.

**Automatic Activation:** You don't need to know framework names - just describe the problem naturally and the appropriate framework activates automatically. See :doc:`ai_assistance/framework_triggering` for details on how this works.

**Development Discipline:** Separate from the frameworks, a hook system enforces:

* **TDD Requirements** - Tests must exist before implementation
* **Parameter Validation** - All ``${parameters.x}`` must resolve
* **Import Verification** - All modules must load cleanly
* **Quality Gates** - Blocks premature success declarations

**Comparisons:**

* **Copilot/Cody:** Offer IDE assistance but don't ship with per-project scaffolding
* **Claude-Orchestrator/Flow frameworks:** Orchestrate multiple Claude agents, but not tied to strategy orchestration
* **BioMapper:** First to embed LLM-native scaffolding inside an orchestration framework repo, making the AI "part of the project contract"

📚 **Available Actions**
------------------------

BioMapper includes actions across multiple categories:

* **Data Operations**: Load, merge, filter, export, transform
* **Protein Actions**: UniProt extraction, accession normalization, multi-bridge resolution
* **Metabolite Actions**: CTS bridge, Nightingale NMR matching, semantic matching, vector matching, API enrichment
* **Chemistry Actions**: LOINC extraction, fuzzy test matching, vendor harmonization
* **Analysis & Reporting**: Set overlap, mapping quality, comprehensive reports
* **Integration Actions**: Google Drive sync with chunked transfer

✅ **2025 Standardizations**
-----------------------------

**Production-Ready Architecture Achieved:**

* **Barebones Architecture**: Client → API → MinimalStrategyService → Self-Registering Actions
* **Comprehensive Test Suite**: 1,217 passing tests with 79.69% coverage
* **Type Safety**: Comprehensive Pydantic v2 migration
* **Standards Compliance**: All 10 biomapper 2025 standardizations implemented
* **Biological Data Testing**: Real-world protein, metabolite, and chemistry data patterns

**Architectural Strengths:**

* **Clean modularity** (strategy vs action vs context)
* **Low barrier for extension** (just register a new action)
* **Declarative configuration** approachable to non-programmers
* **Pragmatic service orientation** (FastAPI, Poetry, pytest, Pydantic)

**Gaps & Opportunities:**

* No DAG/conditional execution in YAML
* Limited provenance/lineage tracking
* Potential performance bottlenecks at scale (10K–1M records)
* Observability/logging not yet first-class
* Single-agent AI model; opportunity for multi-agent orchestration

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

---

---

Verification Sources
--------------------
*Last verified: 2025-08-22*

This documentation was verified against the following project resources:

- ``/biomapper/README.md`` (Project overview and architectural analysis with 1,217 passing tests)
- ``/biomapper/CLAUDE.md`` (Commands, patterns, and 2025 standardizations)
- ``/biomapper/src/actions/registry.py`` (Self-registering action system implementation)
- ``/biomapper/src/client/client_v2.py`` (BiomapperClient class with correct import path and methods)
- ``/biomapper/src/api/main.py`` (FastAPI server configuration and endpoint routing)
- ``/biomapper/pyproject.toml`` (Project configuration, Python 3.11+ requirement, src-layout packages)