#!/bin/bash
# Script de 10 Simulações com Automação e Geração de CSV Final

MOSAIC_HOME="/home/netsim/opt/eclipse-mosaic-24.1"
PROJECT_HOME="/home/netsim/tpnpr"
SCENARIO_CONFIG="$PROJECT_HOME/cenario_manhattan/scenario_config.json"
RESULTS_DIR="$PROJECT_HOME/results/10_runs"
NUM_RUNS=10

echo "╔════════════════════════════════════════════╗"
echo "║             TESTE DE 10 RUNS               ║"
echo "╚════════════════════════════════════════════╝"

# PASSO 1: Compilação
echo "[1/3] A compilar código Maven..."
cd "$PROJECT_HOME"
mvn clean package -DskipTests -q || { echo "ERRO na compilação"; exit 1; }
cp "$PROJECT_HOME/target/tp-app-1.0.jar" "$PROJECT_HOME/cenario_manhattan/application/tp-app-1.0.jar"

# PASSO 2: Preparar diretório de resultados
rm -rf "$RESULTS_DIR"
mkdir -p "$RESULTS_DIR/json_data"

# PASSO 3: Executar 10 runs
echo "[2/3] A executar 10 simulações..."
for i in $(seq 1 $NUM_RUNS); do
    SEED=$RANDOM
    echo " - Execução $i/10 (Seed: $SEED)"
    
    cd "$MOSAIC_HOME"
    ./mosaic.sh -c "$SCENARIO_CONFIG" -r $SEED > /dev/null 2>&1
    
    # Copiar resultado
    if [ -f "$PROJECT_HOME/metrics_from_wrapper.json" ]; then
        cp "$PROJECT_HOME/metrics_from_wrapper.json" "$RESULTS_DIR/json_data/run_$i.json"
    else
        echo "   AVISO: Falha na run $i"
    fi
done

# PASSO 4: Processar Métricas (Python)
echo "[3/3] A calcular Média e Mediana..."
cat << 'EOF' > process_metrics.py
import json, statistics, os, glob

# Mapeamento: Nome_CSV -> Caminho_JSON
mapping = {
    "Trip_Time_Avg": ("trips", "avg_trip_time_s"),
    "P50": ("trips", "percentile_50_s"),
    "P95": ("trips", "percentile_95_s"),
    "Queue_Max_M": ("queue", "max_queue_length_m"),
    "Queue_Duration_S": ("queue", "queue_duration_s"),
    "Throughput": ("throughput", "avg_throughput_vps"),
    "V2X_Efficiency": ("v2x", "disseminationEfficiency"),
    "CO2_Avg": ("trips", "avg_co2_g"),
    "Fuel_Avg": ("trips", "avg_fuel_ml"),
    "Speed_Bottleneck": ("bottleneck", "avg_speed_kmh")
}

files = glob.glob("json_data/run_*.json")
data_store = {key: [] for key in mapping.keys()}

for f in files:
    with open(f, 'r') as jf:
        try:
            d = json.load(jf)
            for name, (cat, field) in mapping.items():
                val = d.get(cat, {}).get(field, 0)
                data_store[name].append(val)
        except: continue

print("Métrica,Média,Mediana")
for name in mapping.keys():
    vals = data_store[name]
    if vals:
        avg = statistics.mean(vals)
        med = statistics.median(vals)
        print(f"{name},{avg:.3f},{med:.3f}")
EOF

# Executar script python
cd "$RESULTS_DIR"
python3 process_metrics.py > resultados_finais.csv

echo ""
echo "╔════════════════════════════════════════════╗"
echo "║                 SUCESSO                     ║"
echo "╚════════════════════════════════════════════╝"
echo " CSV gerado em: $RESULTS_DIR/resultados_finais.csv"
cat resultados_finais.csv