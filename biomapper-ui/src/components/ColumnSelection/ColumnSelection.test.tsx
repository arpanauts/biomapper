import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { vi } from 'vitest';
import ColumnSelection from './ColumnSelection';
import { apiService } from '../../services/api';
import { useAppStore } from '../../store/appStore';

// Mock the API service
vi.mock('../../services/api', () => ({
  apiService: {
    getColumns: vi.fn(),
  },
}));

// Mock the app store
vi.mock('../../store/appStore', () => ({
  useAppStore: vi.fn(),
}));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const renderComponent = () => {
  return render(
    <QueryClientProvider client={queryClient}>
      <MantineProvider>
        <Notifications />
        <ColumnSelection />
      </MantineProvider>
    </QueryClientProvider>
  );
};

describe('ColumnSelection', () => {
  const mockSetActiveStep = vi.fn();
  const mockSessionId = 'test-session-123';

  beforeEach(() => {
    vi.clearAllMocks();
    (useAppStore as any).mockReturnValue({
      sessionId: mockSessionId,
      setActiveStep: mockSetActiveStep,
    });
  });

  it('should render loading state initially', () => {
    (apiService.getColumns as any).mockImplementation(() => new Promise(() => {}));
    
    renderComponent();
    
    expect(screen.getByText('Loading columns...')).toBeInTheDocument();
  });

  it('should display columns when loaded', async () => {
    const mockColumns = ['id', 'name', 'email', 'age', 'city'];
    (apiService.getColumns as any).mockResolvedValue({ columns: mockColumns });
    
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Select Columns for Mapping')).toBeInTheDocument();
    });
    
    // Check if columns are displayed
    for (const col of mockColumns) {
      expect(screen.getByLabelText(col)).toBeInTheDocument();
    }
  });

  it('should filter columns based on search term', async () => {
    const mockColumns = ['id', 'name', 'email', 'age', 'city'];
    (apiService.getColumns as any).mockResolvedValue({ columns: mockColumns });
    
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Select Columns for Mapping')).toBeInTheDocument();
    });
    
    // Type in search box
    const searchInput = screen.getByPlaceholderText('Type to filter columns...');
    fireEvent.change(searchInput, { target: { value: 'em' } });
    
    // Should show only 'email' and 'name' columns
    expect(screen.getByLabelText('email')).toBeInTheDocument();
    expect(screen.getByLabelText('name')).toBeInTheDocument();
    expect(screen.queryByLabelText('id')).not.toBeInTheDocument();
  });

  it('should handle column selection', async () => {
    const mockColumns = ['id', 'name', 'email'];
    (apiService.getColumns as any).mockResolvedValue({ columns: mockColumns });
    
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Select Columns for Mapping')).toBeInTheDocument();
    });
    
    // Click on a checkbox
    const nameCheckbox = screen.getByLabelText('name');
    fireEvent.click(nameCheckbox);
    
    // Should show 1 column selected
    expect(screen.getByText('1 column selected')).toBeInTheDocument();
  });

  it('should show error state when API fails', async () => {
    (apiService.getColumns as any).mockRejectedValue(new Error('API Error'));
    
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Error Loading Columns')).toBeInTheDocument();
      expect(screen.getByText('API Error')).toBeInTheDocument();
    });
    
    // Should show retry button
    expect(screen.getByText('Try Again')).toBeInTheDocument();
  });

  it('should navigate to mapping step on submit', async () => {
    const mockColumns = ['id', 'name', 'email'];
    (apiService.getColumns as any).mockResolvedValue({ columns: mockColumns });
    
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Select Columns for Mapping')).toBeInTheDocument();
    });
    
    // Select a column
    const nameCheckbox = screen.getByLabelText('name');
    fireEvent.click(nameCheckbox);
    
    // Click Next button
    const nextButton = screen.getByText('Next');
    fireEvent.click(nextButton);
    
    // Should call setActiveStep
    expect(mockSetActiveStep).toHaveBeenCalledWith('mapping');
  });

  it('should show warning when no columns selected', async () => {
    const mockColumns = ['id', 'name', 'email'];
    (apiService.getColumns as any).mockResolvedValue({ columns: mockColumns });
    
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Select Columns for Mapping')).toBeInTheDocument();
    });
    
    // Click Next without selecting columns
    const nextButton = screen.getByText('Next');
    expect(nextButton).toBeDisabled();
  });
});