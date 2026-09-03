import feedparser
import json
import os
import google.generativeai as genai
import random
from datetime import datetime, timedelta

# Configurações de RSS Feeds (Blogs Oficiais + Perfis do X via Bridge)
RSS_FEEDS = {
    # Portais e Blogs de Engenharia
    "Google Blog": "https://blog.google/rss/",
    "Nvidia News": "https://nvidianews.nvidia.com/releases.xml",
    "Apple Newsroom": "https://www.apple.com/newsroom/rss-feed.rss",
    "Linux.com": "https://www.linux.com/feed/",
    "OpenAI Blog": "https://openai.com/blog/rss.xml",
    "Anthropic News": "https://www.anthropic.com/news.rss",
    "DeepSeek Blog": "https://blog.deepseek.com/rss/",
    "MIT Tech Review": "https://www.technologyreview.com/feed/",
    "TechCrunch": "https://techcrunch.com/feed/",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    # Perfis Oficiais no X (via OpenRSS / RSSHub)
    "X | @OpenAI": "https://openrss.org/twitter.com/OpenAI",
    "X | @AnthropicAI": "https://openrss.org/twitter.com/AnthropicAI",
    "X | @deepseek_ai": "https://openrss.org/twitter.com/deepseek_ai",
    "X | @GoogleDeepMind": "https://openrss.org/twitter.com/GoogleDeepMind",
    "X | @NVIDIAAI": "https://openrss.org/twitter.com/NVIDIAAI",
    "X | @Linux": "https://openrss.org/twitter.com/Linux"
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
    "https://images.unsplash.com/photo-1563986768609-322da13575f3?q=80&w=1600&h=900&fit=crop"
]

def generate_bilingual_post(model, source_name, original_title, original_summary):
    is_x_post = "X |" in source_name
    prompt = f"""
Atue como Editor-Chefe de Tecnologia da plataforma CorticFlow.
Sua tarefa é analisar o fato tecnológico abaixo e produzir DUAS versões analíticas e completas: uma em PORTUGUÊS (PT-BR) e uma em INGLÊS (EN-US).

Fonte: {source_name}
Título Original: {original_title}
Resumo / Post: {original_summary}
Origem: {"Post rápido no X (Twitter) — expanda com contexto arquitetural profundo e implicações para a indústria" if is_x_post else "Artigo de Notícia Técnica"}

Retorne ESTRITAMENTE um objeto JSON com o seguinte schema:
{{
  "title_pt": "Título jornalístico e técnico em Português",
  "title_en": "Journalistic and technical headline in English",
  "excerpt_pt": "Resumo executivo de 2 a 3 frases em Português.",
  "excerpt_en": "Executive summary of 2 to 3 sentences in English.",
  "content_pt": "Análise técnica aprofundada em Português (com síntese executiva, arquitetura técnica e conclusões).",
  "content_en": "Deep technical analysis in English (with executive takeaways, technical architecture and industry outlook)."
}}
"""
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text.strip())
        return data
    except Exception as e:
        print(f"Erro Gemini ({source_name}): {e}")
        return {
            "title_pt": original_title,
            "title_en": original_title,
            "excerpt_pt": original_summary[:160] + "...",
            "excerpt_en": original_summary[:160] + "...",
            "content_pt": original_summary,
            "content_en": original_summary
        }

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
            source = entry.get('source_name', 'Tech News')
            title = entry.get('title', 'Sem Título')
            summary = entry.get('summary', entry.get('description', ''))
            
            post_data = generate_bilingual_post(model, source, title, summary)
            
            processed_posts.append({
                "source": source,
                "link": entry.get('link', ''),
                "image": IMAGE_POOL[i % len(IMAGE_POOL)],
                "title_pt": post_data.get("title_pt", title),
                "title_en": post_data.get("title_en", title),
                "excerpt_pt": post_data.get("excerpt_pt", summary[:160]),
                "excerpt_en": post_data.get("excerpt_en", summary[:160]),
                "content_pt": post_data.get("content_pt", summary),
                "content_en": post_data.get("content_en", summary)
            })

        with open("posts.json", "w", encoding="utf-8") as f:
            json.dump(processed_posts, f, ensure_ascii=False, indent=4)

        print(f"Sucesso: {len(processed_posts)} posts bilíngues salvos em posts.json.")

    except Exception as e:
        print(f"Erro Fatal: {e}")

if __name__ == "__main__":
    main()
