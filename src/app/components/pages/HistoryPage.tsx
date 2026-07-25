import { ProductivityHistory } from "../ProductivityHistory";
import { motion } from "motion/react";

interface HistoryPageProps {
  userId: string;
}

export function HistoryPage({ userId }: HistoryPageProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-6"
      >
        <h1 className="text-3xl mb-1">History</h1>
        <p className="text-gray-600 text-sm">Track your productivity over time</p>
      </motion.div>

      {/* History Component */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <ProductivityHistory userId={userId} />
      </motion.div>
    </div>
  );
}
