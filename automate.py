import os
import json
import datetime
import requests
import feedparser

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

MODELS = [
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro-latest"
]

# Feeds de referência: Seleção de Inteligência Artificial, Big Techs e Hardware
FEEDS = [
    # Inteligência Artificial e Deep Learning
    "https://venturebeat.com/feed/",
    "https://thedecoder.com/feed/",
    "https://www.technologyreview.com/feed/",
    
    # Grandes Portais Globais (Furos de Mercado e Big Techs)
    "https://www.theverge.com/rss/index.xml",
    "https://techcrunch.com/feed/",
    "https://www.wired.com/feed/rss",
    
    # Hardware Puro, Chips e Infraestrutura Open-Source
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://thenewstack.io/feed/",
    "https://news.ycombinator.com/rss",
    
    # Mercado Nacional (Para Atualizações Gerais e de Telecom)
    "https://tecnoblog.net/feed/",
    "https://olhardigital.com.br/feed/"
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
        if res.status_code == 200:
                result = res.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                
                # Limpa as marcações do Markdown para não quebrar a leitura
                text = text.replace("```json", "").replace("```", "").strip()
                
                print(f"✅ Sucesso com {model}!")
                return json.loads(text)

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

def update_posts_json():
    print("🔄 Atualizando arquivo posts.json...")
    posts = []
    pt_dir = "content/pt"
    
    if not os.path.exists(pt_dir):
        return
        
    for filename in os.listdir(pt_dir):
        if filename.endswith(".md"):
            filepath = os.path.join(pt_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            title = ""
            date_str = ""
            category = ""
            in_frontmatter = False
            
            for line in content.split('\n'):
                if line.strip() == '---':
                    if not in_frontmatter:
                        in_frontmatter = True
                        continue
                    else:
                        break
                if in_frontmatter:
                    if line.startswith('title:'):
                        title = line.replace('title:', '').strip().strip('"').strip("'")
                    elif line.startswith('date:') or line.startswith('data:'):
                        date_str = line.replace('date:', '').replace('data:', '').strip().strip('"').strip("'")
                    elif line.startswith('category:') or line.startswith('categoria:'):
                        category = line.replace('category:', '').replace('categoria:', '').strip().strip('"').strip("'")
            
            posts.append({
                "id": filename.replace('.md', ''),
                "title": title,
                "date": date_str,
                "category": category,
                "file_pt": f"content/pt/{filename}",
                "file_en": f"content/en/{filename}"
            })
            
    # Ordena as postagens da mais recente para a mais antiga
    posts.sort(key=lambda x: x["date"], reverse=True)
    
    with open("posts.json", "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print("✅ posts.json gerado com sucesso!")

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

    # Atualiza o índice do site para que as matérias novas apareçam na home
    update_posts_json()
    print(f"🎉 Finalizado com sucesso! {success_count} matérias geradas e indexadas no site.")
