import os
import json
import datetime
import requests
import feedparser
import re
import math

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

MODELS = [
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-pro"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 14 Feeds Oficiais CorticFlow
FEEDS = [
    "https://tecnoblog.net/feed/",
    "https://olhardigital.com.br/feed/",
    "https://mittechreview.com.br/feed/",
    "https://canaltech.com.br/rss/",
    "https://venturebeat.com/category/ai/feed/",
    "https://thedecoder.com/feed/",
    "https://www.windowscentral.com/rss.xml",
    "https://www.phoronix.com/phoronix-rss.php",
    "https://www.omgubuntu.co.uk/feed",
    "https://9to5mac.com/feed/",
    "https://9to5google.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://techcrunch.com/feed/",
    "https://feeds.arstechnica.com/arstechnica/index"
]

def fetch_latest_news():
    articles = []
    for url in FEEDS:
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
                        "summary": summary_clean[:500]
                    })
        except Exception as e:
            print(f"Aviso no feed {url}: {e}")
    return articles[:8]

def call_gemini_api(prompt):
    if not API_KEY:
        raise ValueError("ERRO: GEMINI_API_KEY não configurada!")

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.7,
            "maxOutputTokens": 8192
        }
    }

    last_error = None
    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
        print(f"Tentando com modelo: {model}...")
        try:
            res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=90)
            if res.status_code == 200:
                result = res.json()
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                
                clean_text = re.sub(r'^```json\s*', '', raw_text)
                clean_text = re.sub(r'^```\s*', '', clean_text)
                clean_text = re.sub(r'\s*```$', '', clean_text)
                
                data = json.loads(clean_text)
                print(f"✅ Sucesso com {model}!")
                return data
            else:
                last_error = f"{model} (HTTP {res.status_code}): {res.text}"
        except Exception as e:
            last_error = str(e)

    raise Exception(f"Falha em todos os modelos: {last_error}")

def generate_bilingual_post(news_item):
    prompt = f"""
    You are the Senior Editorial Director for 'CorticFlow', an authoritative technology publication covering AI, Apple, Android, Windows, Linux, Startups, Science, and Developer Tutorials.
    
    Based on this raw news lead:
    - Title: {news_item['title']}
    - Source URL: {news_item['link']}
    - Summary: {news_item['summary']}

    Write a comprehensive, engaging, high-authority journalistic article (800-1200+ words) in TWO languages: English and Portuguese.
    
    Categorize into one of these exact tracks:
    - "Windows & PC"
    - "Linux & Open-Source"
    - "Apple & iOS"
    - "Android & Gadgets"
    - "AI & Models"
    - "Business & Startups"
    - "Science & Space"
    - "Tutorials & Prompts"

    Return strictly as valid JSON with keys:
    "slug", "category", "title_en", "content_en", "title_pt", "content_pt".
    """
    return call_gemini_api(prompt)

def save_posts(data, all_posts_manifest):
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

    all_posts_manifest.append({
        "slug": slug_clean,
        "date": today,
        "category": data.get("category", "Geral"),
        "read_time": read_time,
        "title_pt": data.get("title_pt", ""),
        "title_en": data.get("title_en", ""),
        "content_pt": data.get("content_pt", ""),
        "content_en": data.get("content_en", ""),
        "file_pt": pt_file,
        "file_en": en_file
    })

    print(f"📁 Artigos salvos: {en_file} e {pt_file}")

if __name__ == "__main__":
    os.makedirs("content/en", exist_ok=True)
    os.makedirs("content/pt", exist_ok=True)

    print("🚀 CorticFlow Bot: Buscando notícias nas 14 fontes...")
    news = fetch_latest_news()
    success_count = 0
    all_posts_manifest = []

    for item in news[:6]:
        try:
            post_data = generate_bilingual_post(item)
            if post_data and isinstance(post_data, dict):
                save_posts(post_data, all_posts_manifest)
                success_count += 1
        except Exception as e:
            print(f"Erro ao processar item: {e}")

    with open("posts.json", "w", encoding="utf-8") as f:
        json.dump(all_posts_manifest, f, ensure_ascii=False, indent=2)
    with open("content/posts.json", "w", encoding="utf-8") as f:
        json.dump(all_posts_manifest, f, ensure_ascii=False, indent=2)

    print(f"🎉 Finalizado com sucesso! {success_count} matérias geradas.")
