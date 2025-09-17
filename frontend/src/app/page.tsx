"use client";

import { useState, useRef, useEffect } from "react";
import AudioPlayer from "../components/ui/AudioPlayer";
import FeedbackModal, { ComprehensiveFeedback } from "../components/ui/FeedbackModal";

// Interface for segment features - extracted from AIVocalArranger since we only need the type
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

interface ReferenceAlignment {
  aligned_segments: EnhancedSegmentFeature[];
  alignment_info: {
    total_reference_segments: number;
    matched_segments: number;
    match_rate: number;
    average_similarity: number;
    total_user_segments: number;
    used_user_segments: number;
    usage_rate: number;
  };
  aligned_audio_path?: string;
}

export default function Home() {
  const [vocalsFile, setVocalsFile] = useState<File | null>(null);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [segments, setSegments] = useState<EnhancedSegmentFeature[] | null>(null);
  const [referenceSegments, setReferenceSegments] = useState<EnhancedSegmentFeature[] | null>(null);
  const [alignmentResult, setAlignmentResult] = useState<ReferenceAlignment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recording, setRecording] = useState<boolean>(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [recordedUrl, setRecordedUrl] = useState<string | null>(null);
  const [isVocalsLoading, setIsVocalsLoading] = useState<boolean>(false);
  const [isReferenceLoading, setIsReferenceLoading] = useState<boolean>(false);
  const [isArranging, setIsArranging] = useState<boolean>(false);
  const [selectedGenre, setSelectedGenre] = useState<string>("");
  const [modelStatus, setModelStatus] = useState<any>(null);
  const [showFeedbackModal, setShowFeedbackModal] = useState<boolean>(false);
  const [originalSegments, setOriginalSegments] = useState<EnhancedSegmentFeature[] | null>(null);
  const [aiAnalysisData, setAiAnalysisData] = useState<any>(null);
  const [sessionId] = useState<string>(() => `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
  const audioChunks = useRef<Blob[]>([]);
  const vocalsInputRef = useRef<HTMLInputElement>(null);
  const referenceInputRef = useRef<HTMLInputElement>(null);

  const GENRE_OPTIONS = [
    { value: "", label: "Auto-detect" },
    { value: "pop", label: "Pop" },
    { value: "hip-hop", label: "Hip-Hop" },
    { value: "rnb", label: "R&B" },
    { value: "rock", label: "Rock" },
    { value: "folk", label: "Folk" },
    { value: "electronic", label: "Electronic" }
  ];

  // Fetch model status on component mount
  useEffect(() => {
    fetchModelStatus();
  }, []);

  // Start recording
  const startRecording = async () => {
    setError(null);
    setSegments(null);
    setRecordedBlob(null);
    setRecordedUrl(null);
    audioChunks.current = [];
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    setMediaRecorder(recorder);
    setRecording(true);
    recorder.ondataavailable = (e) => {
      audioChunks.current.push(e.data);
    };
    recorder.onstop = () => {
      const blob = new Blob(audioChunks.current, { type: "audio/wav" });
      setRecordedBlob(blob);
      setRecordedUrl(URL.createObjectURL(blob));
      setVocalsFile(new File([blob], "live_recording.wav"));
      setRecording(false);
    };
    recorder.start();
  };

  // Stop recording
  const stopRecording = () => {
    mediaRecorder?.stop();
    setRecording(false);
  };

  // Remove vocals file
  const removeVocalsFile = () => {
    setVocalsFile(null);
    setRecordedBlob(null);
    setRecordedUrl(null);
    setSegments(null);
    if (vocalsInputRef.current) {
      vocalsInputRef.current.value = "";
    }
  };

  // Remove reference file
  const removeReferenceFile = () => {
    setReferenceFile(null);
    setReferenceSegments(null);
    setAlignmentResult(null);
    if (referenceInputRef.current) {
      referenceInputRef.current.value = "";
    }
  };

  // Step 1 - Process input vocals
  const handleProcessInputVocals = async () => {
    if (!vocalsFile) {
      setError("Please upload a vocals file first.");
      return;
    }
    setIsVocalsLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("vocals", vocalsFile);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

      const response = await fetch(`${apiUrl}/process_vocals`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || "Input vocals processing failed");
        return;
      }

      setSegments(data.segments);
      // Store the vocals path for later use
      sessionStorage.setItem('inputVocalsPath', data.vocals_path);
      // Store original segments for feedback
      setOriginalSegments([...data.segments]);

    } catch (err) {
      setError("Failed to process input vocals");
    } finally {
      setIsVocalsLoading(false);
    }
  };

  // Step 2 - Process reference vocals
  const handleProcessReferenceVocals = async () => {
    if (!referenceFile) {
      setError("Please upload a reference track first.");
      return;
    }
    setIsReferenceLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("reference", referenceFile);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

      const response = await fetch(`${apiUrl}/process_reference`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || "Reference processing failed");
        return;
      }

      setReferenceSegments(data.reference_segments);
      // Store the reference path for later use
      sessionStorage.setItem('referencePath', data.reference_path);

    } catch (err) {
      setError("Failed to process reference vocals");
    } finally {
      setIsReferenceLoading(false);
    }
  };

  // Step 3 - Temporal Alignment (renamed from AI Arrange)
  const handleArrangeToReference = async () => {
    if (!segments || !referenceSegments) {
      setError("Please process both input vocals and reference track first.");
      return;
    }
    setIsArranging(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";
      const inputVocalsPath = sessionStorage.getItem('inputVocalsPath');

      const response = await fetch(`${apiUrl}/arrange_to_reference`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input_segments: segments,
          reference_segments: referenceSegments,
          input_vocals_path: inputVocalsPath,
          genre: selectedGenre || undefined
        })
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || "Temporal alignment failed");
        return;
      }

      // Update segments with the aligned version
      setSegments(data.arranged_segments);

      // Store alignment analysis data for feedback
      setAiAnalysisData({
        original_arrangement: data.original_arrangement,
        ai_analysis: data.ai_analysis,
        reference_structure: data.reference_structure,
        temporal_alignment_info: data.temporal_alignment_info
      });

      // Set alignment result with the arrangement info
      setAlignmentResult({
        aligned_segments: data.arranged_segments,
        alignment_info: {
          total_reference_segments: data.reference_structure?.total_reference_segments || 0,
          matched_segments: data.reference_structure?.matched_segments || 0,
          match_rate: data.reference_structure?.match_rate || 0,
          average_similarity: data.ai_analysis?.confidence || 0,
          total_user_segments: segments.length,
          used_user_segments: data.reference_structure?.matched_segments || 0,
          usage_rate: data.reference_structure?.matched_segments ? data.reference_structure.matched_segments / segments.length : 0
        },
        aligned_audio_path: data.arranged_audio_url
      });

    } catch (err) {
      setError("Failed to perform temporal alignment");
    } finally {
      setIsArranging(false);
    }
  };

  // Fetch model status
  const fetchModelStatus = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";
      const response = await fetch(`${apiUrl}/model_status`);
      const status = await response.json();
      setModelStatus(status);
    } catch (err) {
      console.error("Failed to get model status:", err);
    }
  };

  // Handle feedback submission
  const handleFeedbackSubmit = async (feedback: ComprehensiveFeedback) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";
      const response = await fetch(`${apiUrl}/arrangement/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(feedback)
      });

      const result = await response.json();

      if (response.ok) {
        console.log("Feedback submitted successfully:", result.feedback_id);
        // Show success message or handle success
      } else {
        console.error("Failed to submit feedback:", result.error);
      }
    } catch (error) {
      console.error("Error submitting feedback:", error);
    }
  };

  // Add new state for showing detailed matching info
  const [showMatchingDetails, setShowMatchingDetails] = useState<boolean>(false);

  return (
    <main className="min-h-screen bg-gray-900 text-white p-4">
      {/* Header */}
      <div className="max-w-6xl mx-auto mb-8">
        <h1 className="text-4xl font-bold text-center mb-4 text-teal-400">
          Temporal Vocal Aligner
        </h1>
        <p className="text-center text-gray-300 text-lg">
          Upload freestyle vocals and align them to reference track timing with intelligent segment matching
        </p>
      </div>

      {/* Upload Section */}
      <div className="max-w-2xl mx-auto mb-8">
        <div className="bg-gray-800 p-6 rounded-2xl shadow-lg">
          <h2 className="text-xl font-semibold mb-4 text-teal-300">
            1. Upload or Record Vocals
          </h2>

          <div className="mb-4">
            <input
              ref={vocalsInputRef}
              type="file"
              accept="audio/*"
              onChange={(e) => setVocalsFile(e.target.files?.[0] || null)}
              className="w-full text-sm text-gray-300 file:mr-4 file:py-2 file:px-4
                         file:rounded-full file:border-0 file:text-sm
                         file:font-semibold file:bg-teal-500 file:text-white
                         hover:file:bg-teal-600"
            />
          </div>

          <div className="flex gap-2 mb-4">
            <button
              onClick={recording ? stopRecording : startRecording}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                recording 
                  ? "bg-red-600 hover:bg-red-700 text-white" 
                  : "bg-teal-600 hover:bg-teal-700 text-white"
              }`}
            >
              {recording ? "🔴 Stop Recording" : "🎤 Record Live Vocals"}
            </button>

            {vocalsFile && (
              <button
                onClick={removeVocalsFile}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium transition-colors"
              >
                Remove File
              </button>
            )}
          </div>

          {/* Audio Preview */}
          {vocalsFile && (
            <div className="mb-4 p-4 bg-gray-700 rounded-lg">
              <h3 className="text-sm font-medium text-gray-300 mb-2">Audio Preview</h3>
              <AudioPlayer audioUrl={recordedUrl || URL.createObjectURL(vocalsFile)} />
              <p className="text-xs text-gray-400 mt-2">
                File: {vocalsFile.name} ({(vocalsFile.size / 1024 / 1024).toFixed(2)} MB)
              </p>
            </div>
          )}

          {/* Process Button */}
          <button
            onClick={handleProcessInputVocals}
            className="w-full bg-teal-600 hover:bg-teal-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-bold text-lg transition-colors"
            disabled={isVocalsLoading || !vocalsFile}
          >
            {isVocalsLoading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Processing...
              </span>
            ) : (
              "🎵 Process Input Vocals"
            )}
          </button>

          {/* Error Display */}
          {error && (
            <div className="mt-4 p-4 bg-red-900 border border-red-600 rounded-lg">
              <div className="text-red-200">
                <strong>Error:</strong> {error}
              </div>
            </div>
          )}

          {/* Segments Preview */}
          {segments && (
            <div className="mt-4 p-4 bg-gray-700 rounded-lg">
              <h3 className="text-sm font-medium text-teal-300 mb-2">
                ✓ Segments Detected: {segments.length}
              </h3>
              <div className="text-xs text-gray-300">
                Ready for arrangement!
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Reference Track Upload Section */}
      <div className="max-w-2xl mx-auto mb-8">
        <div className="bg-gray-800 p-6 rounded-2xl shadow-lg">
          <h2 className="text-xl font-semibold mb-4 text-teal-300">
            2. Upload Reference Track
          </h2>

          <div className="mb-4">
            <input
              ref={referenceInputRef}
              type="file"
              accept="audio/*"
              onChange={(e) => setReferenceFile(e.target.files?.[0] || null)}
              className="w-full text-sm text-gray-300 file:mr-4 file:py-2 file:px-4
                         file:rounded-full file:border-0 file:text-sm
                         file:font-semibold file:bg-teal-500 file:text-white
                         hover:file:bg-teal-600"
            />
          </div>

          {/* Reference Audio Preview */}
          {referenceFile && (
            <div className="mb-4 p-4 bg-gray-700 rounded-lg">
              <h3 className="text-sm font-medium text-gray-300 mb-2">Reference Track Preview</h3>
              <AudioPlayer audioUrl={URL.createObjectURL(referenceFile)} />
              <p className="text-xs text-gray-400 mt-2">
                File: {referenceFile.name} ({(referenceFile.size / 1024 / 1024).toFixed(2)} MB)
              </p>
            </div>
          )}

          <div className="flex gap-2 mb-4">
            {/* Process Reference Button */}
            <button
              onClick={handleProcessReferenceVocals}
              className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-bold text-lg transition-colors"
              disabled={isReferenceLoading || !referenceFile}
            >
              {isReferenceLoading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Processing...
                </span>
              ) : (
                "🎵 Process Reference"
              )}
            </button>

            {referenceFile && (
              <button
                onClick={removeReferenceFile}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium transition-colors"
              >
                Remove
              </button>
            )}
          </div>

          {/* Reference Segments Preview */}
          {referenceSegments && (
            <div className="mt-4 p-4 bg-gray-700 rounded-lg">
              <h3 className="text-sm font-medium text-teal-300 mb-2">
                ✓ Reference Segments Detected: {referenceSegments.length}
              </h3>
              <div className="text-xs text-gray-300">
                Reference track processed successfully!
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Temporal Alignment Section (renamed) */}
      {segments && segments.length > 0 && (
        <div className="max-w-4xl mx-auto mb-8">
          <div className="bg-gray-800 p-6 rounded-2xl shadow-lg">
            <h2 className="text-2xl font-semibold mb-4 text-purple-300 text-center">
              ⚡ Temporal Alignment
            </h2>
            <p className="text-gray-300 mb-6 text-center">
              Align your segments to match reference track timing with intelligent windowed text and audio similarity matching
            </p>

            {/* Temporal Align Button */}
            <button
              onClick={handleArrangeToReference}
              disabled={!segments || !referenceSegments || isArranging}
              className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-bold text-lg transition-colors"
            >
              {isArranging ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 714 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Aligning...
                </span>
              ) : (
                "⚡ Temporal Align to Reference"
              )}
            </button>


            {/* Status Display */}
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-gray-400">Input Vocals:</span>
                {segments ? (
                  <span className="text-green-400">✓ {segments.length} segments processed</span>
                ) : (
                  <span className="text-red-400">✗ Not processed</span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">Reference Track:</span>
                {referenceSegments ? (
                  <span className="text-green-400">✓ {referenceSegments.length} segments processed</span>
                ) : (
                  <span className="text-red-400">✗ Not processed</span>
                )}
              </div>
            </div>

            {alignmentResult && (
              <div className="mt-4 text-center">
                <span className="text-green-400 text-sm">✓ Temporal alignment complete!</span>
                <button
                  onClick={() => setShowMatchingDetails(!showMatchingDetails)}
                  className="ml-4 text-blue-400 hover:text-blue-300 text-sm underline"
                >
                  {showMatchingDetails ? 'Hide' : 'Show'} Matching Details
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Detailed Matching Visualization */}
      {alignmentResult && showMatchingDetails && aiAnalysisData && (
        <div className="max-w-6xl mx-auto mb-8">
          <div className="bg-gray-800 p-6 rounded-2xl shadow-lg">
            <h2 className="text-2xl font-semibold mb-4 text-blue-300 text-center">
              🔍 Segment Matching Analysis
            </h2>

            {/* Matching Statistics */}
            <div className="mb-6 p-4 bg-gray-700/50 rounded-lg">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                <div>
                  <div className="text-2xl font-bold text-green-400">
                    {((aiAnalysisData.temporal_alignment_info?.match_rate || 0) * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-gray-300">Overall Match Rate</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-blue-400">
                    {((aiAnalysisData.temporal_alignment_info?.average_similarity || 0) * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-gray-300">Avg Similarity</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-purple-400">
                    {aiAnalysisData.temporal_alignment_info?.matched_segments || 0}
                  </div>
                  <div className="text-xs text-gray-300">Segments Matched</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-yellow-400">
                    {((aiAnalysisData.temporal_alignment_info?.silence_percentage || 0)).toFixed(1)}%
                  </div>
                  <div className="text-xs text-gray-300">Silence Padding</div>
                </div>
              </div>
            </div>

            {/* Segment-by-Segment Matching Details */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-blue-300 mb-4">Segment Matching Details</h3>

              {alignmentResult.aligned_segments.map((segment, index) => {
                const isSilence = segment.text === '[SILENCE]';
                const matchPercentage = segment.alignment_similarity ? (segment.alignment_similarity * 100) : 0;

                return (
                  <div key={index} className={`p-4 rounded-lg border-l-4 ${
                    isSilence 
                      ? 'bg-gray-700/30 border-gray-500' 
                      : matchPercentage > 70 
                        ? 'bg-green-900/20 border-green-400' 
                        : matchPercentage > 40 
                          ? 'bg-yellow-900/20 border-yellow-400'
                          : 'bg-red-900/20 border-red-400'
                  }`}>
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-mono text-gray-400">#{index + 1}</span>
                        <span className="text-sm text-gray-300">
                          {segment.start.toFixed(2)}s - {segment.end.toFixed(2)}s
                        </span>
                        {!isSilence && (
                          <div className={`px-2 py-1 rounded text-xs font-bold ${
                            matchPercentage > 70 
                              ? 'bg-green-600 text-white' 
                              : matchPercentage > 40 
                                ? 'bg-yellow-600 text-white'
                                : 'bg-red-600 text-white'
                          }`}>
                            {matchPercentage.toFixed(1)}% match
                          </div>
                        )}
                      </div>
                      <div className="text-right text-xs text-gray-400">
                        Duration: {(segment.end - segment.start).toFixed(2)}s
                      </div>
                    </div>

                    <div className="mb-3">
                      <div className="text-white font-medium mb-1">
                        {isSilence ? (
                          <span className="italic text-gray-400">[No matching segment - filled with silence]</span>
                        ) : (
                          <div className="space-y-2">
                            {/* Reference Segment */}
                            <div className="bg-blue-900/20 p-3 rounded border-l-2 border-blue-400">
                              <div className="text-xs text-blue-300 font-semibold mb-1">Reference Track:</div>
                              <div className="text-white">"{segment.reference_text || 'N/A'}"</div>
                            </div>

                            {/* Matched Input Segment */}
                            <div className="bg-green-900/20 p-3 rounded border-l-2 border-green-400">
                              <div className="text-xs text-green-300 font-semibold mb-1">Your Input Match:</div>
                              <div className="text-white">"{segment.matched_input_text || segment.text}"</div>
                            </div>

                            {/* Match Quality Indicator */}
                            {matchPercentage > 0 && (
                              <div className="flex items-center gap-2 mt-2">
                                <div className="text-xs text-gray-400">Text Similarity:</div>
                                <div className="flex-1 bg-gray-600 rounded-full h-2">
                                  <div
                                    className={`h-2 rounded-full ${
                                      matchPercentage > 70 ? 'bg-green-400' : 
                                      matchPercentage > 40 ? 'bg-yellow-400' : 'bg-red-400'
                                    }`}
                                    style={{width: `${matchPercentage}%`}}
                                  ></div>
                                </div>
                                <div className="text-xs text-gray-300">{matchPercentage.toFixed(1)}%</div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    {!isSilence && (
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <span className="text-gray-400">Energy:</span>
                          <div className="flex items-center gap-2">
                            <div className="w-16 bg-gray-600 rounded-full h-2">
                              <div
                                className="bg-orange-400 h-2 rounded-full"
                                style={{width: `${(segment.energy || 0) * 100}%`}}
                              ></div>
                            </div>
                            <span className="text-orange-400">{((segment.energy || 0) * 100).toFixed(0)}%</span>
                          </div>
                        </div>

                        <div>
                          <span className="text-gray-400">Pitch:</span>
                          <div className="flex items-center gap-2">
                            <div className="w-16 bg-gray-600 rounded-full h-2">
                              <div
                                className="bg-blue-400 h-2 rounded-full"
                                style={{width: `${(segment.pitch || 0) * 100}%`}}
                              ></div>
                            </div>
                            <span className="text-blue-400">{((segment.pitch || 0) * 100).toFixed(0)}%</span>
                          </div>
                        </div>

                        <div>
                          <span className="text-gray-400">Words:</span>
                          <span className="text-green-400 ml-2">{segment.word_count || 0}</span>
                        </div>

                        <div>
                          <span className="text-gray-400">Type:</span>
                          <span className="text-purple-400 ml-2">{segment.energy_category || 'medium'}</span>
                        </div>
                      </div>
                    )}

                    {!isSilence && segment.keywords && segment.keywords.length > 0 && (
                      <div className="mt-2">
                        <span className="text-gray-400 text-xs">Keywords: </span>
                        {segment.keywords.slice(0, 3).map((keyword, i) => (
                          <span key={i} className="inline-block bg-gray-600 text-xs px-2 py-1 rounded mr-2 text-gray-200">
                            {keyword}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Matching Algorithm Info */}
            <div className="mt-6 p-4 bg-gray-700/30 rounded-lg">
              <h4 className="text-sm font-semibold text-gray-300 mb-2">Matching Algorithm</h4>
              <div className="text-xs text-gray-400 space-y-1">
                <div>• Text Similarity: TF-IDF vectorization + cosine similarity (60% weight)</div>
                <div>• Audio Features: Energy, pitch, and duration matching (40% weight)</div>
                <div>• Similarity Threshold: {((aiAnalysisData.reference_structure?.similarity_threshold || 0.3) * 100).toFixed(0)}% minimum for matching</div>
                <div>• Time Alignment: Segments placed at reference timestamps with audio stretching</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Final Output Music Player */}
      {alignmentResult && alignmentResult.aligned_audio_path && (
        <div className="max-w-4xl mx-auto mb-8">
          <div className="bg-gradient-to-br from-green-900/30 to-blue-900/30 border border-green-600 p-6 rounded-2xl shadow-lg">
            <h2 className="text-2xl font-semibold mb-4 text-green-300 text-center">
              🎵 Your Arranged Vocals
            </h2>
            <p className="text-green-200 mb-4 text-center">
              Your vocals have been intelligently arranged to match the reference track's structure and energy flow!
            </p>

            {/* Audio Player */}
            <div className="mb-4">
              <AudioPlayer audioUrl={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000"}${alignmentResult.aligned_audio_path}`} />
            </div>

            {/* Download Button */}
            <div className="text-center mb-4">
              <div className="flex gap-4 justify-center">
                <a
                  href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000"}${alignmentResult.aligned_audio_path}`}
                  download="ai_arranged_vocals.wav"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-bold text-lg transition-colors"
                >
                  📥 Download Arranged Vocals
                </a>

                <button
                  onClick={() => setShowFeedbackModal(true)}
                  className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-lg font-bold text-lg transition-colors"
                >
                  ⭐ Rate This Arrangement
                </button>
              </div>
            </div>

            {/* Arrangement Statistics */}
            <div className="p-4 bg-gray-800/50 rounded-lg">
              <h3 className="text-sm font-medium text-green-300 mb-2 text-center">
                Arrangement Statistics
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs text-gray-300">
                <div className="text-center">
                  <div className="font-bold text-white">{alignmentResult.alignment_info.total_reference_segments}</div>
                  <div>Reference Segments</div>
                </div>
                <div className="text-center">
                  <div className="font-bold text-white">{alignmentResult.alignment_info.matched_segments}</div>
                  <div>Matched Segments</div>
                </div>
                <div className="text-center">
                  <div className="font-bold text-white">{(alignmentResult.alignment_info.match_rate * 100).toFixed(1)}%</div>
                  <div>Match Rate</div>
                </div>
                <div className="text-center">
                  <div className="font-bold text-white">{(alignmentResult.alignment_info.usage_rate * 100).toFixed(1)}%</div>
                  <div>Usage Rate</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Instructions */}
      {!segments && (
        <div className="max-w-4xl mx-auto">
          <div className="bg-gray-800 p-6 rounded-lg">
            <h2 className="text-xl font-semibold mb-4 text-teal-300">How It Works</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="text-3xl mb-2">🎤</div>
                <h3 className="font-medium mb-2">1. Upload Vocals</h3>
                <p className="text-sm text-gray-400">
                  Upload or record your freestyle vocals and process them into segments
                </p>
              </div>
              <div className="text-center">
                <div className="text-3xl mb-2">🎶</div>
                <h3 className="font-medium mb-2">2. Add Reference</h3>
                <p className="text-sm text-gray-400">
                  Upload a reference track and process it to extract structure patterns
                </p>
              </div>
              <div className="text-center">
                <div className="text-3xl mb-2">🤖</div>
                <h3 className="font-medium mb-2">3. Temporal Align</h3>
                <p className="text-sm text-gray-400">
                  Use intelligent windowed matching to align your segments with reference track timing
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Feedback Modal */}
      {showFeedbackModal && alignmentResult && originalSegments && aiAnalysisData && (
        <FeedbackModal
          isOpen={showFeedbackModal}
          onClose={() => setShowFeedbackModal(false)}
          onSubmit={handleFeedbackSubmit}
          arrangementData={{
            original_segments: originalSegments,
            arranged_segments: alignmentResult.aligned_segments,
            ai_analysis: aiAnalysisData.ai_analysis,
            reference_segments: referenceSegments || undefined,
            genre: selectedGenre,
            reference_structure: aiAnalysisData.reference_structure
          }}
          sessionId={sessionId}
        />
      )}
    </main>
  );
}
