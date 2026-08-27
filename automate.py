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

# Bloqueio estrito de assuntos não-tecnológicos (tragédias, acidentes, crimes, esportes)
TERMOS_BLOQUEADOS = [
    "inundação", "inundacao", "enchente", "desastre", "morte", "matou", "morreu", "acidente",
    "desaparecido", "polícia", "policia", "preso", "crime", "assalto", "nepal", "futebol",
    "flamengo", "palmeiras", "corinthians", "brasileirão", "campeonato", "eleição", "política",
    "famosos", "novela", "loteria", "mega-sena"
]

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

def selecionar_foto_exata(titulo, categoria):
    """Mapeamento rigoroso de fotos de alta resolução sem erros ou logos estranhos."""
    t = titulo.lower()
    c = categoria.lower()

    # 1. Uber, 99, Carros, Viagens, Mobilidade, GPS
    if any(k in t for k in ["uber", "99", "corrida", "motorista", "carro", "trânsito", "viagem", "gps"]):
        return "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&auto=format&fit=crop&q=80" # Smartphone com tela de App e Mapa

    # 2. WhatsApp, Mensagens, Golpes, Segurança, Hack
    elif any(k in t for k in ["whatsapp", "zap", "golpe", "invasão", "hack", "vítima", "segurança", "senha", "privacidade"]):
        return "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=1200&auto=format&fit=crop&q=80" # Segurança Mobile

    # 3. Windows, PC, Dell, Laptops, Notebooks, Copilot
    elif any(k in t for k in ["windows", "microsoft", "pc", "laptop", "notebook", "dell", "lenovo", "acer", "desktop"]):
        return "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=1200&auto=format&fit=crop&q=80" # Notebook em mesa de trabalho

    # 4. Apple, Mac, macOS, MacBook, iPhone, iPad, iOS
    elif any(k in t for k in ["apple", "mac", "macos", "macbook", "iphone", "ios", "ipad", "m4", "m3"]):
        return "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=1200&auto=format&fit=crop&q=80" # MacBook Pro

    # 5. Processadores, Chips, Semicondutores, GPU, Nvidia, AMD
    elif any(k in t for k in ["chip", "chips", "nvidia", "amd", "intel", "processador", "gpu", "semicondutor", "hbm"]):
        return "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&auto=format&fit=crop&q=80" # Placa de Circuito / Processador

    # 6. Espaço, SpaceX, Starship, Foguete, Satélite, NASA
    elif any(k in t for k in ["space", "spacex", "starship", "satélite", "satelite", "foguete", "nasa", "órbita"]):
        return "https://images.unsplash.com/photo-1517976487504-59a1c0188b4c?w=1200&auto=format&fit=crop&q=80" # Foguete Espacial

    # 7. Redes Sociais, Instagram, Reels, TikTok, YouTube
    elif any(k in t for k in ["instagram", "reels", "tiktok", "social", "youtube", "vídeo", "influencer"]):
        return "https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=1200&auto=format&fit=crop&q=80" # Redes Sociais

    # 8. Celulares, Smartphones, Android, Galaxy
    elif any(k in t for k in ["celular", "smartphone", "android", "galaxy", "samsung", "xiaomi", "motorola"]):
        return "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=1200&auto=format&fit=crop&q=80" # Smartphone

    # 9. Inteligência Artificial e LLMs
    elif any(k in t for k in ["ia", "ai", "llm", "chatgpt", "deepseek", "gemini", "claude", "modelo", "inteligência"]):
        return "https://images.unsplash.com/photo-1677442136019-21780efad99a?w=1200&auto=format&fit=crop&q=80" # Conexões Neurais

    # 10. Linux e Open-Source
    elif any(k in t for k in ["linux", "ubuntu", "kernel", "open-source", "docker", "código", "programador"]):
        return "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=1200&auto=format&fit=crop&q=80" # Terminal escuro

    else:
        return "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&auto=format&fit=crop&q=80" # Tecnologia Global

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
                # Remove frases promocionais de rodapé dos feeds
                summary_clean = re.sub(r'O post .* apareceu primeiro em .*', '', summary_clean).strip()
                
                texto_check = (title + " " + summary_clean).lower()
                # Descarta tragédias, esportes e notícias fora de tecnologia
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
    if not API_KEY:
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

    STRUCTURE REQUIREMENT (NO BOILERPLATE):
    - Write multiple rich paragraphs explaining:
      1. Context & Breakthrough
      2. Technical Deep Dive (Architecture, specs, performance)
      3. Ecosystem Impact (Who benefits, market dynamics)
      4. Key Takeaways
      5. The CorticFlow Outlook

    Return strictly as valid JSON with keys:
    "slug", "category", "title_en", "content_en", "title_pt", "content_pt".
    """
    data = call_gemini_api(prompt)
    
    # Fallback denso e profissional (sem frases inúteis de rodapé)
    if not data:
        slug_gen = re.sub(r'[^a-zA-Z0-9]+', '-', news_item['title'].lower()).strip('-')[:50]
        data = {
            "slug": slug_gen,
            "category": news_item["category"],
            "title_en": news_item["title"],
            "content_en": f"## Executive Summary\n\n{news_item['summary']}\n\n### Technical Analysis & Market Impact\n\nThis development marks a substantial evolution in the {news_item['category']} landscape. By expanding capabilities and refining architecture, this update sets a new operational standard across the global tech ecosystem.\n\n### Strategic Takeaways\n\n1. Enhanced efficiency and integrated workflows.\n2. Stronger ecosystem alignment for enterprise and consumer users.\n3. Increased competitive pressure across adjacent market sectors.\n\n*Original Source: [{news_item['link']}]({news_item['link']})*",
            "title_pt": news_item["title"],
            "content_pt": f"## Visão Geral Executiva\n\n{news_item['summary']}\n\n### Análise Técnica e Impacto de Mercado\n\nEste anúncio representa um marco relevante para o ecossistema de {news_item['category']}. A evolução das especificações e a integração da infraestrutura estabelecem novos padrões operacionais e competitivos no setor de tecnologia.\n\n### Principais Destaques Estratégicos\n\n1. Otimização de eficiência operacional e experiência do usuário.\n2. Consolidação de novas arquiteturas de software e hardware.\n3. Aceleração de padrões de mercado para a próxima geração de produtos.\n\n*Acompanhe a matéria original em: [{news_item['link']}]({news_item['link']})*"
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
    read_time = f"{max(3, math.ceil(words_pt / 180))} min"
    category = data.get("category", news_item.get("category", "Geral"))
    title_final = data.get("title_pt") or data.get("title_en") or news_item["title"]
    
    desc_raw = data.get("content_pt") or news_item["summary"]
    desc_clean = re.sub(r'[#*_`]', '', desc_raw).strip()
    desc_clean = re.sub(r'Visão Geral Executiva', '', desc_clean).strip()
    desc_final = desc_clean[:200] + "..." if len(desc_clean) > 200 else desc_clean

    foto_correta = selecionar_foto_exata(title_final, category)

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
        "image": foto_correta,
        "img": foto_correta,
        "cover": foto_correta,
        "imagem": foto_correta,
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

    print(f"📁 [{idx+1}] Matéria Salva com Foto Exata: {title_final}")

if __name__ == "__main__":
    os.makedirs("content/en", exist_ok=True)
    os.makedirs("content/pt", exist_ok=True)

    print("🚀 CorticFlow Bot: Mineração de notícias com filtro anti-tragédias e fotos exatas...")
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

    print(f"🎉 Finalizado com sucesso! {len(all_posts_manifest)} matérias salvas com compatibilidade total.")
