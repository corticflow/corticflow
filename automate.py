import feedparser
import json
import os
import time
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

def generate_bilingual_post(model, source_name, original_title, original_summary):
    is_x = "X |" in source_name
    prompt = f"""
Atue como Editor-Chefe da plataforma CorticFlow.
Sua missão é produzir DUAS versões analíticas desta notícia:
1. VERSÃO 100% EM PORTUGUÊS DO BRASIL (PT-BR) para os campos _pt. Não deixe palavras em inglês nos campos _pt.
2. VERSÃO 100% EM INGLÊS (EN-US) para os campos _en.
3. Prompt visual em inglês (image_concept_prompt) descrevendo o elemento central da tecnologia em 16:9.

Notícia:
Fonte: {source_name}
Título: {original_title}
Resumo: {original_summary}
Tipo: {"Post do X (Twitter)" if is_x else "Artigo de Imprensa"}

Retorne ESTRITAMENTE um objeto JSON válido (sem tags markdown):
{{
  "title_pt": "Título jornalístico 100% em Português",
  "title_en": "Journalistic headline 100% in English",
  "excerpt_pt": "Resumo de 2 a 3 frases 100% em Português.",
  "excerpt_en": "Executive summary of 2 to 3 sentences 100% in English.",
  "content_pt": "Análise técnica aprofundada de 2 a 3 parágrafos 100% em Português.",
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
        try:
            pt_trans = model.generate_content(f"Traduza e resuma em Português em 2 parágrafos: {original_title}. {original_summary}").text.strip()
        except:
            pt_trans = f"Análise técnica sobre {original_title} em processamento pelo núcleo CorticFlow."

        return {
            "title_pt": f"Análise: {original_title}",
            "title_en": original_title,
            "excerpt_pt": pt_trans[:160] + "...",
            "excerpt_en": (original_summary or original_title)[:160] + "...",
            "content_pt": pt_trans,
            "content_en": original_summary or original_title,
            "image_concept_prompt": f"Advanced technology representing {original_title}"
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
                for entry in feed.entries[:4]:
                    all_entries.append((source_name, entry))
            except Exception as e:
                print(f"Feed {source_name}: {e}")

        if not all_entries:
            print("Nenhum feed disponível.")
            return

        random.shuffle(all_entries)
        selected_entries = all_entries[:8]
        processed = []

        for i, (source, entry) in enumerate(selected_entries):
            title = entry.get('title', 'Tecnologia em Foco')
            summary = entry.get('summary', entry.get('description', ''))
            link = entry.get('link', '')

            print(f"[{i+1}/{len(selected_entries)}] Processando: {title[:35]}...")
            post_data = generate_bilingual_post(model, source, title, summary)

            img_prompt = post_data.get("image_concept_prompt", f"Advanced artificial intelligence system {title}")
            clean_p = re.sub(r'[^\w\s,.-]', '', img_prompt)[:160].strip()
            encoded_p = urllib.parse.quote(f"{clean_p}, 16:9 panoramic cinematic tech, photorealistic, 8k, dark slate cyan violet accents")
            
            # URL direta da imagem em alta resolução (1280x720) gerada por IA
            ai_image_url = f"[https://image.pollinations.ai/prompt/](https://image.pollinations.ai/prompt/){encoded_p}?width=1280&height=720&nologo=true&seed={i+42}&model=flux"

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
            print(f"Sucesso: {len(processed)} matérias salvas com imagens em posts.json!")

    except Exception as e:
        print(f"Erro geral: {e}")

if __name__ == "__main__":
    main()
