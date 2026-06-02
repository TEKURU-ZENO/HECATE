import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Filter, RefreshCw, Eye } from 'lucide-react';
import { SeverityBadge, StatusBadge } from '@/components/Badge';
import { MOCK_INCIDENTS } from '@/lib/mockData';
import { formatTimestamp } from '@/lib/utils';
import type { Incident } from '@/types';

export default function IncidentsPage() {
  const [search, setSearch] = useState('');
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);

  const filtered = MOCK_INCIDENTS.filter(
    (i) =>
      i.title.toLowerCase().includes(search.toLowerCase()) ||
      i.serviceName.toLowerCase().includes(search.toLowerCase()) ||
      i.incidentCode.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Incidents</h2>
          <p className="text-sm text-white/40 mt-0.5">Track and investigate system alerts</p>
        </div>
      </div>

      {/* Filters and search */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-white/35" />
          <input
            type="text"
            placeholder="Search code, title or service..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm bg-surface-900 border border-white/8 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-hecate-500 transition-colors"
          />
        </div>
        <button className="flex items-center gap-2 px-3 py-2 bg-surface-900 border border-white/8 rounded-lg text-white/70 hover:text-white hover:bg-surface-800 transition-colors text-sm">
          <Filter className="h-4 w-4" />
          Filter
        </button>
      </div>

      {/* Incident table */}
      <div className="overflow-x-auto rounded-xl border border-white/8 bg-surface-800/60">
        <table className="w-full border-collapse text-left text-sm text-white/80">
          <thead className="bg-white/2 text-xs font-semibold uppercase text-white/40 border-b border-white/8">
            <tr>
              <th className="px-6 py-3">Code</th>
              <th className="px-6 py-3">Incident</th>
              <th className="px-6 py-3">Service</th>
              <th className="px-6 py-3">Severity</th>
              <th className="px-6 py-3">Status</th>
              <th className="px-6 py-3">Detected At</th>
              <th className="px-6 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {filtered.map((incident) => (
              <tr key={incident.id} className="hover:bg-white/2 transition-colors">
                <td className="px-6 py-4 font-mono text-xs text-white/50">{incident.incidentCode}</td>
                <td className="px-6 py-4 font-medium text-white">{incident.title}</td>
                <td className="px-6 py-4 font-mono text-xs text-white/50">{incident.serviceName}</td>
                <td className="px-6 py-4"><SeverityBadge severity={incident.severity} /></td>
                <td className="px-6 py-4"><StatusBadge status={incident.status} /></td>
                <td className="px-6 py-4 text-xs text-white/40">{formatTimestamp(incident.detectedAt)}</td>
                <td className="px-6 py-4 text-right">
                  <button
                    onClick={() => setSelectedIncident(incident)}
                    className="inline-flex items-center justify-center p-1.5 rounded-lg bg-white/5 hover:bg-hecate-500/20 text-white/75 hover:text-hecate-300 transition-all border border-white/5"
                  >
                    <Eye className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Detail Modal */}
      {selectedIncident && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-xl border border-white/10 bg-surface-900 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <h3 className="font-mono text-xs text-white/40">{selectedIncident.incidentCode}</h3>
              <button
                onClick={() => setSelectedIncident(null)}
                className="text-white/40 hover:text-white"
              >
                ✕
              </button>
            </div>
            <div>
              <h4 className="text-lg font-bold text-white">{selectedIncident.title}</h4>
              <p className="text-xs text-white/40 mt-1">Service: <span className="font-mono">{selectedIncident.serviceName}</span></p>
            </div>
            <div className="grid grid-cols-2 gap-4 py-2 border-y border-white/5">
              <div>
                <span className="text-[10px] uppercase text-white/35 block mb-1">Severity</span>
                <SeverityBadge severity={selectedIncident.severity} />
              </div>
              <div>
                <span className="text-[10px] uppercase text-white/35 block mb-1">Status</span>
                <StatusBadge status={selectedIncident.status} />
              </div>
            </div>
            {selectedIncident.rootCause && (
              <div className="p-3 rounded-lg bg-surface-800 border border-white/5">
                <span className="text-[10px] uppercase text-hecate-300 font-semibold block mb-1">Autonomous RCA Diagnosis</span>
                <p className="text-xs text-white/80 leading-relaxed">{selectedIncident.rootCause}</p>
                {selectedIncident.confidenceScore && (
                  <div className="mt-2 text-[10px] text-white/35">
                    Confidence score: <span className="font-mono font-bold text-white/60">{(selectedIncident.confidenceScore * 100).toFixed(0)}%</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}