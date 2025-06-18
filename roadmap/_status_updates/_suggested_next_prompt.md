# Suggested Next Work Session Prompt

## Context Brief
The biomapper project is currently blocked by a critical `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file` error. This prevents all database operations and pipeline executions. A detailed diagnostic prompt has been prepared to guide the next AI instance in resolving this issue.

## Initial Steps
1.  **CRITICAL:** Review the active diagnostic prompt at `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/2025-06-18-033559-fix-and-validate.md`. This file contains the full context and a step-by-step plan to resolve the database error.
2.  Review the final status update at `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_status_updates/2025-06-18-offboarding-summary.md` for a summary of the last session's accomplishments and the current blocker.

## Work Priorities

### Priority 1: Resolve the SQLite Database Connection Error
- **This is the only priority.** No other work can proceed until the database is accessible.
- Follow the detailed instructions in the active prompt file to diagnose and fix the issue, which is likely in `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/db/session.py`.

### Priority 2: Validate the `StrategyAction` Refactor
- Once the database connection is fixed, execute the validation steps outlined in the active prompt:
  1.  Run `python scripts/setup_and_configuration/populate_metamapper_db.py`
  2.  Run `python scripts/main_pipelines/run_full_ukbb_hpa_mapping.py`

## References
- **Active Diagnostic Prompt:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/2025-06-18-033559-fix-and-validate.md`
- **Suspected Faulty File:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/db/session.py`
- **Configuration File:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/config.py`

## Workflow Integration
- The next step is not a typical development task but a focused debugging session. The entire workflow should be dedicated to executing the plan in the active prompt file. There is no need to design new features or prompts until this blocker is resolved.