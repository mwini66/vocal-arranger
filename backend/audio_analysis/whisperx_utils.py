import librosa
import numpy as np
import torch
import whisperx


def transcribe_with_whisperx(audio_path, model_size="small", device=None, padding_ms=50):
    """
    Transcribe audio and return word-level timestamps using WhisperX with adaptive padding.
    Uses the 'small' model by default and int8 compute type for CPU compatibility.
    Forces English alignment model to avoid unsupported language errors.

    Args:
        audio_path: Path to audio file
        model_size: WhisperX model size
        device: Processing device
        padding_ms: Base padding in milliseconds (adaptive based on silence)
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    # Load WhisperX model and transcribe
    model = whisperx.load_model(model_size, device, compute_type="int8")
    result = model.transcribe(audio_path)

    # Force English align model
    model_a, metadata = whisperx.load_align_model(language_code="en", device=device)
    result_aligned = whisperx.align(result["segments"], model_a, metadata, audio_path, device)

    # Apply adaptive padding to segments
    padded_segments = _apply_adaptive_padding(
        result_aligned["word_segments"],
        audio_path,
        padding_ms
    )

    return padded_segments


def _apply_adaptive_padding(segments, audio_path, base_padding_ms=50):
    """
    Apply adaptive padding to segments based on available silence between them.

    Args:
        segments: Original WhisperX segments
        audio_path: Path to audio file for silence analysis
        base_padding_ms: Base padding in milliseconds

    Returns:
        List of segments with adaptive padding applied
    """
    if not segments:
        return segments

    # Load audio for silence analysis
    try:
        audio, sr = librosa.load(audio_path, sr=None)
        total_duration = len(audio) / sr
    except Exception as e:
        print(f"Warning: Could not load audio for padding analysis: {e}")
        return segments  # Return original segments if audio loading fails

    # Convert base padding to seconds
    base_padding_s = base_padding_ms / 1000.0

    padded_segments = []

    for i, segment in enumerate(segments):
        start = segment.get('start', 0)
        end = segment.get('end', 0)

        # Calculate available space before and after segment
        prev_end = segments[i - 1].get('end', 0) if i > 0 else 0
        next_start = segments[i + 1].get('start', total_duration) if i < len(segments) - 1 else total_duration

        # Calculate adaptive padding based on available silence
        available_before = start - prev_end
        available_after = next_start - end

        # Adaptive padding strategy:
        # - Use base padding if there's enough silence
        # - Use half available silence if space is limited
        # - Minimum 10ms padding for audio quality
        min_padding_s = 0.01  # 10ms minimum
        max_padding_s = base_padding_s * 2  # Don't exceed 2x base padding

        # Calculate actual padding
        padding_before = min(
            max_padding_s,
            max(min_padding_s, min(base_padding_s, available_before * 0.5))
        )

        padding_after = min(
            max_padding_s,
            max(min_padding_s, min(base_padding_s, available_after * 0.5))
        )

        # Apply padding while respecting boundaries
        padded_start = max(0, start - padding_before)
        padded_end = min(total_duration, end + padding_after)

        # Ensure we don't overlap with adjacent segments
        if i > 0:
            padded_start = max(padded_start, segments[i - 1].get('end', 0))
        if i < len(segments) - 1:
            padded_end = min(padded_end, segments[i + 1].get('start', total_duration))

        # Create padded segment
        padded_segment = segment.copy()
        padded_segment['start'] = padded_start
        padded_segment['end'] = padded_end

        # Store original timing for reference
        padded_segment['original_start'] = start
        padded_segment['original_end'] = end
        padded_segment['padding_applied'] = {
            'before_ms': (start - padded_start) * 1000,
            'after_ms': (padded_end - end) * 1000
        }

        padded_segments.append(padded_segment)

    # Log padding statistics
    total_padding_ms = sum([
        seg['padding_applied']['before_ms'] + seg['padding_applied']['after_ms']
        for seg in padded_segments
    ])
    avg_padding_ms = total_padding_ms / len(padded_segments) if padded_segments else 0

    print(f"Applied adaptive padding: {avg_padding_ms:.1f}ms average per segment")

    return padded_segments


def _detect_speech_boundaries(audio, sr, start_time, end_time, threshold_db=-40):
    """
    Detect natural speech boundaries (voice onset/offset) for more precise padding.

    Args:
        audio: Audio signal
        sr: Sample rate
        start_time: Segment start time in seconds
        end_time: Segment end time in seconds
        threshold_db: Energy threshold for speech detection

    Returns:
        Tuple of (adjusted_start, adjusted_end) with natural boundaries
    """
    # Convert times to samples
    start_sample = int(start_time * sr)
    end_sample = int(end_time * sr)

    # Get audio segment with padding for analysis
    analysis_padding = int(0.1 * sr)  # 100ms padding for analysis
    analysis_start = max(0, start_sample - analysis_padding)
    analysis_end = min(len(audio), end_sample + analysis_padding)

    segment_audio = audio[analysis_start:analysis_end]

    if len(segment_audio) == 0:
        return start_time, end_time

    # Calculate frame-based energy (RMS)
    frame_length = int(0.025 * sr)  # 25ms frames
    hop_length = int(0.010 * sr)  # 10ms hop

    try:
        # Calculate RMS energy
        rms = librosa.feature.rms(
            y=segment_audio,
            frame_length=frame_length,
            hop_length=hop_length
        )[0]

        # Convert to dB
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)

        # Find speech boundaries
        speech_frames = rms_db > threshold_db

        if not np.any(speech_frames):
            return start_time, end_time

        # Find first and last speech frames
        first_speech = np.argmax(speech_frames)
        last_speech = len(speech_frames) - 1 - np.argmax(speech_frames[::-1])

        # Convert back to time
        first_speech_time = analysis_start / sr + (first_speech * hop_length) / sr
        last_speech_time = analysis_start / sr + (last_speech * hop_length) / sr

        # Extend slightly beyond detected boundaries for natural sound
        boundary_padding = 0.02  # 20ms boundary padding

        adjusted_start = max(start_time - 0.05, first_speech_time - boundary_padding)
        adjusted_end = min(end_time + 0.05, last_speech_time + boundary_padding)

        return adjusted_start, adjusted_end

    except Exception as e:
        print(f"Warning: Speech boundary detection failed: {e}")
        return start_time, end_time
