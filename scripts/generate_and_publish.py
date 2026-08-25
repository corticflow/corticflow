import os
import sys
import datetime
import re
import math
import json
import requests
import feedparser

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("ERRO CRÍTICO: Secret GEMINI_API_KEY não encontrado.")
    sys.exit(1)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

FONTES_RSS = [
    {"url": "https://venturebeat.com/category/ai/feed/", "category": "IA & Modelos", "badge": "IA & Pesquisa", "img": "cat-ai.jpeg"},
    {"url": "https://thedecoder.com/feed/", "category": "IA & Modelos", "badge": "Modelos & LLMs", "img": "cat-ai.jpeg"},
    {"url": "https://www.technologyreview.com/feed/", "category": "IA & Modelos", "badge": "Deep Tech", "img": "cat-ai.jpeg"},
    {"url": "https://theverge.com/rss/ai-artificial-intelligence/index.xml", "category": "Apple & iOS", "badge": "Apple & Big Tech", "img": "cat-business.jpeg"},
    {"url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "Mercado & Big Techs", "badge": "Startups & Capital", "img": "cat-business.jpeg"},
    {"url": "https://www.wired.com/feed/tag/ai/latest/rss", "category": "Inovação Global", "badge": "Inovação", "img": "cat-business.jpeg"},
    {"url": "https://feeds.arstechnica.com/arstechnica/index", "category": "Windows & PC", "badge": "Hardware & Chips", "img": "cat-tutorials.jpeg"},
    {"url": "https://thenewstack.io/feed/", "category": "Open-Source & Devs", "badge": "Devs & Nuvem", "img": "cat-tools.jpeg"},
    {"url": "https://news.ycombinator.com/rss", "category": "Open-Source & Devs", "badge": "Hacker News", "img": "cat-tools.jpeg"},
    {"url": "https://tecnoblog.net/feed/", "category": "Brasil & Telecom", "badge": "Brasil & Tech", "img": "cat-business.jpeg"},
    {"url": "https://olhardigital.com.br/feed/", "category": "Tecnologia Geral", "badge": "Tecnologia BR", "img": "cat-tutorials.jpeg"}
]

def coletar_noticias(limite_total=10):
    artigos = []
    for fonte in FONTES_RSS:
        try:
            resp = requests.get(fonte["url"], headers=HEADERS, timeout=12)
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:2]:
                title = getattr(entry, "title", "").strip()
                link = getattr(entry, "link", "").strip()
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                summary_clean = re.sub(r'<[^>]+>', '', summary).strip()
                
                if title and link and not any(a["titulo"] == title for a in artigos):
                    artigos.append({
                        "titulo": title,
                        "link": link,
                        "resumo": summary_clean[:600],
                        "categoria": fonte["category"],
                        "badge": fonte["badge"],
                        "img": fonte["img"]
                    })
                    if len(artigos) >= limite_total:
                        return artigos
        except Exception as e:
            print(f"Aviso no feed {fonte['url']}: {e}")
    return artigos

def calcular_tempo_leitura(texto):
    palavras = len(re.findall(r'\w+', texto))
    minutos = max(1, math.ceil(palavras / 200))
    return f"{minutos} min", palavras

def gerar_post_gemini(noticia):
    prompt = f"""Você é o redator técnico sênior do CorticFlow.
Transforme esta notícia em um artigo seguindo ESTRITAMENTE a estrutura abaixo:

DADOS DA NOTÍCIA:
- Título: {noticia['titulo']}
- Categoria Sugerida: {noticia['categoria']}
- Fonte Original: {noticia['link']}
- Resumo: {noticia['resumo']}

ESTRUTURA OBRIGATÓRIA:
# [Crie um Título Forte, Curto e Impactante em Português]

[Subtítulo/Linha de apoio explicando a essência da matéria em 1 frase elegante]

### [Subtítulo da Seção 1: Contexto e Acontecimento]
(Mínimo de 2 parágrafos detalhados explicando o contexto do acontecimento)

### [Subtítulo da Seção 2: O Impacto no Hardware ou Ecossistema]
(Mínimo de 2 parágrafos dissecando a parte técnica, especificações de chips, TOPS, energia ou latência)

*Insira uma conclusão ou insight rápido sobre o que esperar do mercado nas próximas semanas.*

IMPORTANTE:
- Não inclua blocos ```markdown.
- Não inclua o frontmatter no texto de resposta."""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096}
    }

    models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
    for model in models:
        endpoint = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){model}:generateContent?key={GEMINI_API_KEY}"
        try:
            res = requests.post(endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=45)
            if res.status_code == 200:
                data = res.json()
                corpo = data["candidates"][0]["content"]["parts"][0]["text"]
                corpo = re.sub(r'^```markdown\s*', '', corpo)
                corpo = re.sub(r'^```\s*', '', corpo)
                corpo = re.sub(r'\s*```$', '', corpo)
                
                tempo_str, total_palavras = calcular_tempo_leitura(corpo)
                
                h1_m = re.search(r'^#\s+(.+)$', corpo, re.MULTILINE)
                titulo_final = h1_m.group(1).strip() if h1_m else noticia['titulo']
                
                linhas = [l.strip() for l in corpo.split('\n') if l.strip() and not l.startswith('#')]
                resumo_card = linhas[0] if linhas else noticia['resumo'][:160]

                cabecalho = f"""---
categoria: "{noticia['categoria']}"
tempo_leitura: "{tempo_str}"
fonte_original: "{noticia['link']}"
---

"""
                return {
                    "md": cabecalho + corpo,
                    "titulo": titulo_final,
                    "categoria": noticia["categoria"],
                    "badge": noticia["badge"],
                    "tempo_leitura": tempo_str,
                    "resumo": resumo_card[:200] + "...",
                    "link_fonte": noticia["link"],
                    "img": noticia["img"],
                    "corpo": corpo
                }
        except Exception as err:
            print(f"Erro em {model}: {err}")
    return None

def main():
    os.makedirs("content/posts", exist_ok=True)
    noticias = coletar_noticias(limite_total=10)
    data_str = datetime.date.today().strftime("%Y%m%d")
    data_formatada = datetime.date.today().strftime("%d/%m/%Y")
    
    posts_json_data = []
    gerados = 0

    for i, noticia in enumerate(noticias):
        res = gerar_post_gemini(noticia)
        if res:
            filename = f"content/posts/{data_str}-artigo-{i+1}.md"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(res["md"])
            
            posts_json_data.append({
                "id": i + 1,
                "titulo": res["titulo"],
                "categoria": res["categoria"],
                "badge": res["badge"],
                "tempo_leitura": res["tempo_leitura"],
                "data": data_formatada,
                "resumo": res["resumo"],
                "img": res["img"],
                "link_fonte": res["link_fonte"],
                "corpo": res["corpo"]
            })
            print(f"[{i+1}/{len(noticias)}] Post gerado: {filename}")
            gerados += 1
            
    with open("posts.json", "w", encoding="utf-8") as f:
        json.dump(posts_json_data, f, ensure_ascii=False, indent=2)

    print(f"Sucesso: {gerados} artigos salvos e posts.json atualizado!")

if __name__ == "__main__":
    main()
