# Development Status Update: UI Consistency Evaluation

## 1. Recent Accomplishments

- Completed comprehensive analysis of the entity mapping and semantic search UI components, identifying key differences in approach and implementation
- Evaluated the workflow paradigms for both features - entity mapping using a linear step-based process vs. semantic search using a tab-based structure
- Identified specific inconsistencies in component layouts, visual design, terminology, and user guidance
- Developed recommendations for a unified navigation structure that preserves feature-specific functionality
- Established a clear distinction between embedding and semantic search as separate but related features

## 2. Current Project State

- The biomapper-ui implements two fundamentally different user experiences:
  - Entity Mapping: Step-based linear workflow with configuration options targeting ontologies
  - Semantic Search: Tab-based interface with embedding and search functions combined
- Current implementation creates cognitive load when switching between features due to inconsistent patterns
- Both features function as designed but lack cohesiveness in the overall application experience
- Embedding functionality is currently nested under Search, creating potential confusion about their relationship
- The application uses consistent component libraries (Mantine) but applies them differently across features

## 3. Technical Context

- Key architectural decision: Establishing a unified navigation pattern with primary features at the top level
- Recommended hierarchy: Entity Mapping | Embedder | Semantic Search (ordered by workflow sequence)
- Biomapper component structure currently separates:
  - MappingConfig and Results components for entity mapping
  - EmbedDataPage, SearchPage, and SearchResults for semantic search
- Both features leverage the same backend API services but present different user interfaces for configuration
- Entity mapping uses session storage for state persistence between steps, while semantic search treats operations as independent

## 4. Next Steps

1. Refactor navigation structure to create top-level primary features:
   - Move Embedder from being a tab within Search to a primary navigation item
   - Place Embedder before Semantic Search to reflect natural workflow progression
   - Maintain Entity Mapping as a separate primary feature

2. Standardize visual presentation:
   - Align card layouts, form elements, and results visualization
   - Create consistent patterns for status indicators and progress tracking
   - Standardize terminology across features

3. Enhance cross-feature integration:
   - Add "Search this collection" button after completing embedding jobs
   - Maintain distinct purposes while creating logical connections
   - Implement consistent help and guidance systems

4. Improve workflow consistency:
   - Standardize file upload and server file selection interfaces
   - Align configuration patterns while preserving feature-specific options
   - Create consistent results visualization with feature-appropriate content

## 5. Open Questions & Considerations

- How much should the linear workflow of entity mapping influence the semantic search interface?
- What is the right balance between guided experiences and direct access to functionality?
- Should collection management be a separate feature area or remain within the Embedder section?
- How to handle users with existing vector databases who want to bypass the embedding step?
- Is there value in creating cross-feature workflows where mapped entities could be used for semantic searches?
- What visual design patterns should be standardized vs. kept feature-specific?
