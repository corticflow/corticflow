import os
import json
import datetime
import requests
import feedparser

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

MODELS = [
    "gemini-3.6-flash",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-pro"
]

# Feeds de referência: Brasil + Internacional (incluindo Windows e Linux)
FEEDS = [
    # Nacionais e Foco no Brasil
    "https://canaltech.com.br/rss/",
    "https://tecnoblog.net/feed/",
    "https://olhardigital.com.br/feed/",
    "https://www.inovacaotecnologica.com.br/boletim/rss.xml",
    "https://mittechreview.com.br/feed/",
    # Internacionais (Apple, Android, Windows, Linux, Startups, IA)
    "https://www.windowscentral.com/rss.xml",
    "https://www.phoronix.com/phoronix-rss.php",
    "https://www.omgubuntu.co.uk/feed",
    "https://9to5mac.com/feed/",
    "https://9to5google.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://techcrunch.com/feed/",
    "https://www.wired.com/feed/rss",
    "https://www.economist.com/science-and-technology/rss.xml"
]

def fetch_latest_news():
    articles = []
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                articles.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": getattr(entry, 'summary', '')
                })
        except Exception as e:
            print(f"Aviso ao ler feed {url}: {e}")
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
        print(f"Tentando gerar com o modelo: {model}...")
        try:
            res = requests.post(url, json=payload, timeout=90)
            if res.status_code == 200:
                result = res.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                print(f"✅ Sucesso com {model}!")
                return json.loads(text)
            else:
                last_error = f"{model} (HTTP {res.status_code}): {res.text}"
        except Exception as e:
            last_error = str(e)

    raise Exception(f"Falha em todos os modelos. Último retorno: {last_error}")

def generate_bilingual_post(news_item):
    prompt = f"""
    You are the Senior Editorial Director for 'CorticFlow', an authoritative technology publication covering AI, Apple, Android, Windows, Linux, Startups, Science, and Developer Tutorials.
    
    Based on this raw news lead:
    - Title: {news_item['title']}
    - Source URL: {news_item['link']}
    - Summary: {news_item['summary']}

    Write a comprehensive, engaging, high-authority journalistic article (800-1200+ words) in TWO languages: English and Portuguese.
    
    Categorize into one of these exact tracks:
    - "Windows & PC" (Copilot+ PCs, Windows 11/12, ARM processors, hardware, gaming PCs)
    - "Linux & Open-Source" (Linux distros, kernel updates, Docker, cloud servers, open-source AI)
    - "Apple & iOS" (iPhone, iOS, Mac, Apple Intelligence, Apple hardware)
    - "Android & Gadgets" (Android smartphones, foldables, chips, wearable gadgets, reviews)
    - "AI & Models" (LLMs, neural networks, reasoning agents)
    - "Business & Startups" (Venture capital, Big Tech earnings, telecom, market trends)
    - "Science & Space" (Scientific breakthroughs, physics, space, deep tech, energy)
    - "Tutorials & Prompts" (Prompt engineering, how-to guides, actionable workflows)

    Return strictly as valid JSON with keys:
    "slug", "category", "title_en", "content_en", "title_pt", "content_pt".
    """
    return call_gemini_api(prompt)

def save_posts(data):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    slug = data.get("slug", "tech-dispatch")
    
    os.makedirs("content/en", exist_ok=True)
    os.makedirs("content/pt", exist_ok=True)

    en_file = f"content/en/{today}-{slug}.md"
    with open(en_file, "w", encoding="utf-8") as f:
        f.write(f"---\ntitle: \"{data['title_en']}\"\ndate: \"{today}\"\ncategory: \"{data['category']}\"\n---\n\n")
        f.write(data["content_en"])

    pt_file = f"content/pt/{today}-{slug}.md"
    with open(pt_file, "w", encoding="utf-8") as f:
        f.write(f"---\ntitle: \"{data['title_pt']}\"\ndata: \"{today}\"\ncategoria: \"{data['category']}\"\n---\n\n")
        f.write(data["content_pt"])

    print(f"📁 Artigos salvos: {en_file} e {pt_file}")

if __name__ == "__main__":
    os.makedirs("content/en", exist_ok=True)
    os.makedirs("content/pt", exist_ok=True)
    print("🚀 CorticFlow Bot: Buscando notícias em todas as plataformas...")
    news = fetch_latest_news()
    success_count = 0
    for item in news[:4]:
        try:
            post_data = generate_bilingual_post(item)
            save_posts(post_data)
            success_count += 1
        except Exception as e:
            print(f"Erro ao processar item: {e}")

    print(f"🎉 Finalizado com sucesso! {success_count} matérias geradas.")
