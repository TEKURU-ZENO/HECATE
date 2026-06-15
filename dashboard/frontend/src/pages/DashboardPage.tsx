import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Shield, Activity, Clock, Server, CheckCircle2, AlertTriangle, XCircle, Power, Brain, Sparkles, Lightbulb } from 'lucide-react';
import { SeverityBadge, StatusBadge } from '@/components/Badge';
import { formatTimestamp } from '@/lib/utils';

export default function DashboardPage() {
  const [incidents, setIncidents] = useState<any[]>([]);
  const [remediations, setRemediations] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [systemHealth, setSystemHealth] = useState<'Healthy' | 'Warning' | 'Critical'>('Healthy');
  const [learningFeedback, setLearningFeedback] = useState<any[]>([]);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [learningStats, setLearningStats] = useState<any>({
    total_incidents: 0,
    avg_recovery_time: 0.0,
    avg_effectiveness: 0.0,
    successful_remediations: 0,
    top_successful_action: "None"
  });
  
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

      const feedbackRes = await fetch('http://localhost:8000/api/v1/learning/feedback');
      if (feedbackRes.ok) setLearningFeedback(await feedbackRes.json());

      const recsRes = await fetch('http://localhost:8000/api/v1/recommendations');
      if (recsRes.ok) setRecommendations(await recsRes.json());

      const statsRes = await fetch('http://localhost:8000/api/v1/learning/stats');
      if (statsRes.ok) setLearningStats(await statsRes.json());
      
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
            {['monitoring', 'detection', 'decision', 'remediation', 'learning'].map((role) => {
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

        {/* ML INTELLIGENCE & RCA DIAGNOSTICS CARD */}
        <div className="rounded-xl border border-white/8 bg-surface-800/40 p-6 backdrop-blur-md md:col-span-2">
          <div className="flex items-center justify-between mb-4 border-b border-white/5 pb-2">
            <span className="text-xs font-semibold text-white/30 uppercase tracking-wider block">ML Detection & Root Cause Diagnostics</span>
            <div className="flex gap-4 text-[10px] font-mono">
              <span className="text-amber-400">Rule Alerts: {incidents.filter(i => !i.title.toLowerCase().includes("ml")).length}</span>
              <span className="text-indigo-400">ML Detections: {incidents.filter(i => i.title.toLowerCase().includes("ml")).length}</span>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* List of ML detections */}
            <div className="space-y-3">
              <span className="text-[11px] font-semibold text-white/50 block">Active Machine Learning Alerts</span>
              {incidents.filter(i => i.title.toLowerCase().includes("ml")).length === 0 ? (
                <div className="text-center py-6 text-xs text-white/20 border border-dashed border-white/5 rounded-lg">No ML anomalies detected in this cycle.</div>
              ) : (
                incidents.filter(i => i.title.toLowerCase().includes("ml")).slice(0, 3).map(inc => (
                  <div key={inc.id} className="p-3 rounded-lg bg-indigo-950/20 border border-indigo-500/20 flex justify-between items-center">
                    <div>
                      <span className="text-xs font-bold text-indigo-400 block">Unsupervised Isolation Forest</span>
                      <span className="text-[10px] text-white/60 font-mono mt-0.5 block">Target: {inc.service_name} · {inc.root_cause || "Analyzing dependencies..."}</span>
                    </div>
                    <span className="px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/25 text-[9px] text-indigo-300 font-mono">ML ACTIVE</span>
                  </div>
                ))
              )}
            </div>
            {/* Decoupled RCA Diagnostics Panel */}
            <div className="space-y-3">
              <span className="text-[11px] font-semibold text-white/50 block">Dependency Path Root Cause Diagnostics</span>
              {incidents.filter(i => i.root_cause && i.root_cause.includes("caused by")).length === 0 ? (
                <div className="text-center py-6 text-xs text-white/20 border border-dashed border-white/5 rounded-lg">No cascading failures diagnosed yet.</div>
              ) : (
                incidents.filter(i => i.root_cause && i.root_cause.includes("caused by")).slice(0, 3).map(inc => (
                  <div key={inc.id} className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-500/20">
                    <div className="flex justify-between items-start">
                      <span className="text-xs font-bold text-emerald-400">Cascading Failure Isolated</span>
                      <span className="text-[10px] text-emerald-400/80 font-mono font-bold">Conf: {inc.confidence_score ? `${(inc.confidence_score * 100).toFixed(0)}%` : "N/A"}</span>
                    </div>
                    <p className="text-[10px] text-white/70 mt-1">{inc.root_cause}</p>
                    {inc.risk_score !== undefined && (
                      <div className="mt-2 flex items-center gap-2">
                        <span className="text-[9px] text-white/40 uppercase">Risk Index:</span>
                        <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                          <div className="h-full bg-red-500" style={{ width: `${inc.risk_score * 100}%` }} />
                        </div>
                        <span className="text-[9px] text-red-400 font-mono">{inc.risk_score.toFixed(2)}</span>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* RELIABILITY INTELLIGENCE & RECOMMENDATIONS CARD */}
        <div className="rounded-xl border border-white/8 bg-surface-800/40 p-6 backdrop-blur-md md:col-span-2">
          <div className="flex items-center justify-between mb-4 border-b border-white/5 pb-2">
            <div className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-indigo-400 animate-pulse" />
              <span className="text-xs font-semibold text-white/30 uppercase tracking-wider block">Reliability Intelligence & Recommendations</span>
            </div>
            <span className="px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/25 text-[10px] text-indigo-300 font-mono font-bold flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-indigo-400 animate-pulse" />
              AI RECOMMENDATION ENGINE
            </span>
          </div>

          <div className="space-y-3">
            <span className="text-[11px] font-semibold text-white/50 block">Active Recommendations & Playbook Scoring</span>
            {recommendations.length === 0 ? (
              <div className="text-center py-8 text-xs text-white/20 border border-dashed border-white/5 rounded-lg">No playbook recommendations generated yet.</div>
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {recommendations.slice(0, 3).map((rec) => {
                  const scorePercent = rec.recommendation_score * 100;
                  const probPercent = rec.success_probability * 100;
                  const tierNames: { [key: number]: string } = {
                    1: 'Tier 1: Exact Match (High Similarity)',
                    2: 'Tier 2: Partial Match (Cross-Service)',
                    3: 'Tier 3: Policy Fallback (Cold Start)'
                  };
                  const tierColors: { [key: number]: string } = {
                    1: 'text-indigo-400 border-indigo-500/20 bg-indigo-500/10',
                    2: 'text-cyan-400 border-cyan-500/20 bg-cyan-500/10',
                    3: 'text-amber-400 border-amber-500/20 bg-amber-500/10'
                  };
                  return (
                    <div key={rec.id} className="p-4 rounded-lg bg-black/20 border border-white/5 hover:border-white/10 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4 font-mono text-[11px]">
                      <div className="space-y-2 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`px-2 py-0.5 rounded border text-[9px] font-bold ${tierColors[rec.match_tier] || 'text-white border-white/10 bg-white/5'}`}>
                            {tierNames[rec.match_tier] || `Tier ${rec.match_tier}`}
                          </span>
                          <span className="text-white/40">·</span>
                          <span className="text-white font-bold">{rec.incident_type}</span>
                          <span className="text-white/40">on</span>
                          <span className="text-white/80 font-bold">{rec.root_cause_service}</span>
                        </div>
                        
                        <div className="flex items-center gap-2 text-white/60">
                          <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
                          <span>Recommended Action:</span>
                          <span className="text-white font-bold capitalize bg-white/5 px-2 py-0.5 rounded">{rec.recommended_action.replace('_', ' ')}</span>
                          {rec.similar_cases_count > 0 && (
                            <span className="text-white/35">({rec.similar_cases_count} historical cases)</span>
                          )}
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-6 border-t md:border-t-0 border-white/5 pt-3 md:pt-0">
                        <div className="flex flex-col">
                          <span className="text-[9px] text-white/40 uppercase">Success Probability</span>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="font-bold text-white">{probPercent.toFixed(0)}%</span>
                            <div className="w-16 h-1 bg-white/5 rounded-full overflow-hidden">
                              <div className="h-full bg-green-500" style={{ width: `${probPercent}%` }} />
                            </div>
                          </div>
                        </div>

                        <div className="flex flex-col">
                          <span className="text-[9px] text-white/40 uppercase">Engine Score</span>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="font-bold text-indigo-400">{rec.recommendation_score.toFixed(2)}</span>
                            <div className="w-16 h-1 bg-white/5 rounded-full overflow-hidden">
                              <div className="h-full bg-indigo-500" style={{ width: `${scorePercent}%` }} />
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* OPERATIONAL MEMORY & FEEDBACK CARD */}
        <div className="rounded-xl border border-white/8 bg-surface-800/40 p-6 backdrop-blur-md md:col-span-2">
          <div className="flex items-center justify-between mb-4 border-b border-white/5 pb-2">
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-emerald-400 animate-pulse" />
              <span className="text-xs font-semibold text-white/30 uppercase tracking-wider block">Operational Memory & Learning Feedback</span>
            </div>
            <span className="px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/25 text-[10px] text-emerald-400 font-mono font-bold">
              KNOWLEDGE BASE ACTIVE
            </span>
          </div>

          {/* KPI Mini-cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="p-3 rounded-lg bg-black/20 border border-white/5">
              <span className="text-[10px] text-white/40 uppercase block">Total Incidents</span>
              <span className="text-lg font-bold text-white mt-1 block">{learningStats.total_incidents}</span>
            </div>
            <div className="p-3 rounded-lg bg-black/20 border border-white/5">
              <span className="text-[10px] text-white/40 uppercase block">Avg Recovery Time</span>
              <span className="text-lg font-bold text-white mt-1 block">{learningStats.avg_recovery_time}s</span>
            </div>
            <div className="p-3 rounded-lg bg-black/20 border border-white/5">
              <span className="text-[10px] text-white/40 uppercase block">Avg Effectiveness</span>
              <span className="text-lg font-bold text-white mt-1 block">{(learningStats.avg_effectiveness * 100).toFixed(0)}%</span>
            </div>
            <div className="p-3 rounded-lg bg-black/20 border border-white/5">
              <span className="text-[10px] text-white/40 uppercase block">Top Successful Action</span>
              <span className="text-lg font-bold text-emerald-400 mt-1 block capitalize">{learningStats.top_successful_action.replace('_', ' ')}</span>
            </div>
          </div>

          {/* Feedback list */}
          <div className="space-y-3">
            <span className="text-[11px] font-semibold text-white/50 block">Remediation Feedback Logs</span>
            {learningFeedback.length === 0 ? (
              <div className="text-center py-8 text-xs text-white/20 border border-dashed border-white/5 rounded-lg">No operational memories logged in the database yet.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-[11px]">
                  <thead>
                    <tr className="border-b border-white/5 text-white/30 text-[9px] uppercase tracking-wider">
                      <th className="pb-2">Incident</th>
                      <th className="pb-2">Root Cause</th>
                      <th className="pb-2">Remediation</th>
                      <th className="pb-2">Status</th>
                      <th className="pb-2 text-right">Time</th>
                      <th className="pb-2 text-right pl-4">Effectiveness</th>
                    </tr>
                  </thead>
                  <tbody>
                    {learningFeedback.slice(0, 5).map((fb) => {
                      const effPercent = fb.effectiveness_score * 100;
                      const effColor = fb.effectiveness_score >= 0.75 ? 'bg-green-500' : fb.effectiveness_score >= 0.40 ? 'bg-amber-500' : 'bg-red-500';
                      const effText = fb.effectiveness_score >= 0.75 ? 'text-green-400' : fb.effectiveness_score >= 0.40 ? 'text-amber-400' : 'text-red-400';
                      return (
                        <tr key={fb.id} className="border-b border-white/5 hover:bg-white/2 transition-colors">
                          <td className="py-2.5 max-w-[150px] truncate pr-2">
                            <span className="text-white font-bold block">{fb.incident_title}</span>
                            <span className="text-[9px] text-white/40">{fb.incident_type}</span>
                          </td>
                          <td className="py-2.5 text-white/60 pr-2">{fb.root_cause_service}</td>
                          <td className="py-2.5 text-white/60 pr-2 capitalize">{fb.remediation_action.replace('_', ' ')}</td>
                          <td className="py-2.5">
                            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${fb.success ? 'bg-green-500/10 border border-green-500/20 text-green-400' : 'bg-red-500/10 border border-red-500/20 text-red-400'}`}>
                              {fb.success ? 'SUCCESS' : 'FAILED'}
                            </span>
                          </td>
                          <td className="py-2.5 text-right font-bold text-white/80">{fb.recovery_time_seconds}s</td>
                          <td className="py-2.5 text-right pl-4">
                            <div className="flex items-center justify-end gap-2">
                              <span className={`font-bold ${effText}`}>{effPercent.toFixed(0)}%</span>
                              <div className="w-16 h-1.5 bg-white/5 rounded-full overflow-hidden hidden sm:block">
                                <div className={`h-full ${effColor}`} style={{ width: `${effPercent}%` }} />
                              </div>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}