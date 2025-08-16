#!/bin/bash
# Generated biomapper cleanup script
# Review carefully before executing!

set -e  # Exit on error

echo '🧹 Biomapper Cleanup Script'
echo '=========================='

echo 'Removing HIGH CONFIDENCE files only...'

echo 'Removing SAFE confidence files...'

rm -f 'archive/deprecated_code/pipelines/compounds/__init__.py'
rm -f 'archive/deprecated_code/pipelines/compounds/rag_compound_mapper.py'
rm -f 'archive/deprecated_code/pipelines/compounds/compound_mapper.py'
rm -f 'archive/deprecated_code/pipelines/compounds/compound_pipeline.py'
rm -f 'archive/deprecated_code/pipelines/proteins/__init__.py'
rm -f 'archive/deprecated_code/pipelines/proteins/protein_mapper.py'
rm -f 'archive/deprecated_code/pipelines/proteins/protein_pipeline.py'
rm -f 'archive/deprecated_code/mapping/__init__.py'
rm -f 'archive/deprecated_code/mapping/metabolite_mapper.py'
rm -f 'archive/deprecated_code/mapping/extractors.py'
rm -f 'archive/deprecated_code/mapping/result_processor.py'
rm -f 'archive/deprecated_code/mapping/resources/clients/unichem_client.py'
rm -f 'archive/deprecated_code/mapping/embeddings/__init__.py'
rm -f 'archive/deprecated_code/mapping/clients/chebi_client.py'
rm -f 'archive/deprecated_code/mapping/clients/uniprot_focused_mapper.py'
rm -f 'archive/deprecated_code/mapping/rag/embedder.py'
rm -f 'archive/deprecated_code/mapping/rag/prompts.py'
rm -f 'archive/deprecated_code/mapping/rag/compound_mapper.py'
rm -f 'archive/deprecated_code/mapping/adapters/spoke_adapter.py'
rm -f 'archive/deprecated_code/mapping/adapters/cache_adapter.py'
rm -f 'biomapper-api/biomapper_mock/core/__init__.py'
rm -f 'biomapper-api/biomapper_mock/core/models/__init__.py'
rm -f 'biomapper-api/biomapper_mock/mapping/__init__.py'
rm -f 'biomapper-api/biomapper_mock/mapping/relationships/__init__.py'
rm -f 'scripts/__init__.py'
rm -f 'scripts/setup_and_configuration/__init__.py'
rm -f 'scripts/main_pipelines/__init__.py'

echo 'Cleaning __pycache__ directories...'
find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

echo '✅ Cleanup complete!'
