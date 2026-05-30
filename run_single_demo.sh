#!/bin/bash
# Script de Teste Único - Modo Transparente (Logs no Ecrã)

MOSAIC_HOME="/home/netsim/opt/eclipse-mosaic-24.1"
# Caminho do projeto derivado da localização deste script (robusto a onde é chamado)
PROJECT_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCENARIO_CONFIG="$PROJECT_HOME/cenario_manhattan/scenario_config.json"
RESULTS_DIR="$PROJECT_HOME/results/run_test"

echo "╔════════════════════════════════════════════╗"
echo "║         A INICIAR DEMO - 1 RUN             ║"
echo "╚════════════════════════════════════════════╝"

# Limpar resultados antigos
rm -rf "$RESULTS_DIR"
mkdir -p "$RESULTS_DIR"

# 1. Compilar código
echo "[1/4] A compilar código Maven..."
cd "$PROJECT_HOME"

# Tirei o '-q' para poderes ver se a compilação falha!
mvn clean package -DskipTests
if [ $? -ne 0 ]; then
    echo "ERRO NA COMPILAÇÃO! Vê o erro do Maven acima."
    exit 1
fi

cp "$PROJECT_HOME/target/tp-app-1.0.jar" "$PROJECT_HOME/cenario_manhattan/application/tp-app-1.0.jar"

# Apagar lixo anterior para ter a certeza que o JSON é novo
rm -f "$PROJECT_HOME/metrics_from_wrapper.json"
rm -f "$MOSAIC_HOME/metrics_from_wrapper.json"

# 2. Executar MOSAIC
SEED=$RANDOM
echo "[2/4] A executar MOSAIC (Seed: $SEED)."
echo "A simulação vai começar! Vê os logs abaixo:"
echo "--------------------------------------------------------"

cd "$MOSAIC_HOME"

# Direciona o JSON de métricas diretamente para a pasta de resultados (lido pela dashboard).
# Assim o ficheiro é criado no sítio certo sem depender de um 'find' posterior.
export JAVA_TOOL_OPTIONS="-Dnpr.metrics.out=$RESULTS_DIR/metrics_test.json -Dnpr.live.out=$PROJECT_HOME/metrics_live.json"

# O comando 'tee' mostra os logs no teu ecrã e grava no ficheiro ao mesmo tempo!
./mosaic.sh -c "$SCENARIO_CONFIG" -r $SEED 2>&1 | tee "$RESULTS_DIR/mosaic_log.txt"

unset JAVA_TOOL_OPTIONS

echo "--------------------------------------------------------"

# 3. Verificar o ficheiro JSON (escrito diretamente em RESULTS_DIR pela system property)
echo "[3/4] A recolher métricas geradas..."
if [ -f "$RESULTS_DIR/metrics_test.json" ]; then
    echo "Ficheiro gerado com sucesso em: $RESULTS_DIR/metrics_test.json"
else
    # Fallback: procurar o ficheiro no caminho por defeito do MetricsCollector
    FILE_PATH=$(find "$PROJECT_HOME" "$MOSAIC_HOME" -name "metrics_from_wrapper.json" -type f 2>/dev/null | head -n 1)
    if [ -n "$FILE_PATH" ]; then
        echo "Ficheiro encontrado em: $FILE_PATH"
        cp "$FILE_PATH" "$RESULTS_DIR/metrics_test.json"
    else
        echo " ERRO CRÍTICO: O ficheiro JSON não foi gerado!"
        echo "Lê as últimas linhas vermelhas que apareceram aí em cima no terminal."
        echo " Provavelmente o código Java (MetricsCollector) deu um 'NullPointerException' ou não encontrou a diretoria."
        exit 1
    fi
fi

# 4. Copiar o tripinfo
echo "[4/4] A recolher dados do SUMO..."
if [ -f "$PROJECT_HOME/tripinfo.xml" ]; then
    cp "$PROJECT_HOME/tripinfo.xml" "$RESULTS_DIR/tripinfo.xml"
    echo "tripinfo.xml copiado."
fi

echo "╔════════════════════════════════════════════╗"
echo "║            TESTE CONCLUÍDO!                ║"
echo "╚════════════════════════════════════════════╝"