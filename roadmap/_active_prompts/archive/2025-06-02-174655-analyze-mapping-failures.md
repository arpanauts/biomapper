# Task: Deep Dive Analysis of Mapping Failures

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-02-174655-analyze-mapping-failures.md`

## 1. Objective

To perform a detailed investigation into the root causes of the low mapping success rate (currently ~0.2-0.5%) in the Biomapper project. This involves selecting a representative failing mapping case, tracing its execution, and identifying specific points of failure and contributing factors.

The primary output will be a comprehensive analysis report.

## 2. Background

The Biomapper project aims to map identifiers between various biological and clinical datasets. Despite functional components, the overall end-to-end mapping success rate is critically low. Understanding these failures at a granular level is essential for devising effective solutions.

**Key Areas to Investigate:**
*   Input data quality (e.g., malformed identifiers, ambiguous terms).
*   Mapping logic within `MappingExecutor`, `OntologyMapper`, and specific client implementations.
*   Effectiveness of different mapping strategies (direct lookup, path-based, secondary ID lookups).
*   Limitations of ontologies and external resources (e.g., missing synonyms, outdated entries, API rate limits, historical ID resolution issues – see MEMORY[e6278ce7-18d9-4677-ada7-2910782148c7], MEMORY[c82f0648-ebe4-487f-b43d-210bc06a0529]).
*   Role of `metamapper.db` configuration in the success or failure of mappings.

**Relevant Project Files & Context:**
*   Core mapping logic:
    *   `/home/ubuntu/biomapper/biomapper/mapping/executor.py` (MappingExecutor)
    *   `/home/ubuntu/biomapper/biomapper/mapping/ontology_mapper.py`
    *   `/home/ubuntu/biomapper/biomapper/resources/clients/` (various client implementations)
*   Database models & session:
    *   `/home/ubuntu/biomapper/biomapper/db/models.py`
    *   `/home/ubuntu/biomapper/biomapper/db/session.py`
*   Configuration:
    *   `/home/ubuntu/biomapper/biomapper/config.py`
    *   The `metamapper.db` SQLite database itself (schema described by models.py).
*   Known issues (refer to project memories like MEMORY[37e78782-dd9b-4c37-b305-9c17a323373c] for context on data quality and UniProt).

## 3. Task Details

### 3.1. Select/Define a Representative Failing Case
*   If specific examples of failing (source_id, source_ontology, target_ontology) tuples are available from logs or prior analysis, use one.
*   Otherwise, construct a plausible failing scenario based on known problematic patterns (e.g., mapping a gene name that is known to be ambiguous or poorly formatted to UniProtKB AC, or attempting to map an outdated UniProt ID).
*   Clearly document the chosen failing case in your report.

### 3.2. Trace and Analyze the Mapping Attempt
For the selected failing case:
*   Simulate or trace its path through the `MappingExecutor`.
*   Detail which mapping strategies are attempted and in what order.
*   Identify the exact step where the mapping fails or produces an incorrect result.
*   Examine the state of relevant variables, API calls made (and their responses), and database queries performed during the attempt.

### 3.3. Investigate Contributing Factors
*   **Data Quality:** Assess the quality of the source identifier. Is it malformed, ambiguous, or using an unexpected format?
*   **Ontology/Resource Limitations:** For the specific ontologies/resources involved, are there known limitations (e.g., incomplete coverage, outdated data, poor synonym matching for the given identifier)?
*   **Mapping Logic:** Is there a flaw in the Biomapper's logic for this type of mapping? Is a path chosen incorrectly? Is a secondary lookup not triggered when it should be?
*   **Configuration (`metamapper.db`):** Is the `metamapper.db` correctly configured for the entities and relationships involved in this failing case? Are relevant `OntologyPath` entries, `EndpointPropertyConfig`, etc., present and accurate?

### 3.4. Document Findings
Compile all findings into a detailed Markdown report.

## 4. Deliverables

### 4.1. Main Analysis Report
*   **Location:** `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/YYYY-MM-DD-HHMMSS-mapping-failure-analysis-report.md` (replace timestamp).
*   **Content:**
    *   **Introduction:** Briefly state the purpose of the analysis.
    *   **Selected Failing Case:** Detailed description of the (source_id, source_ontology, target_ontology) and why it was chosen/constructed.
    *   **Execution Trace:** Step-by-step account of how Biomapper attempted to map this identifier.
    *   **Point(s) of Failure:** Clear identification of where and why the mapping failed.
    *   **Analysis of Contributing Factors:**
        *   Data Quality Issues
        *   Ontology/Resource Limitations
        *   Biomapper Logic Issues
        *   Configuration Issues (`metamapper.db`)
    *   **Hypotheses for Failure:** Summarize the most likely reasons for the failure.
    *   **Potential Solutions/Next Steps (High-Level):** Suggest (without implementing) potential ways this specific failure (and similar ones) might be addressed.
    *   **Supporting Evidence:** Include relevant code snippets (from Biomapper or hypothetical API responses), log excerpts (if applicable), or db query results that support your analysis.

### 4.2. Standard Feedback File
*   **Location:** `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-mapping-failure-analysis.md` (replace timestamp).
*   **Content:**
    *   Summary of actions taken to produce the main report.
    *   Confirmation of the main report's creation and its full path.
    *   Any significant challenges encountered during the analysis itself.
    *   Any questions for the Project Manager (Cascade).

## 5. Tools and Permissions
*   You will likely need to read various Python files from the `/home/ubuntu/biomapper/` directory.
*   You will need permission to write the two Markdown files to their specified locations. Ensure the target directory `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/` exists or can be created.
