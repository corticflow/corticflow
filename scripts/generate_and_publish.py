import os
import sys
import datetime
import re
import math
import requests
import feedparser

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("ERRO CRÍTICO: Secret GEMINI_API_KEY não encontrado.")
    sys.exit(1)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

FEEDS = [
    {"url": "https://venturebeat.com/category/ai/feed/", "category": "Hardware & Chips", "badge": "Hardware"},
    {"url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "Mercado & Big Techs", "badge": "Mercado"},
    {"url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "category": "IA & Modelos", "badge": "Inteligência Artificial"}
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
                        "categoria": item["category"],
                        "badge": item["badge"]
                    })
        except Exception as e:
            print(f"Aviso no feed {item['url']}: {e}")
    return artigos[:4]

def calcular_tempo_leitura(texto):
    palavras = len(re.findall(r'\w+', texto))
    minutos = max(1, math.ceil(palavras / 200))
    return minutos, palavras

def gerar_artigo_completo(noticia):
    prompt = f"""Você é o Editor-Chefe e Especialista Sênior em Tecnologia e Inteligência Artificial do portal CorticFlow.
Sua missão é redigir um artigo longo, técnico e aprofundado em português sobre esta notícia.

Título: {noticia['titulo']}
Categoria: {noticia['categoria']}
Fonte: {noticia['link']}
Resumo: {noticia['resumo']}

ESTRUTURA OBRIGATÓRIA (LONG-FORM - MÍNIMO 1.200 PALAVRAS):
1. <h2> O Ponto de Inflexão (Contexto Histórico) — Mínimo 3 parágrafos densos.
2. <h2> Engenharia & Arquitetura Sob o Capô — Mínimo 4 parágrafos técnicos detalhando métricas, tradeoffs e funcionamento.
3. <h2> Disputa de Mercado e Impacto nos Ecossistemas — Mínimo 3 parágrafos sobre Big Techs, startups e devs.
4. <h2> Guia Prático e Lições de Engenharia — Mínimo 3 parágrafos de boas práticas e aplicação real.
5. <h2> O Veredito CorticFlow — Conclusão analítica de mercado para os próximos meses.

IMPORTANTE:
- Escreva o corpo do artigo diretamente em tags HTML limpas (<h2>, <p>, <ul>, <li>, <strong>).
- Não use blocos de código ```html. Retorne apenas o conteúdo HTML interno do artigo."""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192}
    }

    models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
    for model in models:
        endpoint = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){model}:generateContent?key={GEMINI_API_KEY}"
        try:
            res = requests.post(endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
            if res.status_code == 200:
                data = res.json()
                html_body = data["candidates"][0]["content"]["parts"][0]["text"]
                html_body = re.sub(r'^```html\s*', '', html_body)
                html_body = re.sub(r'^```\s*', '', html_body)
                html_body = re.sub(r'\s*```$', '', html_body)
                return html_body
        except Exception as err:
            print(f"Erro em {model}: {err}")
    return None

def atualizar_index_html(artigos_gerados):
    if not os.path.exists("index.html"):
        print("index.html não encontrado na raiz.")
        return

    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    cards_html = ""
    data_hoje = datetime.date.today().strftime("%d/%m/%Y")

    for i, item in enumerate(artigos_gerados):
        minutos, palavras = calcular_tempo_leitura(item["corpo_html"])
        cards_html += f"""
        <article class="cortic-card" style="background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 28px; margin-bottom: 32px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);">
            <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 12px;">
                <span style="background: #00E5FF; color: #0B0F19; font-weight: bold; font-size: 12px; padding: 4px 10px; border-radius: 20px; text-transform: uppercase;">{item['badge']}</span>
                <span style="color: #94a3b8; font-size: 14px;">📅 {data_hoje} • ⏱️ {minutos} min de leitura ({palavras} palavras)</span>
            </div>
            <h2 style="color: #FFFFFF; font-size: 24px; margin-top: 0; line-height: 1.3;">{item['titulo']}</h2>
            <div class="article-body" style="color: #cbd5e1; font-size: 16px; line-height: 1.8; margin-top: 20px;">
                {item['corpo_html']}
            </div>
            <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #334155; font-size: 13px; color: #64748b;">
                Fonte Original: <a href="{item['link']}" target="_blank" style="color: #00E5FF; text-decoration: none;">{item['link']}</a>
            </div>
        </article>
        """

    # Injetar dentro da seção de artigos do index.html
    if "<!-- POSTS_CONTAINER -->" in html:
        novo_html = re.sub(
            r'<!-- POSTS_CONTAINER -->.*?<!-- END_POSTS_CONTAINER -->',
            f'<!-- POSTS_CONTAINER -->\n{cards_html}\n<!-- END_POSTS_CONTAINER -->',
            html,
            flags=re.DOTALL
        )
    elif "<main" in html:
        # Substitui o conteúdo da tag main
        novo_html = re.sub(
            r'(<main[^>]*>).*?(</main>)',
            f'\\1\n<div style="max-width: 900px; margin: 0 auto; padding: 20px;">\n{cards_html}\n</div>\n\\2',
            html,
            flags=re.DOTALL
        )
    else:
        novo_html = html

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(novo_html)
    print("index.html atualizado com sucesso com as novas matérias long-form!")

def main():
    os.makedirs("content/posts", exist_ok=True)
    noticias = coletar_noticias()
    artigos_gerados = []

    for noticia in noticias:
        corpo = gerar_artigo_completo(noticia)
        if corpo:
            artigos_gerados.append({
                "titulo": noticia["titulo"],
                "link": noticia["link"],
                "badge": noticia["badge"],
                "corpo_html": corpo
            })

    if artigos_gerados:
        atualizar_index_html(artigos_gerados)
        print(f"Total de {len(artigos_gerados)} matérias longas inseridas no site.")

if __name__ == "__main__":
    main()
