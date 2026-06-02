import { cn } from '@/lib/utils';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'severity' | 'status' | 'default';
  value?: string;
  className?: string;
}

const SEVERITY_STYLES: Record<string, string> = {
  critical: 'bg-red-500/15    text-red-400    border-red-500/25',
  high:     'bg-orange-500/15 text-orange-400 border-orange-500/25',
  medium:   'bg-yellow-500/15 text-yellow-400 border-yellow-500/25',
  low:      'bg-green-500/15  text-green-400  border-green-500/25',
};

const STATUS_STYLES: Record<string, string> = {
  open:          'bg-red-500/15    text-red-400    border-red-500/25',
  investigating: 'bg-orange-500/15 text-orange-400 border-orange-500/25',
  remediated:    'bg-green-500/15  text-green-400  border-green-500/25',
  closed:        'bg-white/8       text-white/40   border-white/10',
};

const AGENT_STATUS_STYLES: Record<string, string> = {
  active:   'bg-green-500/15  text-green-400  border-green-500/25',
  idle:     'bg-white/8       text-white/40   border-white/10',
  error:    'bg-red-500/15    text-red-400    border-red-500/25',
  starting: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/25',
};

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border capitalize',
        SEVERITY_STYLES[severity] ?? 'bg-white/8 text-white/50 border-white/10'
      )}
    >
      {severity}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border capitalize',
        STATUS_STYLES[status] ?? AGENT_STATUS_STYLES[status] ?? 'bg-white/8 text-white/50 border-white/10'
      )}
    >
      {status}
    </span>
  );
}

export function Badge({ children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border bg-white/8 text-white/60 border-white/10',
        className
      )}
    >
      {children}
    </span>
  );
}
