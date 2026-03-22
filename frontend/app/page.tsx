"use client";
import React, { useState, useRef, useEffect } from "react";
import { FiSettings, FiSearch, FiX } from "react-icons/fi";

// --- Types & Interfaces ---
interface Message {
  agentIdx: number;
  content: string;
  timestamp: string;
}

interface Agent {
  name: string;
  color: string;
  bg: string;
  text: string;
  logo: string | null;
  initials?: string;
}

interface Source {
  title: string;
  url: string;
}

interface QueuedMessage {
  agentIdx: number;
  content: string;
}

// --- Timing Engine ---
const BASE_TYPE_SPEED = 15;
const MESSAGE_PREVIEW_CHARS = 220;

// --- Sub-Components ---
const Typewriter = ({ text, speedMs }: { text: string; speedMs: number }) => {
  const [displayed, setDisplayed] = useState("");

  useEffect(() => {
    if (!text) {
      setDisplayed("");
      return;
    }
    if (speedMs < 5) {
      setDisplayed(text);
      return;
    }

    setDisplayed("");
    let i = 0;
    const interval = setInterval(() => {
      setDisplayed((prev) => text.substring(0, i + 1));
      i++;
      if (i >= text.length) {
        clearInterval(interval);
      }
    }, speedMs);

    return () => clearInterval(interval);
  }, [text, speedMs]);

  return <span>{displayed}</span>;
};

const AgentTelemetry = ({ isActive, speedMultiplier, hasError }: { isActive: boolean; speedMultiplier: number; hasError: boolean }) => {
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    if (!isActive) return;

    if (hasError) {
      setLogs((prev) => {
        const safe = prev.filter(Boolean);
        if (!safe.includes("ERR: WebSocket connection failed.")) {
          return [...safe, "ERR: WebSocket connection failed.", "SYSTEM: Swarm initialization halted."];
        }
        return safe;
      });
      return;
    }

    const sequence = [
      "INIT protocol::fetch_ai_swarm",
      "SPAWN_NODE: Jacobin (Bias: Left) ... OK",
      "SPAWN_NODE: WSJ (Bias: Center-Right) ... OK",
      "SPAWN_NODE: Fox (Bias: Right) ... OK",
      "SPAWN_NODE: Wired (Domain: Tech) ... OK",
      "CONNECTING wss://fetch.ai/orchestrator ... 200 OK",
      "EXECUTE fetch_papers() -> Parsing 8,402 external links...",
      "WARN: Rate limit threshold near on Target API. Rotating proxies...",
      "VECTORIZING 4,209 semantic memory chunks...",
      "ALIGNING multi-agent consensus caches...",
      "SYSTEM: Swarm alignment complete. Awaiting moderator."
    ];

    let i = 0;
    setLogs([]);
    const interval = setInterval(() => {
      if (i < sequence.length) {
        setLogs((prev) => {
          const newLogs = [...prev.slice(-4), sequence[i]];
          return newLogs.filter(Boolean);
        });
        i++;
      } else {
        clearInterval(interval);
      }
    }, 400 / speedMultiplier);

    return () => clearInterval(interval);
  }, [isActive, speedMultiplier, hasError]);

  return (
    <div className={`w-full bg-[#0a0a0a] border rounded-xl p-4 font-mono text-[10px] sm:text-xs h-36 overflow-hidden relative shadow-[inset_0_0_20px_rgba(0,0,0,0.8)] mt-4 transition-colors duration-300 ${hasError ? 'border-red-900/50' : 'border-zinc-800/80'}`}>
      <div className="absolute top-3 right-4 flex items-center gap-2">
        <span className="relative flex h-2 w-2">
          {isActive && !hasError && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>}
          <span className={`relative inline-flex rounded-full h-2 w-2 ${hasError ? 'bg-red-500' : isActive ? 'bg-indigo-500' : 'bg-zinc-600'}`}></span>
        </span>
        <span className="text-zinc-500 font-bold uppercase tracking-widest text-[8px]">Agent Telemetry</span>
      </div>
      <div className="flex flex-col justify-end h-full pb-1">
        {logs.map((log, idx) => {
          if (!log) return null;
          return (
            <div key={idx} className="flex gap-3 animate-in fade-in slide-in-from-bottom-2 duration-200 mt-1.5">
              <span className="text-zinc-600 shrink-0">[{new Date().toISOString().split('T')[1].slice(0, 11)}]</span>
              <span className={log.includes("WARN") ? "text-amber-400" : log.includes("ERR") ? "text-red-400" : log.includes("OK") ? "text-emerald-400" : log.includes("SYSTEM") ? "text-indigo-400" : "text-zinc-300"}>
                {log}
              </span>
            </div>
          );
        })}
        {isActive && !hasError && (
          <div className="w-2 h-3 bg-zinc-400 animate-pulse mt-2 ml-24" />
        )}
      </div>
    </div>
  );
};

// --- Config ---
const TRENDING_TOPICS = [
  "AGI Timelines",
  "Federal Reserve Rates",
  "TikTok Divestment"
];

const ACTS = [
  { id: 1, label: "Briefing" },
  { id: 2, label: "Debate" },
  { id: 3, label: "Synthesis" },
];

const agentMetadata: Agent[] = [
  { name: "The Contrarian", color: "border-rose-500", bg: "bg-rose-900/20", text: "text-rose-400", logo: null, initials: "C" },
  { name: "The Hype Man", color: "border-blue-500", bg: "bg-blue-900/20", text: "text-blue-400", logo: null, initials: "H" },
  { name: "The Materialist", color: "border-emerald-500", bg: "bg-emerald-900/20", text: "text-emerald-400", logo: null, initials: "M" },
];

const unknownAgent: Agent = { name: "Independent", color: "border-zinc-500", bg: "bg-zinc-800/30", text: "text-zinc-300", logo: null, initials: "IND" };

export default function PunditProtocolPage() {
  // --- UI & Content State ---
  const [topic, setTopic] = useState("");
  const [inputError, setInputError] = useState("");
  const [backendError, setBackendError] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [currentAct, setCurrentAct] = useState<number>(0);
  const [liveSource, setLiveSource] = useState(true); // True = News API, False = Backend Chaos Mock
  const [speedMode, setSpeedMode] = useState<"realtime" | "demo">("realtime");
  const speedMultiplier = speedMode === "demo" ? 10 : 1;

  // --- Settings State ---
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [wpm, setWpm] = useState<number>(250);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [showChat, setShowChat] = useState(true);
  const [expandedMessages, setExpandedMessages] = useState<Record<number, boolean>>({});
  
  const searchInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const queueRef = useRef<QueuedMessage[]>([]);
  const processingRef = useRef(false);
  const pendingSummaryRef = useRef<{ conclusion: string; sources?: Source[] } | null>(null);
  const roundBucketsRef = useRef<Record<number, Record<number, QueuedMessage>>>({});
  const roundTimersRef = useRef<Record<number, number>>({});

  // Load Settings
  useEffect(() => {
    const savedWpm = localStorage.getItem("pundit_wpm");
    const savedTheme = localStorage.getItem("pundit_theme");
    if (savedWpm) setWpm(Number(savedWpm));
    if (savedTheme === "light" || savedTheme === "dark") setTheme(savedTheme);
  }, []);

  // --- Keyboard Shortcuts Engine ---
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isInputFocused = document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA';

      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
      
      if (e.key === 'Escape') {
        setIsSettingsOpen((prev) => !prev);
      }

      if (e.key === 'Enter' && !isInputFocused) {
        e.preventDefault();
        searchInputRef.current?.focus();
      }

      if (e.key.toLowerCase() === 'f' && !isInputFocused) {
        e.preventDefault();
        setShowChat((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleWpmChange = (newWpm: number) => {
    setWpm(newWpm);
    localStorage.setItem("pundit_wpm", newWpm.toString());
  };

  const handleThemeChange = (newTheme: "dark" | "light") => {
    setTheme(newTheme);
    localStorage.setItem("pundit_theme", newTheme);
  };

  // --- Data State ---
  const [moderatorBrief, setModeratorBrief] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [moderatorSynthesis, setModeratorSynthesis] = useState("");
  const [citedSources, setCitedSources] = useState<Source[]>([]);
  const [activeTypist, setActiveTypist] = useState<number | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, activeTypist]);

  useEffect(() => {
    return () => {
      Object.values(roundTimersRef.current).forEach((id) => window.clearTimeout(id));
    };
  }, []);

  const handleClearCache = () => {
    localStorage.clear();
    sessionStorage.clear();
    window.location.reload();
  };

  // --- Core Execution Logic (100% Backend Connected) ---
  const triggerAnalysis = (query: string) => {
    const cleanTopic = query.trim();
    if (!cleanTopic) return;

    if (cleanTopic.length > 120) {
      setInputError("Query too long. Keep it under 120 characters.");
      return;
    }
    if (/[<>{}|\\]/.test(cleanTopic)) {
      setInputError("Invalid input: Special characters (<, >, {, }, \\, |) are locked out.");
      return;
    }
    
    setTopic(cleanTopic);
    setInputError(""); 
    setBackendError(false); 
    setIsAnalyzing(true);
    setCurrentAct(1); 
    setMessages([]);
    setCitedSources([]);
    setActiveTypist(null);
    setShowChat(true);
    setExpandedMessages({});
    queueRef.current = [];
    processingRef.current = false;
    pendingSummaryRef.current = null;
    roundBucketsRef.current = {};
    Object.values(roundTimersRef.current).forEach((id) => window.clearTimeout(id));
    roundTimersRef.current = {};

    const ws = new WebSocket(`ws://localhost:8080/ws/debate`);

    const speakerMap: Record<string, number> = {
      "The_Contrarian": 0,
      "The_Hype_Man": 1,
      "The_Materialist": 2,
    };

    const enqueueRound = (round: number, agentIdx: number, content: string) => {
      const buckets = roundBucketsRef.current;
      const bucket = buckets[round] || {};
      bucket[agentIdx] = { agentIdx, content };
      buckets[round] = bucket;

      const expected = agentMetadata.length;
      if (Object.keys(bucket).length >= expected) {
        flushRound(round);
        return;
      }

      const existingTimer = roundTimersRef.current[round];
      if (existingTimer) window.clearTimeout(existingTimer);
      roundTimersRef.current[round] = window.setTimeout(() => flushRound(round), 1200 / speedMultiplier);
    };

    const flushRound = (round: number) => {
      const bucket = roundBucketsRef.current[round];
      if (!bucket) return;
      const timer = roundTimersRef.current[round];
      if (timer) window.clearTimeout(timer);
      delete roundTimersRef.current[round];
      delete roundBucketsRef.current[round];

      for (let i = 0; i < agentMetadata.length; i++) {
        const msg = bucket[i];
        if (msg) queueRef.current.push(msg);
      }
      processQueue();
    };

    const finalizeSummary = (payload: { conclusion: string; sources?: Source[] }) => {
      setCurrentAct(3);
      setModeratorSynthesis(payload.conclusion || "");
      if (payload.sources) setCitedSources(payload.sources);
      setIsAnalyzing(false);
      setShowChat(false);
    };

    const computeDelayMs = (text: string) => {
      const words = text.trim().split(/\s+/).filter(Boolean).length;
      const base = (words * 60000) / Math.max(120, wpm);
      const scaled = base / speedMultiplier;
      return Math.min(8000, Math.max(650, Math.round(scaled)));
    };

    const processQueue = () => {
      if (processingRef.current) return;
      processingRef.current = true;

      const step = () => {
        const next = queueRef.current.shift();
        if (!next) {
          processingRef.current = false;
          if (pendingSummaryRef.current) {
            const payload = pendingSummaryRef.current;
            pendingSummaryRef.current = null;
            finalizeSummary(payload);
          }
          return;
        }
        setCurrentAct(2);
        setActiveTypist(next.agentIdx);
        const delay = computeDelayMs(next.content);
        window.setTimeout(() => {
          setActiveTypist(null);
          setMessages((prev) => [
            ...prev,
            {
              agentIdx: next.agentIdx,
              content: next.content,
              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            },
          ]);
          window.setTimeout(step, 200 / speedMultiplier);
        }, delay);
      };

      step();
    };

    ws.onopen = () => {
      ws.send(JSON.stringify({
        topic: cleanTopic,
        is_chaos_mode: !liveSource,
        persona_mode: liveSource ? "sources" : "chaos"
      }));
      setModeratorBrief(`Sourcing live context for: ${cleanTopic}...`);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      switch (data.type) {
        case "overview": 
          setModeratorBrief(data.overview || "Brief received.");
          if (Array.isArray(data.sources)) setCitedSources(data.sources);
          break;
        case "turn": {
          const speaker = String(data.speaker || "");
          const agentIdx = speakerMap[speaker] ?? 0;
          const round = Number(data.round ?? 0);
          enqueueRound(round, agentIdx, data.text || "");
          break;
        }
        case "summary":
          if (processingRef.current || queueRef.current.length > 0) {
            pendingSummaryRef.current = {
              conclusion: data.conclusion || "",
              sources: Array.isArray(data.sources) ? data.sources : undefined,
            };
          } else {
            finalizeSummary({
              conclusion: data.conclusion || "",
              sources: Array.isArray(data.sources) ? data.sources : undefined,
            });
          }
          ws.close();
          break;
        case "error":
          setBackendError(true);
          setModeratorBrief(String(data.error || "Backend error"));
          setIsAnalyzing(false);
          break;
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket Error:", err);
      setBackendError(true); 
      setModeratorBrief("Network Error: Could not connect to the Backend Orchestrator.");
      setIsAnalyzing(false);
    };
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    triggerAnalysis(topic);
  };

  function renderAvatar(agent: Agent) {
    return agent.logo ? (
      <img src={agent.logo} alt={agent.name} className="w-full h-full object-cover rounded-full bg-white p-0.5" />
    ) : (
      <span className={`font-mono font-bold text-lg ${agent.text}`}>{agent.initials}</span>
    );
  }

  return (
    <div className={theme === "light" ? "invert hue-rotate-180" : ""}>
      <main className={`relative min-h-screen w-full flex flex-col items-center transition-all duration-1000 p-0 overflow-x-hidden
        ${!liveSource ? "bg-[#140202]" : "bg-zinc-950"} text-zinc-100 font-sans`}>
        
        {/* --- Settings Modal Overlay --- */}
        {isSettingsOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl p-6 w-full max-w-sm flex flex-col gap-6 animate-in zoom-in-95 duration-200">
              <div className="flex justify-between items-center">
                <h2 className="text-xl font-bold text-zinc-100">Settings</h2>
                <button onClick={() => setIsSettingsOpen(false)} className="p-1 text-zinc-500 hover:text-zinc-300 transition-colors">
                  <FiX size={24} />
                </button>
              </div>

              <div className="flex flex-col gap-5">
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-bold uppercase tracking-wider text-zinc-400">Reading Speed (WPM)</label>
                  <input 
                    type="number" 
                    value={wpm} 
                    onChange={(e) => handleWpmChange(Number(e.target.value) || 250)}
                    min="50"
                    max="1000"
                    className="bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2.5 text-zinc-100 outline-none focus:border-indigo-500 transition-colors" 
                  />
                  <p className="text-[10px] text-zinc-500">Note: Live mode pacing is driven by server response time.</p>
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-xs font-bold uppercase tracking-wider text-zinc-400">Theme</label>
                  <select 
                    value={theme} 
                    onChange={(e) => handleThemeChange(e.target.value as "dark" | "light")}
                    className="bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2.5 text-zinc-100 outline-none focus:border-indigo-500 appearance-none cursor-pointer"
                  >
                    <option value="dark">Dark Mode (Recommended)</option>
                    <option value="light">Light Mode (Beta)</option>
                  </select>
                </div>

                <button 
                  onClick={handleClearCache}
                  className="mt-2 w-full py-2.5 rounded-xl bg-red-900/20 text-red-400 border border-red-900/50 hover:bg-red-900/40 hover:text-red-300 font-medium transition-all"
                >
                  Clear Browser Cache
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Settings Cog Trigger */}
        <div className="absolute top-6 right-6 z-50">
          <button 
            onClick={() => setIsSettingsOpen((prev) => !prev)}
            className="p-2 rounded-xl border border-transparent hover:border-zinc-800 hover:bg-zinc-900/50 transition-all text-zinc-500 hover:text-zinc-200 flex gap-2 items-center"
          >
            <span className="text-[10px] font-mono tracking-widest hidden sm:block opacity-50">ESC</span>
            <FiSettings size={20} />
          </button>
        </div>

        {/* Hero: Dynamic Flex Centering */}
        <section className={`w-full max-w-2xl flex flex-col items-center px-4 transition-all duration-1000 ease-in-out
          ${currentAct === 0 ? "flex-1 justify-center pb-24" : "pt-12 pb-8"}`}>
          
          <h1 className={`text-4xl md:text-5xl font-semibold mb-6 tracking-tight transition-all duration-700
            ${currentAct === 0 ? "opacity-100 scale-100" : "opacity-0 scale-95 h-0 overflow-hidden"}`}>
            Out of the loop?
          </h1>

          {/* Quick-Start Pills */}
          <div className={`flex flex-wrap justify-center gap-3 mb-8 transition-all duration-700 ${currentAct === 0 ? "opacity-100" : "opacity-0 h-0 overflow-hidden mb-0"}`}>
            {TRENDING_TOPICS.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => triggerAnalysis(t)}
                disabled={isAnalyzing}
                className="group relative px-5 py-2 rounded-full border border-zinc-800 bg-gradient-to-b from-zinc-800/40 to-zinc-900/40 text-xs font-medium text-zinc-400 backdrop-blur-md transition-all duration-300 hover:text-white hover:border-indigo-500/50 hover:shadow-[0_0_20px_rgba(99,102,241,0.15)] hover:-translate-y-0.5 active:scale-95 disabled:opacity-50 overflow-hidden"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/0 via-indigo-500/10 to-indigo-500/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-full" />
                <span className="relative z-10">{t}</span>
              </button>
            ))}
          </div>

          <div className="w-full flex flex-col gap-2 relative z-10">
            <form className={`w-full flex gap-2 rounded-2xl shadow-2xl border px-3 py-2.5 backdrop-blur-md transition-all duration-300
              ${inputError ? "border-red-500 bg-red-950/20" : !liveSource ? "border-red-900/50 bg-red-950/10" : "border-zinc-800 bg-zinc-900/40"}`} 
              onSubmit={handleFormSubmit}>
              <div className={`flex items-center pl-2 transition-colors ${inputError ? "text-red-400" : "text-zinc-500"}`}>
                <FiSearch size={20} />
              </div>
              <input
                ref={searchInputRef}
                className={`flex-1 bg-transparent outline-none text-lg px-2 placeholder-zinc-600 transition-colors ${inputError ? "text-red-200" : "text-zinc-100"}`}
                placeholder="Ask away... (Press Enter)"
                value={topic}
                onChange={(e) => {
                  setTopic(e.target.value);
                  if (inputError) setInputError(""); 
                }}
                disabled={isAnalyzing}
              />
              <button
                type="submit"
                disabled={isAnalyzing || !topic.trim()}
                className={`flex items-center justify-center w-28 h-11 rounded-xl font-medium transition-all transform active:scale-95
                  ${inputError ? "bg-red-600 hover:bg-red-500 shadow-[0_0_15px_rgba(220,38,38,0.3)]" : !liveSource ? "bg-red-600 hover:bg-red-500 shadow-[0_0_15px_rgba(220,38,38,0.3)]" : "bg-indigo-600 hover:bg-indigo-500"} 
                  text-white disabled:opacity-50`}
              >
                {isAnalyzing ? (
                  <div className="flex gap-1.5 items-center justify-center">
                    <div className="w-1.5 h-1.5 bg-white rounded-full animate-bounce [animation-delay:-0.3s]" />
                    <div className="w-1.5 h-1.5 bg-white rounded-full animate-bounce [animation-delay:-0.15s]" />
                    <div className="w-1.5 h-1.5 bg-white rounded-full animate-bounce" />
                  </div>
                ) : (
                  "Debate"
                )}
              </button>
            </form>
            {inputError && (
              <span className="text-red-400 text-xs font-medium pl-4 animate-in fade-in slide-in-from-top-1">
                {inputError}
              </span>
            )}
          </div>

          {/* Toggles */}
          <div className="flex items-center gap-6 mt-6 justify-center">
            <div className="flex items-center gap-3">
              <span className="uppercase tracking-widest text-[10px] font-bold text-zinc-500">Source</span>
              <button
                type="button"
                className={`transition-all flex items-center gap-2 px-3 py-1.5 rounded-full border shadow-inner
                  ${liveSource ? "border-blue-500/20 bg-blue-900/10" : "border-red-500/50 bg-red-950/20"}`}
                onClick={() => setLiveSource((v) => !v)}
              >
                <span className={`w-2 h-2 rounded-full ${liveSource ? "bg-blue-400" : "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]"}`}></span>
                <span className={`text-xs font-semibold uppercase ${liveSource ? "text-blue-300" : "text-red-400"}`}>
                  {liveSource ? "News" : "Chaos"}
                </span>
              </button>
            </div>
            
            <div className="flex items-center gap-3">
              <span className="uppercase tracking-widest text-[10px] font-bold text-zinc-500">Pacing</span>
              <button
                type="button"
                className={`transition-all flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-900 border border-zinc-800 shadow-inner 
                  ${speedMode === "demo" ? "border-amber-500/30 bg-amber-900/10" : ""}`}
                onClick={() => setSpeedMode(p => p === "demo" ? "realtime" : "demo")}
              >
                <span className={`w-2 h-2 rounded-full ${speedMode === "demo" ? "bg-amber-400" : "bg-zinc-600"}`}></span>
                <span className={`text-xs font-semibold uppercase ${speedMode === "demo" ? "text-amber-300" : "text-zinc-500"}`}>
                  {speedMode === "demo" ? "Turbo" : "Normal"}
                </span>
              </button>
            </div>
          </div>
        </section>

        {/* Main Content Area */}
        <section className="w-full max-w-3xl flex flex-col gap-6 px-4 pb-24">
          <div className="w-full">
            <div className="flex flex-wrap items-center justify-center gap-3">
              {ACTS.map((act) => {
                const isActive = currentAct === act.id;
                const isDone = currentAct > act.id;
                return (
                  <div
                    key={act.id}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-[10px] font-bold uppercase tracking-widest transition-all duration-300
                      ${isActive
                        ? "bg-indigo-500/20 text-indigo-200 border-indigo-400 shadow-[0_0_16px_rgba(99,102,241,0.6)]"
                        : isDone
                        ? "bg-emerald-500/10 text-emerald-200 border-emerald-600/40"
                        : "bg-zinc-900/40 text-zinc-500 border-zinc-800"}`}
                  >
                    <span className={`w-2 h-2 rounded-full ${isActive ? "bg-indigo-400 animate-pulse" : isDone ? "bg-emerald-400" : "bg-zinc-600"}`} />
                    <span>{`Act ${act.id}: ${act.label}`}</span>
                    {isActive && (
                      <span className="text-[8px] px-2 py-0.5 rounded-full bg-indigo-400/20 text-indigo-200 border border-indigo-400/30">
                        Live
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {currentAct >= 1 && (
            <div className="relative animate-in fade-in slide-in-from-bottom-4 duration-700 w-full bg-zinc-900/30 border border-zinc-800/50 rounded-2xl p-6 flex flex-col gap-3 overflow-hidden">
              <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-blue-500/60 via-indigo-500/60 to-cyan-400/60" />
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] font-bold uppercase text-blue-400 tracking-widest">Briefing & Spin-Up</span>
                <span className={`text-[9px] font-semibold uppercase tracking-widest px-2 py-1 rounded-full border ${currentAct === 1 ? "border-blue-500/40 text-blue-300 bg-blue-900/20" : "border-zinc-800 text-zinc-500 bg-zinc-900/40"}`}>
                  Act 1
                </span>
              </div>
              <div className="text-[13px] text-zinc-200 leading-6 min-h-[3rem] whitespace-pre-wrap">
                <Typewriter text={moderatorBrief} speedMs={BASE_TYPE_SPEED / speedMultiplier} />
              </div>
              
              <AgentTelemetry isActive={isAnalyzing} speedMultiplier={speedMultiplier} hasError={backendError} />
            </div>
          )}

          {currentAct >= 2 && (
            <div className="animate-in fade-in slide-in-from-bottom-8 duration-700 w-full">
              <div className={`w-full rounded-2xl bg-zinc-950/50 border border-zinc-800 shadow-xl relative flex flex-col overflow-hidden transition-all duration-500 ease-in-out ${showChat ? "max-h-[60vh] h-[32rem]" : "h-14"}`}>
                
                <div className="flex items-center px-6 h-14 border-b border-zinc-900 bg-zinc-950/80 z-10 shrink-0 cursor-pointer" onClick={() => setShowChat((v) => !v)}>
                  <span className="font-mono text-[10px] font-bold uppercase text-red-400 tracking-widest">Debate</span>
                  <div className="ml-auto flex items-center gap-3">
                    <span className="text-[10px] font-mono tracking-widest hidden sm:block text-zinc-500">Press F</span>
                    <button
                      className={`px-3 py-1 text-xs rounded-lg transition border border-zinc-800 font-medium ${showChat ? "bg-zinc-800 text-zinc-300 hover:bg-zinc-700" : "bg-zinc-900 text-zinc-500 hover:bg-zinc-800"}`}
                    >
                      {showChat ? "Collapse" : "Expand"}
                    </button>
                  </div>
                </div>

                <div className={`transition-opacity duration-500 flex-1 overflow-hidden ${showChat ? "opacity-100" : "opacity-0"}`}>
                  <div className="h-full overflow-y-auto px-4 pb-5 pt-6 font-mono scrollbar-hide">
                    <div className="flex flex-col justify-end min-h-full">
                      {messages.map((msg, idx) => {
                        const agent = agentMetadata[msg.agentIdx] || unknownAgent;
                        const isEven = idx % 2 === 0;
                        const isExpanded = !!expandedMessages[idx];
                        const shouldClamp = msg.content.length > MESSAGE_PREVIEW_CHARS;
                        const shownText = isExpanded || !shouldClamp
                          ? msg.content
                          : `${msg.content.slice(0, MESSAGE_PREVIEW_CHARS).trimEnd()}…`;
                        return (
                          <div className={`flex items-start gap-3 mb-4 ${isEven ? "" : "flex-row-reverse"}`} key={idx}>
                            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center border-2 ${agent.color} ${agent.bg}`}>
                              {renderAvatar(agent)}
                            </div>
                            <div className={`min-w-0 max-w-xl rounded-2xl px-3 py-2 ${agent.bg} border ${agent.color} ${isEven ? 'rounded-tl-sm' : 'rounded-tr-sm'}`}>
                              <div className={`flex items-center gap-2 mb-1 ${isEven ? '' : 'flex-row-reverse'}`}>
                                <span className={`text-[11px] font-semibold ${agent.text}`}>{agent.name}</span>
                                <span className="text-[10px] text-zinc-500">{msg.timestamp}</span>
                              </div>
                              <div className="text-[12px] leading-relaxed text-zinc-200">
                                {shownText}
                              </div>
                              {shouldClamp && (
                                <button
                                  onClick={() => setExpandedMessages((prev) => ({ ...prev, [idx]: !isExpanded }))}
                                  className="mt-1 text-[10px] font-semibold text-indigo-300 hover:text-indigo-200"
                                >
                                  {isExpanded ? "See less" : "See more..."}
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                      {activeTypist !== null && (
                        <div className={`flex items-end gap-2 mb-4 ${messages.length % 2 === 0 ? "" : "flex-row-reverse"}`}>
                          <div className="w-8 h-8 rounded-full border border-zinc-700 bg-zinc-900 animate-pulse" />
                          <div className="bg-zinc-800/50 px-4 py-3 rounded-2xl flex gap-1 items-center">
                            <div className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
                            <div className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
                            <div className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce" />
                          </div>
                        </div>
                      )}
                      <div ref={messagesEndRef} className="h-4" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {currentAct >= 3 && (
            <div className="relative animate-in fade-in zoom-in-95 duration-700 w-full bg-zinc-900/40 border border-zinc-800 rounded-2xl p-8 flex flex-col gap-4 overflow-hidden">
              <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-emerald-500/60 via-lime-400/60 to-teal-400/60" />
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] font-bold uppercase text-green-400 tracking-widest">Synthesis</span>
                <span className={`text-[9px] font-semibold uppercase tracking-widest px-2 py-1 rounded-full border ${currentAct === 3 ? "border-emerald-500/40 text-emerald-300 bg-emerald-900/20" : "border-zinc-800 text-zinc-500 bg-zinc-900/40"}`}>
                  Act 3
                </span>
              </div>
              <div className="text-[13px] text-zinc-200 leading-6 whitespace-pre-wrap">
                <Typewriter text={moderatorSynthesis} speedMs={BASE_TYPE_SPEED / speedMultiplier} />
              </div>
              {citedSources.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {citedSources.map((src, i) => (
                    <a
                      key={i}
                      href={src.url}
                      target="_blank"
                      className="group w-full sm:w-[calc(50%-0.25rem)] text-[11px] font-mono text-zinc-300 transition-all bg-zinc-950/60 px-3 py-2 rounded-lg border border-zinc-800 hover:border-indigo-500/60 hover:bg-indigo-950/30"
                    >
                      <div className="line-clamp-2">{src.title}</div>
                      <div className="mt-1 text-[10px] text-zinc-500 flex items-center justify-between">
                        <span>See full article --&gt;</span>
                        <span className="opacity-0 group-hover:opacity-100 transition-opacity text-indigo-300">
                          Visit site
                        </span>
                      </div>
                    </a>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
