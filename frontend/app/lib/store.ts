import { create } from "zustand";

interface AuthState {
  isAuthenticated: boolean;
  setAuthenticated: (v: boolean) => void;
}

export const useAuth = create<AuthState>((set) => ({
  isAuthenticated: false,
  setAuthenticated: (v) => set({ isAuthenticated: v }),
}));
