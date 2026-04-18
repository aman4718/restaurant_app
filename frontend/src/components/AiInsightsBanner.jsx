import { Sparkles } from "lucide-react";

export default function AiInsightsBanner({ summary }) {
  if (!summary) return null;

  return (
    <div className="w-full max-w-7xl mx-auto px-4 mt-8">
      <div className="bg-[#E6F4EA]/80 backdrop-blur-md rounded-full py-4 px-6 flex items-center gap-4 text-[#0D3B2E] border border-[#CDE5D8] shadow-sm">
        <div className="bg-[#CDE5D8] p-2 rounded-full flex-shrink-0">
          <Sparkles className="w-5 h-5 text-[#0D3B2E]" />
        </div>
        <p className="text-sm font-medium leading-relaxed">
          <span className="font-bold text-[#0D3B2E] mr-1">AI Insights:</span>
          {summary}
        </p>
      </div>
    </div>
  );
}
