import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { History, TrendingUp, TrendingDown, Trash2, Calendar } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { API_ENDPOINTS, authFetch } from "../config/api";

interface HistoryEntry {
  userId: string;
  userName: string;
  score: number;
  category: string;
  timestamp: string;
  breakdown: {
    productive: number;
    idle: number;
    social: number;
    breaks: number;
  };
}

interface ProductivityHistoryProps {
  userId: string;
}

export function ProductivityHistory({ userId }: ProductivityHistoryProps) {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const response = await authFetch(API_ENDPOINTS.history(userId));

      if (!response.ok) {
        throw new Error("Failed to fetch history");
      }

      const data = await response.json();
      // Map backend response to frontend format
      const mappedHistory = (data.history || []).map((item: any) => ({
        userId: item.user_id,
        userName: item.user_name,
        score: item.productivity_score || item.score,
        category: item.category_rule_based || item.category,
        timestamp: item.created_at || item.timestamp,
        breakdown: item.breakdown || {
          productive: item.task_hours || 0,
          idle: item.idle_hours || 0,
          social: item.social_media_usage || 0,
          breaks: item.break_frequency || 0,
        },
      }));
      setHistory(mappedHistory);
    } catch (error) {
      console.error("Error fetching productivity history:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [userId]);

  const handleDeleteHistory = async () => {
    if (!confirm("Are you sure you want to delete all your productivity history?")) {
      return;
    }

    try {
      const response = await authFetch(API_ENDPOINTS.history(userId), {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error("Failed to delete history");
      }

      setHistory([]);
      alert("History deleted successfully!");
    } catch (error) {
      console.error("Error deleting history:", error);
      alert("Failed to delete history. Please try again.");
    }
  };

  // Prepare chart data
  const chartData = history.slice(0, 10).reverse().map((entry) => ({
    date: new Date(entry.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    score: entry.score,
    userName: entry.userName,
  }));

  // Calculate statistics
  const validScores = history
    .map((entry) => entry.score)
    .filter((score) => typeof score === "number" && !isNaN(score));

  const averageScore =
    validScores.length > 0
      ? Math.round(validScores.reduce((sum, score) => sum + score, 0) / validScores.length)
      : 0;

  const trend =
    history.length >= 2 &&
    typeof history[0].score === "number" &&
    typeof history[1].score === "number"
      ? history[0].score - history[1].score
      : 0;

  return (
    <div className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-8">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-2xl flex items-center gap-2">
          <History className="w-6 h-6 text-blue-600" />
          Productivity History
        </h3>
      </div>

      {loading ? (
        <div className="text-center py-8">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-gray-600 mt-4">Loading history...</p>
        </div>
      ) : history.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <Calendar className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>No productivity history yet.</p>
          <p className="text-sm mt-2">Analyze your activity to start tracking!</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Statistics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-xl">
              <div className="text-sm text-gray-600 mb-1">Total Analyses</div>
              <div className="text-2xl">{history.length}</div>
            </div>
            <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-xl">
              <div className="text-sm text-gray-600 mb-1">Average Score</div>
              <div className="text-2xl">{averageScore}</div>
            </div>
            <div className="bg-gradient-to-br from-pink-50 to-pink-100 p-4 rounded-xl">
              <div className="text-sm text-gray-600 mb-1 flex items-center gap-1">
                Recent Trend
                {trend > 0 ? (
                  <TrendingUp className="w-4 h-4 text-green-600" />
                ) : trend < 0 ? (
                  <TrendingDown className="w-4 h-4 text-red-600" />
                ) : null}
              </div>
              <div
                className={`text-2xl ${
                  trend > 0 ? "text-green-600" : trend < 0 ? "text-red-600" : ""
                }`}
              >
                {trend > 0 ? "+" : ""}{trend.toFixed(0)}
              </div>
            </div>
          </div>

          {/* Trend Chart */}
          {chartData.length > 1 && (
            <div className="bg-white/50 rounded-xl p-4">
              <h4 className="text-sm mb-4 text-gray-700">Score Trend</h4>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const { score, userName } = payload[0].payload;
                        return (
                          <div className="p-2 bg-white rounded shadow text-xs">
                            <div><strong>User:</strong> {userName}</div>
                            <div><strong>Score:</strong> {score}</div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="#3b82f6"
                    strokeWidth={3}
                    dot={{ fill: "#3b82f6", r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Recent Entries */}
          <div>
            <h4 className="text-sm mb-3 text-gray-700">Recent Analyses</h4>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {history.slice(0, 5).map((entry, index) => (
                <motion.div
                  key={entry.timestamp}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="bg-white/50 p-4 rounded-xl flex items-center justify-between"
                >
                  <div>
                    <div className="text-sm text-gray-600">
                      {new Date(entry.timestamp).toLocaleString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </div>
                    <div className="mt-1">
                      <span
                        className={`text-sm px-2 py-1 rounded-lg ${
                          entry.category === "Highly Productive"
                            ? "bg-green-100 text-green-700"
                            : entry.category === "Moderately Productive"
                            ? "bg-yellow-100 text-yellow-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {entry.category}
                      </span>
                      <span className="ml-2 text-xs text-gray-500">{entry.userName}</span>
                    </div>
                  </div>
                  <div className="text-2xl">{Math.round(entry.score)}</div>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Delete Button */}
          <button
            onClick={handleDeleteHistory}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-500 hover:bg-red-600 text-white rounded-xl transition-all duration-300"
          >
            <Trash2 className="w-4 h-4" />
            <span>Delete All History</span>
          </button>
        </div>
      )}
    </div>
  );
}