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

ROOT_DIR = Path(__file__).parent
TEMPLATES_DIR = ROOT_DIR / "templates"
OUTPUT_DIR = ROOT_DIR / "sites_gerados"
GITHUB_PAGES_BASE = "https://leo-luz-code.github.io/landing-pages"

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
        
    # Deduplica estabelecimentos pelo link do Maps ou nome
    seen_keys = set()
    unique_leads = []
    for l in leads:
        key = l.get("maps_url") or l.get("nome")
        if key and key not in seen_keys:
            seen_keys.add(key)
            unique_leads.append(l)
    leads = unique_leads
    
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    generated_list = []
    
    print(f"\n🚀 Gerando Landing Pages a partir de: {json_file_path}")
    print(f"Total de estabelecimentos únicos: {len(leads)}")
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
            
        demo_rel_url = f"sites_gerados/{slug}/index.html"
        demo_public_url = f"{GITHUB_PAGES_BASE}/sites_gerados/{slug}/index.html"
        pitch_msg = create_pitch_message(item, demo_public_url)
        
        generated_list.append({
            **item,
            "slug": slug,
            "template_usado": tmpl_name,
            "local_path": str(index_file),
            "demo_rel_url": demo_rel_url,
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
    """Gera um painel com listagem visual, busca e filtros por nicho, nome e nível do lead (ouro, prata, bronze)."""
    
    # Contadores iniciais
    total_leads = len(generated_list)
    total_ouro = sum(1 for x in generated_list if "SEM_SITE" in x.get("status_lead", "") or "ouro" in x.get("score_lead", "").lower())
    total_prata = sum(1 for x in generated_list if "REDE_SOCIAL" in x.get("status_lead", "") or "prata" in x.get("score_lead", "").lower())
    total_bronze = sum(1 for x in generated_list if "SITE_PROPRIO" in x.get("status_lead", "") or "bronze" in x.get("score_lead", "").lower())

    dashboard_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel de Landing Pages Geradas | Prospecção Ativa</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        .pill-active {{
            background-color: rgb(79 70 229);
            color: white;
            border-color: transparent;
        }}
    </style>
</head>
<body class="bg-[#0B1120] text-slate-100 font-sans p-4 sm:p-8 md:p-12 min-h-screen">
    <div class="max-w-7xl mx-auto">
        <!-- HEADER -->
        <header class="mb-8 pb-8 border-b border-slate-800/80 flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
                <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-bold uppercase tracking-wider mb-2">
                    <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    Esteira Ativa de Vendas
                </div>
                <h1 class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">Painel de Landing Pages Geradas</h1>
                <p class="text-slate-400 text-sm mt-1">Sites prontos para demonstração instantânea e prospecção direta no WhatsApp.</p>
            </div>
            
            <div class="flex flex-wrap items-center gap-2">
                <div class="bg-slate-900 border border-slate-800 px-4 py-2 rounded-xl text-xs sm:text-sm">
                    <span class="text-slate-400">Total:</span> <strong class="text-white font-bold">{total_leads}</strong>
                </div>
                <div class="bg-amber-500/10 border border-amber-500/20 px-3 py-2 rounded-xl text-xs sm:text-sm text-amber-300 font-semibold">
                    🔥 Ouro: <strong>{total_ouro}</strong>
                </div>
                <div class="bg-slate-500/10 border border-slate-700 px-3 py-2 rounded-xl text-xs sm:text-sm text-slate-300">
                    ⚡ Prata: <strong>{total_prata}</strong>
                </div>
                <div class="bg-blue-500/10 border border-blue-500/20 px-3 py-2 rounded-xl text-xs sm:text-sm text-blue-300">
                    ❄️ Bronze: <strong>{total_bronze}</strong>
                </div>
            </div>
        </header>

        <!-- BARRA DE FILTROS & BUSCA -->
        <div class="bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-2xl p-5 mb-8 shadow-2xl">
            <div class="grid grid-cols-1 md:grid-cols-12 gap-4">
                <!-- 1. Campo de Busca por Nome / Cidade -->
                <div class="md:col-span-5 relative">
                    <i data-lucide="search" class="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500"></i>
                    <input type="text" id="searchInput" placeholder="Buscar por nome do estabelecimento ou bairro..." class="w-full bg-slate-950/80 border border-slate-700/80 focus:border-indigo-500 rounded-xl pl-11 pr-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none transition">
                </div>

                <!-- 2. Filtro por Nicho -->
                <div class="md:col-span-3">
                    <select id="nicheFilter" class="w-full bg-slate-950/80 border border-slate-700/80 text-slate-200 text-sm rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500 transition cursor-pointer">
                        <option value="todos">Todos os Nichos</option>
                        <option value="barbearia_beleza">💈 Barbearia & Beleza</option>
                        <option value="gastronomia">🍕 Gastronomia</option>
                        <option value="saude">🩺 Saúde & Clínicas</option>
                        <option value="servicos_locais">🔧 Serviços Locais</option>
                    </select>
                </div>

                <!-- 3. Filtro por Potencial (Ouro / Prata / Bronze) -->
                <div class="md:col-span-3">
                    <select id="scoreFilter" class="w-full bg-slate-950/80 border border-slate-700/80 text-slate-200 text-sm rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500 transition cursor-pointer">
                        <option value="todos">Todos os Níveis</option>
                        <option value="ouro">🔥 Ouro (Sem Site)</option>
                        <option value="prata">⚡ Prata (App / Rede Social)</option>
                        <option value="bronze">❄️ Bronze (Com Site)</option>
                    </select>
                </div>

                <!-- 4. Botão Limpar -->
                <div class="md:col-span-1 flex items-center">
                    <button id="clearFiltersBtn" title="Limpar todos os filtros" class="w-full h-full bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-semibold transition flex items-center justify-center p-3">
                        <i data-lucide="rotate-ccw" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>

            <!-- Botões de Atalho Rápido (Pills) -->
            <div class="flex flex-wrap items-center gap-2 mt-4 pt-4 border-t border-slate-800/80 text-xs">
                <span class="text-slate-400 font-semibold mr-1">Atalhos rápidos:</span>
                <button type="button" class="quick-pill px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 transition" data-filter-type="all">Todos</button>
                <button type="button" class="quick-pill px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 border border-amber-500/20 transition" data-filter-type="score" data-filter-val="ouro">🔥 Apenas Ouro</button>
                <button type="button" class="quick-pill px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 transition" data-filter-type="niche" data-filter-val="barbearia_beleza">💈 Barbearias</button>
                <button type="button" class="quick-pill px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 transition" data-filter-type="niche" data-filter-val="gastronomia">🍕 Gastronomia</button>
                
                <div class="ml-auto text-xs text-slate-400">
                    Mostrando <span id="visibleCount" class="font-bold text-white text-sm">{total_leads}</span> de <span id="totalCount">{total_leads}</span> sites
                </div>
            </div>
        </div>

        <!-- GRID DE CARDS DOS SITES -->
        <div id="cardsGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    """
    
    for item in generated_list:
        slug = item["slug"]
        nome = item["nome"]
        nota = item.get("nota", "5.0")
        av = item.get("total_avaliacoes", "+50")
        score = item.get("score_lead", "LEAD")
        status_lead = item.get("status_lead", "")
        tel = item.get("telefone", "Sem telefone")
        endereco = item.get("endereco", "")
        tmpl = item.get("template_usado", "geral")
        tmpl_badge = tmpl.replace("_", " ").upper()
        wa_link = item.get("whatsapp_link", "")
        encoded_pitch = urllib.parse.quote(item["pitch_msg"])
        pitch_wa_url = f"{wa_link}?text={encoded_pitch}" if wa_link else "#"

        # Define tag normalizada de score para filtro
        if "SEM_SITE" in status_lead or "ouro" in score.lower():
            score_filter_tag = "ouro"
            score_badge_class = "bg-amber-500/10 text-amber-300 border-amber-500/20"
        elif "REDE_SOCIAL" in status_lead or "prata" in score.lower():
            score_filter_tag = "prata"
            score_badge_class = "bg-slate-800 text-slate-300 border-slate-700"
        else:
            score_filter_tag = "bronze"
            score_badge_class = "bg-blue-500/10 text-blue-300 border-blue-500/20"

        dashboard_html += f"""
        <div class="lead-card bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-6 flex flex-col justify-between shadow-xl transition-all duration-200 hover:-translate-y-1"
             data-name="{nome.lower()}"
             data-niche="{tmpl}"
             data-score="{score_filter_tag}"
             data-city="{endereco.lower()}">
            <div>
                <div class="flex items-center justify-between gap-2 mb-3">
                    <span class="text-xs font-bold px-2.5 py-1 rounded-md bg-slate-800 text-indigo-400 border border-indigo-500/20">{tmpl_badge}</span>
                    <span class="text-xs font-semibold text-amber-400 flex items-center gap-1">★ {nota} ({av})</span>
                </div>
                <h2 class="font-bold text-lg text-white mb-2 line-clamp-1" title="{nome}">{nome}</h2>
                <div class="mb-4">
                    <span class="inline-block text-xs font-semibold px-2.5 py-1 rounded-lg border {score_badge_class}">
                        {score}
                    </span>
                </div>
                <p class="text-xs text-slate-300 flex items-center gap-2 mb-2">
                    <i data-lucide="phone" class="w-3.5 h-3.5 text-slate-500 shrink-0"></i>
                    <span>{tel}</span>
                </p>
                <p class="text-xs text-slate-400 flex items-start gap-2 mb-6 line-clamp-2" title="{endereco}">
                    <i data-lucide="map-pin" class="w-3.5 h-3.5 text-slate-500 shrink-0 mt-0.5"></i>
                    <span>{endereco if endereco else 'Localização no Google Maps'}</span>
                </p>
            </div>

            <div class="space-y-2 pt-4 border-t border-slate-800">
                <a href="{item['demo_rel_url']}" target="_blank" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2.5 rounded-xl text-xs flex items-center justify-center gap-2 transition shadow-lg shadow-indigo-950/50">
                    <i data-lucide="external-link" class="w-4 h-4"></i>
                    <span>Ver Landing Page Pronta</span>
                </a>

                <a href="{pitch_wa_url}" target="_blank" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2.5 rounded-xl text-xs flex items-center justify-center gap-2 transition shadow-lg shadow-emerald-950/50">
                    <i data-lucide="message-circle" class="w-4 h-4"></i>
                    <span>Enviar Pitch no WhatsApp</span>
                </a>
            </div>
        </div>
        """
        
    dashboard_html += """
        </div>

        <!-- MENSAGEM QUANDO NENHUM RESULTADO FOR ENCONTRADO -->
        <div id="emptyState" class="hidden py-16 text-center bg-slate-900/50 border border-slate-800 rounded-3xl mt-6">
            <div class="w-16 h-16 rounded-2xl bg-slate-800 text-slate-400 flex items-center justify-center mx-auto mb-4">
                <i data-lucide="filter-x" class="w-8 h-8"></i>
            </div>
            <h3 class="text-lg font-bold text-white mb-1">Nenhum estabelecimento encontrado</h3>
            <p class="text-sm text-slate-400 max-w-sm mx-auto mb-6">Tente alterar os termos da busca ou redefinir os filtros selecionados.</p>
            <button onclick="resetFilters()" class="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-5 py-2.5 rounded-xl transition">
                Redefinir Filtros
            </button>
        </div>
    </div>

    <!-- JAVASCRIPT DE FILTRAGEM INSTANTÂNEA -->
    <script>
        lucide.createIcons();

        const searchInput = document.getElementById('searchInput');
        const nicheFilter = document.getElementById('nicheFilter');
        const scoreFilter = document.getElementById('scoreFilter');
        const clearBtn = document.getElementById('clearFiltersBtn');
        const visibleCount = document.getElementById('visibleCount');
        const cardsGrid = document.getElementById('cardsGrid');
        const emptyState = document.getElementById('emptyState');
        const cards = Array.from(document.querySelectorAll('.lead-card'));
        const pills = document.querySelectorAll('.quick-pill');

        function filterLeads() {
            const query = searchInput.value.toLowerCase().trim();
            const selectedNiche = nicheFilter.value;
            const selectedScore = scoreFilter.value;

            let matches = 0;

            cards.forEach(card => {
                const name = card.getAttribute('data-name') || '';
                const city = card.getAttribute('data-city') || '';
                const niche = card.getAttribute('data-niche') || '';
                const score = card.getAttribute('data-score') || '';

                const matchesQuery = !query || name.includes(query) || city.includes(query);
                const matchesNiche = selectedNiche === 'todos' || niche === selectedNiche;
                const matchesScore = selectedScore === 'todos' || score === selectedScore;

                if (matchesQuery && matchesNiche && matchesScore) {
                    card.classList.remove('hidden');
                    matches++;
                } else {
                    card.classList.add('hidden');
                }
            });

            visibleCount.innerText = matches;

            if (matches === 0) {
                emptyState.classList.remove('hidden');
            } else {
                emptyState.classList.add('hidden');
            }
        }

        function resetFilters() {
            searchInput.value = '';
            nicheFilter.value = 'todos';
            scoreFilter.value = 'todos';
            filterLeads();
        }

        // Listeners para os inputs
        searchInput.addEventListener('input', filterLeads);
        nicheFilter.addEventListener('change', filterLeads);
        scoreFilter.addEventListener('change', filterLeads);
        clearBtn.addEventListener('click', resetFilters);

        // Listeners para os botões de atalho (Pills)
        pills.forEach(pill => {
            pill.addEventListener('click', () => {
                const fType = pill.getAttribute('data-filter-type');
                const fVal = pill.getAttribute('data-filter-val');

                if (fType === 'all') {
                    resetFilters();
                } else if (fType === 'score') {
                    scoreFilter.value = fVal;
                    filterLeads();
                } else if (fType === 'niche') {
                    nicheFilter.value = fVal;
                    filterLeads();
                }
            });
        });
    </script>
</body>
</html>
    """
    
    # Salva na raiz do projeto para o GitHub Pages
    root_index = ROOT_DIR / "index.html"
    with open(root_index, "w", encoding="utf-8") as f:
        f.write(dashboard_html)
        
    # Salva também uma cópia em sites_gerados/ para retrocompatibilidade
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
