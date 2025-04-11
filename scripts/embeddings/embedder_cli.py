#!/usr/bin/env python3
"""
Biomapper Embedder CLI.

A command-line interface for the Biomapper Embedder module to process
data, generate embeddings, and perform semantic searches.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("embedder_cli.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Import Biomapper Embedder components
from biomapper.embedder.generators.text_embedder import TextEmbedder
from biomapper.embedder.storage.vector_store import FAISSVectorStore
from biomapper.embedder.pipelines.batch import BatchEmbeddingPipeline
from biomapper.embedder.search.engine import EmbedderSearchEngine
from biomapper.embedder.core.config import default_config


def process_command(args):
    """Process data and generate embeddings."""
    logging.info(f"Processing data from {args.input_file}")
    
    # Initialize components
    embedder = TextEmbedder(
        model_name=args.model,
        device=args.device
    )
    
    vector_store = FAISSVectorStore(
        index_path=args.index_path,
        metadata_path=args.metadata_path
    )
    
    pipeline = BatchEmbeddingPipeline(
        embedder=embedder,
        vector_store=vector_store,
        batch_size=args.batch_size
    )
    
    # Process data
    stats = pipeline.process_from_jsonl(
        jsonl_path=args.input_file,
        max_items=args.max_items
    )
    
    # Print stats
    print("\nProcessing Stats:")
    print(f"- Processed items: {stats['processed']}")
    print(f"- Successful: {stats['successful']}")
    print(f"- Failed: {stats['failed']}")
    print(f"- Batches: {stats['batches']}")
    if 'duration' in stats:
        print(f"- Duration: {stats['duration']:.2f} seconds")
    if 'items_per_second' in stats:
        print(f"- Processing rate: {stats['items_per_second']:.2f} items/second")
    
    print(f"\nEmbeddings saved to: {args.index_path}")
    print(f"Metadata saved to: {args.metadata_path}")


def search_command(args):
    """Search for similar items."""
    logging.info(f"Searching with query: {args.query}")
    
    # Initialize components
    embedder = TextEmbedder(
        model_name=args.model,
        device=args.device
    )
    
    vector_store = FAISSVectorStore(
        index_path=args.index_path,
        metadata_path=args.metadata_path
    )
    
    search_engine = EmbedderSearchEngine(
        embedder=embedder,
        vector_store=vector_store
    )
    
    # Perform search
    results = search_engine.search(
        query=args.query,
        k=args.k,
        filter_types=args.filter_types.split(",") if args.filter_types else None
    )
    
    # Print results
    if args.output_format == 'json':
        print(json.dumps(results, indent=2))
    else:
        formatted_results = search_engine.format_results(
            results=results,
            format_type=args.output_format
        )
        print(formatted_results)


def info_command(args):
    """Display information about the index."""
    logging.info(f"Getting info for index: {args.index_path}")
    
    # Initialize vector store
    vector_store = FAISSVectorStore(
        index_path=args.index_path,
        metadata_path=args.metadata_path
    )
    
    # Get basic info
    total_vectors = vector_store.get_total_count()
    print(f"\nIndex Information:")
    print(f"- Total vectors: {total_vectors}")
    print(f"- Index path: {args.index_path}")
    print(f"- Metadata path: {args.metadata_path}")
    
    # Analyze metadata if available
    if hasattr(vector_store, 'metadata') and vector_store.metadata:
        # Count by type
        type_counts = {}
        sources = set()
        
        for item_id, metadata in vector_store.metadata.items():
            item_type = metadata.get('type', 'unknown')
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
            
            source = metadata.get('source')
            if source:
                sources.add(source)
        
        print("\nContent breakdown:")
        for item_type, count in type_counts.items():
            print(f"- {item_type}: {count} items")
        
        print("\nData sources:")
        for source in sources:
            print(f"- {source}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Biomapper Embedder CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Default paths
    data_dir = os.path.expanduser("~/.biomapper/embeddings")
    os.makedirs(data_dir, exist_ok=True)
    
    default_index_path = os.path.join(data_dir, "embeddings.index")
    default_metadata_path = os.path.join(data_dir, "embeddings_metadata.json")
    
    # Process command
    process_parser = subparsers.add_parser("process", help="Process data and generate embeddings")
    process_parser.add_argument("--input-file", required=True, help="Input JSONL file to process")
    process_parser.add_argument("--index-path", default=default_index_path, help="Path to save the FAISS index")
    process_parser.add_argument("--metadata-path", default=default_metadata_path, help="Path to save metadata")
    process_parser.add_argument("--model", default=default_config.embedding_model, help="Embedding model name")
    process_parser.add_argument("--batch-size", type=int, default=32, help="Batch size for processing")
    process_parser.add_argument("--max-items", type=int, help="Maximum items to process")
    process_parser.add_argument("--device", help="Device to use (cpu, cuda)")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for similar items")
    search_parser.add_argument("--query", required=True, help="Search query")
    search_parser.add_argument("--index-path", default=default_index_path, help="Path to the FAISS index")
    search_parser.add_argument("--metadata-path", default=default_metadata_path, help="Path to metadata")
    search_parser.add_argument("--model", default=default_config.embedding_model, help="Embedding model name")
    search_parser.add_argument("--k", type=int, default=5, help="Number of results to return")
    search_parser.add_argument("--filter-types", help="Comma-separated list of types to filter by")
    search_parser.add_argument("--output-format", choices=["text", "json", "markdown"], default="text", 
                              help="Output format")
    search_parser.add_argument("--device", help="Device to use (cpu, cuda)")
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Display information about the index")
    info_parser.add_argument("--index-path", default=default_index_path, help="Path to the FAISS index")
    info_parser.add_argument("--metadata-path", default=default_metadata_path, help="Path to metadata")
    
    args = parser.parse_args()
    
    if args.command == "process":
        process_command(args)
    elif args.command == "search":
        search_command(args)
    elif args.command == "info":
        info_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
