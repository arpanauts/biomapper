# Biomapper Hierarchical Endpoint Structure Status Update

## 1. Recent Accomplishments

- Implemented a hierarchical endpoint organization in the database schema
  - Added `parent_endpoint_id` and `endpoint_subtype` columns to the `endpoints` table
  - Created "Arivale" as a top-level endpoint to represent the entire multiomic dataset
  - Established proper parent-child relationships for data types within Arivale

- Created specialized property extraction configurations for multiple Arivale data types:
  - Metabolomics (existing MetabolitesCSV): HMDB, PubChem, ChEBI, and other identifiers
  - Clinical Labs: LOINC codes, lab test identifiers, and display names
  - Proteomics: UniProt IDs extracted from column names via pattern matching

- Updated SPOKE endpoint property extraction patterns from Cypher to AQL syntax
  - Converted all six compound identifier query patterns (ChEBI, HMDB, PubChem, DrugBank, ChEMBL, InChIKey)
  - Updated parameter syntax from `$id` to `@id` and comparison operators from `=` to `==`

- Created comprehensive migration scripts for database schema evolution:
  - `migrate_arivale_hierarchy.py`: Implements the hierarchical endpoint structure
  - `update_spoke_to_aql.py`: Updates SPOKE queries from Cypher to AQL

## 2. Current Project State

- **Enhanced Database Schema**: Successfully implemented and migrated to the hierarchical endpoint structure with parent-child relationships
  - Top-level endpoints (e.g., Arivale, SPOKE) represent complete datasources
  - Child endpoints (e.g., MetabolitesCSV, ClinicalLabsCSV, ProteomicsCSV) represent specific data types
  - Property extraction configurations established for each data type

- **Multiple Omics Integration**: Set up structure for handling multiple omic data types from Arivale
  - Metabolomics data with chemical compound identifiers (HMDB, PubChem, etc.)
  - Clinical labs data with LOINC codes and lab test identifiers
  - Proteomics data with UniProt identifiers extracted from column patterns

- **Query Language Migration**: Successfully updated SPOKE endpoint property extraction patterns to use AQL
  - All compound identifier queries now use AQL syntax
  - Maintains compatibility with the existing mapping framework

- **Relationship Management**: Established foundation for flexible relationship definitions at different levels of the hierarchy
  - Can define relationships between top-level datasets
  - Can define more specific relationships between individual data types

## 3. Technical Context

### Key Architectural Decisions

1. **Hierarchical Endpoint Structure**: 
   - Implemented a parent-child relationship in the endpoints table rather than creating separate tables
   - This approach maintains backward compatibility with existing code while adding conceptual clarity
   - Added `parent_endpoint_id` (foreign key to endpoints) and `endpoint_subtype` columns

2. **Special Property Extraction for Proteomics**:
   - Developed a pattern-based approach to extract UniProt IDs from column names
   - Column names like "CAM_P00441" or "ONC2_P08069" are parsed to extract "P00441" or "P08069" as UniProt IDs
   - This allows mapping between protein identifiers without requiring a separate mapping table

3. **AQL for SPOKE Queries**:
   - Migrated from Cypher to AQL for SPOKE graph queries
   - Standard patterns established for entity lookups (`FOR c IN Compound FILTER c.identifier == @id`)
   - Maintains the same functionality while using the appropriate query language

### Database Schema Enhancements

The enhanced hierarchical structure is implemented with minimal changes to the existing schema:

```sql
-- Added columns to endpoints table for hierarchical relationship
ALTER TABLE endpoints ADD COLUMN parent_endpoint_id INTEGER REFERENCES endpoints(endpoint_id);
ALTER TABLE endpoints ADD COLUMN endpoint_subtype TEXT;
```

This approach allows for queries like:

```sql
-- Find all data types within Arivale
SELECT * FROM endpoints 
WHERE parent_endpoint_id = (SELECT endpoint_id FROM endpoints WHERE name = 'Arivale');

-- Find all relationships involving any Arivale data type
SELECT r.* FROM endpoint_relationships r
JOIN endpoint_relationship_members m ON r.relationship_id = m.relationship_id
JOIN endpoints e ON m.endpoint_id = e.endpoint_id
WHERE e.parent_endpoint_id = (SELECT endpoint_id FROM endpoints WHERE name = 'Arivale');
```

## 4. Next Steps

### Immediate Tasks

1. **Complete Property Extraction Configurations**:
   - Further refine the property extraction patterns for each data type
   - Validate extraction patterns with actual data samples
   - Add transform methods for specialized data formats if needed

2. **Implement EndpointManager Class**:
   - Develop the `EndpointManager` class that understands the hierarchical relationship
   - Add methods to retrieve endpoints by parent, by data type, etc.
   - Create utility functions for navigating the endpoint hierarchy

3. **Extend Relationship Dispatcher**:
   - Modify the `RelationshipDispatcher` to work with the hierarchical structure
   - Implement logic to determine which level of the hierarchy to use for relationships
   - Add support for defining relationships at both parent and child levels

4. **Update CLI Commands**:
   - Enhance CLI to support operations on the hierarchical endpoint structure
   - Add commands to list all data types within a parent endpoint
   - Create commands to manage relationships at different levels of the hierarchy

### Priorities for Coming Week

1. Test the hierarchical structure with actual mapping operations
2. Implement the `EndpointManager` class with hierarchy support
3. Update the CLI to work with the hierarchical structure
4. Create documentation for the hierarchical endpoint design

### Potential Challenges

- Ensuring backward compatibility with existing code that expects flat endpoint structure
- Balancing flexibility of the hierarchical model with query performance
- Managing the complexity of relationships that can exist at multiple levels of the hierarchy

## 5. Open Questions & Considerations

1. **Relationship Definition Level**:
   - At what level should relationships primarily be defined - parent or child?
   - Should we support automatic relationship inheritance from parent to children?
   - How do we handle conflicts between parent and child relationship definitions?

2. **Property Inheritance**:
   - Should child endpoints inherit property preferences from their parents?
   - Should property extraction configurations follow a hierarchical override pattern?
   - How do we balance flexibility with maintainability for large numbers of child endpoints?

3. **Endpoint Subtype Standardization**:
   - Should we establish a controlled vocabulary for endpoint_subtype?
   - How do we categorize and standardize the various omic data types?
   - Should we create a lookup table for standard data types and their characteristics?

4. **Scaling Considerations**:
   - How will this approach scale with hundreds of child endpoints under a parent?
   - Should we implement lazy loading or pagination for large endpoint hierarchies?
   - What indexes should be added to optimize queries involving the hierarchy?

5. **Migration Strategy**:
   - What's the best approach for migrating existing mapping caches to work with the hierarchical structure?
   - How do we update existing code to be aware of the hierarchy?
   - Should we provide both flat and hierarchical views of the endpoints for transitioning?

6. **User Interface Considerations**:
   - How should the hierarchical structure be represented in the user interface?
   - Should we use a tree view, breadcrumbs, or another approach?
   - How do we make the complexity of the hierarchy manageable for users?
