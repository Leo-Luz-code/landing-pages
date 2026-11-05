#!/bin/bash
# Inicia um servidor local rápido para visualizar todos os sites gerados
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/sites_gerados"

PORT=8080
echo "=================================================="
echo "🌐 SERVIDOR DE VISUALIZAÇÃO ATIVO!"
echo "👉 Acesse o painel de sites no seu navegador:"
echo "   http://localhost:$PORT/"
echo "=================================================="
echo "Pressione Ctrl+C para encerrar o servidor."

python3 -m http.server $PORT
