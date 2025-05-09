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
    OntologyCoverage,
    Property,
    Ontology,
    MappingSessionLog,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

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

    logging.info("Populating Ontologies...")
    ontologies = {
        "uniprotkb_ac": Ontology(
            name="UNIPROTKB_AC_ONTOLOGY",
            description="UniProtKB Accession Numbers",
            identifier_prefix="UniProtKB:",
            namespace_uri="https://www.uniprot.org/uniprot/",
            version="2025.01"
        ),
        "arivale_protein_id": Ontology(
            name="ARIVALE_PROTEIN_ID_ONTOLOGY",
            description="Arivale Protein Identifiers",
            version="2025.01"
        ),
        "gene_name": Ontology(
            name="GENE_NAME_ONTOLOGY", 
            description="Gene Names/Symbols",
            version="2025.01"
        ),
        "ensembl_protein": Ontology(
            name="ENSEMBL_PROTEIN_ONTOLOGY",
            description="Ensembl Protein Identifiers",
            identifier_prefix="ENSP:",
            namespace_uri="https://www.ensembl.org/id/",
            version="2025.01"
        ),
        "ensembl_gene": Ontology(
            name="ENSEMBL_GENE_ONTOLOGY",
            description="Ensembl Gene Identifiers",
            identifier_prefix="ENSG:",
            namespace_uri="https://www.ensembl.org/id/",
            version="2025.01"
        ),
        "pubchem_id": Ontology(
            name="PUBCHEM_ID_ONTOLOGY",
            description="PubChem Compound Identifiers",
            identifier_prefix="CID:",
            namespace_uri="https://pubchem.ncbi.nlm.nih.gov/compound/",
            version="2025.01"
        ),
        "chebi_id": Ontology(
            name="CHEBI_ID_ONTOLOGY",
            description="Chemical Entities of Biological Interest Identifiers",
            identifier_prefix="CHEBI:",
            namespace_uri="https://www.ebi.ac.uk/chebi/searchId.do?chebiId=",
            version="2025.01"
        ),
        "kegg_id": Ontology(
            name="KEGG_ID_ONTOLOGY",
            description="KEGG Compound Identifiers",
            identifier_prefix="KEGG:",
            namespace_uri="https://www.genome.jp/dbget-bin/www_bget?cpd:",
            version="2025.01"
        ),
    }
    session.add_all(ontologies.values())
    await session.flush()  # Flush to get IDs

    logging.info("Populating Properties...")
    properties = [
        # UniProtKB AC properties
        Property(
            name="UNIPROTKB_AC",
            description="UniProtKB Accession Number",
            ontology_id=ontologies["uniprotkb_ac"].id,
            is_primary=True,
            data_type="string"
        ),
        
        # Arivale Protein ID properties
        Property(
            name="ARIVALE_PROTEIN_ID",
            description="Arivale Protein Identifier",
            ontology_id=ontologies["arivale_protein_id"].id,
            is_primary=True,
            data_type="string"
        ),
        
        # Gene Name properties
        Property(
            name="GENE_NAME",
            description="Gene Name/Symbol",
            ontology_id=ontologies["gene_name"].id,
            is_primary=True,
            data_type="string"
        ),
        
        # Ensembl Protein properties
        Property(
            name="ENSEMBL_PROTEIN",
            description="Ensembl Protein Identifier",
            ontology_id=ontologies["ensembl_protein"].id,
            is_primary=True,
            data_type="string"
        ),
        Property(
            name="ENSEMBL_PROTEIN_ID",
            description="Ensembl Protein Identifier (Alternative naming)",
            ontology_id=ontologies["ensembl_protein"].id,
            is_primary=False,
            data_type="string"
        ),
        
        # Ensembl Gene properties
        Property(
            name="ENSEMBL_GENE",
            description="Ensembl Gene Identifier",
            ontology_id=ontologies["ensembl_gene"].id,
            is_primary=True,
            data_type="string"
        ),
        
        # PubChem properties
        Property(
            name="PUBCHEM_ID",
            description="PubChem Compound Identifier",
            ontology_id=ontologies["pubchem_id"].id,
            is_primary=True,
            data_type="string"
        ),
        
        # ChEBI properties
        Property(
            name="CHEBI_ID",
            description="ChEBI Identifier",
            ontology_id=ontologies["chebi_id"].id,
            is_primary=True,
            data_type="string"
        ),
        
        # KEGG properties
        Property(
            name="KEGG_ID",
            description="KEGG Compound Identifier",
            ontology_id=ontologies["kegg_id"].id,
            is_primary=True,
            data_type="string"
        ),
    ]
    session.add_all(properties)
    await session.flush()  # Flush to get IDs

    logging.info("Populating Endpoints...")
    endpoints = {
        "metabolites_csv": Endpoint(
            name="MetabolitesCSV",
            description="Example Metabolites CSV File",
            connection_details='{"file_path": "data/metabolites_sample.csv", "identifier_column": "MetaboliteName"}',
        ),
        "spoke": Endpoint(
            name="SPOKE",
            description="SPOKE Neo4j Graph Database",
            connection_details='{"uri": "bolt://localhost:7687", "user": "neo4j", "password": "password"}',
        ),  # Example
        "ukbb_protein": Endpoint(
            name="UKBB_Protein",
            description="UK Biobank Protein Biomarkers",
            connection_details='{"path": "/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_Protein_Meta.tsv"}',
            primary_property_name="UNIPROTKB_AC"
        ),  # Updated path
        "arivale_protein": Endpoint(
            name="Arivale_Protein",
            description="Arivale SomaScan Protein Metadata",
            type="protein_tsv",
            connection_details='{"path": "/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv"}',
            primary_property_name="ARIVALE_PROTEIN_ID"
        ),
        "arivale_chem": Endpoint(
            name="Arivale_Chemistry",
            description="Arivale Clinical Lab Chemistries Metadata",
            type="clinical_tsv",
            connection_details='{"path": "/procedure/data/local_data/ARIVALE_SNAPSHOTS/chemistries_metadata.tsv"}',
        ),
    }
    session.add_all(endpoints.values())
    await session.flush()  # Flush to get IDs for relationships

    logging.info("Populating Mapping Resources...")
    resources = {
        "chebi": MappingResource(
            name="ChEBI",
            description="Chemical Entities of Biological Interest",
            resource_type="ontology",
        ),
        "pubchem": MappingResource(
            name="PubChem",
            description="NCBI chemical compound database",
            resource_type="ontology",
        ),
        "kegg": MappingResource(
            name="KEGG",
            description="Metabolic pathway and compound information",
            resource_type="ontology",
        ),
        "unichem": MappingResource(
            name="UniChem",
            description="EBI compound identifier mapping service",
            resource_type="api",
        ),
        "refmet": MappingResource(
            name="RefMet",
            description="Reference metabolite nomenclature",
            resource_type="ontology",
        ),
        "ramp_db": MappingResource(
            name="RaMP DB",
            description="Rapid Mapping Database for metabolites and pathways",
            resource_type="database",
        ),
        # New resources:
        "uniprot_name": MappingResource(
            name="UniProt_NameSearch",
            description="Maps Gene Names/Symbols to UniProtKB Accession IDs using the UniProt ID Mapping API.",
            client_class_path="biomapper.mapping.clients.uniprot_name_client.UniProtNameClient",
            input_ontology_term="GENE_NAME",
            output_ontology_term="UNIPROTKB_AC",
            config_template=json.dumps(
                {
                    # "api_key": "YOUR_API_KEY_IF_NEEDED"
                }
            ),
        ),
        "umls_search": MappingResource(
            name="UMLS_Metathesaurus",
            description="Maps UMLS CUIs to other ontology terms using the UMLS Terminology Services (UTS) API.",
            resource_type="api",
        ),
        "uniprot_idmapping": MappingResource(
            name="UniProt_IDMapping",
            description="UniProt ID Mapping: UniProtKB AC -> Ensembl Gene ID",
            client_class_path="biomapper.mapping.clients.uniprot_ensembl_protein_mapping_client.UniProtEnsemblProteinMappingClient",
            input_ontology_term="UNIPROTKB_AC",
            output_ontology_term="ENSEMBL_GENE",
            config_template=json.dumps(
                {"from_db": "UniProtKB_AC-ID", "to_db": "Ensembl"}
            ),
        ),
        "arivale_lookup": MappingResource(
            name="Arivale_UniProt_Lookup",
            description="Direct lookup from UniProt AC to Arivale protein identifiers using the Arivale metadata file",
            client_class_path="biomapper.mapping.clients.arivale_lookup_client.ArivaleMetadataLookupClient",
            input_ontology_term="UNIPROTKB_AC",
            output_ontology_term="ARIVALE_PROTEIN_ID",
            config_template='{"file_path": "/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv", "key_column": "uniprot", "value_column": "name"}',
        ),
        "arivale_reverse_lookup": MappingResource(
            name="Arivale_Reverse_Lookup",
            description="Direct lookup from Arivale Protein ID to UniProt AC using metadata file (reverse)",
            client_class_path="biomapper.mapping.clients.arivale_lookup_client.ArivaleMetadataLookupClient",
            input_ontology_term="ARIVALE_PROTEIN_ID",
            output_ontology_term="UNIPROTKB_AC",
            config_template='{"file_path": "/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv", "key_column": "name", "value_column": "uniprot"}',
        ),
        "arivale_genename_lookup": MappingResource(
            name="Arivale_GeneName_Lookup",
            description="Direct lookup from Gene Name to Arivale Protein ID using the Arivale metadata file",
            resource_type="client_lookup",  # Inferred type
            # Assuming similar client/config structure to other Arivale lookups
            client_class_path="biomapper.mapping.clients.arivale_lookup_client.ArivaleMetadataLookupClient",  # Placeholder - May need a specific client or config adjustment
            input_ontology_term="GENE_NAME",
            output_ontology_term="ARIVALE_PROTEIN_ID",
            config_template='{"key_column": "Gene_Name", "value_column": "Arivale_Protein_ID"}',  # Placeholder - Needs correct column names from metadata
        ),
        "uniprot_ensembl_protein_mapping": MappingResource(
            name="UniProtEnsemblProteinMapping",
            description="Map Ensembl Protein IDs to UniProtKB ACs via UniProt API",
            client_class_path="biomapper.mapping.clients.uniprot_ensembl_protein_mapping_client.UniProtEnsemblProteinMappingClient",
            input_ontology_term="ENSEMBL_PROTEIN",
            output_ontology_term="UNIPROTKB_AC",
            config_template=json.dumps(
                {
                    "from_db": "Ensembl_Protein",
                    "to_db": "UniProtKB_AC-ID",
                }
            ),
        ),
        "uniprot_historical_resolver": MappingResource(
            name="UniProtHistoricalResolver",
            description="Resolves historical/secondary UniProt accessions to current primary accessions",
            client_class_path="biomapper.mapping.clients.uniprot_historical_resolver_client.UniProtHistoricalResolverClient",
            input_ontology_term="UNIPROTKB_AC",
            output_ontology_term="UNIPROTKB_AC",
            config_template=json.dumps(
                {
                    # No special config needed for the historical resolver
                    "cache_size": 10000,
                }
            ),
        ),
    }
    session.add_all(resources.values())
    await session.flush()  # Flush to get IDs

    logging.info("Populating Mapping Paths...")
    paths = {
        "PUBCHEM_to_CHEBI_via_UniChem": MappingPath(
            name="PUBCHEM_to_CHEBI_via_UniChem",
            source_type="PUBCHEM_ID",
            target_type="CHEBI_ID",
            priority=10,
            description="Map PubChem ID to ChEBI ID using UniChem.",
            steps=[
                MappingPathStep(
                    mapping_resource_id=resources["unichem"].id,
                    step_order=1,
                    description="UniChem: PubChem ID -> ChEBI ID",
                )
            ],
        ),
        "KEGG_to_CHEBI_via_UniChem": MappingPath(
            name="KEGG_to_CHEBI_via_UniChem",
            source_type="KEGG_ID",
            target_type="CHEBI_ID",
            priority=10,
            description="Map KEGG ID to ChEBI ID using UniChem.",
            steps=[
                MappingPathStep(
                    mapping_resource_id=resources["unichem"].id,
                    step_order=1,
                    description="UniChem: KEGG_ID -> ChEBI ID",
                )
            ],
        ),
        "KEGG_to_PUBCHEM_via_UniChem": MappingPath(
            name="KEGG_to_PUBCHEM_via_UniChem",
            source_type="KEGG_ID",
            target_type="PUBCHEM_ID",
            priority=10,
            description="Map KEGG ID to PubChem ID using UniChem.",
            steps=[
                MappingPathStep(
                    mapping_resource_id=resources["unichem"].id,
                    step_order=1,
                    description="UniChem: KEGG_ID -> PUBCHEM_ID",
                )
            ],
        ),
        "PUBCHEM_to_NAME_via_PubChem": MappingPath(
            name="PUBCHEM_to_NAME_via_PubChem",
            source_type="PUBCHEM_ID",
            target_type="NAME",
            priority=20,
            description="Get common name from PubChem ID using PubChem PUG API.",
            steps=[
                MappingPathStep(
                    mapping_resource_id=resources["pubchem"].id,
                    step_order=1,
                    description="PubChem: PUBCHEM_ID -> NAME",
                )
            ],
        ),
        "CHEBI_to_NAME_via_ChEBI": MappingPath(
            name="CHEBI_to_NAME_via_ChEBI",
            source_type="CHEBI_ID",
            target_type="NAME",
            priority=20,
            description="Get common name from ChEBI ID using ChEBI API.",
            steps=[
                MappingPathStep(
                    mapping_resource_id=resources["chebi"].id,
                    step_order=1,
                    description="ChEBI: CHEBI_ID -> NAME",
                )
            ],
        ),
        # --- Direct path for UKBB -> Arivale Protein (via UniProt AC) ---
        "UKBB_to_Arivale_Protein_via_UniProt": MappingPath(
            name="UKBB_to_Arivale_Protein_via_UniProt",
            source_type="UNIPROTKB_AC",
            target_type="ARIVALE_PROTEIN_ID",
            priority=1,  # Highest priority (try this path first)
            description="Maps UKBB UniProt AC directly to Arivale protein identifiers using the Arivale metadata file",
            steps=[
                MappingPathStep(
                    mapping_resource_id=resources["arivale_lookup"].id,
                    step_order=1,
                    description="Direct lookup from UniProt AC to Arivale ID",
                )
            ],
        ),
        # --- Fallback path for UKBB -> Arivale Protein with historical resolution ---
        "UKBB_to_Arivale_Protein_via_Historical_Resolution": MappingPath(
            name="UKBB_to_Arivale_Protein_via_Historical_Resolution",
            source_type="UNIPROTKB_AC",
            target_type="ARIVALE_PROTEIN_ID",
            priority=2,  # Lower priority (try after direct path)
            description="Maps UKBB UniProt AC to Arivale protein identifiers with historical/secondary accession resolution",
            steps=[
                MappingPathStep(
                    mapping_resource_id=resources["uniprot_historical_resolver"].id,
                    step_order=1,
                    description="Resolve historical/secondary UniProt accessions to current primary accessions",
                ),
                MappingPathStep(
                    mapping_resource_id=resources["arivale_lookup"].id,
                    step_order=2,
                    description="Direct lookup from resolved UniProt AC to Arivale ID",
                )
            ],
        ),
        # --- Path for Arivale -> UKBB Protein (NEW: Reverse Direct UniProt AC) ---
        "Arivale_to_UKBB_Protein_via_UniProt": MappingPath(
            name="Arivale_to_UKBB_Protein_via_UniProt",
            source_type="ARIVALE_PROTEIN_ID",
            target_type="UNIPROTKB_AC",
            priority=1,
            description="Maps Arivale protein identifiers directly to UniProt AC using the Arivale metadata file",
            steps=[
                MappingPathStep(
                    mapping_resource_id=resources["arivale_reverse_lookup"].id,
                    step_order=1,
                    description="Direct lookup from Arivale ID to UniProt AC",
                )
            ],
        ),
        # --- Path for Gene Name -> UniProtKB AC --- (New)
        "GeneName_to_UniProtKB": MappingPath(
            name="GeneName_to_UniProtKB",
            source_type="GENE_NAME",
            target_type="UNIPROTKB_AC",
            priority=10,
            description="Maps Gene Name/Symbol to UniProtKB AC using UniProt Name Search API.",
            steps=[
                MappingPathStep(
                    mapping_resource_id=resources["uniprot_name"].id,
                    step_order=1,
                    description="UniProt Name Search: Gene Name -> UniProtKB AC",
                )
            ],
        ),
        # --- Path for Ensembl Protein -> UniProtKB AC --- (New)
        "EnsemblProtein_to_UniProtKB": MappingPath(
            name="EnsemblProtein_to_UniProtKB",
            source_type="ENSEMBL_PROTEIN",
            target_type="UNIPROTKB_AC",
            priority=5,
            description="Maps Ensembl Protein ID to UniProtKB AC using UniProt ID Mapping service.",
            steps=[
                MappingPathStep(
                    mapping_resource_id=resources["uniprot_ensembl_protein_mapping"].id,
                    step_order=1,
                    description="UniProt ID Mapping: Ensembl Protein -> UniProtKB AC",
                )
            ],
        ),
        # Path for Ensembl Gene ID to UniProtKB Accession
        "EnsemblGene_to_UniProtKB_via_IDMapping": MappingPath(
            name="EnsemblGene_to_UniProtKB_via_IDMapping",
            source_type="ENSEMBL_GENE",
            target_type="UNIPROTKB_AC",
            priority=5,
            description="Map Ensembl Gene ID to UniProtKB AC using UniProt ID Mapping service.",
            steps=[
                MappingPathStep(
                    mapping_resource_id=resources["uniprot_idmapping"].id,
                    step_order=1,
                    description="UniProt ID Mapping: ENSEMBL_GENE -> UNIPROTKB_AC",
                )
            ],
        ),
        # === Protein Paths ===
        # Ensembl Protein ID -> Arivale Protein ID (via UniProt)
        "ensembl_arivale_path": MappingPath(
            name="Ensembl_Arivale_Path",
            source_type="ENSEMBL_PROTEIN",
            target_type="ARIVALE_PROTEIN_ID",
            priority=1,
            steps=[
                MappingPathStep(
                    step_order=1,
                    mapping_resource_id=resources["uniprot_ensembl_protein_mapping"].id,
                ),
                MappingPathStep(
                    step_order=2,
                    mapping_resource_id=resources["arivale_lookup"].id,
                ),
            ],
        ),
    }
    session.add_all(paths.values())
    await session.flush()  # Flush to get IDs

    logging.info("Populating Endpoint Relationships...")
    relationships = {
        "arivale_to_spoke": EndpointRelationship(
            source_endpoint_id=endpoints["metabolites_csv"].id,
            target_endpoint_id=endpoints["spoke"].id,
            description="Map Arivale Metabolites (by PUBCHEM) to SPOKE Compounds (prefer CHEBI)",
        )
    }
    ukbb_arivale_protein_rel = EndpointRelationship(
        source_endpoint_id=endpoints["ukbb_protein"].id,
        target_endpoint_id=endpoints["arivale_protein"].id,
        description="Maps UKBB Olink Protein identifiers to Arivale SomaScan Protein identifiers.",
    )
    session.add_all([relationships["arivale_to_spoke"], ukbb_arivale_protein_rel])
    await session.flush()  # Flush to get IDs for preferences

    logging.info("Populating Ontology Preferences...")
    preferences = [
        # Arivale source data is primarily PUBCHEM
        OntologyPreference(
            endpoint_id=endpoints["metabolites_csv"].id,
            relationship_id=relationships["arivale_to_spoke"].id,
            ontology_name="PUBCHEM_ID",
            priority=1,
        ),
        # SPOKE target ideally wants CHEBI
        OntologyPreference(
            endpoint_id=endpoints["spoke"].id,
            relationship_id=relationships["arivale_to_spoke"].id,
            ontology_name="CHEBI_ID",
            priority=1,
        ),
        # Fallback for SPOKE target
        OntologyPreference(
            endpoint_id=endpoints["spoke"].id,
            relationship_id=relationships["arivale_to_spoke"].id,
            ontology_name="PUBCHEM_ID",
            priority=2,
        ),
        # UKBB -> Arivale Protein Relationship Preference
        OntologyPreference(
            relationship_id=ukbb_arivale_protein_rel.id,
            ontology_name="UNIPROTKB_AC",
            priority=1,
        ),
        # --- Add Endpoint-specific Preferences (Overrides Relationship defaults if needed) ---
        # UKBB Protein primarily uses UNIPROT_NAME for its 'PrimaryIdentifier'
        OntologyPreference(
            endpoint_id=endpoints["ukbb_protein"].id,
            ontology_name="UNIPROTKB_AC",
            priority=0,
        ),
        # Arivale Protein primarily uses UNIPROTKB_AC for its 'PrimaryIdentifier'
        OntologyPreference(
            endpoint_id=endpoints["arivale_protein"].id,
            ontology_name="UNIPROTKB_AC",
            priority=0,
        ),
        # Preferences for UKBB Protein
        OntologyPreference(
            endpoint_id=endpoints["ukbb_protein"].id,
            ontology_name="UNIPROTKB_AC",
            priority=1,
        ),
        OntologyPreference(
            endpoint_id=endpoints["ukbb_protein"].id,
            ontology_name="GENE_NAME",
            priority=2,
        ),
        # Preferences for Arivale Protein
        OntologyPreference(
            endpoint_id=endpoints["arivale_protein"].id,
            ontology_name="UNIPROTKB_AC",
            priority=1,
        ),
        OntologyPreference(
            endpoint_id=endpoints["arivale_protein"].id,
            ontology_name="ENSEMBL_PROTEIN",
            priority=2,
        ),
        OntologyPreference(
            endpoint_id=endpoints["arivale_protein"].id,
            ontology_name="GENE_NAME",
            priority=3,
        ),
        OntologyPreference(
            endpoint_id=endpoints["arivale_protein"].id,
            ontology_name="ENSEMBL_GENE",
            priority=4,
        ),
        OntologyPreference(
            endpoint_id=endpoints["arivale_protein"].id,
            ontology_name="ARIVALE_PROTEIN_ID",
            priority=5,
        ),
    ]
    session.add_all(preferences)
    await session.flush()

    logging.info("Populating Property Extraction Configs...")
    prop_extract_configs = [
        # --- UniProt Name Search ---
        # Expects: PROTEIN_NAME or GENE_NAME, Returns: UNIPROTKB_AC
        PropertyExtractionConfig(
            resource_id=resources["uniprot_name"].id,
            ontology_type="UNIPROTKB_AC",
            property_name="identifier",
            extraction_method="client_method",
            extraction_pattern="find_uniprot_id_by_name",
            result_type="string",
        ),
        # --- UMLS Metathesaurus Search ---
        # Expects: TERM, Returns: CUI
        PropertyExtractionConfig(
            resource_id=resources["umls_search"].id,
            ontology_type="CUI",
            property_name="identifier",
            extraction_method="client_method",
            extraction_pattern="find_cui_by_term",
            result_type="string",
        ),
        # Add configs for existing resources if needed...
        # Example: UniChem expects a specific ID type and returns another
        PropertyExtractionConfig(
            resource_id=resources["unichem"].id,
            ontology_type="CHEBI_ID",
            property_name="identifier",
            extraction_method="client_method",
            extraction_pattern="map_id",
            result_type="string",
        ),
        # Config for extracting UKBB UniProt column (MODIFIED) (index 3)
        PropertyExtractionConfig(
            resource_id=None,
            ontology_type="UNIPROTKB_AC",
            property_name="PrimaryIdentifier",
            extraction_method="column",
            extraction_pattern=json.dumps({"column_name": "UniProt"}),
            result_type="string",
        ),
        # Config for extracting UniProt AC from Arivale TSV (index 4)
        PropertyExtractionConfig(
            resource_id=None,
            ontology_type="UNIPROTKB_AC",
            property_name="UniProtKB_Accession",
            extraction_method="column",
            extraction_pattern=json.dumps({"column_name": "uniprot"}),
            result_type="string",
        ),
        # Config for extracting primary identifier (name column) from Arivale TSV
        PropertyExtractionConfig(
            resource_id=None,
            ontology_type="ARIVALE_PROTEIN_ID",
            property_name="PrimaryIdentifier",
            extraction_method="column",
            extraction_pattern=json.dumps({"column_name": "name"}),
            result_type="string",
        ),
        # Config for extracting Ensembl Gene ID
        PropertyExtractionConfig(
            resource_id=None,
            ontology_type="ENSEMBL_GENE",
            property_name="EnsemblGeneID",
            extraction_method="column",
            extraction_pattern=json.dumps({"column_name": "ensembl_gene_id"}),
            result_type="string",
        ),
        # Config for extracting Gene Name from UKBB TSV (index 7)
        PropertyExtractionConfig(
            resource_id=None,
            ontology_type="GENE_NAME",
            property_name="GeneName",
            extraction_method="column",
            extraction_pattern=json.dumps({"column_name": "Assay"}),
            result_type="string",
        ),
        # Config for extracting Gene Name from Arivale TSV (index 8)
        PropertyExtractionConfig(
            resource_id=None,
            ontology_type="GENE_NAME",
            property_name="GeneName",
            extraction_method="column",
            extraction_pattern=json.dumps({"column_name": "gene_name"}),
            result_type="string",
        ),
        # Config for extracting Ensembl Protein ID from Arivale TSV (index 9)
        PropertyExtractionConfig(
            resource_id=None,
            ontology_type="ENSEMBL_PROTEIN_ID",
            property_name="EnsemblProteinID",
            extraction_method="column",
            extraction_pattern=json.dumps({"column_name": "protein_id"}),
            result_type="string",
        ),
    ]
    session.add_all(prop_extract_configs)
    await session.flush()  # Flush to get extraction config IDs

    logging.info("Populating Endpoint Property Configs...")
    # Find the Property objects we need by name
    property_uniprotkb_ac = next(p for p in properties if p.name == "UNIPROTKB_AC")
    property_arivale_protein_id = next(p for p in properties if p.name == "ARIVALE_PROTEIN_ID")
    property_gene_name = next(p for p in properties if p.name == "GENE_NAME")
    property_ensembl_protein = next(p for p in properties if p.name == "ENSEMBL_PROTEIN")
    property_ensembl_protein_id = next(p for p in properties if p.name == "ENSEMBL_PROTEIN_ID")
    property_ensembl_gene = next(p for p in properties if p.name == "ENSEMBL_GENE")
    
    endpoint_prop_configs = [
        # UKBB Protein - UniProtKB AC primary identifier
        EndpointPropertyConfig(
            endpoint_id=endpoints["ukbb_protein"].id,
            property_extraction_config_id=prop_extract_configs[3].id,
            property_name="PrimaryIdentifier",  # The property name in the UI/config
            ontology_type="UNIPROTKB_AC",       # The ontology type for lookup
            is_primary_identifier=True,
        ),
        
        # Arivale Protein - UniProt AC non-primary identifier
        EndpointPropertyConfig(
            endpoint_id=endpoints["arivale_protein"].id,
            property_extraction_config_id=prop_extract_configs[4].id,
            property_name="UniProtKB_Accession",
            ontology_type="UNIPROTKB_AC",
        ),
        
        # Arivale Protein - Primary identifier
        EndpointPropertyConfig(
            endpoint_id=endpoints["arivale_protein"].id,
            property_extraction_config_id=prop_extract_configs[5].id,
            property_name="PrimaryIdentifier",
            ontology_type="ARIVALE_PROTEIN_ID",
            is_primary_identifier=True,
        ),
        
        # UKBB Protein - Ensembl Gene ID
        EndpointPropertyConfig(
            endpoint_id=endpoints["ukbb_protein"].id,
            property_name="EnsemblGeneID",
            property_extraction_config_id=prop_extract_configs[6].id,
            ontology_type="ENSEMBL_GENE",
        ),
        
        # UKBB Protein - Gene Name
        EndpointPropertyConfig(
            endpoint_id=endpoints["ukbb_protein"].id,
            property_extraction_config_id=prop_extract_configs[7].id,
            property_name="GeneName",
            ontology_type="GENE_NAME",
        ),
        
        # Arivale Protein - Gene Name
        EndpointPropertyConfig(
            endpoint_id=endpoints["arivale_protein"].id,
            property_extraction_config_id=prop_extract_configs[8].id,
            property_name="GeneName",
            ontology_type="GENE_NAME",
        ),
        
        # Arivale Protein - Ensembl Protein ID
        EndpointPropertyConfig(
            endpoint_id=endpoints["arivale_protein"].id,
            property_extraction_config_id=prop_extract_configs[9].id,
            property_name="EnsemblProteinID",
            ontology_type="ENSEMBL_PROTEIN_ID",
        ),
        
        # Arivale Protein - Ensembl Gene ID
        EndpointPropertyConfig(
            endpoint_id=endpoints["arivale_protein"].id,
            property_extraction_config_id=prop_extract_configs[6].id,
            property_name="EnsemblGeneID",
            ontology_type="ENSEMBL_GENE",
        ),
    ]
    session.add_all(endpoint_prop_configs)

    logging.info("Populating Ontology Coverage...")
    ontology_coverage_configs = [
        # UniProt Name Search covers NAME -> UNIPROTKB_AC via API lookup
        OntologyCoverage(
            resource_id=resources["uniprot_name"].id,
            source_type="GENE_NAME",
            target_type="UNIPROTKB_AC",
            support_level="api_lookup",
        ),
        # UMLS Search covers TERM -> CUI via API lookup
        OntologyCoverage(
            resource_id=resources["umls_search"].id,
            source_type="TERM",
            target_type="CUI",
            support_level="api_lookup",
        ),
        # Add coverage for existing resources...
        # e.g., UniChem covers PUBCHEM -> CHEBI
        OntologyCoverage(
            resource_id=resources["unichem"].id,
            source_type="PUBCHEM_ID",
            target_type="CHEBI_ID",
            support_level="api_lookup",
        ),
        OntologyCoverage(
            resource_id=resources["unichem"].id,
            source_type="CHEBI_ID",
            target_type="PUBCHEM_ID",
            support_level="api_lookup",
        ),
        # UniProt ID Mapping covers UNIPROTKB_AC -> ENSEMBL_GENE
        OntologyCoverage(
            resource_id=resources["uniprot_idmapping"].id,
            source_type="UNIPROTKB_AC",
            target_type="ENSEMBL_GENE",
            support_level="api_lookup",
        ),
        # UniProt ID Mapping covers ENSEMBL_GENE -> UNIPROTKB_AC (New Coverage)
        OntologyCoverage(
            resource_id=resources["uniprot_idmapping"].id,
            source_type="ENSEMBL_GENE",
            target_type="UNIPROTKB_AC",
            support_level="api_lookup",
        ),
        # Arivale UniProt Lookup covers UNIPROTKB_AC -> ARIVALE_PROTEIN_ID
        OntologyCoverage(
            resource_id=resources["arivale_lookup"].id,
            source_type="UNIPROTKB_AC",
            target_type="ARIVALE_PROTEIN_ID",
            support_level="client_lookup",
        ),
        # Arivale Reverse Lookup covers ARIVALE_PROTEIN_ID -> UNIPROTKB_AC
        OntologyCoverage(
            resource_id=resources["arivale_reverse_lookup"].id,
            source_type="ARIVALE_PROTEIN_ID",
            target_type="UNIPROTKB_AC",
            support_level="client_lookup",
        ),
        # UniProt Ensembl Protein Mapping covers ENSEMBL_PROTEIN -> UNIPROTKB_AC
        OntologyCoverage(
            resource_id=resources["uniprot_ensembl_protein_mapping"].id,
            source_type="ENSEMBL_PROTEIN",
            target_type="UNIPROTKB_AC",
            support_level="api_lookup",
        ),
        # UniProt Historical Resolver covers UNIPROTKB_AC -> UNIPROTKB_AC (with resolution)
        OntologyCoverage(
            resource_id=resources["uniprot_historical_resolver"].id,
            source_type="UNIPROTKB_AC",
            target_type="UNIPROTKB_AC",
            support_level="api_lookup",
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
