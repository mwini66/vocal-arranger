import json
import os

LOG_PATH = "data/alignment_log.json"

if not os.path.exists(LOG_PATH):
    print("No alignment log found.")
    exit()

with open(LOG_PATH, "r") as f:
    try:
        log = json.load(f)
    except json.JSONDecodeError:
        print("Log file is empty or corrupted.")
        exit()

print("Last alignment run:")
print("-" * 40)
print(f"Timestamp: {log.get('timestamp', 'N/A')}")
print(f"Offset Samples: {log.get('offset_samples', 'N/A')}")
print(f"Offset Seconds: {log.get('offset_seconds', 'N/A'):.4f}")
print(f"Tempo Vocal: {log.get('tempo_vocal', 'N/A'):.2f}")
print(f"Tempo Instrumental: {log.get('tempo_instrumental', 'N/A'):.2f}")
print(f"Output File: {log.get('output_file', 'N/A')}")
