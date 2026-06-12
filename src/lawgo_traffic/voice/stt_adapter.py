from lawgo_traffic.config import settings


class STTAdapter:
    """Speech-to-Text interface. Default stub returns empty string."""

    def transcribe(self, audio_bytes: bytes, language: str = "vi") -> str:
        if not settings.voice_enabled:
            return ""
        # TODO: implement PhoWhisper transcription
        raise NotImplementedError
