import os
import datetime
import urllib.request
import json
import feedparser
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# Feeds de referência para curadoria
FEEDS = [
    "https://venturebeat.com/category/ai/feed/",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"
]

def coletar_noticias():
    artigos = []
    for url in FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:2]:
            artigos.append({"titulo": entry.title, "link": entry.link, "resumo": entry.get("summary", "")})
    return artigos[:4]

def gerar_post_markdown(noticia):
    data_hoje = datetime.date.today().strftime("%Y-%m-%d")
    prompt = f"""
    Você é o editor sênior do CorticFlow (portal de IA e Tecnologia).
    Com base nesta notícia:
    Título: {noticia['titulo']}
    Fonte: {noticia['link']}
    Resumo: {noticia['resumo']}

    Gere um artigo completo em Markdown para o portal CorticFlow contendo:
    1. Frontmatter YAML no topo com:
       - title
       - date: {data_hoje}
       - category: (IA & Modelos, Hardware, Open-Source ou Big Techs)
       - tags: lista de tags
       - slug: slug-otimizado-seo
       - source_url: {noticia['link']}
    2. Texto do artigo (500 a 700 palavras) com tom técnico, análise de impacto de mercado e boas práticas de engenharia.
    3. Conclusão com o radar CorticFlow.
    Retorne estritamente o código Markdown, sem blocos extras de código.
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

def main():
    os.makedirs("content/posts", exist_ok=True)
    noticias = coletar_noticias()
    data_str = datetime.date.today().strftime("%Y%m%d")
    
    for i, noticia in enumerate(noticias):
        conteudo = gerar_post_markdown(noticia)
        filename = f"content/posts/{data_str}-artigo-{i+1}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(conteudo)
        print(f"Post gerado: {filename}")

if __name__ == "__main__":
    main()
