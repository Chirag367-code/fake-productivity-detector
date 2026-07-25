import { useState } from "react";
import { motion } from "motion/react";
import { ActivityInput } from "../ActivityInput";
import { ProductivityResults } from "../ProductivityResults";
import { ProductivityAnalysis, ActivityData } from "../Dashboard";
import { API_ENDPOINTS, authFetch } from "../../config/api";

interface ManualAnalysisPageProps {
  userId: string;
  userName: string;
}

export function ManualAnalysisPage({ userId, userName }: ManualAnalysisPageProps) {
  const [analysisResult, setAnalysisResult] = useState<ProductivityAnalysis | null>(null);
  const [showResults, setShowResults] = useState(false);

  const handleAnalyze = async (data: ActivityData) => {
    // Productivity calculation algorithm
    let score = 0;

    // Positive contributions
    score += data.taskHours * 8;
    score += data.tasksCompleted * 5;

    // Negative contributions
    score -= data.idleHours * 6;
    score -= data.socialMediaHours * 7;
    score -= data.breakFrequency * 2;

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
      breaks: data.breakFrequency / 2,
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
      await authFetch(API_ENDPOINTS.analyze, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: userId,
          user_name: userName,
          activity_data: {
            task_hours: data.taskHours,
            idle_hours: data.idleHours,
            social_media_usage: data.socialMediaHours,
            break_frequency: data.breakFrequency,
            tasks_completed: data.tasksCompleted,
          },
        }),
      });
    } catch (error) {
      console.error("Error saving analysis to backend:", error);
    }
  };

  const handleReset = () => {
    setShowResults(false);
    setAnalysisResult(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-6"
      >
        <h1 className="text-3xl mb-1">Manual Analysis</h1>
        <p className="text-gray-600 text-sm">Analyze individual productivity data</p>
      </motion.div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Section */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
        >
          <ActivityInput onAnalyze={handleAnalyze} onReset={handleReset} />
        </motion.div>

        {/* Results Section */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          {showResults && analysisResult ? (
            <ProductivityResults analysis={analysisResult} />
          ) : (
            <div className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-8 h-full flex items-center justify-center">
              <div className="text-center text-gray-500">
                <div className="mb-4 text-6xl">📊</div>
                <p className="text-lg">Enter activity data to see results</p>
                <p className="text-sm mt-2">Fill out the form and click Analyze</p>
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
