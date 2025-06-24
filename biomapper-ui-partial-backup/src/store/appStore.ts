import { create } from 'zustand';

type AppStep = 'upload' | 'columns' | 'mapping' | 'results';

interface AppState {
  sessionId: string | null;
  activeStep: AppStep;
  selectedColumns: string[];
  jobId: string | null;
  
  // Actions
  setSessionId: (sessionId: string | null) => void;
  setActiveStep: (step: AppStep) => void;
  setSelectedColumns: (columns: string[]) => void;
  setJobId: (jobId: string | null) => void;
  reset: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  sessionId: null,
  activeStep: 'upload',
  selectedColumns: [],
  jobId: null,

  setSessionId: (sessionId) => set({ sessionId }),
  setActiveStep: (step) => set({ activeStep: step }),
  setSelectedColumns: (columns) => set({ selectedColumns: columns }),
  setJobId: (jobId) => set({ jobId }),
  
  reset: () => set({
    sessionId: null,
    activeStep: 'upload',
    selectedColumns: [],
    jobId: null,
  }),
}));