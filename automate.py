import os
import json
import datetime
import requests
import feedparser
import re
import math
import urllib.parse

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-1.5-flash"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 14 Feeds Oficiais de Tecnologia
FEEDS = [
    {"url": "https://tecnoblog.net/feed/", "category": "Mercado & Big Techs"},
    {"url": "https://olhardigital.com.br/feed/", "category": "Android & Gadgets"},
    {"url": "https://mittechreview.com.br/feed/", "category": "AI & Models"},
    {"url": "https://canaltech.com.br/rss/", "category": "Windows & PC"},
    {"url": "https://venturebeat.com/category/ai/feed/", "category": "AI & Models"},
    {"url": "https://thedecoder.com/feed/", "category": "AI & Models"},
    {"url": "https://www.windowscentral.com/rss.xml", "category": "Windows & PC"},
    {"url": "https://www.phoronix.com/phoronix-rss.php", "category": "Linux & Open-Source"},
    {"url": "https://www.omgubuntu.co.uk/feed", "category": "Linux & Open-Source"},
    {"url": "https://9to5mac.com/feed/", "category": "Apple & iOS"},
    {"url": "https://9to5google.com/feed/", "category": "Android & Gadgets"},
    {"url": "https://www.theverge.com/rss/index.xml", "category": "Mercado & Big Techs"},
    {"url": "https://techcrunch.com/feed/", "category": "Mercado & Big Techs"},
    {"url": "https://feeds.arstechnica.com/arstechnica/index", "category": "Science & Space"}
]

def gerar_url_imagem_ia(prompt_visual, titulo, categoria):
    """Gera uma imagem hiper-realista via IA baseada no prompt exato do Gemini."""
    if prompt_visual and len(prompt_visual.strip()) > 10:
        clean_prompt = prompt_visual.strip()
    else:
        clean_prompt = f"Futuristic high-tech cinematic photography of {titulo}, {categoria}, 8k, photorealistic, studio lighting, hyperdetailed"

    # Adiciona detalhes visuais para garantir aspecto de capa de revista tecnológica
    prompt_completo = f"{clean_prompt}, cinematic lighting, photorealistic, 8k resolution, technology magazine cover style"
    encoded_prompt = urllib.parse.quote(prompt_completo)
    
    # Gera imagem sob demanda em 1200x675 (proporção 16:9 widescreen para os cards)
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1200&height=675&nologo=true&enhance=true"

def fetch_latest_news():
    articles = []
    for item in FEEDS:
        url = item["url"]
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:2]:
                title = getattr(entry, 'title', '').strip()
                link = getattr(entry, 'link', '').strip()
                summary = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
                summary_clean = re.sub(r'<[^>]+>', '', summary).strip()
                
                if title and link and not any(a["title"] == title for a in articles):
                    articles.append({
                        "title": title,
                        "link": link,
                        "summary": summary_clean[:2000],
                        "category": item["category"],
                        "entry": entry
                    })
        except Exception as e:
            print(f"Aviso no feed {url}: {e}")
    return articles[:8]

def call_gemini_api(prompt):
    if not API_KEY or not API_KEY.startswith("AIzaSy"):
        return None

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.65,
            "maxOutputTokens": 8192
        }
    }

    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
        try:
            res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=65)
            if res.status_code == 200:
                result = res.json()
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                clean_text = re.sub(r'^```json\s*', '', raw_text)
                clean_text = re.sub(r'^```\s*', '', clean_text)
                clean_text = re.sub(r'\s*```$', '', clean_text)
                return json.loads(clean_text)
        except Exception as e:
            print(f"Tentando próximo modelo, erro em {model}: {e}")
    return None

def generate_bilingual_post(news_item):
    prompt = f"""
    You are the Senior Chief Editor and Principal Technology Analyst for 'CorticFlow' (an elite technology, AI, and systems engineering publication).
    
    Source Material:
    - Headline: {news_item['title']}
    - Source URL: {news_item['link']}
    - Raw Feed Context: {news_item['summary']}
    - Category: {news_item['category']}

    EDITORIAL GOAL:
    Write a definitive, exhaustive, masterclass technical essay (1,200+ words per language). The reader must NOT feel the need to visit the original source because your analysis is substantially more comprehensive, structured, and insightful.

    IMAGE PROMPT REQUIREMENT:
    In the JSON field "image_prompt", create an ultra-specific English visual prompt to generate an image via AI. 
    Examples:
    - If the news is about a Garmin smartwatch: "Close-up cinematic studio product photography of Garmin smartwatch with illuminated sapphire OLED display, metallic bezel, rugged texture, dark tech background, 8k"
    - If about Nvidia/Chips: "Photorealistic macro photography of Nvidia AI GPU die with golden traces, glowing neon blue data lines, circuit board, ultra detailed"
    - If about Big Techs/Google/Apple/Microsoft: "Futuristic corporate tech headquarters with glowing 3D logo of Google/Microsoft/Apple, dramatic architectural lighting, clean glass aesthetic"

    REQUIREMENTS FOR THE ESSAY (Provide in BOTH Portuguese and English):
    Use Markdown with clear, professional headers:
    1. ## O Cenário Estratégico / Executive Summary & Industry Context (Explain what happened, background context, and fundamental shift).
    2. ### Análise Técnica Profunda & Arquitetura / Technical Architecture & Specifications (Deep dive into specs, benchmarks, hardware parameters, code logic, or systems design).
    3. ### Impacto nos Ecossistemas & Concorrência / Ecosystem & Market Repercussions (How competitors, developer workflows, enterprise deployments, and open-source communities are affected).
    4. ### Implicações Práticas & O que Observar / Strategic Roadmaps & Future Horizons (Actionable insights for software engineers, tech leaders, and builders).
    5. ### Pontos Decisivos (Takeaways) / Core Technical Takeaways (Bulleted checklist of the absolute facts).

    Also generate:
    - card_desc_pt: A dense, authoritative 280-320 character summary in Portuguese for the preview card.
    - card_desc_en: A dense, authoritative 280-320 character summary in English.

    Return strictly valid JSON with keys:
    "slug", "category", "image_prompt", "title_pt", "content_pt", "card_desc_pt", "title_en", "content_en", "card_desc_en".
    """
    data = call_gemini_api(prompt)
    
    if not data:
        slug_gen = re.sub(r'[^a-zA-Z0-9]+', '-', news_item['title'].lower()).strip('-')[:50]
        desc_default = news_item['summary'][:300] + "..." if len(news_item['summary']) > 300 else news_item['summary']
        data = {
            "slug": slug_gen,
            "category": news_item["category"],
            "image_prompt": f"High-tech futuristic visual representation of {news_item['title']}, editorial tech magazine style, 8k",
            "title_en": news_item["title"],
            "card_desc_en": desc_default,
            "content_en": f"""## Executive Summary\n\n{news_item['summary']}\n\n### Architectural & Systems Analysis\n\nThis development marks a substantial evolution across the {news_item['category']} paradigm, establishing higher standards for performance, integration, and developer adoption.\n\n### Strategic Takeaways\n\n- High-impact progression in {news_item['category']}.\n- Long-term implications for computing and production workflows.\n\n*Original reference: [{news_item['link']}]({news_item['link']})*""",
            "title_pt": news_item["title"],
            "card_desc_pt": desc_default,
            "content_pt": f"""## Análise Editorial e Panorama Estratégico\n\n{news_item['summary']}\n\n### Engenharia, Arquitetura e Desempenho\n\nO anúncio traz mudanças estruturais significativas no segmento de {news_item['category']}, redefinindo benchmarks de eficiência, latência e escalabilidade técnica para o mercado global.\n\n### Pontos Decisivos\n\n- Marco determinante para o ecossistema de {news_item['category']}.\n- Impactos diretos na infraestrutura e na experiência do usuário final.\n\n*Referência original: [{news_item['link']}]({news_item['link']})*"""
        }
    return data

def save_posts(data, all_posts_manifest, news_item, idx):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    slug = data.get("slug", "tech-dispatch")
    slug_clean = re.sub(r'[^a-zA-Z0-9]+', '-', slug.lower()).strip('-')[:60]

    os.makedirs("content/en", exist_ok=True)
    os.makedirs("content/pt", exist_ok=True)

    en_file = f"content/en/{today}-{slug_clean}.md"
    with open(en_file, "w", encoding="utf-8") as f:
        f.write(f"---\ntitle: \"{data.get('title_en', '')}\"\ndate: \"{today}\"\ncategory: \"{data.get('category', 'General')}\"\n---\n\n")
        f.write(data.get("content_en", ""))

    pt_file = f"content/pt/{today}-{slug_clean}.md"
    with open(pt_file, "w", encoding="utf-8") as f:
        f.write(f"---\ntitle: \"{data.get('title_pt', '')}\"\ndata: \"{today}\"\ncategoria: \"{data.get('category', 'Geral')}\"\n---\n\n")
        f.write(data.get("content_pt", ""))

    words_pt = len(re.findall(r'\w+', data.get("content_pt", "")))
    read_time = f"{max(2, math.ceil(words_pt / 200))} min"
    category = data.get("category", news_item.get("category", "Geral"))
    title_final = data.get("title_pt") or data.get("title_en") or news_item["title"]
    
    desc_final = data.get("card_desc_pt")
    if not desc_final:
        desc_raw = data.get("content_pt") or news_item["summary"]
        desc_clean = re.sub(r'[#*_`]', '', desc_raw).strip()
        desc_final = desc_clean[:320] + "..." if len(desc_clean) > 320 else desc_clean

    # Gera a imagem IA personalizada diretamente para a matéria
    image_prompt = data.get("image_prompt", "")
    foto_gerada_ia = gerar_url_imagem_ia(image_prompt, title_final, category)

    all_posts_manifest.append({
        "id": idx + 1,
        "slug": slug_clean,
        "title": title_final,
        "titulo": title_final,
        "title_pt": title_final,
        "titulo_pt": title_final,
        "headline": title_final,
        "name": title_final,
        "title_en": data.get("title_en", title_final),
        "category": category,
        "categoria": category,
        "badge": category,
        "date": today,
        "data": today,
        "readTime": read_time,
        "read_time": read_time,
        "tempo_leitura": read_time,
        "image": foto_gerada_ia,
        "img": foto_gerada_ia,
        "cover": foto_gerada_ia,
        "imagem": foto_gerada_ia,
        "desc": desc_final,
        "description": desc_final,
        "descricao": desc_final,
        "resumo": desc_final,
        "content": data.get("content_pt", ""),
        "content_pt": data.get("content_pt", ""),
        "content_en": data.get("content_en", ""),
        "link": news_item["link"],
        "fonte": news_item["link"],
        "file_pt": pt_file,
        "file_en": en_file
    })

    print(f"🎨 [{idx+1}] Matéria Masterclass & Imagem IA Gerada: {title_final}")

if __name__ == "__main__":
    os.makedirs("content/en", exist_ok=True)
    os.makedirs("content/pt", exist_ok=True)

    print("🚀 CorticFlow Bot: Gerando matérias com Imagens IA hiper-específicas...")
    news = fetch_latest_news()
    all_posts_manifest = []

    for i, item in enumerate(news[:8]):
        try:
            post_data = generate_bilingual_post(item)
            if post_data and isinstance(post_data, dict):
                save_posts(post_data, all_posts_manifest, item, i)
        except Exception as e:
            print(f"Erro no item {i+1}: {e}")

    with open("posts.json", "w", encoding="utf-8") as f:
        json.dump(all_posts_manifest, f, ensure_ascii=False, indent=2)
    with open("content/posts.json", "w", encoding="utf-8") as f:
        json.dump(all_posts_manifest, f, ensure_ascii=False, indent=2)

    print(f"🎉 Finalizado com sucesso! {len(all_posts_manifest)} matérias e imagens IA geradas.")
