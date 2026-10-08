import feedparser
import json
import os
import time
import base64
import requests
import google.generativeai as genai
import random
from datetime import datetime, timezone
import re
import urllib.parse

RSS_FEEDS = {
    "Google DeepMind": "https://blog.google/technology/ai/rss/",
    "Nvidia Newsroom": "https://nvidianews.nvidia.com/releases.xml",
    "OpenAI Blog": "https://openai.com/blog/rss.xml",
    "Anthropic Research": "https://www.anthropic.com/news.rss",
    "DeepSeek Updates": "https://blog.deepseek.com/rss/",
    "MIT Tech Review": "https://www.technologyreview.com/feed/",
    "Ars Technica Tech": "https://feeds.arstechnica.com/arstechnica/index"
}

def slugify(text):
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    return re.sub(r'[-\s]+', '-', text)[:45]

def generate_ai_cover(api_key, image_prompt, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 1. Tentativa via Google Imagen 3 / Nano Banana 2 (Gemini API)
    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={api_key}"
            payload = {
                "instances": [{"prompt": f"{image_prompt}, 16:9 panoramic view, cinematic lighting, 8k resolution, photorealistic technology, dark slate aesthetic"}],
                "parameters": {"sampleCount": 1, "aspectRatio": "16:9", "outputOptions": {"mimeType": "image/jpeg"}}
            }
            res = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=25)
            if res.status_code == 200:
                data = res.json()
                if "predictions" in data and "bytesBase64Encoded" in data["predictions"][0]:
                    with open(output_path, "wb") as f:
                        f.write(base64.b64decode(data["predictions"][0]["bytesBase64Encoded"]))
                    print(f"[Imagen 3 / Nano Banana] Capa gerada com sucesso: {output_path}")
                    return True
        except Exception as e:
            print(f"[Imagen 3] Falha na chamada da API: {e}")

    # 2. Fallback Neural de Alta Resolução 16:9 (Flux AI)
    try:
        clean_p = re.sub(r'[^\w\s,.-]', '', image_prompt)[:200]
        encoded = urllib.parse.quote(f"Cinematic editorial photograph of {clean_p}, 16:9 aspect ratio, dramatic atmospheric lighting, photorealistic tech journalism cover style, 8k")
        poll_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&nologo=true&model=flux"
        img_res = requests.get(poll_url, timeout=30)
        if img_res.status_code == 200 and len(img_res.content) > 5000:
            with open(output_path, "wb") as f:
                f.write(img_res.content)
            print(f"[IA Neural] Capa 16:9 salva com sucesso: {output_path}")
            return True
    except Exception as e:
        print(f"[IA Neural] Erro na geração da capa: {e}")

    return False

def generate_bilingual_post(model, source_name, original_title, original_summary):
    prompt = f"""
Atue como Editor-Chefe Sênior da publicação internacional CorticFlow (especializada em IA, semicondutores e infraestrutura).
Produza DUAS versões completas e independentes desta notícia (PT-BR e EN-US) e um prompt visual cinematográfico:

Regras:
1. title_pt, excerpt_pt, content_pt 100% em Português do Brasil com profundidade jornalística.
2. title_en, excerpt_en, content_en 100% em Inglês Americano.
3. image_concept_prompt: Formule um prompt em inglês no estilo de fotografia editorial cinematográfica focado no elemento técnico central (ex: componentes de silício, usinas, robôs, circuitos, servidores brilhando no escuro), com 8k resolution, dramatic atmospheric lighting.

Notícia:
Fonte: {source_name}
Título: {original_title}
Resumo: {original_summary}

Retorne ESTRITAMENTE um objeto JSON válido:
{{
  "category": "semiconductors | ai-models | infrastructure | security | physical-ai",
  "tag_pt": "Nome da Categoria em Português",
  "tag_en": "Category Name in English",
  "title_pt": "Título jornalístico de impacto em Português",
  "title_en": "High-impact journalistic headline in English",
  "excerpt_pt": "Resumo analítico de 2 a 3 frases em Português.",
  "excerpt_en": "Analytical summary of 2 to 3 sentences in English.",
  "content_pt": "Análise técnica aprofundada de 3 a 5 parágrafos em Português.",
  "content_en": "In-depth technical analysis of 3 to 5 paragraphs in English.",
  "image_concept_prompt": "Cinematic, editorial photograph of [visual concept of core innovation], 8k resolution, photorealistic, dramatic atmospheric lighting, tech journalism cover style, 16:9 aspect ratio"
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
            "category": "ai-models",
            "tag_pt": "Tecnologia",
            "tag_en": "Technology",
            "title_pt": f"Análise: {original_title}",
            "title_en": original_title,
            "excerpt_pt": (original_summary or original_title)[:160] + "...",
            "excerpt_en": (original_summary or original_title)[:160] + "...",
            "content_pt": f"<p>{original_summary}</p>",
            "content_en": f"<p>{original_summary}</p>",
            "image_concept_prompt": f"Cinematic editorial photograph of advanced technological innovation representing {original_title}, 8k resolution, dramatic lighting"
        }

def main():
    try:
        os.makedirs("covers", exist_ok=True)
        with open("covers/.gitkeep", "w") as f:
            f.write("")

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("GEMINI_API_KEY não encontrada no ambiente.")
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
            print("Nenhum item de feed encontrado.")
            return

        random.shuffle(all_entries)
        selected_entries = all_entries[:6]
        processed = []

        now_utc = datetime.now(timezone.utc)
        date_pt_str = now_utc.strftime("%d Out %Y • %H:%M UTC")
        date_en_str = now_utc.strftime("%b %d, %Y • %H:%M UTC")

        for i, (source, entry) in enumerate(selected_entries):
            title = entry.get('title', 'Tecnologia de Fronteira')
            summary = entry.get('summary', entry.get('description', ''))
            link = entry.get('link', '')

            print(f"[{i+1}/{len(selected_entries)}] Analisando: {title[:40]}...")
            post_data = generate_bilingual_post(model, source, title, summary)

            slug = slugify(post_data.get("title_en", title))
            cover_file = f"covers/{slug}.jpg"
            img_prompt = post_data.get("image_concept_prompt", f"Advanced technology {title}")

            has_img = generate_ai_cover(api_key, img_prompt, cover_file)
            final_img = cover_file if has_img else "covers/default-ai.jpg"

            processed.append({
                "id": i + 1,
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
                "content_en": post_data.get("content_en", summary)
            })
            time.sleep(2)

        if processed:
            with open("posts.json", "w", encoding="utf-8") as f:
                json.dump(processed, f, ensure_ascii=False, indent=4)
            print(f"Sucesso: {len(processed)} matérias salvas em posts.json com capas de IA geradas!")

    except Exception as e:
        print(f"Erro na execução da esteira: {e}")

if __name__ == "__main__":
    main()

