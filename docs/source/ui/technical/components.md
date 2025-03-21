# UI Components

This document describes the key components in the Biomapper UI.

## Core Components

### FileUpload

The `FileUpload` component handles file uploads and manages the upload process.

```typescript
// Key props
interface FileUploadProps {
  onFileUploaded: (sessionId: string) => void;
  allowedFileTypes: string[];
}
```

Key features:
- Drag-and-drop file upload
- Progress indicator
- File validation
- Error handling

### ColumnSelection

The `ColumnSelection` component allows users to select columns from their uploaded data.

```typescript
// Key props
interface ColumnSelectionProps {
  sessionId: string;
  onColumnsSelected: (columns: string[]) => void;
}
```

### MappingConfiguration

The `MappingConfiguration` component allows users to configure how their data should be mapped.

## Layout Components

### Navbar

The top navigation bar component that provides application-wide navigation.

### Sidebar

The sidebar component that provides context-specific navigation and options.

## Utility Components

### LoadingIndicator

A reusable loading indicator component.

### ErrorBoundary

A component that catches JavaScript errors anywhere in its child component tree and displays a fallback UI.

### Toast

A notification component for displaying success, error, and informational messages.
