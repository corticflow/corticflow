import os
import json
import datetime
import requests
import feedparser

API_KEY = os.environ.get("GEMINI_API_KEY")

# Modelos em ordem de tentativa
MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-2.5-pro"
]

FEEDS = [
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
    return articles[:4]

def call_gemini_api(prompt):
    if not API_KEY:
        raise ValueError("ERRO CRÍTICO: GEMINI_API_KEY não foi configurada nas Secrets!")

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }

    last_error = None
    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
        print(f"Tentando gerar com o modelo: {model}...")
        try:
            res = requests.post(url, json=payload, timeout=45)
            if res.status_code == 200:
                result = res.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                print(f" Sucesso com o modelo: {model}")
                return json.loads(text)
            else:
                last_error = f"{model} ({res.status_code}): {res.text}"
                print(f"Aviso: {model} retornou erro {res.status_code}. Tentando próximo...")
        except Exception as e:
            last_error = str(e)
            print(f"Falha na requisição com {model}: {e}")

    raise Exception(f"Todos os modelos falharam. Último erro: {last_error}")

def generate_bilingual_post(news_item):
    prompt = f"""
    You are the lead tech editor for 'CorticFlow', an authoritative international AI and Tech publication.
    Based on this raw news item:
    Title: {news_item['title']}
    Source Link: {news_item['link']}
    Raw Summary: {news_item['summary']}

    Generate a complete, high-quality editorial article in TWO languages (English and Portuguese).
    The tone must be analytical, educational, and engaging.

    Return the output in valid JSON with these exact keys:
    - "slug": "a-clean-url-slug-in-english"
    - "category": "AI & Models" or "Tutorials & Guides" or "Business & Startups" or "AI Tools"
    - "title_en": "Catchy SEO Title in English"
    - "content_en": "Full markdown article in English (with H2, bullet points, deep analysis and source link)"
    - "title_pt": "Título atraente em Português"
    - "content_pt": "Artigo completo em Markdown em Português (com subtítulos H2, tópicos, análise prática e link da fonte)"
    """
    return call_gemini_api(prompt)

def save_posts(data):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    slug = data.get("slug", "tech-update")
    
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

    print(f"✅ Artigos gerados: {en_file} e {pt_file}")

if __name__ == "__main__":
    print("🚀 CorticFlow Bot: Buscando notícias...")
    news = fetch_latest_news()
    success_count = 0
    for item in news[:2]:
        try:
            post_data = generate_bilingual_post(item)
            save_posts(post_data)
            success_count += 1
        except Exception as e:
            print(f"Erro ao processar item: {e}")

    if success_count == 0:
        raise SystemExit("Nenhum artigo pôde ser gerado nesta rodada.")
    print(f"🎉 Finalizado com sucesso! {success_count} matérias geradas.")
