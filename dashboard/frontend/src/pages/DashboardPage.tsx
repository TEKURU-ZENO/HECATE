import { motion } from 'framer-motion';
import {
  AlertTriangle,
  Activity,
  Clock,
  Percent,
  ArrowRight,
  CheckCircle2,
  XCircle,
  Minus,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { Link } from 'react-router-dom';
import StatCard from '@/components/StatCard';
import { SeverityBadge, StatusBadge } from '@/components/Badge';
import {
  MOCK_INCIDENTS,
  MOCK_AGENTS,
  MOCK_SERVICE_HEALTH,
  MOCK_SYSTEM_UPTIME,
  MOCK_INCIDENTS_OVER_TIME,
} from '@/lib/mockData';
import { formatDuration, formatTimestamp, cn } from '@/lib/utils';

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.07 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  show:  { opacity: 1, y: 0, transition: { duration: 0.35, ease: 'easeOut' } },
};

const activeIncidents = MOCK_INCIDENTS.filter(
  (i) => i.status === 'open' || i.status === 'investigating'
);

const totalMTTR = MOCK_INCIDENTS.filter((i) => i.recoveryTimeSeconds)
  .reduce((sum, i) => sum + (i.recoveryTimeSeconds ?? 0), 0);
const avgMTTR = totalMTTR / MOCK_INCIDENTS.filter((i) => i.recoveryTimeSeconds).length;

function ServiceStatusIcon({ status }: { status: 'healthy' | 'degraded' | 'down' }) {
  if (status === 'healthy') return <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />;
  if (status === 'degraded') return <Minus className="w-3.5 h-3.5 text-amber-400" />;
  return <XCircle className="w-3.5 h-3.5 text-red-400" />;
}

const SERVICE_STATUS_COLORS = {
  healthy:  'border-green-500/20 bg-green-500/5',
  degraded: 'border-amber-500/20 bg-amber-500/5',
  down:     'border-red-500/20   bg-red-500/5',
};

export default function DashboardPage() {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-6 max-w-screen-xl mx-auto"
    >
      {/* ── Page header ── */}
      <motion.div variants={itemVariants} className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Overview</h2>
          <p className="text-sm text-white/40 mt-0.5">Real-time platform reliability summary</p>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-green-500/10 border border-green-500/20 text-xs text-green-400 font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          Live
        </div>
      </motion.div>

      {/* ── Stat cards ── */}
      <motion.div variants={itemVariants} className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          id="stat-total-incidents"
          label="Total Incidents"
          value={MOCK_INCIDENTS.length}
          sub="Last 24 hours"
          icon={<AlertTriangle className="w-5 h-5" />}
          accent="red"
          trend={{ value: -12, label: 'vs yesterday' }}
        />
        <StatCard
          id="stat-active-incidents"
          label="Active Incidents"
          value={activeIncidents.length}
          sub={`${activeIncidents.filter((i) => i.severity === 'critical').length} critical`}
          icon={<Activity className="w-5 h-5" />}
          accent="amber"
        />
        <StatCard
          id="stat-avg-mttr"
          label="Avg. MTTR"
          value={formatDuration(Math.round(avgMTTR))}
          sub="Mean time to recover"
          icon={<Clock className="w-5 h-5" />}
          accent="purple"
          trend={{ value: -8, label: 'vs last week' }}
        />
        <StatCard
          id="stat-uptime"
          label="Platform Uptime"
          value="99.87%"
          sub="Rolling 30-day SLA"
          icon={<Percent className="w-5 h-5" />}
          accent="green"
          trend={{ value: 0.02, label: 'vs last week' }}
        />
      </motion.div>

      {/* ── Uptime chart + Service health ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Uptime area chart */}
        <motion.div
          variants={itemVariants}
          className="lg:col-span-2 rounded-xl border border-white/8 bg-surface-800/60 p-5"
        >
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">System Uptime (24h)</h3>
              <p className="text-xs text-white/30 mt-0.5">Aggregated across all services</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={MOCK_SYSTEM_UPTIME} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="uptimeGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#5b5ef9" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#5b5ef9" stopOpacity={0}   />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="hour"
                tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                interval={3}
              />
              <YAxis
                domain={[99, 100]}
                tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip
                contentStyle={{ background: '#131625', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', fontSize: 12 }}
                labelStyle={{ color: 'rgba(255,255,255,0.6)' }}
                itemStyle={{ color: '#7485ff' }}
                formatter={(v: number) => [`${v.toFixed(3)}%`, 'Uptime']}
              />
              <Area
                type="monotone"
                dataKey="uptime"
                stroke="#7485ff"
                strokeWidth={2}
                fill="url(#uptimeGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Service health panel */}
        <motion.div
          variants={itemVariants}
          className="rounded-xl border border-white/8 bg-surface-800/60 p-5"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white">Service Health</h3>
            <Link
              to="/analytics"
              className="text-xs text-hecate-400 hover:text-hecate-300 flex items-center gap-1"
            >
              Details <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="space-y-2">
            {MOCK_SERVICE_HEALTH.map((svc) => (
              <div
                key={svc.serviceName}
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg border',
                  SERVICE_STATUS_COLORS[svc.status]
                )}
              >
                <ServiceStatusIcon status={svc.status} />
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-white/80 truncate">{svc.serviceName}</div>
                  <div className="text-[10px] text-white/35 font-mono">{svc.availability}% · {svc.responseTime}ms</div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* ── Incidents over time + Recent incidents ── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Incidents over time (stacked bars) */}
        <motion.div
          variants={itemVariants}
          className="lg:col-span-3 rounded-xl border border-white/8 bg-surface-800/60 p-5"
        >
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">Incidents (14d)</h3>
              <p className="text-xs text-white/30 mt-0.5">By severity, per day</p>
            </div>
            <div className="flex items-center gap-3 text-[10px] text-white/40">
              {[
                { label: 'Critical', color: '#ef4444' },
                { label: 'High',     color: '#f97316' },
                { label: 'Medium',   color: '#eab308' },
                { label: 'Low',      color: '#22c55e' },
              ].map(({ label, color }) => (
                <div key={label} className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-sm" style={{ background: color }} />
                  {label}
                </div>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={MOCK_INCIDENTS_OVER_TIME} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="date"
                tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                interval={2}
              />
              <YAxis
                tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{ background: '#131625', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', fontSize: 12 }}
                labelStyle={{ color: 'rgba(255,255,255,0.6)' }}
              />
              <Area type="monotone" dataKey="critical" stackId="1" stroke="#ef4444" fill="#ef444430" strokeWidth={1.5} />
              <Area type="monotone" dataKey="high"     stackId="1" stroke="#f97316" fill="#f9731630" strokeWidth={1.5} />
              <Area type="monotone" dataKey="medium"   stackId="1" stroke="#eab308" fill="#eab30830" strokeWidth={1.5} />
              <Area type="monotone" dataKey="low"      stackId="1" stroke="#22c55e" fill="#22c55e30" strokeWidth={1.5} />
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Recent incidents */}
        <motion.div
          variants={itemVariants}
          className="lg:col-span-2 rounded-xl border border-white/8 bg-surface-800/60 p-5"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white">Recent Incidents</h3>
            <Link
              to="/incidents"
              className="text-xs text-hecate-400 hover:text-hecate-300 flex items-center gap-1"
            >
              All <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="space-y-2.5">
            {MOCK_INCIDENTS.slice(0, 5).map((incident) => (
              <div
                key={incident.id}
                className="flex items-start gap-3 py-2 border-b border-white/5 last:border-0"
              >
                <div className="pt-0.5">
                  <SeverityBadge severity={incident.severity} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-white/80 leading-snug truncate">
                    {incident.title}
                  </p>
                  <p className="text-[10px] text-white/30 mt-0.5 font-mono">{incident.serviceName}</p>
                </div>
                <StatusBadge status={incident.status} />
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* ── Agent status strip ── */}
      <motion.div
        variants={itemVariants}
        className="rounded-xl border border-white/8 bg-surface-800/60 p-5"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white">Agent Status</h3>
          <Link
            to="/agents"
            className="text-xs text-hecate-400 hover:text-hecate-300 flex items-center gap-1"
          >
            Manage <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          {MOCK_AGENTS.map((agent) => (
            <div
              key={agent.id}
              className="flex flex-col items-center gap-2 px-3 py-3 rounded-xl border border-white/6 bg-white/2 hover:bg-white/4 transition-colors"
            >
              <div
                className="w-2.5 h-2.5 rounded-full"
                style={{
                  background: agent.status === 'active' ? '#10b981'
                    : agent.status === 'idle'   ? '#6b7280'
                    : agent.status === 'error'  ? '#ef4444'
                    : '#f59e0b',
                  boxShadow: agent.status === 'active'
                    ? '0 0 8px #10b981'
                    : undefined,
                }}
              />
              <span className="text-[10px] text-white/50 font-mono text-center leading-tight">
                {agent.agentName.replace('-agent', '')}
              </span>
              <span className="text-[10px] font-bold text-white/70 font-mono">
                {(agent.healthScore * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </motion.div>
    </motion.div>
  );
}
