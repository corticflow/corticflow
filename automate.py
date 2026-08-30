


import feedparser
import json
import os
import google.generativeai as genai
import random
import time
from datetime import datetime, timedelta

# Configurações de RSS Feeds
RSS_FEEDS = {
    "Google": "https://blog.google/rss/",
    "Nvidia": "https://nvidianews.nvidia.com/releases.xml",
    "Apple": "https://www.apple.com/newsroom/rss-feed.rss",
    "Linux": "https://www.linux.com/feed/",
    "OpenAI": "https://openai.com/blog/rss.xml",
    "Anthropic": "https://www.anthropic.com/news.rss",
    "DeepSeek": "https://blog.deepseek.com/rss/",
    "MIT Tech Review": "https://www.technologyreview.com/feed/",
    "TechCrunch": "https://techcrunch.com/feed/",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index"
}

# Pool de URLs de alta resolução 16:9 temáticas
IMAGE_POOL = [
    "https://images.unsplash.com/photo-1677442136019-21780ecad995?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1620712943543-bcc463867000?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1531746790731-6c087fecd05a?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1507413245164-6160d8298b31?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1539193143244-c83d9436d633?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1563986768609-322da13575f3?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1509062522246-3755977927d7?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1527430253228-e93688616381?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1581092160562-40aa08e78837?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1558494949-ef010911182e?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1518433278981-d57f73efe02a?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1614064641938-3bbee52942c7?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1535223289827-42f1e9919769?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1516116216624-53e697fedbea?q=80&w=1600&h=900&fit=crop",
    "https://images.unsplash.com/photo-1555664424-778a1e5e1b48?q=80&w=1600&h=900&fit=crop"
]

def rewrite_to_long_form(model, title, summary):
    prompt = (
        f"Reescreva o seguinte conteúdo de notícias em um artigo de formato longo (long-form), "
        f"mantendo um tom profissional, informativo e envolvente.\n\n"
        f"Título: {title}\n"
        f"Resumo Original: {summary}"
    )
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Erro Gemini: {e}")
        return summary

def main():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("GEMINI_API_KEY não configurada.")
            return

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        cutoff_date = datetime.now() - timedelta(hours=72)
        all_entries = []

        for source_name, url in RSS_FEEDS.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    published = entry.get('published_parsed')
                    if published:
                        dt_published = datetime(*published[:6])
                        if dt_published >= cutoff_date:
                            entry['source_name'] = source_name
                            all_entries.append(entry)
            except Exception as e:
                print(f"Erro ao coletar {source_name}: {e}")

        random.shuffle(all_entries)
        selected_entries = all_entries[:16]
        
        random.shuffle(IMAGE_POOL)
        processed_posts = []

        for i, entry in enumerate(selected_entries):
            title = entry.get('title', 'Sem Título')
            summary = entry.get('summary', entry.get('description', ''))
            content = rewrite_to_long_form(model, title, summary)
            
            processed_posts.append({
                "source": entry['source_name'],
                "title": title,
                "link": entry.get('link', ''),
                "image": IMAGE_POOL[i % len(IMAGE_POOL)],
                "content": content
            })

        with open("posts.json", "w", encoding="utf-8") as f:
            json.dump(processed_posts, f, ensure_ascii=False, indent=4)
        
        print(f"Sucesso: {len(processed_posts)} posts salvos.")

    except Exception as e:
        print(f"Erro Fatal: {e}")

if __name__ == "__main__":
    main()

