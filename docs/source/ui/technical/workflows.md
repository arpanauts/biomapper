# UI Workflows

This document describes the key workflows in the Biomapper UI using sequence diagrams.

## File Upload Workflow

The following diagram illustrates the workflow when a user uploads a file:

```mermaid
sequenceDiagram
    participant FileUpload
    participant App
    participant ColumnSelection
    
    FileUpload->>App: onFileUploaded(sessionId)
    App->>App: setSessionId(sessionId)
    App->>App: State update completes
    App->>App: useEffect triggers navigation
    App->>ColumnSelection: Renders with valid sessionId
    ColumnSelection->>API: fetchColumns(sessionId)
    API-->>ColumnSelection: Returns columns data
```

## Mapping Configuration Workflow

The following diagram shows the data flow during the mapping configuration process:

```mermaid
sequenceDiagram
    participant ColumnSelection
    participant MappingConfig
    participant API
    participant ResultView
    
    ColumnSelection->>MappingConfig: selectedColumns
    MappingConfig->>API: configureMappings(columns, options)
    API-->>MappingConfig: mappingId
    MappingConfig->>ResultView: Navigate with mappingId
    ResultView->>API: fetchResults(mappingId)
    API-->>ResultView: Returns mapping results
```

## State Management

The following diagram demonstrates the state management flow in the UI:

```mermaid
sequenceDiagram
    participant Component
    participant Store
    participant API
    
    Component->>Store: dispatch(action)
    Store->>Store: Reducer updates state
    Store-->>Component: Updated state via selector
    Component->>API: API call based on state
    API-->>Store: dispatch(successAction)
    Store-->>Component: Updated state with API response
```
