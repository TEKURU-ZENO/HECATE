import { create } from 'zustand';
import type { Agent } from '@/types';

interface AgentStore {
  agents: Agent[];
  setAgents: (agents: Agent[]) => void;
  updateAgent: (id: string, patch: Partial<Agent>) => void;
}

export const useAgentStore = create<AgentStore>((set) => ({
  agents: [],
  setAgents: (agents) => set({ agents }),
  updateAgent: (id, patch) =>
    set((state) => ({
      agents: state.agents.map((a) =>
        a.id === id ? { ...a, ...patch } : a
      ),
    })),
}));
