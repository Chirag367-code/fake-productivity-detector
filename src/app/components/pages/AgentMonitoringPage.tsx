import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import {
    Monitor,
    Shield,
    Info,
    TrendingUp,
    AlertTriangle,
    Trophy,
    Clock,
    RefreshCw,
    Radio,
    Keyboard,
    MousePointer,
    LayoutGrid,
    Activity,
    Cpu,
} from "lucide-react";
import {
    LineChart,
    Line,
    PieChart,
    Pie,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    Cell,
} from "recharts";
import { API_ENDPOINTS, authFetch } from "../../config/api";

interface AgentRecord {
    id?: string;
    user_id: string;
    date: string;
    authenticity_score: number;
    avg_typing_speed?: number;
    avg_mouse_velocity?: number;
    top_window_categories?: Array<{ category: string; seconds: number }>;
    created_at?: string;
}

interface AgentStatus {
    is_running: boolean;
    agent_version: string;
    session_start: number;
    session_minutes: number;
    last_scan: number;
    seconds_since_scan: number;
    total_events: number;
    keystrokes: number;
    mouse_moves: number;
    window_switches: number;
    current_window: string;
    last_activity: number;
    events_per_minute: number;
    keystrokes_per_minute?: number;
    mouse_moves_per_minute?: number;
}

interface AgentMonitoringPageProps {
    userId: string;
}

const PIE_COLORS = [
    "#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444",
    "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#6366f1",
];

// How often the live view re-scans the agent (milliseconds)
const LIVE_REFRESH_MS = 5000;

export function AgentMonitoringPage({ userId }: AgentMonitoringPageProps) {
    const [records, setRecords] = useState<AgentRecord[]>([]);
    const [status, setStatus] = useState<AgentStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [seeding, setSeeding] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [seedSuccess, setSeedSuccess] = useState<string | null>(null);
    const [live, setLive] = useState(true);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

    // Guards so background polling never stacks up or re-seeds repeatedly
    const inFlightRef = useRef(false);
    const hasSeededRef = useRef(false);

    /**
     * Fetch the freshest agent data.
     * Hits /agent/scan first so the backend re-analyzes today's behavioral
     * events and recomputes the score on EVERY refresh. Also fetches live
     * agent status/telemetry.
     */
    const fetchAgentData = useCallback(
        async ({ silent = false }: { silent?: boolean } = {}) => {
            if (inFlightRef.current) return;
            inFlightRef.current = true;

            try {
                if (silent) setRefreshing(true);
                else setLoading(true);
                setError(null);

                // Cache-buster so browsers/proxies never serve a stale snapshot
                const bust = `_t=${Date.now()}`;
                const scanUrl = `${API_ENDPOINTS.agentScan(userId)}?${bust}`;
                const historyUrl = `${API_ENDPOINTS.agentHistory(userId)}?${bust}`;
                const statusUrl = `${API_ENDPOINTS.agentStatus(userId)}?${bust}`;

                // Fetch scan + status in parallel
                const [scanRes, statusRes] = await Promise.all([
                    authFetch(scanUrl, { cache: "no-store" }),
                    authFetch(statusUrl, { cache: "no-store" }).catch(() => null),
                ]);

                let response = scanRes;
                if (!response.ok) {
                    // Scan requires auth / may be unavailable — fall back to history
                    response = await authFetch(historyUrl, { cache: "no-store" });
                }

                if (response.ok) {
                    const data = await response.json();
                    setRecords(data.history || []);
                    setLastUpdated(new Date());
                } else if (!silent) {
                    setRecords([]);
                }

                // Parse agent status if available
                if (statusRes && statusRes.ok) {
                    const statusData = await statusRes.json();
                    if (statusData.status) {
                        setStatus(statusData.status);
                    }
                }
            } catch (err: any) {
                console.error("Error fetching agent data:", err);
                // Don't blow away a good view because one poll failed
                if (silent) return;

                // Distinguish network errors from other issues
                const isNetworkError =
                    err instanceof TypeError &&
                    (err.message?.includes("fetch") || err.message?.includes("network"));
                if (isNetworkError) {
                    setError(
                        "Could not connect to the backend. Make sure the backend is running at " +
                        (import.meta.env.VITE_API_URL || "the configured API URL") +
                        "."
                    );
                } else {
                    setError(err?.message || "Could not load agent data. Make sure the backend is running.");
                }
                setRecords([]);
            } finally {
                inFlightRef.current = false;
                setRefreshing(false);
                setLoading(false);
            }
        },
        [userId]
    );

    // Initial load (runs on every page mount / browser refresh)
    useEffect(() => {
        hasSeededRef.current = false;
        fetchAgentData();
    }, [userId, fetchAgentData]);

    // Live polling — keeps the view current without a manual refresh
    useEffect(() => {
        if (!live) return;
        const id = setInterval(() => {
            if (document.visibilityState === "visible") {
                fetchAgentData({ silent: true });
            }
        }, LIVE_REFRESH_MS);
        return () => clearInterval(id);
    }, [live, fetchAgentData]);

    // Re-scan the moment the user comes back to the tab/window
    useEffect(() => {
        const onFocus = () => {
            if (document.visibilityState === "visible") {
                fetchAgentData({ silent: true });
            }
        };
        window.addEventListener("focus", onFocus);
        document.addEventListener("visibilitychange", onFocus);
        return () => {
            window.removeEventListener("focus", onFocus);
            document.removeEventListener("visibilitychange", onFocus);
        };
    }, [fetchAgentData]);

    // Auto-seed demo data once when no records exist and no error
    useEffect(() => {
        if (!loading && records.length === 0 && !error && !seeding && !hasSeededRef.current) {
            hasSeededRef.current = true;
            handleSeedData();
        }
    }, [loading, records.length, error, seeding]);

    const handleSeedData = async () => {
        try {
            setSeeding(true);
            setError(null);
            const response = await authFetch(API_ENDPOINTS.agentSeed(userId), {
                method: "POST",
            });

            if (response.ok) {
                const data = await response.json();
                await fetchAgentData({ silent: true });
                // Show a brief success message
                setSeedSuccess(data.message || "Demo data loaded successfully!");
                setTimeout(() => setSeedSuccess(null), 3000);
            } else {
                const data = await response.json().catch(() => ({}));
                setError(data.detail || "Failed to seed demo data");
            }
        } catch (err: any) {
            console.error("Error seeding data:", err);
            // Distinguish network errors from other issues
            const isNetworkError =
                err instanceof TypeError &&
                (err.message?.includes("fetch") || err.message?.includes("network"));
            if (isNetworkError) {
                setError(
                    "Could not connect to the backend. Make sure the backend is running at " +
                    (import.meta.env.VITE_API_URL || "the configured API URL") +
                    "."
                );
            } else {
                setError(err?.message || "Could not seed data. Make sure the backend is running.");
            }
        } finally {
            setSeeding(false);
        }
    };

    // Latest record
    const latestRecord = records.length > 0 ? records[0] : null;

    // Trend data for line chart
    const trendData = [...records].reverse().map((r) => ({
        date: new Date(r.date).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
        }),
        score: r.authenticity_score,
    }));

    // Window category data for pie chart
    const windowCategoryData =
        latestRecord?.top_window_categories?.map((cat) => ({
            name: cat.category,
            value: Math.round(cat.seconds / 60), // convert to minutes
        })) || [];

    // Stats cards
    const avgScore =
        records.length > 0
            ? Math.round(
                records.reduce((sum, r) => sum + r.authenticity_score, 0) /
                records.length
            )
            : 0;

    const highCount = records.filter((r) => r.authenticity_score >= 80).length;
    const fakeCount = records.filter((r) => r.authenticity_score < 50).length;

    // Format session duration
    const formatSession = (minutes: number) => {
        if (minutes < 60) return `${minutes}m`;
        const h = Math.floor(minutes / 60);
        const m = minutes % 60;
        return `${h}h ${m}m`;
    };

    // Format last activity time
    const formatLastActivity = (ts: number) => {
        if (!ts) return "—";
        const diff = Math.floor((Date.now() / 1000) - ts);
        if (diff < 5) return "just now";
        if (diff < 60) return `${diff}s ago`;
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        return `${Math.floor(diff / 3600)}h ago`;
    };

    const statsCards = [
        {
            title: "Days Tracked",
            value: records.length,
            icon: Clock,
            gradient: "from-blue-400 to-blue-600",
            bg: "from-blue-50 to-blue-100",
        },
        {
            title: "Avg Authenticity",
            value: avgScore,
            icon: TrendingUp,
            gradient: "from-purple-400 to-purple-600",
            bg: "from-purple-50 to-purple-100",
        },
        {
            title: "Highly Authentic",
            value: highCount,
            icon: Trophy,
            gradient: "from-green-400 to-green-600",
            bg: "from-green-50 to-green-100",
        },
        {
            title: "Low Authenticity",
            value: fakeCount,
            icon: AlertTriangle,
            gradient: "from-red-400 to-red-600",
            bg: "from-red-50 to-red-100",
        },
    ];

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="text-center">
                    <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-gray-600">Loading agent data...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-6"
            >
                <div className="flex items-center justify-between flex-wrap gap-4">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl shadow-lg">
                            <Monitor className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h1 className="text-3xl mb-1">Agent Monitor</h1>
                            <p className="text-gray-600 text-sm">
                                Behavioral authenticity tracking from your local agent
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3 flex-wrap">
                        {/* Live status */}
                        <div className="flex items-center gap-2 text-xs text-gray-600">
                            <span className="relative flex h-2.5 w-2.5">
                                {live && status?.is_running && (
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                                )}
                                <span
                                    className={`relative inline-flex rounded-full h-2.5 w-2.5 ${live && status?.is_running ? "bg-green-500" : "bg-gray-400"
                                        }`}
                                ></span>
                            </span>
                            <span>
                                {refreshing
                                    ? "Scanning…"
                                    : lastUpdated
                                        ? `Updated ${lastUpdated.toLocaleTimeString()}`
                                        : "Not updated yet"}
                            </span>
                        </div>

                        {/* Live toggle */}
                        <button
                            onClick={() => setLive((v) => !v)}
                            title={
                                live
                                    ? `Live view on — re-scanning every ${LIVE_REFRESH_MS / 1000}s`
                                    : "Live view paused"
                            }
                            className={`px-3 py-2 rounded-xl text-sm border transition-all flex items-center gap-2 ${live
                                ? "bg-green-50 text-green-700 border-green-200 hover:bg-green-100"
                                : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
                                }`}
                        >
                            <Radio className="w-4 h-4" />
                            {live ? "Live" : "Paused"}
                        </button>

                        <button
                            onClick={() => fetchAgentData({ silent: true })}
                            disabled={refreshing}
                            className="px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-xl hover:shadow-lg transition-all text-sm disabled:opacity-60 flex items-center gap-2"
                        >
                            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
                            {refreshing ? "Refreshing…" : "Refresh Data"}
                        </button>
                    </div>
                </div>
            </motion.div>

            {/* Live Agent Telemetry */}
            {status && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="backdrop-blur-lg bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700 rounded-2xl shadow-xl p-6"
                >
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-green-500/20 rounded-lg">
                                <Cpu className="w-5 h-5 text-green-400" />
                            </div>
                            <div>
                                <h3 className="text-white font-semibold">Agent Live Telemetry</h3>
                                <p className="text-slate-400 text-xs">
                                    v{status.agent_version} • Session {formatSession(status.session_minutes)}
                                </p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                            </span>
                            <span className="text-green-400 text-xs font-medium">RUNNING</span>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {/* Keystrokes */}
                        <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                            <div className="flex items-center gap-2 mb-2">
                                <Keyboard className="w-4 h-4 text-blue-400" />
                                <span className="text-slate-400 text-xs">Keystrokes</span>
                            </div>
                            <div className="text-2xl text-white font-bold">
                                {status.keystrokes.toLocaleString()}
                            </div>
                            <div className="text-slate-500 text-xs mt-1">
                                {(status.keystrokes_per_minute ?? status.events_per_minute).toFixed(1)}/min
                            </div>
                        </div>

                        {/* Mouse Moves */}
                        <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                            <div className="flex items-center gap-2 mb-2">
                                <MousePointer className="w-4 h-4 text-purple-400" />
                                <span className="text-slate-400 text-xs">Mouse Moves</span>
                            </div>
                            <div className="text-2xl text-white font-bold">
                                {status.mouse_moves.toLocaleString()}
                            </div>
                            <div className="text-slate-500 text-xs mt-1">
                                {(status.mouse_moves_per_minute ?? status.events_per_minute).toFixed(1)}/min
                            </div>
                        </div>

                        {/* Window Switches */}
                        <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                            <div className="flex items-center gap-2 mb-2">
                                <LayoutGrid className="w-4 h-4 text-green-400" />
                                <span className="text-slate-400 text-xs">Window Switches</span>
                            </div>
                            <div className="text-2xl text-white font-bold">
                                {status.window_switches.toLocaleString()}
                            </div>
                            <div className="text-slate-500 text-xs mt-1">
                                {status.total_events.toLocaleString()} total events
                            </div>
                        </div>

                        {/* Activity */}
                        <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                            <div className="flex items-center gap-2 mb-2">
                                <Activity className="w-4 h-4 text-amber-400" />
                                <span className="text-slate-400 text-xs">Last Activity</span>
                            </div>
                            <div className="text-2xl text-white font-bold">
                                {formatLastActivity(status.last_activity)}
                            </div>
                            <div className="text-slate-500 text-xs mt-1">
                                {status.seconds_since_scan}s since scan
                            </div>
                        </div>
                    </div>

                    {/* Current window */}
                    <div className="mt-4 bg-white/5 rounded-xl p-3 border border-white/10 flex items-center gap-3">
                        <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">Current Window:</span>
                        <span className="text-white text-sm font-mono truncate">{status.current_window}</span>
                    </div>
                </motion.div>
            )}

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {statsCards.map((card, index) => {
                    const Icon = card.icon;
                    return (
                        <motion.div
                            key={card.title}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.1 }}
                            className={`backdrop-blur-lg bg-gradient-to-br ${card.bg} border border-white/50 rounded-2xl shadow-xl p-6 hover:shadow-2xl transition-all duration-300`}
                        >
                            <div className="flex items-start justify-between mb-4">
                                <div className={`p-3 bg-gradient-to-br ${card.gradient} rounded-xl shadow-lg`}>
                                    <Icon className="w-6 h-6 text-white" />
                                </div>
                            </div>
                            <div className="text-3xl mb-1">{card.value}</div>
                            <div className="text-sm text-gray-600">{card.title}</div>
                        </motion.div>
                    );
                })}
            </div>

            {/* Today's Score + Window Categories */}
            {latestRecord && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Today's Score */}
                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-6"
                    >
                        <h3 className="text-xl mb-4">Today's Authenticity Score</h3>
                        <div className="flex items-center gap-6">
                            <div className="relative w-32 h-32">
                                <svg className="w-full h-full" viewBox="0 0 100 100">
                                    <circle
                                        cx="50"
                                        cy="50"
                                        r="45"
                                        fill="none"
                                        stroke="#e5e7eb"
                                        strokeWidth="8"
                                    />
                                    <motion.circle
                                        cx="50"
                                        cy="50"
                                        r="45"
                                        fill="none"
                                        stroke={
                                            latestRecord.authenticity_score >= 80
                                                ? "#10b981"
                                                : latestRecord.authenticity_score >= 50
                                                    ? "#f59e0b"
                                                    : "#ef4444"
                                        }
                                        strokeWidth="8"
                                        strokeLinecap="round"
                                        strokeDasharray={`${(latestRecord.authenticity_score / 100) * 283} 283`}
                                        initial={{ strokeDasharray: "0 283" }}
                                        animate={{
                                            strokeDasharray: `${(latestRecord.authenticity_score / 100) * 283} 283`,
                                        }}
                                        transition={{ duration: 1.5, ease: "easeOut" }}
                                        transform="rotate(-90 50 50)"
                                    />
                                    <text
                                        x="50"
                                        y="50"
                                        textAnchor="middle"
                                        dominantBaseline="central"
                                        className="text-2xl font-bold"
                                        fill="currentColor"
                                    >
                                        {Math.round(latestRecord.authenticity_score)}
                                    </text>
                                </svg>
                            </div>
                            <div className="space-y-2">
                                <div className="text-sm text-gray-600">
                                    <span className="font-semibold">Date:</span>{" "}
                                    {new Date(latestRecord.date).toLocaleDateString("en-US", {
                                        weekday: "long",
                                        year: "numeric",
                                        month: "long",
                                        day: "numeric",
                                    })}
                                </div>
                                <div className="text-sm text-gray-600">
                                    <span className="font-semibold">Typing Speed:</span>{" "}
                                    {latestRecord.avg_typing_speed
                                        ? `${latestRecord.avg_typing_speed.toFixed(0)} ms`
                                        : "N/A"}
                                </div>
                                <div className="text-sm text-gray-600">
                                    <span className="font-semibold">Mouse Velocity:</span>{" "}
                                    {latestRecord.avg_mouse_velocity
                                        ? `${latestRecord.avg_mouse_velocity.toFixed(0)} px/s`
                                        : "N/A"}
                                </div>
                            </div>
                        </div>
                    </motion.div>

                    {/* Window Category Pie Chart */}
                    <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-6"
                    >
                        <h3 className="text-xl mb-4">Window Categories (Today)</h3>
                        {windowCategoryData.length > 0 ? (
                            <ResponsiveContainer width="100%" height={300}>
                                <PieChart>
                                    <Pie
                                        data={windowCategoryData}
                                        cx="50%"
                                        cy="50%"
                                        labelLine={false}
                                        label={({ name, percent }) =>
                                            `${name}: ${(percent * 100).toFixed(0)}%`
                                        }
                                        outerRadius={100}
                                        dataKey="value"
                                    >
                                        {windowCategoryData.map((_entry, index) => (
                                            <Cell
                                                key={`cell-${index}`}
                                                fill={PIE_COLORS[index % PIE_COLORS.length]}
                                            />
                                        ))}
                                    </Pie>
                                    <Tooltip />
                                </PieChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="h-[300px] flex items-center justify-center text-gray-500">
                                No window data available yet
                            </div>
                        )}
                    </motion.div>
                </div>
            )}

            {/* Trend Line Chart */}
            {trendData.length > 1 && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-6"
                >
                    <h3 className="text-xl mb-4">Authenticity Score Trend</h3>
                    <ResponsiveContainer width="100%" height={300}>
                        <LineChart data={trendData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                            <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: "rgba(255, 255, 255, 0.95)",
                                    border: "1px solid #e5e7eb",
                                    borderRadius: "8px",
                                    boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
                                }}
                            />
                            <Legend />
                            <Line
                                type="monotone"
                                dataKey="score"
                                stroke="#8b5cf6"
                                strokeWidth={3}
                                dot={{ fill: "#8b5cf6", r: 5 }}
                                activeDot={{ r: 7 }}
                                name="Authenticity Score"
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </motion.div>
            )}

            {/* Empty State */}
            {records.length === 0 && !error && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-12 text-center"
                >
                    <Monitor className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-xl mb-2">No Agent Data Yet</h3>
                    <p className="text-gray-600 max-w-md mx-auto mb-6">
                        Install and run the local behavioral agent on your computer to start
                        tracking behavioral authenticity. The agent captures only passive
                        metadata — never your keystroke content, screen, or personal data.
                    </p>
                    <div className="flex justify-center gap-4">
                        <a
                            href="/AGENT_SETUP.md"
                            className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-xl hover:shadow-lg transition-all text-sm"
                        >
                            View Setup Guide
                        </a>
                        <button
                            onClick={handleSeedData}
                            disabled={seeding}
                            className="px-6 py-3 bg-white text-purple-600 border border-purple-200 rounded-xl hover:bg-purple-50 hover:shadow-lg transition-all text-sm disabled:opacity-50 flex items-center gap-2"
                        >
                            {seeding ? (
                                <>
                                    <div className="w-4 h-4 border-2 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
                                    Loading...
                                </>
                            ) : (
                                "Load Demo Data"
                            )}
                        </button>
                    </div>
                </motion.div>
            )}

            {/* Success State */}
            {seedSuccess && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="backdrop-blur-lg bg-green-50/70 border border-green-200 rounded-2xl shadow-xl p-6"
                >
                    <div className="flex items-center gap-3 text-green-600">
                        <Trophy className="w-6 h-6" />
                        <p>{seedSuccess}</p>
                    </div>
                </motion.div>
            )}

            {/* Error State */}
            {error && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="backdrop-blur-lg bg-red-50/70 border border-red-200 rounded-2xl shadow-xl p-6"
                >
                    <div className="flex items-center gap-3 text-red-600">
                        <AlertTriangle className="w-6 h-6" />
                        <p>{error}</p>
                    </div>
                </motion.div>
            )}

            {/* Transparency Notice */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-6"
            >
                <div className="flex items-center gap-3 mb-4">
                    <Shield className="w-6 h-6 text-green-500" />
                    <h3 className="text-xl">Privacy & Transparency</h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <h4 className="font-semibold text-green-600 mb-2">
                            ✓ What the Agent Captures
                        </h4>
                        <ul className="space-y-1 text-sm text-gray-600">
                            <li>• Keystroke timing intervals (never which keys)</li>
                            <li>• Mouse movement vectors (never click targets)</li>
                            <li>• Active window titles only (never content)</li>
                        </ul>
                    </div>
                    <div>
                        <h4 className="font-semibold text-red-600 mb-2">
                            ✗ What the Agent NEVER Captures
                        </h4>
                        <ul className="space-y-1 text-sm text-gray-600">
                            <li>• Screen captures or recordings</li>
                            <li>• Webcam or microphone access</li>
                            <li>• Actual keystrokes or typed content</li>
                            <li>• Email, file, or document content</li>
                            <li>• Passwords or personal information</li>
                        </ul>
                    </div>
                </div>
                <div className="mt-4 p-4 bg-blue-50 rounded-xl">
                    <div className="flex items-start gap-3">
                        <Info className="w-5 h-5 text-blue-500 mt-0.5" />
                        <p className="text-sm text-gray-600">
                            Raw behavioral events are stored ONLY on your local machine in
                            <code className="bg-gray-200 px-1 rounded"> ~/.fpd-agent/agent_events.db</code>.
                            Only the daily aggregated authenticity score and summary statistics
                            are synced to the backend — never raw event data. You can opt out
                            at any time by running{" "}
                            <code className="bg-gray-200 px-1 rounded">
                                python -m app.agent.run_agent --opt-out
                            </code>
                            .
                        </p>
                    </div>
                </div>
            </motion.div>
        </div>
    );
}