#!/bin/bash
# Script de Teste Único com Seed Aleatória

MOSAIC_HOME="/home/netsim/opt/eclipse-mosaic-24.1"
SCENARIO_CONFIG="/home/netsim/tpnpr/cenario_manhattan/scenario_config.json"
PROJECT_HOME="/home/netsim/tpnpr"

# Gerar uma Seed aleatória
SEED=$RANDOM
echo "A iniciar simulação com Seed: $SEED"

# Limpar resultados anteriores
rm -rf "$PROJECT_HOME/results/run_test"
mkdir -p "$PROJECT_HOME/results/run_test"

# Mover para a pasta do MOSAIC
cd "$MOSAIC_HOME"

# Correr o MOSAIC com random seed
./mosaic.sh -c "$SCENARIO_CONFIG" -r $SEED

# Copiar o resultado
if [ -f "$PROJECT_HOME/metrics_from_wrapper.json" ]; then
    cp "$PROJECT_HOME/metrics_from_wrapper.json" "$PROJECT_HOME/results/run_test/metrics_test.json"
    echo "Teste concluído com sucesso!"
    echo "Resultados da run (Seed $SEED):"
    cat "$PROJECT_HOME/results/run_test/metrics_test.json"
else
    echo "Erro: O ficheiro metrics_from_wrapper.json não foi gerado!"
fi