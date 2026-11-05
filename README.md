# 🚀 Sistema Completo de Prospecção & Landing Pages para Negócios Locais

Pipeline automatizado para:
1. **Extrair** dados de empresas no Google Maps filtrando quem não tem site próprio.
2. **Qualificar** leads por potencial comercial (🔥 Ouro, ⚡ Prata, ❄️ Bronze).
3. **Gerar Landing Pages profissionais** automaticamente com design mobile-first de alta conversão.
4. **Painel de Controle** com prévia de cada site e botão com **pitch de vendas pronto para WhatsApp**.

---

## 📂 Os 4 Templates Profissionais Criados

Os templates utilizam **Tailwind CSS**, tipografia moderna (Google Fonts), ícones do **Lucide** e design mobile-first:

1. 🍕 **Gastronomia** (`templates/gastronomia.html`):
   - Focado em: Pizzarias, Hamburguerias, Restaurantes, Sushi, Cafés.
   - Recursos: Hero gastronômico escuro com foto de capa em alta definição, selo do Google Maps, destaques do cardápio, depoimentos reais, mapa de localização e botão de pedido direto no WhatsApp.

2. 💈 **Barbearia & Beleza** (`templates/barbearia_beleza.html`):
   - Focado em: Barbearias, Salões de Beleza, Estética, Sobrancelhas, Tatuagens.
   - Recursos: Visual refinado noir/gold, menu de serviços e tratamentos, toalha quente / barboterapia, avaliações 5 estrelas e agendamento sem fila no WhatsApp.

3. 🩺 **Saúde & Clínicas** (`templates/saude.html`):
   - Focado em: Dentistas/Odontologia, Clínicas Médicas, Fisioterapia, Psicologia, Veterinária.
   - Recursos: Visual limpo clínico com azul royal/celeste, sensação de confiança e higiene, especialidades, protocolo de biossegurança e agendamento de consultas com a recepção.

4. 🔧 **Serviços Locais & Oficinas** (`templates/servicos_locais.html`):
   - Focado em: Mecânicas, Auto Centers, Vidraçarias, Climatização, Eletricistas, Chaveiros.
   - Recursos: Visual industrial escuro com laranja vibrante, ênfase em orçamento rápido sem compromisso, garantia de serviço e rota no GPS.

---

## ⚡ Passo a Passo: Do Google Maps ao Site Pronto

### Passo 1: Extrair Leads do Google Maps
Execute o extrator (interativo ou por linha de comando):
```bash
# Modo interativo (responda as perguntas no terminal):
./executar.sh

# Ou direto na linha de comando buscando quem NÃO tem site:
./executar.sh "barbearia sorocaba" --qtd 15 --sem-site
./executar.sh "hamburgueria campinas" --qtd 10 --sem-site
```
Os dados serão salvos em `dados_leads/` em formato `.json`, `.xlsx` e `.csv`.

---

### Passo 2: Gerar as Landing Pages
Para gerar os sites de todos os leads encontrados:
```bash
source venv/bin/activate

# Gera para o arquivo de leads mais recente coletado:
python3 gerador_sites.py

# Ou gera para TODOS os arquivos já coletados:
python3 gerador_sites.py --todos

# Ou força um template específico:
python3 gerador_sites.py dados_leads/seuarquivo.json --template gastronomia
```
*O gerador detecta automaticamente o nicho do estabelecimento pelo nome e categoria!*

---

### Passo 3: Visualizar os Sites Criados no Navegador
Para abrir o painel local e testar os sites gerados:
```bash
./visualizar.sh
```
Acesse no seu navegador: **`http://localhost:8080/`**

Você verá o **Painel Central** com:
- Todos os estabelecimentos listados.
- Botão **"Ver Landing Page Pronta"**.
- Botão **"Enviar Pitch no WhatsApp"** (já com a mensagem personalizada pronta com nome, nota do Google e link da demo!).

---

### 🌐 Como Enviar a Prévia para o Dono do Estabelecimento

Para que o dono veja o site no celular dele quando você mandar o link no WhatsApp, você pode subir a pasta `sites_gerados` para a internet gratuitamente:

1. **Vercel / Netlify / Cloudflare Pages (Grátis):**
   - Arraste a pasta `sites_gerados` para o dashboard do Netlify Drop (ou Vercel).
   - Você ganha um link instantâneo tipo: `https://seusite-demo.netlify.app/barbearia_trezentos/`
2. **Ou via subdomínio próprio:**
   - Ex: `preview.suaagencia.com.br/barbearia-trezentos`
