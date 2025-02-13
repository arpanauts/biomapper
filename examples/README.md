# BiomappeR Examples

This directory contains examples and tutorials demonstrating how to use the BiomappeR package. The examples are organized into two main categories:

## Tutorials

Located in `tutorials/`, these are step-by-step guides demonstrating complete workflows using BiomappeR. Each tutorial shows how to combine different components of the package to solve specific use cases.

- `tutorial_basic_llm_mapping.py`: Demonstrates basic usage of the LLM mapper for term mapping
- `tutorial_chromadb_hmdb_openai.py`: Shows how to use ChromaDB, HMDB data, and OpenAI for compound mapping

## Utilities

Located in `utilities/`, these are helper scripts for exploring data, verifying setups, and performing common operations.

- `explore_arango_data.py`: Explore and inspect ArangoDB data
- `inspect_chromadb_store.py`: Inspect and analyze ChromaDB vector store contents
- `load_hmdb_data.py`: Load and process HMDB compound data
- `search_compound_database.py`: Search compounds in the database
- `verify_chromadb_setup.py`: Verify ChromaDB installation and configuration

## Prerequisites

Before running these examples, make sure you have:

1. Installed BiomappeR and its dependencies
2. Set up necessary environment variables (see individual examples for specific requirements)
3. Installed any additional dependencies required by specific examples

## Running Examples

Each example can be run directly as a Python script. For example:

```bash
python examples/tutorials/tutorial_basic_llm_mapping.py
```

See individual script documentation for specific usage instructions and requirements.
