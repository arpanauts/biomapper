import React, { useState } from 'react';
import { MantineProvider, Container, Button, Group } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import Results from './Results';

// Mock API service for demonstration
class MockApiService {
  private progress = 0;
  private status: 'pending' | 'running' | 'completed' | 'failed' = 'pending';

  async getMappingStatus(jobId: string) {
    // Simulate progress
    if (this.status === 'pending') {
      this.status = 'running';
    } else if (this.status === 'running') {
      this.progress += 20;
      if (this.progress >= 100) {
        this.status = 'completed';
        this.progress = 100;
      }
    }

    return {
      status: this.status,
      progress: this.progress,
    };
  }

  async getMappingResults(jobId: string) {
    return {
      headers: ['Source ID', 'Source Name', 'Target ID', 'Target Name', 'Confidence'],
      rows: [
        {
          'Source ID': 'UKBB_001',
          'Source Name': 'Albumin',
          'Target ID': 'P02768',
          'Target Name': 'Serum albumin',
          'Confidence': '0.99',
        },
        {
          'Source ID': 'UKBB_002',
          'Source Name': 'Alpha-1-antitrypsin',
          'Target ID': 'P01009',
          'Target Name': 'Alpha-1-antitrypsin',
          'Confidence': '0.98',
        },
        {
          'Source ID': 'UKBB_003',
          'Source Name': 'Apolipoprotein A1',
          'Target ID': 'P02647',
          'Target Name': 'Apolipoprotein A-I',
          'Confidence': '0.97',
        },
        {
          'Source ID': 'UKBB_004',
          'Source Name': 'C-reactive protein',
          'Target ID': 'P02741',
          'Target Name': 'C-reactive protein',
          'Confidence': '0.99',
        },
        {
          'Source ID': 'UKBB_005',
          'Source Name': 'Unknown protein',
          'Target ID': '',
          'Target Name': '',
          'Confidence': '0.00',
        },
      ],
      statistics: {
        total_rows: 150,
        mapped_count: 142,
        unmapped_count: 8,
        mapping_rate: 0.9467,
      },
    };
  }

  downloadResults(jobId: string) {
    console.log(`Downloading results for job ${jobId}`);
    // In a real implementation, this would trigger a file download
    alert(`Download started for job ${jobId}`);
  }

  reset() {
    this.progress = 0;
    this.status = 'pending';
  }
}

// Mock app store for demonstration
class MockAppStore {
  jobId = 'demo-job-123';

  reset() {
    console.log('Resetting app state');
    // In a real implementation, this would clear all app state
    window.location.reload();
  }
}

// Example component demonstrating different states
export default function ResultsExample() {
  const [scenario, setScenario] = useState<'running' | 'completed' | 'failed'>('running');
  const [apiService] = useState(() => new MockApiService());
  const [appStore] = useState(() => new MockAppStore());

  // Create different API services for different scenarios
  const getApiService = () => {
    switch (scenario) {
      case 'failed':
        return {
          getMappingStatus: async () => ({
            status: 'failed' as const,
            error: 'Failed to connect to mapping service',
          }),
          getMappingResults: async () => null,
          downloadResults: () => {},
        };
      case 'completed':
        return {
          getMappingStatus: async () => ({
            status: 'completed' as const,
            progress: 100,
          }),
          getMappingResults: apiService.getMappingResults.bind(apiService),
          downloadResults: apiService.downloadResults.bind(apiService),
        };
      default:
        return apiService;
    }
  };

  return (
    <MantineProvider>
      <Notifications />
      <Container size="lg" py="xl">
        <Group mb="xl">
          <Button
            variant={scenario === 'running' ? 'filled' : 'outline'}
            onClick={() => setScenario('running')}
          >
            Running State
          </Button>
          <Button
            variant={scenario === 'completed' ? 'filled' : 'outline'}
            onClick={() => setScenario('completed')}
          >
            Completed State
          </Button>
          <Button
            variant={scenario === 'failed' ? 'filled' : 'outline'}
            onClick={() => setScenario('failed')}
          >
            Failed State
          </Button>
        </Group>

        <Results apiService={getApiService()} appStore={appStore} />
      </Container>
    </MantineProvider>
  );
}

// To run this example:
// 1. Import and render this component in your app
// 2. Click the buttons to see different states
// 3. In the "Running State", the component will poll and show progress
// 4. In the "Completed State", you'll see the results table and statistics
// 5. In the "Failed State", you'll see the error handling