"use client";

import { useState, useRef, useEffect } from "react";
import AudioPlayer from "../components/ui/AudioPlayer";

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

  // Step 3 - AI Arrange to match reference
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
        setError(data.error || "Arrangement to reference failed");
        return;
      }

      // Update segments with the arranged version
      setSegments(data.arranged_segments);

      // Set alignment result with the arrangement info
      setAlignmentResult({
        aligned_segments: data.arranged_segments,
        alignment_info: {
          total_reference_segments: data.reference_structure?.total_reference_segments || 0,
          matched_segments: data.reference_structure?.matched_segments || 0,
          match_rate: data.ai_analysis?.confidence || 0,
          average_similarity: data.ai_analysis?.confidence || 0,
          total_user_segments: segments.length,
          used_user_segments: data.reference_structure?.matched_segments || 0,
          usage_rate: data.reference_structure?.matched_segments ? data.reference_structure.matched_segments / segments.length : 0
        },
        aligned_audio_path: data.arranged_audio_url
      });

    } catch (err) {
      setError("Failed to arrange vocals to reference");
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

  return (
    <main className="min-h-screen bg-gray-900 text-white p-4">
      {/* Header */}
      <div className="max-w-6xl mx-auto mb-8">
        <h1 className="text-4xl font-bold text-center mb-4 text-teal-400">
          AI-Driven Vocal Arranger
        </h1>
        <p className="text-center text-gray-300 text-lg">
          Upload or record freestyle vocals and let AI intelligently arrange them into a structured song
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
                Ready for AI arrangement!
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Reference Track Upload Section */}
      <div className="max-w-2xl mx-auto mb-8">
        <div className="bg-gray-800 p-6 rounded-2xl shadow-lg">
          <h2 className="text-xl font-semibold mb-4 text-teal-300">
            2. Upload Reference Track (Optional)
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

      {/* AI Arrangement Section */}
      {segments && segments.length > 0 && (
        <div className="max-w-4xl mx-auto mb-8">
          <div className="bg-gray-800 p-6 rounded-2xl shadow-lg">
            <h2 className="text-2xl font-semibold mb-4 text-purple-300 text-center">
              🎯 AI Arrangement
            </h2>
            <p className="text-gray-300 mb-6 text-center">
              Choose genre and let AI arrange your segments to match reference structure
            </p>

            {/* Genre Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium mb-2 text-gray-300">Genre (Optional)</label>
              <select
                value={selectedGenre}
                onChange={(e) => setSelectedGenre(e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 text-white"
              >
                {GENRE_OPTIONS.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            {/* AI Arrange Button */}
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
                  Arranging...
                </span>
              ) : (
                "🤖 AI Arrange to Reference"
              )}
            </button>

            {/* AI Model Status */}
            {modelStatus && (
              <div className="mt-4 p-3 bg-gray-700/50 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-300">AI Model Status:</span>
                  <div className="flex items-center gap-2">
                    {modelStatus.models?.ai_llm ? (
                      <>
                        <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                        <span className="text-sm text-green-400">Ready</span>
                      </>
                    ) : (
                      <>
                        <div className="w-2 h-2 bg-red-400 rounded-full"></div>
                        <span className="text-sm text-red-400">Unavailable</span>
                      </>
                    )}
                  </div>
                </div>
                {!modelStatus.models?.ai_llm && (
                  <div className="mt-2 text-xs text-yellow-400">
                    ⚠️ AI model not available. Check OPENROUTER_API_KEY configuration.
                  </div>
                )}
              </div>
            )}

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
                <span className="text-green-400 text-sm">✓ Arrangement complete!</span>
              </div>
            )}
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
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000"}${alignmentResult.aligned_audio_path}`}
                download="ai_arranged_vocals.wav"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-bold text-lg transition-colors"
              >
                📥 Download Arranged Vocals
              </a>
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
                <h3 className="font-medium mb-2">3. AI Arrange</h3>
                <p className="text-sm text-gray-400">
                  Let AI intelligently arrange your segments to match the reference structure
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
