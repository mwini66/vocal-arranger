"use client";

import { useEffect, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";

interface WaveSurferPlayerProps {
  audioUrl: string;
}

export default function WaveSurferPlayer({ audioUrl }: WaveSurferPlayerProps) {
  const waveformRef = useRef<HTMLDivElement>(null);
  const waveSurferInstance = useRef<WaveSurfer | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    setIsReady(false);
    setLoadError(null);
    if (!waveformRef.current) return;

    if (waveSurferInstance.current) {
      waveSurferInstance.current.destroy();
    }

    waveSurferInstance.current = WaveSurfer.create({
      container: waveformRef.current,
      waveColor: "#a0a0a0",
      progressColor: "#3b82f6",
      height: 100
    });

    waveSurferInstance.current.load(audioUrl);

    waveSurferInstance.current.on("ready", () => {
      setIsReady(true);
    });

    waveSurferInstance.current.on("error", () => {
      setLoadError("Failed to load audio.");
    });

    waveSurferInstance.current.on("play", () => setIsPlaying(true));
    waveSurferInstance.current.on("pause", () => setIsPlaying(false));
    waveSurferInstance.current.on("finish", () => setIsPlaying(false));

    return () => {
      waveSurferInstance.current?.destroy();
    };
  }, [audioUrl]);

  const handlePlayPause = () => {
    if (!isReady || !waveSurferInstance.current) return;
    waveSurferInstance.current.playPause();
  };

  if (!audioUrl) {
    return <div className="text-red-400 text-xs">No audio available.</div>;
  }
  if (loadError) {
    return <div className="text-red-400 text-xs">{loadError}</div>;
  }

  return (
    <div>
      <div ref={waveformRef}></div>
      {!isReady && <div className="text-gray-400 text-xs mt-2">Loading waveform...</div>}
      <button
        onClick={handlePlayPause}
        disabled={!isReady}
        className={`mt-2 px-4 py-1 rounded-lg font-bold text-white ${isReady ? "bg-teal-500 hover:bg-teal-600" : "bg-gray-500"}`}
      >
        {isPlaying ? "Pause" : "Play"}
      </button>
    </div>
  );
}
