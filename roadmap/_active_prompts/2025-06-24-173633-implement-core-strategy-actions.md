Task: Implement Core Processing Components for UKBB-HPA Protein Dataset Mapping
Source Prompt Reference: This task is defined by the prompt: /home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-24-173633-implement-core-strategy-actions.md

1. Task Objective
The objective is to implement and test two new StrategyAction classes required for the UKBB-HPA protein metadata mapping pipeline. These components will handle critical protein data preprocessing and analysis steps within the new service-oriented architecture for bioinformatics research.

CompositeIdSplitter: A reusable component to split protein identifiers that contain multiple UniProt IDs in a single string (e.g., "Q14213_Q8NEV9").
DatasetOverlapAnalyzer: A reusable component to compare two sets of protein identifiers and calculate intersection statistics between proteomic datasets.

2. Service Architecture Context
Primary Service: biomapper (core library for proteomic data processing)
API Endpoints Required: None. This task is focused on developing components for the core bioinformatics library.
Service Dependencies: None.
Configuration Files: No configuration files will be modified directly in this task. These components will be referenced later in configs/ukbb_hpa_analysis_strategy.yaml.

3. Prerequisites
[ ] The BaseStrategyAction class exists at /home/ubuntu/biomapper/biomapper/core/strategy_actions/base_action.py.

4. Task Decomposition
Create CompositeIdSplitter Component:

Create a new file: /home/ubuntu/biomapper/biomapper/core/strategy_actions/composite_id_splitter.py.
Implement the CompositeIdSplitter class, inheriting from BaseStrategyAction.
Create Unit Tests for CompositeIdSplitter:

Create a new test file: /home/ubuntu/biomapper/tests/unit/test_composite_id_splitter.py.
Write unit tests to verify its functionality, including handling of different delimiters, empty inputs, and protein metadata lineage recording.
Create DatasetOverlapAnalyzer Component:

Create a new file: /home/ubuntu/biomapper/biomapper/core/strategy_actions/overlap_analyzer.py.
Implement the DatasetOverlapAnalyzer class, inheriting from BaseStrategyAction.
Create Unit Tests for DatasetOverlapAnalyzer:

Create a new test file: /home/ubuntu/biomapper/tests/unit/test_overlap_analyzer.py.
Write unit tests to verify its functionality, including protein set intersection calculation and statistics generation.

5. Implementation Requirements
CompositeIdSplitter
File: /home/ubuntu/biomapper/biomapper/core/strategy_actions/composite_id_splitter.py
Class: CompositeIdSplitter(BaseStrategyAction)
__init__(self, params: dict):
Requires input_context_key, output_context_key, and delimiter from params.
Optionally accepts track_metadata_lineage (default False).
async def execute(self, context: dict, executor: 'MappingExecutor') -> dict:
Retrieves a list of protein identifiers from context[self.input_context_key].
Splits each UniProt protein identifier by the delimiter.
Flattens the list of lists into a single list of unique protein identifiers.
If track_metadata_lineage is True, it should store the mapping from the original composite protein ID to its split components in the context.
Stores the resulting list in context[self.output_context_key].

DatasetOverlapAnalyzer
File: /home/ubuntu/biomapper/biomapper/core/strategy_actions/overlap_analyzer.py
Class: DatasetOverlapAnalyzer(BaseStrategyAction)
__init__(self, params: dict):
Requires dataset1_context_key, dataset2_context_key, and output_context_key from params.
Optionally accepts dataset1_name (default 'dataset1'), dataset2_name (default 'dataset2'), and generate_statistics (default False).
async def execute(self, context: dict, executor: 'MappingExecutor') -> dict:
Retrieves two lists of protein identifiers from the context.
Calculates the intersection of the two protein datasets.
If generate_statistics is True, it computes counts (original, unique, overlap) and percentages for the protein set comparison.
Stores the results (the overlapping protein set and optionally statistics) in context[self.output_context_key].

Testing Requirements
Unit tests must be self-contained and not require any external services or files.
Use pytest for testing.
For CompositeIdSplitter, test with various delimiters, multiple splits in one protein ID, and cases where no splitting occurs.
For DatasetOverlapAnalyzer, test with full overlap, partial overlap, and no overlap scenarios between protein datasets.

6. Scientific Context
UK Biobank (UKBB): A large-scale biomedical database containing protein expression data from human samples
Human Protein Atlas (HPA): A comprehensive resource for protein expression and localization data
Purpose: This analysis maps protein metadata between these two major proteomic research databases to identify shared protein entries and facilitate cross-dataset comparative studies in biomedical research.

7. Error Recovery Instructions
If any required parameters are missing during component initialization, raise a ValueError.
Follow standard Python debugging practices. Use logging to trace execution flow if necessary.

8. Success Criteria and Validation
Task is complete when:

[ ] The composite_id_splitter.py and overlap_analyzer.py files are created in the correct directory.
[ ] The corresponding test files are created with comprehensive unit tests.
[ ] Running pytest on the tests/unit/ directory passes without errors.

9. Deployment Considerations
These are core library components for bioinformatics analysis. Once implemented and tested, the biomapper-api service will need to be restarted to recognize and use these new components in a protein mapping workflow.

10. Feedback Requirements
Create a detailed Markdown feedback file at: [PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-implement-core-strategy-actions.md

Include:

Execution Status: [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED]
Completed Subtasks: Checklist of completed items from section 4.
Links to Artifacts: Direct links to the four new files created.
Test Output: A copy of the pytest output showing that all new tests passed.