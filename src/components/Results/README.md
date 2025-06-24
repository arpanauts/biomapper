# Results Component

## Overview

The Results component displays the status and results of a biomapper mapping job. It polls the API for job status updates and displays the final results in a table format once the job is completed.

## Features

- **Real-time status polling**: Automatically polls for job status every 2 seconds
- **Progress visualization**: Shows progress percentage for running jobs
- **Results table**: Displays mapping results in a Mantine Table
- **Statistics display**: Shows total rows, mapped/unmapped counts, and success rate
- **Error handling**: Gracefully handles and displays errors
- **Download functionality**: Allows users to download results
- **Reset workflow**: Button to start a new mapping job

## Dependencies

- React
- Mantine UI (Table, Alert, Badge, Button, Card, etc.)
- Mantine Notifications
- Tabler Icons

## Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| apiService | ApiService | No | Service for API calls (will be injected) |
| appStore | AppStore | No | Global state store (will be injected) |

## API Service Interface

The component expects an apiService with the following methods:

```typescript
interface ApiService {
  getMappingStatus(jobId: string): Promise<MappingStatusResponse>;
  getMappingResults(jobId: string): Promise<MappingResult>;
  downloadResults(jobId: string): void;
}
```

## App Store Interface

The component expects an appStore with:

```typescript
interface AppStore {
  jobId: string | null;
  reset(): void;
}
```

## Job Status States

- `pending`: Job is queued
- `running`: Job is in progress
- `completed`: Job finished successfully
- `failed`: Job encountered an error

## Usage

```tsx
import Results from './components/Results/Results';

// With services injected
<Results apiService={apiService} appStore={appStore} />

// For testing without services
<Results />
```

## Testing

The component includes comprehensive tests covering:
- Initial rendering
- Polling behavior
- Progress updates
- Success state with results
- Error handling
- Download functionality
- Reset functionality
- Component unmounting

Run tests with:
```bash
npm test Results.test.tsx
```

## Example

See `Results.example.tsx` for a working demonstration with mock services showing different states:
- Running state with progress
- Completed state with results
- Failed state with error

## File Structure

```
src/components/Results/
├── Results.tsx          # Main component
├── Results.test.tsx     # Test suite
├── Results.example.tsx  # Example usage
└── README.md           # This file
```