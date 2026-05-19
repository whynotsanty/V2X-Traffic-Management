#!/bin/bash
#
# 30 SIMULAÇÕES MOSAIC - PIPELINE LIMPO
# Coleta métricas via:
#   1. MetricsCollector.java (V2X, CO2, fila, etc)
#   2. SUMO XMLs (tripinfo, netstate, detector)
# Output: metrics_sumo_X.json para cada run
#

SCENARIO_CONFIG="/home/netsim/tpnpr/cenario_manhattan/scenario_config.json"
MOSAIC_HOME="/home/netsim/opt/eclipse-mosaic-24.1"
PROJECT_HOME="/home/netsim/tpnpr"
RESULTS_DIR="$PROJECT_HOME/results"
NUM_RUNS=30

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         🚀 MOSAIC 30-RUN SIMULATION                        ║"
echo "║  Scenario: Manhattan | Detector: -E17 (Bottleneck)         ║"
echo "╚════════════════════════════════════════════════════════════╝"

mkdir -p "$RESULTS_DIR"
START_TIME=$(date +%s)

for i in $(seq 1 $NUM_RUNS); do
    RUN_DIR="$RESULTS_DIR/run_$i"
    mkdir -p "$RUN_DIR"
    
    ELAPSED=$(($(date +%s) - START_TIME))
    ELAPSED_MIN=$((ELAPSED / 60))
    
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  Run $i/$NUM_RUNS | Elapsed: ${ELAPSED_MIN}m"
    echo "═══════════════════════════════════════════════════════════"
    
    # Limpar ficheiros antigos
    rm -f "$PROJECT_HOME/metrics_from_wrapper.json" \
          "$PROJECT_HOME/tripinfo.xml" \
          "$PROJECT_HOME/netstate.xml" \
          "$PROJECT_HOME/bottleneck_detector.xml"
    
    # [1] MOSAIC simulation
    echo "  [1/3] 🚀 MOSAIC simulation..."
    cd "$MOSAIC_HOME"
    timeout 300 ./mosaic.sh -c "$SCENARIO_CONFIG" -w 1 > "$RUN_DIR/mosaic.log" 2>&1
    
    # [2] Fix XMLs e copiar
    echo "  [2/3] 📋 Copying & fixing XMLs..."
    
    # Fix tripinfo
    if [ -f "$PROJECT_HOME/tripinfo.xml" ]; then
        if ! tail -1 "$PROJECT_HOME/tripinfo.xml" | grep -q "</tripinfos>"; then
            echo "</tripinfos>" >> "$PROJECT_HOME/tripinfo.xml"
        fi
        cp "$PROJECT_HOME/tripinfo.xml" "$RUN_DIR/"
    fi
    
    # Fix netstate
    if [ -f "$PROJECT_HOME/netstate.xml" ]; then
        if ! tail -1 "$PROJECT_HOME/netstate.xml" | grep -q "</netstate>"; then
            echo "</netstate>" >> "$PROJECT_HOME/netstate.xml"
        fi
        cp "$PROJECT_HOME/netstate.xml" "$RUN_DIR/"
    fi
    
    # Fix detector
    if [ -f "$PROJECT_HOME/bottleneck_detector.xml" ]; then
        if ! tail -1 "$PROJECT_HOME/bottleneck_detector.xml" | grep -q "</detector>"; then
            echo "</detector>" >> "$PROJECT_HOME/bottleneck_detector.xml"
        fi
        cp "$PROJECT_HOME/bottleneck_detector.xml" "$RUN_DIR/"
    fi
    
    # Copy wrapper metrics
    if [ -f "$PROJECT_HOME/metrics_from_wrapper.json" ]; then
        cp "$PROJECT_HOME/metrics_from_wrapper.json" "$RUN_DIR/metrics_wrapper.json"
    fi
    
    # [3] Process metrics
    echo "  [3/3] 📊 Processing metrics..."
    cd "$PROJECT_HOME"
    python3 metrics_aggregator.py $i > /dev/null 2>&1
    
    if [ -f "$RUN_DIR/metrics_sumo_$i.json" ]; then
        echo "  ✅ Completo!"
    else
        echo "  ⚠️  Incompleto"
    fi
done

# Final summary
TOTAL_TIME=$(($(date +%s) - START_TIME))
TOTAL_MIN=$((TOTAL_TIME / 60))
TOTAL_SEC=$((TOTAL_TIME % 60))

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║             ✅ 30 RUNS COMPLETE!                           ║"
echo "║   Total Time: ${TOTAL_MIN}m ${TOTAL_SEC}s                           "
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📁 Resultados: $RESULTS_DIR/run_1 até run_30"
echo "📊 Para compilar estatísticas:"
echo "   python3 compile_statistics.py"
echo ""
