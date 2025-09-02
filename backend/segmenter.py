import librosa

def segment_track(audio_path):
    y, sr = librosa.load(audio_path)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    return {"tempo": tempo, "beats": beats.tolist()}
