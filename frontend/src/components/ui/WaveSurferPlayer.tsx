"use client";

import { useEffect, useRef } from "react";
import WaveSurfer from "wavesurfer.js";

interface WaveSurferPlayerProps {
  audioUrl: string;
}

export default function WaveSurferPlayer({ audioUrl }: WaveSurferPlayerProps) {
  const waveformRef = useRef<HTMLDivElement>(null);
  const waveSurferInstance = useRef<WaveSurfer | null>(null);

  useEffect(() => {
    if (!waveformRef.current) return;

    // Destroy previous instance if any
    if (waveSurferInstance.current) {
      waveSurferInstance.current.destroy();
    }

    // Create new instance
    waveSurferInstance.current = WaveSurfer.create({
      container: waveformRef.current,
      waveColor: "#a0a0a0",
      progressColor: "#3b82f6",
      height: 100,
      responsive: true,
    });

    waveSurferInstance.current.load(audioUrl);

    return () => {
      waveSurferInstance.current?.destroy();
    };
  }, [audioUrl]);

  return <div ref={waveformRef}></div>;
}
