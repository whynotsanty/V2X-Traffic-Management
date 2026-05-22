#!/bin/bash

MOSAIC_HOME="/home/netsim/opt/eclipse-mosaic-24.1"
SCENARIO_CONFIG="/home/netsim/tpnpr/cenario_manhattan/scenario_config.json"
PROJECT_HOME="/home/netsim/tpnpr"
RESULTS_DIR="$PROJECT_HOME/results"

echo "╔════════════════════════════════════════════╗"
echo "║         A CORRER 30 RUNS DE TESTE          ║"
echo "╚════════════════════════════════════════════╝"

# Limpa diretório de resultados antigo
rm -rf "$RESULTS_DIR"
mkdir -p "$RESULTS_DIR"

for i in {1..30}; do
    RUN_DIR="$RESULTS_DIR/run_$i"
    mkdir -p "$RUN_DIR"
    
    # Seed aleatória para cada run
    SEED=$RANDOM
    
    echo "--- A executar Run $i/30 (Seed: $SEED) ---"
    
    cd "$MOSAIC_HOME"
    ./mosaic.sh -c "$SCENARIO_CONFIG" -r $SEED > "$RUN_DIR/mosaic.log" 2>&1
    
    if [ -f "$PROJECT_HOME/metrics_from_wrapper.json" ]; then
        cp "$PROJECT_HOME/metrics_from_wrapper.json" "$RUN_DIR/metrics_wrapper.json"
        echo "Run $i concluída com sucesso."
    else
        echo "Erro na Run $i: metrics_from_wrapper.json não encontrado."
    fi
done

echo "30 Runs concluídas! Os dados encontram-se guardados em $RESULTS_DIR"