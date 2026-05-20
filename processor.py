import os
import json
import logging
import anthropic

logger = logging.getLogger(__name__)

def extraer_recomendacion(texto_usuario: str) -> dict | None:
    """Usa Claude para analizar el texto enviado por el usuario y extraer la recomendación."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = f"""Analizá el siguiente texto enviado por un usuario y determiná si menciona o recomienda un libro, película o serie. 
Extrae el título correcto de la obra, clasificala y haz un breve resumen o descripción basado en lo que dice el usuario o en tu propio conocimiento si el texto es muy corto.

TEXTO DEL USUARIO:
{texto_usuario}

Respondé SOLO con un JSON válido con este formato exacto:
{{
  "titulo": "Nombre exacto del libro/película/serie",
  "categoria": "libro" | "película" | "serie",
  "descripcion": "Breve reseña o de qué trata, en 1-2 oraciones cortas y concretas"
}}

Si el texto NO habla de ninguna recomendación de libro, película o serie, respondé exactamente: null"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )

        texto_respuesta = message.content[0].text.strip()
        if texto_respuesta.lower() == "null":
            return None

        # Limpiar posibles bloques de código markdown que meta la IA
        texto_respuesta = texto_respuesta.replace("```json", "").replace("```", "").strip()
        return json.loads(texto_respuesta)
    except Exception as e:
        logger.error(f"Error al conectar con Claude: {e}")
        return None

def procesar_video(texto: str) -> dict | None:
    """Mantiene la estructura original pero procesa el texto directamente."""
    logger.info(f"Procesando texto: {texto[:50]}...")
    return extraer_recomendacion(texto)
