# Example Scripts

This section provides an overview of the example scripts available in the BiomappeR package. These examples demonstrate real-world usage patterns and common workflows.

## Tutorial Examples

Located in `examples/tutorials/`, these step-by-step guides demonstrate complete workflows:

### Basic LLM Mapping
`tutorial_basic_llm_mapping.py` - Demonstrates the basic usage of LLM-based mapping:
- How to initialize and configure the LLM mapper
- Basic term mapping with confidence scores
- Mapping with specific target ontologies

### ChromaDB HMDB OpenAI Integration
`tutorial_chromadb_hmdb_openai.py` - Shows how to combine ChromaDB, HMDB data, and OpenAI:
- Setting up ChromaDB for vector storage
- Processing HMDB compound data
- Using OpenAI for compound mapping

### Metabolite Mapping Workflows
- `tutorial_metabolite_mapping_rag.py` - RAG-based metabolite mapping
- `tutorial_metabolite_mapping_workflow.py` - Complete metabolite mapping pipeline

### Multi-Provider Integration
`tutorial_multi_provider.py` - Demonstrates using multiple mapping providers:
- Combining different mapping strategies
- Handling provider-specific configurations
- Aggregating results from multiple sources

### Protein Mapping
`tutorial_protein.py` - Protein-specific mapping workflows:
- Protein identifier mapping
- Handling protein nomenclature
- Working with protein databases

## Utility Scripts

Located in `examples/utilities/`, these scripts help with common tasks:

### Data Exploration
- `explore_arango_data.py` - Explore and inspect ArangoDB data
- `inspect_chromadb_store.py` - Analyze ChromaDB vector store contents

### Data Loading and Processing
- `load_hmdb_data.py` - Load and process HMDB compound data
- `search_compound_database.py` - Search compounds in the database

### Setup and Verification
- `verify_chromadb_setup.py` - Verify ChromaDB installation and configuration

## Running Examples

Each example can be run directly as a Python script. Before running:

1. Ensure you have installed all required dependencies
2. Set up any necessary environment variables or configuration files
3. Follow the specific setup instructions in each script's documentation

For example, to run the basic LLM mapping tutorial:

```bash
python examples/tutorials/tutorial_basic_llm_mapping.py
```

See the [examples README](../../examples/README.md) for more detailed information about prerequisites and setup.
