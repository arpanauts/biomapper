"""Script to populate the metamapper.db configuration database with standard data."""

import asyncio
import logging
import os
import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Assuming db.session provides get_session and Base, and models are in db.models
from biomapper.db.models import (
    Base,
    Endpoint,
    MappingResource,
    MappingPath,
    OntologyPreference,
    EndpointRelationship,
    PropertyExtractionConfig,
    EndpointPropertyConfig,
    OntologyCoverage,
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
        # New resources:
        "uniprot_name": MappingResource(
            name="UniProt_NameSearch",
            description="Maps Gene Names/Symbols to UniProtKB Accession IDs using the UniProt ID Mapping API.",
            client_class_path="biomapper.mapping.clients.uniprot_name_client.UniProtNameClient", 
            input_ontology_term="Gene_Name", 
            output_ontology_term="UniProtKB", 
            config_template=json.dumps({ 
                # "api_key": "YOUR_API_KEY_IF_NEEDED"
            })
        ),
        "umls_search": MappingResource(
            name="UMLS_Metathesaurus",
            description="Maps UMLS CUIs to other ontology terms using the UMLS Terminology Services (UTS) API.",
            resource_type="api"
        ),
        # Placeholder for future RAG resource
        # "pubchem_rag": MappingResource(name="PubChemRAG", description="Uses PubChem embeddings for similarity-based mapping fallback.", resource_type="rag"),
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

    logging.info("Populating Property Extraction Configs...")
    prop_extract_configs = [
        # --- UniProt Name Search --- 
        # Expects: PROTEIN_NAME or GENE_NAME, Returns: UNIPROTKB_AC
        PropertyExtractionConfig(
            resource_id=resources["uniprot_name"].id, 
            ontology_type="UNIPROTKB_AC", # What we get OUT
            property_name="identifier", # The primary identifier
            extraction_method="client_method", # Client handles extraction
            extraction_pattern="find_uniprot_id_by_name", # Placeholder method name
            result_type="string"
        ),
        # --- UMLS Metathesaurus Search ---
        # Expects: TERM, Returns: CUI
        PropertyExtractionConfig(
            resource_id=resources["umls_search"].id,
            ontology_type="CUI", # What we get OUT
            property_name="identifier", # The primary identifier
            extraction_method="client_method",
            extraction_pattern="find_cui_by_term", # Placeholder method name
            result_type="string"
        ),
        # Add configs for existing resources if needed...
        # Example: UniChem expects a specific ID type and returns another
        PropertyExtractionConfig(
            resource_id=resources["unichem"].id,
            ontology_type="CHEBI", # What we get OUT (example)
            property_name="identifier",
            extraction_method="client_method",
            extraction_pattern="map_id", # Placeholder method name in UniChem client
            result_type="string"
        ),
    ]
    session.add_all(prop_extract_configs)
    await session.flush()

    logging.info("Populating Endpoint Property Configs...")
    endpoint_prop_configs = [
        # --- UKBB Protein Endpoint --- 
        # How to get the NAME property (which is a PROTEIN_NAME) from this endpoint
        EndpointPropertyConfig(
            endpoint_id=endpoints["ukbb_protein"].id,
            ontology_type="PROTEIN_NAME", # The type of thing this property represents
            property_name="name", # The generic property name (e.g., used in mapping requests)
            extraction_method="column_name", # Method to get it from the TSV
            extraction_pattern="Protein Name" # Actual column header in the TSV (Guessing!)
        ),
        # --- Arivale Protein Endpoint ---
        EndpointPropertyConfig(
            endpoint_id=endpoints["arivale_protein"].id,
            ontology_type="PROTEIN_NAME", 
            property_name="name", 
            extraction_method="column_name", 
            extraction_pattern="Protein Name" # Actual column header in the TSV (Guessing!)
        ),
         # Add configs for other endpoints if needed...
    ]
    session.add_all(endpoint_prop_configs)
    await session.flush()

    logging.info("Populating Ontology Coverage...")
    ontology_coverage_configs = [
        # UniProt Name Search covers NAME -> UNIPROTKB_AC via API lookup
        OntologyCoverage(
            resource_id=resources["uniprot_name"].id,
            source_type="PROTEIN_NAME", # Or GENE_NAME
            target_type="UNIPROTKB_AC",
            support_level="api_lookup"
        ),
        OntologyCoverage(
            resource_id=resources["uniprot_name"].id,
            source_type="GENE_NAME",
            target_type="UNIPROTKB_AC",
            support_level="api_lookup"
        ),
        # UMLS Search covers TERM -> CUI via API lookup
        OntologyCoverage(
            resource_id=resources["umls_search"].id,
            source_type="TERM", # Generic term
            target_type="CUI",
            support_level="api_lookup"
        ),
        # Add coverage for existing resources...
        # e.g., UniChem covers PUBCHEM -> CHEBI
        OntologyCoverage(
            resource_id=resources["unichem"].id,
            source_type="PUBCHEM",
            target_type="CHEBI",
            support_level="api_lookup"
        ),
        OntologyCoverage(
            resource_id=resources["unichem"].id,
            source_type="CHEBI",
            target_type="PUBCHEM",
            support_level="api_lookup"
        ),
        # ... add others as needed ...
    ]
    session.add_all(ontology_coverage_configs)
    await session.flush()

    # Note: We are not populating RelationshipMappingPath yet as specific
    # relationships using these paths haven't been defined.

    try:
        await session.commit()
        logging.info("Successfully populated database.")
    except Exception as e:
        await session.rollback()
        logging.error(f"Error populating database: {e}")
        raise

async def main():
    """Main function to set up DB and populate data."""
    # Ensure parent directory exists
    CONFIG_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Delete existing DB if it exists
    await delete_existing_db()

    # Create engine and session
    engine = create_async_engine(f"sqlite+aiosqlite:///{CONFIG_DB_PATH}")
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Create tables
    async with engine.begin() as conn:
        logging.info("Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)
        logging.info("Database tables created.")

    # Populate data
    async with async_session() as session:
        await populate_data(session)

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
