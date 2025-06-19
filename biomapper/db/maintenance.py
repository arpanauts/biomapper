"""Database maintenance utilities for managing the SQLite mapping cache."""

import datetime
import logging
import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any

import sqlalchemy as sa

from biomapper.db.models import EntityMapping, CacheStats, TransitiveJobLog
from biomapper.db.session import get_db_manager


logger = logging.getLogger(__name__)


class DatabaseMaintenance:
    """Maintenance utilities for the SQLite mapping cache."""

    def __init__(
        self,
        data_dir: Optional[str] = None,
        db_name: str = "biomapper.db",
        backup_dir: Optional[str] = None,
    ):
        """Initialize database maintenance utilities.

        Args:
            data_dir: Directory where database files are stored
            db_name: Database filename
            backup_dir: Directory where backups should be stored
        """
        self.db_manager = get_db_manager(data_dir, db_name)

        # Set up backup directory
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        elif data_dir:
            self.backup_dir = Path(data_dir) / "backups"
        else:
            home_dir = Path.home()
            self.backup_dir = home_dir / ".biomapper" / "data" / "backups"

        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)

        # Get database file path
        self.db_file = self.db_manager.db_path

    def initialize_database(self, drop_all: bool = False) -> bool:
        """Initialize the database schema.

        Args:
            drop_all: Whether to drop existing tables

        Returns:
            Success status
        """
        try:
            self.db_manager.init_db(drop_all=drop_all)
            logger.info(
                f"Database initialized at {self.db_file}"
                + (" (dropped existing tables)" if drop_all else "")
            )
            return True
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            return False

    def create_backup(self, compress: bool = True) -> Optional[str]:
        """Create a backup of the current database.

        Args:
            compress: Whether to compress the backup

        Returns:
            Path to backup file if successful, None otherwise
        """
        # Create timestamp for filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"biomapper_backup_{timestamp}.db"

        if compress:
            backup_filename += ".gz"

        backup_path = self.backup_dir / backup_filename

        try:
            # Ensure we can access the database file
            if not os.path.exists(self.db_file):
                logger.error(f"Database file not found at {self.db_file}")
                return None

            # Create backup
            if compress:
                import gzip

                with open(self.db_file, "rb") as f_in:
                    with gzip.open(str(backup_path), "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(self.db_file, backup_path)

            logger.info(f"Database backup created at {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None

    def restore_backup(self, backup_path: str) -> bool:
        """Restore database from a backup file.

        Args:
            backup_path: Path to backup file

        Returns:
            Success status
        """
        backup_path = Path(backup_path)

        if not backup_path.exists():
            logger.error(f"Backup file not found at {backup_path}")
            return False

        # Create backup of current database before restoration
        current_backup = self.create_backup(compress=True)
        if not current_backup:
            logger.warning(
                "Could not create backup of current database before restoration"
            )

        try:
            # Close any open connections
            self.db_manager.close()

            # Handle compressed backups
            if str(backup_path).endswith(".gz"):
                import gzip

                with gzip.open(str(backup_path), "rb") as f_in:
                    with open(self.db_file, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(backup_path, self.db_file)

            logger.info(f"Database restored from {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Error restoring database: {e}")
            return False

    def list_backups(self) -> List[Dict[str, Any]]:
        """List available database backups.

        Returns:
            List of backup information dictionaries
        """
        backups = []

        for file in self.backup_dir.glob("biomapper_backup_*.db*"):
            try:
                # Extract timestamp from filename
                filename = file.name
                timestamp_str = filename.split("_")[2].split(".")[0]

                # Get file stats
                stats = file.stat()

                # Add to list
                backups.append(
                    {
                        "filename": filename,
                        "path": str(file),
                        "size_bytes": stats.st_size,
                        "size_mb": round(stats.st_size / (1024 * 1024), 2),
                        "timestamp": timestamp_str,
                        "created": datetime.datetime.fromtimestamp(
                            stats.st_ctime
                        ).isoformat(),
                        "compressed": filename.endswith(".gz"),
                    }
                )
            except Exception as e:
                logger.warning(f"Error processing backup file {file}: {e}")

        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x["timestamp"], reverse=True)

        return backups

    def vacuum_database(self) -> bool:
        """Vacuum the database to optimize storage and performance.

        Returns:
            Success status
        """
        try:
            # Vacuuming requires direct execution
            engine = self.db_manager.engine

            # Execute vacuum command
            with engine.connect() as conn:
                # Some SQLite connection optimizations
                conn.execute(sa.text("PRAGMA journal_mode = DELETE"))
                conn.execute(sa.text("PRAGMA synchronous = NORMAL"))

                # Execute vacuum
                conn.execute(sa.text("VACUUM"))

            logger.info("Database vacuum completed successfully")
            return True

        except Exception as e:
            logger.error(f"Error vacuuming database: {e}")
            return False

    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the database.

        Returns:
            Dictionary of database statistics
        """
        stats = {
            "file_size_bytes": 0,
            "file_size_mb": 0,
            "tables": {},
            "cache_stats": {},
        }

        try:
            # Get file size
            if os.path.exists(self.db_file):
                file_size = os.path.getsize(self.db_file)
                stats["file_size_bytes"] = file_size
                stats["file_size_mb"] = round(file_size / (1024 * 1024), 2)

            # Get table statistics
            with self.db_manager.create_session() as session:
                # Count records in each table
                stats["tables"]["entity_mappings"] = session.query(
                    EntityMapping
                ).count()
                stats["tables"]["cache_stats"] = session.query(CacheStats).count()
                stats["tables"]["transitive_jobs"] = session.query(
                    TransitiveJobLog
                ).count()

                # Count derived mappings
                derived_count = (
                    session.query(EntityMapping)
                    .filter(EntityMapping.is_derived == True)
                    .count()
                )

                stats["tables"]["derived_mappings"] = derived_count

                # Get latest cache stats
                latest_stats = (
                    session.query(CacheStats).order_by(CacheStats.date.desc()).first()
                )

                if latest_stats:
                    stats["cache_stats"] = {
                        "date": latest_stats.date.isoformat(),
                        "hits": latest_stats.hits,
                        "misses": latest_stats.misses,
                        "hit_ratio": round(latest_stats.hit_ratio, 2)
                        if latest_stats.hit_ratio
                        else 0,
                        "direct_lookups": latest_stats.direct_lookups,
                        "derived_lookups": latest_stats.derived_lookups,
                        "api_calls": latest_stats.api_calls,
                        "transitive_derivations": latest_stats.transitive_derivations,
                    }

        except Exception as e:
            logger.error(f"Error getting database stats: {e}")

        return stats

    def delete_expired_mappings(self) -> int:
        """Delete mappings that have expired.

        Returns:
            Number of deleted mappings
        """
        try:
            now = datetime.datetime.utcnow()

            with self.db_manager.create_session() as session:
                expired = (
                    session.query(EntityMapping)
                    .filter(EntityMapping.expires_at <= now)
                    .all()
                )

                count = len(expired)

                if count > 0:
                    # Delete in batches to avoid memory issues
                    batch_size = 1000
                    for i in range(0, count, batch_size):
                        batch = expired[i : i + batch_size]
                        for mapping in batch:
                            session.delete(mapping)
                        session.commit()

                logger.info(f"Deleted {count} expired mappings")
                return count

        except Exception as e:
            logger.error(f"Error deleting expired mappings: {e}")
            return 0

    def analyze_mapping_distribution(self) -> Dict[str, Dict[str, int]]:
        """Analyze the distribution of mappings by entity type.

        Returns:
            Dictionary with source and target type distributions
        """
        result = {"source_types": {}, "target_types": {}, "bidirectional_pairs": {}}

        try:
            with self.db_manager.create_session() as session:
                # Count source types
                source_counts = (
                    session.query(
                        EntityMapping.source_type, sa.func.count(EntityMapping.id)
                    )
                    .group_by(EntityMapping.source_type)
                    .all()
                )

                for source_type, count in source_counts:
                    result["source_types"][source_type] = count

                # Count target types
                target_counts = (
                    session.query(
                        EntityMapping.target_type, sa.func.count(EntityMapping.id)
                    )
                    .group_by(EntityMapping.target_type)
                    .all()
                )

                for target_type, count in target_counts:
                    result["target_types"][target_type] = count

                # Analyze bidirectional pairs
                type_pairs = (
                    session.query(
                        EntityMapping.source_type,
                        EntityMapping.target_type,
                        sa.func.count(EntityMapping.id),
                    )
                    .group_by(EntityMapping.source_type, EntityMapping.target_type)
                    .all()
                )

                for source_type, target_type, count in type_pairs:
                    # Create a standardized key for the pair (sorted alphabetically)
                    pair_key = f"{min(source_type, target_type)}-{max(source_type, target_type)}"

                    if pair_key not in result["bidirectional_pairs"]:
                        result["bidirectional_pairs"][pair_key] = 0

                    result["bidirectional_pairs"][pair_key] += count

        except Exception as e:
            logger.error(f"Error analyzing mapping distribution: {e}")

        return result


def run_maintenance(
    data_dir: Optional[str] = None,
    vacuum: bool = True,
    backup: bool = True,
    analyze: bool = True,
) -> Dict[str, Any]:
    """Run standard database maintenance tasks.

    Args:
        data_dir: Optional data directory path
        vacuum: Whether to vacuum the database
        backup: Whether to create a backup
        analyze: Whether to analyze the database

    Returns:
        Dictionary with maintenance results
    """
    results = {
        "success": True,
        "start_time": datetime.datetime.now().isoformat(),
        "actions": [],
        "errors": [],
        "stats": None,
        "backup_path": None,
    }

    try:
        maintenance = DatabaseMaintenance(data_dir=data_dir)

        # Delete expired mappings
        expired_count = maintenance.delete_expired_mappings()
        results["actions"].append(f"Deleted {expired_count} expired mappings")

        # Vacuum database if requested
        if vacuum:
            if maintenance.vacuum_database():
                results["actions"].append("Database vacuum completed")
            else:
                results["errors"].append("Database vacuum failed")
                results["success"] = False

        # Create backup if requested
        if backup:
            backup_path = maintenance.create_backup(compress=True)
            if backup_path:
                results["actions"].append(f"Created database backup at {backup_path}")
                results["backup_path"] = backup_path
            else:
                results["errors"].append("Database backup failed")
                results["success"] = False

        # Get database statistics if requested
        if analyze:
            stats = maintenance.get_database_stats()
            results["stats"] = stats
            results["actions"].append("Database statistics collected")

            # Additional analysis if there are mappings
            if stats["tables"]["entity_mappings"] > 0:
                distribution = maintenance.analyze_mapping_distribution()
                results["type_distribution"] = distribution
                results["actions"].append("Mapping type distribution analyzed")

    except Exception as e:
        results["errors"].append(f"Maintenance error: {str(e)}")
        results["success"] = False

    results["end_time"] = datetime.datetime.now().isoformat()

    return results


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run maintenance
    results = run_maintenance()

    # Print results
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
