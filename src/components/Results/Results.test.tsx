import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import Results from './Results';

// Mock API service
const mockApiService = {
  getMappingStatus: jest.fn(),
  getMappingResults: jest.fn(),
  downloadResults: jest.fn(),
};

// Mock app store
const mockAppStore = {
  jobId: 'test-job-123',
  reset: jest.fn(),
};

// Wrapper component with Mantine providers
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <MantineProvider>
    <Notifications />
    {children}
  </MantineProvider>
);

describe('Results Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders initial pending state', () => {
    render(
      <TestWrapper>
        <Results apiService={mockApiService} appStore={mockAppStore} />
      </TestWrapper>
    );

    expect(screen.getByText('Mapping Results')).toBeInTheDocument();
    expect(screen.getByText('Job Status:')).toBeInTheDocument();
    expect(screen.getByText('Pending')).toBeInTheDocument();
  });

  it('polls for status updates and shows progress', async () => {
    mockApiService.getMappingStatus
      .mockResolvedValueOnce({ status: 'running', progress: 25 })
      .mockResolvedValueOnce({ status: 'running', progress: 50 })
      .mockResolvedValueOnce({ status: 'running', progress: 75 });

    render(
      <TestWrapper>
        <Results apiService={mockApiService} appStore={mockAppStore} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('In Progress')).toBeInTheDocument();
      expect(screen.getByText('Progress: 25%')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText('Progress: 50%')).toBeInTheDocument();
    });
  });

  it('displays results when mapping is completed', async () => {
    const mockResults = {
      headers: ['ID', 'Name', 'Mapped ID'],
      rows: [
        { ID: '1', Name: 'Protein A', 'Mapped ID': 'P12345' },
        { ID: '2', Name: 'Protein B', 'Mapped ID': 'P67890' },
      ],
      statistics: {
        total_rows: 100,
        mapped_count: 95,
        unmapped_count: 5,
        mapping_rate: 0.95,
      },
    };

    mockApiService.getMappingStatus.mockResolvedValue({
      status: 'completed',
      progress: 100,
    });
    mockApiService.getMappingResults.mockResolvedValue(mockResults);

    render(
      <TestWrapper>
        <Results apiService={mockApiService} appStore={mockAppStore} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Completed')).toBeInTheDocument();
      expect(screen.getByText('Mapping Completed')).toBeInTheDocument();
    });

    // Check statistics
    expect(screen.getByText('100')).toBeInTheDocument(); // Total rows
    expect(screen.getByText('95')).toBeInTheDocument(); // Mapped count
    expect(screen.getByText('5')).toBeInTheDocument(); // Unmapped count
    expect(screen.getByText('95.0%')).toBeInTheDocument(); // Success rate

    // Check table headers
    expect(screen.getByText('ID')).toBeInTheDocument();
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Mapped ID')).toBeInTheDocument();

    // Check table data
    expect(screen.getByText('Protein A')).toBeInTheDocument();
    expect(screen.getByText('P12345')).toBeInTheDocument();
  });

  it('displays error state when mapping fails', async () => {
    mockApiService.getMappingStatus.mockResolvedValue({
      status: 'failed',
      error: 'Connection timeout',
    });

    render(
      <TestWrapper>
        <Results apiService={mockApiService} appStore={mockAppStore} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Failed')).toBeInTheDocument();
      expect(screen.getByText('Mapping Failed')).toBeInTheDocument();
      expect(screen.getByText('Connection timeout')).toBeInTheDocument();
    });
  });

  it('handles download button click', async () => {
    const mockResults = {
      headers: ['ID', 'Name'],
      rows: [{ ID: '1', Name: 'Test' }],
      statistics: {
        total_rows: 1,
        mapped_count: 1,
        unmapped_count: 0,
        mapping_rate: 1.0,
      },
    };

    mockApiService.getMappingStatus.mockResolvedValue({
      status: 'completed',
    });
    mockApiService.getMappingResults.mockResolvedValue(mockResults);

    render(
      <TestWrapper>
        <Results apiService={mockApiService} appStore={mockAppStore} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Download Results')).toBeInTheDocument();
    });

    const downloadButton = screen.getByText('Download Results');
    await userEvent.click(downloadButton);

    expect(mockApiService.downloadResults).toHaveBeenCalledWith('test-job-123');
  });

  it('handles reset button click', async () => {
    render(
      <TestWrapper>
        <Results apiService={mockApiService} appStore={mockAppStore} />
      </TestWrapper>
    );

    const resetButton = screen.getByText('Start New Mapping');
    await userEvent.click(resetButton);

    expect(mockAppStore.reset).toHaveBeenCalled();
  });

  it('stops polling when component unmounts', async () => {
    mockApiService.getMappingStatus.mockResolvedValue({
      status: 'running',
      progress: 50,
    });

    const { unmount } = render(
      <TestWrapper>
        <Results apiService={mockApiService} appStore={mockAppStore} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(mockApiService.getMappingStatus).toHaveBeenCalled();
    });

    const callCount = mockApiService.getMappingStatus.mock.calls.length;
    unmount();

    // Wait a bit to ensure no more calls are made
    await new Promise((resolve) => setTimeout(resolve, 3000));
    expect(mockApiService.getMappingStatus).toHaveBeenCalledTimes(callCount);
  });

  it('renders without services for testing', () => {
    render(
      <TestWrapper>
        <Results />
      </TestWrapper>
    );

    expect(screen.getByText('Mapping Results')).toBeInTheDocument();
    expect(screen.getByText('Start New Mapping')).toBeInTheDocument();
  });
});