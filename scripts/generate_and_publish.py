import os
import sys
import datetime
import re
import requests
import feedparser

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("ERRO CRÍTICO: Secret GEMINI_API_KEY não encontrado no ambiente do GitHub.")
    sys.exit(1)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

FEEDS = [
    {"url": "https://venturebeat.com/category/ai/feed/", "category": "IA & Modelos"},
    {"url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "Mercado & Big Techs"},
    {"url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "category": "Hardware & Inovação"}
]

def coletar_noticias():
    artigos = []
    for item in FEEDS:
        try:
            resp = requests.get(item["url"], headers=HEADERS, timeout=15)
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:2]:
                title = getattr(entry, "title", "").strip()
                link = getattr(entry, "link", "").strip()
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                summary_clean = re.sub(r'<[^>]+>', '', summary).strip()
                if title and link:
                    artigos.append({
                        "titulo": title,
                        "link": link,
                        "resumo": summary_clean[:500],
                        "categoria": item["category"]
                    })
        except Exception as e:
            print(f"Aviso no feed {item['url']}: {e}")
    return artigos[:4]

def gerar_post_gemini(noticia):
    data_hoje = datetime.date.today().strftime("%Y-%m-%d")
    prompt = f"""Você é o editor sênior do CorticFlow (portal de IA e Tecnologia).
Escreva um artigo técnico e aprofundado em português sobre esta notícia:

Título: {noticia['titulo']}
Categoria: {noticia['categoria']}
Fonte Original: {noticia['link']}
Resumo: {noticia['resumo']}

Estrutura obrigatória:
1. No topo, inclua EXATAMENTE o frontmatter YAML entre '---':
---
title: "{noticia['titulo'].replace('\"', '')}"
date: {data_hoje}
category: "{noticia['categoria']}"
tags: ["Inteligência Artificial", "Tecnologia", "Inovação"]
slug: "{re.sub(r'[^a-zA-Z0-9]+', '-', noticia['titulo'].lower())[:60]}"
source_url: "{noticia['link']}"
---

2. Corpo do artigo em Markdown (500 a 700 palavras):
- Introdução contextualizando o anúncio.
- Análise técnica detalhada dos impactos práticos e de engenharia.
- Relevância para o mercado corporativo e desenvolvedores.
- Pílula técnica ou lição prática derivada da notícia.
- Conclusão com a visão do CorticFlow.

Retorne APENAS o conteúdo Markdown puro."""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}
    }

    # Modelos com fallback automático
    models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
    for model in models:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            res = requests.post(endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
            if res.status_code == 200:
                data = res.json()
                texto = data["candidates"][0]["content"]["parts"][0]["text"]
                texto = re.sub(r'^```markdown\s*', '', texto)
                texto = re.sub(r'^```\s*', '', texto)
                texto = re.sub(r'\s*```$', '', texto)
                return texto
            else:
                print(f"Tentativa {model} retornou status {res.status_code}")
        except Exception as err:
            print(f"Erro em {model}: {err}")
    return None

def main():
    os.makedirs("content/posts", exist_ok=True)
    noticias = coletar_noticias()
    data_str = datetime.date.today().strftime("%Y%m%d")
    
    gerados = 0
    for i, noticia in enumerate(noticias):
        conteudo = gerar_post_gemini(noticia)
        if conteudo:
            filename = f"content/posts/{data_str}-artigo-{i+1}.md"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(conteudo)
            print(f"Post gerado com sucesso: {filename}")
            gerados += 1
            
    print(f"Total de posts criados: {gerados}")

if __name__ == "__main__":
    main()
