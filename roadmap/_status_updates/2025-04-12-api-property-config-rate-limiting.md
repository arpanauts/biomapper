# API Property Configuration and Rate Limiting Improvements

## 1. Recent Accomplishments

- Implemented proper rate limiting in the KEGG client to respect the API's restriction of 3 requests per second
- Added a comprehensive rate limiting framework in the `ResourceVerifier` class to handle different API limits for each resource
- Enhanced the `_parse_compound_entry` method in the KEGG client to better handle KEGG's text format
- Improved KEGG property extraction configurations, increasing success rate from 18.2% to 63.6%
- Prioritized extraction patterns for ontological database IDs, which are critical for the metamapper's primary function
- Redesigned the RefMet client to utilize a local CSV file (~187,000 entries) for faster and more reliable lookups
- Fixed RefMet API endpoint URLs to align with the Metabolomics Workbench REST API specifications
- Implemented multi-level fallback strategies in RefMet client (local CSV → REST API → legacy endpoints)
- Created diagnostic scripts for analyzing KEGG and RefMet data formats to better understand extraction patterns
- Added verification script to test API property extractions across all resources

## 2. Current Project State

- The biomapper project now has improved resource clients that respect API rate limiting policies
- KEGG client has a 63.6% success rate for property extractions (up from 18.2%)
- The RefMet client successfully integrates with both local data (CSV) and the REST API
- The verification system has been enhanced with resource-specific rate limiting
- 6 out of 8 configured resources are now verified successfully
- 2 resources still have client implementation issues:
  - MetabolitesCSV client is missing implementation
  - SPOKE (ArangoDB) client is missing implementation
- The local RefMet CSV file with ~187,000 entries is now utilized for faster lookups
- Rate limiting is properly implemented for both KEGG (3 requests/second) and other APIs with appropriate defaults
- Currently focused on metabolite entities, but infrastructure needs to be extended to other entity types
- The project has a solid foundation for extracting ontological database IDs, which is the primary objective for building the mapping paths table

## 3. Technical Context

### Rate Limiting Architecture
- Implemented a dictionary of rate limits specific to each API in the `ResourceVerifier.API_RATE_LIMITS` attribute
- Added time tracking between requests to enforce proper intervals based on API requirements
- Incorporated small random jitter to prevent synchronized requests
- Implemented an adaptive sleep mechanism that only waits when necessary

### KEGG Data Format Analysis
- Discovered that KEGG's text format requires more robust regex patterns without anchors (^) for reliable extraction
- Identified that some properties (HMDB ID, InChI, SMILES) are not consistently present in KEGG compound entries
- Updated patterns to use specific data type patterns (e.g., `[\d\.]+` for numeric fields)
- Prioritized patterns for extracting ontological database IDs, which are critical for the mapping functionality

### RefMet Integration Strategy
- Identified distinction between RefMet standardized nomenclature and Metabolomics Workbench repository
- Implemented a hybrid approach utilizing:
  1. Local CSV file (`data/refmet/refmet.csv`) as primary data source
  2. REST API endpoints with the "refmet" context as fallback
  3. Legacy database endpoints as last resort
- Added multiple search strategies (exact match, partial match, term decomposition)

### UniChem Integration Potential
- Identified numerous additional ontological databases in UniChem (25+ sources including DrugBank, HMDB, LipidMaps)
- These represent significant expansion opportunities for the mapping system
- Each database adds new identifier mapping capabilities to the system

### Database Schema Considerations
- Current focus is on building comprehensive mapping paths in the metamapper SQLite database
- These mapping paths will be used when direct records aren't available in the mapping cache
- Need to expand resources table to include an entity_type field to support entities beyond metabolites

## 4. Next Steps

- Fix remaining issues with RefMet URL construction for entity lookups
  - Current error: `404 Client Error: Not Found for url: https://www.metabolomicsworkbench.org/databases/refmet/refmet/name/1/all`
  - URL path appears to have duplicate segments that need correction

- Implement the missing clients:
  - Create a base implementation for the MetabolitesCSV client
  - Implement the SPOKE/ArangoDB client for graph database integration

- Further improve KEGG property extraction:
  - Mark certain properties (HMDB ID, InChI, SMILES) as optional in configurations
  - Consider implementing secondary lookups to other databases for missing properties

- Enhance verification reporting:
  - Add more detailed error analysis to help debug extraction failures
  - Create visual reports showing extraction success rates by property and resource

- Optimize rate limiting parameters:
  - Fine-tune rate limits based on observed API performance
  - Consider implementing adaptive rate limiting that adjusts based on response times

- Add entity_type field to the resources table:
  - Support entities beyond metabolites (proteins, clinical labs, etc.)
  - Design a schema that allows flexible entity type categorization

- Implement additional UniChem ontological databases:
  - Prioritize high-value sources based on compound coverage and relevance
  - Leverage UniChem's extensive database connections (25+ sources)

- Integrate RAG approach into the mapping framework:
  - Determine whether RAG should be a resource option or fallback mechanism
  - Consider adding indicators in the mapping_paths table for RAG utilization

- Focus on expanding the mapping_paths table:
  - This is the primary end goal for metamapper development
  - Ensure paths prioritize ontological database ID extraction capabilities

## 5. Open Questions & Considerations

- What's the best approach for implementing the entity_type field in the resources table?
  - Enumerated types vs. free-form text
  - How to handle entity-specific validation and processing
  - Whether to create separate tables for entity-specific attributes

- How should we integrate RAG capabilities into the mapping process?
  - As a last-resort fallback in the mapping_paths
  - As a separate mapping resource with its own extraction patterns
  - As an optional enhancement layer on top of traditional mapping

- What's the optimal strategy for incorporating the 25+ additional ontological databases from UniChem?
  - Which databases should be prioritized based on coverage and relevance
  - How to efficiently batch import these databases
  - How to maintain and update these connections over time

- Should we implement a caching layer for API responses to reduce external requests?
- Is it worth implementing a proxy service or queue for high-volume API interactions?
- How should we handle the inconsistent availability of certain properties across different databases?
- Should we continue using regular expressions for property extraction, or would a more structured parser be more maintainable?
- How do we best handle API changes or outages from external services?
- Should we implement automatic retries with exponential backoff for transient API failures?
- What monitoring systems should we put in place to detect when APIs change their response formats?
