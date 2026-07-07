import base64
import io
import pygame


class AudioPlayer:
    def __init__(self):
        self.enabled = True

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except pygame.error as exc:
            self.enabled = False
            print(f"AudioPlayer error: could not initialize pygame mixer: {exc}")

    def play_base64_audio(self, audio_base64: str):
        if not self.enabled:
            return

        if not audio_base64:
            print("AudioPlayer error: missing audio payload")
            return

        try:
            audio_bytes = base64.b64decode(audio_base64)

            audio_file = io.BytesIO(audio_bytes)
            pygame.mixer.music.load(audio_file, "mp3")
            pygame.mixer.music.play()
        except Exception as exc:
            print(f"AudioPlayer error: could not play audio: {exc}")

    def stfu(self):
        if self.enabled:
            pygame.mixer.music.stop()
