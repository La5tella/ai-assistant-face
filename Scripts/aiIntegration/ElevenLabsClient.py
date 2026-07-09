import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def create_speak_command(text:str, debug:bool):
    """
    Gathers raw text from an LLM input. Returns Mouth Anims/timings and Audio as 
    [
    {"type":"speak","syllables":data}, 
    {"type":"play","audio":data}
    ]
    """
    if debug:
        audio = build_debug_audio()
    else:
        audio = normalize_audio_response(create_elevenlabs_audio(text))
    
    #payload = process_audio(audio)
    #alignment = audio["alignment"]
    #audio_span = (
    #    alignment["character_end_times_seconds"][-1]
    #    - alignment["character_start_times_seconds"][0]
    #)
#
    #payload_span = sum(item[2] for item in payload)
    #
    #print("audio_span", audio_span)
    #print("payload_span", payload_span)
    #print("payload_minus_audio", payload_span - audio_span)

    return [{"type":"speak", "syllables":payload}, {"type":"play", "audio":audio["audio_base64"]}]

def process_audio(audio_data):
    alignment = audio_data["alignment"]

    short_gap_limit = 0.12
    previous_extend_cap = 0.06

    neutral_total = 0.10
    neutral_transition = 0.04

    min_viseme_duration = 0.04

    char_to_shape = {
        "a": "a",
        "i": "a",
        "y": "e",
        "e": "e",
        "o": "o",
        "u": "o",
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

    merged = []

    def add_syllable(shape, transition_time, total_time):
        if total_time <= 0:
            return

        if merged and merged[-1][0] == shape:
            merged[-1][2] += total_time
            return

        if shape != "wait" and total_time < min_viseme_duration and merged:
            merged[-1][2] += total_time
            return

        merged.append([shape, transition_time, total_time])

    def add_pause(duration):
        if not merged:
            return

        if duration <= short_gap_limit:
            merged[-1][2] += min(duration, previous_extend_cap)

            leftover = duration - previous_extend_cap
            if leftover > 0:
                add_syllable("wait", 0.0, leftover)

            return

        visible_neutral = min(neutral_total, duration)
        add_syllable(
            "neutral",
            min(neutral_transition, visible_neutral),
            visible_neutral
        )

        leftover = duration - visible_neutral
        if leftover > 0:
            add_syllable("wait", 0.0, leftover)


    for character, start, end in zip(
        alignment["characters"],
        alignment["character_start_times_seconds"],
        alignment["character_end_times_seconds"]
    ):
        duration = end - start

        if duration <= 0:
            continue

        char = character.lower()

        if char.isalpha():
            shape = char_to_shape.get(char)

            if shape is not None:
                add_syllable(shape, duration, duration)
            else:
                add_pause(duration)

            continue

        add_pause(duration)

    return merged

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
        "u": "o",
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
    
    lowercased = [item.lower() for item in characters]
 
    for index, char in enumerate(lowercased):
        next_char = (
            lowercased[index + 1]
            if index + 1 < len(lowercased)
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
        transition_time = duration
        if duration <= 0:
            continue

        if merged and merged[-1][0] == syllable:
            merged[-1][2] += duration
            continue

        if duration < min_duration and merged:
            merged[-1][2] += duration
            continue

        total_time = duration
        merged.append([syllable, transition_time, total_time])

    return merged

def create_elevenlabs_audio(text: str):
    from elevenlabs.client import ElevenLabs

    api_key = load_api_key()
    client = ElevenLabs(api_key=api_key)

    return client.text_to_speech.convert_with_timestamps(
        text=text,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_multilingual_v2",
    )

def load_api_key() -> str:
    key_path = BASE_DIR / "API_KEYS.json"

    if not key_path.exists():
        raise FileNotFoundError(
            f"Missing ElevenLabs API key file: {key_path}. "
            "Create API_KEYS.json with {'elevenlabs': 'YOUR_KEY'}."
        )

    with open(key_path, "r") as file:
        data = json.load(file)

    try:
        api_key = data["elevenlabs"]
    except KeyError as exc:
        raise KeyError(
            f"Missing 'elevenlabs' key in {key_path}."
        ) from exc

    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError(
            f"'elevenlabs' in {key_path} must be a non-empty string."
        )

    return api_key

def build_debug_audio():
    return {
            "audio_base64": "base64_encoded_audio_string",
            "alignment": {
              "characters": [
                "H",
                "e",
                "l",
                "l",
                "o"
              ],
              "character_start_times_seconds": [
                0,
                0.1,
                0.2,
                0.3,
                0.4
              ],
              "character_end_times_seconds": [
                0.1,
                0.2,
                0.3,
                0.4,
                0.5
              ]
            },
            "normalized_alignment": {
              "characters": [
                "H",
                "e",
                "l",
                "l",
                "o"
              ],
              "character_start_times_seconds": [
                0,
                0.1,
                0.2,
                0.3,
                0.4
              ],
              "character_end_times_seconds": [
                0.1,
                0.2,
                0.3,
                0.4,
                0.5
              ]
            }
        }

def normalize_audio_response(audio):
    if isinstance(audio, dict):
        return audio

    return {
        "audio_base64": audio.audio_base_64,
        "alignment": {
            "characters": audio.alignment.characters,
            "character_start_times_seconds": audio.alignment.character_start_times_seconds,
            "character_end_times_seconds": audio.alignment.character_end_times_seconds,
        },
    }
