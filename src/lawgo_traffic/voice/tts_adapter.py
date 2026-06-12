from lawgo_traffic.config import settings


class TTSAdapter:
    """Text-to-Speech interface. Default stub returns empty bytes."""

    def synthesize(self, text: str, voice: str | None = None) -> bytes:
        if not settings.voice_enabled:
            return b""
        # TODO: implement Edge-TTS synthesis (vi-VN-HoaiMyNeural)
        raise NotImplementedError
