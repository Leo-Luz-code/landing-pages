#!/usr/bin/env python3
"""
Gerador Automático de Landing Pages para Leads do Google Maps
Renderiza templates profissionais baseados nos dados coletados pelo scraper.
"""

import os
import re
import json
import glob
import urllib.parse
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent / "templates"
OUTPUT_DIR = Path(__file__).parent / "sites_gerados"

CATEGORY_MAPPING = {
    "gastronomia": [
        "pizza", "pizzaria", "hambúrguer", "hamburgueria", "restaurante", "bar", 
        "comida", "lanche", "sushi", "café", "cafeteria", "confeitaria", 
        "padaria", "choperia", "gastronomia", "churrascaria", "açaí", "sorveteria"
    ],
    "barbearia_beleza": [
        "barbearia", "barbeiro", "corte", "salão", "cabeleireiro", "cabelo", 
        "estética", "beleza", "unha", "manicure", "pedicure", "sobrancelha", 
        "cílios", "tatuagem", "tattoo", "piercing", "depilação", "spa"
    ],
    "saude": [
        "dentista", "odontologia", "odonto", "médico", "médica", "clínica", 
        "saúde", "fisioterapia", "fisioterapeuta", "psicologia", "psicólogo", 
        "veterinário", "veterinária", "oftalmologia", "pediatra", "nutricionista", "quiropraxia"
    ],
    "servicos_locais": [
        "mecânica", "oficina", "auto center", "pneus", "funilaria", "pintura", 
        "martelinho", "vidraçaria", "serralheria", "marmoraria", "marcenaria", 
        "ar-condicionado", "climatização", "eletricista", "encanador", "chaveiro", 
        "desentupidora", "dedetizadora", "construção", "reforma", "gesso"
    ]
}

def detect_template(item: dict) -> str:
    """Detecta automaticamente o melhor template baseado na categoria e nome do negócio."""
    text = f"{item.get('categoria', '')} {item.get('nome', '')}".lower()
    
    # Ordem prioritária de checagem
    priority_order = ["barbearia_beleza", "saude", "gastronomia", "servicos_locais"]
    
    for template_name in priority_order:
        keywords = CATEGORY_MAPPING[template_name]
        for kw in keywords:
            # Usa regex para garantir match de palavra ou início exato, evitando 'bar' em 'barbearia'
            pattern = rf"\b{re.escape(kw)}"
            if re.search(pattern, text):
                return template_name
                
    return "servicos_locais"

def slugify(text: str) -> str:
    """Transforma o nome do negócio em slug seguro para pastas."""
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", text)[:50]

def create_pitch_message(item: dict, demo_url: str) -> str:
    """Cria uma mensagem personalizada de abordagem comercial para WhatsApp."""
    nome = item.get("nome", "Empresa")
    nota = item.get("nota", "5.0")
    total_av = item.get("total_avaliacoes", "+50")
    
    msg = (
        f"Olá, tudo bem? Aqui é o Leonardo!\n\n"
        f"Estava pesquisando os melhores serviços da nossa região e vi que a *{nome}* "
        f"tem uma reputação excelente no Google Maps (nota {nota} com mais de {total_av} avaliações!).\n\n"
        f"Notei que vocês ainda não tinham um site próprio oficial para receber e converter quem busca por vocês no Google todos os dias.\n\n"
        f"Para mostrar na prática como vocês podem se destacar ainda mais, montei uma prévia exclusiva e sem compromisso de como ficaria a presença digital oficial de vocês:\n\n"
        f"👉 {demo_url}\n\n"
        f"O site já está otimizado para celulares, com botão de WhatsApp direto para a equipe de vocês e mapa integrado. "
        f"Se vocês gostarem e fizer sentido, podemos colocar no ar no próprio domínio oficial de vocês esta semana. O que acharam?"
    )
    return msg

def generate_sites(json_file_path: str, template_override: str = None):
    """Lê o JSON de leads e gera os sites estáticos completos."""
    with open(json_file_path, "r", encoding="utf-8") as f:
        leads = json.load(f)
        
    if not leads:
        print(f"⚠️ O arquivo {json_file_path} está vazio.")
        return
        
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    generated_list = []
    
    print(f"\n🚀 Gerando Landing Pages a partir de: {json_file_path}")
    print(f"Total de estabelecimentos: {len(leads)}")
    print("=" * 60)
    
    for idx, item in enumerate(leads, 1):
        # Determina o template
        tmpl_name = template_override if template_override else detect_template(item)
        tmpl_file = f"{tmpl_name}.html"
        
        try:
            template = env.get_template(tmpl_file)
        except Exception as e:
            print(f"❌ Erro ao carregar template '{tmpl_file}': {e}. Usando 'servicos_locais.html'")
            template = env.get_template("servicos_locais.html")
            tmpl_name = "servicos_locais"
            
        # Nome da pasta
        slug = slugify(item.get("nome", f"lead_{idx}"))
        site_folder = OUTPUT_DIR / slug
        site_folder.mkdir(parents=True, exist_ok=True)
        
        # Renderiza a página
        html_content = template.render(**item)
        index_file = site_folder / "index.html"
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        demo_url = f"preview/{slug}/index.html"
        pitch_msg = create_pitch_message(item, f"https://seusite.com.br/{slug}")
        
        generated_list.append({
            **item,
            "slug": slug,
            "template_usado": tmpl_name,
            "local_path": str(index_file),
            "demo_rel_url": f"{slug}/index.html",
            "pitch_msg": pitch_msg
        })
        
        print(f"[{idx}/{len(leads)}] ✅ {item['nome']}")
        print(f"   Template: {tmpl_name.upper()} | Pasta: sites_gerados/{slug}/")
        
    # Gera um Painel de Controle (Dashboard) para você gerenciar os sites criados!
    generate_dashboard(generated_list)
    
    print("\n" + "=" * 60)
    print("🎉 SUCESSO! TODAS AS LANDING PAGES FORAM GERADAS!")
    print(f"📂 Diretório dos sites: {OUTPUT_DIR}")
    print(f"📊 Painel de Navegação: {OUTPUT_DIR}/index.html")
    print("=" * 60)
    return generated_list

def generate_dashboard(generated_list: list):
    """Gera um painel com listagem visual de todos os sites prontos e mensagens de pitch."""
    dashboard_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel de Landing Pages Geradas | Prospecção Ativa</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lucide@latest"></script>
</head>
<body class="bg-[#0F172A] text-slate-100 font-sans p-6 md:p-12">
    <div class="max-w-6xl mx-auto">
        <header class="mb-10 flex flex-col md:flex-row md:items-center justify-between gap-4 pb-8 border-b border-slate-800">
            <div>
                <span class="text-xs font-bold uppercase tracking-widest text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">Esteira Comercial</span>
                <h1 class="text-3xl font-extrabold text-white mt-3">Painel de Landing Pages Geradas</h1>
                <p class="text-slate-400 text-sm mt-1">Sites prontos para demonstração e pitch de prospecção para os donos.</p>
            </div>
            <div class="flex items-center gap-3">
                <span class="bg-slate-800 border border-slate-700 px-4 py-2 rounded-xl text-sm font-bold text-slate-200">
                    Total: {len(generated_list)} Sites Criados
                </span>
            </div>
        </header>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    """
    
    for item in generated_list:
        slug = item["slug"]
        nome = item["nome"]
        nota = item.get("nota", "5.0")
        av = item.get("total_avaliacoes", "+50")
        score = item.get("score_lead", "LEAD")
        tel = item.get("telefone", "Sem telefone")
        tmpl = item.get("template_usado", "geral").replace("_", " ").upper()
        wa_link = item.get("whatsapp_link", "")
        encoded_pitch = urllib.parse.quote(item["pitch_msg"])
        pitch_wa_url = f"{wa_link}?text={encoded_pitch}" if wa_link else "#"

        dashboard_html += f"""
        <div class="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-6 flex flex-col justify-between shadow-xl transition">
            <div>
                <div class="flex items-center justify-between gap-2 mb-3">
                    <span class="text-xs font-bold px-2.5 py-1 rounded-md bg-slate-800 text-emerald-400 border border-emerald-500/20">{tmpl}</span>
                    <span class="text-xs font-semibold text-amber-400 flex items-center gap-1">★ {nota} ({av})</span>
                </div>
                <h2 class="font-bold text-lg text-white mb-1 line-clamp-1" title="{nome}">{nome}</h2>
                <p class="text-xs text-slate-400 mb-4">{score}</p>
                <p class="text-xs text-slate-300 flex items-center gap-1 mb-6">
                    <i data-lucide="phone" class="w-3.5 h-3.5 text-slate-500"></i>
                    {tel}
                </p>
            </div>

            <div class="space-y-2 pt-4 border-t border-slate-800">
                <a href="{item['demo_rel_url']}" target="_blank" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2.5 rounded-xl text-xs flex items-center justify-center gap-2 transition">
                    <i data-lucide="external-link" class="w-4 h-4"></i>
                    <span>Ver Landing Page Pronta</span>
                </a>

                <a href="{pitch_wa_url}" target="_blank" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2.5 rounded-xl text-xs flex items-center justify-center gap-2 transition">
                    <i data-lucide="message-circle" class="w-4 h-4"></i>
                    <span>Enviar Pitch no WhatsApp</span>
                </a>
            </div>
        </div>
        """
        
    dashboard_html += """
        </div>
    </div>
    <script>lucide.createIcons();</script>
</body>
</html>
    """
    
    with open(OUTPUT_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(dashboard_html)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gerador de Landing Pages para Leads do Google Maps")
    parser.add_argument("arquivo_json", type=str, nargs="?", default="", help="Caminho do arquivo .json de leads")
    parser.add_argument("--todos", action="store_true", help="Gerar landing pages para TODOS os arquivos JSON em dados_leads/")
    parser.add_argument("--template", type=str, choices=["gastronomia", "barbearia_beleza", "saude", "servicos_locais"], help="Forçar um template específico")
    
    args = parser.parse_args()
    
    if args.todos:
        json_files = glob.glob("dados_leads/*.json")
        if not json_files:
            print("❌ Nenhum arquivo JSON encontrado em dados_leads/.")
            exit(1)
        todos_leads = []
        for jf in json_files:
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    todos_leads.extend(json.load(f))
            except Exception as e:
                print(f"Aviso ao ler {jf}: {e}")
        # Salva merge temporário e gera
        merged_path = "dados_leads/leads_consolidados.json"
        with open(merged_path, "w", encoding="utf-8") as f:
            json.dump(todos_leads, f, ensure_ascii=False, indent=2)
        generate_sites(merged_path, args.template)
    else:
        target_file = args.arquivo_json
        if not target_file:
            json_files = sorted(glob.glob("dados_leads/*.json"), key=os.path.getmtime, reverse=True)
            # Ignora consolidado se houver
            json_files = [f for f in json_files if "consolidado" not in f]
            if json_files:
                target_file = json_files[0]
                print(f"📂 Selecionado automaticamente o arquivo mais recente: {target_file}")
            else:
                print("❌ Nenhum arquivo JSON encontrado em dados_leads/. Execute o scraper primeiro!")
                exit(1)
                
        generate_sites(target_file, args.template)
