# Prompt: Create Resource Metadata System Architecture Document

## Task Description
Create a comprehensive architecture document titled `resource_metadata_system.md` to be saved in `/home/ubuntu/biomapper/docs/architecture/`. This document should outline a vision and plan for a robust system within Biomapper to manage and leverage rich metadata associated with various biological entities and mapping resources.

The system should consider:
1.  Metadata derivable from the `PubChemRAGMappingClient` (both current and planned enhancements). This includes information from Qdrant payloads, PubChem API enrichments (as detailed in `/home/ubuntu/biomapper/roadmap/1_planning/rag_mapping_feature/design.md`), and potential LLM justifications.
2.  Integration with the existing `metamapper.db` and `MappingExecutor` framework.
3.  Broader needs for storing and using diverse metadata across different mapping paths and data sources in Biomapper.

## Input Files & Context
*   **Current RAG Client Summary:** `/home/ubuntu/biomapper/roadmap/3_completed/pubchem_rag_mapping_client/summary.md`
*   **Advanced RAG Planning - Design (for metadata enrichment ideas):** `/home/ubuntu/biomapper/roadmap/1_planning/rag_mapping_feature/design.md`
*   **Advanced RAG Planning - Specification:** `/home/ubuntu/biomapper/roadmap/1_planning/rag_mapping_feature/spec.md`
*   **Latest Status Update (for context on RAG client):** `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-23-210820-session-summary.md` (particularly "Open Questions & Considerations")
*   **Relevant Memories (for existing DB/architecture context):**
    *   MEMORY[fdf2eb62-5c45-415a-973e-2e3029072c97] (DB separation)
    *   MEMORY[c3f81352-4385-4f0e-b00f-c46577cbec43] (populate_metamapper_db.py example)
    *   MEMORY[52fb2518-677d-468d-9803-6873261b7654] (metamapper.db contents)
    *   MEMORY[7ea9f333-e8d5-4d18-8429-af5941a93929] (EntityMapping new fields)
    *   MEMORY[f5d191cd-b5ec-4d9b-ab87-543799a0071c] (Endpoint/Resource architecture)

## Key Areas to Cover in the Document
*   **Types of Metadata:** Identify the various types of metadata to be managed (e.g., confidence scores, similarity scores, source database links, synonyms, structural information, LLM justifications, data quality flags, provenance).
*   **Storage Strategy:**
    *   Propose how and where this metadata should be stored. Consider extensions to `metamapper.db`, `mapping_cache.db` (e.g., `EntityMapping` model), or potentially new storage solutions.
    *   Discuss data models for representing this metadata.
*   **Access and Integration:**
    *   How will components like `MappingExecutor`, mapping clients, and reconciliation scripts access and utilize this metadata?
    *   How can metadata influence mapping path selection or result ranking?
*   **RAG-Specific Metadata:** Detail how metadata from the `PubChemRAGMappingClient` (e.g., Qdrant payloads, enriched PubChem data, LLM outputs from the advanced design) fits into this system.
*   **User-Facing Implications:** How might this richer metadata be presented to users or used in reports?
*   **Scalability and Maintainability:** Address concerns for managing a growing volume and variety of metadata.
*   **Roadmap:** Suggest phased implementation if applicable.

## Expected Output
*   A new Markdown file: `/home/ubuntu/biomapper/docs/architecture/resource_metadata_system.md`.
    *   Ensure the `/home/ubuntu/biomapper/docs/architecture/` directory is created if it doesn't exist.
*   The document should be well-structured, clear, and provide a forward-looking vision.

## Feedback
Upon completion, create a feedback file in `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-resource-metadata-sys.md` (use UTC timestamp for feedback generation time). The feedback should summarize the work done, link to the created document, and note any challenges or assumptions made.

## Source Prompt Reference
This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-05-23-213400-prompt-create-resource-metadata-sys-plan.md`
