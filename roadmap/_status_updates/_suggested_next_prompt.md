# Suggested Next Work Session: UKBB-Arivale Metabolite Mapping Implementation

## Context Brief
We've completed the planning phase for UKBB-Arivale metabolite mapping with a comprehensive design that includes iterative mapping and fallback mechanisms. The documentation has been generalized to support multiple entity types, and we've identified specific client implementations needed for metabolite mapping. We're now ready to begin implementing the core infrastructure and clients.

## Initial Steps
First, review `/home/ubuntu/biomapper/CLAUDE.md` to get up to speed on the overall project context, roadmap structure, and workflow procedures. This document provides essential guidance for navigating the Biomapper project organization and understanding the development approach.

## Key References
- Generalized mapping strategy: `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/iterative_mapping_strategy.md`
- Metabolite mapping plan: `/home/ubuntu/biomapper/roadmap/1_planning/ukbb_arivale_metabolite_mapping/`
- Phase 3 reconciliation script (for bug fix): `/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py`
- Status update: `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-16-metabolite-mapping-strategy-planning.md`

## Work Priorities
1. Fix the `is_one_to_many_target` flag bug in `phase3_bidirectional_reconciliation.py`
2. Update validation terminology throughout the codebase ("UnidirectionalSuccess" → "Successful")
3. Implement the `UniChemClient` for metabolite identifier mapping
4. Create unit tests for the client

## Workflow Integration
After reviewing the project context and understanding the current priorities, incorporate Claude into your workflow as an independent step. First analyze and break down each task, then provide Claude with clear, focused instructions for specific components. For example, after understanding the validation terminology issue yourself, you could have Claude assist with the terminology standardization across the codebase. Similarly, once you've established the requirements for the `UniChemClient`, Claude could help implement specific methods while you maintain oversight of the overall architecture and integration.
