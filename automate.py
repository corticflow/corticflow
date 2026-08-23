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

# Feeds globais incluindo The Economist, TechCrunch, The Verge e MIT Tech Review
FEEDS = [
    "https://www.economist.com/science-and-technology/rss.xml",
    "https://www.economist.com/business/rss.xml",
    "https://www.economist.com/finance-and-economics/rss.xml",
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.technologyreview.com/feed/",
    "https://feeds.arstechnica.com/arstechnica/index"
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
    return articles[:6]

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
        print(f"Tentando gerar matéria aprofundada com o modelo: {model}...")
        try:
            res = requests.post(url, json=payload, timeout=90)
            if res.status_code == 200:
                result = res.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                print(f"✅ Sucesso com o modelo: {model}!")
                return json.loads(text)
            else:
                last_error = f"{model} (HTTP {res.status_code}): {res.text}"
        except Exception as e:
            last_error = str(e)

    raise Exception(f"Falha em todos os modelos. Último retorno: {last_error}")

def generate_bilingual_post(news_item):
    prompt = f"""
    You are the Senior Editorial Director and Chief AI Analyst for 'CorticFlow', an authoritative international publication with the editorial depth of The Economist and the visual flair of The Verge.
    
    Based on this raw news lead:
    - Lead Headline: {news_item['title']}
    - Source URL: {news_item['link']}
    - Raw Lead Summary: {news_item['summary']}

    Your mission is to write a comprehensive, authoritative, deeply analytical, and long-form journalistic article (800 to 1,200+ words per language) in TWO languages: English and Portuguese.
    
    CRITICAL EDITORIAL GUIDELINES:
    1. Strategic Context: The economic, technological, and market implications.
    2. Granular Analysis: Architecture, computational physics, capital expenditures, or prompt workflows.
    3. Practical Takeaways: Real-world enterprise and developer applications.
    4. Sourcing: Cite the primary source with a clean markdown link.
    5. Formatting: Rich markdown with H2, H3 headers, bullet points, and pull-quotes.

    Return the complete response strictly as valid JSON with keys:
    "slug", "category", "title_en", "content_en", "title_pt", "content_pt".
    """
    return call_gemini_api(prompt)

def save_posts(data):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    slug = data.get("slug", "tech-analysis")
    
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

    print(f"📁 Artigos completos salvos: {en_file} e {pt_file}")

if __name__ == "__main__":
    os.makedirs("content/en", exist_ok=True)
    os.makedirs("content/pt", exist_ok=True)
    print("🚀 CorticFlow Bot: Buscando notícias (Economist, Verge, TechCrunch)...")
    news = fetch_latest_news()
    success_count = 0
    for item in news[:3]:
        try:
            post_data = generate_bilingual_post(item)
            save_posts(post_data)
            success_count += 1
        except Exception as e:
            print(f"Erro ao processar item: {e}")

    print(f"🎉 Finalizado com sucesso! {success_count} matérias geradas.")
