"use client";

import { useState } from 'react';
import WaveformVisualizer, { WaveformSegment } from './WaveformVisualizer';
import { EnhancedSegmentFeature } from '../../app/page';

interface WaveformComparisonProps {
  inputAudioUrl?: string;
  referenceAudioUrl?: string;
  arrangedAudioUrl?: string;
  inputSegments?: EnhancedSegmentFeature[];
  referenceSegments?: EnhancedSegmentFeature[];
  arrangedSegments?: EnhancedSegmentFeature[];
  className?: string;
}

export default function WaveformComparison({
  inputAudioUrl,
  referenceAudioUrl,
  arrangedAudioUrl,
  inputSegments = [],
  referenceSegments = [],
  arrangedSegments = [],
  className = ''
}: WaveformComparisonProps) {
  const [selectedView, setSelectedView] = useState<'stacked' | 'tabbed'>('stacked');
  const [activeTab, setActiveTab] = useState<'input' | 'reference' | 'arranged'>('input');

  // Convert segments to waveform format and add tracking info
  const convertToWaveformSegments = (
    segments: EnhancedSegmentFeature[], 
    type: 'input' | 'reference' | 'arranged'
  ): WaveformSegment[] => {
    return segments.map((segment, index) => {
      let originalIndex = index;
      let isMatched = false;
      let isSilence = false;

      // For arranged segments, try to find original index and match status
      if (type === 'arranged') {
        isSilence = segment.text === '[SILENCE]';
        
        if (!isSilence) {
          // Find the original segment in input segments
          const matchedInput = inputSegments.find(inputSeg => 
            inputSeg.text === segment.text || 
            (inputSeg.text && segment.text && 
             inputSeg.text.toLowerCase().trim() === segment.text.toLowerCase().trim())
          );
          
          if (matchedInput) {
            originalIndex = inputSegments.indexOf(matchedInput);
            isMatched = true;
          }
        }
      }

      return {
        start: segment.start,
        end: segment.end,
        text: segment.text,
        segment_index: segment.segment_index,
        originalIndex,
        energy: segment.energy,
        pitch: segment.pitch,
        isMatched,
        isSilence
      };
    });
  };

  const inputWaveformSegments = convertToWaveformSegments(inputSegments, 'input');
  const referenceWaveformSegments = convertToWaveformSegments(referenceSegments, 'reference');
  const arrangedWaveformSegments = convertToWaveformSegments(arrangedSegments, 'arranged');

  // Calculate segment movement statistics
  const getSegmentMovementStats = () => {
    if (!inputSegments.length || !arrangedSegments.length) return null;

    const movements: { from: number; to: number; distance: number; text: string }[] = [];
    const silenceSegments = arrangedSegments.filter(seg => seg.text === '[SILENCE]').length;
    
    arrangedSegments.forEach((arrangedSeg, arrangedIndex) => {
      if (arrangedSeg.text !== '[SILENCE]') {
        const originalIndex = inputSegments.findIndex(inputSeg => 
          inputSeg.text === arrangedSeg.text || 
          (inputSeg.text && arrangedSeg.text && 
           inputSeg.text.toLowerCase().trim() === arrangedSeg.text.toLowerCase().trim())
        );
        
        if (originalIndex !== -1) {
          movements.push({
            from: originalIndex,
            to: arrangedIndex,
            distance: arrangedIndex - originalIndex,
            text: arrangedSeg.text.substring(0, 30) + (arrangedSeg.text.length > 30 ? '...' : '')
          });
        }
      }
    });

    return {
      totalMovements: movements.length,
      silenceSegments,
      movements: movements.sort((a, b) => Math.abs(b.distance) - Math.abs(a.distance)),
      averageMovement: movements.length > 0 
        ? movements.reduce((sum, m) => sum + Math.abs(m.distance), 0) / movements.length 
        : 0
    };
  };

  const movementStats = getSegmentMovementStats();

  const renderLegend = () => (
    <div className="bg-gray-700/50 p-4 rounded-lg mb-4">
      <h4 className="text-sm font-semibold text-gray-300 mb-3">Segment Legend</h4>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        <div>
          <div className="font-medium text-teal-300 mb-2">🎤 Input Segments</div>
          <div className="text-gray-400">Original order (1, 2, 3...)</div>
          <div className="text-gray-400">Colors represent segment sequence</div>
        </div>
        <div>
          <div className="font-medium text-blue-300 mb-2">🎵 Reference Segments</div>
          <div className="text-gray-400">Target structure timing</div>
          <div className="text-gray-400">Shows desired arrangement pattern</div>
        </div>
        <div>
          <div className="font-medium text-purple-300 mb-2">⚡ Arranged Segments</div>
          <div className="text-gray-400">Numbers show original positions</div>
          <div className="text-gray-400">✓ = matched, — = silence padding</div>
        </div>
      </div>
      
      {movementStats && (
        <div className="mt-4 pt-3 border-t border-gray-600">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-lg font-bold text-purple-400">{movementStats.totalMovements}</div>
              <div className="text-xs text-gray-400">Segments Moved</div>
            </div>
            <div>
              <div className="text-lg font-bold text-yellow-400">{movementStats.silenceSegments}</div>
              <div className="text-xs text-gray-400">Silence Gaps</div>
            </div>
            <div>
              <div className="text-lg font-bold text-green-400">{movementStats.averageMovement.toFixed(1)}</div>
              <div className="text-xs text-gray-400">Avg Movement</div>
            </div>
            <div>
              <div className="text-lg font-bold text-blue-400">
                {inputSegments.length > 0 ? ((movementStats.totalMovements / inputSegments.length) * 100).toFixed(0) : 0}%
              </div>
              <div className="text-xs text-gray-400">Rearranged</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const renderSegmentMovementTable = () => {
    if (!movementStats || movementStats.movements.length === 0) return null;

    return (
      <div className="bg-gray-700/50 p-4 rounded-lg mt-4">
        <h4 className="text-sm font-semibold text-gray-300 mb-3">Largest Segment Movements</h4>
        <div className="space-y-2 max-h-40 overflow-y-auto">
          {movementStats.movements.slice(0, 10).map((movement, index) => (
            <div key={index} className="flex items-center justify-between text-xs p-2 bg-gray-600/50 rounded">
              <div className="flex items-center gap-2">
                <span className="font-mono text-gray-400">#{movement.from + 1}</span>
                <span className="text-gray-300">→</span>
                <span className="font-mono text-gray-400">#{movement.to + 1}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`font-bold ${
                  Math.abs(movement.distance) > 3 ? 'text-red-400' : 
                  Math.abs(movement.distance) > 1 ? 'text-yellow-400' : 'text-green-400'
                }`}>
                  {movement.distance > 0 ? '+' : ''}{movement.distance}
                </span>
                <span className="text-gray-400 max-w-40 truncate">{movement.text}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header with view controls */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-white">
          🌊 Waveform Analysis & Segment Tracking
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSelectedView('stacked')}
            className={`px-3 py-2 rounded text-sm font-medium transition-colors ${
              selectedView === 'stacked' 
                ? 'bg-purple-600 text-white' 
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            📊 Stacked View
          </button>
          <button
            onClick={() => setSelectedView('tabbed')}
            className={`px-3 py-2 rounded text-sm font-medium transition-colors ${
              selectedView === 'tabbed' 
                ? 'bg-purple-600 text-white' 
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            📑 Tabbed View
          </button>
        </div>
      </div>

      {/* Legend */}
      {renderLegend()}

      {selectedView === 'stacked' ? (
        /* Stacked View */
        <div className="space-y-4">
          {/* Input Waveform */}
          {inputAudioUrl && (
            <WaveformVisualizer
              audioUrl={inputAudioUrl}
              segments={inputWaveformSegments}
              title="Original Input Vocals"
              type="input"
              height={150}
            />
          )}

          {/* Reference Waveform */}
          {referenceAudioUrl && (
            <WaveformVisualizer
              audioUrl={referenceAudioUrl}
              segments={referenceWaveformSegments}
              title="Reference Track Structure"
              type="reference"
              height={150}
            />
          )}

          {/* Arranged Waveform */}
          {arrangedAudioUrl && (
            <WaveformVisualizer
              audioUrl={arrangedAudioUrl}
              segments={arrangedWaveformSegments}
              title="Temporally Aligned Result"
              type="arranged"
              height={200}
            />
          )}
        </div>
      ) : (
        /* Tabbed View */
        <div>
          {/* Tab Navigation */}
          <div className="flex border-b border-gray-700 mb-4">
            {inputAudioUrl && (
              <button
                onClick={() => setActiveTab('input')}
                className={`px-4 py-2 font-medium transition-colors ${
                  activeTab === 'input'
                    ? 'border-b-2 border-teal-400 text-teal-400'
                    : 'text-gray-400 hover:text-gray-300'
                }`}
              >
                🎤 Original Input ({inputSegments.length})
              </button>
            )}
            {referenceAudioUrl && (
              <button
                onClick={() => setActiveTab('reference')}
                className={`px-4 py-2 font-medium transition-colors ${
                  activeTab === 'reference'
                    ? 'border-b-2 border-blue-400 text-blue-400'
                    : 'text-gray-400 hover:text-gray-300'
                }`}
              >
                🎵 Reference ({referenceSegments.length})
              </button>
            )}
            {arrangedAudioUrl && (
              <button
                onClick={() => setActiveTab('arranged')}
                className={`px-4 py-2 font-medium transition-colors ${
                  activeTab === 'arranged'
                    ? 'border-b-2 border-purple-400 text-purple-400'
                    : 'text-gray-400 hover:text-gray-300'
                }`}
              >
                ⚡ Arranged ({arrangedSegments.length})
              </button>
            )}
          </div>

          {/* Tab Content */}
          <div>
            {activeTab === 'input' && inputAudioUrl && (
              <WaveformVisualizer
                audioUrl={inputAudioUrl}
                segments={inputWaveformSegments}
                title="Original Input Vocals"
                type="input"
                height={250}
              />
            )}
            {activeTab === 'reference' && referenceAudioUrl && (
              <WaveformVisualizer
                audioUrl={referenceAudioUrl}
                segments={referenceWaveformSegments}
                title="Reference Track Structure"
                type="reference"
                height={250}
              />
            )}
            {activeTab === 'arranged' && arrangedAudioUrl && (
              <WaveformVisualizer
                audioUrl={arrangedAudioUrl}
                segments={arrangedWaveformSegments}
                title="Temporally Aligned Result"
                type="arranged"
                height={250}
              />
            )}
          </div>
        </div>
      )}

      {/* Segment Movement Analysis */}
      {renderSegmentMovementTable()}

      {/* Technical Info */}
      <div className="text-xs text-gray-500 bg-gray-800/50 p-3 rounded">
        <div className="font-medium mb-1">Visualization Guide:</div>
        <div>• Each colored segment represents a vocal phrase with consistent coloring across views</div>
        <div>• Numbers show original positions - track how segments moved from input to arranged</div>
        <div>• Red playhead shows current playback position (click waveform to seek)</div>
        <div>• Silence segments (—) represent gaps filled during temporal alignment</div>
        <div>• Checkmarks (✓) indicate successfully matched segments in the arranged output</div>
      </div>
    </div>
  );
}