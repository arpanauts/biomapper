# Biomapper Planning and Development Documents

This directory contains planning documents, fix plans, and migration strategies for the biomapper project.

## Planning Documents

### Active Fix Plans

- **[METABOLOMICS_PIPELINE_FIX_PLAN.md](METABOLOMICS_PIPELINE_FIX_PLAN.md)** (Aug 21, 2025)
  - Status: 🔧 In Progress
  - Discovery: Pipeline achieves only 15.2% coverage (not claimed 77.9%)
  - Decision: Fix broken Stages 2-4 before Stage 5 LIPID MAPS integration
  - Priority: High

- **[PIPELINE_FIX_SUMMARY.md](PIPELINE_FIX_SUMMARY.md)** (Aug 21, 2025)
  - Status: ✅ Fixes Applied
  - Issues fixed:
    - Client execution issue (endpoint mismatch)
    - Context parameter passing
  - Documents applied solutions and their effectiveness

### Future Work

- **[UV_MIGRATION_PLAN.md](UV_MIGRATION_PLAN.md)** (Aug 18, 2025)
  - Status: 📋 Planning Phase
  - Comprehensive migration strategy from Poetry to UV
  - Addresses 75+ dependencies, 1,297 tests
  - Priority: Low (future enhancement)

## Document Categories

### Fix Plans
Detailed plans for addressing identified issues and bugs.

### Migration Strategies
Long-term plans for technology stack updates and improvements.

### Implementation Summaries
Documentation of fixes applied and their outcomes.

## Status Legend

- 📋 **Planning Phase** - Document created, not yet implemented
- 🔧 **In Progress** - Actively being worked on
- ✅ **Completed** - Implementation finished
- ⏸️ **On Hold** - Postponed for future consideration

## Usage

These planning documents serve to:
1. Track planned improvements and fixes
2. Document decision-making processes
3. Provide implementation roadmaps
4. Record what was attempted and why

## Contributing

When adding new planning documents:
1. Use clear, descriptive filenames
2. Include creation date and status in the document
3. Update this INDEX.md with a brief description
4. Mark status clearly (Planning/In Progress/Completed)

## Note

These are living documents that may be updated as work progresses. Check individual document headers for the most recent update dates.