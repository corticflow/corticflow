

import feedparser
import json
import os
import google.generativeai as genai
import random

# CorticFlow Automation Script: automate.py
# Configured for expanded RSS collection and Gemini long-form rewriting

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

# Pool de 20 imagens de capa 16:9 exclusivas e temáticas
IMAGE_POOL = [f"cover_{i}.png" for i in range(1, 21)]

# API Configuration
GEMINI_API_KEY = "YOUR_API_KEY"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def rewrite_to_long_form(title, summary):
    """
    Utiliza a API do Gemini para reescrever o conteúdo do RSS em formato long-form.
    """
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
        print(f"Erro ao processar '{title}': {e}")
        return summary

def main():
    """
    Executa o ciclo de coleta, processamento e salvamento.
    """
    processed_posts = []
    # Shuffle para garantir que as imagens não se repitam no feed diário
    random.shuffle(IMAGE_POOL)
    image_index = 0

    all_entries = []
    for source_name, url in RSS_FEEDS.items():
        print(f"Coletando feeds de: {source_name}")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            entry['source_name'] = source_name
            all_entries.append(entry)

    # Limita a coleta para 12 a 16 matérias conforme solicitado
    target_count = min(len(all_entries), random.randint(12, 16))
    selected_entries = all_entries[:target_count]

    for entry in selected_entries:
        title = entry.get('title', 'Sem Título')
        summary = entry.get('summary', entry.get('description', 'Sem conteúdo disponível.'))
        link = entry.get('link', '')
        source_name = entry['source_name']

        print(f"Reescrevendo post: {title}")
        long_form_content = rewrite_to_long_form(title, summary)

        # Atribui uma imagem exclusiva do pool
        image_url = IMAGE_POOL[image_index % len(IMAGE_POOL)]
        image_index += 1

        processed_posts.append({
            "source": source_name,
            "title": title,
            "link": link,
            "image": image_url,
            "content": long_form_content
        })

    # Salva o resultado final no arquivo posts.json
    with open("posts.json", "w", encoding="utf-8") as f:
        json.dump(processed_posts, f, ensure_ascii=False, indent=4)

    print(f"\nAutomação concluída. {len(processed_posts)} posts salvos em posts.json")

if __name__ == "__main__":
    main()

