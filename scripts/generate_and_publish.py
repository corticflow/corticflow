import os
import sys
import datetime
import re
import math
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
                        "resumo": summary_clean[:600],
                        "categoria": item["category"]
                    })
        except Exception as e:
            print(f"Aviso no feed {item['url']}: {e}")
    return artigos[:4]

def calcular_tempo_leitura(texto):
    palavras = len(re.findall(r'\w+', texto))
    minutos = max(1, math.ceil(palavras / 200))
    return minutos, palavras

def gerar_post_gemini(noticia):
    data_hoje = datetime.date.today().strftime("%Y-%m-%d")
    
    prompt = f"""Você é o Editor-Chefe e Especialista Sênior em Tecnologia e Inteligência Artificial do portal CorticFlow.
Sua missão é redigir um artigo investigativo, técnico e aprofundado em português (estilo Ars Technica, MIT Technology Review e SemiAnalysis).

DADOS DA NOTÍCIA:
- Título: {noticia['titulo']}
- Categoria: {noticia['categoria']}
- Fonte: {noticia['link']}
- Resumo Base: {noticia['resumo']}

REGRAS RÍGIDAS DE EXTENSÃO E ESTRUTURA (OBRIGATÓRIO: MÍNIMO 1.200 PALAVRAS):
Você DEVE desenvolver cada uma das seções abaixo com riqueza de detalhes, sem atalhos ou resumos curtos:

# [Título Jornalístico Impactante e Exclusivo]

## 1. O Ponto de Inflexão e Contexto Histórico (Mínimo 3 parágrafos longos)
- Explique em detalhes o que foi anunciado e por que este anúncio ocorre neste momento.
- Descreva o cenário tecnológico anterior, as limitações que existiam e o que motivou essa inovação.

## 2. Engenharia e Arquitetura Sob o Capô (Mínimo 4 parágrafos longos + 1 Tabela Comparativa em Markdown)
- Explique a mecânica técnica fundamental (hardware, tensores, microarquitetura, algoritmos, pesos, consumo elétrico, latência ou throughput).
- Compare com as tecnologias concorrentes do mercado em uma tabela Markdown detalhada com métricas e tradeoffs.

## 3. Disputa de Mercado e Impacto nos Ecossistemas (Mínimo 3 parágrafos longos)
- Quem ganha e quem perde com este movimento (Nvidia, OpenAI, Google, Meta, Apple, Microsoft, startups e devs).
- Como isso altera a relação de custos (OpEx/CapEx) e a dependência de fornecedores.

## 4. Guia Prático para Engenheiros e Empresas (Mínimo 3 parágrafos longos)
- Casos de uso reais e cenários onde essa solução deve (ou não deve) ser adotada.
- Possíveis gargalos de implementação, migração e boas práticas recomendadas de engenharia.

## 5. O Veredito CorticFlow e Perspectiva Futura (Mínimo 2 parágrafos reflexivos)
- Conclusão analítica e prospectiva sobre os próximos 6 a 12 meses.

IMPORTANTE:
- Desenvolva cada parágrafo com explicações completas.
- Não inclua frontmatter YAML na sua resposta. Comece direto pelo título #."""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192}
    }

    models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
    for model in models:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            res = requests.post(endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
            if res.status_code == 200:
                data = res.json()
                corpo = data["candidates"][0]["content"]["parts"][0]["text"]
                corpo = re.sub(r'^```markdown\s*', '', corpo)
                corpo = re.sub(r'^```\s*', '', corpo)
                corpo = re.sub(r'\s*```$', '', corpo)
                
                h1_match = re.search(r'^#\s+(.+)$', corpo, re.MULTILINE)
                titulo_artigo = h1_match.group(1).replace('"', '').strip() if h1_match else noticia['titulo'].replace('"', '').strip()
                
                minutos_leitura, total_palavras = calcular_tempo_leitura(corpo)
                slug_limpo = re.sub(r'[^a-zA-Z0-9]+', '-', titulo_artigo.lower()).strip('-')[:60]
                
                frontmatter = f"""---
title: "{titulo_artigo}"
date: {data_hoje}
category: "{noticia['categoria']}"
tags: ["Inteligência Artificial", "Tecnologia", "Inovação", "Engenharia"]
slug: "{slug_limpo}"
author: "CorticFlow Editorial"
reading_time: "{minutos_leitura} min de leitura"
word_count: {total_palavras}
source_url: "{noticia['link']}"
---

"""
                return frontmatter + corpo
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
            print(f"Post denso gerado ({filename})")
            gerados += 1
            
    print(f"Total de posts criados: {gerados}")

if __name__ == "__main__":
    main()
