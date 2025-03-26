"""Command-line interface for the mapping cache."""

import argparse
import datetime
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..db.session import DatabaseManager, get_db_manager
from .manager import CacheManager
from ..transitivity.builder import TransitivityBuilder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def init_cache(args: argparse.Namespace) -> None:
    """Initialize the mapping cache database.
    
    Args:
        args: Command-line arguments
    """
    data_dir = args.data_dir or os.path.join(str(Path.home()), ".biomapper", "data")
    
    # Create directories if they don't exist
    os.makedirs(data_dir, exist_ok=True)
    
    # Initialize database
    db_manager = get_db_manager(data_dir=data_dir, echo=args.verbose)
    try:
        db_manager.init_db(drop_all=args.reset)
        
        if args.reset:
            logger.info(f"Mapping cache database reset at {data_dir}")
        else:
            logger.info(f"Mapping cache database initialized at {data_dir}")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        sys.exit(1)


def add_mapping(args: argparse.Namespace) -> None:
    """Add a new mapping to the cache.
    
    Args:
        args: Command-line arguments
    """
    cache_manager = CacheManager()
    
    # Parse metadata if provided
    metadata = None
    if args.metadata:
        try:
            metadata = json.loads(args.metadata)
        except json.JSONDecodeError:
            logger.error("Invalid JSON format for metadata")
            sys.exit(1)
    
    # Add mapping
    try:
        result = cache_manager.add_mapping(
            source_id=args.source_id,
            source_type=args.source_type,
            target_id=args.target_id,
            target_type=args.target_type,
            confidence=args.confidence,
            mapping_source=args.source,
            bidirectional=not args.no_bidirectional
        )
        
        if args.verbose:
            print(json.dumps(result, indent=2))
        else:
            print(f"Added mapping: {args.source_type}:{args.source_id} -> {args.target_type}:{args.target_id}")
    except Exception as e:
        logger.error(f"Error adding mapping: {e}")
        sys.exit(1)


def lookup_mapping(args: argparse.Namespace) -> None:
    """Look up mappings from the cache.
    
    Args:
        args: Command-line arguments
    """
    cache_manager = CacheManager()
    
    try:
        if args.bidirectional:
            results = cache_manager.bidirectional_lookup(
                entity_id=args.id,
                entity_type=args.type,
                target_type=args.target_type,
                include_derived=not args.direct_only,
                min_confidence=args.min_confidence
            )
        else:
            results = cache_manager.lookup(
                source_id=args.id,
                source_type=args.type,
                target_type=args.target_type,
                include_derived=not args.direct_only,
                min_confidence=args.min_confidence
            )
        
        if args.format == "json":
            print(json.dumps(results, indent=2))
        else:
            print(f"Found {len(results)} mappings for {args.type}:{args.id}")
            for i, mapping in enumerate(results, 1):
                source = f"{mapping['source_type']}:{mapping['source_id']}"
                target = f"{mapping['target_type']}:{mapping['target_id']}"
                conf = f"{mapping['confidence']:.2f}"
                derived = " (derived)" if mapping.get("is_derived") else ""
                print(f"{i}. {source} -> {target} [{conf}]{derived}")
    except Exception as e:
        logger.error(f"Error looking up mappings: {e}")
        sys.exit(1)


def build_transitive(args: argparse.Namespace) -> None:
    """Build transitive relationships.
    
    Args:
        args: Command-line arguments
    """
    cache_manager = CacheManager()
    builder = TransitivityBuilder(
        cache_manager=cache_manager,
        min_confidence=args.min_confidence,
        max_chain_length=args.max_chain_length,
        confidence_decay=args.confidence_decay
    )
    
    try:
        print("Building transitive relationships...")
        count = builder.build_transitive_mappings()
        
        if args.extended:
            print("Building extended transitive relationships...")
            extended_count = builder.build_extended_transitive_mappings()
            print(f"Created {count} direct and {extended_count} extended transitive mappings")
        else:
            print(f"Created {count} transitive mappings")
    except Exception as e:
        logger.error(f"Error building transitive relationships: {e}")
        sys.exit(1)


def clean_expired(args: argparse.Namespace) -> None:
    """Clean expired mappings from the cache.
    
    Args:
        args: Command-line arguments
    """
    cache_manager = CacheManager()
    
    try:
        count = cache_manager.delete_expired_mappings()
        print(f"Deleted {count} expired mappings")
    except Exception as e:
        logger.error(f"Error cleaning expired mappings: {e}")
        sys.exit(1)


def show_stats(args: argparse.Namespace) -> None:
    """Show cache statistics.
    
    Args:
        args: Command-line arguments
    """
    cache_manager = CacheManager()
    
    # Parse dates if provided
    start_date = None
    if args.start_date:
        try:
            start_date = datetime.datetime.strptime(args.start_date, "%Y-%m-%d").date()
        except ValueError:
            logger.error("Invalid start date format (use YYYY-MM-DD)")
            sys.exit(1)
    
    end_date = None
    if args.end_date:
        try:
            end_date = datetime.datetime.strptime(args.end_date, "%Y-%m-%d").date()
        except ValueError:
            logger.error("Invalid end date format (use YYYY-MM-DD)")
            sys.exit(1)
    
    try:
        stats = cache_manager.get_cache_stats(start_date, end_date)
        
        if args.format == "json":
            print(json.dumps(stats, indent=2))
        else:
            print(f"Cache statistics ({len(stats)} days):")
            for day_stats in stats:
                date = day_stats["date"]
                hit_ratio = day_stats["hit_ratio"] * 100
                hits = day_stats["hits"]
                misses = day_stats["misses"]
                print(f"{date}: Hit ratio: {hit_ratio:.1f}% ({hits} hits, {misses} misses)")
                
                if args.verbose:
                    direct = day_stats["direct_lookups"]
                    derived = day_stats["derived_lookups"]
                    api_calls = day_stats["api_calls"]
                    transitive = day_stats["transitive_derivations"]
                    print(f"  Direct: {direct}, Derived: {derived}, API calls: {api_calls}, Transitive: {transitive}")
    except Exception as e:
        logger.error(f"Error showing cache statistics: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point for the mapping cache CLI."""
    parser = argparse.ArgumentParser(description="Biomapper mapping cache management")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Initialize cache command
    init_parser = subparsers.add_parser("init", help="Initialize the mapping cache")
    init_parser.add_argument(
        "--data-dir", 
        help="Directory for storing cache data"
    )
    init_parser.add_argument(
        "--reset", 
        action="store_true", 
        help="Reset the cache (delete all data)"
    )
    init_parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Print verbose output"
    )
    
    # Add mapping command
    add_parser = subparsers.add_parser("add", help="Add a mapping to the cache")
    add_parser.add_argument(
        "--source-id", 
        required=True, 
        help="Source entity ID"
    )
    add_parser.add_argument(
        "--source-type", 
        required=True, 
        help="Source entity type"
    )
    add_parser.add_argument(
        "--target-id", 
        required=True, 
        help="Target entity ID"
    )
    add_parser.add_argument(
        "--target-type", 
        required=True, 
        help="Target entity type"
    )
    add_parser.add_argument(
        "--confidence", 
        type=float, 
        default=1.0, 
        help="Mapping confidence (0-1)"
    )
    add_parser.add_argument(
        "--source", 
        default="manual", 
        help="Mapping source (e.g., manual, api, ramp)"
    )
    add_parser.add_argument(
        "--metadata", 
        help="JSON metadata for the mapping"
    )
    add_parser.add_argument(
        "--no-bidirectional", 
        action="store_true", 
        help="Don't create bidirectional mapping"
    )
    add_parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Print verbose output"
    )
    
    # Lookup command
    lookup_parser = subparsers.add_parser("lookup", help="Look up mappings from the cache")
    lookup_parser.add_argument(
        "--id", 
        required=True, 
        help="Entity ID to look up"
    )
    lookup_parser.add_argument(
        "--type", 
        required=True, 
        help="Entity type to look up"
    )
    lookup_parser.add_argument(
        "--target-type", 
        help="Target entity type filter"
    )
    lookup_parser.add_argument(
        "--direct-only", 
        action="store_true", 
        help="Only include direct mappings (no derived)"
    )
    lookup_parser.add_argument(
        "--bidirectional", 
        action="store_true", 
        help="Look up mappings in both directions"
    )
    lookup_parser.add_argument(
        "--min-confidence", 
        type=float, 
        default=0.7, 
        help="Minimum confidence threshold"
    )
    lookup_parser.add_argument(
        "--format", 
        choices=["text", "json"], 
        default="text", 
        help="Output format"
    )
    
    # Build transitive command
    transitive_parser = subparsers.add_parser(
        "build-transitive", 
        help="Build transitive relationships"
    )
    transitive_parser.add_argument(
        "--min-confidence", 
        type=float, 
        default=0.5, 
        help="Minimum confidence for derived mappings"
    )
    transitive_parser.add_argument(
        "--max-chain-length", 
        type=int, 
        default=3, 
        help="Maximum length of derivation chains"
    )
    transitive_parser.add_argument(
        "--confidence-decay", 
        type=float, 
        default=0.9, 
        help="Factor to reduce confidence with each step"
    )
    transitive_parser.add_argument(
        "--extended", 
        action="store_true", 
        help="Build extended transitive relationships (chains > 2)"
    )
    
    # Clean expired command
    clean_parser = subparsers.add_parser(
        "clean-expired", 
        help="Clean expired mappings from the cache"
    )
    
    # Show stats command
    stats_parser = subparsers.add_parser("stats", help="Show cache statistics")
    stats_parser.add_argument(
        "--start-date", 
        help="Start date (YYYY-MM-DD)"
    )
    stats_parser.add_argument(
        "--end-date", 
        help="End date (YYYY-MM-DD)"
    )
    stats_parser.add_argument(
        "--format", 
        choices=["text", "json"], 
        default="text", 
        help="Output format"
    )
    stats_parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Print verbose output"
    )
    
    # Parse arguments and execute commands
    args = parser.parse_args()
    
    if args.command == "init":
        init_cache(args)
    elif args.command == "add":
        add_mapping(args)
    elif args.command == "lookup":
        lookup_mapping(args)
    elif args.command == "build-transitive":
        build_transitive(args)
    elif args.command == "clean-expired":
        clean_expired(args)
    elif args.command == "stats":
        show_stats(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
