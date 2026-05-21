import os
import json
import logging
import anthropic

logger = logging.getLogger(__name__)


def agregar_por_nombre(title: str, category: str) -> dict:
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
