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
    MappingPathStep,
    OntologyPreference,
    EndpointRelationship,
    PropertyExtractionConfig,
    EndpointPropertyConfig,
    OntologyCoverage
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
        "metabolites_csv": Endpoint(name="MetabolitesCSV", description="Example Metabolites CSV File", connection_details='{"file_path": "data/metabolites_sample.csv", "identifier_column": "MetaboliteName"}'),
        "spoke": Endpoint(name="SPOKE", description="SPOKE Neo4j Graph Database", connection_details='{"uri": "bolt://localhost:7687", "user": "neo4j", "password": "password"}'), # Example
        "ukbb_protein": Endpoint(name="UKBB_Protein", description="UK Biobank Protein Biomarkers", connection_details='{"path": "/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_Protein_Meta.tsv"}'), # Updated path
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
            input_ontology_term="UNIPROT_NAME", 
            output_ontology_term="UNIPROTKB_AC", 
            config_template=json.dumps({ 
                # "api_key": "YOUR_API_KEY_IF_NEEDED"
            })
        ),
        "umls_search": MappingResource(
            name="UMLS_Metathesaurus",
            description="Maps UMLS CUIs to other ontology terms using the UMLS Terminology Services (UTS) API.",
            resource_type="api"
        ),
        "uniprot_idmapping": MappingResource(
            name="UniProt_IDMapping",
            description="UniProt ID Mapping: UniProtKB AC -> Ensembl Gene ID",
            client_class_path="biomapper.mapping.clients.uniprot_idmapping_client.UniProtIDMappingClient",
            input_ontology_term="UNIPROTKB_AC",
            output_ontology_term="ENSEMBL_GENE",
            config_template=json.dumps({
                "from_db": "UniProtKB_AC-ID",
                "to_db": "Ensembl"
            }),
        ),
        "arivale_lookup": MappingResource(
            name="Arivale_Metadata_Lookup",
            description="Direct lookup from UniProtKB AC to Arivale Protein ID using the Arivale metadata file",
            client_class_path="biomapper.mapping.clients.arivale_lookup_client.ArivaleMetadataLookupClient",
            input_ontology_term="UNIPROTKB_AC",
            output_ontology_term="ARIVALE_PROTEIN_ID",
            config_template=json.dumps({
                "file_path": "/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv",
                "key_column": "uniprot",
                "value_column": "name"
            }),
        ),
        # Placeholder for future RAG resource
        # "pubchem_rag": MappingResource(name="PubChemRAG", description="Uses PubChem embeddings for similarity-based mapping fallback.", resource_type="rag"),
    }
    session.add_all(resources.values())
    await session.flush() # Flush to get IDs

    logging.info("Populating Mapping Paths...")
    # Note: Steps are now defined using MappingPathStep model instances
    paths = [
        MappingPath(
            name="PUBCHEM_to_CHEBI_via_UniChem", # Added name
            source_type="PUBCHEM_ID", # Changed to PUBCHEM_ID
            target_type="CHEBI_ID", # Changed to CHEBI_ID
            priority=10, # Added priority
            description="Map PubChem ID to ChEBI ID using UniChem.",
            steps=[ # Create model instance(s)
                MappingPathStep(
                    mapping_resource_id=resources["unichem"].id,
                    step_order=1,
                    description="UniChem: PUBCHEM_ID -> CHEBI_ID"
                )
            ]
        ),
        MappingPath(
            name="PUBCHEM_to_KEGG_via_UniChem",
            source_type="PUBCHEM_ID", # Changed to PUBCHEM_ID
            target_type="KEGG_ID", # Changed to KEGG_ID
            priority=10,
            description="Map PubChem ID to KEGG ID using UniChem.",
            steps=[
                MappingPathStep(
                    mapping_resource_id=resources["unichem"].id,
                    step_order=1,
                    description="UniChem: PUBCHEM_ID -> KEGG_ID"
                )
            ]
        ),
        MappingPath(
            name="CHEBI_to_PUBCHEM_via_UniChem",
            source_type="CHEBI_ID", # Changed to CHEBI_ID
            target_type="PUBCHEM_ID", # Changed to PUBCHEM_ID
            priority=10,
            description="Map ChEBI ID to PubChem ID using UniChem.",
            steps=[
                MappingPathStep(
                    mapping_resource_id=resources["unichem"].id,
                    step_order=1,
                    description="UniChem: CHEBI_ID -> PUBCHEM_ID"
                )
            ]
        ),
        MappingPath(
            name="KEGG_to_PUBCHEM_via_UniChem",
            source_type="KEGG_ID", # Changed to KEGG_ID
            target_type="PUBCHEM_ID", # Changed to PUBCHEM_ID
            priority=10,
            description="Map KEGG ID to PubChem ID using UniChem.",
            steps=[
                MappingPathStep(
                    mapping_resource_id=resources["unichem"].id,
                    step_order=1,
                    description="UniChem: KEGG_ID -> PUBCHEM_ID"
                )
            ]
        ),
         MappingPath(
             name="PUBCHEM_to_NAME_via_PubChem",
             source_type="PUBCHEM_ID", # Changed to PUBCHEM_ID
             target_type="NAME", # Changed to NAME
             priority=20, # Lower priority than UniChem direct
             description="Get common name from PubChem ID using PubChem PUG API.",
             steps=[
                 MappingPathStep(
                     mapping_resource_id=resources["pubchem"].id,
                     step_order=1,
                     description="PubChem: PUBCHEM_ID -> NAME"
                )
            ]
        ),
         MappingPath(
             name="CHEBI_to_NAME_via_ChEBI",
             source_type="CHEBI_ID", # Changed to CHEBI_ID
             target_type="NAME", # Changed to NAME
             priority=20,
             description="Get common name from ChEBI ID using ChEBI API.",
             steps=[
                 MappingPathStep(
                     mapping_resource_id=resources["chebi"].id,
                     step_order=1,
                     description="ChEBI: CHEBI_ID -> NAME"
                )
            ]
        ),
        # --- Path for UKBB -> Arivale Protein ---
        # Assuming UKBB uses Gene_Name and Arivale uses UniProtKB_AC based on executor code
        MappingPath(
            name="UKBB_GENE_NAME_to_Arivale_UniProtAC",
            source_type="GENE_NAME", # From UKBB_Protein EndpointPropertyConfig
            target_type="UNIPROTKB_AC", # From Arivale_Protein EndpointPropertyConfig
            priority=5, # High priority for this specific mapping
            description="Map Gene Name to UniProt AC using UniProt Name Client.",
            steps=[
                MappingPathStep(
                    mapping_resource_id=resources["uniprot_name"].id, # Use the UniProt resource
                    step_order=1,
                    description="UniProt: GENE_NAME -> UNIPROTKB_AC"
                )
            ]
        ),
        MappingPath(
            name="UKBB_GENE_NAME_to_Arivale_Protein",
            source_type="GENE_NAME", 
            target_type="ARIVALE_PROTEIN_ID",
            priority=5, # High priority for this specific mapping
            description="Maps UKBB gene names to Arivale protein identifiers via UniProt accessions",
            steps=[
                MappingPathStep(
                    mapping_resource_id=resources["uniprot_name"].id,
                    step_order=1,
                    description="UniProt: GENE_NAME -> UNIPROTKB_AC"
                ),
                MappingPathStep(
                    mapping_resource_id=resources["arivale_lookup"].id, # Use the new lookup resource
                    step_order=2,
                    description="Arivale Lookup: UNIPROTKB_AC -> ARIVALE_PROTEIN_ID"
                )
            ]
        ),
        MappingPath(
            name="UKBB_GENE_NAME_to_EnsemblGene",
            source_type="GENE_NAME",
            target_type="ENSEMBL_GENE",
            priority=10,
            description="Gene Name -> UniProtKB AC -> Ensembl Gene ID",
            steps=[
                MappingPathStep(
                    mapping_resource_id=resources["uniprot_name"].id,
                    step_order=1,
                    description="UniProt: GENE_NAME -> UNIPROTKB_AC"
                ),
                MappingPathStep(
                    mapping_resource_id=resources["uniprot_idmapping"].id,
                    step_order=2,
                    description="UniProt: UNIPROTKB_AC -> ENSEMBL_GENE"
                )
            ]
        ),
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
    ukbb_arivale_protein_rel = EndpointRelationship(
        source_endpoint_id=endpoints["ukbb_protein"].id,
        target_endpoint_id=endpoints["arivale_protein"].id,
        description="Maps UKBB Olink Protein identifiers to Arivale SomaScan Protein identifiers."
    )
    session.add_all([relationships["arivale_to_spoke"], ukbb_arivale_protein_rel])
    await session.flush() # Flush to get IDs for preferences

    logging.info("Populating Ontology Preferences...")
    preferences = [
        # Arivale source data is primarily PUBCHEM
        OntologyPreference(endpoint_id=endpoints["metabolites_csv"].id, relationship_id=relationships["arivale_to_spoke"].id, ontology_name="PUBCHEM_ID", priority=1),
        # SPOKE target ideally wants CHEBI
        OntologyPreference(endpoint_id=endpoints["spoke"].id, relationship_id=relationships["arivale_to_spoke"].id, ontology_name="CHEBI_ID", priority=1), # Higher priority
        # Fallback for SPOKE target
        OntologyPreference(endpoint_id=endpoints["spoke"].id, relationship_id=relationships["arivale_to_spoke"].id, ontology_name="PUBCHEM_ID", priority=2), # Lower priority
        # UKBB -> Arivale Protein Relationship Preference
        OntologyPreference(relationship_id=ukbb_arivale_protein_rel.id, ontology_name="UNIPROTKB_AC", priority=1), # Specify target ontology, not the resource
        # --- Add Endpoint-specific Preferences (Overrides Relationship defaults if needed) ---
        # UKBB Protein primarily uses UNIPROT_NAME for its 'PrimaryIdentifier'
        OntologyPreference(endpoint_id=endpoints["ukbb_protein"].id, ontology_name="UNIPROT_NAME", priority=0),
        # Arivale Protein primarily uses UNIPROTKB_AC for its 'PrimaryIdentifier'
        OntologyPreference(endpoint_id=endpoints["arivale_protein"].id, ontology_name="UNIPROTKB_AC", priority=0),
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
            ontology_type="CHEBI_ID", # What we get OUT (example)
            property_name="identifier",
            extraction_method="client_method",
            extraction_pattern="map_id", # Placeholder method name in UniChem client
            result_type="string"
        ),
        # Config for extracting primary identifier (Assay column) from UKBB TSV
        PropertyExtractionConfig(
            resource_id=None, # Not tied to a specific mapping resource
            ontology_type="GENE_NAME", # Type of the identifier being extracted
            property_name="PrimaryIdentifier", # Standard name for the main ID
            extraction_method="column",
            extraction_pattern=json.dumps({"column_name": "Assay"}), # Actual column name
            result_type="string"
        ),
        # Config for extracting UniProt AC from Arivale TSV
        PropertyExtractionConfig(
            resource_id=None,
            ontology_type="UNIPROTKB_AC", # Type of the identifier being extracted
            property_name="UniProtKB_Accession", # Specific property name
            extraction_method="column",
            extraction_pattern=json.dumps({"column_name": "uniprot"}), # Actual column name
            result_type="string"
        ),
        # Config for extracting primary identifier (name column) from Arivale TSV
        PropertyExtractionConfig(
            resource_id=None,
            ontology_type="ARIVALE_PROTEIN_ID", # Custom type for the Arivale primary ID
            property_name="PrimaryIdentifier", # Standard name for the main ID
            extraction_method="column",
            extraction_pattern=json.dumps({"column_name": "name"}), # Actual column name
            result_type="string"
        ),
        # Config for extracting Ensembl Gene ID
        PropertyExtractionConfig(
            resource_id=None,
            ontology_type="ENSEMBL_GENE", # Type of the identifier being extracted
            property_name="EnsemblGeneID", # Specific property name
            extraction_method="column",
            extraction_pattern=json.dumps({"column_name": "ensembl_gene_id"}), # Actual column name
            result_type="string"
        ),
    ]
    session.add_all(prop_extract_configs)
    await session.flush() # Flush to get extraction config IDs

    logging.info("Populating Endpoint Property Configs...")
    endpoint_prop_configs = [
        EndpointPropertyConfig(
            endpoint_id=endpoints["ukbb_protein"].id,
            property_extraction_config_id=prop_extract_configs[3].id, # Index of UKBB config
            property_name="PrimaryIdentifier" # Links UKBB endpoint + 'PrimaryIdentifier' to the 'ukbb_assay_column' config
        ),
        # Link Arivale endpoint to its UniProt AC extraction config
        EndpointPropertyConfig(
            endpoint_id=endpoints["arivale_protein"].id,
            property_extraction_config_id=prop_extract_configs[4].id, # Index of the Arivale UniProt config
            property_name="UniProtKB_Accession"
        ),
        # Link Arivale endpoint to its PrimaryIdentifier extraction config
        EndpointPropertyConfig(
            endpoint_id=endpoints["arivale_protein"].id,
            property_extraction_config_id=prop_extract_configs[5].id, # Use UniProt config (index -2)
            property_name="PrimaryIdentifier"
        ),
        # ... potentially add configs for other endpoints/properties ...
        # Define a property for Ensembl Gene ID (even if no endpoint uses it directly yet)
        # This allows targeting ENSEMBL_GENE in mapping paths
        EndpointPropertyConfig(
            id=4,
            endpoint_id=endpoints["ukbb_protein"].id, # Associate with UKBB Protein arbitrarily for now
            property_name="EnsemblGeneID",
            property_extraction_config_id=prop_extract_configs[6].id # Ensembl Gene ID extraction
        ),
    ]
    session.add_all(endpoint_prop_configs)

    logging.info("Populating Ontology Coverage...")
    ontology_coverage_configs = [
        # UniProt Name Search covers NAME -> UNIPROTKB_AC via API lookup
        OntologyCoverage(
            resource_id=resources["uniprot_name"].id,
            source_type="UNIPROT_NAME", # Consistent uppercase
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
            source_type="PUBCHEM_ID", # Assuming IDs are used
            target_type="CHEBI_ID", # Assuming IDs are used
            support_level="api_lookup"
        ),
        OntologyCoverage(
            resource_id=resources["unichem"].id,
            source_type="CHEBI_ID", # Assuming IDs are used
            target_type="PUBCHEM_ID", # Assuming IDs are used
            support_level="api_lookup"
        ),
        # UniProt ID Mapping covers UNIPROTKB_AC -> ENSEMBL_GENE
        OntologyCoverage(
            resource_id=resources["uniprot_idmapping"].id,
            source_type="UNIPROTKB_AC",
            target_type="ENSEMBL_GENE",
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
