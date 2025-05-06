#!/usr/bin/env python
"""Script to populate the database with common composite identifier patterns.

This script adds default patterns for handling composite identifiers to the
metamapper.db database, focusing on common patterns like underscore-separated
gene names and comma-separated UniProt IDs.

Example usage:
    python scripts/populate_composite_patterns.py
"""

import sys
import os
import logging
import argparse
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from biomapper.config import settings
from biomapper.db.models import CompositePatternConfig, CompositeProcessingStep, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_gene_name_patterns(session: Session) -> None:
    """Create patterns for composite gene names.
    
    Args:
        session: SQLAlchemy database session
    """
    # Check if pattern already exists
    existing = (
        session.query(CompositePatternConfig)
        .filter(CompositePatternConfig.name == "Underscore Separated Genes")
        .first()
    )
    
    if existing:
        logger.info(f"Pattern 'Underscore Separated Genes' already exists (ID: {existing.id})")
        return
    
    # Create the pattern
    pattern = CompositePatternConfig(
        name="Underscore Separated Genes",
        description="Pattern for underscore-separated gene names like GENE1_GENE2",
        ontology_type="GENE_NAME",  # Ensure uppercase for consistency
        pattern=r"[A-Za-z0-9]+_[A-Za-z0-9]+",  # Simple regex for NAME_NAME
        delimiters="_",
        mapping_strategy="first_match",  # Use the first successful match
        keep_component_type=True,  # Components are still gene names
        priority=1,
    )
    
    session.add(pattern)
    session.flush()  # Flush to get the pattern ID
    
    # Create processing steps
    steps = [
        CompositeProcessingStep(
            pattern_id=pattern.id,
            step_type="split",
            parameters="{\"delimiter\": \"_\"}",
            order=1,
        ),
        CompositeProcessingStep(
            pattern_id=pattern.id,
            step_type="clean",
            parameters="{\"strip\": true}",
            order=2,
        ),
    ]
    
    for step in steps:
        session.add(step)
    
    logger.info(f"Created pattern 'Underscore Separated Genes' (ID: {pattern.id}) with {len(steps)} processing steps")


def create_uniprot_id_patterns(session: Session) -> None:
    """Create patterns for composite UniProt identifiers.
    
    Args:
        session: SQLAlchemy database session
    """
    # Check if pattern already exists
    existing = (
        session.query(CompositePatternConfig)
        .filter(CompositePatternConfig.name == "Comma Separated UniProt IDs")
        .first()
    )
    
    if existing:
        logger.info(f"Pattern 'Comma Separated UniProt IDs' already exists (ID: {existing.id})")
        return
    
    # Create the pattern
    pattern = CompositePatternConfig(
        name="Comma Separated UniProt IDs",
        description="Pattern for comma-separated UniProt IDs like P12345,Q67890",
        ontology_type="UNIPROTKB_AC",  # Ensure uppercase for consistency
        pattern=r"[A-Z][0-9][A-Z0-9]{3}[0-9],([A-Z][0-9][A-Z0-9]{3}[0-9],?)+",  # Regex for UniProt IDs
        delimiters=",",
        mapping_strategy="all_matches",  # Combine results from all components
        keep_component_type=True,  # Components are still UniProt IDs
        priority=1,
    )
    
    session.add(pattern)
    session.flush()  # Flush to get the pattern ID
    
    # Create processing steps
    steps = [
        CompositeProcessingStep(
            pattern_id=pattern.id,
            step_type="split",
            parameters="{\"delimiter\": \",\"}",
            order=1,
        ),
        CompositeProcessingStep(
            pattern_id=pattern.id,
            step_type="clean",
            parameters="{\"strip\": true}",
            order=2,
        ),
    ]
    
    for step in steps:
        session.add(step)
    
    logger.info(f"Created pattern 'Comma Separated UniProt IDs' (ID: {pattern.id}) with {len(steps)} processing steps")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Populate the database with common composite identifier patterns"
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=settings.metamapper_db_url,
        help="Database URL (default: from settings)",
    )
    args = parser.parse_args()
    
    # Create database engine and session
    logger.info(f"Connecting to database at {args.db_url}")
    # Use regular SQLite URL if using aiosqlite
    db_url = args.db_url
    if 'aiosqlite' in db_url:
        db_url = db_url.replace('sqlite+aiosqlite', 'sqlite')
    logger.info(f"Using connection URL: {db_url}")
    
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Create the tables if they don't exist
        Base.metadata.create_all(engine, tables=[
            CompositePatternConfig.__table__,
            CompositeProcessingStep.__table__,
        ])
        
        # Create patterns
        create_gene_name_patterns(session)
        create_uniprot_id_patterns(session)
        
        # Commit the changes
        session.commit()
        logger.info("Successfully populated composite identifier patterns")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error populating composite identifier patterns: {e}")
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
