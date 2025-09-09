import sounddevice as sd
import wavio
import requests
import os

# --- CONFIG ---
AI_SERVER = "http://127.0.0.1:8000"
BUS_SERVER = "http://127.0.0.1:8001"
AUDIO_FILE = "temp_audio.wav"
OUTPUT_FILE = "response.wav"

# --- RECORD VOICE ---
def record_audio(duration=5, fs=44100):
    print(f"Recording for {duration} seconds... Speak now!")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()
    wavio.write(AUDIO_FILE, recording, fs, sampwidth=2)
    print(f"Saved your recording as {AUDIO_FILE}")

# --- SEND AUDIO TO AI ---
def get_text_from_audio(audio_file_path):
    with open(audio_file_path, "rb") as f:
        files = {"file": f}
        response = requests.post(f"{AI_SERVER}/process_audio", files=files)
    response.raise_for_status()
    data = response.json()
    return data.get("text", "")

# --- GET BUS INFO ---
def get_bus_info(user_query):
    payload = {"query": user_query}
    response = requests.post(f"{BUS_SERVER}/businfo", json=payload)
    response.raise_for_status()
    return response.json()

# --- CONVERT TEXT TO SPEECH ---
def text_to_speech(text, output_file=OUTPUT_FILE):
    payload = {"text": text}
    response = requests.post(f"{AI_SERVER}/speak", json=payload)
    response.raise_for_status()
    with open(output_file, "wb") as f:
        f.write(response.content)
    print(f"Audio response saved to {output_file}")
    # Play the audio
    os.system(f"afplay {output_file}")

# --- MAIN WORKFLOW ---
if __name__ == "__main__":
    record_audio(duration=5)  # change duration if you need longer
    text_query = get_text_from_audio(AUDIO_FILE)
    print(f"You said: {text_query}")

    bus_response = get_bus_info(text_query)
    print(f"Bus info: {bus_response}")

    speech_text = bus_response.get("message", "Sorry, I could not find the bus info.")
    text_to_speech(speech_text)
