"use client";

import { useState, useRef } from "react";
import AudioPlayer from "../components/ui/AudioPlayer";
import { AIVocalArranger, EnhancedSegmentFeature } from "../components/ui/AIVocalArranger";

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
  const [processingMode, setProcessingMode] = useState<'standard' | 'reference'>('standard');
  const [error, setError] = useState<string | null>(null);
  const [recording, setRecording] = useState<boolean>(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [recordedUrl, setRecordedUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isReferenceLoading, setIsReferenceLoading] = useState<boolean>(false);
  const audioChunks = useRef<Blob[]>([]);
  const vocalsInputRef = useRef<HTMLInputElement>(null);
  const referenceInputRef = useRef<HTMLInputElement>(null);

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

  // Process vocals and extract enhanced features
  const handleProcessVocals = async () => {
    if (!vocalsFile) {
      setError("Please upload or record a vocals file.");
      return;
    }
    setIsLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("vocals", vocalsFile);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

      // Upload vocals and get enhanced segment features
      const response = await fetch(`${apiUrl}/segment`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || "Segmentation failed");
        return;
      }

      // The enhanced extract_segment_features now returns all the features we need
      setSegments(data.segments);

    } catch (err) {
      setError("Failed to connect to backend. Is the server running at " + (process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000") + "?");
    } finally {
      setIsLoading(false);
    }
  };

  // Process with reference track (complete workflow)
  const handleProcessWithReference = async () => {
    if (!vocalsFile || !referenceFile) {
      setError("Please upload both vocals and reference track files.");
      return;
    }
    setIsReferenceLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("vocals", vocalsFile);
    formData.append("reference", referenceFile);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

      // Complete workflow: process both files and align
      const response = await fetch(`${apiUrl}/process_with_reference`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || "Reference alignment failed");
        return;
      }

      // Set all the results
      setSegments(data.user_segments);
      setReferenceSegments(data.reference_segments);
      setAlignmentResult({
        aligned_segments: data.aligned_segments,
        alignment_info: data.alignment_info,
        aligned_audio_path: data.aligned_audio_path
      });

    } catch (err) {
      setError("Failed to connect to backend. Is the server running at " + (process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000") + "?");
    } finally {
      setIsReferenceLoading(false);
    }
  };

  // Process reference track only
  const handleProcessReference = async () => {
    if (!referenceFile) {
      setError("Please upload a reference track.");
      return;
    }
    setIsLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("reference", referenceFile);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

      // Process reference track
      const response = await fetch(`${apiUrl}/reference/process`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || "Reference processing failed");
        return;
      }

      setReferenceSegments(data.reference_segments);

      // If we already have user segments, perform alignment
      if (segments && segments.length > 0) {
        await performAlignment(segments, data.reference_segments);
      }

    } catch (err) {
      setError("Failed to connect to backend. Is the server running at " + (process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000") + "?");
    } finally {
      setIsLoading(false);
    }
  };

  // Perform alignment between user and reference segments
  const performAlignment = async (userSegments: EnhancedSegmentFeature[], refSegments: EnhancedSegmentFeature[]) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

      const response = await fetch(`${apiUrl}/align/to_reference`, {
        method: "POST",
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_segments: userSegments,
          reference_segments: refSegments,
          user_audio_path: vocalsFile ? `uploads/audio/${vocalsFile.name}` : null,
          create_audio: true
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || "Alignment failed");
        return;
      }

      setAlignmentResult({
        aligned_segments: data.aligned_segments,
        alignment_info: data.alignment_info,
        aligned_audio_path: data.aligned_audio_path
      });

    } catch (err) {
      setError("Alignment process failed");
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
            onClick={handleProcessVocals}
            className="w-full bg-teal-600 hover:bg-teal-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-bold text-lg transition-colors"
            disabled={isLoading || !vocalsFile}
          >
            {isLoading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Processing Vocals...
              </span>
            ) : (
              "🎵 Analyze & Segment Vocals"
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
                Segments Detected: {segments.length}
              </h3>
              <div className="text-xs text-gray-300">
                Ready for AI arrangement! Scroll down to see arrangement options.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Reference Track Section */}
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

          <div className="flex gap-2 mb-4">
            {/* Single button to process both vocals and reference together */}
            {vocalsFile && referenceFile ? (
              <button
                onClick={handleProcessWithReference}
                className="flex-1 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-bold text-lg transition-colors"
                disabled={isReferenceLoading}
              >
                {isReferenceLoading ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Processing & Aligning...
                  </span>
                ) : (
                  "🔄 Process & Align to Reference"
                )}
              </button>
            ) : (
              <div className="flex-1 text-center text-gray-400 text-sm py-3">
                {!vocalsFile && !referenceFile ? (
                  "Upload both vocals and reference track to enable processing"
                ) : !vocalsFile ? (
                  "Upload vocals file first"
                ) : (
                  "Upload reference track to enable alignment"
                )}
              </div>
            )}

            {referenceFile && (
              <button
                onClick={removeReferenceFile}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium transition-colors"
              >
                Remove
              </button>
            )}
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

          {/* Reference Segments Preview */}
          {referenceSegments && (
            <div className="mt-4 p-4 bg-gray-700 rounded-lg">
              <h3 className="text-sm font-medium text-teal-300 mb-2">
                Reference Segments Detected: {referenceSegments.length}
              </h3>
              <div className="text-xs text-gray-300">
                Reference track processed successfully!
              </div>
            </div>
          )}

          {/* Alignment Result Display */}
          {alignmentResult && (
            <div className="mt-4 space-y-4">
              {/* Alignment Statistics */}
              <div className="p-4 bg-gray-700 rounded-lg">
                <h3 className="text-sm font-medium text-teal-300 mb-2">
                  Alignment Results
                </h3>
                <div className="grid grid-cols-2 gap-4 text-xs text-gray-300">
                  <div>
                    <strong>Total Reference Segments:</strong> {alignmentResult.alignment_info.total_reference_segments}
                  </div>
                  <div>
                    <strong>Matched Segments:</strong> {alignmentResult.alignment_info.matched_segments}
                  </div>
                  <div>
                    <strong>Match Rate:</strong> {(alignmentResult.alignment_info.match_rate * 100).toFixed(2)}%
                  </div>
                  <div>
                    <strong>Average Similarity:</strong> {alignmentResult.alignment_info.average_similarity.toFixed(4)}
                  </div>
                  <div>
                    <strong>Total User Segments:</strong> {alignmentResult.alignment_info.total_user_segments}
                  </div>
                  <div>
                    <strong>Used User Segments:</strong> {alignmentResult.alignment_info.used_user_segments}
                  </div>
                  <div>
                    <strong>Usage Rate:</strong> {(alignmentResult.alignment_info.usage_rate * 100).toFixed(2)}%
                  </div>
                  <div>
                    <strong>Aligned Segments:</strong> {alignmentResult.aligned_segments.length}
                  </div>
                </div>
              </div>

              {/* Aligned Audio Player */}
              {alignmentResult.aligned_audio_path && (
                <div className="p-4 bg-green-900/30 border border-green-600 rounded-lg">
                  <h3 className="text-sm font-medium text-green-300 mb-2">
                    🎵 Aligned Audio Output
                  </h3>
                  <p className="text-xs text-green-200 mb-3">
                    Your vocals have been rearranged to match the reference track's timing and sequence!
                  </p>
                  <AudioPlayer audioUrl={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000"}${alignmentResult.aligned_audio_path}`} />
                  <div className="mt-2 flex gap-2">
                    <a
                      href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000"}${alignmentResult.aligned_audio_path}`}
                      download="aligned_vocals.wav"
                      className="text-xs bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded transition-colors"
                    >
                      📥 Download Aligned Audio
                    </a>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* AI Arrangement Section */}
      {segments && segments.length > 0 && (
        <div className="mb-8">
          <div className="max-w-6xl mx-auto mb-4">
            <h2 className="text-2xl font-semibold text-center text-teal-300">
              3. AI-Powered Vocal Arrangement
            </h2>
            <p className="text-center text-gray-400 mt-2">
              Choose arrangement method and let AI organize your segments into a coherent song structure
            </p>
          </div>

          <AIVocalArranger
            segments={segments}
            audioId={vocalsFile?.name || "uploaded-vocal"}
          />
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
                <h3 className="font-medium mb-2">1. Upload Audio</h3>
                <p className="text-sm text-gray-400">
                  Upload a freestyle vocal recording or record directly in your browser
                </p>
              </div>
              <div className="text-center">
                <div className="text-3xl mb-2">🎶</div>
                <h3 className="font-medium mb-2">2. Reference Track (Optional)</h3>
                <p className="text-sm text-gray-400">
                  Upload a reference vocal track to align your vocals to match its timing and structure
                </p>
              </div>
              <div className="text-center">
                <div className="text-3xl mb-2">🤖</div>
                <h3 className="font-medium mb-2">3. AI Arrangement</h3>
                <p className="text-sm text-gray-400">
                  AI analyzes and arranges your segments into a structured song or matches reference timing
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
