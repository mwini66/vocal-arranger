"use client";

import React, { useState } from "react";
import { Button } from "./button";

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (feedback: ComprehensiveFeedback) => void;
  arrangementData: {
    original_segments: any[];
    arranged_segments: any[];
    ai_analysis: any;
    reference_segments?: any[];
    genre?: string;
    reference_structure?: any;
  };
  sessionId: string;
}

export interface ComprehensiveFeedback {
  session_id: string;
  user_rating: number;
  audio_quality: number;
  alignment_accuracy: number;
  text_matching_quality: number;
  timing_synchronization: number;
  overall_satisfaction: number;
  feedback_text: string;
  would_use_again: boolean;
  arrangement_data: any;
}

export default function FeedbackModal({
  isOpen,
  onClose,
  onSubmit,
  arrangementData,
  sessionId
}: FeedbackModalProps) {
  const [ratings, setRatings] = useState({
    user_rating: 3,
    audio_quality: 3,
    alignment_accuracy: 3,
    text_matching_quality: 3,
    timing_synchronization: 3,
    overall_satisfaction: 3
  });
  const [feedbackText, setFeedbackText] = useState("");
  const [wouldUseAgain, setWouldUseAgain] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleRatingChange = (category: string, value: number) => {
    setRatings(prev => ({
      ...prev,
      [category]: value
    }));
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);

    const comprehensiveFeedback: ComprehensiveFeedback = {
      session_id: sessionId,
      ...ratings,
      feedback_text: feedbackText,
      would_use_again: wouldUseAgain,
      arrangement_data: arrangementData
    };

    try {
      await onSubmit(comprehensiveFeedback);
      onClose();
      // Reset form
      setRatings({
        user_rating: 3,
        audio_quality: 3,
        alignment_accuracy: 3,
        text_matching_quality: 3,
        timing_synchronization: 3,
        overall_satisfaction: 3
      });
      setFeedbackText("");
      setWouldUseAgain(true);
    } catch (error) {
      console.error("Failed to submit feedback:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const RatingStars = ({
    category,
    value,
    label,
    description
  }: {
    category: string;
    value: number;
    label: string;
    description: string;
  }) => (
    <div className="mb-4">
      <div className="flex justify-between items-center mb-2">
        <label className="text-sm font-medium text-gray-200">{label}</label>
        <span className="text-xs text-gray-400">{value}/5</span>
      </div>
      <p className="text-xs text-gray-400 mb-2">{description}</p>
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              handleRatingChange(category, star);
            }}
            onMouseDown={(e) => {
              e.preventDefault();
            }}
            className={`text-2xl transition-colors hover:scale-110 transform cursor-pointer ${
              star <= value 
                ? "text-yellow-400 hover:text-yellow-300" 
                : "text-gray-600 hover:text-gray-500"
            }`}
            style={{ userSelect: 'none' }}
          >
            {star <= value ? "★" : "☆"}
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
      }}
    >
      <div
        className="bg-gray-800 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
        }}
      >
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-teal-300">
              ⚡ Rate Your Temporal Alignment
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white text-xl"
            >
              ✕
            </button>
          </div>

          <p className="text-gray-300 mb-6 text-center">
            Your feedback helps improve the windowed matching algorithm for better vocal alignment!
          </p>

          {/* Alignment Summary */}
          <div className="bg-gray-700/50 rounded-lg p-4 mb-6">
            <h3 className="text-lg font-semibold text-purple-300 mb-2">
              Temporal Alignment Summary
            </h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-400">Input Segments:</span>
                <span className="text-white ml-2">{arrangementData.original_segments?.length || 0}</span>
              </div>
              <div>
                <span className="text-gray-400">Reference Segments:</span>
                <span className="text-white ml-2">{arrangementData.reference_segments?.length || 0}</span>
              </div>
              <div>
                <span className="text-gray-400">Match Rate:</span>
                <span className="text-white ml-2">
                  {((arrangementData.reference_structure?.match_rate || 0) * 100).toFixed(1)}%
                </span>
              </div>
              <div>
                <span className="text-gray-400">Window Size Used:</span>
                <span className="text-white ml-2">{arrangementData.reference_structure?.selected_window_size || "Auto"}</span>
              </div>
            </div>
          </div>

          {/* Rating Categories */}
          <div className="space-y-1">
            <RatingStars
              category="user_rating"
              value={ratings.user_rating}
              label="Overall Rating"
              description="How would you rate this temporal alignment overall?"
            />

            <RatingStars
              category="audio_quality"
              value={ratings.audio_quality}
              label="Audio Quality"
              description="How smooth and natural does the aligned audio sound?"
            />

            <RatingStars
              category="alignment_accuracy"
              value={ratings.alignment_accuracy}
              label="Alignment Accuracy"
              description="How well did the windowed matching algorithm align your segments to the reference timing?"
            />

            <RatingStars
              category="text_matching_quality"
              value={ratings.text_matching_quality}
              label="Text Matching Quality"
              description="How accurately were similar lyrics matched between your vocals and the reference?"
            />

            <RatingStars
              category="timing_synchronization"
              value={ratings.timing_synchronization}
              label="Timing Synchronization"
              description="How well does your vocal timing match the reference track structure?"
            />

            <RatingStars
              category="overall_satisfaction"
              value={ratings.overall_satisfaction}
              label="Overall Satisfaction"
              description="How satisfied are you with this temporal alignment result?"
            />
          </div>

          {/* Text Feedback */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-200 mb-2">
              Additional Comments (Optional)
            </label>
            <textarea
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              placeholder="Share thoughts about the matching accuracy, audio quality, or timing alignment..."
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 text-white resize-none"
              rows={3}
            />
          </div>

          {/* Would Use Again */}
          <div className="mb-6">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={wouldUseAgain}
                onChange={(e) => setWouldUseAgain(e.target.checked)}
                className="w-4 h-4 text-purple-600 bg-gray-700 border-gray-600 rounded focus:ring-purple-500"
              />
              <span className="text-sm text-gray-200">
                I would use this temporal alignment feature again
              </span>
            </label>
          </div>

          {/* Training Data Notice */}
          <div className="bg-blue-900/30 border border-blue-600 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-blue-400">⚡</span>
              <h4 className="text-sm font-semibold text-blue-300">
                Algorithm Improvement Data
              </h4>
            </div>
            <p className="text-xs text-blue-200">
              Your feedback helps improve the windowed matching algorithm and audio processing quality.
              Data includes segment features, matching accuracy scores, and alignment quality metrics.
              No personal information is stored.
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-4">
            <Button
              onClick={onClose}
              variant="outline"
              className="flex-1 border-gray-600 text-gray-300 hover:bg-gray-700"
            >
              Skip Feedback
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="flex-1 bg-purple-600 hover:bg-purple-700 text-white"
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 714 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Submitting...
                </span>
              ) : (
                "Submit Feedback"
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
