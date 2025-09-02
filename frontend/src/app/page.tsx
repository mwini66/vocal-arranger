"use client";

import { useState } from "react";

export default function Home() {
  const [vocalsFile, setVocalsFile] = useState<File | null>(null);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async () => {
    if (!vocalsFile || !referenceFile) {
      setError("Please upload both vocals and reference files.");
      return;
    }

    const formData = new FormData();
    formData.append("vocals", vocalsFile);
    formData.append("reference", referenceFile);

    try {
      const response = await fetch("http://127.0.0.1:5000/align", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || "Upload failed");
        setResult(null);
      } else {
        setResult(data);
        setError(null);
      }
    } catch (err) {
      setError("Failed to connect to backend.");
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
            type="file"
            accept="audio/*"
            onChange={(e) => setVocalsFile(e.target.files?.[0] || null)}
            className="w-full text-sm text-gray-300 file:mr-4 file:py-2 file:px-4 
                       file:rounded-full file:border-0 file:text-sm 
                       file:font-semibold file:bg-teal-500 file:text-white 
                       hover:file:bg-teal-600"
          />
        </div>

        <div className="mb-4">
          <label className="block mb-2 text-sm font-medium text-teal-300">
            Upload Reference
          </label>
          <input
            type="file"
            accept="audio/*"
            onChange={(e) => setReferenceFile(e.target.files?.[0] || null)}
            className="w-full text-sm text-gray-300 file:mr-4 file:py-2 file:px-4 
                       file:rounded-full file:border-0 file:text-sm 
                       file:font-semibold file:bg-teal-500 file:text-white 
                       hover:file:bg-teal-600"
          />
        </div>

        <button
          onClick={handleUpload}
          className="w-full bg-teal-500 hover:bg-teal-600 text-white font-bold py-2 px-4 rounded-lg"
        >
          Process Alignment
        </button>

        {error && (
          <p className="mt-4 text-red-400 font-semibold">{error}</p>
        )}

        {result && (
          <div className="mt-6 bg-gray-700 p-4 rounded-lg">
            <h2 className="text-lg font-semibold text-teal-400 mb-2">
              Alignment Result
            </h2>
            <pre className="text-sm text-gray-200 whitespace-pre-wrap">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </main>
  );
}
