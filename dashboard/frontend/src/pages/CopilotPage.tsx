import { useState, useRef, useEffect } from 'react';
import {
  Send,
  Sparkles,
  MessageSquare,
  Activity,
  History,
  TrendingUp,
  Shield,
  Zap,
  Cpu,
  BookOpen,
  ArrowRight,
  RefreshCw
} from 'lucide-react';

interface Source {
  id: string;
  source: string;
  text: string;
  score?: number;
  metadata?: any;
}

interface Message {
  sender: 'user' | 'assistant';
  text: string;
  mode?: string;
  sources?: Source[];
  timestamp: Date;
}

const SUGGESTIONS = [
  { text: "What is our average MTTR?", icon: History },
  { text: "How many incidents were prevented?", icon: Zap },
  { text: "Why did payment-db fail?", icon: Cpu },
  { text: "Show recent approvals", icon: Shield },
  { text: "How accurate are our predictions?", icon: TrendingUp },
  { text: "What remediation works best?", icon: Activity },
  { text: "Top root causes this month", icon: BookOpen }
];

export default function CopilotPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: 'assistant',
      text: "Hello! I am HECATE Copilot, your AI reliability operations assistant. I can query our incidents, operational memory, policies, approvals, recommendations, and predictions. Ask me anything about our platform's self-healing activities or metrics!",
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (textToSend: string) => {
    if (!textToSend.trim() || loading) return;

    const userMessage: Message = {
      sender: 'user',
      text: textToSend,
      timestamp: new Date()
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('/api/v1/copilot/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: textToSend })
      });

      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${await response.text()}`);
      }

      const data = await response.json();
      const assistantMessage: Message = {
        sender: 'assistant',
        text: data.response,
        mode: data.mode,
        sources: data.sources,
        timestamp: new Date()
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error: any) {
      const errorMessage: Message = {
        sender: 'assistant',
        text: `Sorry, I encountered an error communicating with the Copilot Service: ${error.message || error}`,
        timestamp: new Date()
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const getSourceIcon = (source: string) => {
    switch (source) {
      case 'operational_memory':
        return History;
      case 'approvals':
        return Shield;
      case 'prediction_outcomes':
        return Zap;
      case 'policies':
        return BookOpen;
      case 'recommendations':
        return Sparkles;
      default:
        return Cpu;
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-6rem)] max-w-5xl mx-auto gap-4">
      {/* Copilot Header */}
      <div className="flex items-center justify-between p-4 rounded-xl bg-surface-900/40 border border-white/5 backdrop-blur-sm shadow-md">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-hecate-500 to-accent-purple shadow-lg shadow-hecate-500/20">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white/90">HECATE Copilot</h2>
            <p className="text-[10px] text-white/40">Natural Language Operations & Reliability Assistant</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wider font-mono bg-hecate-500/20 text-hecate-300 border border-hecate-500/30 px-2.5 py-1 rounded-full flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-hecate-400 animate-pulse" />
            Interactive Retrieval
          </span>
        </div>
      </div>

      {/* Main Messaging Container */}
      <div className="flex flex-col flex-1 min-h-0 rounded-2xl bg-surface-900/30 border border-white/5 backdrop-blur-md shadow-2xl p-4 gap-4">
        {/* Messages Thread */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-2 scrollbar-thin scrollbar-thumb-white/5 scrollbar-track-transparent">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex flex-col ${
                msg.sender === 'user' ? 'items-end' : 'items-start'
              }`}
            >
              {/* Message Bubble */}
              <div
                className={`relative px-4 py-3 rounded-2xl max-w-[85%] text-sm leading-relaxed shadow-sm transition-all duration-200 ${
                  msg.sender === 'user'
                    ? 'bg-hecate-600/30 border border-hecate-500/20 text-white rounded-tr-none'
                    : 'bg-white/5 border border-white/8 text-white/90 rounded-tl-none'
                }`}
              >
                {msg.text}

                {/* Mode indicator for assistant */}
                {msg.sender === 'assistant' && msg.mode && (
                  <span className="absolute -top-2.5 -right-2 text-[8px] tracking-wider uppercase font-mono px-1.5 py-0.5 rounded border border-white/10 bg-surface-950 text-white/40 shadow">
                    {msg.mode} mode
                  </span>
                )}
              </div>

              {/* Sources and Citations */}
              {msg.sender === 'assistant' && msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 ml-2 flex flex-wrap gap-1.5 items-center">
                  <span className="text-[9px] text-white/30 uppercase tracking-wider font-mono mr-1">Sources:</span>
                  {msg.sources.map((src, sIdx) => {
                    const SrcIcon = getSourceIcon(src.source);
                    return (
                      <div
                        key={sIdx}
                        title={src.text}
                        className="group flex items-center gap-1 px-2 py-0.5 rounded-full border border-white/5 bg-white/2 hover:bg-white/5 transition-all text-[10px] text-white/50 cursor-help"
                      >
                        <SrcIcon className="w-2.5 h-2.5 text-white/40" />
                        <span className="capitalize">{src.source.replace('_', ' ')}</span>
                        <span className="text-[9px] text-white/20 font-mono">#{src.id.split('-').pop()?.substring(0, 4)}</span>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Timestamp */}
              <span className="text-[9px] text-white/25 mt-1 px-2">
                {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          ))}

          {/* Typing Indicator */}
          {loading && (
            <div className="flex flex-col items-start">
              <div className="flex gap-1.5 px-4 py-3 rounded-2xl rounded-tl-none bg-white/5 border border-white/8 text-white/40 shadow-sm">
                <span className="h-1.5 w-1.5 rounded-full bg-white/40 animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="h-1.5 w-1.5 rounded-full bg-white/40 animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="h-1.5 w-1.5 rounded-full bg-white/40 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggestion Chips */}
        {messages.length === 1 && !loading && (
          <div className="flex flex-col gap-2 border-t border-white/5 pt-4">
            <span className="text-[10px] uppercase tracking-wider font-mono text-white/30 px-1">Suggested Queries</span>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((suggestion, index) => {
                const SugIcon = suggestion.icon;
                return (
                  <button
                    key={index}
                    onClick={() => handleSend(suggestion.text)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-white/8 bg-white/3 hover:bg-white/8 hover:border-white/15 transition-all text-xs text-white/60 hover:text-white cursor-pointer shadow-sm active:scale-95 duration-100"
                  >
                    <SugIcon className="w-3.5 h-3.5 text-white/40" />
                    <span>{suggestion.text}</span>
                    <ArrowRight className="w-2.5 h-2.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Chat Input Area */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend(input);
          }}
          className="flex items-center gap-2 border-t border-white/5 pt-4"
        >
          <div className="relative flex-1">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask HECATE Copilot a question..."
              disabled={loading}
              className="w-full bg-white/3 hover:bg-white/5 focus:bg-white/5 border border-white/8 focus:border-hecate-500/40 rounded-xl px-4 py-3 text-sm text-white placeholder-white/20 focus:outline-none transition-all duration-200 pr-10 focus:shadow-[0_0_15px_rgba(99,102,241,0.05)] disabled:opacity-50"
            />
            <MessageSquare className="absolute right-3.5 top-3.5 w-4 h-4 text-white/15 pointer-events-none" />
          </div>

          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="flex items-center justify-center w-11 h-11 rounded-xl bg-gradient-to-br from-hecate-600 to-hecate-500 hover:from-hecate-500 hover:to-hecate-400 text-white font-medium shadow-md shadow-hecate-600/10 active:scale-95 disabled:opacity-50 disabled:pointer-events-none transition-all duration-200"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
