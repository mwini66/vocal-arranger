"use client";

import { useState, useRef } from "react";
import WaveSurferPlayer from "../components/ui/WaveSurferPlayer";

export default function Home() {
  const [vocalsFile, setVocalsFile] = useState<File | null>(null);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
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
  const referenceInputRef = useRef<HTMLInputElement>(null);

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

  // Remove reference file
  const removeReferenceFile = () => {
    setReferenceFile(null);
    setResult(null);
    if (referenceInputRef.current) {
      referenceInputRef.current.value = "";
    }
  };

  const handleUpload = async () => {
    if (!vocalsFile || !referenceFile) {
      setError("Please upload both vocals and reference files.");
      return;
    }
    setIsLoading(true);
    const formData = new FormData();
    formData.append("vocals", vocalsFile);
    formData.append("reference", referenceFile);
    try {
      // Use explicit localhost:5000 if env not set
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";
      const response = await fetch(`${apiUrl}/align`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      setIsLoading(false);
      if (!response.ok) {
        setError(data.error || "Upload failed");
        setResult(null);
      } else {
        setResult(data);
        setError(null);
      }
    } catch (err) {
      setIsLoading(false);
      setError("Failed to connect to backend. Is the server running at " + (process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000") + "?");
      setResult(null);
    }
  };

  return (
    <main className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center p-8">
      <h1 className="text-3xl font-bold mb-6 text-teal-400">
        Intelligent Vocal Alignment
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
              <WaveSurferPlayer audioUrl={recordedUrl || URL.createObjectURL(vocalsFile)} />
              <p className="text-xs text-gray-400 mt-2">Vocals waveform</p>
            </div>
          )}
        </div>

        <div className="mb-4">
          <label className="block mb-2 text-sm font-medium text-teal-300">
            Upload Reference
          </label>
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
          <div className="mt-2">
            {referenceFile && (
              <button
                onClick={removeReferenceFile}
                className="bg-gray-600 text-white px-4 py-2 rounded-lg font-bold"
              >
                Remove
              </button>
            )}
          </div>
          {referenceFile && (
            <div className="mt-4">
              <WaveSurferPlayer audioUrl={URL.createObjectURL(referenceFile)} />
              <p className="text-xs text-gray-400 mt-2">Reference waveform</p>
            </div>
          )}
        </div>

        <button
          onClick={handleUpload}
          className={`w-full font-bold py-2 px-4 rounded-lg ${isLoading ? "bg-gray-500" : "bg-teal-500 hover:bg-teal-600 text-white"}`}
          disabled={isLoading}
        >
          {isLoading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin h-5 w-5 mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>
              Processing...
            </span>
          ) : (
            "Arrange"
          )}
        </button>
        {isLoading && (
          <div className="mt-4 flex items-center justify-center">
            <svg className="animate-spin h-6 w-6 mr-2 text-teal-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>
            <span className="text-teal-400 font-semibold">Arranging and aligning... Please wait.</span>
          </div>
        )}

        {error && (
          <p className="mt-4 text-red-400 font-semibold">{error}</p>
        )}

        {result && (
          <>
            {/* Alignment Results: Always visible, grouped */}
            <div className="mt-6 bg-gray-700 p-4 rounded-lg">
              <h2 className="text-lg font-semibold text-teal-400 mb-4">Alignment Results</h2>
              <div className="mb-4">
                <h3 className="text-teal-300 font-bold mb-2">Original Vocals</h3>
                <WaveSurferPlayer
                  audioUrl={recordedUrl || (vocalsFile ? URL.createObjectURL(vocalsFile) : "")}
                  regions={result.vocals_segments?.map((seg: any) => ({
                    start: seg.start,
                    end: seg.end,
                    word: seg.word || seg.text
                  })) || []}
                />
                <p className="text-xs text-gray-400 mt-2">Original waveform</p>
              </div>
              <div className="mb-4">
                <h3 className="text-teal-300 font-bold mb-2">Rearranged Output</h3>
                <WaveSurferPlayer
                  audioUrl={result.arranged_audio_url}
                  regions={result.timeline?.map((item: any) => ({
                    start: item.start,
                    end: item.end,
                    word: item.word
                  })) || []}
                />
                <p className="text-xs text-gray-400 mt-2">Rearranged waveform</p>
              </div>
            </div>
            {/* Timeline: Timestamps only, toggle visibility */}
            <div className="mt-6 bg-gray-700 p-4 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-lg font-semibold text-teal-400">
                  Timestamps
                </h2>
                <button
                  onClick={() => setShowResult((v) => !v)}
                  className="bg-teal-600 text-white px-3 py-1 rounded-lg text-xs font-bold"
                >
                  {showResult ? "Hide" : "Show"}
                </button>
              </div>
              {showResult && (
                <>
                  <h3 className="text-teal-300 font-bold mb-2">Original Vocals Timeline</h3>
                  <ul className="text-xs text-gray-200 mb-4">
                    {result.vocals_segments?.map((item: any, idx: number) => (
                      <li key={idx}>
                        <span className="text-teal-400">{item.word || item.text}</span>: {item.start.toFixed(2)}s - {item.end.toFixed(2)}s
                      </li>
                    ))}
                  </ul>
                  <h3 className="text-teal-300 font-bold mb-2">Reference Audio Timeline</h3>
                  <ul className="text-xs text-gray-200 mb-4">
                    {result.reference_segments?.map((item: any, idx: number) => (
                      <li key={idx}>
                        <span className="text-teal-400">{item.word || item.text}</span>: {item.start.toFixed(2)}s - {item.end.toFixed(2)}s
                      </li>
                    ))}
                  </ul>
                  <h3 className="text-teal-300 font-bold mb-2">Rearranged Output Timeline</h3>
                  <ul className="text-xs text-gray-200">
                    {result.timeline.map((item: any, idx: number) => (
                      <li key={idx}>
                        <span className="text-teal-400">{item.word}</span>: {item.start.toFixed(2)}s - {item.end.toFixed(2)}s
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          </>
        )}
      </div>
    </main>
  );
}
