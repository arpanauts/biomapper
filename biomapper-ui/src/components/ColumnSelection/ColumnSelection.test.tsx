import { render, screen } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { describe, it, expect, vi } from 'vitest';
import ColumnSelection from './ColumnSelection';

// Mock the store
vi.mock('../../store/appStore', () => ({
  useAppStore: () => ({
    sessionId: 'test-session',
    setActiveStep: vi.fn(),
  }),
}));

describe('ColumnSelection', () => {
  it('renders column selection interface', () => {
    render(
      <MantineProvider>
        <ColumnSelection />
      </MantineProvider>
    );
    
    expect(screen.getByText('Select Column for Mapping')).toBeInTheDocument();
  });
});