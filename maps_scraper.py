#!/usr/bin/env python3
"""
Google Maps Business Scraper & Lead Generator
Desenvolvido para prospecção ativa de Landing Pages locais.
"""

import asyncio
import os
import re
import json
import urllib.parse
from datetime import datetime
import pandas as pd
from playwright.async_api import async_playwright

SOCIAL_DELIVERY_DOMAINS = [
    "instagram.com",
    "facebook.com",
    "fb.com",
    "ifood.com.br",
    "cardapioweb.com",
    "linktr.ee",
    "wa.me",
    "whatsapp.com",
    "bio.site",
    "beacons.ai",
    "anota.ai",
    "ola.click",
    "goomer.app",
    "pedir.delivery",
    "cardapio.digital",
    "tiktok.com"
]

def classify_website(website_url: str):
    """Classifica o site da empresa para medir o potencial de venda."""
    if not website_url or website_url.strip() == "":
        return {
            "status": "SEM_SITE",
            "score": "🔥 OURO (Sem Site)",
            "observacao": "Prospect perfeito: precisa de presença profissional urgente."
        }
    
    clean_url = website_url.lower()
    for domain in SOCIAL_DELIVERY_DOMAINS:
        if domain in clean_url:
            return {
                "status": "REDE_SOCIAL_OU_APP",
                "score": "⚡ PRATA (Rede Social/App Terceiro)",
                "observacao": f"Usa intermediário ({domain}). Forte potencial para economizar comissões e ter site próprio."
            }
            
    return {
        "status": "SITE_PROPRIO",
        "score": "❄️ BRONZE (Já tem site)",
        "observacao": "Já tem site cadastrado. Avaliar se o site atual é antigo/ruim antes de abordar."
    }

def clean_phone_and_whatsapp(raw_phone: str):
    """Limpa o telefone e gera link direto de WhatsApp para o Brasil."""
    if not raw_phone:
        return "", ""
    
    digits = re.sub(r"\D", "", raw_phone)
    if digits.startswith("55") and len(digits) in [12, 13]:
        wa_number = digits
    elif len(digits) in [10, 11]:
        wa_number = f"55{digits}"
    else:
        wa_number = digits if digits else ""
        
    wa_link = f"https://wa.me/{wa_number}" if wa_number else ""
    return raw_phone.strip(), wa_link

async def extract_place_details(context, place_info: dict):
    """Abre a página do estabelecimento e extrai os detalhes completos."""
    page = await context.new_page()
    try:
        await page.goto(place_info["maps_url"], wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_selector("h1.DUwDvf", timeout=6000)
        
        # 1. Categoria
        categoria = place_info.get("categoria", "")
        cat_btn = page.locator("button.DkEaL")
        if await cat_btn.count() > 0:
            categoria = (await cat_btn.first.text_content() or "").strip()
            
        # 2. Endereço completo
        endereco = ""
        addr_btn = page.locator("button[data-item-id='address']")
        if await addr_btn.count() > 0:
            raw_addr = await addr_btn.first.get_attribute("aria-label") or await addr_btn.first.text_content() or ""
            endereco = raw_addr.replace("Endereço: ", "").strip()
            
        # 3. Telefone
        raw_phone = ""
        phone_btn = page.locator("button[data-item-id^='phone:tel:']")
        if await phone_btn.count() > 0:
            raw_p = await phone_btn.first.get_attribute("aria-label") or await phone_btn.first.text_content() or ""
            raw_phone = raw_p.replace("Telefone: ", "").replace("", "").strip()
            
        telefone, wa_link = clean_phone_and_whatsapp(raw_phone)
        
        # 4. Website
        website = ""
        web_btn = page.locator("a[data-item-id='authority']")
        if await web_btn.count() > 0:
            website = (await web_btn.first.get_attribute("href") or "").strip()
            
        classification = classify_website(website)
        
        # 5. Horário de funcionamento
        horario = ""
        hours_btn = page.locator("div[data-item-id='oh'], button[data-item-id='oh']")
        if await hours_btn.count() > 0:
            raw_h = await hours_btn.first.get_attribute("aria-label") or await hours_btn.first.text_content() or ""
            horario = raw_h.replace("", "").strip()
            
        # 6. Foto de capa em alta definição
        foto_capa = ""
        # Tenta múltiplos seletores de imagem de capa do Google Maps
        photo_locators = [
            page.locator("button[aria-label*='Foto de'] img, button[aria-label*='foto de'] img"),
            page.locator("button[jsaction*='heroHeaderImage'] img"),
            page.locator("button.aoRNLd img")
        ]
        for loc in photo_locators:
            if await loc.count() > 0:
                raw_src = await loc.first.get_attribute("src") or ""
                if raw_src and "googleusercontent.com" in raw_src:
                    foto_capa = re.sub(r"=w\d+-h\d+-k-no", "=w1200-h800-k-no", raw_src)
                    break
                    
        # 7. Nota e total de avaliações refinados
        nota = place_info.get("nota", "")
        avaliacoes = place_info.get("avaliacoes", "")
        rating_elem = page.locator("div.F7nice")
        if await rating_elem.count() > 0:
            text_r = await rating_elem.first.text_content() or ""
            match = re.search(r"(\d+,\d+)\s*(?:\(([\d\.]+)\))?", text_r)
            if match:
                nota = match.group(1)
                if match.group(2):
                    avaliacoes = match.group(2)
                    
        return {
            "nome": place_info["nome"],
            "categoria": categoria,
            "nota": nota,
            "total_avaliacoes": avaliacoes,
            "telefone": telefone,
            "whatsapp_link": wa_link,
            "website": website,
            "status_lead": classification["status"],
            "score_lead": classification["score"],
            "diagnostico_comercial": classification["observacao"],
            "endereco": endereco,
            "horario": horario,
            "foto_capa": foto_capa,
            "maps_url": place_info["maps_url"],
            "coletado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        print(f"  [Aviso] Erro ao extrair detalhes de '{place_info.get('nome')}': {e}")
        return None
    finally:
        await page.close()

async def scrape_google_maps(
    termo_busca: str,
    max_resultados: int = 15,
    apenas_sem_site: bool = False,
    min_nota: float = 0.0,
    headless: bool = True
):
    """
    Realiza a pesquisa no Google Maps, rola a lista de resultados e extrai cada empresa.
    """
    print(f"\n🚀 Iniciando busca no Google Maps: '{termo_busca}'")
    print(f"🎯 Meta: coletar {max_resultados} leads qualificados...")
    if apenas_sem_site:
        print("🔍 Filtro ativo: Apenas leads SEM SITE ou com redes sociais/apps!")
        
    dados_finais = []
    
    # Se filtrando sem site, precisamos coletar uma lista maior inicial para suprir os descartes
    meta_busca_bruta = max_resultados * 3 if apenas_sem_site else max_resultados
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            locale="pt-BR",
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        search_page = await context.new_page()
        query_encoded = urllib.parse.quote(termo_busca)
        url = f"https://www.google.com/maps/search/{query_encoded}?hl=pt-BR"
        
        print(f"🌐 Acessando Google Maps...")
        await search_page.goto(url, wait_until="domcontentloaded", timeout=25000)
        
        try:
            await search_page.wait_for_selector("div[role='feed'], a.hfpxzc", timeout=15000)
        except Exception:
            print("❌ Não foi possível carregar os resultados da busca. Tente refinar o termo.")
            await browser.close()
            return []
            
        feed = search_page.locator("div[role='feed']")
        places_brutos = []
        links_vistos = set()
        scroll_attempts = 0
        max_scrolls = 25
        
        print("📜 Rolando a lista de estabelecimentos...")
        while len(places_brutos) < meta_busca_bruta and scroll_attempts < max_scrolls:
            cards = search_page.locator("a.hfpxzc")
            count = await cards.count()
            
            for i in range(count):
                link_el = cards.nth(i)
                nome = await link_el.get_attribute("aria-label") or ""
                href = await link_el.get_attribute("href") or ""
                
                if href and href not in links_vistos:
                    links_vistos.add(href)
                    places_brutos.append({
                        "nome": nome,
                        "maps_url": href
                    })
                    if len(places_brutos) >= meta_busca_bruta:
                        break
                        
            print(f"  Encontrados até agora: {len(places_brutos)} empresas...")
            if len(places_brutos) >= meta_busca_bruta:
                break
                
            if await feed.count() > 0:
                await feed.evaluate("node => node.scrollTop = node.scrollHeight")
            await search_page.wait_for_timeout(1800)
            scroll_attempts += 1
            
        print(f"\n✅ {len(places_brutos)} estabelecimentos pré-selecionados! Analisando detalhes...")
        
        for idx, item in enumerate(places_brutos, 1):
            if len(dados_finais) >= max_resultados:
                print(f"\n🎯 Meta de {max_resultados} leads qualificados atingida com sucesso!")
                break
                
            print(f"[{idx}/{len(places_brutos)}] Processando: {item['nome']}...")
            detalhes = await extract_place_details(context, item)
            
            if detalhes:
                try:
                    nota_float = float(detalhes["nota"].replace(",", ".")) if detalhes["nota"] else 0.0
                except ValueError:
                    nota_float = 0.0
                    
                if nota_float < min_nota:
                    print(f"  ⏭ Ignorado por nota ({nota_float} < {min_nota})")
                    continue
                    
                if apenas_sem_site and detalhes["status_lead"] == "SITE_PROPRIO":
                    print(f"  ⏭ Ignorado (já possui site próprio)")
                    continue
                    
                print(f"  ⭐ {detalhes['score_lead']} | Tel: {detalhes['telefone'] or 'N/A'}")
                dados_finais.append(detalhes)
                
            await asyncio.sleep(0.4)
            
        await browser.close()
        
    return dados_finais

def exportar_dados(dados: list, termo_busca: str, pasta_saida: str = "dados_leads"):
    """Salva os leads em formatos Excel (.xlsx), CSV (.csv) e JSON (.json)."""
    if not dados:
        print("\n⚠️ Nenhum lead atendeu aos critérios selecionados.")
        return None
        
    os.makedirs(pasta_saida, exist_ok=True)
    slug = re.sub(r"[^\w\s-]", "", termo_busca).strip().lower().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{pasta_saida}/leads_{slug}_{timestamp}"
    
    # 1. JSON (para o gerador de Landing Pages)
    json_path = f"{base_name}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
        
    # 2. DataFrame Pandas para Excel e CSV
    df = pd.DataFrame(dados)
    colunas_ordem = [
        "score_lead",
        "nome",
        "categoria",
        "nota",
        "total_avaliacoes",
        "telefone",
        "whatsapp_link",
        "website",
        "diagnostico_comercial",
        "endereco",
        "horario",
        "foto_capa",
        "maps_url"
    ]
    colunas_presentes = [c for c in colunas_ordem if c in df.columns]
    df = df[colunas_presentes]
    
    csv_path = f"{base_name}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    
    excel_path = f"{base_name}.xlsx"
    try:
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Leads Google Maps")
    except Exception as e:
        print(f"Erro ao salvar Excel: {e}")
        excel_path = None
        
    print("\n" + "="*55)
    print(f"🎉 SUCESSO! {len(dados)} LEADS EXTRAÍDOS E QUALIFICADOS:")
    print(f"📁 JSON (para gerar Landing Pages): {json_path}")
    print(f"📊 CSV (Planilha comercial):       {csv_path}")
    if excel_path:
        print(f"📗 Excel (.xlsx formatado):         {excel_path}")
    print("="*55)
    
    return {
        "json": json_path,
        "csv": csv_path,
        "excel": excel_path,
        "total": len(dados)
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Google Maps Leads Scraper para Landing Pages")
    parser.add_argument("busca", type=str, nargs="?", default="", help="Termo de pesquisa (ex: 'barbearia sorocaba sp')")
    parser.add_argument("--qtd", type=int, default=15, help="Quantidade máxima de estabelecimentos qualificados (padrão: 15)")
    parser.add_argument("--sem-site", action="store_true", help="Filtrar apenas estabelecimentos sem site próprio")
    parser.add_argument("--min-nota", type=float, default=0.0, help="Filtrar por nota mínima (ex: 4.0)")
    parser.add_argument("--visible", action="store_true", help="Abrir o navegador visível (não-headless)")
    
    args = parser.parse_args()
    
    busca = args.busca
    if not busca:
        print("\n=== GOOGLE MAPS LEAD GENERATOR ===")
        busca = input("Digite o nicho e a cidade que deseja buscar (ex: barbearia sorocaba): ").strip()
        if not busca:
            print("Busca cancelada.")
            exit(0)
            
        qtd_input = input("Quantos leads você quer extrair? (padrão: 10): ").strip()
        qtd = int(qtd_input) if qtd_input.isdigit() else 10
        
        filtro_site = input("Buscar APENAS quem NÃO tem site? (S/n): ").strip().lower()
        apenas_sem_site = filtro_site != "n"
        
        leads = asyncio.run(scrape_google_maps(
            termo_busca=busca,
            max_resultados=qtd,
            apenas_sem_site=apenas_sem_site,
            min_nota=0.0,
            headless=True
        ))
        exportar_dados(leads, busca)
    else:
        leads = asyncio.run(scrape_google_maps(
            termo_busca=busca,
            max_resultados=args.qtd,
            apenas_sem_site=args.sem_site,
            min_nota=args.min_nota,
            headless=not args.visible
        ))
        exportar_dados(leads, busca)
