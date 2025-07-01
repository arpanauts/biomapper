# Vision: Towards an Agent-Driven, Autonomous Mapping Platform

**Date:** 2025-06-29

## 1. Overview

This document outlines a long-term vision for the `biomapper` project, evolving it from a tool for executing pre-defined mapping pipelines into a flexible, autonomous platform where AI agents can reason about, plan, and execute complex metadata mapping tasks. This represents a shift from a static, human-driven process to a dynamic, agent-driven one.

The core of this vision is to leverage the service-oriented architecture we are building, exposing the `biomapper`'s capabilities through a clean API that can be used by higher-order AI agents.

## 2. The Three Levels of Agent-Driven Mapping

We envision a three-tiered approach to integrating AI agents into the mapping process, each building on the capabilities of the last.

### Level 1: Agent-Driven Action & Test Creation

This is the foundational level, focused on streamlining the development of the core building blocks (actions).

*   **Goal:** An AI agent can generate a new, fully functional `BaseStrategyAction` and its corresponding unit tests from a high-level natural language prompt.
*   **Agent Input:** A structured request specifying the action's purpose, required parameters, and expected behavior (e.g., "Create an action to query the MyGene.info API").
*   **Agent Workflow:**
    1.  Follow the `developing_new_action_types.md` guide.
    2.  Generate the action's Python module in `biomapper/core/strategy_actions/`.
    3.  Generate a corresponding test file in `tests/test_actions/`.
    4.  The agent validates its own work by running `pytest`.
*   **Benefit:** Radically accelerates the expansion of `biomapper`'s capabilities.

### Level 2: Agent-Driven Strategy Assembly

This level moves up the abstraction stack, with an agent acting as a "strategy assembler."

*   **Goal:** An AI agent can create a complete, valid `strategy.yaml` file to solve a specific, well-defined mapping problem.
*   **Agent Input:** A high-level objective (e.g., "Map UKBB protein assay IDs to HPA gene names").
*   **Agent Workflow:**
    1.  **Discover:** The agent queries a new `/api/actions` endpoint to get a list of all available action types and their schemas.
    2.  **Select & Sequence:** It reasons about which actions are needed and in what order.
    3.  **Configure & Chain:** It generates the YAML, ensuring the `output_context_key` of one step correctly feeds into the `input_context_key` of the next.
*   **Benefit:** Allows users to solve mapping problems without needing to know the low-level YAML syntax.

### Level 3: Autonomous Mapping Investigation (The "Planner" Agent)

This is the ultimate goal: a truly autonomous mapping agent that can figure out *how* to map two datasets with minimal human guidance.

*   **Goal:** An AI agent can, given two datasets, autonomously investigate them, devise a mapping plan, execute it, and analyze the results.
*   **Agent Input:** A very high-level request: "Map `DATASET_A` to `DATASET_B`."
*   **Agent Workflow (Planner/Executor Model):**
    1.  **Explore:** The agent uses foundational actions (e.g., `DESCRIBE_ENDPOINT`, `GET_SAMPLE_ROWS`) to understand the schemas and data.
    2.  **Hypothesize:** It identifies potential mapping pathways (e.g., "Column `uniprot_acc` in A looks like `uniprot_id` in B," or "I can bridge `gene_symbol` in A to `ensembl_id` in B via UniProt").
    3.  **Plan:** It generates a strategy YAML based on its hypothesis (leveraging the workflow from Level 2).
    4.  **Execute:** It submits the strategy to the `biomapper-api` for execution.
    5.  **Analyze & Refine:** It inspects the results. If the mapping fails or coverage is low, it can form a new hypothesis and try again (e.g., "Let's try resolving historical IDs").
*   **Benefit:** Creates a "zero-shot" mapping capability, where the system can solve novel mapping problems on its own.

## 3. Architectural Endpoint: An MCP Server for Autonomous Mapping

The ultimate embodiment of this vision is to expose the Level 3 Planner Agent as a resource on an MCP (Multi-Compute-Provider) server.

*   **Resource:** `mapping_investigation`
*   **User Interaction:** A user would simply `POST` a request to the MCP server, specifying the two endpoints to be mapped.
*   **Backend Process:** The MCP server would trigger the Planner Agent, which would autonomously carry out the entire investigation and execution process, returning the final mapped dataset to the user.

This architecture would transform `biomapper` into a powerful, general-purpose, and intelligent metadata mapping service.
