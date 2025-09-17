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

interface AIVocalArrangerProps {
  segments: EnhancedSegmentFeature[];
  audioId: string;
  onArrangementComplete?: (arrangement: number[], method: string) => void;
  showReferenceAlignment?: boolean;
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

export const AIVocalArranger: React.FC<AIVocalArrangerProps> = ({
  segments,
  audioId,
  onArrangementComplete,
  showReferenceAlignment = false
}) => {
  const [selectedGenre, setSelectedGenre] = useState("");
  const [arrangementResult, setArrangementResult] = useState<ArrangementResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>("");
  const [modelStatus, setModelStatus] = useState<any>(null);
  const [userRating, setUserRating] = useState<number>(0);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [alignmentResult, setAlignmentResult] = useState<any>(null);

  useEffect(() => {
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

  const handleAIArrange = async () => {
    setIsLoading(true);
    setError("");
    setArrangementResult(null);

    try {
      const response = await fetch(`${API_URL}/arrange`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          segments,
          genre: selectedGenre || undefined
        })
      });

      if (!response.ok) {
        throw new Error("Failed to get AI arrangement");
      }

      const data: ArrangementResult = await response.json();
      setArrangementResult(data);

      if (onArrangementComplete && !data.error) {
        onArrangementComplete(data.arrangement, data.method);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : "AI arrangement failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleReferenceAlignment = async () => {
    if (!referenceFile) {
      setError("Please upload a reference track first");
      return;
    }

    setIsLoading(true);
    setError("");
    setAlignmentResult(null);

    try {
      const formData = new FormData();
      formData.append("vocals", new File([], "vocals.wav")); // This would be the current vocals file
      formData.append("reference", referenceFile);
      if (selectedGenre) {
        formData.append("genre", selectedGenre);
      }

      const response = await fetch(`${API_URL}/align_to_reference`, {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        throw new Error("Failed to align to reference");
      }

      const data = await response.json();
      setAlignmentResult(data);

    } catch (err) {
      setError(err instanceof Error ? err.message : "Reference alignment failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCompleteWorkflow = async () => {
    if (!referenceFile) {
      setError("Please upload a reference track for the complete workflow");
      return;
    }

    setIsLoading(true);
    setError("");
    setArrangementResult(null);
    setAlignmentResult(null);

    try {
      const formData = new FormData();
      formData.append("vocals", new File([], "vocals.wav")); // This would be the current vocals file
      formData.append("reference", referenceFile);
      if (selectedGenre) {
        formData.append("genre", selectedGenre);
      }

      const response = await fetch(`${API_URL}/arrange_and_align`, {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        throw new Error("Failed to complete arrangement and alignment workflow");
      }

      const data = await response.json();

      // Set both arrangement and alignment results
      if (data.ai_arrangement) {
        setArrangementResult({
          arrangement: data.ai_arrangement.arrangement,
          confidence: data.ai_arrangement.confidence,
          method: "ai_then_reference_aligned",
          analysis: data.ai_arrangement.analysis
        });
      }

      setAlignmentResult(data);

      if (onArrangementComplete && data.ai_arrangement) {
        onArrangementComplete(data.ai_arrangement.arrangement, "ai_then_reference_aligned");
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : "Complete workflow failed");
    } finally {
      setIsLoading(false);
    }
  };

  const submitFeedback = async () => {
    if (!arrangementResult || userRating === 0) return;

    try {
      await fetch(`${API_URL}/arrangement/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          audio_id: audioId,
          arrangement_type: arrangementResult.method,
          ordered_indices: arrangementResult.arrangement,
          score: arrangementResult.confidence,
          user_rating: userRating,
          segments: segments
        })
      });

      alert("Feedback submitted! This helps improve the AI.");
      setUserRating(0);
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
    <div className="w-full max-w-6xl mx-auto p-6 bg-gray-800 text-white">
      <div className="mb-6">
        <h2 className="text-3xl font-bold mb-2 text-teal-400">AI Vocal Arranger</h2>
        <p className="text-gray-300">
          Intelligently arrange your vocal segments using AI analysis of lyrics, energy, and musical flow.
          {showReferenceAlignment && " Optionally align to a reference track's timing."}
        </p>
      </div>

      {/* Genre Selection */}
      <div className="mb-6">
        <label className="block text-sm font-medium mb-2">Genre (Optional)</label>
        <select
          value={selectedGenre}
          onChange={(e) => setSelectedGenre(e.target.value)}
          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500"
        >
          {GENRE_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {/* Reference Track Upload (if enabled) */}
      {showReferenceAlignment && (
        <div className="mb-6">
          <label className="block text-sm font-medium mb-2">Reference Track (Optional)</label>
          <input
            type="file"
            accept="audio/*"
            onChange={(e) => setReferenceFile(e.target.files?.[0] || null)}
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
          {referenceFile && (
            <p className="text-sm text-gray-400 mt-1">
              Selected: {referenceFile.name}
            </p>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="mb-6 flex flex-wrap gap-4">
        <Button
          onClick={handleAIArrange}
          disabled={isLoading || segments.length === 0}
          className="bg-teal-600 hover:bg-teal-700 disabled:opacity-50"
        >
          {isLoading ? "Processing..." : "AI Smart Arrange"}
        </Button>

        {showReferenceAlignment && (
          <>
            <Button
              onClick={handleReferenceAlignment}
              disabled={isLoading || !referenceFile}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
            >
              {isLoading ? "Processing..." : "Align to Reference Only"}
            </Button>

            <Button
              onClick={handleCompleteWorkflow}
              disabled={isLoading || !referenceFile}
              className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50"
            >
              {isLoading ? "Processing..." : "AI Arrange + Reference Align"}
            </Button>
          </>
        )}
      </div>

      {/* Model Status */}
      {modelStatus && (
        <div className="mb-6 p-4 bg-gray-700 rounded-lg">
          <h3 className="text-lg font-semibold mb-2">System Status</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-400">AI Model:</span>
              <span className={`ml-2 ${modelStatus.models?.ai_llm ? 'text-green-400' : 'text-red-400'}`}>
                {modelStatus.models?.ai_llm ? '✓ Available' : '✗ Unavailable'}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Reference Alignment:</span>
              <span className={`ml-2 ${modelStatus.services?.reference_alignment ? 'text-green-400' : 'text-red-400'}`}>
                {modelStatus.services?.reference_alignment ? '✓ Available' : '✗ Unavailable'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mb-6 p-4 bg-red-900 border border-red-700 rounded-lg">
          <p className="text-red-300">{error}</p>
        </div>
      )}

      {/* Arrangement Results */}
      {arrangementResult && !arrangementResult.error && (
        <div className="mb-6">
          <h3 className="text-xl font-semibold mb-4 text-teal-400">
            AI Arrangement Result ({arrangementResult.method})
          </h3>

          <div className="mb-4 p-4 bg-gray-700 rounded-lg">
            <div className="flex justify-between items-center">
              <span>Confidence: {(arrangementResult.confidence * 100).toFixed(1)}%</span>
              {arrangementResult.analysis?.reasoning && (
                <span className="text-sm text-gray-400 max-w-md">
                  {arrangementResult.analysis.reasoning}
                </span>
              )}
            </div>
          </div>

          <div className="grid gap-4">
            <h4 className="text-lg font-medium">Arranged Segments:</h4>
            {arrangementResult.arrangement.map((segmentIndex, position) =>
              renderSegmentCard(segmentIndex, position)
            )}
          </div>

          {/* User Feedback */}
          <div className="mt-6 p-4 bg-gray-700 rounded-lg">
            <h4 className="text-lg font-medium mb-3">Rate this arrangement (1-5 stars):</h4>
            <div className="flex items-center gap-4">
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map(rating => (
                  <button
                    key={rating}
                    onClick={() => setUserRating(rating)}
                    className={`text-2xl ${
                      userRating >= rating ? 'text-yellow-400' : 'text-gray-500'
                    } hover:text-yellow-300`}
                  >
                    ★
                  </button>
                ))}
              </div>
              {userRating > 0 && (
                <Button
                  onClick={submitFeedback}
                  className="bg-green-600 hover:bg-green-700"
                  size="sm"
                >
                  Submit Feedback
                </Button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Alignment Results */}
      {alignmentResult && (
        <div className="mb-6">
          <h3 className="text-xl font-semibold mb-4 text-blue-400">
            Reference Alignment Result
          </h3>

          {alignmentResult.aligned_audio_url && (
            <div className="mb-4">
              <audio controls className="w-full">
                <source src={`${API_URL}${alignmentResult.aligned_audio_url}`} type="audio/wav" />
                Your browser does not support the audio element.
              </audio>
            </div>
          )}

          {alignmentResult.alignment_info && (
            <div className="p-4 bg-gray-700 rounded-lg">
              <h4 className="font-medium mb-2">Alignment Statistics:</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>Match Rate: {(alignmentResult.alignment_info.match_rate * 100).toFixed(1)}%</div>
                <div>Average Similarity: {(alignmentResult.alignment_info.average_similarity * 100).toFixed(1)}%</div>
                <div>Segments Matched: {alignmentResult.alignment_info.matched_segments}/{alignmentResult.alignment_info.total_reference_segments}</div>
                <div>Segments Used: {alignmentResult.alignment_info.used_user_segments}/{alignmentResult.alignment_info.total_user_segments}</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Original Segments Display */}
      <div className="mb-6">
        <h3 className="text-xl font-semibold mb-4 text-gray-400">
          Original Segments ({segments.length})
        </h3>
        <div className="grid gap-4">
          {segments.map((_, index) => renderSegmentCard(index, index))}
        </div>
      </div>
    </div>
  );
};
