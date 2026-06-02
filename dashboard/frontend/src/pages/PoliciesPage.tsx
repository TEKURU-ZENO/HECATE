import React from 'react';
import { ShieldCheck, Plus, Check } from 'lucide-react';
import { MOCK_POLICIES } from '@/lib/mockData';
import { Badge } from '@/components/Badge';

export default function PoliciesPage() {
  return (
    <div className="space-y-6 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Remediation Policies</h2>
          <p className="text-sm text-white/40 mt-0.5">Configure conditional trigger logic and auto-healing rules</p>
        </div>
        <button className="flex items-center gap-2 px-3 py-2 bg-hecate-600 hover:bg-hecate-500 rounded-lg text-white transition-colors text-sm font-semibold">
          <Plus className="h-4 w-4" />
          Add Policy
        </button>
      </div>

      <div className="space-y-4">
        {MOCK_POLICIES.map((policy) => (
          <div
            key={policy.id}
            className="flex flex-col lg:flex-row items-start lg:items-center justify-between p-5 rounded-xl border border-white/8 bg-surface-800/60 gap-4"
          >
            <div className="flex-1 space-y-2 min-w-0">
              <div className="flex items-center gap-3">
                <ShieldCheck className="h-5 w-5 text-hecate-400 shrink-0" />
                <h3 className="text-sm font-semibold text-white truncate">{policy.policyName}</h3>
                <Badge className={policy.riskLevel === 'high' ? 'text-red-400 border-red-500/20 bg-red-500/5' : ''}>
                  {policy.riskLevel} Risk
                </Badge>
              </div>
              <div className="space-y-1.5 text-xs text-white/60">
                <div className="font-mono bg-black/20 p-2 rounded border border-white/5 truncate">
                  <span className="text-hecate-400 font-semibold">IF: </span>
                  {policy.conditionExpression}
                </div>
                <div className="font-mono bg-black/20 p-2 rounded border border-white/5 truncate">
                  <span className="text-green-400 font-semibold">THEN: </span>
                  {policy.actionDefinition}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4 shrink-0">
              <div className="flex flex-col items-end">
                <span className="text-[10px] text-white/30 uppercase">Status</span>
                <span className={`text-xs font-semibold ${policy.enabled ? 'text-green-400' : 'text-white/30'}`}>
                  {policy.enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              <button
                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  policy.enabled ? 'bg-hecate-500' : 'bg-white/10'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                    policy.enabled ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}