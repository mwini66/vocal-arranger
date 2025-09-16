import React, { useState } from "react";

export interface SegmentFeature {
  start: number;
  end: number;
  text: string;
  energy: number;
  pitch: number;
  duration: number;
  pause: number;
  keywords: string[];
}

interface ArrangementResult {
  arrangement: number[];
  score: number;
  mode: "rule" | "ml";
}

interface FeedbackPayload {
  audio_id: string;
  arrangement_type: "rule" | "ml";
  ordered_indices: number[];
  score: number;
  user_rating: number;
  timestamp?: string;
}

interface ArrangementComparisonProps {
  audioId: string;
  segments: SegmentFeature[];
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:5000";

async function fetchArrangement(segments: SegmentFeature[], mode: "rule" | "ml"): Promise<ArrangementResult> {
  const res = await fetch(`${API_URL}/arrange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ segments, mode }),
  });
  if (!res.ok) throw new Error("Failed to fetch arrangement");
  return await res.json();
}

async function sendFeedback(payload: FeedbackPayload) {
  await fetch(`${API_URL}/arrangement/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export const ArrangementComparison: React.FC<ArrangementComparisonProps> = ({ audioId, segments }) => {
  const [ruleResult, setRuleResult] = useState<ArrangementResult | null>(null);
  const [mlResult, setMlResult] = useState<ArrangementResult | null>(null);
  const [selected, setSelected] = useState<"rule" | "ml" | null>(null);
  const [userRating, setUserRating] = useState<number>(0);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string>("");

  React.useEffect(() => {
    fetchArrangement(segments, "rule").then(setRuleResult).catch(() => setError("Rule arrangement failed"));
    fetchArrangement(segments, "ml").then(setMlResult).catch(() => setError("ML arrangement failed"));
  }, [segments]);

  const handleSubmit = async () => {
    if (!selected || !ruleResult || !mlResult || userRating < 1) return;
    const result = selected === "rule" ? ruleResult : mlResult;
    const payload: FeedbackPayload = {
      audio_id: audioId,
      arrangement_type: selected,
      ordered_indices: result.arrangement,
      score: result.score,
      user_rating: userRating,
    };
    await sendFeedback(payload);
    setSubmitted(true);
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold">Arrangement Comparison</h2>
      {error && <div className="text-red-500">{error}</div>}
      <div className="grid grid-cols-2 gap-4">
        <div className="border p-4 rounded">
          <h3 className="font-semibold">Rule-Based Arrangement</h3>
          {ruleResult ? (
            <>
              <div>Score: {ruleResult.score.toFixed(2)}</div>
              <ol>
                {ruleResult.arrangement.map((idx) => (
                  <li key={idx}>
                    {segments[idx].text} <span className="text-xs text-gray-500">({segments[idx].start.toFixed(2)}s - {segments[idx].end.toFixed(2)}s)</span>
                  </li>
                ))}
              </ol>
              <button
                className={`mt-2 px-3 py-1 rounded ${selected === "rule" ? "bg-blue-600 text-white" : "bg-gray-200"}`}
                onClick={() => setSelected("rule")}
              >
                Select Rule-Based
              </button>
            </>
          ) : (
            <div>Loading...</div>
          )}
        </div>
        <div className="border p-4 rounded">
          <h3 className="font-semibold">ML-Based Arrangement</h3>
          {mlResult ? (
            <>
              <div>Score: {mlResult.score.toFixed(2)}</div>
              <ol>
                {mlResult.arrangement.map((idx) => (
                  <li key={idx}>
                    {segments[idx].text} <span className="text-xs text-gray-500">({segments[idx].start.toFixed(2)}s - {segments[idx].end.toFixed(2)}s)</span>
                  </li>
                ))}
              </ol>
              <button
                className={`mt-2 px-3 py-1 rounded ${selected === "ml" ? "bg-blue-600 text-white" : "bg-gray-200"}`}
                onClick={() => setSelected("ml")}
              >
                Select ML-Based
              </button>
            </>
          ) : (
            <div>Loading...</div>
          )}
        </div>
      </div>
      {selected && (
        <div className="mt-4">
          <label className="block mb-2">Rate your preferred arrangement (1-5):</label>
          <input
            type="number"
            min={1}
            max={5}
            value={userRating}
            onChange={(e) => setUserRating(Number(e.target.value))}
            className="border px-2 py-1 rounded w-16"
          />
          <button
            className="ml-4 px-4 py-2 bg-green-600 text-white rounded"
            onClick={handleSubmit}
            disabled={submitted || userRating < 1}
          >
            Submit Feedback
          </button>
          {submitted && <span className="ml-4 text-green-600">Thank you for your feedback!</span>}
        </div>
      )}
    </div>
  );
};

