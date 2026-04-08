"""
Speech-to-Text moduli
=====================
Google Speech Recognition (bepul) yordamida ovozli habarni tekstga aylantiradi.
ffmpeg orqali OGG → WAV konvertatsiya.
"""

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def transcribe_voice(ogg_path: str, language: str = "uz-UZ") -> str:
    """
    Ovozli faylni tekstga aylantiradi.
    
    Args:
        ogg_path: Telegram'dan kelgan OGG fayl yo'li
        language: Til kodi ("uz-UZ" = o'zbek, "ru-RU" = rus)
    
    Returns:
        Transkripsiya qilingan tekst
    """
    wav_path = ogg_path.replace(".ogg", ".wav")

    try:
        # 1) OGG → WAV konvertatsiya
        await _convert_ogg_to_wav(ogg_path, wav_path)

        # 2) Google STT
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(
            None, _recognize_google, wav_path, language
        )
        return text.strip() if text else ""

    except Exception as e:
        logger.error(f"Transcription xatosi: {e}")
        raise
    finally:
        wav = Path(wav_path)
        if wav.exists():
            wav.unlink(missing_ok=True)


async def _convert_ogg_to_wav(ogg_path: str, wav_path: str):
    """OGG → WAV (ffmpeg kerak)"""
    cmd = [
        "ffmpeg", "-y",
        "-i", ogg_path,
        "-ar", "16000",
        "-ac", "1",
        "-sample_fmt", "s16",
        wav_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg xatosi: {stderr.decode()[:300]}")


def _recognize_google(wav_path: str, language: str) -> str:
    """Google Speech Recognition (bepul, internet orqali)"""
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True

    with sr.AudioFile(wav_path) as source:
        audio = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio, language=language)
        logger.info(f"STT natijasi ({language}): {text[:100]}...")
        return text
    except sr.UnknownValueError:
        logger.warning("Ovozli habar tushunarsiz")
        return ""
    except sr.RequestError as e:
        logger.error(f"Google STT xatosi: {e}")
        raise RuntimeError(f"Google STT xizmatiga ulanib bo'lmadi: {e}")
