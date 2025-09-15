"use client";

interface AudioPlayerProps {
  audioUrl: string;
}

export default function AudioPlayer({ audioUrl }: AudioPlayerProps) {
  if (!audioUrl) {
    return <div className="text-red-400 text-xs">No audio available.</div>;
  }
  return (
    <div className="flex flex-col items-center">
      <audio controls src={audioUrl} className="w-full" />
    </div>
  );
}

