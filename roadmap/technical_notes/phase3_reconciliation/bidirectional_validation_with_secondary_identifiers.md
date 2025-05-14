# Bidirectional Validation with Secondary Identifiers

## Overview

The bidirectional validation process in our mapping system determines whether a mapping between two entities is validated in both the forward and reverse directions. A key challenge in this process arises when primary identifiers are missing or malformed, but secondary identifiers (like gene names) are available and could be used for matching.

This document describes the enhancement to our bidirectional validation logic to properly handle these cases.

## Problem

In some scenarios, especially when dealing with biological entities like proteins, we may have:

1. A source entity with a missing primary ID but a valid secondary ID (e.g., gene name)
2. A mapping from this source entity to a target entity
3. A reverse mapping from the target entity back to the same source entity, but using the secondary ID

Without enhancements, these would be incorrectly classified as unidirectional mappings, when they should actually be classified as bidirectional matches.

## Solution

The bidirectional validation algorithm has been enhanced to:

1. Identify gene name columns and other secondary identifier columns in the input data
2. Build a local forward mapping dictionary that can use parsed gene names as a fallback
3. During validation, check if the gene name from a row matches a reverse mapping UKBB ID
4. For indirect matches, check if any reverse mapping IDs are in the local forward map
5. Include detailed information about the matching process in the validation details

## Implementation

The key implementation changes in `phase3_bidirectional_reconciliation.py` include:

1. Detection of gene name columns from common naming patterns
2. Construction of a local forward mapping dictionary that includes mappings via gene names
3. Enhanced matching logic that checks multiple paths for bidirectional validation
4. Additional validation details in the JSON output indicating gene name matches

## Example

Consider this scenario:

**Phase 1 (Forward) Mapping:**
- Source ID: [MISSING]
- Gene Name: GENE3
- Target ID: ARIVALE3

**Phase 2 (Reverse) Mapping:**
- Source ID: ARIVALE3
- Target ID: GENE3 (matches the gene name from Phase 1)

Without enhancements, this would be classified as two unidirectional mappings.
With enhancements, it is correctly classified as a bidirectional match via the gene name.

## Testing

A test script `test_bidirectional_validation_fallback.py` has been created to verify:

1. Normal mappings with valid source IDs work as expected
2. Mappings with missing source IDs but valid gene names are correctly validated
3. Mappings with no valid identifiers remain non-bidirectional

## Future Improvements

1. Extend the algorithm to handle additional secondary identifier types
2. Add configurable matching options for different identifier types
3. Implement fuzzy matching for cases where identifiers have minor formatting differences