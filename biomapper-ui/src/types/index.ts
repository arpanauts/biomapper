export interface Session {
  id: string;
  filename: string;
  createdAt?: string;
}

export interface AppState {
  activeStep: number;
  session: Session | null;
  isLoading: boolean;
  error: string | null;
  setActiveStep: (step: number) => void;
  setSession: (session: Session | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  advanceStep: () => void;
}

export interface UploadResponse {
  session_id: string;
  filename: string;
  message?: string;
}