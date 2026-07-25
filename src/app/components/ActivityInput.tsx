import { useState } from "react";
import { motion } from "motion/react";
import { TrendingUp, RotateCcw, Clock, Coffee, Smartphone, CheckCircle2, Target } from "lucide-react";
import { ActivityData } from "./Dashboard";

interface ActivityInputProps {
  onAnalyze: (data: ActivityData) => void;
  onReset: () => void;
}

export function ActivityInput({ onAnalyze, onReset }: ActivityInputProps) {
  const [formData, setFormData] = useState<ActivityData>({
    taskHours: 0,
    idleHours: 0,
    socialMediaHours: 0,
    breakFrequency: 0,
    tasksCompleted: 0,
  });

  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleChange = (field: keyof ActivityData, value: string) => {
    const numValue = parseFloat(value) || 0;
    setFormData((prev) => ({
      ...prev,
      [field]: Math.max(0, numValue),
    }));
  };

  const handleAnalyze = () => {
    setIsAnalyzing(true);
    
    // Simulate analysis processing
    setTimeout(() => {
      onAnalyze(formData);
      setIsAnalyzing(false);
    }, 800);
  };

  const handleReset = () => {
    setFormData({
      taskHours: 0,
      idleHours: 0,
      socialMediaHours: 0,
      breakFrequency: 0,
      tasksCompleted: 0,
    });
    onReset();
  };

  const inputFields = [
    {
      key: "taskHours" as keyof ActivityData,
      label: "Task Hours",
      icon: Target,
      placeholder: "e.g., 6",
      description: "Hours spent on productive tasks",
    },
    {
      key: "idleHours" as keyof ActivityData,
      label: "Idle Hours",
      icon: Clock,
      placeholder: "e.g., 2",
      description: "Hours of unproductive time",
    },
    {
      key: "socialMediaHours" as keyof ActivityData,
      label: "Social Media (hours)",
      icon: Smartphone,
      placeholder: "e.g., 1.5",
      description: "Time spent on social platforms",
    },
    {
      key: "breakFrequency" as keyof ActivityData,
      label: "Break Frequency",
      icon: Coffee,
      placeholder: "e.g., 5",
      description: "Number of breaks taken",
    },
    {
      key: "tasksCompleted" as keyof ActivityData,
      label: "Tasks Completed",
      icon: CheckCircle2,
      placeholder: "e.g., 8",
      description: "Number of tasks finished",
    },
  ];

  return (
    <div className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-8">
      <h3 className="text-2xl mb-6 flex items-center gap-2">
        <TrendingUp className="w-6 h-6 text-blue-600" />
        Activity Input
      </h3>

      <div className="space-y-5">
        {inputFields.map((field, index) => (
          <motion.div
            key={field.key}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05, duration: 0.3 }}
          >
            <label className="block mb-2 flex items-center gap-2">
              <field.icon className="w-4 h-4 text-purple-600" />
              {field.label}
            </label>
            <input
              type="number"
              step="0.5"
              min="0"
              value={formData[field.key] || ""}
              onChange={(e) => handleChange(field.key, e.target.value)}
              placeholder={field.placeholder}
              className="w-full px-4 py-3 bg-white/80 backdrop-blur-sm border-2 border-gray-200 rounded-xl focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-200 transition-all duration-300"
            />
            <p className="text-xs text-gray-500 mt-1 ml-1">{field.description}</p>
          </motion.div>
        ))}
      </div>

      <div className="mt-8 flex gap-4">
        <motion.button
          onClick={handleAnalyze}
          disabled={isAnalyzing}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="flex-1 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white py-4 px-6 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isAnalyzing ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              <span>Analyzing...</span>
            </>
          ) : (
            <>
              <TrendingUp className="w-5 h-5" />
              <span>Analyze Productivity</span>
            </>
          )}
        </motion.button>

        <motion.button
          onClick={handleReset}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="bg-white hover:bg-gray-50 text-gray-700 py-4 px-6 rounded-xl border-2 border-gray-200 shadow-md hover:shadow-lg transition-all duration-300 flex items-center justify-center gap-2"
        >
          <RotateCcw className="w-5 h-5" />
          <span>Reset</span>
        </motion.button>
      </div>
    </div>
  );
}
