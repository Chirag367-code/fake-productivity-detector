import { motion } from "motion/react";
import { Trophy, TrendingUp, AlertCircle, Lightbulb, BarChart3, Download } from "lucide-react";
import { ProductivityAnalysis } from "./Dashboard";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from "recharts";

interface ProductivityResultsProps {
  analysis: ProductivityAnalysis;
}

export function ProductivityResults({ analysis }: ProductivityResultsProps) {
  const { score, category, suggestions, breakdown } = analysis;

  // Determine color scheme based on category
  const getColorScheme = () => {
    if (category === "Highly Productive") {
      return {
        gradient: "from-green-400 to-emerald-600",
        bg: "bg-green-50",
        text: "text-green-700",
        icon: Trophy,
        emoji: "🏆",
      };
    } else if (category === "Moderately Productive") {
      return {
        gradient: "from-yellow-400 to-orange-600",
        bg: "bg-yellow-50",
        text: "text-yellow-700",
        icon: TrendingUp,
        emoji: "📈",
      };
    } else {
      return {
        gradient: "from-red-400 to-pink-600",
        bg: "bg-red-50",
        text: "text-red-700",
        icon: AlertCircle,
        emoji: "⚠️",
      };
    }
  };

  const colorScheme = getColorScheme();
  const Icon = colorScheme.icon;

  // Chart data
  const chartData = [
    { name: "Productive", hours: breakdown.productive, fill: "#3b82f6" },
    { name: "Idle", hours: breakdown.idle, fill: "#ef4444" },
    { name: "Social Media", hours: breakdown.social, fill: "#f59e0b" },
    { name: "Breaks", hours: breakdown.breaks, fill: "#8b5cf6" },
  ];

  // Export report as text
  const handleExportReport = () => {
    const reportDate = new Date().toLocaleString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

    const reportContent = `
========================================
PRODUCTIVITY ANALYSIS REPORT
========================================

Generated: ${reportDate}

PRODUCTIVITY SCORE: ${Math.round(score)}/100
CATEGORY: ${category}

ACTIVITY BREAKDOWN (Hours):
- Productive Tasks: ${breakdown.productive}
- Idle Time: ${breakdown.idle}
- Social Media: ${breakdown.social}
- Breaks: ${breakdown.breaks}

IMPROVEMENT SUGGESTIONS:
${suggestions.map((s, i) => `${i + 1}. ${s}`).join("\n")}

========================================
Fake Productivity Detector
Academic Project - Data Science
========================================
    `.trim();

    // Create and download file
    const blob = new Blob([reportContent], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `productivity-report-${new Date().toISOString().split("T")[0]}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-8 space-y-6">
      {/* Header with Export Button */}
      <div className="flex items-center justify-between">
        <h3 className="text-2xl flex items-center gap-2">
          <BarChart3 className="w-6 h-6 text-purple-600" />
          Productivity Analysis
        </h3>
        <button
          onClick={handleExportReport}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white rounded-xl transition-all duration-300 shadow-md hover:shadow-lg text-sm"
        >
          <Download className="w-4 h-4" />
          <span>Export</span>
        </button>
      </div>

      {/* Score Display */}
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="text-center"
      >
        {/* Circular Score Meter */}
        <div className="relative w-48 h-48 mx-auto mb-6">
          <svg className="w-full h-full transform -rotate-90">
            {/* Background circle */}
            <circle
              cx="96"
              cy="96"
              r="80"
              stroke="#e5e7eb"
              strokeWidth="12"
              fill="none"
            />
            {/* Progress circle */}
            <motion.circle
              cx="96"
              cy="96"
              r="80"
              stroke={`url(#gradient-${category.replace(/\s/g, "")})`}
              strokeWidth="12"
              fill="none"
              strokeLinecap="round"
              strokeDasharray={`${2 * Math.PI * 80}`}
              initial={{ strokeDashoffset: 2 * Math.PI * 80 }}
              animate={{ strokeDashoffset: 2 * Math.PI * 80 * (1 - score / 100) }}
              transition={{ duration: 1.5, ease: "easeOut" }}
            />
            <defs>
              <linearGradient id={`gradient-${category.replace(/\s/g, "")}`} x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor={category === "Highly Productive" ? "#4ade80" : category === "Moderately Productive" ? "#fbbf24" : "#f87171"} />
                <stop offset="100%" stopColor={category === "Highly Productive" ? "#059669" : category === "Moderately Productive" ? "#ea580c" : "#ec4899"} />
              </linearGradient>
            </defs>
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.5, duration: 0.5, type: "spring" }}
              className="text-5xl mb-1"
            >
              {Math.round(score)}
            </motion.div>
            <div className="text-gray-600 text-sm">Score</div>
          </div>
        </div>

        {/* Category Badge */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8, duration: 0.5 }}
          className={`inline-flex items-center gap-2 px-6 py-3 rounded-full ${colorScheme.bg} ${colorScheme.text} shadow-md`}
        >
          <Icon className="w-5 h-5" />
          <span>{category}</span>
          <span>{colorScheme.emoji}</span>
        </motion.div>
      </motion.div>

      {/* Activity Breakdown Chart */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1, duration: 0.5 }}
        className="bg-white/50 rounded-xl p-4"
      >
        <h4 className="text-sm mb-4 text-gray-700">Activity Breakdown (hours)</h4>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
              }}
            />
            <Bar dataKey="hours" radius={[8, 8, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </motion.div>

      {/* Suggestions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1.2, duration: 0.5 }}
        className="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6"
      >
        <h4 className="flex items-center gap-2 mb-4 text-gray-800">
          <Lightbulb className="w-5 h-5 text-yellow-500" />
          Improvement Suggestions
        </h4>
        <ul className="space-y-2">
          {suggestions.map((suggestion, index) => (
            <motion.li
              key={index}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 1.3 + index * 0.1, duration: 0.3 }}
              className="flex items-start gap-2 text-sm text-gray-700"
            >
              <span className="text-blue-500 mt-0.5">•</span>
              <span>{suggestion}</span>
            </motion.li>
          ))}
        </ul>
      </motion.div>
    </div>
  );
}