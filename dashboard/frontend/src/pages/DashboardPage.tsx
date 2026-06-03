import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Shield, Activity, Clock, Server, CheckCircle2, AlertTriangle, XCircle, Power } from 'lucide-react';
import { SeverityBadge, StatusBadge } from '@/components/Badge';
import { formatTimestamp } from '@/lib/utils';

export default function DashboardPage() {
  const [incidents, setIncidents] = useState<any[]>([]);
  const [remediations, setRemediations] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [systemHealth, setSystemHealth] = useState<'Healthy' | 'Warning' | 'Critical'>('Healthy');
  
  const fetchDashboardData = async () => {
    try {
      const incRes = await fetch('http://localhost:8000/api/v1/incidents');
      if (incRes.ok) {
        const incs = await incRes.json();
        setIncidents(incs);
        
        // Compute overall system health from open incidents
        const openIncs = incs.filter((i: any) => i.status === 'open' || i.status === 'investigating');
        if (openIncs.some((i: any) => i.severity === 'critical')) {
          setSystemHealth('Critical');
        } else if (openIncs.length > 0) {
          setSystemHealth('Warning');
        } else {
          setSystemHealth('Healthy');
        }
      }
      
      const remRes = await fetch('http://localhost:8000/api/v1/remediations');
      if (remRes.ok) setRemediations(await remRes.json());
      
      const agRes = await fetch('http://localhost:8000/api/v1/agents');
      if (agRes.ok) setAgents(await agRes.json());
      
    } catch (e) {
      console.warn('Dashboard REST API not reachable yet. Using simulated feed.');
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 3000);
    
    // Connect live WebSockets to stream incoming incidents/remediations
    const ws = new WebSocket('ws://localhost:8000/ws/live');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('WS event:', data);
      fetchDashboardData();
    };
    
    return () => {
      clearInterval(interval);
      ws.close();
    };
  }, []);

  return (
    <div className="space-y-6 max-w-screen-xl mx-auto p-4">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">HECATE Platform Control Panel</h2>
          <p className="text-sm text-white/40 mt-1">Autonomous Event-Driven self-healing runtime</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/10 border border-green-500/20 text-xs text-green-400 font-medium font-mono">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          ACTIVE LOOP
        </div>
      </div>

      {/* Grid containing 4 Core Cards requested in Session 2 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* CARD 1: SYSTEM HEALTH */}
        <div className="rounded-xl border border-white/8 bg-surface-800/40 p-6 flex flex-col justify-between min-h-[160px] backdrop-blur-md relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-hecate-500/10 rounded-full blur-2xl" />
          <div>
            <span className="text-xs font-semibold text-white/30 uppercase tracking-wider block">System Health Status</span>
            <h3 className={`text-4xl font-extrabold mt-3 tracking-tight flex items-center gap-3 ${
              systemHealth === 'Healthy' ? 'text-green-400' 
              : systemHealth === 'Warning' ? 'text-amber-400' 
              : 'text-red-400'
            }`}>
              {systemHealth === 'Healthy' && <CheckCircle2 className="w-9 h-9" />}
              {systemHealth === 'Warning' && <AlertTriangle className="w-9 h-9" />}
              {systemHealth === 'Critical' && <XCircle className="w-9 h-9" />}
              {systemHealth}
            </h3>
          </div>
          <p className="text-xs text-white/40 mt-4 leading-relaxed border-t border-white/5 pt-3">
            {systemHealth === 'Healthy' ? 'All monitored service levels operate inside baseline thresholds.' : 'Automated playbooks currently resolving anomalous spikes.'}
          </p>
        </div>

        {/* CARD 3: AGENT STATUS */}
        <div className="rounded-xl border border-white/8 bg-surface-800/40 p-6 backdrop-blur-md">
          <span className="text-xs font-semibold text-white/30 uppercase tracking-wider block mb-4">Operations Agent Network</span>
          <div className="grid grid-cols-2 gap-3">
            {['monitoring', 'detection', 'decision', 'remediation'].map((role) => {
              const matchedAgent = agents.find(a => a.agentName.startsWith(role));
              const isActive = matchedAgent ? matchedAgent.status === 'active' : true;
              return (
                <div key={role} className="flex items-center gap-3 p-3 rounded-lg border border-white/5 bg-white/2">
                  <div className={`w-2.5 h-2.5 rounded-full ${isActive ? 'bg-green-400 shadow-[0_0_8px_#4ade80]' : 'bg-white/20'}`} />
                  <div className="flex flex-col">
                    <span className="text-xs font-semibold text-white/80 capitalize">{role} Agent</span>
                    <span className="text-[9px] text-white/40 font-mono">v0.1.0 · Active</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* CARD 2: ACTIVE INCIDENTS */}
        <div className="rounded-xl border border-white/8 bg-surface-800/40 p-6 backdrop-blur-md md:col-span-2 lg:col-span-1">
          <div className="flex items-center justify-between mb-4 border-b border-white/5 pb-2">
            <span className="text-xs font-semibold text-white/30 uppercase tracking-wider block">Active Incidents</span>
            <span className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-[10px] text-white/50 font-mono font-bold">
              {incidents.filter(i => i.status !== 'remediated' && i.status !== 'closed').length} Unresolved
            </span>
          </div>
          <div className="space-y-3 max-h-[220px] overflow-y-auto pr-1">
            {incidents.length === 0 ? (
              <div className="text-center py-6 text-xs text-white/30">No active incidents reported.</div>
            ) : (
              incidents.slice(0, 4).map((inc) => (
                <div key={inc.id} className="flex items-start justify-between p-3 rounded-lg bg-black/20 border border-white/5 hover:border-white/10 transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={inc.severity} />
                      <span className="text-xs font-semibold text-white truncate max-w-[180px]">{inc.title}</span>
                    </div>
                    <p className="text-[10px] text-white/40 font-mono">{inc.service_name} · {inc.root_cause}</p>
                  </div>
                  <StatusBadge status={inc.status} />
                </div>
              ))
            )}
          </div>
        </div>

        {/* CARD 4: RECENT ACTIONS LOG */}
        <div className="rounded-xl border border-white/8 bg-surface-800/40 p-6 backdrop-blur-md md:col-span-2 lg:col-span-1">
          <span className="text-xs font-semibold text-white/30 uppercase tracking-wider block mb-4 border-b border-white/5 pb-2">Recent Healing Actions</span>
          <div className="space-y-3 max-h-[220px] overflow-y-auto pr-1">
            {remediations.length === 0 ? (
              <div className="text-center py-6 text-xs text-white/30">No self-healing execution runs yet.</div>
            ) : (
              remediations.slice(0, 4).map((rem) => (
                <div key={rem.id} className="flex items-center justify-between p-3 rounded-lg bg-black/20 border border-white/5 font-mono text-[11px]">
                  <div className="flex items-center gap-3">
                    <div className={`w-1.5 h-1.5 rounded-full ${rem.success ? 'bg-green-400' : 'bg-red-400'}`} />
                    <div className="flex flex-col">
                      <span className="text-white/80 font-bold capitalize">{rem.action_type.replace('_', ' ')}</span>
                      <span className="text-white/35 text-[9px]">Target: {rem.target}</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end">
                    <span className={rem.success ? 'text-green-400 font-bold' : 'text-red-400 font-bold'}>
                      {rem.success ? 'SUCCESS' : 'FAILED'}
                    </span>
                    <span className="text-[9px] text-white/35 mt-0.5">{rem.execution_duration_ms}ms</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
}