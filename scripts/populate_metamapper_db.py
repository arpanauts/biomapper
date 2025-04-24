"""Script to populate the metamapper.db configuration database with standard data."""

import asyncio
import logging
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Assuming db.session provides get_session and Base, and models are in db.models
from biomapper.db.models import (
    Base,
    Endpoint,
    MappingResource,
    MappingPath,
    OntologyPreference,
    EndpointRelationship,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the path to the configuration database
CONFIG_DB_PATH = Path(__file__).parent.parent / "data" / "metamapper.db"

async def delete_existing_db():
    """Deletes the existing database file if it exists."""
    if CONFIG_DB_PATH.exists():
        logging.warning(f"Existing database found at {CONFIG_DB_PATH}. Deleting...")
        try:
            CONFIG_DB_PATH.unlink()
            logging.info("Existing database deleted successfully.")
        except OSError as e:
            logging.error(f"Error deleting database file {CONFIG_DB_PATH}: {e}")
            raise
    else:
        logging.info(f"No existing database found at {CONFIG_DB_PATH}. Proceeding.")

async def populate_data(session: AsyncSession):
    """Adds standard configuration data to the database."""

    logging.info("Populating Endpoints...")
    endpoints = {
        "metabolites_csv": Endpoint(name="MetabolitesCSV", description="Arivale Metabolomics Data", type="csv"),
        "spoke": Endpoint(name="SPOKE", description="SPOKE Biomedical Knowledge Graph", type="graphdb", connection_details='{"host": "localhost", "port": 8529}'),
        # New endpoints:
        "ukbb_protein": Endpoint(name="UKBB_Protein", description="UKBB Olink Protein Metadata", type="protein_tsv", connection_details='{"path": "/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_Protein_Meta.tsv"}'),
        "arivale_protein": Endpoint(name="Arivale_Protein", description="Arivale SomaScan Protein Metadata", type="protein_tsv", connection_details='{"path": "/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv"}'),
        "arivale_chem": Endpoint(name="Arivale_Chemistry", description="Arivale Clinical Lab Chemistries Metadata", type="clinical_tsv", connection_details='{"path": "/procedure/data/local_data/ARIVALE_SNAPSHOTS/chemistries_metadata.tsv"}')
    }
    session.add_all(endpoints.values())
    await session.flush() # Flush to get IDs for relationships

    logging.info("Populating Mapping Resources...")
    resources = {
        "chebi": MappingResource(name="ChEBI", description="Chemical Entities of Biological Interest", resource_type="ontology"),
        "pubchem": MappingResource(name="PubChem", description="NCBI chemical compound database", resource_type="ontology"),
        "kegg": MappingResource(name="KEGG", description="Metabolic pathway and compound information", resource_type="ontology"),
        "unichem": MappingResource(name="UniChem", description="EBI compound identifier mapping service", resource_type="api"),
        "refmet": MappingResource(name="RefMet", description="Reference metabolite nomenclature", resource_type="ontology"),
        "ramp_db": MappingResource(name="RaMP DB", description="Rapid Mapping Database for metabolites and pathways", resource_type="database"),
    }
    session.add_all(resources.values())
    await session.flush() # Flush to get IDs

    logging.info("Populating Mapping Paths...")
    # Example paths - need refinement based on actual implementation
    # Note: Steps often involve intermediate resources like UniChem
    paths = [
        # Direct mappings (if available)
        MappingPath(source_type="PUBCHEM", target_type="CHEBI",
                    steps=[{"resource_name": "UniChem", "source": "PUBCHEM", "target": "CHEBI"}]),
        MappingPath(source_type="PUBCHEM", target_type="KEGG",
                    steps=[{"resource_name": "UniChem", "source": "PUBCHEM", "target": "KEGG"}]),
        MappingPath(source_type="CHEBI", target_type="PUBCHEM",
                    steps=[{"resource_name": "UniChem", "source": "CHEBI", "target": "PUBCHEM"}]),
        MappingPath(source_type="KEGG", target_type="PUBCHEM",
                    steps=[{"resource_name": "UniChem", "source": "KEGG", "target": "PUBCHEM"}]),
        # Potentially add paths for HMDB, InChIKey, SMILES etc. later
        MappingPath(source_type="PUBCHEM", target_type="NAME",
                    steps=[{"resource_name": "PubChem", "source": "PUBCHEM", "target": "NAME"}]),
        MappingPath(source_type="CHEBI", target_type="NAME",
                    steps=[{"resource_name": "ChEBI", "source": "CHEBI", "target": "NAME"}]),
    ]
    session.add_all(paths)
    await session.flush()

    logging.info("Populating Endpoint Relationships...")
    relationships = {
        "arivale_to_spoke": EndpointRelationship(
            source_endpoint_id=endpoints["metabolites_csv"].id,
            target_endpoint_id=endpoints["spoke"].id,
            description="Map Arivale Metabolites (by PUBCHEM) to SPOKE Compounds (prefer CHEBI)"
        )
    }
    session.add_all(relationships.values())
    await session.flush()

    logging.info("Populating Ontology Preferences...")
    preferences = [
        # Arivale source data is primarily PUBCHEM
        OntologyPreference(endpoint_id=endpoints["metabolites_csv"].id, relationship_id=relationships["arivale_to_spoke"].id, ontology_name="PUBCHEM", priority=1),
        # SPOKE target ideally wants CHEBI
        OntologyPreference(endpoint_id=endpoints["spoke"].id, relationship_id=relationships["arivale_to_spoke"].id, ontology_name="CHEBI", priority=1), # Higher priority
        # Fallback for SPOKE target
        OntologyPreference(endpoint_id=endpoints["spoke"].id, relationship_id=relationships["arivale_to_spoke"].id, ontology_name="PUBCHEM", priority=2), # Lower priority
    ]
    session.add_all(preferences)
    await session.flush()

    await session.commit()
    logging.info("Database population complete.")

async def main():
    # Ensure data directory exists
    CONFIG_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Delete existing DB if it exists
    await delete_existing_db()

    # Set up the database engine
    db_url = f"sqlite+aiosqlite:///{CONFIG_DB_PATH}" # Use aiosqlite driver
    temp_engine = create_async_engine(db_url, echo=False)
    async with temp_engine.begin() as conn:
        logging.info(f"Creating schema in {CONFIG_DB_PATH}...")
        await conn.run_sync(Base.metadata.create_all)
    await temp_engine.dispose()
    logging.info("Schema creation/check complete.")

    # Create engine and session specifically for this script, pointing to the config DB
    engine = create_async_engine(db_url, echo=False)
    AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    async with AsyncSessionLocal() as session:
        await populate_data(session)

if __name__ == "__main__":
    asyncio.run(main())
