from elevenlabs.client import ElevenLabs
import os
import json
from pathlib import Path
from Listener import send_commands

BASE_DIR = Path(__file__).resolve().parent
try:
    with open(BASE_DIR / "API_KEYS.json", "r") as file:
        key = json.load(file)
        API_KEY = key["elevenlabs"]
except FileNotFoundError:
    print("Must create an API key file. Name file 'API_KEYS.json' with {'elevenlabs':APIKEY} inside.")

elevenlabs = ElevenLabs(
  api_key=API_KEY,
)

def create_speak_command(text:str):
    """
    Gathers raw text from an LLM input. Returns Mouth Anims/timings and Audio as 
    [
    {"type":"speak","syllables":data}, 
    {"type":"play","audio":data}
    ]
    """
    audio = elevenlabs.text_to_speech.convert_with_timestamps(
        text=text,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_multilingual_v2",
    )
    payload = process_audio(audio)

    return [{"type":"speak", "syllable":payload}, {"type":"play", "audio":audio["audio_base64"]}]


def process_audio(audio_data):
    alignment = audio_data["alignment"]

    syllables = characters_to_syllables(alignment["characters"])
    timings = timing_processing(
        alignment["character_start_times_seconds"],
        alignment["character_end_times_seconds"]
    )

    speak_pairs = merge_syllable_timings(syllables, timings)

    return speak_pairs

def characters_to_syllables(characters):
    """Convert ElevenLabs character alignment into mouth-shape names.

    This is a rough grapheme-to-viseme mapper. It only returns mouth shape
    names currently defined in dataLibrary/mouth_shapes.json:
    a, d, e, f, m, o, r, s, wo, neutral.
    """

    syllables = []
    char_to_shape = {
        "a": "a",
        "i": "a",
        "y": "e",
        "e": "e",
        "o": "o",
        "u": "wo",
        "w": "wo",
        "q": "wo",
        "b": "m",
        "m": "m",
        "p": "m",
        "f": "f",
        "v": "f",
        "c": "s",
        "s": "s",
        "x": "s",
        "z": "s",
        "d": "d",
        "g": "d",
        "j": "d",
        "k": "d",
        "l": "d",
        "n": "d",
        "t": "d",
        "h": "d",
        "r": "r",
    }


    for index, char in enumerate(characters):
        next_char = (
            characters[index + 1]
            if index + 1 < len(characters)
            else ""
        )

        if char == "w" and next_char in {"o", "u"}:
            syllables.append("wo")
            continue

        syllables.append(char_to_shape.get(char, "neutral"))

    return syllables

def timing_processing(start,end):
    timing_array = []
    for end_time, start_time in zip(end, start):
        timing_array.append(end_time - start_time)
    return timing_array

def merge_syllable_timings(syllables, timings, min_duration=0.05):
    merged = []

    for syllable, duration in zip(syllables, timings):
        if duration <= 0:
            continue

        if merged and merged[-1][0] == syllable:
            merged[-1][1] += duration
            continue

        if duration < min_duration and merged:
            merged[-1][1] += duration
            continue

        merged.append([syllable, duration])

    return merged