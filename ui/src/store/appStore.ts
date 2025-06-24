import { create } from 'zustand';

export type AppStep = 'upload' | 'columns' | 'mapping' | 'results';

interface AppState {
  activeStep: AppStep;
  sessionId: string | null;
  jobId: string | null;
  filename: string | null;
  setActiveStep: (step: AppStep) => void;
  setSessionId: (sessionId: string | null) => void;
  setJobId: (jobId: string | null) => void;
  setFilename: (filename: string | null) => void;
  reset: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  activeStep: 'upload',
  sessionId: null,
  jobId: null,
  filename: null,
  setActiveStep: (step) => set({ activeStep: step }),
  setSessionId: (sessionId) => set({ sessionId }),
  setJobId: (jobId) => set({ jobId }),
  setFilename: (filename) => set({ filename }),
  reset: () => set({
    activeStep: 'upload',
    sessionId: null,
    jobId: null,
    filename: null,
  }),
}));