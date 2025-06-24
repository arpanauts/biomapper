import { create } from 'zustand'

export type StepType = 'upload' | 'columns' | 'mapping' | 'results'

interface AppState {
  activeStep: StepType
  sessionId: string | null
  filename: string | null
  jobId: string | null
  isLoading: boolean
  error: string | null
}

interface AppActions {
  setSession: (sessionId: string, filename: string) => void
  setJobId: (jobId: string) => void
  setActiveStep: (step: StepType) => void
  reset: () => void
  setLoading: (isLoading: boolean) => void
  setError: (error: string | null) => void
}

type AppStore = AppState & AppActions

const initialState: AppState = {
  activeStep: 'upload',
  sessionId: null,
  filename: null,
  jobId: null,
  isLoading: false,
  error: null
}

export const useAppStore = create<AppStore>((set) => ({
  ...initialState,
  
  setSession: (sessionId: string, filename: string) => 
    set({ sessionId, filename }),
  
  setJobId: (jobId: string) => 
    set({ jobId }),
  
  setActiveStep: (step: StepType) => 
    set({ activeStep: step }),
  
  reset: () => 
    set(initialState),
  
  setLoading: (isLoading: boolean) => 
    set({ isLoading }),
  
  setError: (error: string | null) => 
    set({ error })
}))