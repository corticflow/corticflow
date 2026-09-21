import feedparser
import json
import os
import time
import base64
import requests
import google.generativeai as genai
import random
from datetime import datetime, timedelta
import re
import urllib.parse

RSS_FEEDS = {
    "Google Blog": "https://blog.google/rss/",
    "Nvidia News": "https://nvidianews.nvidia.com/releases.xml",
    "Apple Newsroom": "https://www.apple.com/newsroom/rss-feed.rss",
    "OpenAI Blog": "https://openai.com/blog/rss.xml",
    "Anthropic News": "https://www.anthropic.com/news.rss",
    "DeepSeek Blog": "https://blog.deepseek.com/rss/",
    "MIT Tech Review": "https://www.technologyreview.com/feed/",
    "TechCrunch": "https://techcrunch.com/feed/",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "X | @OpenAI": "https://openrss.org/twitter.com/OpenAI",
    "X | @AnthropicAI": "https://openrss.org/twitter.com/AnthropicAI",
    "X | @deepseek_ai": "https://openrss.org/twitter.com/deepseek_ai",
    "X | @GoogleDeepMind": "https://openrss.org/twitter.com/GoogleDeepMind",
    "X | @NVIDIAAI": "https://openrss.org/twitter.com/NVIDIAAI"
}

def slugify(text):
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    return re.sub(r'[-\s]+', '-', text)[:45]

def get_ai_image_url(image_prompt):
    clean_p = re.sub(r'[^\w\s,.-]', '', image_prompt)[:160]
    encoded = urllib.parse.quote(f"{clean_p}, 16:9 panoramic view, cinematic lighting, photorealistic technology, dark slate cyan violet, 8k")
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&nologo=true&model=flux"

def generate_bilingual_post(model, source_name, original_title, original_summary):
    is_x = "X |" in source_name
    prompt = f"""
Atue como Editor-Chefe da plataforma CorticFlow.
Sua missão é produzir DUAS versões completas e independentes desta notícia:
1. UMA VERSÃO 100% EM PORTUGUÊS DO BRASIL (PT-BR) para os campos _pt. PROIBIDO deixar qualquer palavra em inglês em title_pt, excerpt_pt ou content_pt.
2. UMA VERSÃO 100% EM INGLÊS (EN-US) para os campos _en.
3. Um prompt em inglês (image_concept_prompt) descrevendo o elemento central da tecnologia em 16:9 para um gerador de arte por IA.

Notícia:
Fonte: {source_name}
Título Original: {original_title}
Resumo: {original_summary}
Tipo: {"Post do X (Twitter) — contextualize tecnicamente" if is_x else "Artigo de Imprensa"}

Retorne ESTRITAMENTE um objeto JSON válido:
{{
  "title_pt": "Título jornalístico 100% em Português",
  "title_en": "Journalistic headline 100% in English",
  "excerpt_pt": "Resumo de 2 a 3 frases 100% em Português.",
  "excerpt_en": "Executive summary of 2 to 3 sentences 100% in English.",
  "content_pt": "Análise técnica de 2 a 3 parágrafos aprofundados 100% em Português.",
  "content_en": "In-depth technical analysis of 2 to 3 paragraphs 100% in English.",
  "image_concept_prompt": "Cinematic 16:9 visual concept prompt in English describing the principal technical element"
}}
"""
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json", "temperature": 0.2}
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except Exception as e:
        print(f"Erro Gemini ({source_name}): {e}")
        return {
            "title_pt": f"Análise: {original_title}",
            "title_en": original_title,
            "excerpt_pt": (original_summary or original_title)[:160] + "...",
            "excerpt_en": (original_summary or original_title)[:160] + "...",
            "content_pt": original_summary or original_title,
            "content_en": original_summary or original_title,
            "image_concept_prompt": f"Advanced artificial intelligence system {original_title}"
        }

def main():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("GEMINI_API_KEY não configurada.")
            return

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        all_entries = []
        for source_name, url in RSS_FEEDS.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:
                    all_entries.append((source_name, entry))
            except Exception as e:
                print(f"Feed {source_name}: {e}")

        if not all_entries:
            print("Nenhum feed disponível.")
            return

        random.shuffle(all_entries)
        selected_entries = all_entries[:9]
        processed = []

        for i, (source, entry) in enumerate(selected_entries):
            title = entry.get('title', 'Tecnologia em Foco')
            summary = entry.get('summary', entry.get('description', ''))
            link = entry.get('link', '')

            print(f"[{i+1}/{len(selected_entries)}] Processando: {title[:40]}...")
            post_data = generate_bilingual_post(model, source, title, summary)

            img_prompt = post_data.get("image_concept_prompt", f"Technology system {title}")
            ai_image_url = get_ai_image_url(img_prompt)

            processed.append({
                "id": i + 1,
                "source": source,
                "link": link,
                "image": ai_image_url,
                "title_pt": post_data.get("title_pt", title),
                "title_en": post_data.get("title_en", title),
                "excerpt_pt": post_data.get("excerpt_pt", summary[:160]),
                "excerpt_en": post_data.get("excerpt_en", summary[:160]),
                "content_pt": post_data.get("content_pt", summary),
                "content_en": post_data.get("content_en", summary)
            })
            time.sleep(1.2)

        if processed:
            with open("posts.json", "w", encoding="utf-8") as f:
                json.dump(processed, f, ensure_ascii=False, indent=4)
            print(f"Sucesso: {len(processed)} matérias salvas com imagens dedicadas de IA!")

    except Exception as e:
        print(f"Erro geral: {e}")

if __name__ == "__main__":
    main()
