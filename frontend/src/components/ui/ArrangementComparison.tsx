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
  mode: string;
}

interface EnsembleResult {
  best_arrangement: number[];
  confidence: number;
  all_results: {
    [key: string]: {
      arrangement: number[];
      score: number;
      method: string;
      available: boolean;
      error?: string;
    };
  };
  method: string;
}

interface FeedbackPayload {
  audio_id: string;
  arrangement_type: string;
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

async function fetchArrangement(segments: SegmentFeature[], mode: string): Promise<ArrangementResult> {
  const endpoint = mode === "ensemble" ? "/arrange_ensemble" :
                  mode === "trained_ml" ? "/arrange_ml" :
                  mode === "llm" ? "/arrange_llm" : "/arrange";

  const payload = mode === "ensemble" ?
    { segments, methods: ["rule", "ml", "llm", "trained_ml"] } :
    { segments, mode };

  const res = await fetch(`${API_URL}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Failed to fetch ${mode} arrangement`);
  return await res.json();
}

async function sendFeedback(payload: FeedbackPayload) {
  await fetch(`${API_URL}/arrangement/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function getModelStatus() {
  const res = await fetch(`${API_URL}/model_status`);
  if (!res.ok) throw new Error("Failed to get model status");
  return await res.json();
}

export const ArrangementComparison: React.FC<ArrangementComparisonProps> = ({ audioId, segments }) => {
  const [results, setResults] = useState<{[key: string]: ArrangementResult | EnsembleResult}>({});
  const [modelStatus, setModelStatus] = useState<any>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [userRating, setUserRating] = useState<number>(0);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(false);

  React.useEffect(() => {
    // Load model status
    getModelStatus().then(setModelStatus).catch(() => setError("Failed to get model status"));

    // Load all available arrangements
    const availableMethods = ["rule", "ml", "trained_ml", "llm", "ensemble"];
    setLoading(true);

    Promise.allSettled(
      availableMethods.map(async (method) => {
        try {
          const result = await fetchArrangement(segments, method);
          return { method, result };
        } catch (e) {
          return { method, result: null, error: String(e) };
        }
      })
    ).then((results) => {
      const newResults: {[key: string]: ArrangementResult | EnsembleResult} = {};
      results.forEach((result) => {
        if (result.status === 'fulfilled' && result.value.result) {
          newResults[result.value.method] = result.value.result;
        }
      });
      setResults(newResults);
      setLoading(false);
    });
  }, [segments]);

  const handleSubmit = async () => {
    if (!selected || userRating < 1) return;

    const selectedResult = results[selected];
    if (!selectedResult) return;

    const arrangement = 'best_arrangement' in selectedResult ?
      selectedResult.best_arrangement : selectedResult.arrangement;
    const score = 'confidence' in selectedResult ?
      selectedResult.confidence : selectedResult.score;

    const payload: FeedbackPayload = {
      audio_id: audioId,
      arrangement_type: selected,
      ordered_indices: arrangement,
      score: score,
      user_rating: userRating,
    };

    await sendFeedback(payload);
    setSubmitted(true);
  };

  const renderArrangement = (method: string, result: ArrangementResult | EnsembleResult) => {
    const arrangement = 'best_arrangement' in result ? result.best_arrangement : result.arrangement;
    const score = 'confidence' in result ? result.confidence : result.score;
    const isEnsemble = method === 'ensemble';

    return (
      <div key={method} className="border p-4 rounded">
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-semibold capitalize">{method.replace('_', ' ')} Arrangement</h3>
          {modelStatus?.models?.[method] === false && (
            <span className="text-yellow-500 text-xs">Not Available</span>
          )}
        </div>

        <div className="mb-2">
          <span className="text-sm">Score: {score.toFixed(3)}</span>
          {isEnsemble && (
            <span className="ml-2 text-xs text-blue-500">
              (Best of {Object.keys((result as EnsembleResult).all_results).length} methods)
            </span>
          )}
        </div>

        <ol className="text-sm mb-3 max-h-40 overflow-y-auto">
          {arrangement.map((idx, pos) => (
            <li key={pos} className="mb-1">
              <span className="text-gray-500">{pos + 1}.</span> {segments[idx]?.text || 'No text'}{' '}
              <span className="text-xs text-gray-400">
                ({segments[idx]?.start.toFixed(1)}s - {segments[idx]?.end.toFixed(1)}s,
                E: {segments[idx]?.energy.toFixed(2)})
              </span>
            </li>
          ))}
        </ol>

        {isEnsemble && (result as EnsembleResult).all_results && (
          <details className="text-xs text-gray-600 mb-2">
            <summary>Show individual method results</summary>
            <div className="mt-2 space-y-1">
              {Object.entries((result as EnsembleResult).all_results).map(([subMethod, subResult]) => (
                <div key={subMethod}>
                  <strong>{subMethod}:</strong> Score {subResult.score.toFixed(3)},
                  Available: {subResult.available ? 'Yes' : 'No'}
                  {subResult.error && <span className="text-red-500"> (Error: {subResult.error})</span>}
                </div>
              ))}
            </div>
          </details>
        )}

        <button
          className={`px-3 py-1 rounded text-sm ${
            selected === method ? "bg-blue-600 text-white" : "bg-gray-200"
          }`}
          onClick={() => setSelected(method)}
          disabled={loading}
        >
          Select {method.replace('_', ' ')}
        </button>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <h2 className="text-xl font-bold">AI-Driven Arrangement Comparison</h2>
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-2">Generating arrangements...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold">AI-Driven Arrangement Comparison</h2>
        <p className="text-sm text-gray-600 mt-1">
          Compare different AI methods for arranging your vocal segments. Each method uses different approaches:
        </p>
        <ul className="text-xs text-gray-500 mt-2 ml-4">
          <li>• <strong>Rule:</strong> Energy progression & keyword grouping</li>
          <li>• <strong>ML:</strong> Weighted feature scoring</li>
          <li>• <strong>Trained ML:</strong> Machine learning on real song data</li>
          <li>• <strong>LLM:</strong> Local AI language model analysis</li>
          <li>• <strong>Ensemble:</strong> Best combination of all methods</li>
        </ul>
      </div>

      {error && <div className="text-red-500 text-sm">{error}</div>}

      {modelStatus && (
        <div className="bg-gray-100 p-3 rounded text-sm">
          <strong>System Status:</strong>
          {modelStatus.models?.trained_ml ? ' Trained ML ✓' : ' Trained ML ✗'}
          {modelStatus.services?.ollama ? ' Ollama LLM ✓' : ' Ollama LLM ✗'}
          <span className="ml-2 text-xs">
            ({modelStatus.data?.feature_files || 0} training files available)
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Object.entries(results).map(([method, result]) => renderArrangement(method, result))}
      </div>

      {selected && (
        <div className="bg-blue-50 p-4 rounded">
          <label className="block mb-2 font-medium">
            Rate your selected arrangement ({selected.replace('_', ' ')}):
          </label>
          <div className="flex items-center space-x-4">
            <input
              type="range"
              min={1}
              max={5}
              value={userRating}
              onChange={(e) => setUserRating(Number(e.target.value))}
              className="flex-1"
            />
            <span className="font-bold">{userRating}/5</span>
            <button
              className="px-4 py-2 bg-green-600 text-white rounded"
              onClick={handleSubmit}
              disabled={submitted || userRating < 1}
            >
              Submit Feedback
            </button>
          </div>
          {submitted && <span className="text-green-600 text-sm mt-2 block">Thank you for your feedback!</span>}
        </div>
      )}
    </div>
  );
};
