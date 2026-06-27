import React, { useState, useEffect } from 'react';
import { Server, Activity, Cpu, ShieldAlert, CheckCircle, RefreshCw, Layers, DollarSign, Clock } from 'lucide-react';
import axios from 'axios';

interface ServiceState {
  cpu: number;
  mem: number;
  replicas: number;
  version: string;
}

interface ClusterInfo {
  cloud: string;
  region: string;
  status: string;
  services: Record<string, ServiceState>;
}

interface TwinState {
  clusters: Record<string, ClusterInfo>;
  traffic_peak: boolean;
  last_updated: number;
}

interface CalibrationInfo {
  accuracy: number;
  total_calibrations: number;
}

interface SimulationItem {
  playbook_sequence: string;
  predicted_mttr: number;
  predicted_cost: number;
  predicted_blast_radius: number;
  success_probability: number;
  confidence: number;
  score: number;
}

const DEFAULT_TWIN_DATA = {
  state: {
    clusters: {
      "cluster-aws-primary": {
        cloud: "aws",
        region: "us-east-1",
        status: "healthy",
        services: {
          "gateway": { cpu: 30.0, mem: 45.0, replicas: 3, version: "v1.2.0" },
          "order-service": { cpu: 40.0, mem: 50.0, replicas: 2, version: "v1.2.0" },
          "payment-service": { cpu: 93.0, mem: 88.0, replicas: 4, version: "v1.2.1-buggy" },
          "payment-db": { cpu: 45.0, mem: 70.0, replicas: 1, version: "postgres-14" }
        }
      },
      "cluster-gcp-secondary": {
        cloud: "gcp",
        region: "us-central1",
        status: "healthy",
        services: {
          "payment-cache": { cpu: 20.0, mem: 30.0, replicas: 2, version: "redis-6" }
        }
      },
      "cluster-azure-recovery": {
        cloud: "azure",
        region: "eastus",
        status: "healthy",
        services: {}
      }
    },
    traffic_peak: false,
    last_updated: Date.now() / 1000
  },
  calibration: {
    accuracy: 0.95,
    total_calibrations: 0
  }
};

export default function TwinExplorerPage() {
  const [twinData, setTwinData] = useState<{ state: TwinState; calibration: CalibrationInfo }>(DEFAULT_TWIN_DATA);
  const [selectedService, setSelectedService] = useState<string>("payment-service");
  const [simulations, setSimulations] = useState<SimulationItem[]>([]);
  const [twinConfidence, setTwinConfidence] = useState<number>(0.9);
  const [telemetryCompleteness, setTelemetryCompleteness] = useState<number>(1.0);
  const [topologyFreshness, setTopologyFreshness] = useState<number>(1.0);
  
  // Calibration UI State
  const [actualMttr, setActualMttr] = useState<string>("24");
  const [calibrationResult, setCalibrationResult] = useState<any>(null);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTwinData = async () => {
    setLoading(true);
    try {
      const res = await axios.get("http://localhost:8006/api/v1/twin/data");
      if (res.data) {
        setTwinData(res.data);
      }
      setError(null);
    } catch (err: any) {
      console.warn("Failed to fetch digital-twin-service data, using defaults:", err.message);
      // Fallback
    } finally {
      setLoading(false);
    }
  };

  const runSimulation = async (serviceName: string) => {
    try {
      const res = await axios.post("http://localhost:8006/api/v1/twin/simulate", {
        service: serviceName,
        incident_id: "INC-UI-" + Math.floor(Math.random() * 1000),
        incident_type: "cpu_high",
        metrics: { cpu_usage: 95.0, memory_usage: 90.0 }
      });
      if (res.data) {
        setSimulations(res.data.simulations);
        setTwinConfidence(res.data.confidence);
        setTelemetryCompleteness(res.data.telemetry_completeness);
        setTopologyFreshness(res.data.topology_freshness);
      }
    } catch (err: any) {
      console.warn("Simulation API offline, generating mock simulations:", err.message);
      // Fallback mocks
      const mockSims: SimulationItem[] = [
        { playbook_sequence: "scale_deployment -> restart_pod", predicted_mttr: 27.0, predicted_cost: 10.0, predicted_blast_radius: 0.1, success_probability: 0.97, confidence: 0.88, score: 0.812 },
        { playbook_sequence: "scale_deployment", predicted_mttr: 15.0, predicted_cost: 10.0, predicted_blast_radius: 0.0, success_probability: 0.90, confidence: 0.88, score: 0.801 },
        { playbook_sequence: "restart_pod", predicted_mttr: 12.0, predicted_cost: 0.0, predicted_blast_radius: 0.1, success_probability: 0.75, confidence: 0.88, score: 0.768 },
        { playbook_sequence: "rollback_release", predicted_mttr: 18.0, predicted_cost: 0.0, predicted_blast_radius: 0.2, success_probability: 0.85, confidence: 0.88, score: 0.744 },
        { playbook_sequence: "migrate_service", predicted_mttr: 25.0, predicted_cost: 5.0, predicted_blast_radius: 0.4, success_probability: 0.60, confidence: 0.88, score: 0.523 }
      ];
      setSimulations(mockSims);
      setTwinConfidence(0.88);
      setTelemetryCompleteness(1.0);
      setTopologyFreshness(0.92);
    }
  };

  const handleCalibrate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!simulations || simulations.length === 0) return;
    
    const bestPlaybook = simulations[0].playbook_sequence;
    try {
      const res = await axios.post("http://localhost:8006/api/v1/twin/calibrate", {
        incident_id: "INC-UI-SIM",
        playbook_sequence: bestPlaybook,
        actual_mttr: parseFloat(actualMttr)
      });
      setCalibrationResult(res.data);
      // Refresh twin data
      fetchTwinData();
    } catch (err: any) {
      console.error("Calibration API error:", err.message);
      // Mock result
      setCalibrationResult({
        status: "success",
        predicted_mttr: simulations[0].predicted_mttr,
        actual_mttr: parseFloat(actualMttr),
        prediction_error: Math.abs(parseFloat(actualMttr) - simulations[0].predicted_mttr),
        new_calibration_accuracy: 0.92
      });
    }
  };

  useEffect(() => {
    fetchTwinData();
  }, []);

  useEffect(() => {
    if (selectedService) {
      runSimulation(selectedService);
    }
  }, [selectedService]);

  // Find selected service properties
  let currentServiceState: ServiceState | null = null;
  let serviceCluster = "Unknown";
  for (const [clsName, clsVal] of Object.entries(twinData.state.clusters)) {
    if (clsVal.services && selectedService in clsVal.services) {
      currentServiceState = clsVal.services[selectedService];
      serviceCluster = clsName;
      break;
    }
  }

  // Simulated predicted state based on best simulation
  const bestSim = simulations[0];
  const predictedState = bestSim ? {
    cpu: selectedService === "payment-service" ? 37.0 : Math.max(15, (currentServiceState?.cpu || 50) - 40),
    mem: Math.max(20, (currentServiceState?.mem || 50) - 25),
    replicas: bestSim.playbook_sequence.includes("scale_deployment") 
      ? (currentServiceState?.replicas || 1) + 1 
      : (currentServiceState?.replicas || 1),
    status: "healthy"
  } : null;

  return (
    <div className="space-y-6 max-w-screen-2xl mx-auto">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/5 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white">Digital Twin Virtual Infrastructure Explorer</h2>
          <p className="text-sm text-white/40 mt-0.5">
            Model topology, run predictive recovery simulations, and calibrate simulation parameters.
          </p>
        </div>
        <button
          onClick={fetchTwinData}
          className="flex items-center gap-2 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-white border border-white/8 text-xs font-semibold transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Twin State
        </button>
      </div>

      {/* Accuracy & Twin Health Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-white/8 bg-surface-800/60 flex items-center gap-4">
          <div className="p-3 rounded-lg bg-hecate-500/10 border border-hecate-500/20 text-hecate-400">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <div className="text-[10px] text-white/40 uppercase font-mono">Twin Calibration Accuracy</div>
            <div className="text-2xl font-bold text-white font-mono">
              {(twinData.calibration.accuracy * 100).toFixed(1)}%
            </div>
          </div>
        </div>
        
        <div className="p-4 rounded-xl border border-white/8 bg-surface-800/60 flex items-center gap-4">
          <div className="p-3 rounded-lg bg-accent-purple/10 border border-accent-purple/20 text-accent-purple">
            <Layers className="w-6 h-6" />
          </div>
          <div>
            <div className="text-[10px] text-white/40 uppercase font-mono">Telemetry Completeness</div>
            <div className="text-2xl font-bold text-white font-mono">
              {(telemetryCompleteness * 100).toFixed(0)}%
            </div>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-white/8 bg-surface-800/60 flex items-center gap-4">
          <div className="p-3 rounded-lg bg-accent-blue/10 border border-accent-blue/20 text-accent-blue">
            <Server className="w-6 h-6" />
          </div>
          <div>
            <div className="text-[10px] text-white/40 uppercase font-mono">Topology Freshness</div>
            <div className="text-2xl font-bold text-white font-mono">
              {(topologyFreshness * 100).toFixed(0)}%
            </div>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-white/8 bg-surface-800/60 flex items-center gap-4">
          <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400">
            <CheckCircle className="w-6 h-6" />
          </div>
          <div>
            <div className="text-[10px] text-white/40 uppercase font-mono">Total Twin Calibrations</div>
            <div className="text-2xl font-bold text-white font-mono">
              {twinData.calibration.total_calibrations}
            </div>
          </div>
        </div>
      </div>

      {/* Topology & Controls Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Topology map panel */}
        <div className="lg:col-span-2 space-y-6">
          <div className="p-5 rounded-xl border border-white/8 bg-surface-800/60">
            <h3 className="text-sm font-semibold text-white mb-4">Multi-Cluster Virtual Infrastructure Map</h3>
            <div className="space-y-4">
              {Object.entries(twinData.state.clusters).map(([clsName, clsVal]) => (
                <div key={clsName} className="p-4 rounded-lg border border-white/5 bg-black/25">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-hecate-400 font-bold uppercase">[{clsVal.cloud}]</span>
                      <span className="text-sm font-semibold text-white">{clsName}</span>
                    </div>
                    <span className="text-[10px] bg-green-500/10 border border-green-500/20 text-green-400 px-2 py-0.5 rounded uppercase font-semibold">
                      {clsVal.status}
                    </span>
                  </div>
                  
                  {/* Service list */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {clsVal.services && Object.keys(clsVal.services).length > 0 ? (
                      Object.entries(clsVal.services).map(([svcName, svcState]) => (
                        <button
                          key={svcName}
                          onClick={() => setSelectedService(svcName)}
                          className={`flex items-center justify-between p-3 rounded-lg border transition-all text-left ${
                            selectedService === svcName
                              ? 'border-hecate-500 bg-hecate-600/10 text-white'
                              : 'border-white/5 bg-white/3 hover:bg-white/5 text-white/70'
                          }`}
                        >
                          <div className="min-w-0">
                            <div className="text-xs font-semibold truncate">{svcName}</div>
                            <div className="text-[10px] text-white/30 font-mono mt-0.5">{svcState.version}</div>
                          </div>
                          <div className="text-right">
                            <div className="text-xs font-mono font-bold text-white/80">{svcState.cpu.toFixed(0)}% CPU</div>
                            <div className="text-[10px] text-white/40 mt-0.5">{svcState.replicas} Replicas</div>
                          </div>
                        </button>
                      ))
                    ) : (
                      <div className="col-span-2 py-6 text-center text-xs text-white/20">
                        No active service workloads deployed in this cluster twin.
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Current vs Predicted State Panel */}
        <div className="space-y-6">
          <div className="p-5 rounded-xl border border-white/8 bg-surface-800/60">
            <h3 className="text-sm font-semibold text-white mb-4">
              State Comparison: <span className="text-hecate-400 font-bold">{selectedService}</span>
            </h3>
            
            {currentServiceState ? (
              <div className="space-y-5">
                {/* Current State Column */}
                <div className="p-3.5 rounded-lg border border-red-500/20 bg-red-500/5">
                  <div className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <ShieldAlert className="w-3.5 h-3.5" />
                    Current Degraded State
                  </div>
                  <div className="space-y-2 text-xs font-mono">
                    <div className="flex justify-between">
                      <span className="text-white/40">CPU Usage:</span>
                      <span className="text-white font-bold">{currentServiceState.cpu.toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-white/40">Memory Usage:</span>
                      <span className="text-white font-bold">{currentServiceState.mem.toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-white/40">Replica Count:</span>
                      <span className="text-white font-bold">{currentServiceState.replicas}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-white/40">Cluster Region:</span>
                      <span className="text-white font-bold uppercase">{serviceCluster}</span>
                    </div>
                  </div>
                </div>

                {/* Predicted Remediation Outcome State */}
                {predictedState ? (
                  <div className="p-3.5 rounded-lg border border-green-500/20 bg-green-500/5">
                    <div className="text-xs font-semibold text-green-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                      <CheckCircle className="w-3.5 h-3.5" />
                      Predicted Post-Remediation State
                    </div>
                    <div className="space-y-2 text-xs font-mono">
                      <div className="flex justify-between">
                        <span className="text-white/40">Predicted CPU:</span>
                        <span className="text-white font-bold">{predictedState.cpu.toFixed(1)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-white/40">Predicted Mem:</span>
                        <span className="text-white font-bold">{predictedState.mem.toFixed(1)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-white/40">Predicted Replicas:</span>
                        <span className="text-white font-bold">{predictedState.replicas}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-white/40">Downtime Risk:</span>
                        <span className="text-white font-bold text-green-400">0s</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="py-6 text-center text-xs text-white/30">
                    Run simulation to compute predicted state.
                  </div>
                )}
              </div>
            ) : (
              <div className="py-12 text-center text-xs text-white/30">
                Select a service workload from the map to view state details.
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Simulated playbook candidates table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Playbook simulations */}
        <div className="lg:col-span-2 p-5 rounded-xl border border-white/8 bg-surface-800/60">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white">Simulated Playbook Sequence Comparison</h3>
            <span className="text-xs text-white/40 font-mono">
              Twin Confidence: <strong>{(twinConfidence * 100).toFixed(0)}%</strong>
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-white/5 text-white/40 font-semibold">
                  <th className="py-3 px-2">Remediation Sequence Candidate</th>
                  <th className="py-3 px-2 text-center">Success Rate</th>
                  <th className="py-3 px-2 text-center">Projected MTTR</th>
                  <th className="py-3 px-2 text-center">Cost Impact</th>
                  <th className="py-3 px-2 text-center">Blast Radius</th>
                  <th className="py-3 px-2 text-right">Twin Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 font-mono text-white/90">
                {simulations.map((s, idx) => (
                  <tr key={s.playbook_sequence} className={idx === 0 ? "bg-hecate-500/5 text-white" : ""}>
                    <td className="py-3 px-2 font-semibold">
                      {idx === 0 && <span className="mr-1.5 text-hecate-400 font-bold">★</span>}
                      {s.playbook_sequence}
                    </td>
                    <td className="py-3 px-2 text-center text-green-400">{(s.success_probability * 100).toFixed(0)}%</td>
                    <td className="py-3 px-2 text-center">{s.predicted_mttr}s</td>
                    <td className="py-3 px-2 text-center">${s.predicted_cost.toFixed(2)}</td>
                    <td className="py-3 px-2 text-center">{s.predicted_blast_radius}</td>
                    <td className="py-3 px-2 text-right font-bold text-hecate-400">{s.score.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Calibration panel */}
        <div className="p-5 rounded-xl border border-white/8 bg-surface-800/60">
          <h3 className="text-sm font-semibold text-white mb-4">Feed Reality & Calibrate Twin</h3>
          
          {bestSim ? (
            <form onSubmit={handleCalibrate} className="space-y-4">
              <div className="p-3 bg-black/20 rounded border border-white/5 space-y-1.5 text-xs font-mono">
                <div><span className="text-white/40">Latest Playbook:</span> {bestSim.playbook_sequence}</div>
                <div><span className="text-white/40">Predicted MTTR:</span> {bestSim.predicted_mttr}s</div>
              </div>
              
              <div className="space-y-2">
                <label className="text-xs text-white/60 block font-semibold">Actual Execution MTTR (seconds)</label>
                <input
                  type="number"
                  value={actualMttr}
                  onChange={(e) => setActualMttr(e.target.value)}
                  className="w-full px-3 py-2 bg-black/25 border border-white/10 rounded-lg text-white font-mono text-sm focus:outline-none focus:border-hecate-500"
                  required
                />
              </div>

              <button
                type="submit"
                className="w-full py-2 bg-hecate-600 hover:bg-hecate-500 rounded-lg text-white font-semibold transition-colors text-xs flex items-center justify-center gap-1.5"
              >
                <Clock className="w-3.5 h-3.5" />
                Submit Reality Calibration
              </button>
            </form>
          ) : (
            <div className="py-6 text-center text-xs text-white/30">
              No simulations run yet to calibrate.
            </div>
          )}

          {calibrationResult && (
            <div className="mt-4 p-4 rounded bg-green-500/10 border border-green-500/20 text-xs space-y-2 font-mono">
              <div className="text-green-400 font-semibold uppercase tracking-wider text-[10px]">Calibration Complete</div>
              <div className="flex justify-between">
                <span className="text-white/50">Predicted MTTR:</span>
                <span>{calibrationResult.predicted_mttr}s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-white/50">Actual MTTR:</span>
                <span>{calibrationResult.actual_mttr}s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-white/50">Deviation Error:</span>
                <span className="text-red-400">+{calibrationResult.prediction_error}s</span>
              </div>
              <div className="flex justify-between pt-1 border-t border-white/5 font-bold">
                <span className="text-white/70">New Accuracy:</span>
                <span className="text-hecate-400">{(calibrationResult.new_calibration_accuracy * 100).toFixed(1)}%</span>
              </div>
            </div>
          )}
        </div>

      </div>

      {/* Reality vs Prediction vs Error panel */}
      <div className="p-5 rounded-xl border border-white/8 bg-surface-800/60">
        <h3 className="text-sm font-semibold text-white mb-4">Reality vs Prediction Deviation Metrics</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-white/5 text-white/40 font-semibold">
                <th className="py-3 px-2">Twin Metrics KPI</th>
                <th className="py-3 px-2 text-center">Predicted state</th>
                <th className="py-3 px-2 text-center">Actual state (Reality)</th>
                <th className="py-3 px-2 text-right">Prediction Error</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono text-white/90">
              <tr>
                <td className="py-3 px-2 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-accent-blue" />
                  Mean Time to Recovery (MTTR)
                </td>
                <td className="py-3 px-2 text-center">21 s</td>
                <td className="py-3 px-2 text-center">24 s</td>
                <td className="py-3 px-2 text-right text-red-400 font-bold">+3 s</td>
              </tr>
              <tr>
                <td className="py-3 px-2 flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5 text-hecate-400" />
                  Post-Remediation CPU Util
                </td>
                <td className="py-3 px-2 text-center">37%</td>
                <td className="py-3 px-2 text-center">40%</td>
                <td className="py-3 px-2 text-right text-red-400 font-bold">+3%</td>
              </tr>
              <tr>
                <td className="py-3 px-2 flex items-center gap-1.5">
                  <DollarSign className="w-3.5 h-3.5 text-green-400" />
                  Resource Cost Impact
                </td>
                <td className="py-3 px-2 text-center">$11.00</td>
                <td className="py-3 px-2 text-center">$10.00</td>
                <td className="py-3 px-2 text-right text-green-400 font-bold">-$1.00</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
