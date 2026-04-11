"use client";

import { create } from "zustand";

export interface TrialState {
  onTrial: boolean;
  daysLeft: number;
  isExpired: boolean;
  warningLevel: "normal" | "warning" | "urgent";
  setTrial: (payload: Partial<TrialState>) => void;
}

export const useTrialStore = create<TrialState>((set) => ({
  onTrial: false,
  daysLeft: 0,
  isExpired: false,
  warningLevel: "normal",
  setTrial: (payload) => set((state) => ({ ...state, ...payload })),
}));
