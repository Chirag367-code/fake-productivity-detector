import { useState, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Upload, FileText, CheckCircle, AlertCircle, Download, Trash2 } from "lucide-react";
import { API_ENDPOINTS, authFetch } from "../../config/api";
import { CSVTemplateDownload } from "./CSVTemplate";

interface CSVAnalysisResult {
  row: number;
  score: number;
  category: string;
  breakdown: {
    taskHours: number;
    idleHours: number;
    socialMediaHours: number;
    breakFrequency: number;
    tasksCompleted: number;
  };
}

interface UploadCSVPageProps {
  userId: string;
  userName: string;
}

export function UploadCSVPage({ userId, userName }: UploadCSVPageProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [csvData, setCSVData] = useState<string[][]>([]);
  const [results, setResults] = useState<CSVAnalysisResult[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && (droppedFile.type === "text/csv" || droppedFile.type === "application/vnd.ms-excel" || droppedFile.name.toLowerCase().endsWith(".csv"))) {
      processFile(droppedFile);
    } else {
      setError("Please upload a valid CSV file");
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      processFile(selectedFile);
    }
  };

  const processFile = (uploadedFile: File) => {
    setFile(uploadedFile);
    setError("");
    setResults([]);

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const rows = text.split("\n").map((row) => row.split(",").map((cell) => cell.trim()));
      setCSVData(rows);
    };
    reader.readAsText(uploadedFile);
  };

  const analyzeCSV = async () => {
    if (!file) {
      setError("No file selected");
      return;
    }

    setIsAnalyzing(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("user_id", userId);
      formData.append("user_name", userName);

      const response = await authFetch(API_ENDPOINTS.uploadCsv, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(errorData.detail || "Failed to upload CSV");
      }

      const result = await response.json();

      if (result.errors && result.errors.length > 0 && result.results.length === 0) {
        throw new Error(result.errors[0]);
      }

      // Transform backend response to frontend format
      const analysisResults: CSVAnalysisResult[] = result.results.map((r: any, idx: number) => ({
        row: idx + 2, // Backend uses 1-based indexing from data rows
        score: r.productivity_score,
        category: r.category_rule_based, // Use rule-based category as primary
        breakdown: {
          taskHours: r.task_hours,
          idleHours: r.idle_hours,
          socialMediaHours: r.social_media_usage,
          breakFrequency: r.break_frequency,
          tasksCompleted: r.tasks_completed,
        },
      }));

      setResults(analysisResults);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error uploading CSV file");
      console.error("CSV upload error:", err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const exportResults = () => {
    if (results.length === 0) return;

    const csvContent = [
      ["Row", "Score", "Category", "Task Hours", "Idle Hours", "Social Media", "Breaks", "Tasks Completed"],
      ...results.map((r) => [
        r.row,
        r.score.toFixed(2),
        r.category,
        r.breakdown.taskHours,
        r.breakdown.idleHours,
        r.breakdown.socialMediaHours,
        r.breakdown.breakFrequency,
        r.breakdown.tasksCompleted,
      ]),
    ]
      .map((row) => row.join(","))
      .join("\n");

    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `analysis-results-${new Date().toISOString().split("T")[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const clearData = () => {
    setFile(null);
    setCSVData([]);
    setResults([]);
    setError("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

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
            <h1 className="text-3xl mb-1">Upload CSV</h1>
            <p className="text-gray-600 text-sm">Batch analyze productivity data from CSV files</p>
          </div>
          <CSVTemplateDownload />
        </div>
      </motion.div>

      {/* Upload Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-8"
      >
        <h3 className="text-xl mb-4">CSV File Upload</h3>

        {/* Drag and Drop Area */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300 ${
            isDragging
              ? "border-blue-500 bg-blue-50"
              : "border-gray-300 hover:border-blue-400 hover:bg-blue-50/50"
          }`}
        >
          <Upload className={`w-16 h-16 mx-auto mb-4 ${isDragging ? "text-blue-500" : "text-gray-400"}`} />
          <p className="text-lg mb-2">
            {file ? file.name : "Drag and drop your CSV file here"}
          </p>
          <p className="text-sm text-gray-600">or click to browse</p>
          <p className="text-xs text-gray-500 mt-4">
            Expected columns: Task_Hours, Idle_Hours, Social_Media_Usage, Break_Frequency, Tasks_Completed
          </p>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileSelect}
          className="hidden"
        />

        {/* Error Message */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-2 text-red-700"
            >
              <AlertCircle className="w-5 h-5" />
              <span>{error}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Action Buttons */}
        {file && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-6 flex gap-4"
          >
            <button
              onClick={analyzeCSV}
              disabled={isAnalyzing}
              className="flex-1 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white py-3 px-6 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isAnalyzing ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <CheckCircle className="w-5 h-5" />
                  <span>Analyze CSV</span>
                </>
              )}
            </button>
            <button
              onClick={clearData}
              className="bg-white hover:bg-gray-50 text-gray-700 py-3 px-6 rounded-xl border-2 border-gray-200 shadow-md hover:shadow-lg transition-all duration-300 flex items-center gap-2"
            >
              <Trash2 className="w-5 h-5" />
              <span>Clear</span>
            </button>
          </motion.div>
        )}
      </motion.div>

      {/* CSV Preview */}
      {csvData.length > 0 && results.length === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-6"
        >
          <h3 className="text-xl mb-4">Preview (First 5 Rows)</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-gray-200">
                  {csvData[0].map((header, idx) => (
                    <th key={idx} className="px-4 py-3 text-left font-semibold">
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {csvData.slice(1, 6).map((row, rowIdx) => (
                  <tr key={rowIdx} className="border-b border-gray-100 hover:bg-white/50">
                    {row.map((cell, cellIdx) => (
                      <td key={cellIdx} className="px-4 py-3">
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl">Analysis Results ({results.length} entries)</h3>
            <button
              onClick={exportResults}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white rounded-xl transition-all duration-300 shadow-md text-sm"
            >
              <Download className="w-4 h-4" />
              <span>Export Results</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-96 overflow-y-auto">
            {results.map((result, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: idx * 0.05 }}
                className={`p-4 rounded-xl border-2 ${
                  result.category === "Highly Productive"
                    ? "bg-green-50 border-green-200"
                    : result.category === "Moderately Productive"
                    ? "bg-yellow-50 border-yellow-200"
                    : "bg-red-50 border-red-200"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold">Row {result.row}</span>
                  <span className="text-2xl font-bold">{Math.round(result.score)}</span>
                </div>
                <div
                  className={`text-xs px-2 py-1 rounded-lg inline-block ${
                    result.category === "Highly Productive"
                      ? "bg-green-200 text-green-800"
                      : result.category === "Moderately Productive"
                      ? "bg-yellow-200 text-yellow-800"
                      : "bg-red-200 text-red-800"
                  }`}
                >
                  {result.category}
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}