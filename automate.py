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
        raise ValueError("ERRO: GEMINI_API_KEY não foi configurada nas Secrets!")

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
        print(f"Tentando gerar artigo longo com o modelo: {model}...")
        try:
            res = requests.post(url, json=payload, timeout=90)
            if res.status_code == 200:
                result = res.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                print(f"✅ Sucesso com o modelo: {model}!")
                return json.loads(text)
            else:
                last_error = f"{model} (HTTP {res.status_code}): {res.text}"
                print(f"Aviso: {model} retornou erro {res.status_code}. Tentando próximo...")
        except Exception as e:
            last_error = str(e)
            print(f"Falha na requisição com {model}: {e}")

    raise Exception(f"Falha em todos os modelos. Último retorno: {last_error}")

def generate_bilingual_post(news_item):
    prompt = f"""
    You are the Senior Editorial Director and Chief AI Analyst for 'CorticFlow', an authoritative international publication focused on AI engineering, frontier models, and technology ecosystems.
    
    Based on this raw news lead:
    - Lead Headline: {news_item['title']}
    - Source URL: {news_item['link']}
    - Raw Lead Summary: {news_item['summary']}

    Your mission is to write a comprehensive, authoritative, deeply analytical, and long-form journalistic article (800 to 1,200+ words per language) in TWO languages: English and Portuguese.
    
    CRITICAL EDITORIAL GUIDELINES FOR THE ARTICLE BODY:
    1. Introduction & Strategic Context: Explain the background, the core development, and why it is a critical milestone for the industry.
    2. Deep Technical Breakdown: Provide a granular analysis of the architecture, algorithmic approach, performance benchmarks, or underlying infrastructure.
    3. Practical Applications & Real-World Use Cases: How developers, enterprises, and everyday creators can practically utilize or prepare for this technology (include prompt examples or actionable workflows if applicable).
    4. Market Dynamics & Competitive Landscape: Compare this move against competitors (OpenAI, Google, Anthropic, Meta, open-source community) and evaluate long-term financial/operational implications.
    5. Editorial Outlook & Next Steps: Synthesize future implications and conclude with a clean citation acknowledging the primary source with a markdown hyperlink.
    6. Formatting: Use rich Markdown formatting with H2, H3 headers, bullet points, bold key terms, blockquotes, and structured readability.

    Return the complete response strictly as a single valid JSON object with these exact keys:
    - "slug": "a-concise-seo-friendly-url-slug-in-english"
    - "category": "AI & Models" or "Tutorials & Guides" or "Business & Startups" or "AI Tools"
    - "title_en": "Compelling, High-CTR, SEO-Optimized Title in English"
    - "content_en": "Full extensive long-form markdown article in English (800-1200+ words)"
    - "title_pt": "Título Atraente, Otimizado para SEO e Alta Taxa de Cliques em Português"
    - "content_pt": "Artigo completo e aprofundado em Markdown em Português (800-1200+ palavras)"
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
    print("🚀 CorticFlow Bot: Buscando notícias para redação aprofundada...")
    news = fetch_latest_news()
    success_count = 0
    for item in news[:2]:
        try:
            post_data = generate_bilingual_post(item)
            save_posts(post_data)
            success_count += 1
        except Exception as e:
            print(f"Erro ao processar item: {e}")

    print(f"🎉 Finalizado com sucesso! {success_count} matérias aprofundadas geradas.")
