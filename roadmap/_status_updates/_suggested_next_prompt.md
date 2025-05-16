# Suggested Next Work Session: Completing Metabolite Mapping Client Implementation

## Context Brief
We've successfully implemented the `UniChemClient` for metabolite identifier mapping, fixed the `is_one_to_many_target` flag bug in the bidirectional reconciliation script, and updated the validation terminology throughout the codebase. Now we need to implement the remaining metabolite mapping clients and develop the dedicated metabolite mapping scripts to complete the metabolite mapping infrastructure.

## Initial Steps
First, review `/home/ubuntu/biomapper/CLAUDE.md` to get up to speed on the overall project context, roadmap structure, and workflow procedures. Then review our recent progress in the latest status update to understand what has been accomplished and what remains to be done.

## Key References
- Latest status update: `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-16-metabolite-mapping-unichem-implementation.md`
- Metabolite mapping design: `/home/ubuntu/biomapper/roadmap/1_planning/ukbb_arivale_metabolite_mapping/design.md`
- UniChem client implementation: `/home/ubuntu/biomapper/biomapper/mapping/clients/unichem_client.py`
- UniChem tests: `/home/ubuntu/biomapper/tests/mapping/clients/test_unichem_client.py`
- Base client interface: `/home/ubuntu/biomapper/biomapper/mapping/clients/base_client.py`

## Work Priorities
1. Implement the `TranslatorNameResolverClient` for metabolite name resolution
   - Follow the design in the metabolite mapping plan
   - Use the same interface pattern as the `UniChemClient`
   - Create comprehensive unit tests

2. Implement the `UMLSClient` for concept mapping
   - Integrate with the UMLS API for metabolite concept mapping
   - Implement proper authentication and token management
   - Create unit tests with appropriate mocks

3. Create dedicated metabolite mapping scripts
   - Develop `/home/ubuntu/biomapper/scripts/map_ukbb_metabolites_to_arivale_metabolites.py`
   - Develop `/home/ubuntu/biomapper/scripts/map_ukbb_metabolites_to_arivale_clinlabs.py`
   - Ensure proper integration with the new mapping clients

## Workflow Integration
After reviewing the project context and understanding the current priorities, incorporate Claude into your workflow as an independent step. First, establish the requirements and API details for each client, then have Claude assist with implementation following the patterns established in the `UniChemClient`. For the mapping scripts, you could have Claude help generate initial implementations based on the existing protein mapping scripts, which you can then review and adapt as needed. This approach allows you to focus on architecture and integration decisions while leveraging Claude for implementation details.
