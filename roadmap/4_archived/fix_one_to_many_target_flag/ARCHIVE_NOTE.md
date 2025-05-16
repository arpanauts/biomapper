# Archive Note: One-to-Many Target Flag Bug Fix

**Date Archived:** 2025-05-15

## Reason for Archiving

This feature has been temporarily deprioritized in favor of focusing on the higher-priority UKBB-Arivale metabolite mapping work. 

## Current Status

The bug where the `is_one_to_many_target` flag is incorrectly set to TRUE for all records in the Phase 3 reconciliation output has been documented and understood. While this issue affects metadata tracking and reporting aspects, the core mapping functionality is working correctly.

## Impact of the Bug

The bug primarily affects reporting and metadata tracking, not the actual mapping functionality:
- It incorrectly identifies all target entities as having multiple source mappings
- It may affect canonical mapping selection in some edge cases
- It does not prevent successful mapping between entities

## Future Plans

This issue will be revisited after completing the metabolite mapping work. The goal is to first expand the Biomapper's capabilities to handle more entity types (proteins, metabolites, etc.) and then address metadata and reporting refinements like this issue.
