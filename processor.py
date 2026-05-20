import os
import json
import tempfile
import logging
import yt_dlp
import whisper
import anthropic

logger = logging.getLogger(__name__)

# Cargamos el modelo de Whisper una sola vez (small = buen balance velocidad/precisión)
_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        logger.info("Cargando modelo Whisper...")
        _whisper_model = whisper.load_model("small")
    return _whisper_model


def descargar_audio(url: str, output_path: str) -> str:
    """Descarga el audio del video y lo guarda como MP3."""
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
    """Transcribe el audio usando Whisper."""
    model = get_whisper_model()
    result = model.transcribe(audio_path, language="es")
    return result["text"].strip()


def extraer_recomendacion(transcripcion: str) -> dict | None:
    """Usa Claude para extraer la recomendación de la transcripción."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = f"""Analizá esta transcripción de un video corto y determiná si recomienda un libro, película o serie.

TRANSCRIPCIÓN:
{transcripcion[:3000]}

Si hay una recomendación clara, respondé SOLO con un JSON válido con este formato exacto:
{{
  "titulo": "Nombre exacto del libro/película/serie",
  "categoria": "libro" | "película" | "serie",
  "descripcion": "Por qué lo recomiendan, en 1-2 oraciones cortas y concretas"
}}

Si NO hay una recomendación clara de libro/película/serie, respondé exactamente: null"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    texto = message.content[0].text.strip()
    if texto.lower() == "null":
        return None

    # Limpiar posibles backticks
    texto = texto.replace("```json", "").replace("```", "").strip()
    return json.loads(texto)


def procesar_video(url: str) -> dict | None:
    """Pipeline completo: descarga → transcribe → extrae recomendación."""
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_base = os.path.join(tmpdir, "audio")
        logger.info(f"Descargando: {url}")
        audio_path = descargar_audio(url, audio_base)

        logger.info("Transcribiendo...")
        transcripcion = transcribir_audio(audio_path)
        logger.info(f"Transcripción: {transcripcion[:100]}...")

        logger.info("Extrayendo recomendación...")
        resultado = extraer_recomendacion(transcripcion)
        logger.info(f"Resultado: {resultado}")

        return resultado
