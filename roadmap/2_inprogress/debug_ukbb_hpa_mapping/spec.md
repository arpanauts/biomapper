# Specification: Debug UKBB to HPA Protein Mapping Failures

## 1. Overview
This document specifies the requirements for debugging the UKBB to HPA protein mapping process, which currently results in zero successful mappings.

## 2. Problem Statement
The `map_ukbb_to_hpa.py` script, utilizing `MappingExecutor` and configurations from `populate_metamapper_db.py`, fails to map any of the initial 10 test records from UKBB protein data to HPA protein data.

## 3. Scope
- Identify the cause(s) of the mapping failures.
- Implement corrective actions in the relevant scripts or configurations.
- Ensure the test set of 10 records can be successfully mapped.
- Provide clear logging or feedback mechanisms to understand mapping outcomes.

## 4. Requirements
- **R1:** The system must correctly identify matching UniProtKB ACs between the UKBB source and the HPA target data.
- **R2:** Configuration files (e.g., `populate_metamapper_db.py`) must accurately define endpoints, resources, and property extraction logic for both UKBB and HPA.
- **R3:** Data file paths specified in configurations must be correct and accessible.
- **R4:** The `MappingExecutor` must be correctly invoked and utilized by `map_ukbb_to_hpa.py`.
- **R5:** The debugging process should yield actionable insights, leading to a fix that enables successful mapping for the test dataset.

## 5. Acceptance Criteria
- **AC1:** At least one of the 10 test UKBB protein records successfully maps to an HPA protein record.
- **AC2:** The root cause of the "0 successful mappings" issue is identified and documented.
- **AC3:** Any code or configuration changes are committed and explained.
