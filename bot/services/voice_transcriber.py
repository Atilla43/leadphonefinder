"""Транскрибация голосовых сообщений через Groq Whisper API."""

import logging
import os
from typing import Optional

import aiohttp

from bot.utils.config import settings

logger = logging.getLogger(__name__)


class VoiceTranscriber:
    """Транскрибирует аудио через Groq Whisper API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1/audio/transcriptions"

    async def transcribe(self, file_path: str) -> Optional[str]:
        """Транскрибирует аудиофайл. Возвращает текст или None."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            ) as session:
                data = aiohttp.FormData()
                data.add_field(
                    "file",
                    open(file_path, "rb"),
                    filename=os.path.basename(file_path),
                )
                data.add_field("model", "whisper-large-v3")
                data.add_field("language", "ru")

                headers = {"Authorization": f"Bearer {self.api_key}"}

                async with session.post(
                    self.base_url, headers=headers, data=data
                ) as response:
                    if response.status != 200:
                        error = await response.text()
                        logger.error(f"Groq Whisper error: {response.status} - {error}")
                        return None

                    result = await response.json()
                    text = result.get("text", "").strip()
                    if text:
                        logger.info(f"[VOICE] Transcribed: {text[:80]}")
                        return text
                    return None

        except Exception as e:
            logger.error(f"Voice transcription error: {e}")
            return None


_instance: Optional[VoiceTranscriber] = None


def get_voice_transcriber() -> Optional[VoiceTranscriber]:
    """Возвращает синглтон VoiceTranscriber или None если нет API ключа."""
    global _instance
    if _instance is None:
        key = settings.groq_api_key
        if key:
            _instance = VoiceTranscriber(api_key=key)
            logger.info("VoiceTranscriber initialized (Groq Whisper)")
    return _instance
