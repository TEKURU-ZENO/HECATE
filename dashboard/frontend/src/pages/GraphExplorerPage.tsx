import { useEffect, useState, useRef } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import {
  Share2,
  RefreshCw,
  Info,
  Terminal,
  Activity,
  PlayCircle,
  HelpCircle,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';
import axios from 'axios';

interface GraphNode {
  data: {
    id: string;
    label: string;
    type: string;
    status: string;
    [key: string]: any;
  };
}

interface GraphEdge {
  data: {
    source: string;
    target: string;
    label: string;
    [key: string]: any;
  };
}

const API_BASE = 'http://localhost:8000/api/v1';

export default function GraphExplorerPage() {
  const [elements, setElements] = useState<(GraphNode | GraphEdge)[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [cypherQuery, setCypherQuery] = useState('');
  const [queryResults, setQueryResults] = useState<any>(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cyRef = useRef<any>(null);

  const fetchGraphData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API_BASE}/graph/data`);
      if (res.data && (res.data.nodes || res.data.edges)) {
        const nodes = res.data.nodes || [];
        const edges = res.data.edges || [];
        setElements([...nodes, ...edges]);
      }
    } catch (err: any) {
      console.error(err);
      setError('Failed to fetch graph data. Is graph-service running?');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraphData();
  }, []);

  const handleNodeClick = (nodeData: any) => {
    setSelectedNode(nodeData);
  };

  const runCustomQuery = async () => {
    if (!cypherQuery.trim()) return;
    setQueryLoading(true);
    setQueryResults(null);
    try {
      const res = await axios.post(`${API_BASE}/graph/query`, {
        query: cypherQuery,
        parameters: {},
      });
      setQueryResults(res.data.data || res.data);
    } catch (err: any) {
      setQueryResults({ error: err.response?.data?.detail || err.message });
    } finally {
      setQueryLoading(false);
    }
  };

  // Node styles based on the suggested color palette:
  // Healthy: Green (#22c55e)
  // Predicted: Blue (#3b82f6)
  // Degraded: Yellow (#eab308)
  // Incident: Red (#ef4444)
  // Approval: Orange (#f97316)
  // Remediated / Playbook: Purple (#a855f7)
  const cytoscapeStylesheet = [
    {
      selector: 'node',
      style: {
        label: 'data(label)',
        'text-valign': 'center',
        'text-halign': 'center',
        color: '#ffffff',
        'font-size': '11px',
        'font-family': 'JetBrains Mono, Courier New, monospace',
        'background-color': '#1f2937',
        width: '70px',
        height: '70px',
        'border-width': '2px',
        'border-color': '#4b5563',
        'transition-property': 'background-color, border-color',
        'transition-duration': '0.3s',
      },
    },
    {
      selector: 'node[type="Service"]',
      style: {
        'background-color': '#10b981', // healthy green
        'border-color': '#047857',
        shape: 'round-rectangle',
      },
    },
    {
      selector: 'node[type="Service"][status="degraded"]',
      style: {
        'background-color': '#eab308', // degraded yellow
        'border-color': '#a16207',
      },
    },
    {
      selector: 'node[type="Incident"]',
      style: {
        'background-color': '#ef4444', // incident red
        'border-color': '#b91c1c',
        shape: 'ellipse',
      },
    },
    {
      selector: 'node[type="Incident"][status="remediated"]',
      style: {
        'background-color': '#a855f7', // remediated purple
        'border-color': '#7e22ce',
      },
    },
    {
      selector: 'node[type="Incident"][status="awaiting_approval"]',
      style: {
        'background-color': '#f97316', // approval orange
        'border-color': '#c2410c',
      },
    },
    {
      selector: 'node[status="predicted"]',
      style: {
        'background-color': '#3b82f6', // predicted blue
        'border-color': '#1d4ed8',
      },
    },
    {
      selector: 'node[type="Approval"]',
      style: {
        'background-color': '#f97316', // approval orange
        'border-color': '#c2410c',
        shape: 'diamond',
      },
    },
    {
      selector: 'node[type="Approval"][status="approved"]',
      style: {
        'background-color': '#10b981', // green
        'border-color': '#047857',
      },
    },
    {
      selector: 'node[type="Approval"][status="rejected"]',
      style: {
        'background-color': '#ef4444', // red
        'border-color': '#b91c1c',
      },
    },
    {
      selector: 'node[type="Playbook"]',
      style: {
        'background-color': '#a855f7', // playbook purple
        'border-color': '#7e22ce',
        shape: 'hexagon',
      },
    },
    {
      selector: 'node[type="Recommendation"]',
      style: {
        'background-color': '#6366f1', // recommendation indigo
        'border-color': '#4338ca',
        shape: 'triangle',
      },
    },
    {
      selector: 'edge',
      style: {
        width: 2,
        'line-color': '#4b5563',
        'target-arrow-color': '#4b5563',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        label: 'data(label)',
        'font-size': '8px',
        'text-background-opacity': 0.7,
        'text-background-color': '#0f172a',
        'text-background-padding': '2px',
        color: '#9ca3af',
        'font-family': 'monospace',
      },
    },
    {
      selector: 'edge[label="TRIGGERED"]',
      style: {
        'line-color': '#f87171',
        'target-arrow-color': '#ef4444',
        width: 3,
        'line-style': 'dashed',
      },
    },
    {
      selector: 'edge[label="RESOLVED_BY"]',
      style: {
        'line-color': '#c084fc',
        'target-arrow-color': '#a855f7',
        width: 3,
      },
    },
  ];

  const triggerLayout = () => {
    if (cyRef.current) {
      cyRef.current.layout({ name: 'cose', animate: true, fit: true }).run();
    }
  };

  const getStatusIcon = (status: string, type: string) => {
    const s = status?.toLowerCase();
    const t = type?.toLowerCase();
    if (s === 'healthy' || s === 'remediated' || s === 'approved') {
      return <CheckCircle className="w-5 h-5 text-accent-green" />;
    }
    if (s === 'degraded' || s === 'pending') {
      return <AlertCircle className="w-5 h-5 text-accent-yellow" />;
    }
    if (s === 'incident' || s === 'failed' || s === 'rejected') {
      return <AlertCircle className="w-5 h-5 text-accent-red" />;
    }
    if (t === 'playbook') {
      return <PlayCircle className="w-5 h-5 text-accent-purple" />;
    }
    return <Info className="w-5 h-5 text-hecate-400" />;
  };

  return (
    <div className="flex flex-col gap-6 p-6 min-h-[calc(100vh-73px)] text-white">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-white via-white/90 to-white/50 bg-clip-text text-transparent">
            Knowledge Graph Explorer
          </h1>
          <p className="text-sm text-white/40">
            Real-time relationship topology: causality, prediction history, and operational outcomes
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchGraphData}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh Graph
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-accent-red/10 border border-accent-red/20 text-accent-red text-sm">
          {error}
        </div>
      )}

      {/* Main Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-[500px]">
        {/* Graph Canvas */}
        <div className="lg:col-span-2 relative flex flex-col rounded-xl bg-surface-900 border border-white/5 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-white/5 bg-white/3">
            <div className="flex items-center gap-2">
              <Share2 className="w-4 h-4 text-hecate-400" />
              <span className="text-sm font-semibold">Topology Visualizer</span>
            </div>
            <button
              onClick={triggerLayout}
              className="text-xs text-hecate-400 hover:text-white transition-colors"
            >
              Reset Layout
            </button>
          </div>

          <div className="flex-1 w-full bg-slate-950/40 relative" style={{ height: '550px' }}>
            {loading && elements.length === 0 ? (
              <div className="absolute inset-0 flex items-center justify-center bg-surface-950/80 z-10">
                <RefreshCw className="w-8 h-8 text-hecate-500 animate-spin" />
              </div>
            ) : elements.length === 0 ? (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-white/40 gap-2">
                <HelpCircle className="w-12 h-12" />
                <span>No topology data available.</span>
              </div>
            ) : (
              <CytoscapeComponent
                elements={elements}
                style={{ width: '100%', height: '100%' }}
                stylesheet={cytoscapeStylesheet}
                cy={(cy) => {
                  cyRef.current = cy;
                  cy.on('tap', 'node', (evt) => {
                    handleNodeClick(evt.target.data());
                  });
                  cy.layout({ name: 'cose', animate: false }).run();
                }}
              />
            )}
          </div>
        </div>

        {/* Details Sidebar */}
        <div className="flex flex-col gap-6">
          {/* Node Details Card */}
          <div className="flex flex-col rounded-xl bg-surface-900 border border-white/5 overflow-hidden">
            <div className="flex items-center gap-2 px-5 py-4 border-b border-white/5 bg-white/3">
              <Info className="w-4 h-4 text-hecate-400" />
              <span className="text-sm font-semibold">Node Inspector</span>
            </div>

            <div className="p-5 flex-1 flex flex-col justify-between">
              {selectedNode ? (
                <div className="space-y-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-lg font-bold text-white font-mono">{selectedNode.id}</h3>
                      <span className="inline-flex items-center px-2.5 py-0.5 mt-1 rounded-full text-xs font-medium bg-white/5 text-white/70">
                        {selectedNode.type}
                      </span>
                    </div>
                    {getStatusIcon(selectedNode.status, selectedNode.type)}
                  </div>

                  <div className="pt-4 border-t border-white/5 space-y-3">
                    <div>
                      <span className="text-xs text-white/40 block">Label</span>
                      <span className="text-sm font-mono">{selectedNode.label}</span>
                    </div>
                    <div>
                      <span className="text-xs text-white/40 block">Status</span>
                      <span className="text-sm font-mono capitalize">{selectedNode.status || 'unknown'}</span>
                    </div>
                    {Object.entries(selectedNode).map(([key, val]) => {
                      if (['id', 'label', 'type', 'status'].includes(key)) return null;
                      return (
                        <div key={key}>
                          <span className="text-xs text-white/40 block capitalize">{key.replace('_', ' ')}</span>
                          <span className="text-sm font-mono break-all">{JSON.stringify(val)}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-white/30 space-y-2">
                  <Activity className="w-8 h-8 mx-auto animate-pulse text-hecate-500/50" />
                  <p className="text-sm">Click a node on the canvas to inspect its details and relationships</p>
                </div>
              )}
            </div>
          </div>

          {/* Color Legend Card */}
          <div className="flex flex-col rounded-xl bg-surface-900 border border-white/5 p-5 space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-white/40">Status Key</h4>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded bg-accent-green inline-block" />
                <span>Healthy</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded bg-accent-blue inline-block" />
                <span>Predicted</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded bg-accent-yellow inline-block" />
                <span>Degraded</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded bg-accent-red inline-block" />
                <span>Incident</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded bg-accent-orange inline-block" />
                <span>Approval Gate</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded bg-accent-purple inline-block" />
                <span>Remediated</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Query Terminal */}
      <div className="flex flex-col rounded-xl bg-surface-900 border border-white/5 overflow-hidden">
        <div className="flex items-center gap-2 px-5 py-4 border-b border-white/5 bg-white/3">
          <Terminal className="w-4 h-4 text-hecate-400" />
          <span className="text-sm font-semibold">Cypher Query Terminal (Graph Gateway)</span>
        </div>
        <div className="p-5 space-y-4">
          <div className="flex gap-3">
            <input
              type="text"
              value={cypherQuery}
              onChange={(e) => setCypherQuery(e.target.value)}
              placeholder="MATCH (n) RETURN n LIMIT 10"
              className="flex-1 px-4 py-2 text-sm rounded-lg bg-surface-950 border border-white/10 focus:outline-none focus:border-hecate-500 font-mono text-white placeholder-white/20"
            />
            <button
              onClick={runCustomQuery}
              disabled={queryLoading}
              className="px-5 py-2 rounded-lg bg-hecate-600 hover:bg-hecate-500 font-medium text-sm transition-colors disabled:opacity-50"
            >
              {queryLoading ? 'Executing...' : 'Run Query'}
            </button>
          </div>

          <div className="flex gap-2">
            <span className="text-xs text-white/30">Presets:</span>
            <button
              onClick={() => setCypherQuery('MATCH (s:Service)-->(d:Service) RETURN s, d')}
              className="text-xs bg-white/5 border border-white/5 hover:bg-white/10 px-2 py-0.5 rounded text-white/70"
            >
              Get Service Topology
            </button>
            <button
              onClick={() => setCypherQuery("MATCH (i:Incident) WHERE i.status = 'investigating' RETURN i")}
              className="text-xs bg-white/5 border border-white/5 hover:bg-white/10 px-2 py-0.5 rounded text-white/70"
            >
              Get Active Incidents
            </button>
            <button
              onClick={() => setCypherQuery('MATCH (a:Approval)-[:GOVERNS]->(i:Incident) RETURN a, i')}
              className="text-xs bg-white/5 border border-white/5 hover:bg-white/10 px-2 py-0.5 rounded text-white/70"
            >
              Get Approval Gates
            </button>
          </div>

          {queryResults && (
            <div className="p-4 rounded-lg bg-surface-950 border border-white/5 max-h-60 overflow-y-auto font-mono text-xs text-white/80">
              <pre>{JSON.stringify(queryResults, null, 2)}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
