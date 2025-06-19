"""
Default SPOKE schema mapping for Biomapper's generalized knowledge graph layer.

This module provides a standardized schema mapping for the SPOKE knowledge graph,
based on its known structure. This mapping can be used without needing to
dynamically discover the schema through potentially expensive database operations.

SPOKE integrates data from 41 specialized biomedical databases including:
- ChEMBL, DrugBank, DrugCentral (chemical compounds and drugs)
- Entrez Gene, COSMIC, OMIM (genes and genetic disorders)
- DisGeNET, OMIM (disease associations)
- Human Interactome, iRefIndex (protein interactions)
- Reactome, Pathway Commons (biological pathways)
- FooDB (food constituents)
- SIDER (drug side effects)
- And many others

This schema mapping captures the core entity types and relationships from these
integrated data sources to support Biomapper's hybrid architecture.
"""

from typing import Dict, Any, Optional

# Default schema definition for SPOKE knowledge graph
SPOKE_DEFAULT_SCHEMA = {
    "name": "spoke",
    "type": "knowledge_graph",
    "description": "SPOKE Knowledge Graph - Integrated biomedical knowledge from 41 specialized databases",
    "schema_mapping": {
        "node_types": {
            "Compound": {
                "ontology_types": [
                    "chebi",
                    "hmdb",
                    "pubchem",
                    "inchikey",
                    "drugbank",
                    "chembl",
                ],
                "property_map": {
                    "properties.identifier": "chebi",  # Default mapping
                    "properties.chebi": "chebi",
                    "properties.hmdb": "hmdb",
                    "properties.pubchem": "pubchem",
                    "properties.inchikey": "inchikey",
                    "properties.drugbank": "drugbank",
                    "properties.chembl": "chembl",
                },
                "source_databases": [
                    "ChEMBL",
                    "DrugBank",
                    "DrugCentral",
                    "BindingDB",
                    "FooDB",
                ],
            },
            "Gene": {
                "ontology_types": ["ensembl", "entrez", "gene_symbol", "hgnc"],
                "property_map": {
                    "name": "gene_symbol",  # Default mapping
                    "properties.ensembl": "ensembl",
                    "properties.entrez": "entrez",
                    "properties.symbol": "gene_symbol",
                    "properties.hgnc": "hgnc",
                },
                "source_databases": [
                    "Entrez Gene",
                    "COSMIC",
                    "DisGeNET",
                    "DistiLD",
                    "OMIM",
                    "Bgee",
                    "LINCS L1000",
                ],
            },
            "Protein": {
                "ontology_types": ["uniprot", "pdb", "interpro"],
                "property_map": {
                    "properties.uniprot": "uniprot",
                    "properties.pdb": "pdb",
                    "properties.interpro": "interpro",
                },
                "source_databases": ["Human Interactome Database", "iRefIndex"],
            },
            "Disease": {
                "ontology_types": ["mondo", "doid", "mesh", "omim", "disgenet"],
                "property_map": {
                    "properties.mondo": "mondo",
                    "properties.doid": "doid",
                    "properties.mesh": "mesh",
                    "properties.omim": "omim",
                    "properties.disgenet": "disgenet",
                },
                "source_databases": ["DisGeNET", "OMIM", "MeSH"],
            },
            "Pathway": {
                "ontology_types": ["reactome", "kegg", "go", "pathwaycommons", "pid"],
                "property_map": {
                    "properties.reactome": "reactome",
                    "properties.kegg": "kegg",
                    "properties.go": "go",
                    "properties.pathwaycommons": "pathwaycommons",
                    "properties.pid": "pid",
                },
                "source_databases": [
                    "Reactome",
                    "Pathway Commons",
                    "Pathway Interaction Database",
                ],
            },
            "Anatomy": {
                "ontology_types": ["uberon"],
                "property_map": {"properties.uberon": "uberon"},
            },
            "Symptom": {
                "ontology_types": ["mesh", "umls"],
                "property_map": {"properties.mesh": "mesh", "properties.umls": "umls"},
            },
            "Food": {
                "ontology_types": ["foodb", "foodon"],
                "property_map": {
                    "properties.foodb": "foodb",
                    "properties.foodon": "foodon",
                },
                "source_databases": ["FooDB"],
            },
            "Pharmacologic": {
                "ontology_types": ["atc", "ndc", "rxnorm"],
                "property_map": {
                    "properties.atc": "atc",
                    "properties.ndc": "ndc",
                    "properties.rxnorm": "rxnorm",
                },
                "source_databases": ["DrugCentral", "PharmacoDB"],
            },
            "SideEffect": {
                "ontology_types": ["sider", "mesh"],
                "property_map": {
                    "properties.sider": "sider",
                    "properties.mesh": "mesh",
                },
                "source_databases": ["SIDER"],
            },
        }
    },
    "capabilities": [
        {
            "name": "compound_to_gene",
            "description": "Map compounds to genes",
            "confidence": 0.9,
            "expected_labels": ["INTERACTS_CmG", "TARGETS_CtG"],
            "source_databases": ["ChEMBL", "DrugBank", "BindingDB"],
        },
        {
            "name": "gene_to_disease",
            "description": "Map genes to diseases",
            "confidence": 0.9,
            "expected_labels": [
                "ASSOCIATES_DaG",
                "UPREGULATES_GuD",
                "DOWNREGULATES_GdD",
            ],
            "source_databases": ["DisGeNET", "OMIM", "COSMIC", "DistiLD"],
        },
        {
            "name": "compound_to_pathway",
            "description": "Map compounds to pathways",
            "confidence": 0.9,
            "expected_labels": ["PARTICIPATES_CpP"],
        },
        {
            "name": "gene_to_pathway",
            "description": "Map genes to pathways",
            "confidence": 0.9,
            "expected_labels": ["PARTICIPATES_GpP"],
        },
        {
            "name": "protein_to_pathway",
            "description": "Map proteins to pathways",
            "confidence": 0.9,
            "expected_labels": ["PARTICIPATES_PrpP"],
        },
        {
            "name": "compound_to_disease",
            "description": "Map compounds to diseases",
            "confidence": 0.9,
            "expected_labels": ["TREATS_CpD", "PALLIATES_CpD", "CAUSES_CcD"],
        },
        {
            "name": "disease_to_symptom",
            "description": "Map diseases to symptoms",
            "confidence": 0.9,
            "expected_labels": ["PRESENTS_DpS"],
        },
        {
            "name": "gene_to_protein",
            "description": "Map genes to proteins",
            "confidence": 0.9,
            "expected_labels": ["EXPRESSES_GeP"],
        },
    ],
}


def get_default_schema_mapping() -> Dict[str, Any]:
    """Get the default schema mapping for SPOKE.

    Returns:
        Dict with the default schema mapping
    """
    return SPOKE_DEFAULT_SCHEMA


def create_spoke_config(
    host: str = "localhost",
    port: int = 8529,
    database: str = "spoke",
    username: str = "root",
    password: str = "ph",
    use_ssl: bool = False,
    schema_mapping: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a complete SPOKE configuration using the default schema mapping.

    Args:
        host: ArangoDB host
        port: ArangoDB port
        database: Database name
        username: Database username
        password: Database password
        use_ssl: Whether to use SSL for the connection
        schema_mapping: Custom schema mapping (default: use SPOKE_DEFAULT_SCHEMA)

    Returns:
        Dict with the complete SPOKE configuration
    """
    schema = schema_mapping or SPOKE_DEFAULT_SCHEMA

    config = {
        "name": "spoke",
        "type": "knowledge_graph",
        "description": schema["description"],
        "optional": True,  # System can function without SPOKE
        "connection": {
            "type": "arangodb",
            "host": host,
            "port": port,
            "database": database,
            "username": username,
            "password": password,
            "use_ssl": use_ssl,
        },
        "schema_mapping": schema["schema_mapping"],
        "capabilities": schema["capabilities"],
    }

    return config
