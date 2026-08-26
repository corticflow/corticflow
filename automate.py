import os
import json
import datetime
import requests
import feedparser
import re
import math

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
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

def selecionar_imagem_alta_fidelidade(titulo, categoria, entry):
    """Gera foto contextual 100% condizente com o assunto da matéria, sem imagens aleatórias."""
    t = titulo.lower()
    c = categoria.lower()

    # 1. WhatsApp, Golpes e Segurança
    if any(k in t for k in ["whatsapp", "zap", "golpe", "invasão", "hack", "vítima", "segurança", "vulnerabilidade", "senha"]):
        return "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=1200&auto=format&fit=crop&q=80"
    
    # 2. Apple, Mac, macOS, iPhone e iOS
    elif any(k in t for k in ["apple", "mac", "macos", "macbook", "iphone", "ios", "ipad", "m4", "m3"]):
        return "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=1200&auto=format&fit=crop&q=80"

    # 3. SpaceX, Starship, Espaço, Foguete e Satélite
    elif any(k in t for k in ["space", "spacex", "starship", "satélite", "satelite", "foguete", "nasa", "órbita", "astronomia"]):
        return "https://images.unsplash.com/photo-1517976487504-59a1c0188b4c?w=1200&auto=format&fit=crop&q=80"

    # 4. Redes Sociais, Instagram, Reels e TikTok
    elif any(k in t for k in ["instagram", "reels", "tiktok", "social", "youtube", "influencer", "post", "vídeo"]):
        return "https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=1200&auto=format&fit=crop&q=80"

    # 5. Nvidia, AMD, Chips, Semicondutores e Processadores
    elif any(k in t for k in ["chip", "chips", "nvidia", "amd", "intel", "processador", "gpu", "semicondutor", "hardware"]):
        return "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&auto=format&fit=crop&q=80"

    # 6. Aviação, Latam, Voos e Viagens
    elif any(k in t for k in ["latam", "voo", "voos", "avião", "aéreo", "aeroporto", "viagem"]):
        return "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=1200&auto=format&fit=crop&q=80"

    # 7. Google, Buscas e Big Techs
    elif any(k in t for k in ["google", "busca", "search", "alphabet", "chrome"]):
        return "https://images.unsplash.com/photo-1573804633927-bfcbcd909acd?w=1200&auto=format&fit=crop&q=80"

    # 8. Linux, Open-Source e Programação
    elif any(k in t for k in ["linux", "ubuntu", "kernel", "open-source", "código", "programador", "github", "docker", "server"]):
        return "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=1200&auto=format&fit=crop&q=80"

    # 9. Windows, PC e Copilot
    elif any(k in t for k in ["windows", "microsoft", "pc", "laptop", "copilot", "computador"]):
        return "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=1200&auto=format&fit=crop&q=80"

    # 10. Android e Smartphones
    elif any(k in t for k in ["android", "samsung", "galaxy", "smartphone", "celular", "gadget"]):
        return "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=1200&auto=format&fit=crop&q=80"

    # 11. Inteligência Artificial e Modelos LLM
    elif any(k in t for k in ["ia", "ai", "llm", "chatgpt", "deepseek", "gemini", "claude", "modelo", "inteligência"]):
        return "https://images.unsplash.com/photo-1677442136019-21780efad99a?w=1200&auto=format&fit=crop&q=80"

    # 12. Cinema, Entretenimento e Filmes
    elif any(k in t for k in ["aranha", "vingadores", "marvel", "filme", "cinema", "jogo", "game"]):
        return "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=1200&auto=format&fit=crop&q=80"

    # Fallbacks Oficiais por Categoria
    elif "ia" in c or "model" in c:
        return "https://images.unsplash.com/photo-1677442136019-21780efad99a?w=1200&auto=format&fit=crop&q=80"
    elif "hardware" in c or "pc" in c:
        return "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&auto=format&fit=crop&q=80"
    elif "android" in c:
        return "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=1200&auto=format&fit=crop&q=80"
    else:
        return "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&auto=format&fit=crop&q=80"

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
                        "summary": summary_clean[:600],
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
    Return as JSON: "slug", "category", "title_en", "content_en", "title_pt", "content_pt".
    """
    data = call_gemini_api(prompt)
    
    if not data:
        slug_gen = re.sub(r'[^a-zA-Z0-9]+', '-', news_item['title'].lower()).strip('-')[:50]
        data = {
            "slug": slug_gen,
            "category": news_item["category"],
            "title_en": news_item["title"],
            "content_en": f"## Overview\n\n{news_item['summary']}\n\n### Strategic Analysis\n\nThis development marks a significant update in the {news_item['category']} landscape, redefining industry benchmarks.\n\n*Original source: [{news_item['link']}]({news_item['link']})*",
            "title_pt": news_item["title"],
            "content_pt": f"## Visão Geral\n\n{news_item['summary']}\n\n### Análise de Impacto e Engenharia\n\nEste anúncio traz desdobramentos importantes para o ecossistema de {news_item['category']}, elevando o nível de inovação no mercado global.\n\n*Fonte original: [{news_item['link']}]({news_item['link']})*"
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

    # Foto HD contextual do tema exato
    foto_hd = selecionar_imagem_alta_fidelidade(title_final, category, news_item.get("entry", {}))

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
        "imagem": foto_hd,
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

    print(f"📁 [{idx+1}] Matéria salva com Foto HD Contextual: {title_final}")

if __name__ == "__main__":
    os.makedirs("content/en", exist_ok=True)
    os.makedirs("content/pt", exist_ok=True)

    print("🚀 CorticFlow Bot: Gerando matérias com Fotos Contextuais HD...")
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

    print(f"🎉 Finalizado com sucesso! {len(all_posts_manifest)} matérias salvas com fotos contextuais.")
