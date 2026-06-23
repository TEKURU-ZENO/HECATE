import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  AlertTriangle,
  Bot,
  Shield,
  BarChart2,
  Settings,
  Zap,
  ChevronRight,
  MessageSquare,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { to: '/',          label: 'Dashboard',  Icon: LayoutDashboard, end: true },
  { to: '/incidents', label: 'Incidents',  Icon: AlertTriangle               },
  { to: '/agents',    label: 'Agents',     Icon: Bot                         },
  { to: '/policies',  label: 'Policies',   Icon: Shield                      },
  { to: '/analytics', label: 'Analytics',  Icon: BarChart2                   },
  { to: '/settings',  label: 'Settings',   Icon: Settings                    },
  { to: '/copilot',   label: 'HECATE Copilot', Icon: MessageSquare               },
];

export default function Sidebar() {
  return (
    <aside className="flex flex-col w-64 min-h-screen bg-surface-900 border-r border-white/5">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-white/5">
        <div className="relative flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-br from-hecate-500 to-accent-purple shadow-lg shadow-hecate-500/30">
          <Zap className="w-5 h-5 text-white" strokeWidth={2.5} />
          <div className="absolute inset-0 rounded-xl animate-pulse-slow bg-hecate-400/20" />
        </div>
        <div>
          <div className="text-base font-bold tracking-widest text-white">HECATE</div>
          <div className="text-[10px] text-white/40 tracking-wider uppercase">Reliability Platform</div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        <p className="px-3 mb-2 text-[10px] font-semibold tracking-widest uppercase text-white/25">
          Navigation
        </p>
        {navItems.map(({ to, label, Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                'group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                isActive
                  ? 'bg-hecate-600/30 text-white border border-hecate-500/30 shadow-sm shadow-hecate-500/10'
                  : 'text-white/50 hover:text-white hover:bg-white/5'
              )
            }
          >
            {({ isActive }) => (
              <>
                <Icon
                  className={cn(
                    'w-4 h-4 transition-colors',
                    isActive ? 'text-hecate-400' : 'text-white/40 group-hover:text-white/70'
                  )}
                />
                <span className="flex-1">{label}</span>
                {isActive && (
                  <motion.div
                    layoutId="nav-indicator"
                    className="w-1.5 h-1.5 rounded-full bg-hecate-400"
                    transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                  />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer status */}
      <div className="px-4 py-4 border-t border-white/5">
        <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-white/3 border border-white/5">
          <div className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-green opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-green" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium text-white/80">System Operational</div>
            <div className="text-[10px] text-white/30 font-mono">8/8 agents running</div>
          </div>
          <ChevronRight className="w-3.5 h-3.5 text-white/20" />
        </div>
      </div>
    </aside>
  );
}
