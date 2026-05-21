import os
import json
import tempfile
import logging
import yt_dlp
import whisper
import anthropic

logger = logging.getLogger(__name__)

_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        logger.info("Loading Whisper model...")
        _whisper_model = whisper.load_model("small")
    return _whisper_model


def descargar_audio(url: str, output_path: str) -> str:
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
        "quiet": True,
        "no_warnings": True,
        "cookiesfrombrowser": None,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_path + ".mp3"


def transcribir_audio(audio_path: str) -> str:
    model = get_whisper_model()
    result = model.transcribe(audio_path)
    return result["text"].strip()


def extraer_recomendacion(transcripcion: str) -> dict | None:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = f"""Analyze this transcript from a short video and determine if it recommends a book, movie, show, or anime.

TRANSCRIPT:
{transcripcion[:3000]}

If there is a clear recommendation, respond ONLY with a valid JSON in this exact format:
{{
  "title": "Exact name of the book/movie/show/anime",
  "category": "movie" | "book" | "show" | "anime",
  "description": "Why they recommend it in the video, 1-2 sentences",
  "synopsis": "Objective synopsis of the work in 2-3 sentences, no spoilers",
  "genre": "main genre (horror, drama, sci-fi, romance, thriller, comedy, fantasy, action, etc.) or null",
  "country": "country of origin or null",
  "year": release/publication year as integer or null,
  "director_author": "director if movie/show/anime, author if book, or null"
}}

If there is NO clear recommendation of a book/movie/show/anime, respond exactly: null"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    texto = message.content[0].text.strip()
    if texto.lower() == "null":
        return None

    texto = texto.replace("```json", "").replace("```", "").strip()
    return json.loads(texto)


def agregar_por_nombre(title: str, category: str) -> dict:
    """Generates a full entry from just a title and category."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = f"""Generate a complete entry for this work:

Title: {title}
Category: {category}

Respond ONLY with a valid JSON in this exact format:
{{
  "title": "Official/correct name of the work",
  "category": "{category}",
  "description": "Why it's worth it, 1-2 sentences with a hook",
  "synopsis": "Objective synopsis in 2-3 sentences, no spoilers",
  "genre": "main genre",
  "country": "country of origin",
  "year": year as integer,
  "director_author": "director or author"
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    texto = message.content[0].text.strip()
    texto = texto.replace("```json", "").replace("```", "").strip()
    return json.loads(texto)


def procesar_video(url: str) -> dict | None:
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_base = os.path.join(tmpdir, "audio")
        logger.info(f"Downloading: {url}")
        audio_path = descargar_audio(url, audio_base)

        logger.info("Transcribing...")
        transcripcion = transcribir_audio(audio_path)
        logger.info(f"Transcript: {transcripcion[:100]}...")

        logger.info("Extracting recommendation...")
        resultado = extraer_recomendacion(transcripcion)
        logger.info(f"Result: {resultado}")

        return resultado
