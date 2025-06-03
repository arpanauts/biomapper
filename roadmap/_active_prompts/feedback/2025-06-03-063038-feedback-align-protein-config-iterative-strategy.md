# Feedback: Alignment of protein_config.yaml with Iterative Mapping Strategy

## 1. Summary of Current Support

The `protein_config.yaml` currently provides a solid foundation for supporting the iterative mapping strategy, with several key elements in place:

- **Ontology Definitions**: All necessary protein ontology types are defined, with `PROTEIN_UNIPROTKB_AC_ONTOLOGY` correctly marked as the primary shared ontology.
- **Database Endpoints**: All 6 protein sources (Arivale, UKBB, HPP, Function Health, SPOKE, KG2) are configured with endpoints and property mappings.
- **Basic Atomic Clients**: Some atomic mapping clients are defined for direct lookups within individual databases.
- **Multi-Step Paths**: The `mapping_paths` section defines several multi-step conversion routes between databases.

## 2. Identified Gaps and Areas Needing Clarification

### 2.1 Missing Secondary-to-Primary Conversion Clients

The iterative strategy explicitly mentions these secondary-to-primary conversions that are **missing** from the current configuration:

1. **GENE_NAME → UNIPROTKB_AC**: Referenced in the strategy (line 48, 121) but missing from `additional_resources`. While `uniprot_name_search` exists, it's not integrated as a mapping client in the databases section.

2. **ENSEMBL_PROTEIN → UNIPROTKB_AC**: Referenced in the strategy (line 48, 122) but missing. The codebase has `UniProtEnsemblProteinMappingClient` but it's not configured.

3. **ENSEMBL_GENE → UNIPROTKB_AC**: Referenced in the strategy (lines 39, 48, 130) for Arivale but:
   - Missing the ontology definition for `PROTEIN_ENSEMBL_GENE_ONTOLOGY`
   - Missing the property mapping in Arivale database (should extract from "ensembl_gene_id" column)
   - Missing the conversion client

### 2.2 Incomplete Property Mappings

Several databases lack comprehensive secondary identifier mappings:

1. **UKBB**: Only has `UKBB_PROTEIN_ASSAY_ID_ONTOLOGY` as secondary. The strategy mentions `GENE_NAME` should be extractable from the "Assay" column (line 108), but this isn't configured.

2. **SPOKE**: Missing actual column mapping for `uniprot_id` field (line 298 references "uniprot_ac" but properties define "uniprot_id").

3. **KG2**: Similar issue - line 343 references "uniprot_ac" but properties define "uniprot_accession".

4. **Function Health**: Marked as placeholder, needs actual implementation details.

### 2.3 Missing Identity Lookups

The strategy uses "identity lookups" for databases where the primary is already UniProtKB (e.g., HPP). While `hpp_uniprot_identity_lookup` is defined, similar identity lookups are commented out for UKBB (lines 162-170) but may be needed.

### 2.4 OntologyPreference Configuration

The strategy extensively discusses `OntologyPreference` (lines 16, 29, 44, 101, 132-134) to guide secondary type conversion order, but:
- No `OntologyPreference` structure exists in the YAML
- No clear mechanism to specify priority order for secondary types per endpoint
- The strategy specifies explicit priorities for UKBB and Arivale proteins (lines 132-134) that aren't reflected

### 2.5 Generic File Client Limitations

All atomic mapping clients use `GenericFileLookupClient`, but the strategy suggests specialized clients may be needed (line 50) for:
- API-based lookups (UniProt Name Search, UniProt ID Mapping)
- Complex conversions requiring multiple steps or validation

## 3. Interaction Between mapping_paths and MappingExecutor

Based on the strategy document and current configuration, the interaction appears to work as follows:

**Primary Mode**: The `MappingExecutor` dynamically discovers and chains atomic client capabilities:
- Uses `mapping_clients` defined within each database as atomic building blocks
- Chains these based on input/output ontology type matching
- The `mapping_paths` section provides pre-defined "highways" for common conversions

**Hybrid Approach**: The system uses both:
- **Dynamic Discovery**: For the iterative strategy steps (especially secondary → primary conversions)
- **Named Paths**: For well-known, optimized multi-hop conversions between specific databases

This hybrid approach allows flexibility while providing optimized paths for common use cases.

## 4. Concrete Proposals for Modifications

### 4.1 Add Missing Ontology Types

```yaml
ontologies:
  # Add this new ontology type
  PROTEIN_ENSEMBL_GENE_ONTOLOGY:
    description: "Ensembl gene identifiers"
    identifier_prefix: "ENSG:"
    is_primary: false
```

### 4.2 Fix and Expand Property Mappings

#### For Arivale:
```yaml
databases:
  arivale:
    properties:
      mappings:
        # Add this mapping
        PROTEIN_ENSEMBL_GENE_ONTOLOGY:
          column: "ensembl_gene_id"
          ontology_type: "PROTEIN_ENSEMBL_GENE_ONTOLOGY"
```

#### For UKBB (if GENE_NAME is extractable from Assay column):
```yaml
databases:
  ukbb:
    properties:
      mappings:
        # Consider adding if Assay column contains gene names
        PROTEIN_GENE_NAME_ONTOLOGY:
          column: "Assay"  # Verify this is correct
          ontology_type: "PROTEIN_GENE_NAME_ONTOLOGY"
          extraction_pattern: "regex_to_extract_gene_name"  # If needed
```

#### Fix SPOKE and KG2 column references:
```yaml
databases:
  spoke:
    mapping_clients:
      - name: "spoke_node_to_uniprot_lookup"
        config:
          value_column: "uniprot_id"  # Match the property definition
          
  kg2:
    mapping_clients:
      - name: "kg2_entity_to_uniprot_lookup"
        config:
          value_column: "uniprot_accession"  # Match the property definition
```

### 4.3 Add Secondary-to-Primary Conversion Clients

Add these to `additional_resources`:

```yaml
additional_resources:
  # Gene name to UniProt conversion
  - name: "gene_name_to_uniprot"
    client_class_path: "biomapper.mapping.clients.uniprot_name_client.UniProtNameClient"
    input_ontology_type: "PROTEIN_GENE_NAME_ONTOLOGY"
    output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
    config:
      api_timeout: 30
      batch_size: 100
      
  # Ensembl protein to UniProt conversion  
  - name: "ensembl_protein_to_uniprot"
    client_class_path: "biomapper.mapping.clients.uniprot_ensembl_protein_mapping_client.UniProtEnsemblProteinMappingClient"
    input_ontology_type: "PROTEIN_ENSEMBL_ONTOLOGY"
    output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
    config:
      timeout: 60
      batch_size: 100
      
  # Ensembl gene to UniProt conversion
  - name: "ensembl_gene_to_uniprot"
    client_class_path: "biomapper.mapping.clients.uniprot_idmapping_client.UniProtIDMappingClient"
    input_ontology_type: "PROTEIN_ENSEMBL_GENE_ONTOLOGY"
    output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
    config:
      from_db: "Ensembl"
      to_db: "UniProtKB"
      timeout: 60
```

### 4.4 Add Placeholder Conversion Clients for Missing Sources

For SPOKE, KG2, and Function Health that may have proprietary identifiers:

```yaml
additional_resources:
  # SPOKE-specific conversions (if needed)
  - name: "spoke_gene_to_uniprot"
    client_class_path: "biomapper.mapping.clients.generic_file_client.GenericFileLookupClient"
    input_ontology_type: "PROTEIN_GENE_NAME_ONTOLOGY"
    output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
    config:
      file_path: "${DATA_DIR}/spoke_export/gene_protein_mapping.tsv"
      key_column: "gene_name"
      value_column: "uniprot_id"
      delimiter: "\t"
      
  # Similar for KG2 and Function Health as needed...
```

### 4.5 Implement OntologyPreference Structure

Add a new top-level section to define ontology preferences per endpoint:

```yaml
# Ontology preferences for iterative mapping strategy
ontology_preferences:
  UKBB_PROTEIN:
    preferences:
      - ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
        priority: 1
      - ontology_type: "PROTEIN_GENE_NAME_ONTOLOGY"
        priority: 2
        
  ARIVALE_PROTEIN:
    preferences:
      - ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
        priority: 1
      - ontology_type: "PROTEIN_ENSEMBL_ONTOLOGY"
        priority: 2
      - ontology_type: "PROTEIN_GENE_NAME_ONTOLOGY"
        priority: 3
      - ontology_type: "PROTEIN_ENSEMBL_GENE_ONTOLOGY"
        priority: 4
      - ontology_type: "ARIVALE_PROTEIN_ID_ONTOLOGY"
        priority: 5
        
  # Similar for other endpoints...
```

## 5. Discussion on OntologyPreference Mechanism

The `OntologyPreference` mechanism should be integrated as follows:

1. **Configuration Level**: Add the `ontology_preferences` section as proposed above to explicitly define priority orders.

2. **MappingExecutor Integration**: 
   - The executor should read these preferences when identifying secondary types (Step 3 of the strategy)
   - Use the priority values to sort available secondary types before attempting conversions
   - This ensures the "first success wins" approach follows a predictable, configured order

3. **Relationship with EndpointRelationship**:
   - The primary shared ontology should still be determined by the `EndpointRelationship`
   - The preferences guide the fallback order when primary mapping fails

4. **Default Behavior**: If no preference is defined for an endpoint, the executor could:
   - Use a default order based on ontology reliability (e.g., prefer Ensembl over gene names)
   - Or require explicit configuration for all endpoints to avoid ambiguity

This integration ensures the iterative strategy can be tuned per endpoint while maintaining the systematic approach described in the strategy document.

## Conclusion

The current `protein_config.yaml` provides a good foundation but needs several enhancements to fully support the iterative mapping strategy:

1. Add missing ontology types (ENSEMBL_GENE)
2. Expand property mappings for comprehensive secondary identifier coverage
3. Add specialized conversion clients for secondary → primary mappings
4. Implement the OntologyPreference structure
5. Fix column reference inconsistencies

These modifications will enable the `MappingExecutor` to fully implement the sophisticated iterative strategy outlined in the documentation, maximizing mapping success across all 6 protein data sources.