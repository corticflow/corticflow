

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

def generate_ai_cover(api_key, image_prompt, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 1. Tentativa via Imagen 3 (Gemini API)
    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={api_key}"
            payload = {
                "instances": [{"prompt": f"{image_prompt}. 16:9 panoramic view, cinematic lighting, 8k, photorealistic technology, dark slate"}],
                "parameters": {"sampleCount": 1, "aspectRatio": "16:9", "outputOptions": {"mimeType": "image/jpeg"}}
            }
            res = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=20)
            if res.status_code == 200:
                data = res.json()
                if "predictions" in data and "bytesBase64Encoded" in data["predictions"][0]:
                    with open(output_path, "wb") as f:
                        f.write(base64.b64decode(data["predictions"][0]["bytesBase64Encoded"]))
                    print(f"[Imagen 3] Capa gerada com sucesso: {output_path}")
                    return True
        except Exception as e:
            print(f"[Imagen 3] Falha na chamada: {e}")

    # 2. Gerador Neural Confiável de Alta Resolução 16:9 (Flux AI)
    try:
        clean_p = re.sub(r'[^\w\s,.-]', '', image_prompt)[:180]
        encoded = urllib.parse.quote(f"{clean_p}, 16:9 aspect ratio, cinematic lighting, photorealistic tech, dark slate cyan violet, 8k")
        poll_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&nologo=true&model=flux"
        img_res = requests.get(poll_url, timeout=30)
        if img_res.status_code == 200 and len(img_res.content) > 5000:
            with open(output_path, "wb") as f:
                f.write(img_res.content)
            print(f"[IA Neural] Capa 16:9 baixada e salva com sucesso: {output_path}")
            return True
    except Exception as e:
        print(f"[IA Neural] Erro na geração da capa: {e}")

    return False

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

Retorne ESTRITAMENTE um objeto JSON válido (sem tags markdown de código):
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
        data = json.loads(raw)
        return data
    except Exception as e:
        print(f"Erro Gemini ({source_name}): {e}")
        try:
            pt_trans = model.generate_content(f"Traduza e resuma em Português em 2 parágrafos: {original_title}. {original_summary}").text.strip()
        except:
            pt_trans = f"Análise técnica sobre {original_title} em processamento pelo núcleo da CorticFlow."

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
        os.makedirs("covers", exist_ok=True)
        with open("covers/.gitkeep", "w") as f:
            f.write("")

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

            print(f"[{i+1}/{len(selected_entries)}] Processando: {title[:40]}...")
            post_data = generate_bilingual_post(model, source, title, summary)

            slug = slugify(post_data.get("title_en", title))
            cover_file = f"covers/{slug}.jpg"
            img_prompt = post_data.get("image_concept_prompt", f"Technology system {title}")
            
            has_img = generate_ai_cover(api_key, img_prompt, cover_file)
            final_img = cover_file if has_img else "covers/default-ai.jpg"

            processed.append({
                "id": i + 1,
                "source": source,
                "link": link,
                "image": final_img,
                "title_pt": post_data.get("title_pt", title),
                "title_en": post_data.get("title_en", title),
                "excerpt_pt": post_data.get("excerpt_pt", summary[:160]),
                "excerpt_en": post_data.get("excerpt_en", summary[:160]),
                "content_pt": post_data.get("content_pt", summary),
                "content_en": post_data.get("content_en", summary)
            })
            time.sleep(1.5)

        if processed:
            with open("posts.json", "w", encoding="utf-8") as f:
                json.dump(processed, f, ensure_ascii=False, indent=4)
            print(f"Sucesso: {len(processed)} matérias salvas em posts.json com imagens de IA!")

    except Exception as e:
        print(f"Erro geral: {e}")

if __name__ == "__main__":
    main()

