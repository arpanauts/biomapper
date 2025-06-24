import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import MappingConfig from './MappingConfig';
import { useAppStore } from '../../store/appStore';
import { apiService } from '../../services/apiService';

// Mock the dependencies
jest.mock('../../store/appStore');
jest.mock('../../services/apiService');

// Helper to render component with providers
const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <MantineProvider>
      <Notifications />
      {component}
    </MantineProvider>
  );
};

describe('MappingConfig Component', () => {
  beforeEach(() => {
    // Reset mocks before each test
    jest.clearAllMocks();
    
    // Setup default mock state
    (useAppStore as unknown as jest.Mock).mockReturnValue({
      sessionId: 'test-session-123',
      selectedColumn: 'test_column',
      setJobId: jest.fn(),
      setCurrentStep: jest.fn(),
    });
  });

  it('renders the component with form fields', () => {
    renderWithProviders(<MappingConfig />);
    
    expect(screen.getByText('Configure Mapping Strategy')).toBeInTheDocument();
    expect(screen.getByLabelText('Source Column')).toBeInTheDocument();
    expect(screen.getByLabelText('Target Data Source')).toBeInTheDocument();
    expect(screen.getByLabelText('Mapping Strategy')).toBeInTheDocument();
    expect(screen.getByText('Start Mapping')).toBeInTheDocument();
  });

  it('displays session information correctly', () => {
    renderWithProviders(<MappingConfig />);
    
    expect(screen.getByText('test-session-123')).toBeInTheDocument();
    expect(screen.getByDisplayValue('test_column')).toBeInTheDocument();
  });

  it('shows alert when session data is missing', () => {
    (useAppStore as unknown as jest.Mock).mockReturnValue({
      sessionId: null,
      selectedColumn: null,
      setJobId: jest.fn(),
      setCurrentStep: jest.fn(),
    });

    renderWithProviders(<MappingConfig />);
    
    expect(screen.getByText('Missing Session Data')).toBeInTheDocument();
    expect(screen.getByText(/Session information is missing/)).toBeInTheDocument();
  });

  it('validates target data source selection', async () => {
    renderWithProviders(<MappingConfig />);
    
    const startButton = screen.getByText('Start Mapping');
    fireEvent.click(startButton);
    
    // Should show validation error
    await waitFor(() => {
      expect(screen.getByText(/Please select a target data source/)).toBeInTheDocument();
    });
  });

  it('submits form with correct data', async () => {
    const mockSetJobId = jest.fn();
    const mockSetCurrentStep = jest.fn();
    
    (useAppStore as unknown as jest.Mock).mockReturnValue({
      sessionId: 'test-session-123',
      selectedColumn: 'test_column',
      setJobId: mockSetJobId,
      setCurrentStep: mockSetCurrentStep,
    });

    (apiService.startMapping as jest.Mock).mockResolvedValue({
      jobId: 'test-job-123',
      status: 'pending',
    });

    renderWithProviders(<MappingConfig />);
    
    // Select target data source
    const targetSelect = screen.getByLabelText('Target Data Source');
    fireEvent.change(targetSelect, { target: { value: 'chebi' } });
    
    // Click submit
    const startButton = screen.getByText('Start Mapping');
    fireEvent.click(startButton);
    
    await waitFor(() => {
      expect(apiService.startMapping).toHaveBeenCalledWith({
        sessionId: 'test-session-123',
        sourceColumn: 'test_column',
        targetDataSource: 'chebi',
        strategy: 'direct_mapping',
        parameters: {
          confidence_threshold: 0.8,
          max_iterations: 1,
          enable_validation: false,
        }
      });
      
      expect(mockSetJobId).toHaveBeenCalledWith('test-job-123');
      expect(mockSetCurrentStep).toHaveBeenCalledWith('results');
    });
  });

  it('handles API errors gracefully', async () => {
    (apiService.startMapping as jest.Mock).mockRejectedValue(
      new Error('API connection failed')
    );

    renderWithProviders(<MappingConfig />);
    
    // Select target and submit
    const targetSelect = screen.getByLabelText('Target Data Source');
    fireEvent.change(targetSelect, { target: { value: 'pubchem' } });
    
    const startButton = screen.getByText('Start Mapping');
    fireEvent.click(startButton);
    
    await waitFor(() => {
      expect(screen.getByText(/Failed to start mapping: API connection failed/)).toBeInTheDocument();
    });
  });

  it('updates strategy description when selection changes', () => {
    renderWithProviders(<MappingConfig />);
    
    const strategySelect = screen.getByLabelText('Mapping Strategy');
    
    // Change to bidirectional validation
    fireEvent.change(strategySelect, { target: { value: 'bidirectional_validation' } });
    
    expect(screen.getByText(/Bidirectional validation performs mapping/)).toBeInTheDocument();
    
    // Change to iterative mapping
    fireEvent.change(strategySelect, { target: { value: 'iterative_mapping' } });
    
    expect(screen.getByText(/Iterative mapping uses multiple passes/)).toBeInTheDocument();
  });

  it('disables button during submission', async () => {
    (apiService.startMapping as jest.Mock).mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );

    renderWithProviders(<MappingConfig />);
    
    // Select target
    const targetSelect = screen.getByLabelText('Target Data Source');
    fireEvent.change(targetSelect, { target: { value: 'hmdb' } });
    
    const startButton = screen.getByText('Start Mapping');
    fireEvent.click(startButton);
    
    // Button should be disabled during submission
    expect(startButton).toBeDisabled();
    
    await waitFor(() => {
      expect(startButton).not.toBeDisabled();
    });
  });
});