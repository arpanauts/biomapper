# Task: Refactor and Enhance Pydantic Models

**Source Prompt Reference:** Orchestrator-generated task to improve API documentation and validation.

## 1. Task Objective

To improve the Pydantic models used in the API. This involves adding detailed descriptions, examples, and using more specific types where appropriate. This will enrich the auto-generated OpenAPI documentation, making the API easier to understand and use.

## 2. Service Architecture Context

- **Primary Service:** `biomapper-api`
- **Files to Modify:** All files within `/home/ubuntu/biomapper/biomapper-api/app/models/`.

## 3. Task Decomposition

1.  **Review Existing Models:** Examine all Pydantic models in the `app/models/` directory.
2.  **Add Field Descriptions:** For each field in every model, add a clear and concise `description` using the `Field` function from Pydantic (e.g., `job_id: str = Field(description="The unique identifier for the mapping job.")`).
3.  **Add Model Examples:** For each model, add a `Config` inner class with a schema_extra that provides a complete, realistic example of the model's structure. This example will be shown in the `/api/docs` UI.
    ```python
    class MyModel(BaseModel):
        field: str

        class Config:
            schema_extra = {
                "example": {
                    "field": "example_value"
                }
            }
    ```
4.  **Use Specific Types:** Where applicable, use more specific types instead of generic ones. For example, use `datetime` for timestamps, `UUID` for UUIDs, etc.

## 4. Implementation Requirements

- Every field in every model should have a description.
- Every model should have a complete example.
- The changes should not break the existing functionality of the API.

## 5. Success Criteria and Validation

- All model files in `app/models/` are updated.
- The API starts correctly.
- When viewing the `/api/docs` page, the models now display descriptions for each field and have a full example payload visible.

## 6. Feedback Requirements

Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-06-refactor-pydantic-models.md`

Include:
-   **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED]
-   **Links to Artifacts:** Links to the modified model files.
-   **Screenshots:** Before and after screenshots of one of the models as rendered in the `/api/docs` UI to demonstrate the improvements.
