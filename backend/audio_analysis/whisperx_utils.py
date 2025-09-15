import whisperx
import torch

def transcribe_with_whisperx(audio_path, model_size="small", device=None):
    """
    Transcribe audio and return word-level timestamps using WhisperX.
    Uses the 'small' model by default and int8 compute type for CPU compatibility.
    Forces English alignment model to avoid unsupported language errors.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    model = whisperx.load_model(model_size, device, compute_type="int8")
    result = model.transcribe(audio_path)
    # Force English align model
    model_a, metadata = whisperx.load_align_model(language_code="en", device=device)
    result_aligned = whisperx.align(result["segments"], model_a, metadata, audio_path, device)
    return result_aligned["word_segments"]
