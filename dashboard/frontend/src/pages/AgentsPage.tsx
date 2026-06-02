import React from 'react';
import { motion } from 'framer-motion';
import { Cpu, CpuIcon, Check, Power } from 'lucide-react';
import { StatusBadge } from '@/components/Badge';
import { MOCK_AGENTS } from '@/lib/mockData';
import { formatTimestamp } from '@/lib/utils';

export default function AgentsPage() {
  return (
    <div className="space-y-6 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Platform Agents</h2>
          <p className="text-sm text-white/40 mt-0.5">Manage and observe autonomous operations workers</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {MOCK_AGENTS.map((agent) => (
          <div
            key={agent.id}
            className="rounded-xl border border-white/8 bg-surface-800/60 p-5 flex flex-col justify-between space-y-4 hover:border-hecate-500/30 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-hecate-500/10 border border-hecate-500/20 text-hecate-400">
                  <Cpu className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white truncate max-w-[150px]">{agent.agentName}</h3>
                  <span className="text-[10px] text-white/35 font-mono">v{agent.version}</span>
                </div>
              </div>
              <StatusBadge status={agent.status} />
            </div>

            <div className="space-y-2 py-2 border-y border-white/5 text-xs text-white/60">
              <div className="flex justify-between">
                <span>Last heartbeat</span>
                <span className="font-mono text-white/40">{formatTimestamp(agent.lastSeen)}</span>
              </div>
              <div className="flex justify-between">
                <span>Memory usage</span>
                <span className="font-mono">142 MB</span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-white/40 uppercase font-semibold">Agent Health</span>
                <span className="text-xs font-bold text-hecate-400">{(agent.healthScore * 100).toFixed(0)}%</span>
              </div>
              <div className="w-24 bg-white/5 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-hecate-500 h-full rounded-full"
                  style={{ width: `${agent.healthScore * 100}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}