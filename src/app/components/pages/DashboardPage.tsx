import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { Users, TrendingUp, AlertTriangle, Trophy, Calendar } from "lucide-react";
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { API_ENDPOINTS, authFetch } from "../../config/api";

interface DashboardStats {
  totalAnalyses: number;
  averageScore: number;
  fakeProductivityCount: number;
  highlyProductiveCount: number;
}

interface DashboardPageProps {
  userId: string;
}

export function DashboardPage({ userId }: DashboardPageProps) {
  const [stats, setStats] = useState<DashboardStats>({
    totalAnalyses: 0,
    averageScore: 0,
    fakeProductivityCount: 0,
    highlyProductiveCount: 0,
  });
  const [loading, setLoading] = useState(true);
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    fetchDashboardData();
  }, [userId]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const response = await authFetch(API_ENDPOINTS.history(userId));

      if (response.ok) {
        const data = await response.json();
        const analyses = data.history || [];
        setHistory(analyses);

        // Calculate stats
        const total = analyses.length;
        const avgScore = total > 0
          ? Math.round(analyses.reduce((sum: number, a: any) => sum + (a.productivity_score || a.score || 0), 0) / total)
          : 0;
        const fakeCount = analyses.filter((a: any) => (a.category_rule_based || a.category) === "Fake Productivity").length;
        const highCount = analyses.filter((a: any) => (a.category_rule_based || a.category) === "Highly Productive").length;

        setStats({
          totalAnalyses: total,
          averageScore: avgScore,
          fakeProductivityCount: fakeCount,
          highlyProductiveCount: highCount,
        });
      }
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
    } finally {
      setLoading(false);
    }
  };

  const getCurrentDate = () => {
    const date = new Date();
    return date.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  // Overview cards data
  const overviewCards = [
    {
      title: "Total Analyses",
      value: stats.totalAnalyses,
      icon: Users,
      gradient: "from-blue-400 to-blue-600",
      bg: "from-blue-50 to-blue-100",
    },
    {
      title: "Average Score",
      value: stats.averageScore,
      icon: TrendingUp,
      gradient: "from-purple-400 to-purple-600",
      bg: "from-purple-50 to-purple-100",
    },
    {
      title: "Fake Productivity",
      value: stats.fakeProductivityCount,
      icon: AlertTriangle,
      gradient: "from-red-400 to-red-600",
      bg: "from-red-50 to-red-100",
    },
    {
      title: "Highly Productive",
      value: stats.highlyProductiveCount,
      icon: Trophy,
      gradient: "from-green-400 to-green-600",
      bg: "from-green-50 to-green-100",
    },
  ];

  // Prepare chart data
  const categoryData = [
    {
      name: "Highly Productive",
      value: stats.highlyProductiveCount,
      fill: "#10b981",
    },
    {
      name: "Moderately Productive",
      value: stats.totalAnalyses - stats.highlyProductiveCount - stats.fakeProductivityCount,
      fill: "#f59e0b",
    },
    {
      name: "Fake Productivity",
      value: stats.fakeProductivityCount,
      fill: "#ef4444",
    },
  ];

  const activityData = history.slice(0, 5).map((entry) => ({
    name: new Date(entry.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    Productive: entry.task_hours || 0,
    Idle: entry.idle_hours || 0,
    Social: entry.social_media_usage || 0,
  }));

  const trendData = history.slice(0, 10).reverse().map((entry) => ({
    date: new Date(entry.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    score: entry.productivity_score,
  }));

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading dashboard...</p>
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
          <div>
            <h1 className="text-3xl mb-1">Dashboard</h1>
            <p className="text-gray-600 text-sm">Overview of your productivity analytics</p>
          </div>
          <div className="flex items-center gap-2 text-gray-600">
            <Calendar className="w-4 h-4" />
            <span className="text-sm">{getCurrentDate()}</span>
          </div>
        </div>
      </motion.div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {overviewCards.map((card, index) => {
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

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pie Chart - Category Distribution */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
          className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-6"
        >
          <h3 className="text-xl mb-4">Productivity Categories</h3>
          {stats.totalAnalyses > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={100}
                  dataKey="value"
                >
                  {categoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-500">
              No data available yet
            </div>
          )}
        </motion.div>

        {/* Bar Chart - Activity Breakdown */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.5 }}
          className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-6"
        >
          <h3 className="text-xl mb-4">Recent Activity Breakdown</h3>
          {activityData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={activityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(255, 255, 255, 0.95)",
                    border: "1px solid #e5e7eb",
                    borderRadius: "8px",
                    boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
                  }}
                />
                <Legend />
                <Bar dataKey="Productive" fill="#3b82f6" radius={[8, 8, 0, 0]} />
                <Bar dataKey="Idle" fill="#ef4444" radius={[8, 8, 0, 0]} />
                <Bar dataKey="Social" fill="#f59e0b" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-500">
              No activity data available yet
            </div>
          )}
        </motion.div>
      </div>

      {/* Line Chart - Trend */}
      {trendData.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-6"
        >
          <h3 className="text-xl mb-4">Productivity Trend</h3>
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
                name="Productivity Score"
              />
            </LineChart>
          </ResponsiveContainer>
        </motion.div>
      )}
    </div>
  );
}
