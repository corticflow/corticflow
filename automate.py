import os
import datetime
import feedparser
from google import genai

# Inicializa o cliente da API do Gemini usando a Secret do GitHub
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Feeds RSS das principais fontes globais
FEEDS = [
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.technologyreview.com/feed/",
    "https://feeds.arstechnica.com/arstechnica/index"
]

def fetch_latest_news():
    articles = []
    for url in FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:3]:
            articles.append({
                "title": entry.title,
                "link": entry.link,
                "summary": getattr(entry, 'summary', '')
            })
    return articles[:6]

def generate_bilingual_post(news_item):
    prompt = f"""
    You are the lead tech editor for 'CorticFlow', an authoritative international AI and Tech publication.
    Based on this raw news item:
    Title: {news_item['title']}
    Source Link: {news_item['link']}
    Raw Summary: {news_item['summary']}

    Generate a complete, high-quality, long-form editorial article in TWO languages (English and Portuguese).
    The tone must be analytical, educational, and engaging.

    Return the output in valid JSON with these exact keys:
    - "slug": "a-clean-url-slug-in-english"
    - "category": "AI & Models" or "Tutorials & Guides" or "Business & Startups" or "AI Tools"
    - "title_en": "Catchy SEO Title in English"
    - "content_en": "Full markdown article in English (with H2, bullet points, deep analysis and source link)",
    - "title_pt": "Título atraente em Português"
    - "content_pt": "Artigo completo em Markdown em Português (com subtítulos H2, tópicos, análise prática e link da fonte)"
    """

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config={'response_mime_type': 'application/json'}
    )
    import json
    return json.loads(response.text)

def save_posts(data):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    slug = data.get("slug", "tech-update")
    
    os.makedirs("content/en", exist_ok=True)
    os.makedirs("content/pt", exist_ok=True)

    # Post em Inglês
    en_file = f"content/en/{today}-{slug}.md"
    with open(en_file, "w", encoding="utf-8") as f:
        f.write(f"---\ntitle: \"{data['title_en']}\"\ndate: \"{today}\"\ncategory: \"{data['category']}\"\n---\n\n")
        f.write(data["content_en"])

    # Post em Português
    pt_file = f"content/pt/{today}-{slug}.md"
    with open(pt_file, "w", encoding="utf-8") as f:
        f.write(f"---\ntitle: \"{data['title_pt']}\"\ndata: \"{today}\"\ncategoria: \"{data['category']}\"\n---\n\n")
        f.write(data["content_pt"])

    print(f"✅ Artigos gerados: {en_file} e {pt_file}")

if __name__ == "__main__":
    print("🚀 CorticFlow Bot: Buscando notícias...")
    news = fetch_latest_news()
    for item in news[:2]:
        try:
            post_data = generate_bilingual_post(item)
            save_posts(post_data)
        except Exception as e:
            print(f"Erro ao processar notícia: {e}")
