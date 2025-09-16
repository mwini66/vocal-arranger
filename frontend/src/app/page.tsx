"use client";

import { useState, useRef } from "react";
import AudioPlayer from "../components/ui/AudioPlayer";
import { ArrangementComparison } from "../components/ui/ArrangementComparison";
import { SegmentFeature } from "../components/ui/ArrangementComparison";

export default function Home() {
  const [vocalsFile, setVocalsFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [recording, setRecording] = useState<boolean>(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [recordedUrl, setRecordedUrl] = useState<string | null>(null);
  const [showResult, setShowResult] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const audioChunks = useRef<Blob[]>([]);
  const vocalsInputRef = useRef<HTMLInputElement>(null);

  // Start recording
  const startRecording = async () => {
    setError(null);
    setResult(null);
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
    setResult(null);
    if (vocalsInputRef.current) {
      vocalsInputRef.current.value = "";
    }
  };

  // Upload and process vocals only
  const handleUpload = async () => {
    if (!vocalsFile) {
      setError("Please upload or record a vocals file.");
      return;
    }
    setIsLoading(true);
    const formData = new FormData();
    formData.append("vocals", vocalsFile);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";
      // Step 1: Upload vocals and get segments (Whisper)
      const response = await fetch(`${apiUrl}/segment`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        setIsLoading(false);
        setError(data.error || "Segmentation failed");
        setResult(null);
        return;
      }
      // Step 2: Extract segment features and arrange
      const segments: SegmentFeature[] = data.segments;
      const arrangementRes = await fetch(`${apiUrl}/arrange`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ segments, mode: "rule" }),
      });
      const arrangementData = await arrangementRes.json();
      setIsLoading(false);
      setResult({ segments, arrangement: arrangementData });
      setError(null);
    } catch (err) {
      setIsLoading(false);
      setError("Failed to connect to backend. Is the server running at " + (process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000") + "?");
      setResult(null);
    }
  };

  return (
    <main className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center p-8">
      <h1 className="text-3xl font-bold mb-6 text-teal-400">
        Intelligent Vocal Arrangement
      </h1>
      <div className="bg-gray-800 p-6 rounded-2xl shadow-lg w-full max-w-lg">
        <div className="mb-4">
          <label className="block mb-2 text-sm font-medium text-teal-300">
            Upload Vocals
          </label>
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
          <div className="mt-2 flex gap-2">
            <button
              onClick={recording ? stopRecording : startRecording}
              className={`bg-teal-600 text-white px-4 py-2 rounded-lg font-bold ${recording ? "bg-red-500" : ""}`}
            >
              {recording ? "Stop Recording" : "Record Live Vocals"}
            </button>
            {vocalsFile && (
              <button
                onClick={removeVocalsFile}
                className="bg-gray-600 text-white px-4 py-2 rounded-lg font-bold"
              >
                Remove
              </button>
            )}
          </div>
          {vocalsFile && (
            <div className="mt-4">
              <AudioPlayer audioUrl={recordedUrl || URL.createObjectURL(vocalsFile)} />
              <p className="text-xs text-gray-400 mt-2">Vocals playback</p>
            </div>
          )}
        </div>
        <div className="mb-4">
          <button
            onClick={handleUpload}
            className="bg-teal-500 text-white px-6 py-2 rounded-lg font-bold w-full"
            disabled={isLoading || !vocalsFile}
          >
            {isLoading ? "Processing..." : "Segment & Arrange Vocals"}
          </button>
          {error && <div className="text-red-500 mt-2">{error}</div>}
        </div>
        {result && result.segments && result.arrangement && (
          <ArrangementComparison
            audioId={"uploaded-vocal"}
            segments={result.segments}
          />
        )}
      </div>
    </main>
  );
}
