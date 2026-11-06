#!/usr/bin/env python3
"""
Gerador Automático de Landing Pages para Leads do Google Maps
Renderiza templates profissionais e alimenta o banco de dados 'database.json'.
O painel 'index.html' gerencia status de contato (Pendentes vs Abordados) com persistência no localStorage.
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
OUTPUT_DIR = ROOT_DIR / "sites"
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
    
    priority_order = ["barbearia_beleza", "saude", "gastronomia", "servicos_locais"]
    for template_name in priority_order:
        keywords = CATEGORY_MAPPING[template_name]
        for kw in keywords:
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
    """Lê o JSON de leads, gera os sites estáticos e salva o banco de dados 'database.json'."""
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
    
    database_records = []
    
    print(f"\n🚀 Gerando Landing Pages a partir de: {json_file_path}")
    print(f"Total de estabelecimentos únicos: {len(leads)}")
    print("=" * 60)
    
    for idx, item in enumerate(leads, 1):
        tmpl_name = template_override if template_override else detect_template(item)
        tmpl_file = f"{tmpl_name}.html"
        
        try:
            template = env.get_template(tmpl_file)
        except Exception as e:
            print(f"❌ Erro ao carregar template '{tmpl_file}': {e}. Usando 'servicos_locais.html'")
            template = env.get_template("servicos_locais.html")
            tmpl_name = "servicos_locais"
            
        slug = slugify(item.get("nome", f"lead_{idx}"))
        site_folder = OUTPUT_DIR / slug
        site_folder.mkdir(parents=True, exist_ok=True)
        
        html_content = template.render(**item)
        index_file = site_folder / "index.html"
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        demo_rel_url = f"sites/{slug}/index.html"
        demo_public_url = f"{GITHUB_PAGES_BASE}/sites/{slug}/index.html"
        pitch_msg = create_pitch_message(item, demo_public_url)
        
        status_lead = item.get("status_lead", "")
        score_lead = item.get("score_lead", "LEAD")
        if "SEM_SITE" in status_lead or "ouro" in score_lead.lower():
            score_tag = "ouro"
        elif "REDE_SOCIAL" in status_lead or "prata" in score_lead.lower():
            score_tag = "prata"
        else:
            score_tag = "bronze"

        wa_link = item.get("whatsapp_link", "")
        encoded_pitch = urllib.parse.quote(pitch_msg)
        pitch_wa_url = f"{wa_link}?text={encoded_pitch}" if wa_link else "#"

        record = {
            "id": slug,
            "slug": slug,
            "nome": item.get("nome", ""),
            "categoria": item.get("categoria", ""),
            "nota": item.get("nota", "5.0"),
            "total_avaliacoes": item.get("total_avaliacoes", "+50"),
            "telefone": item.get("telefone", "Sem telefone"),
            "endereco": item.get("endereco", ""),
            "score_lead": score_lead,
            "score_tag": score_tag,
            "status_lead": status_lead,
            "template": tmpl_name,
            "template_badge": tmpl_name.replace("_", " ").upper(),
            "demo_rel_url": demo_rel_url,
            "demo_public_url": demo_public_url,
            "pitch_wa_url": pitch_wa_url,
            "coletado_em": item.get("coletado_em", "")
        }
        database_records.append(record)
        
        print(f"[{idx}/{len(leads)}] ✅ {item['nome']}")
        print(f"   Template: {tmpl_name.upper()} | Pasta: sites/{slug}/")
        
    save_database_and_dashboard(database_records)
    
    print("\n" + "=" * 60)
    print("🎉 SUCESSO! TODAS AS LANDING PAGES FORAM GERADAS!")
    print(f"📂 Diretório dos sites: {OUTPUT_DIR}")
    print(f"💾 Banco de Dados: {ROOT_DIR / 'database.json'}")
    print(f"📊 Painel Dinâmico: {ROOT_DIR / 'index.html'}")
    print("=" * 60)
    return database_records

def save_database_and_dashboard(database_records: list):
    """
    1. Salva o banco de dados 'database.json'.
    2. Gera o painel 'index.html' com CRM de status de envio (localStorage),
       filtros por nicho, nome, ouro/prata/bronze e status de contato.
    """
    db_path_root = ROOT_DIR / "database.json"
    with open(db_path_root, "w", encoding="utf-8") as f:
        json.dump(database_records, f, ensure_ascii=False, indent=2)
        
    db_path_sites = OUTPUT_DIR / "database.json"
    with open(db_path_sites, "w", encoding="utf-8") as f:
        json.dump(database_records, f, ensure_ascii=False, indent=2)

    json_embedded = json.dumps(database_records, ensure_ascii=False)

    dashboard_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel de Landing Pages Geradas | Prospecção Ativa</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <!-- Lucide Icons -->
    <script src="https://unpkg.com/lucide@latest"></script>
</head>
<body class="bg-[#0B1120] text-slate-100 font-sans p-4 sm:p-8 md:p-12 min-h-screen">
    <div class="max-w-7xl mx-auto">
        <!-- HEADER -->
        <header class="mb-8 pb-8 border-b border-slate-800/80 flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
                <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-bold uppercase tracking-wider mb-2">
                    <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    CRM & Prospecção Ativa
                </div>
                <h1 class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">Painel de Landing Pages</h1>
                <p class="text-slate-400 text-sm mt-1">Gerencie seus leads, envie mensagens pelo WhatsApp e acompanhe quem já recebeu abordagem.</p>
            </div>
            
            <!-- CONTADORES GERAIS -->
            <div class="flex flex-wrap items-center gap-2" id="statsContainer">
                <div class="bg-slate-900 border border-slate-800 px-3.5 py-2 rounded-xl text-xs sm:text-sm">
                    <span class="text-slate-400">Total:</span> <strong id="statTotal" class="text-white font-bold">0</strong>
                </div>
                <div class="bg-slate-900 border border-slate-800 px-3.5 py-2 rounded-xl text-xs sm:text-sm">
                    <span class="text-slate-400">Ainda não mandei:</span> <strong id="statNaoEnviado" class="text-slate-200 font-bold">0</strong>
                </div>
                <div class="bg-emerald-500/10 border border-emerald-500/20 px-3 py-2 rounded-xl text-xs sm:text-sm text-emerald-300 font-semibold">
                    <i data-lucide="check-check" class="w-3.5 h-3.5 inline mr-1"></i>Já mandei mensagem: <strong id="statAbordado">0</strong>
                </div>
                <div class="bg-slate-800/50 border border-slate-700/80 px-3 py-2 rounded-xl text-xs sm:text-sm text-amber-200">
                    🔥 Ouro: <strong id="statOuro">0</strong>
                </div>
            </div>
        </header>

        <!-- BARRA DE FILTROS & BUSCA -->
        <div class="bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-2xl p-5 mb-8 shadow-2xl">
            <div class="grid grid-cols-1 md:grid-cols-12 gap-4">
                <!-- 1. Campo de Busca por Nome / Bairro / Cidade -->
                <div class="md:col-span-4 relative">
                    <i data-lucide="search" class="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500"></i>
                    <input type="text" id="searchInput" placeholder="Buscar por nome do estabelecimento ou bairro..." class="w-full bg-slate-950/80 border border-slate-700/80 focus:border-indigo-500 rounded-xl pl-11 pr-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none transition">
                </div>

                <!-- 2. Filtro por Status de Contato -->
                <div class="md:col-span-3">
                    <select id="contactFilter" class="w-full bg-slate-950/80 border border-slate-700/80 text-slate-200 text-sm rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500 transition cursor-pointer font-medium">
                        <option value="todos">Todos os Estabelecimentos</option>
                        <option value="nao_enviado">Apenas os que AINDA NÃO mandei mensagem</option>
                        <option value="enviado">Apenas os que JÁ MANDEI mensagem</option>
                    </select>
                </div>

                <!-- 3. Filtro por Nicho -->
                <div class="md:col-span-2">
                    <select id="nicheFilter" class="w-full bg-slate-950/80 border border-slate-700/80 text-slate-200 text-sm rounded-xl px-3 py-3 focus:outline-none focus:border-indigo-500 transition cursor-pointer">
                        <option value="todos">Todos os Nichos</option>
                        <option value="barbearia_beleza">💈 Barbearias</option>
                        <option value="gastronomia">🍕 Gastronomia</option>
                        <option value="saude">🩺 Saúde</option>
                        <option value="servicos_locais">🔧 Oficinas/Serviços</option>
                    </select>
                </div>

                <!-- 4. Filtro por Potencial (Ouro / Prata / Bronze) -->
                <div class="md:col-span-2">
                    <select id="scoreFilter" class="w-full bg-slate-950/80 border border-slate-700/80 text-slate-200 text-sm rounded-xl px-3 py-3 focus:outline-none focus:border-indigo-500 transition cursor-pointer">
                        <option value="todos">Todos os Níveis</option>
                        <option value="ouro">🔥 Ouro (Sem Site)</option>
                        <option value="prata">⚡ Prata (App / Rede Social)</option>
                        <option value="bronze">❄️ Bronze (Com Site)</option>
                    </select>
                </div>

                <!-- 5. Botão Limpar -->
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
                <button type="button" class="quick-pill px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 transition" data-filter-type="contact" data-filter-val="nao_enviado">Ainda não mandei</button>
                <button type="button" class="quick-pill px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20 border border-emerald-500/20 transition font-bold" data-filter-type="contact" data-filter-val="enviado">Já mandei mensagem</button>
                <button type="button" class="quick-pill px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 transition" data-filter-type="score" data-filter-val="ouro">🔥 Ouro</button>
                
                <button type="button" onclick="resetAllContactHistory()" title="Limpar marcações de mensagens enviadas" class="ml-2 px-2.5 py-1.5 rounded-lg bg-slate-800/60 hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 border border-slate-700/60 hover:border-rose-500/30 transition text-xs flex items-center gap-1.5">
                    <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                    <span>Zerar status de envio</span>
                </button>

                <div class="ml-auto text-xs text-slate-400">
                    Mostrando <span id="visibleCount" class="font-bold text-white text-sm">0</span> de <span id="totalCount">0</span> sites
                </div>
            </div>
        </div>

        <!-- GRID DE CARDS DINÂMICOS -->
        <div id="cardsGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"></div>

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

    <!-- DADOS DE FALLBACK (Garante funcionamento mesmo em navegadores locais offline sem CORS) -->
    <script id="databaseFallback" type="application/json">
{json_embedded}
    </script>

    <!-- MOTOR DINÂMICO DE CRM, RENDERIZAÇÃO & FILTROS -->
    <script>
        const STORAGE_KEY = 'landing_pages_crm_contacted';
        let allLeads = [];

        // Elementos do DOM
        const searchInput = document.getElementById('searchInput');
        const contactFilter = document.getElementById('contactFilter');
        const nicheFilter = document.getElementById('nicheFilter');
        const scoreFilter = document.getElementById('scoreFilter');
        const clearBtn = document.getElementById('clearFiltersBtn');
        const visibleCount = document.getElementById('visibleCount');
        const totalCount = document.getElementById('totalCount');
        const cardsGrid = document.getElementById('cardsGrid');
        const emptyState = document.getElementById('emptyState');
        const pills = document.querySelectorAll('.quick-pill');

        // Gerenciamento de Histórico no LocalStorage
        function getContactHistory() {{
            try {{
                const raw = localStorage.getItem(STORAGE_KEY);
                return raw ? JSON.parse(raw) : {{}};
            }} catch (e) {{
                return {{}};
            }}
        }}

        function saveContactHistory(history) {{
            try {{
                localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
            }} catch (e) {{
                console.error('Erro ao salvar no localStorage:', e);
            }}
        }}

        // Marca um estabelecimento como contatado
        function markAsContacted(leadId) {{
            const history = getContactHistory();
            const now = new Date();
            const dataStr = now.toLocaleDateString('pt-BR', {{ day: '2-digit', month: '2-digit' }});
            const horaStr = now.toLocaleTimeString('pt-BR', {{ hour: '2-digit', minute: '2-digit' }});
            
            history[leadId] = {{
                date: dataStr,
                time: horaStr,
                timestamp: now.getTime()
            }};
            saveContactHistory(history);
            updateStats(allLeads);
            filterLeads();
        }}

        // Alterna status manualmente (desmarcar / marcar)
        function toggleContactStatus(leadId, e) {{
            if (e) e.stopPropagation();
            const history = getContactHistory();
            if (history[leadId]) {{
                delete history[leadId];
            }} else {{
                const now = new Date();
                history[leadId] = {{
                    date: now.toLocaleDateString('pt-BR', {{ day: '2-digit', month: '2-digit' }}),
                    time: now.toLocaleTimeString('pt-BR', {{ hour: '2-digit', minute: '2-digit' }}),
                    timestamp: now.getTime()
                }};
            }}
            saveContactHistory(history);
            updateStats(allLeads);
            filterLeads();
        }}

        // Dispara o WhatsApp e marca como contatado automaticamente
        function handleSendPitch(leadId, waUrl) {{
            markAsContacted(leadId);
            window.open(waUrl, '_blank');
        }}

        // Zera todo o histórico de contatos salvos no navegador
        function resetAllContactHistory() {{
            if (confirm('Deseja realmente zerar todos os status e definir todos os estabelecimentos como "Ainda não mandei"?')) {{
                localStorage.removeItem(STORAGE_KEY);
                updateStats(allLeads);
                filterLeads();
            }}
        }}

        // Carrega dados
        async function loadDatabase() {{
            try {{
                const res = await fetch('database.json?t=' + Date.now());
                if (!res.ok) throw new Error('Falha HTTP');
                allLeads = await res.json();
            }} catch (e) {{
                console.warn('Carregando dados a partir do fallback embutido:', e);
                const raw = document.getElementById('databaseFallback').textContent;
                allLeads = JSON.parse(raw);
            }}

            updateStats(allLeads);
            renderCards(allLeads);
        }}

        // Atualiza contadores
        function updateStats(data) {{
            const history = getContactHistory();
            const total = data.length;
            const ouro = data.filter(x => x.score_tag === 'ouro').length;
            
            let abordados = 0;
            data.forEach(x => {{
                if (history[x.id]) abordados++;
            }});
            const naoEnviados = total - abordados;

            document.getElementById('statTotal').innerText = total;
            document.getElementById('statOuro').innerText = ouro;
            document.getElementById('statNaoEnviado').innerText = naoEnviados;
            document.getElementById('statAbordado').innerText = abordados;
            totalCount.innerText = total;
        }}

        // Renderiza os cards usando laço 'for'
        function renderCards(items) {{
            cardsGrid.innerHTML = '';
            visibleCount.innerText = items.length;

            if (items.length === 0) {{
                emptyState.classList.remove('hidden');
                return;
            }}
            emptyState.classList.add('hidden');

            const history = getContactHistory();

            for (let i = 0; i < items.length; i++) {{
                const item = items[i];
                const contactInfo = history[item.id];
                const isContacted = !!contactInfo;

                let scoreBadgeClass = "bg-blue-500/10 text-blue-300 border-blue-500/20";
                if (item.score_tag === "ouro") {{
                    scoreBadgeClass = "bg-amber-500/10 text-amber-300 border-amber-500/20";
                }} else if (item.score_tag === "prata") {{
                    scoreBadgeClass = "bg-slate-800 text-slate-300 border-slate-700";
                }}

                // Status de Contato: limpo por padrão (nenhum badge de pendente)
                // Só ganha badge verde quando a mensagem for de fato enviada
                let crmBadgeHtml = '';
                let cardBorderClass = 'border-slate-800 hover:border-slate-700';

                if (isContacted) {{
                    cardBorderClass = 'border-emerald-500/40 bg-slate-900/95';
                    crmBadgeHtml = `
                        <div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-xs font-semibold">
                            <i data-lucide="check-check" class="w-3.5 h-3.5 text-emerald-400"></i>
                            <span>Mensagem enviada (${{contactInfo.date || ''}} às ${{contactInfo.time || ''}})</span>
                            <button onclick="toggleContactStatus('${{item.id}}', event)" title="Desmarcar / Resetar status" class="ml-1 text-slate-400 hover:text-white">
                                <i data-lucide="x" class="w-3 h-3"></i>
                            </button>
                        </div>
                    `;
                }}

                const card = document.createElement('div');
                card.className = `lead-card bg-slate-900 border ${{cardBorderClass}} rounded-2xl p-6 flex flex-col justify-between shadow-xl transition-all duration-200 hover:-translate-y-1 relative`;
                
                card.innerHTML = `
                    <div>
                        <div class="flex items-center justify-between gap-2 mb-3">
                            <span class="text-xs font-bold px-2.5 py-1 rounded-md bg-slate-800 text-indigo-400 border border-indigo-500/20">${{item.template_badge}}</span>
                            <span class="text-xs font-semibold text-amber-400 flex items-center gap-1">★ ${{item.nota}} (${{item.total_avaliacoes}})</span>
                        </div>
                        
                        <h2 class="font-bold text-lg text-white mb-2 line-clamp-1" title="${{item.nome}}">${{item.nome}}</h2>
                        
                        <div class="flex flex-wrap items-center gap-2 mb-4">
                            <span class="inline-block text-xs font-semibold px-2.5 py-1 rounded-lg border ${{scoreBadgeClass}}">
                                ${{item.score_lead}}
                            </span>
                            ${{crmBadgeHtml}}
                        </div>

                        <p class="text-xs text-slate-300 flex items-center gap-2 mb-2">
                            <i data-lucide="phone" class="w-3.5 h-3.5 text-slate-500 shrink-0"></i>
                            <span>${{item.telefone || 'Sem telefone'}}</span>
                        </p>
                        <p class="text-xs text-slate-400 flex items-start gap-2 mb-6 line-clamp-2" title="${{item.endereco || ''}}">
                            <i data-lucide="map-pin" class="w-3.5 h-3.5 text-slate-500 shrink-0 mt-0.5"></i>
                            <span>${{item.endereco || 'Localização no Google Maps'}}</span>
                        </p>
                    </div>

                    <div class="space-y-2 pt-4 border-t border-slate-800">
                        <a href="${{item.demo_rel_url}}" target="_blank" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2.5 rounded-xl text-xs flex items-center justify-center gap-2 transition shadow-lg shadow-indigo-950/50">
                            <i data-lucide="external-link" class="w-4 h-4"></i>
                            <span>Ver Landing Page Pronta</span>
                        </a>

                        <button onclick="handleSendPitch('${{item.id}}', '${{item.pitch_wa_url}}')" class="w-full ${{isContacted ? 'bg-slate-800 hover:bg-emerald-600 text-slate-300 hover:text-white' : 'bg-emerald-600 hover:bg-emerald-500 text-white'}} font-bold py-2.5 rounded-xl text-xs flex items-center justify-center gap-2 transition shadow-lg shadow-emerald-950/50">
                            <i data-lucide="message-circle" class="w-4 h-4"></i>
                            <span>${{isContacted ? 'Enviar Novamente no WhatsApp' : 'Enviar Pitch no WhatsApp'}}</span>
                        </button>
                    </div>
                `;
                cardsGrid.appendChild(card);
            }}

            lucide.createIcons();
        }}

        // Filtragem dos dados (busca, contato, nicho e score)
        function filterLeads() {{
            const query = searchInput.value.toLowerCase().trim();
            const selectedContact = contactFilter.value;
            const selectedNiche = nicheFilter.value;
            const selectedScore = scoreFilter.value;

            const history = getContactHistory();

            const filtered = allLeads.filter(item => {{
                const name = (item.nome || '').toLowerCase();
                const address = (item.endereco || '').toLowerCase();
                const niche = item.template || '';
                const score = item.score_tag || '';
                const isContacted = !!history[item.id];

                const matchesQuery = !query || name.includes(query) || address.includes(query);
                const matchesNiche = selectedNiche === 'todos' || niche === selectedNiche;
                const matchesScore = selectedScore === 'todos' || score === selectedScore;
                
                let matchesContact = true;
                if (selectedContact === 'nao_enviado') {{
                    matchesContact = !isContacted;
                }} else if (selectedContact === 'enviado') {{
                    matchesContact = isContacted;
                }}

                return matchesQuery && matchesNiche && matchesScore && matchesContact;
            }});

            renderCards(filtered);
        }}

        function resetFilters() {{
            searchInput.value = '';
            contactFilter.value = 'todos';
            nicheFilter.value = 'todos';
            scoreFilter.value = 'todos';
            filterLeads();
        }}

        // Event Listeners
        searchInput.addEventListener('input', filterLeads);
        contactFilter.addEventListener('change', filterLeads);
        nicheFilter.addEventListener('change', filterLeads);
        scoreFilter.addEventListener('change', filterLeads);
        clearBtn.addEventListener('click', resetFilters);

        pills.forEach(pill => {{
            pill.addEventListener('click', () => {{
                const fType = pill.getAttribute('data-filter-type');
                const fVal = pill.getAttribute('data-filter-val');

                if (fType === 'all') {{
                    resetFilters();
                }} else if (fType === 'contact') {{
                    contactFilter.value = fVal;
                    filterLeads();
                }} else if (fType === 'score') {{
                    scoreFilter.value = fVal;
                    filterLeads();
                }} else if (fType === 'niche') {{
                    nicheFilter.value = fVal;
                    filterLeads();
                }}
            }});
        }});

        document.addEventListener('DOMContentLoaded', loadDatabase);
    </script>
</body>
</html>
    """
    
    with open(ROOT_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(dashboard_html)
        
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
        json_files = [f for f in glob.glob("dados_leads/*.json") if "consolidado" not in f]
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
        merged_path = "dados_leads/leads_consolidados.json"
        with open(merged_path, "w", encoding="utf-8") as f:
            json.dump(todos_leads, f, ensure_ascii=False, indent=2)
        generate_sites(merged_path, args.template)
    else:
        target_file = args.arquivo_json
        if not target_file:
            json_files = sorted(glob.glob("dados_leads/*.json"), key=os.path.getmtime, reverse=True)
            json_files = [f for f in json_files if "consolidado" not in f]
            if json_files:
                target_file = json_files[0]
                print(f"📂 Selecionado automaticamente o arquivo mais recente: {target_file}")
            else:
                print("❌ Nenhum arquivo JSON encontrado em dados_leads/. Execute o scraper primeiro!")
                exit(1)
                
        generate_sites(target_file, args.template)
