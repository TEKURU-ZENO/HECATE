import React from 'react';
import { Settings, Bell, Shield, Database, Webhook } from 'lucide-react';

export default function SettingsPage() {
  return (
    <div className="space-y-6 max-w-screen-md mx-auto">
      <div>
        <h2 className="text-xl font-bold text-white">Settings</h2>
        <p className="text-sm text-white/40 mt-0.5">Configure platform settings, auth, and integrations</p>
      </div>

      <div className="rounded-xl border border-white/8 bg-surface-800/60 divide-y divide-white/5">
        <div className="p-5 space-y-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Bell className="h-4 w-4 text-hecate-400" />
            Notifications
          </h3>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-white">Slack Alerts</p>
              <p className="text-[10px] text-white/45 mt-0.5">Send notifications on critical incident remediation</p>
            </div>
            <button className="relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out bg-hecate-500">
              <span className="pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition duration-200 ease-in-out translate-x-4" />
            </button>
          </div>
        </div>

        <div className="p-5 space-y-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Shield className="h-4 w-4 text-hecate-400" />
            Security & Controls
          </h3>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-white">Dry Run Mode</p>
              <p className="text-[10px] text-white/45 mt-0.5">Log self-healing actions without making actual modifications</p>
            </div>
            <button className="relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out bg-white/10">
              <span className="pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition duration-200 ease-in-out translate-x-0" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}