"use client";

import { useEffect, useRef, useState } from 'react';

export interface WaveformSegment {
  start: number;
  end: number;
  text: string;
  segment_index: number;
  color?: string;
  originalIndex?: number;
  energy?: number;
  pitch?: number;
  isMatched?: boolean;
  isSilence?: boolean;
}

interface WaveformVisualizerProps {
  audioUrl: string;
  segments: WaveformSegment[];
  title: string;
  type: 'input' | 'reference' | 'arranged';
  className?: string;
  showSegmentLabels?: boolean;
  height?: number;
}

const SEGMENT_COLORS = [
  '#3B82F6', // Blue
  '#EF4444', // Red  
  '#10B981', // Green
  '#F59E0B', // Amber
  '#8B5CF6', // Purple
  '#06B6D4', // Cyan
  '#F97316', // Orange
  '#84CC16', // Lime
  '#EC4899', // Pink
  '#6B7280', // Gray
  '#14B8A6', // Teal
  '#DC2626', // Red-600
  '#7C3AED', // Violet
  '#059669', // Emerald
  '#D97706', // Amber-600
  '#0284C7', // Sky
  '#DB2777', // Pink-600
  '#65A30D', // Lime-600
  '#0891B2', // Cyan-600
  '#7C2D12', // Orange-800
];

export default function WaveformVisualizer({ 
  audioUrl, 
  segments, 
  title, 
  type,
  className = '',
  showSegmentLabels = true,
  height = 200 
}: WaveformVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const [audioBuffer, setAudioBuffer] = useState<AudioBuffer | null>(null);
  const [duration, setDuration] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  // Load and decode audio
  useEffect(() => {
    const loadAudio = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(audioUrl);
        const arrayBuffer = await response.arrayBuffer();
        
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        const buffer = await audioContext.decodeAudioData(arrayBuffer);
        
        setAudioBuffer(buffer);
        setDuration(buffer.duration);
      } catch (error) {
        console.error('Failed to load audio:', error);
      } finally {
        setIsLoading(false);
      }
    };

    if (audioUrl) {
      loadAudio();
    }
  }, [audioUrl]);

  // Draw waveform
  useEffect(() => {
    if (!audioBuffer || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { width, height: canvasHeight } = canvas;
    ctx.clearRect(0, 0, width, canvasHeight);

    // Get audio data
    const channelData = audioBuffer.getChannelData(0);
    const sampleRate = audioBuffer.sampleRate;
    const samplesPerPixel = channelData.length / width;

    // Draw waveform background
    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, canvasHeight / 2);
    ctx.lineTo(width, canvasHeight / 2);
    ctx.stroke();

    // Draw waveform
    ctx.strokeStyle = '#6B7280';
    ctx.lineWidth = 1;
    ctx.beginPath();

    for (let x = 0; x < width; x++) {
      const sampleIndex = Math.floor(x * samplesPerPixel);
      let sum = 0;
      let count = 0;

      // Average samples for this pixel
      for (let i = 0; i < samplesPerPixel && sampleIndex + i < channelData.length; i++) {
        sum += Math.abs(channelData[sampleIndex + i]);
        count++;
      }

      const average = count > 0 ? sum / count : 0;
      const y = canvasHeight / 2 - (average * canvasHeight / 2 * 0.8);

      if (x === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();

    // Draw segment overlays
    segments.forEach((segment, index) => {
      const startX = (segment.start / duration) * width;
      const endX = (segment.end / duration) * width;
      const segmentWidth = endX - startX;

      if (segmentWidth < 1) return; // Skip very small segments

      // Get segment color
      let color = segment.color;
      if (!color) {
        if (segment.isSilence) {
          color = '#6B7280'; // Gray for silence
        } else if (type === 'arranged' && segment.originalIndex !== undefined) {
          color = SEGMENT_COLORS[segment.originalIndex % SEGMENT_COLORS.length];
        } else {
          color = SEGMENT_COLORS[index % SEGMENT_COLORS.length];
        }
      }

      // Draw segment background with transparency
      ctx.fillStyle = color + '40'; // Add transparency
      ctx.fillRect(startX, 0, segmentWidth, canvasHeight);

      // Draw segment border
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(startX, 0, segmentWidth, canvasHeight);

      // Draw segment number/label
      if (showSegmentLabels && segmentWidth > 20) {
        ctx.fillStyle = color;
        ctx.font = 'bold 12px monospace';
        ctx.textAlign = 'center';
        
        let label;
        if (segment.isSilence) {
          label = '—';
        } else if (type === 'arranged' && segment.originalIndex !== undefined) {
          label = `${segment.originalIndex + 1}`;
        } else {
          label = `${index + 1}`;
        }
        
        ctx.fillText(label, startX + segmentWidth / 2, 20);
      }

      // Draw match indicators for arranged type
      if (type === 'arranged' && !segment.isSilence) {
        if (segment.isMatched) {
          // Draw checkmark for matched segments
          ctx.fillStyle = '#10B981';
          ctx.font = 'bold 16px monospace';
          ctx.textAlign = 'left';
          ctx.fillText('✓', startX + 5, canvasHeight - 10);
        }
      }
    });

    // Draw playhead
    if (duration > 0) {
      const playheadX = (currentTime / duration) * width;
      ctx.strokeStyle = '#EF4444';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(playheadX, 0);
      ctx.lineTo(playheadX, canvasHeight);
      ctx.stroke();
    }

  }, [audioBuffer, segments, duration, currentTime, showSegmentLabels, type]);

  // Handle audio time updates
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
    };

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('ended', handleEnded);
    };
  }, []);

  // Handle canvas click for seeking
  const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!audioRef.current || !duration) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const clickTime = (x / canvas.width) * duration;
    
    audioRef.current.currentTime = clickTime;
    setCurrentTime(clickTime);
  };

  const togglePlayPause = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
  };

  const getTypeIcon = () => {
    switch (type) {
      case 'input': return '🎤';
      case 'reference': return '🎵';
      case 'arranged': return '⚡';
      default: return '🎶';
    }
  };

  const getTypeColor = () => {
    switch (type) {
      case 'input': return 'text-teal-400';
      case 'reference': return 'text-blue-400';
      case 'arranged': return 'text-purple-400';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className={`bg-gray-800 rounded-lg p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className={`text-lg font-semibold ${getTypeColor()}`}>
          {getTypeIcon()} {title}
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-400">
            {segments.filter(s => !s.isSilence).length} segments
          </span>
          {duration > 0 && (
            <span className="text-sm text-gray-400">
              {duration.toFixed(1)}s
            </span>
          )}
        </div>
      </div>

      {/* Waveform */}
      <div className="relative">
        {isLoading ? (
          <div className="flex items-center justify-center h-48 bg-gray-700 rounded">
            <div className="flex items-center gap-2">
              <svg className="animate-spin h-5 w-5 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span className="text-gray-400">Loading waveform...</span>
            </div>
          </div>
        ) : (
          <canvas
            ref={canvasRef}
            width={800}
            height={height}
            className="w-full cursor-pointer bg-gray-700 rounded"
            onClick={handleCanvasClick}
          />
        )}
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between mt-3">
        <button
          onClick={togglePlayPause}
          disabled={isLoading}
          className="flex items-center gap-2 px-3 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded font-medium transition-colors"
        >
          {isPlaying ? '⏸️' : '▶️'}
          {isPlaying ? 'Pause' : 'Play'}
        </button>

        <div className="text-sm text-gray-400">
          {currentTime.toFixed(1)}s / {duration.toFixed(1)}s
        </div>
      </div>

      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        src={audioUrl}
        preload="metadata"
      />
    </div>
  );
}