import { motion } from "motion/react";
import { User, Mail, Calendar, Award, BarChart3 } from "lucide-react";
import { Activity } from "lucide-react";
import { useEffect, useState } from "react";
import { API_ENDPOINTS, authFetch } from "../../config/api";

interface UserData {
  name: string;
  email: string;
  photo: string;
}

interface ProfilePageProps {
  user: UserData;
}

export function ProfilePage({ user }: ProfilePageProps) {
  const [stats, setStats] = useState({
    totalAnalyses: 0,
    averageScore: 0,
    bestScore: 0,
    memberSince: "",
  });

  useEffect(() => {
    fetchUserStats();
  }, [user.name]);

  const fetchUserStats = async () => {
    try {
      const response = await authFetch(API_ENDPOINTS.history(user.name));

      if (response.ok) {
        const data = await response.json();
        const analyses = data.history || [];

        const total = analyses.length;
        const avgScore = total > 0
          ? Math.round(analyses.reduce((sum: number, a: any) => sum + (a.productivity_score || a.score || 0), 0) / total)
          : 0;
        const bestScore = total > 0 ? Math.max(...analyses.map((a: any) => a.productivity_score || a.score || 0)) : 0;

        // Get earliest analysis date
        const dates = analyses.map((a: any) => new Date(a.created_at || a.timestamp).getTime());
        const earliestDate = dates.length > 0 ? new Date(Math.min(...dates)) : new Date();

        setStats({
          totalAnalyses: total,
          averageScore: avgScore,
          bestScore: Math.round(bestScore),
          memberSince: earliestDate.toLocaleDateString("en-US", {
            month: "long",
            year: "numeric",
          }),
        });
      }
    } catch (error) {
      console.error("Error fetching user stats:", error);
    }
  };

  const profileStats = [
    {
      label: "Total Analyses",
      value: stats.totalAnalyses,
      icon: BarChart3,
      gradient: "from-blue-400 to-blue-600",
    },
    {
      label: "Average Score",
      value: stats.averageScore,
      icon: Award,
      gradient: "from-purple-400 to-purple-600",
    },
    {
      label: "Best Score",
      value: stats.bestScore,
      icon: Award,
      gradient: "from-green-400 to-green-600",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-6"
      >
        <h1 className="text-3xl mb-1">Profile</h1>
        <p className="text-gray-600 text-sm">Your account information and statistics</p>
      </motion.div>

      {/* Profile Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="backdrop-blur-lg bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 border border-white/50 rounded-2xl shadow-xl p-8"
      >
        <div className="flex items-center gap-6 flex-wrap">
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="w-32 h-32 rounded-full border-4 border-white shadow-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center"
          >
            <Activity className="w-16 h-16 text-white" />
          </motion.div>
          <div className="flex-1">
            <motion.h2
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 }}
              className="text-3xl mb-2"
            >
              {user.name}
            </motion.h2>
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
              className="space-y-2"
            >
              <div className="flex items-center gap-2 text-gray-600">
                <Calendar className="w-4 h-4" />
                <span>Productivity Analyst</span>
              </div>
            </motion.div>
          </div>
        </div>
      </motion.div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {profileStats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 + index * 0.1 }}
              className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-6"
            >
              <div className="flex items-center justify-between mb-4">
                <div className={`p-3 bg-gradient-to-br ${stat.gradient} rounded-xl shadow-lg`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
              </div>
              <div className="text-3xl mb-1">{stat.value}</div>
              <div className="text-sm text-gray-600">{stat.label}</div>
            </motion.div>
          );
        })}
      </div>

      {/* About Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
        className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-6"
      >
        <h3 className="text-xl mb-4 flex items-center gap-2">
          <User className="w-5 h-5 text-purple-600" />
          About
        </h3>
        <div className="space-y-3 text-gray-700">
          <p>
            Welcome to your Fake Productivity Detector profile. This application helps you analyze
            and improve your productivity by tracking various metrics and providing actionable
            insights.
          </p>
          <p className="text-sm text-gray-600">
            Academic Project • Data Science & Web Technologies
          </p>
        </div>
      </motion.div>
    </div>
  );
}
