import { useState } from "react";
import { motion } from "motion/react";
import { LogOut, Calendar } from "lucide-react";
import { ActivityInput } from "./ActivityInput";
import { ProductivityResults } from "./ProductivityResults";
import { ProductivityHistory } from "./ProductivityHistory";
import { API_ENDPOINTS, authFetch } from "../config/api";

interface UserData {
  name: string;
  email: string;
  photo: string;
}

interface DashboardProps {
  user: UserData;
  onLogout: () => void;
}

export interface ActivityData {
  taskHours: number;
  idleHours: number;
  socialMediaHours: number;
  breakFrequency: number;
  tasksCompleted: number;
}

export interface ProductivityAnalysis {
  score: number;
  category: "Highly Productive" | "Moderately Productive" | "Fake Productivity";
  suggestions: string[];
  breakdown: {
    productive: number;
    idle: number;
    social: number;
    breaks: number;
  };
}

export function Dashboard({ user, onLogout }: DashboardProps) {
  const [analysisResult, setAnalysisResult] = useState<ProductivityAnalysis | null>(null);
  const [showResults, setShowResults] = useState(false);
  const [historyKey, setHistoryKey] = useState(0); // Used to refresh history component

  const handleAnalyze = async (data: ActivityData) => {
    // Productivity calculation algorithm
    const totalHours = data.taskHours + data.idleHours + data.socialMediaHours;
    
    // Calculate score (0-100)
    let score = 0;
    
    // Positive contributions
    score += data.taskHours * 8; // Weight: 8 points per task hour
    score += data.tasksCompleted * 5; // Weight: 5 points per completed task
    
    // Negative contributions
    score -= data.idleHours * 6; // Penalty: 6 points per idle hour
    score -= data.socialMediaHours * 7; // Penalty: 7 points per social media hour
    score -= data.breakFrequency * 2; // Penalty: 2 points per break (excessive breaks)
    
    // Normalize score to 0-100
    score = Math.max(0, Math.min(100, score));
    
    // Determine category
    let category: ProductivityAnalysis["category"];
    if (score >= 80) {
      category = "Highly Productive";
    } else if (score >= 50) {
      category = "Moderately Productive";
    } else {
      category = "Fake Productivity";
    }
    
    // Generate suggestions
    const suggestions: string[] = [];
    
    if (data.socialMediaHours > 2) {
      suggestions.push("Reduce social media usage to improve focus");
    }
    if (data.idleHours > 1) {
      suggestions.push("Minimize idle time with better task planning");
    }
    if (data.taskHours < 4) {
      suggestions.push("Increase focused work hours for better productivity");
    }
    if (data.breakFrequency > 8) {
      suggestions.push("Consolidate breaks to maintain workflow momentum");
    }
    if (data.tasksCompleted < 3) {
      suggestions.push("Set clear, achievable task goals for each day");
    }
    if (suggestions.length === 0) {
      suggestions.push("Excellent work! Maintain your current productivity habits");
      suggestions.push("Consider sharing your productivity strategies with peers");
    }
    
    // Calculate breakdown for visualization
    const breakdown = {
      productive: data.taskHours,
      idle: data.idleHours,
      social: data.socialMediaHours,
      breaks: data.breakFrequency / 2, // Convert to hours (assuming 30 min breaks)
    };
    
    const result: ProductivityAnalysis = {
      score,
      category,
      suggestions,
      breakdown,
    };
    
    setAnalysisResult(result);
    setShowResults(true);

    // Save to backend
    try {
      const userId = user.name; // Use name as userId
      
      await authFetch(API_ENDPOINTS.analyze, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: userId,
          user_name: user.name,
          activity_data: {
            task_hours: data.taskHours,
            idle_hours: data.idleHours,
            social_media_usage: data.socialMediaHours,
            break_frequency: data.breakFrequency,
            tasks_completed: data.tasksCompleted,
          },
        }),
      });

      // Refresh history component
      setHistoryKey(prev => prev + 1);
    } catch (error) {
      console.error("Error saving analysis to backend:", error);
      // Continue even if save fails - don't disrupt user experience
    }
  };

  const handleReset = () => {
    setShowResults(false);
    setAnalysisResult(null);
  };

  const getCurrentDate = () => {
    const date = new Date();
    return date.toLocaleDateString("en-US", { 
      weekday: "long", 
      year: "numeric", 
      month: "long", 
      day: "numeric" 
    });
  };

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 p-4 md:p-8">
      {/* Background decorative elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-20 w-96 h-96 bg-blue-300 rounded-full mix-blend-multiply filter blur-xl opacity-10 animate-blob"></div>
        <div className="absolute top-40 right-20 w-96 h-96 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-10 animate-blob animation-delay-2000"></div>
        <div className="absolute bottom-20 left-1/2 w-96 h-96 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-10 animate-blob animation-delay-4000"></div>
      </div>

      <div className="max-w-7xl mx-auto relative z-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-6 mb-8"
        >
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4">
              <img
                src={user.photo}
                alt={user.name}
                className="w-16 h-16 rounded-full border-4 border-white shadow-md"
              />
              <div>
                <h2 className="text-2xl">Welcome back, {user.name.split(" ")[0]}! 👋</h2>
                <p className="text-gray-600 text-sm">{user.name}</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right hidden md:block">
                <div className="flex items-center gap-2 text-gray-600">
                  <Calendar className="w-4 h-4" />
                  <span className="text-sm">{getCurrentDate()}</span>
                </div>
              </div>
              <button
                onClick={onLogout}
                className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-xl transition-all duration-300 shadow-md hover:shadow-lg"
              >
                <LogOut className="w-4 h-4" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </motion.div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Activity Input Section */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <ActivityInput onAnalyze={handleAnalyze} onReset={handleReset} />
          </motion.div>

          {/* Results Section */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            {showResults && analysisResult ? (
              <ProductivityResults analysis={analysisResult} />
            ) : (
              <div className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-8 h-full flex items-center justify-center">
                <div className="text-center text-gray-500">
                  <div className="mb-4 text-6xl">📊</div>
                  <p className="text-lg">Enter your activity data to analyze productivity</p>
                </div>
              </div>
            )}
          </motion.div>
        </div>

        {/* History Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="mt-8"
        >
          <ProductivityHistory key={historyKey} userId={user.name} />
        </motion.div>
      </div>

      <style>{`
        @keyframes blob {
          0%, 100% { transform: translate(0px, 0px) scale(1); }
          33% { transform: translate(30px, -50px) scale(1.1); }
          66% { transform: translate(-20px, 20px) scale(0.9); }
        }
        .animate-blob {
          animation: blob 7s infinite;
        }
        .animation-delay-2000 {
          animation-delay: 2s;
        }
        .animation-delay-4000 {
          animation-delay: 4s;
        }
      `}</style>
    </div>
  );
}