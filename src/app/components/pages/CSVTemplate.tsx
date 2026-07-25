import { Download } from "lucide-react";

export function CSVTemplateDownload() {
  const downloadTemplate = () => {
    const csvContent = `Task_Hours,Idle_Hours,Social_Media_Usage,Break_Frequency,Tasks_Completed
6,1,0.5,4,8
8,0.5,1,3,12
4,3,2,8,3
7,1,1.5,5,10
5,2,3,6,5
3,4,4,10,2
9,0,0.5,2,15`;

    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "productivity_template.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <button
      onClick={downloadTemplate}
      className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-xl transition-all duration-300 shadow-md text-sm"
    >
      <Download className="w-4 h-4" />
      <span>Download Template</span>
    </button>
  );
}
