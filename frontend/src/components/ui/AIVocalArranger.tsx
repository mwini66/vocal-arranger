"use client";

import React, { useState, useEffect } from "react";
import { Card } from "./card";
import { Button } from "./button";

export interface EnhancedSegmentFeature {
  start: number;
  end: number;
  text: string;
  segment_index: number;

  // Normalized audio features (0-1 scale)
  energy: number;
  pitch: number;
  duration: number;
  pause: number;

  // Categorical features for display
  energy_category: string;
  pitch_category: string;
  duration_category: string;
  text_density: string;

  // Musical characteristics
  is_repetitive: boolean;
  has_vocal_runs: boolean;
  is_sustained: boolean;

  // Structural hints
  likely_intro: boolean;
  likely_outro: boolean;
  likely_hook: boolean;

  // Text characteristics
  keywords: string[];
  word_count: number;
  unique_word_ratio: number;
}

interface ArrangementResult {
  arrangement: number[];
  confidence: number;
  method: string;
  analysis?: any;
  structure?: any;
  error?: string;
}

interface ArrangementComparisonResults {
  results: {
    [key: string]: ArrangementResult;
  };
  similarities: {
    [key: string]: number;
  };
  methods_tested: string[];
}

interface AIVocalArrangerProps {
  segments: EnhancedSegmentFeature[];
  audioId: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

const GENRE_OPTIONS = [
  { value: "", label: "Auto-detect" },
  { value: "pop", label: "Pop" },
  { value: "hip-hop", label: "Hip-Hop" },
  { value: "rnb", label: "R&B" },
  { value: "rock", label: "Rock" },
  { value: "folk", label: "Folk" },
  { value: "electronic", label: "Electronic" }
];

const STRUCTURE_OPTIONS = [
  { value: "auto", label: "Auto-arrange" },
  { value: "standard_pop", label: "Standard Pop" },
  { value: "hip_hop", label: "Hip-Hop" },
  { value: "rnb", label: "R&B" },
  { value: "simple", label: "Simple" }
];

export const AIVocalArranger: React.FC<AIVocalArrangerProps> = ({ segments, audioId }) => {
  const [selectedGenre, setSelectedGenre] = useState("");
  const [selectedStructure, setSelectedStructure] = useState("auto");
  const [arrangements, setArrangements] = useState<ArrangementComparisonResults | null>(null);
  const [selectedMethod, setSelectedMethod] = useState<string>("hybrid");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>("");
  const [modelStatus, setModelStatus] = useState<any>(null);
  const [userRating, setUserRating] = useState<number>(0);
  const [customArrangement, setCustomArrangement] = useState<number[]>([]);

  useEffect(() => {
    // Initialize custom arrangement with original order
    setCustomArrangement(segments.map((_, i) => i));

    // Load model status
    fetchModelStatus();
  }, [segments]);

  const fetchModelStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/model_status`);
      const status = await response.json();
      setModelStatus(status);
    } catch (err) {
      console.error("Failed to get model status:", err);
    }
  };

  const handleArrange = async () => {
    setIsLoading(true);
    setError("");

    try {
      const methods = ["hybrid"];
      if (modelStatus?.models?.llm) methods.push("llm_only");
      if (modelStatus?.models?.traditional_ml) methods.push("ml_only");

      const response = await fetch(`${API_URL}/arrangement/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          segments,
          methods,
          genre: selectedGenre || undefined
        })
      });

      if (!response.ok) {
        throw new Error("Failed to get arrangements");
      }

      const data: ArrangementComparisonResults = await response.json();
      setArrangements(data);

      // Set the best arrangement as selected
      const bestMethod = Object.keys(data.results)
        .filter(method => !data.results[method].error)
        .sort((a, b) => (data.results[b].confidence || 0) - (data.results[a].confidence || 0))[0];

      if (bestMethod) {
        setSelectedMethod(bestMethod);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : "Arrangement failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSingleMethodArrange = async (method: string) => {
    setIsLoading(true);
    setError("");

    try {
      let endpoint = "/arrange";
      let payload: any = { segments, genre: selectedGenre || undefined };

      if (method === "llm_only") {
        endpoint = "/arrange/llm_only";
      } else if (method === "ml_only") {
        endpoint = "/arrange/ml_only";
      } else {
        payload.structure = selectedStructure;
      }

      const response = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Failed to get ${method} arrangement`);
      }

      const data = await response.json();

      // Create a single-method result that matches the comparison format
      const singleResult: ArrangementComparisonResults = {
        results: {
          [method]: {
            arrangement: data.arrangement,
            confidence: data.confidence,
            method: data.method,
            analysis: data.analysis,
            structure: data.structure
          }
        },
        similarities: {},
        methods_tested: [method]
      };

      setArrangements(singleResult);
      setSelectedMethod(method);

    } catch (err) {
      setError(err instanceof Error ? err.message : "Arrangement failed");
    } finally {
      setIsLoading(false);
    }
  };

  const submitFeedback = async () => {
    if (!arrangements || !selectedMethod || userRating === 0) return;

    const selectedResult = arrangements.results[selectedMethod];
    if (!selectedResult || selectedResult.error) return;

    try {
      await fetch(`${API_URL}/arrangement/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          audio_id: audioId,
          arrangement_type: selectedMethod,
          ordered_indices: selectedResult.arrangement,
          score: selectedResult.confidence,
          user_rating: userRating,
          segments: segments
        })
      });

      alert("Feedback submitted! This helps improve the AI.");
    } catch (err) {
      console.error("Failed to submit feedback:", err);
    }
  };

  const renderSegmentCard = (segmentIndex: number, position: number) => {
    const segment = segments[segmentIndex];
    if (!segment) return null;

    return (
      <Card key={`${segmentIndex}-${position}`} className="p-4 mb-2 bg-gray-700 border-gray-600">
        <div className="flex justify-between items-start mb-2">
          <div className="text-sm text-gray-400">Segment {segmentIndex + 1} • Position {position + 1}</div>
          <div className="text-xs text-teal-400">
            {segment.duration?.toFixed(1)}s
          </div>
        </div>

        <div className="text-white mb-2 font-medium">
          "{segment.text || 'No text'}"
        </div>

        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <span className="text-gray-400">Energy:</span>
            <span className={`ml-1 px-1 rounded ${getEnergyColor(segment.energy_category)}`}>
              {segment.energy_category}
            </span>
          </div>
          <div>
            <span className="text-gray-400">Pitch:</span>
            <span className={`ml-1 px-1 rounded ${getPitchColor(segment.pitch_category)}`}>
              {segment.pitch_category}
            </span>
          </div>
        </div>

        <div className="mt-2 flex flex-wrap gap-1">
          {segment.likely_intro && <span className="text-xs bg-blue-600 px-1 rounded">Intro</span>}
          {segment.likely_hook && <span className="text-xs bg-yellow-600 px-1 rounded">Hook</span>}
          {segment.likely_outro && <span className="text-xs bg-purple-600 px-1 rounded">Outro</span>}
          {segment.is_repetitive && <span className="text-xs bg-green-600 px-1 rounded">Repetitive</span>}
          {segment.has_vocal_runs && <span className="text-xs bg-pink-600 px-1 rounded">Vocal Runs</span>}
        </div>

        {segment.keywords && segment.keywords.length > 0 && (
          <div className="mt-2 text-xs text-gray-400">
            Keywords: {segment.keywords.slice(0, 5).join(", ")}
          </div>
        )}
      </Card>
    );
  };

  const getEnergyColor = (category: string) => {
    switch (category) {
      case "very_high": return "bg-red-600 text-white";
      case "high": return "bg-orange-600 text-white";
      case "moderate": return "bg-yellow-600 text-black";
      case "low": return "bg-blue-600 text-white";
      default: return "bg-gray-600 text-white";
    }
  };

  const getPitchColor = (category: string) => {
    switch (category) {
      case "very_high": return "bg-purple-600 text-white";
      case "high": return "bg-indigo-600 text-white";
      case "mid_range": return "bg-green-600 text-white";
      case "low": return "bg-teal-600 text-white";
      default: return "bg-gray-600 text-white";
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto p-4">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Control Panel */}
        <div className="lg:col-span-1">
          <Card className="p-6 bg-gray-800 border-gray-700">
            <h3 className="text-xl font-bold text-teal-400 mb-4">AI Arrangement Controls</h3>

            {/* Genre Selection */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Genre Hint
              </label>
              <select
                value={selectedGenre}
                onChange={(e) => setSelectedGenre(e.target.value)}
                className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
              >
                {GENRE_OPTIONS.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Structure Selection */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Song Structure
              </label>
              <select
                value={selectedStructure}
                onChange={(e) => setSelectedStructure(e.target.value)}
                className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
              >
                {STRUCTURE_OPTIONS.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Arrangement Methods */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Arrangement Methods
              </label>
              <div className="space-y-2">
                <Button
                  onClick={handleArrange}
                  disabled={isLoading}
                  className="w-full bg-teal-600 hover:bg-teal-700"
                >
                  {isLoading ? "Arranging..." : "Compare All Methods"}
                </Button>

                <div className="grid grid-cols-2 gap-2">
                  <Button
                    onClick={() => handleSingleMethodArrange("hybrid")}
                    disabled={isLoading}
                    variant="outline"
                    className="text-xs"
                  >
                    Hybrid AI
                  </Button>

                  {modelStatus?.models?.llm && (
                    <Button
                      onClick={() => handleSingleMethodArrange("llm_only")}
                      disabled={isLoading}
                      variant="outline"
                      className="text-xs"
                    >
                      LLM Only
                    </Button>
                  )}

                  {modelStatus?.models?.traditional_ml && (
                    <Button
                      onClick={() => handleSingleMethodArrange("ml_only")}
                      disabled={isLoading}
                      variant="outline"
                      className="text-xs"
                    >
                      ML Only
                    </Button>
                  )}
                </div>
              </div>
            </div>

            {/* Model Status */}
            {modelStatus && (
              <div className="mb-4 text-xs">
                <div className="text-gray-400 mb-1">Available Models:</div>
                <div className="space-y-1">
                  <div className={`flex items-center ${modelStatus.models?.llm ? 'text-green-400' : 'text-red-400'}`}>
                    • LLM: {modelStatus.models?.llm ? 'Ready' : 'Unavailable'}
                  </div>
                  <div className={`flex items-center ${modelStatus.models?.traditional_ml ? 'text-green-400' : 'text-red-400'}`}>
                    • ML Model: {modelStatus.models?.traditional_ml ? 'Ready' : 'Unavailable'}
                  </div>
                </div>
              </div>
            )}

            {/* Error Display */}
            {error && (
              <div className="mb-4 p-2 bg-red-900 border border-red-600 rounded text-red-200 text-sm">
                {error}
              </div>
            )}

            {/* User Feedback */}
            {arrangements && selectedMethod && (
              <div className="border-t border-gray-600 pt-4">
                <div className="text-sm font-medium text-gray-300 mb-2">
                  Rate this arrangement:
                </div>
                <div className="flex gap-1 mb-2">
                  {[1, 2, 3, 4, 5].map(rating => (
                    <button
                      key={rating}
                      onClick={() => setUserRating(rating)}
                      className={`w-6 h-6 text-sm ${
                        rating <= userRating ? 'text-yellow-400' : 'text-gray-600'
                      }`}
                    >
                      ★
                    </button>
                  ))}
                </div>
                <Button
                  onClick={submitFeedback}
                  disabled={userRating === 0}
                  variant="outline"
                  className="w-full text-xs"
                >
                  Submit Feedback
                </Button>
              </div>
            )}
          </Card>
        </div>

        {/* Arrangement Results */}
        <div className="lg:col-span-2">
          {arrangements && (
            <div className="space-y-4">
              {/* Method Selector */}
              <div className="flex gap-2 mb-4">
                {Object.keys(arrangements.results).map(method => (
                  <Button
                    key={method}
                    onClick={() => setSelectedMethod(method)}
                    variant={selectedMethod === method ? "default" : "outline"}
                    className={`text-xs ${
                      arrangements.results[method].error ? 'opacity-50' : ''
                    }`}
                    disabled={!!arrangements.results[method].error}
                  >
                    {method.replace('_', ' ').toUpperCase()}
                    {arrangements.results[method].confidence && (
                      <span className="ml-1 text-xs">
                        ({(arrangements.results[method].confidence * 100).toFixed(0)}%)
                      </span>
                    )}
                  </Button>
                ))}
              </div>

              {/* Selected Arrangement Display */}
              {selectedMethod && arrangements.results[selectedMethod] && !arrangements.results[selectedMethod].error && (
                <div>
                  <h4 className="text-lg font-semibold text-white mb-4">
                    {selectedMethod.replace('_', ' ').toUpperCase()} Arrangement
                    <span className="text-sm text-teal-400 ml-2">
                      (Confidence: {((arrangements.results[selectedMethod].confidence || 0) * 100).toFixed(0)}%)
                    </span>
                  </h4>

                  <div className="grid gap-2">
                    {arrangements.results[selectedMethod].arrangement.map((segmentIndex, position) =>
                      renderSegmentCard(segmentIndex, position)
                    )}
                  </div>

                  {/* Analysis Display */}
                  {arrangements.results[selectedMethod].analysis && (
                    <Card className="mt-4 p-4 bg-gray-800 border-gray-600">
                      <h5 className="font-medium text-teal-400 mb-2">AI Analysis</h5>
                      <div className="text-sm text-gray-300">
                        {arrangements.results[selectedMethod].analysis.reasoning ||
                         "Analysis data available"}
                      </div>
                    </Card>
                  )}
                </div>
              )}

              {/* Error Display for Selected Method */}
              {selectedMethod && arrangements.results[selectedMethod]?.error && (
                <Card className="p-4 bg-red-900 border-red-600">
                  <div className="text-red-200">
                    <strong>{selectedMethod.toUpperCase()} Error:</strong><br />
                    {arrangements.results[selectedMethod].error}
                  </div>
                </Card>
              )}
            </div>
          )}

          {/* Original Segments (when no arrangements yet) */}
          {!arrangements && (
            <div>
              <h4 className="text-lg font-semibold text-white mb-4">
                Original Segments ({segments.length} segments)
              </h4>
              <div className="grid gap-2">
                {segments.map((segment, index) =>
                  renderSegmentCard(index, index)
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
