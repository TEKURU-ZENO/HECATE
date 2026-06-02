import { create } from 'zustand';
import type { Incident } from '@/types';

interface IncidentStore {
  incidents: Incident[];
  selectedIncident: Incident | null;
  setIncidents: (incidents: Incident[]) => void;
  setSelectedIncident: (incident: Incident | null) => void;
  addIncident: (incident: Incident) => void;
  updateIncident: (id: string, patch: Partial<Incident>) => void;
}

export const useIncidentStore = create<IncidentStore>((set) => ({
  incidents: [],
  selectedIncident: null,
  setIncidents: (incidents) => set({ incidents }),
  setSelectedIncident: (incident) => set({ selectedIncident: incident }),
  addIncident: (incident) =>
    set((state) => ({ incidents: [incident, ...state.incidents] })),
  updateIncident: (id, patch) =>
    set((state) => ({
      incidents: state.incidents.map((i) =>
        i.id === id ? { ...i, ...patch } : i
      ),
    })),
}));
