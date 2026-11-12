import base64
from datetime import datetime, timezone
import json
import os
import random
import re
import time
import urllib.parse
import feedparser
import google.generativeai as genai
import requests

RSS_FEEDS = {
    "Google DeepMind": "https://blog.google/technology/ai/rss/",
    "Nvidia Newsroom": "https://nvidianews.nvidia.com/releases.xml",
    "OpenAI Blog": "https://openai.com/blog/rss.xml",
    "Anthropic Research": "https://www.anthropic.com/news.rss",
    "DeepSeek Updates": "https://blog.deepseek.com/rss/",
    "MIT Tech Review": "https://www.technologyreview.com/feed/",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Engadget": "https://www.engadget.com/rss.xml",
    "9to5Mac": "https://9to5mac.com/feed/",
}

POSTS_PER_RUN = 3  # 3 por hora (6h-22h) ≈ 45 a 50 matérias/notas por dia
MAX_ARCHIVE = 150


def slugify(text):
  text = re.sub(r"[^\w\s-]", "", text).strip().lower()
  return re.sub(r"[-\s]+", "-", text)[:45] or "post"


def load_existing_posts():
  if os.path.exists("posts.json"):
    try:
      with open("posts.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, list):
          return data
    except Exception as e:
      print(f"Aviso ao ler posts.json existente: {e}")
  return []


def generate_ai_cover(api_key, image_prompt, output_path):
  os.makedirs(os.path.dirname(output_path), exist_ok=True)

  if api_key:
    try:
      url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={api_key}"
      payload = {
          "instances": [{
              "prompt": (
                  f"{image_prompt}, 16:9 panoramic view, cinematic editorial"
                  " photography, 8k resolution, photorealistic technology,"
                  " dark slate aesthetic, no text"
              )
          }],
          "parameters": {
              "sampleCount": 1,
              "aspectRatio": "16:9",
              "outputOptions": {"mimeType": "image/jpeg"},
          },
      }
      res = requests.post(
          url,
          headers={"Content-Type": "application/json"},
          json=payload,
          timeout=30,
      )
      if res.status_code == 200:
        data = res.json()
        if (
            "predictions" in data
            and data["predictions"]
            and "bytesBase64Encoded" in data["predictions"][0]
        ):
          with open(output_path, "wb") as f:
            f.write(
                base64.b64decode(data["predictions"][0]["bytesBase64Encoded"])
            )
          print(f"[Imagen] Capa gerada: {output_path}")
          return True
    except Exception as e:
      print(f"[Imagen] Falha: {e}")

  try:
    clean_p = re.sub(r"[^\w\s,.-]", "", image_prompt)[:180]
    encoded = urllib.parse.quote(
        f"Cinematic editorial photograph of {clean_p}, 16:9 aspect ratio,"
        " dramatic atmospheric lighting, tech journalism cover, 8k, no text"
    )
    poll_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&nologo=true&model=flux"
    img_res = requests.get(poll_url, timeout=35)
    if img_res.status_code == 200 and len(img_res.content) > 5000:
      with open(output_path, "wb") as f:
        f.write(img_res.content)
      print(f"[Flux] Capa salva: {output_path}")
      return True
  except Exception as e:
    print(f"[Flux] Erro na capa: {e}")

  return False


def generate_bilingual_post(
    model, source_name, original_title, original_summary, is_quick_note=False
):
  style_instruction = (
      "Formato NOTA RÁPIDA (estilo Storystream): 1 a 2 parágrafos diretos e"
      " analíticos."
      if is_quick_note
      else (
          "Formato MATÉRIA ANALÍTICA COMPLETA: 3 a 5 parágrafos aprofundados"
          " sobre arquitetura, impacto de mercado e engenharia."
      )
  )

  prompt = f"""
Atue como Editor-Chefe Sênior da publicação internacional CorticFlow (especializada em IA, semicondutores, infraestrutura e tecnologia).
Reescreva esta pauta 100% DO ZERO com voz editorial própria e autoral, sem copiar frases ou estruturas dos portais originais.
{style_instruction}

Produza versões independentes em Português do Brasil (PT-BR) e Inglês Americano (EN-US), além de um prompt visual cinematográfico em inglês.

Pauta original:
Fonte: {source_name}
Título: {original_title}
Resumo: {original_summary}

Retorne ESTRITAMENTE um objeto JSON válido (sem markdown):
{{
  "category": "semiconductors | ai-models | infrastructure | security | physical-ai",
  "tag_pt": "Nome da Categoria em Português",
  "tag_en": "Category Name in English",
  "title_pt": "Título jornalístico autoral de impacto em Português",
  "title_en": "High-impact original journalistic headline in English",
  "excerpt_pt": "Resumo analítico de 2 frases em Português.",
  "excerpt_en": "Analytical 2-sentence summary in English.",
  "content_pt": "Texto completo em HTML simples (<p>...</p>) em Português.",
  "content_en": "Full text in simple HTML (<p>...</p>) in English.",
  "image_concept_prompt": "Cinematic editorial photograph of [visual concept of the core technology], 8k resolution, photorealistic, dramatic atmospheric lighting, no text"
}}
"""
  try:
    response = model.generate_content(
        prompt,
        generation_config={
            "response_mime_type": "application/json",
            "temperature": 0.35,
        },
    )
    raw = response.text.strip()
    if raw.startswith("```"):
      raw = re.sub(r"^```(?:json)?\s*", "", raw)
      raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)
  except Exception as e:
    print(f"Erro Gemini ({source_name}): {e}")
    return None


def main():
  api_key = os.getenv("GEMINI_API_KEY")
  if not api_key:
    print("GEMINI_API_KEY não encontrada.")
    return

  os.makedirs("covers", exist_ok=True)
  genai.configure(api_key=api_key)
  model = genai.GenerativeModel("gemini-1.5-flash")

  existing_posts = load_existing_posts()
  existing_links = {p.get("link") for p in existing_posts if p.get("link")}

  candidates = []
  for source_name, url in RSS_FEEDS.items():
    try:
      feed = feedparser.parse(url)
      for entry in feed.entries[:4]:
        link = entry.get("link", "")
        if link and link not in existing_links:
          candidates.append((source_name, entry))
    except Exception as e:
      print(f"Feed {source_name}: {e}")

  if not candidates:
    print("Nenhuma pauta inédita encontrada nesta rodada.")
    return

  random.shuffle(candidates)
  selected = candidates[:POSTS_PER_RUN]

  now_utc = datetime.now(timezone.utc)
  date_pt_str = now_utc.strftime("%d/%m/%Y • %H:%M UTC")
  date_en_str = now_utc.strftime("%b %d, %Y • %H:%M UTC")
  timestamp_id = int(now_utc.timestamp())

  new_posts = []
  for i, (source, entry) in enumerate(selected):
    title = entry.get("title", "Tecnologia de Fronteira")
    summary = entry.get("summary", entry.get("description", ""))
    link = entry.get("link", "")
    is_quick_note = i == POSTS_PER_RUN - 1  # Alterna análises densas e nota rápida

    print(f"[{i+1}/{len(selected)}] Reescrevendo: {title[:45]}...")
    post_data = generate_bilingual_post(
        model, source, title, summary, is_quick_note=is_quick_note
    )
    if not post_data:
      continue

    slug = slugify(post_data.get("title_en", title))
    cover_file = f"covers/{timestamp_id}-{slug}.jpg"
    img_prompt = post_data.get(
        "image_concept_prompt", f"Advanced technology representing {title}"
    )

    has_img = generate_ai_cover(api_key, img_prompt, cover_file)
    final_img = cover_file if has_img else "covers/default-ai.jpg"

    new_posts.append({
        "id": timestamp_id + i,
        "type": "note" if is_quick_note else "article",
        "source": source,
        "link": link,
        "image": final_img,
        "category": post_data.get("category", "ai-models"),
        "date_pt": date_pt_str,
        "date_en": date_en_str,
        "tag_pt": post_data.get("tag_pt", "Inovação"),
        "tag_en": post_data.get("tag_en", "Innovation"),
        "title_pt": post_data.get("title_pt", title),
        "title_en": post_data.get("title_en", title),
        "excerpt_pt": post_data.get("excerpt_pt", summary[:160]),
        "excerpt_en": post_data.get("excerpt_en", summary[:160]),
        "content_pt": post_data.get("content_pt", summary),
        "content_en": post_data.get("content_en", summary),
    })
    time.sleep(2)

  if new_posts:
    updated_posts = (new_posts + existing_posts)[:MAX_ARCHIVE]
    with open("posts.json", "w", encoding="utf-8") as f:
      json.dump(updated_posts, f, ensure_ascii=False, indent=4)
    print(f"Sucesso: {len(new_posts)} novas publicações adicionadas ao topo!")


if __name__ == "__main__":
  main()
