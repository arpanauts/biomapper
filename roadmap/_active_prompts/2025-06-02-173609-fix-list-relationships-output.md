# Task: Fix `list-relationships` CLI Output Formatting

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-02-173609-fix-list-relationships-output.md`

## 1. Objective

Modify the `biomapper metamapper list-relationships` CLI command, specifically its output formatting, to correctly display information for each relationship. The command currently runs but shows "N/A" for several fields because it attempts to print non-existent attributes.

## 2. Background

The `list-relationships` command queries the `endpoint_relationships` table and displays the results.
Previous fixes have addressed:
*   Ensuring the command connects to the correct, populated database.
*   Correcting the SQL query to use `r.id` instead of `r.relationship_id` for joins and grouping.

The current issue is that the `click.echo` statements in `/home/ubuntu/biomapper/biomapper/cli/metamapper_commands.py` are trying to display attributes like `name` and `created_at` which do not exist on the `EndpointRelationship` model or in the query results.

**Key Context:**

*   **File to Modify:** `/home/ubuntu/biomapper/biomapper/cli/metamapper_commands.py` (specifically the `list_relationships` function and its helper `_list_relationships_async`).
*   **Relevant Model (`EndpointRelationship` from `/home/ubuntu/biomapper/biomapper/db/models.py`):**
    ```python
    class EndpointRelationship(Base):
        __tablename__ = "endpoint_relationships"
        id = Column(Integer, primary_key=True)
        source_endpoint_id = Column(Integer, ForeignKey("endpoints.id"), nullable=False)
        target_endpoint_id = Column(Integer, ForeignKey("endpoints.id"), nullable=False)
        description = Column(Text)
        # ... other relationship attributes ...
    ```
*   **Schema of `endpoint_relationships` table (from `PRAGMA table_info`):**
    *   `id` (INTEGER, PK)
    *   `source_endpoint_id` (INTEGER)
    *   `target_endpoint_id` (INTEGER)
    *   `description` (TEXT)
*   **SQL Query in `_list_relationships_async` (provides `r` object):**
    ```sql
    SELECT r.*,
           COUNT(DISTINCT m.endpoint_id) as member_count
    FROM endpoint_relationships r
    LEFT JOIN endpoint_relationship_members m ON r.id = m.relationship_id
    GROUP BY r.id
    ORDER BY r.id
    ```
    This means each `r` object in the Python loop will have attributes `r.id`, `r.description`, `r.source_endpoint_id`, `r.target_endpoint_id`, and `r.member_count`.

## 3. Task Details: Modify `metamapper_commands.py`

In the file `/home/ubuntu/biomapper/biomapper/cli/metamapper_commands.py`, locate the `list_relationships` Click command and the `_list_relationships_async` helper function.

Make the following changes to the `click.echo` statements that print the table header and data rows:

1.  **Update the table header:**
    *   Change the current header:
        `click.echo(f"{'ID':<5} {'Name':<30} {'Members':<10} {'Created':<20}")`
    *   To a new header that reflects available data:
        `click.echo(f"{'ID':<5} {'Description':<60} {'Members':<10}")`
        (Adjust width of 'Description' as appropriate, e.g., 60 or 70, and update the separator line `'-' * X` accordingly).

2.  **Update the data row printing:**
    *   Change the current data row formatting logic:
        `click.echo(f"{str(r.id if hasattr(r, 'id') else 'N/A'):<5} {str(r.name if hasattr(r, 'name') else 'N/A'):<30} {str(r.member_count if hasattr(r, 'member_count') else 'N/A'):<10} {str(r.created_at if hasattr(r, 'created_at') else 'N/A'):<20}")`
    *   To print the actual available attributes: `id`, `description`, and `member_count`.
        Ensure `description` is handled gracefully if it's `None` (e.g., print an empty string).
        Example:
        `click.echo(f"{str(r.id):<5} {str(r.description if r.description else ''):<60} {str(r.member_count):<10}")`

## 4. Expected Outcome

After modification, running `poetry run biomapper metamapper list-relationships` should display a table with columns "ID", "Description", and "Members", populated with correct data from the `metamapper.db` database. "N/A" values for these specific fields should no longer appear.

## 5. Testing

Verify your changes by running:
`poetry run biomapper metamapper list-relationships --db-url sqlite+aiosqlite:////home/ubuntu/biomapper/metamapper.db`
Ensure the output is correctly formatted and displays actual data.

## 6. Feedback File

Upon completion of this task (successful or not), create a detailed Markdown feedback file in the following location:
`/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-fix-list-relationships-output.md`

Replace `YYYY-MM-DD-HHMMSS` with the UTC timestamp of when you complete this task.

The feedback file must include:
*   A summary of actions taken.
*   A diff of the changes made to `/home/ubuntu/biomapper/biomapper/cli/metamapper_commands.py`.
*   Confirmation of whether the `list-relationships` command produces the correct output after your changes. Include a small sample of the successful output if possible.
*   Any issues encountered during the process.
*   Any questions you have for the Project Manager (Cascade).
