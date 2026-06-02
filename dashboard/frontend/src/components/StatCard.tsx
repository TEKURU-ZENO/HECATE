import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

interface StatCardProps {
  id?: string;
  label: string;
  value: string | number;
  sub?: string;
  icon?: ReactNode;
  trend?: { value: number; label: string };
  accent?: 'default' | 'green' | 'red' | 'amber' | 'purple';
  className?: string;
}

const ACCENT_CLASSES = {
  default: 'from-hecate-600/20 to-hecate-800/10 border-hecate-500/20',
  green:   'from-green-600/20  to-green-800/10  border-green-500/20',
  red:     'from-red-600/20    to-red-800/10    border-red-500/20',
  amber:   'from-amber-600/20  to-amber-800/10  border-amber-500/20',
  purple:  'from-purple-600/20 to-purple-800/10 border-purple-500/20',
};

const ICON_CLASSES = {
  default: 'bg-hecate-500/20 text-hecate-300',
  green:   'bg-green-500/20  text-green-300',
  red:     'bg-red-500/20    text-red-300',
  amber:   'bg-amber-500/20  text-amber-300',
  purple:  'bg-purple-500/20 text-purple-300',
};

export default function StatCard({
  id,
  label,
  value,
  sub,
  icon,
  trend,
  accent = 'default',
  className,
}: StatCardProps) {
  const isPositiveTrend = (trend?.value ?? 0) >= 0;

  return (
    <div
      id={id}
      className={cn(
        'relative overflow-hidden rounded-xl border bg-gradient-to-br p-5 transition-all duration-300 hover:scale-[1.01] hover:shadow-lg',
        ACCENT_CLASSES[accent],
        className
      )}
    >
      {/* Subtle glow */}
      <div className="absolute -top-6 -right-6 w-24 h-24 rounded-full bg-gradient-radial from-white/5 to-transparent" />

      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-white/40 uppercase tracking-wider mb-1">{label}</p>
          <p className="text-2xl font-bold text-white font-mono">{value}</p>
          {sub && <p className="text-xs text-white/35 mt-1">{sub}</p>}
          {trend && (
            <p className={cn('text-xs mt-1.5 font-medium', isPositiveTrend ? 'text-green-400' : 'text-red-400')}>
              {isPositiveTrend ? '↑' : '↓'} {Math.abs(trend.value)}% {trend.label}
            </p>
          )}
        </div>
        {icon && (
          <div className={cn('flex items-center justify-center w-10 h-10 rounded-xl', ICON_CLASSES[accent])}>
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
