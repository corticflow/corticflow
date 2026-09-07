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
    return re.sub(r'[-\s]+', '-', text)[:50]

def generate_ai_cover(api_key, image_prompt, output_path):
    """Gera capa 16:9 via Imagen 3 no Gemini API baseada no elemento principal da matéria"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    full_prompt = (
        f"{image_prompt}. Hyper-detailed, 8k resolution, cinematic lighting, photorealistic, "
        f"clean technological aesthetic, dark slate atmosphere with cyan and violet accents, "
        f"master composition, 16:9 panoramic view, professional editorial art, no text, no letters."
    )
    
    payload = {
        "instances": [{"prompt": full_prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": "16:9",
            "outputOptions": {"mimeType": "image/jpeg"}
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=50)
        if response.status_code == 200:
            result = response.json()
            predictions = result.get("predictions", [])
            if predictions and "bytesBase64Encoded" in predictions[0]:
                image_bytes = base64.b64decode(predictions[0]["bytesBase64Encoded"])
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as img_file:
                    img_file.write(image_bytes)
                print(f"[Imagen 3] Capa gerada: {output_path}")
                return True
        print(f"[Imagen 3] Aviso na geração: {response.status_code}")
    except Exception as e:
        print(f"[Imagen 3] Erro: {e}")
    
    return False

def generate_bilingual_post(model, source_name, original_title, original_summary):
    is_x_post = "X |" in source_name
    
    prompt = f"""
Atue como Editor-Chefe de Tecnologia da plataforma CorticFlow.
Analise a notícia abaixo e produza DUAS versões: uma em PORTUGUÊS (PT-BR) e uma em INGLÊS (EN-US).
Formule também um prompt em inglês para gerar uma imagem conceitual 16:9 focada no ELEMENTO PRINCIPAL da matéria (sem usar fotos prontas).

Fonte: {source_name}
Título: {original_title}
Resumo: {original_summary}
Origem: {"Post do X (Twitter)" if is_x_post else "Notícia Técnica"}

Retorne ESTRITAMENTE um objeto JSON com o seguinte schema:
{{
  "title_pt": "Título jornalístico em Português",
  "title_en": "Journalistic headline in English",
  "excerpt_pt": "Resumo executivo em Português (2 a 3 frases).",
  "excerpt_en": "Executive summary in English (2 to 3 sentences).",
  "content_pt": "Análise técnica em Português.",
  "content_en": "Deep technical analysis in English.",
  "image_concept_prompt": "Cinematic visual description in English of the core technical subject of this article for an AI image generator"
}}
"""
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text.strip())
    except Exception as e:
        print(f"Erro Gemini ({source_name}): {e}")
        return {
            "title_pt": original_title,
            "title_en": original_title,
            "excerpt_pt": original_summary[:160] + "...",
            "excerpt_en": original_summary[:160] + "...",
            "content_pt": original_summary,
            "content_en": original_summary,
            "image_concept_prompt": f"Advanced technology visual representing {original_title}"
        }

def main():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("GEMINI_API_KEY não configurada.")
            return

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        cutoff_date = datetime.now() - timedelta(hours=72)
        all_entries = []

        for source_name, url in RSS_FEEDS.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    published = entry.get('published_parsed')
                    if published:
                        dt_published = datetime(*published[:6])
                        if dt_published >= cutoff_date:
                            entry['source_name'] = source_name
                            all_entries.append(entry)
            except Exception as e:
                print(f"Erro em {source_name}: {e}")

        if not all_entries:
            print("Nenhum artigo recente encontrado.")
            return

        random.shuffle(all_entries)
        selected_entries = all_entries[:12]
        processed_posts = []
        os.makedirs("covers", exist_ok=True)

        for i, entry in enumerate(selected_entries):
            source = entry.get('source_name', 'Tech News')
            title = entry.get('title', 'Sem Título')
            summary = entry.get('summary', entry.get('description', ''))
            
            print(f"[{i+1}/{len(selected_entries)}] Processando: {title[:45]}...")
            post_data = generate_bilingual_post(model, source, title, summary)
            
            slug = slugify(post_data.get("title_en", title))
            cover_filename = f"covers/{slug}.jpg"
            
            image_prompt = post_data.get("image_concept_prompt", f"Advanced artificial intelligence for {title}")
            image_ok = generate_ai_cover(api_key, image_prompt, cover_filename)
            image_path = cover_filename if image_ok else "covers/default-ai.jpg"
            
            processed_posts.append({
                "id": i + 1,
                "source": source,
                "link": entry.get('link', ''),
                "image": image_path,
                "title_pt": post_data.get("title_pt", title),
                "title_en": post_data.get("title_en", title),
                "excerpt_pt": post_data.get("excerpt_pt", summary[:160]),
                "excerpt_en": post_data.get("excerpt_en", summary[:160]),
                "content_pt": post_data.get("content_pt", summary),
                "content_en": post_data.get("content_en", summary)
            })
            time.sleep(1)

        with open("posts.json", "w", encoding="utf-8") as f:
            json.dump(processed_posts, f, ensure_ascii=False, indent=4)

        print(f"Sucesso: {len(processed_posts)} posts com capas de IA salvos em posts.json!")

    except Exception as e:
        print(f"Erro Fatal: {e}")

if __name__ == "__main__":
    main()
