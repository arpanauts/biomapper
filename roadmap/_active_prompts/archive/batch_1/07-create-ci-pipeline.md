# Task: Create a Basic CI Pipeline with GitHub Actions

**Source Prompt Reference:** Orchestrator-generated task to automate testing.

## 1. Task Objective

To create a basic Continuous Integration (CI) pipeline using GitHub Actions. This pipeline will automatically run the project's test suite (`pytest`) on every push to the main branch, ensuring code quality and preventing regressions.

## 2. Service Architecture Context

- **Primary Service:** This applies to the entire `biomapper` repository.
- **Files to Create:** `/home/ubuntu/biomapper/.github/workflows/ci.yml`

## 3. Task Decomposition

1.  **Create Workflow Directory:** Create the `.github/workflows` directory at the root of the `biomapper` project.
2.  **Create Workflow File:** Create a new file named `ci.yml` inside that directory.
3.  **Define Workflow:**
    *   **Name:** Give the workflow a descriptive name, like "Biomapper CI".
    *   **Trigger:** Configure the workflow to run on `push` events for the `main` or `master` branch, and also on `pull_request` events targeting that branch.
    *   **Jobs:** Define a single job named `test`.
    *   **Runner:** Configure the job to run on the latest Ubuntu runner (`runs-on: ubuntu-latest`).
    *   **Steps:**
        1.  **Checkout:** Use the `actions/checkout@v3` action to check out the repository code.
        2.  **Set up Python:** Use the `actions/setup-python@v4` action to install a specific version of Python (e.g., 3.11).
        3.  **Install Dependencies:** Add a step to install the project's dependencies. This will require installing dependencies for both the core `biomapper` library and the `biomapper-api` service. You may need to `pip install -e .` in both directories.
        4.  **Run Tests:** Add a step to run the test suite using the command `pytest` from the root directory.

## 4. Implementation Requirements

- The YAML file must be well-formed.
- The dependency installation steps must be correct for a clean environment.
- The test command must be run from the correct directory to discover all tests.

## 5. Success Criteria and Validation

- The `ci.yml` file is created in the correct location.
- After pushing this file to a GitHub repository, the action appears under the "Actions" tab and runs successfully.

## 6. Feedback Requirements

Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-07-create-ci-pipeline.md`

Include:
-   **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED]
-   **Links to Artifacts:** A link to the new `ci.yml` file.
-   **Summary of Changes:** A description of the CI pipeline's triggers and steps.
