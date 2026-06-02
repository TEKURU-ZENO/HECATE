import React from 'react';
import { BarChart3, LineChart, TrendingUp } from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
} from 'recharts';
import { MOCK_MTTR_DATA, MOCK_INCIDENTS_BY_SEVERITY } from '@/lib/mockData';

export default function AnalyticsPage() {
  return (
    <div className="space-y-6 max-w-screen-xl mx-auto">
      <div>
        <h2 className="text-xl font-bold text-white">System Analytics</h2>
        <p className="text-sm text-white/40 mt-0.5">Evaluate remediation metrics and recovery trends</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* MTTR Trend */}
        <div className="rounded-xl border border-white/8 bg-surface-800/60 p-5">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <LineChart className="h-4 w-4 text-hecate-400" />
            MTTR Recovery Trend (30d)
          </h3>
          <ResponsiveContainer width="100%" height={240}>
            <RechartsLineChart data={MOCK_MTTR_DATA} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="date" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: '#131625', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', fontSize: 12 }} />
              <Line type="monotone" dataKey="mttr" stroke="#7485ff" strokeWidth={2} dot={false} />
            </RechartsLineChart>
          </ResponsiveContainer>
        </div>

        {/* Severity counts */}
        <div className="rounded-xl border border-white/8 bg-surface-800/60 p-5">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-hecate-400" />
            Incidents by Severity
          </h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={MOCK_INCIDENTS_BY_SEVERITY} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="severity" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: '#131625', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', fontSize: 12 }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}