YAML Strategy System
====================

The strategy system enables declarative workflow definition through YAML configurations, providing BioMapper's configuration-driven approach to biological data harmonization.

Strategy Structure
------------------

Every strategy follows this comprehensive pattern:

.. code-block:: yaml

    name: "strategy_name"
    description: "Clear description of what this strategy accomplishes"
    
    parameters:
      input_file: "${DATA_DIR}/input.tsv"
      output_dir: "${OUTPUT_DIR:-/tmp/results}"
      threshold: 0.85
    
    metadata:
      version: "1.0.0"
      author: "researcher@institution.edu"
      tags: ["proteins", "uniprot", "harmonization"]
    
    steps:
      - name: load_data
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "${parameters.input_file}"
            identifier_column: "protein_id"
            output_key: "raw_proteins"
      
      - name: normalize
        action:
          type: PROTEIN_NORMALIZE_ACCESSIONS
          params:
            input_key: "raw_proteins"
            output_key: "normalized_proteins"
      
      - name: export
        action:
          type: EXPORT_DATASET_V2
          params:
            input_key: "normalized_proteins"
            output_file: "${parameters.output_dir}/results.csv"
            format: "csv"

Execution Model
---------------

**Sequential Processing**
  Steps execute in the order defined in the YAML file, with each step building on previous results.

**Shared Execution Context**
  A ``Dict[str, Any]`` is passed between all steps containing:
  
  * ``datasets`` - Named datasets from action outputs
  * ``current_identifiers`` - Active identifier set being processed
  * ``statistics`` - Accumulated metrics and counts
  * ``output_files`` - Paths to generated files
  * ``metadata`` - Strategy metadata and parameters

**Key-Value Storage Pattern**
  Each action stores results using ``output_key`` parameters, enabling downstream actions to reference data via ``input_key``.

**Automatic Tracking**
  Execution statistics, timing information, and checkpoints are automatically collected for recovery and monitoring.

**Variable Substitution**
  Supports multiple substitution patterns:
  
  * ``${parameters.key}`` - Access strategy parameters
  * ``${env.VAR_NAME}`` - Environment variables
  * ``${VAR_NAME}`` - Shorthand for environment variables
  * ``${metadata.field}`` - Access metadata fields
  * ``${VAR:-default}`` - Default values if variable not set

Common Strategy Patterns
------------------------

**Entity Harmonization**
  Load identifiers → Normalize → Enrich → Export

**Multi-Source Integration**
  Load multiple datasets → Merge → Deduplicate → Analyze overlap

**Quality Assessment**
  Load data → Validate → Calculate metrics → Generate report

**API Enrichment**
  Load identifiers → Call external APIs → Combine results → Export

See ``configs/strategies/`` for production examples and the :doc:`../configuration` guide for best practices.

Strategy Loading and Discovery
-------------------------------

The ``MinimalStrategyService`` loads strategies from multiple sources:

1. **Config Directory** (``configs/strategies/``)
   Automatically discovered at startup, organized by entity type:
   
   * ``experimental/`` - Development and testing strategies
   * ``production/`` - Validated production workflows
   * ``templates/`` - Reusable strategy templates

2. **Direct File Paths**
   Absolute paths specified in API calls or client requests

3. **YAML String Content**
   Strategy definitions passed directly as strings

4. **URL Loading** (planned)
   Remote strategy loading from version-controlled repositories

Integration Points
------------------

**REST API Endpoints**
  * ``POST /strategies/execute`` - Execute strategy with parameters
  * ``GET /strategies/list`` - List available strategies
  * ``GET /strategies/{name}`` - Get strategy definition
  * ``GET /jobs/{job_id}`` - Check job status
  * ``GET /jobs/{job_id}/stream`` - SSE progress stream

**Python Client Library**
  .. code-block:: python
  
      from biomapper_client import BiomapperClient
      
      client = BiomapperClient()
      result = client.run("strategy_name", parameters={
          "input_file": "/data/proteins.csv",
          "threshold": 0.9
      })

**CLI Tools**
  .. code-block:: bash
  
      poetry run python scripts/run_strategy.py --strategy my_strategy
      poetry run biomapper execute --strategy production/protein_harmonization

Benefits
--------

* **Version Control**: Plain text YAML files work with Git
* **Reproducibility**: Identical YAML + data produces identical results
* **Collaboration**: Non-programmers can create and modify workflows
* **Testing**: Simple to create test strategies with mock data
* **Documentation**: Self-documenting with descriptions and metadata
* **Modularity**: Strategies can reference and build on each other
* **Portability**: YAML strategies work across environments
* **Validation**: Schema validation ensures correctness before execution

---

Verification Sources
--------------------
*Last verified: 2025-08-13*

This documentation was verified against the following project resources:

* ``biomapper/core/services/strategy_service_v2_minimal.py`` (Strategy loader)
* ``configs/strategies/`` (Example strategy files)
* ``biomapper-api/app/api/strategies.py`` (API endpoints)
* ``biomapper_client/client_v2.py`` (Client integration)
* ``README.md`` (Strategy examples)
* ``CLAUDE.md`` (Variable substitution patterns)