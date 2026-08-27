import os
import json
import datetime
import requests
import feedparser
import re
import math

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

MODELS = [
    "gemini-3.7-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Filtro rigoroso: Bloqueia cupons, promoções, futebol e e-commerce
TERMOS_BLOQUEADOS = [
    "desconto", "cupom", "oferta", "mercado livre", "achados", "compre", "promoção", "promocao",
    "por r$", "preço", "preco", "economize", "futebol", "flamengo", "palmeiras", "corinthians",
    "campeonato", "brasileirão", "smart tv", "fone de ouvido", "garmin", "relogio", "fifa"
]

# Feeds 100% focados em Deep Tech, IA, Semicondutores e Engenharia (Sem feeds de cupons)
FEEDS = [
    {"url": "https://mittechreview.com.br/feed/", "category": "AI & Models"},
    {"url": "https://www.inovacaotecnologica.com.br/boletim/rss.xml", "category": "Science & Space"},
    {"url": "https://venturebeat.com/category/ai/feed/", "category": "AI & Models"},
    {"url": "https://thedecoder.com/feed/", "category": "AI & Models"},
    {"url": "https://feeds.arstechnica.com/arstechnica/index", "category": "Hardware & Chips"},
    {"url": "https://thenewstack.io/feed/", "category": "Linux & Open-Source"},
    {"url": "https://www.phoronix.com/phoronix-rss.php", "category": "Linux & Open-Source"},
    {"url": "https://9to5mac.com/feed/", "category": "Apple & iOS"},
    {"url": "https://www.windowscentral.com/rss.xml", "category": "Windows & PC"},
    {"url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "Mercado & Big Techs"},
    {"url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "category": "AI & Models"}
]

def selecionar_foto_hd(titulo, categoria):
    t = titulo.lower()
    c = categoria.lower()

    if any(k in t for k in ["memória", "memoria", "ram", "ssd", "hbm", "cxl", "armazenamento", "sk hynix", "micron"]):
        return "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=1200&auto=format&fit=crop&q=80"
    elif any(k in t for k in ["chip", "chips", "nvidia", "amd", "intel", "processador", "gpu", "semicondutor", "silício"]):
        return "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&auto=format&fit=crop&q=80"
    elif any(k in t for k in ["apple", "mac", "macos", "macbook", "iphone", "ios", "m4"]):
        return "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=1200&auto=format&fit=crop&q=80"
    elif any(k in t for k in ["space", "spacex", "starship", "satélite", "foguete", "nasa", "espaço"]):
        return "https://images.unsplash.com/photo-1517976487504-59a1c0188b4c?w=1200&auto=format&fit=crop&q=80"
    elif any(k in t for k in ["segurança", "hack", "invasão", "vulnerabilidade", "rowhammer", "ciber"]):
        return "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=1200&auto=format&fit=crop&q=80"
    elif any(k in t for k in ["windows", "microsoft", "pc", "laptop", "copilot"]):
        return "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=1200&auto=format&fit=crop&q=80"
    elif any(k in t for k in ["linux", "kernel", "open-source", "código", "docker", "servidor"]):
        return "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=1200&auto=format&fit=crop&q=80"
    elif "ia" in c or "model" in c or "ai" in c:
        return "https://images.unsplash.com/photo-1677442136019-21780efad99a?w=1200&auto=format&fit=crop&q=80"
    else:
        return "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&auto=format&fit=crop&q=80"

def fetch_latest_news():
    articles = []
    for item in FEEDS:
        url = item["url"]
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:3]:
                title = getattr(entry, 'title', '').strip()
                link = getattr(entry, 'link', '').strip()
                summary = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
                summary_clean = re.sub(r'<[^>]+>', '', summary).strip()
                
                texto_check = (title + " " + summary_clean).lower()
                
                # Bloqueia ofertas comerciais, futebol e cupons
                if any(bloq in texto_check for bloq in TERMOS_BLOQUEADOS):
                    continue

                if title and link and not any(a["title"] == title for a in articles):
                    articles.append({
                        "title": title,
                        "link": link,
                        "summary": summary_clean[:600],
                        "category": item["category"]
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
    You are the Senior Editorial Director for 'CorticFlow', an authoritative technology magazine.
    Write an in-depth journalistic article (800-1200+ words) in TWO languages: English and Portuguese.
    
    News Title: {news_item['title']}
    Source: {news_item['link']}
    Summary: {news_item['summary']}
    Category: "{news_item['category']}"

    STRUCTURE REQUIREMENT:
    - Write multiple dense paragraphs with:
      1. Context & Technological Breakthrough
      2. Engineering & Architecture Deep Dive
      3. Ecosystem Impact & Market Dynamics
      4. Key Takeaways for Developers & Enterprises
      5. The CorticFlow Outlook

    Return as JSON with keys: "slug", "category", "title_en", "content_en", "title_pt", "content_pt".
    """
    data = call_gemini_api(prompt)
    
    if not data:
        slug_gen = re.sub(r'[^a-zA-Z0-9]+', '-', news_item['title'].lower()).strip('-')[:50]
        data = {
            "slug": slug_gen,
            "category": news_item["category"],
            "title_en": news_item["title"],
            "content_en": f"## Overview\n\n{news_item['summary']}\n\n### Strategic Analysis\n\nThis development in {news_item['category']} represents a key milestone for modern technology infrastructure, bringing new benchmarks for developers and enterprises worldwide.\n\n*Original source: [{news_item['link']}]({news_item['link']})*",
            "title_pt": news_item["title"],
            "content_pt": f"## Visão Geral do Acontecimento\n\n{news_item['summary']}\n\n### Análise de Impacto e Engenharia\n\nEste anúncio em {news_item['category']} traz desdobramentos estratégicos para a infraestrutura de tecnologia, elevando o padrão de eficiência, segurança e inovação no mercado global.\n\n*Acompanhe a matéria original em: [{news_item['link']}]({news_item['link']})*"
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
    desc_final = desc_clean[:220] + "..." if len(desc_clean) > 220 else desc_clean

    foto_hd = selecionar_foto_hd(title_final, category)

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
        "image": foto_hd,
        "img": foto_hd,
        "cover": foto_hd,
        "desc": desc_final,
        "description": desc_final,
        "resumo": desc_final,
        "content": data.get("content_pt", ""),
        "content_pt": data.get("content_pt", ""),
        "content_en": data.get("content_en", ""),
        "link": news_item["link"],
        "fonte": news_item["link"],
        "file_pt": pt_file,
        "file_en": en_file
    })

    print(f"📁 [{idx+1}] Matéria Salva: {title_final}")

if __name__ == "__main__":
    os.makedirs("content/en", exist_ok=True)
    os.makedirs("content/pt", exist_ok=True)

    print("🚀 CorticFlow Bot: Mineração de notícias estritamente de Tecnologia e IA...")
    news = fetch_latest_news()
    all_posts_manifest = []

    for i, item in enumerate(news):
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

    print(f"🎉 Finalizado com sucesso! {len(all_posts_manifest)} matérias salvas.")
