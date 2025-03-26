#!/usr/bin/env python
"""Initialization and management script for Biomapper's SQLite mapping cache."""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from biomapper.cache.config import CacheConfig, get_default_config
from biomapper.db.maintenance import DatabaseMaintenance, run_maintenance
from biomapper.db.session import get_db_manager


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def init_cache(args):
    """Initialize the cache database.
    
    Args:
        args: Command line arguments
    """
    # Load or create configuration
    if args.config:
        config = CacheConfig.load(args.config)
        logger.info(f"Loaded configuration from {args.config}")
    else:
        config = get_default_config()
        logger.info("Using default configuration")
    
    # Override data directory if specified
    if args.data_dir:
        config.data_dir = args.data_dir
    
    # Ensure data directory exists
    os.makedirs(config.data_dir, exist_ok=True)
    logger.info(f"Using data directory: {config.data_dir}")
    
    # Initialize database
    db_manager = get_db_manager(data_dir=config.data_dir, db_name=config.db_name)
    db_manager.init_db(drop_all=args.reset)
    
    logger.info(
        f"Database initialized at {os.path.join(config.data_dir, config.db_name)}" +
        (" (existing tables were dropped)" if args.reset else "")
    )
    
    # Save configuration if requested
    if args.save_config:
        config_path = config.save()
        logger.info(f"Configuration saved to {config_path}")


def backup_cache(args):
    """Create a backup of the cache database.
    
    Args:
        args: Command line arguments
    """
    maintenance = DatabaseMaintenance(
        data_dir=args.data_dir,
        backup_dir=args.backup_dir
    )
    
    backup_path = maintenance.create_backup(compress=not args.no_compress)
    
    if backup_path:
        logger.info(f"Backup created at {backup_path}")
    else:
        logger.error("Failed to create backup")
        sys.exit(1)


def restore_cache(args):
    """Restore the cache database from a backup.
    
    Args:
        args: Command line arguments
    """
    maintenance = DatabaseMaintenance(
        data_dir=args.data_dir,
        backup_dir=args.backup_dir
    )
    
    success = maintenance.restore_backup(args.backup_file)
    
    if success:
        logger.info(f"Database restored from {args.backup_file}")
    else:
        logger.error(f"Failed to restore from {args.backup_file}")
        sys.exit(1)


def list_backups(args):
    """List available database backups.
    
    Args:
        args: Command line arguments
    """
    maintenance = DatabaseMaintenance(
        data_dir=args.data_dir,
        backup_dir=args.backup_dir
    )
    
    backups = maintenance.list_backups()
    
    if not backups:
        logger.info("No backups found")
        return
    
    logger.info(f"Found {len(backups)} backups:")
    
    for i, backup in enumerate(backups):
        compressed = " (compressed)" if backup["compressed"] else ""
        logger.info(
            f"{i+1}. {backup['filename']} - "
            f"{backup['size_mb']}MB - "
            f"{backup['created']}{compressed}"
        )


def maintain_cache(args):
    """Run maintenance tasks on the cache database.
    
    Args:
        args: Command line arguments
    """
    results = run_maintenance(
        data_dir=args.data_dir,
        vacuum=not args.no_vacuum,
        backup=not args.no_backup,
        analyze=True
    )
    
    if results["success"]:
        logger.info("Maintenance completed successfully")
    else:
        logger.warning("Maintenance completed with errors")
    
    for action in results["actions"]:
        logger.info(f"- {action}")
    
    for error in results["errors"]:
        logger.error(f"- {error}")
    
    if results["stats"]:
        stats = results["stats"]
        logger.info(f"Database size: {stats['file_size_mb']} MB")
        logger.info(f"Entity mappings: {stats['tables']['entity_mappings']}")
        logger.info(f"Derived mappings: {stats['tables']['derived_mappings']}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Biomapper SQLite Mapping Cache Management Tool"
    )
    
    # Common arguments
    parser.add_argument(
        "--data-dir",
        help="Data directory for cache files",
        default=None
    )
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        help="Command to execute"
    )
    
    # Initialize command
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize the cache database"
    )
    init_parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the database if it already exists"
    )
    init_parser.add_argument(
        "--config",
        help="Path to configuration file"
    )
    init_parser.add_argument(
        "--save-config",
        action="store_true",
        help="Save configuration to file"
    )
    init_parser.set_defaults(func=init_cache)
    
    # Backup command
    backup_parser = subparsers.add_parser(
        "backup",
        help="Create a backup of the database"
    )
    backup_parser.add_argument(
        "--backup-dir",
        help="Directory for storing backups"
    )
    backup_parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Don't compress the backup file"
    )
    backup_parser.set_defaults(func=backup_cache)
    
    # Restore command
    restore_parser = subparsers.add_parser(
        "restore",
        help="Restore from a backup"
    )
    restore_parser.add_argument(
        "backup_file",
        help="Path to backup file"
    )
    restore_parser.add_argument(
        "--backup-dir",
        help="Directory containing backups"
    )
    restore_parser.set_defaults(func=restore_cache)
    
    # List backups command
    list_parser = subparsers.add_parser(
        "list-backups",
        help="List available backups"
    )
    list_parser.add_argument(
        "--backup-dir",
        help="Directory containing backups"
    )
    list_parser.set_defaults(func=list_backups)
    
    # Maintenance command
    maintain_parser = subparsers.add_parser(
        "maintain",
        help="Run maintenance tasks"
    )
    maintain_parser.add_argument(
        "--no-vacuum",
        action="store_true",
        help="Skip database vacuum"
    )
    maintain_parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup during maintenance"
    )
    maintain_parser.set_defaults(func=maintain_cache)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute command
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
