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
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-pro"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

FEEDS = [
    {"url": "https://tecnoblog.net/feed/", "category": "Mercado & Big Techs", "fallback_img": "cat-business.jpeg"},
    {"url": "https://olhardigital.com.br/feed/", "category": "Android & Gadgets", "fallback_img": "cat-tutorials.jpeg"},
    {"url": "https://mittechreview.com.br/feed/", "category": "AI & Models", "fallback_img": "cat-ai.jpeg"},
    {"url": "https://canaltech.com.br/rss/", "category": "Windows & PC", "fallback_img": "cat-tutorials.jpeg"},
    {"url": "https://venturebeat.com/category/ai/feed/", "category": "AI & Models", "fallback_img": "cat-ai.jpeg"},
    {"url": "https://thedecoder.com/feed/", "category": "AI & Models", "fallback_img": "cat-ai.jpeg"},
    {"url": "https://www.windowscentral.com/rss.xml", "category": "Windows & PC", "fallback_img": "cat-tutorials.jpeg"},
    {"url": "https://www.phoronix.com/phoronix-rss.php", "category": "Linux & Open-Source", "fallback_img": "cat-tools.jpeg"},
    {"url": "https://www.omgubuntu.co.uk/feed", "category": "Linux & Open-Source", "fallback_img": "cat-tools.jpeg"},
    {"url": "https://9to5mac.com/feed/", "category": "Apple & iOS", "fallback_img": "cat-business.jpeg"},
    {"url": "https://9to5google.com/feed/", "category": "Android & Gadgets", "fallback_img": "cat-tutorials.jpeg"},
    {"url": "https://www.theverge.com/rss/index.xml", "category": "Mercado & Big Techs", "fallback_img": "cat-business.jpeg"},
    {"url": "https://techcrunch.com/feed/", "category": "Mercado & Big Techs", "fallback_img": "cat-business.jpeg"},
    {"url": "https://feeds.arstechnica.com/arstechnica/index", "category": "Science & Space", "fallback_img": "cat-tutorials.jpeg"}
]

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
                        "summary": summary_clean[:500],
                        "category": item["category"],
                        "fallback_img": item["fallback_img"]
                    })
        except Exception as e:
            print(f"Aviso no feed {url}: {e}")
    return articles[:8]

def gerar_capa_ia(titulo, categoria, seed_num):
    prompt_visual = f"Futuristic technology visual of {titulo}, {categoria}, dark slate background, glowing neon cyan and purple accents, high tech concept art, 8k resolution, cinematic 16:9"
    encoded = urllib.parse.quote(prompt_visual[:200])
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1200&height=630&nologo=true&seed={seed_num}&model=flux"

def call_gemini_api(prompt):
    if not API_KEY or not API_KEY.startswith("AIzaSy"):
        return None

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.7,
            "maxOutputTokens": 8192
        }
    }

    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
        try:
            res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
            if res.status_code == 200:
                result = res.json()
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                clean_text = re.sub(r'^```json\s*', '', raw_text)
                clean_text = re.sub(r'^```\s*', '', clean_text)
                clean_text = re.sub(r'\s*```$', '', clean_text)
                return json.loads(clean_text)
        except Exception as e:
            print(f"Erro em {model}: {e}")
    return None

def generate_bilingual_post(news_item):
    prompt = f"""
    You are the Senior Editorial Director for 'CorticFlow', an authoritative technology publication.
    Based on this news:
    - Title: {news_item['title']}
    - Source: {news_item['link']}
    - Summary: {news_item['summary']}

    Write an article (800+ words) in TWO languages: English and Portuguese.
    Category: "{news_item['category']}".
    Return as JSON with keys: "slug", "category", "title_en", "content_en", "title_pt", "content_pt".
    """
    data = call_gemini_api(prompt)
    
    if not data:
        slug_gen = re.sub(r'[^a-zA-Z0-9]+', '-', news_item['title'].lower()).strip('-')[:50]
        data = {
            "slug": slug_gen,
            "category": news_item["category"],
            "title_en": news_item["title"],
            "content_en": f"## Overview\n\n{news_item['summary']}\n\n### Impact & Analysis\n\nThis development in {news_item['category']} marks a significant advancement in modern technology.\n\n*Original source: [{news_item['link']}]({news_item['link']})*",
            "title_pt": news_item["title"],
            "content_pt": f"## Visão Geral\n\n{news_item['summary']}\n\n### Análise de Impacto e Engenharia\n\nEste anúncio em {news_item['category']} traz desdobramentos importantes para o ecossistema tecnológico global.\n\n*Fonte original: [{news_item['link']}]({news_item['link']})*"
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
    read_time = f"{max(1, math.ceil(words_pt / 200))} min"
    category = data.get("category", news_item.get("category", "Geral"))
    title_final = data.get("title_pt") or data.get("title_en") or news_item["title"]
    
    desc_raw = data.get("content_pt") or news_item["summary"]
    desc_clean = re.sub(r'[#*_`]', '', desc_raw).strip()
    desc_final = desc_clean[:160] + "..." if len(desc_clean) > 160 else desc_clean

    cover_image = gerar_capa_ia(title_final, category, idx + 1)

    # Preenche rigorosamente TODOS os nomes de campos para zerar o undefined
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
        "tempo": read_time,
        "image": cover_image,
        "img": cover_image,
        "cover": cover_image,
        "imagem": cover_image,
        "desc": desc_final,
        "description": desc_final,
        "descricao": desc_final,
        "resumo": desc_final,
        "subtitulo": desc_final,
        "subtitle": desc_final,
        "snippet": desc_final,
        "summary": desc_final,
        "content": data.get("content_pt", ""),
        "content_pt": data.get("content_pt", ""),
        "content_en": data.get("content_en", ""),
        "link": news_item["link"],
        "fonte": news_item["link"],
        "file_pt": pt_file,
        "file_en": en_file
    })

    print(f"📁 [{idx+1}] Post salvo: {title_final}")

if __name__ == "__main__":
    os.makedirs("content/en", exist_ok=True)
    os.makedirs("content/pt", exist_ok=True)

    print("🚀 CorticFlow Bot: Gerando matérias e capas dinâmicas...")
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

    print(f"🎉 Finalizado com sucesso! {len(all_posts_manifest)} matérias com títulos e capas geradas.")
