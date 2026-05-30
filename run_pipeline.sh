#!/usr/bin/env bash
#
# run_pipeline.sh - Orquestracao da matriz de testes V2X (Eclipse MOSAIC + SUMO)
#
# Matriz: 2 cenarios (volume) x 2 RSU (com/sem) x 4 testes (personalidades) x N runs
# Uso:    bash run_pipeline.sh [N]      (N = numero de runs por celula, default 3)
#
set -u

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------
PROJ="/home/netsim/opt/tpnpr"
MOSAIC_HOME="/home/netsim/opt/eclipse-mosaic-24.1"
SCENARIO_CFG="$PROJ/cenario_manhattan/scenario_config.json"

SUMO_DIR="$PROJ/cenario_manhattan/sumo"
MAP_DIR="$PROJ/cenario_manhattan/mapping"

ROUTES_LIVE="$SUMO_DIR/routes.rou.xml"
MAP_LIVE="$MAP_DIR/mapping_config.json"
TRIPINFO_SRC="$PROJ/tripinfo.xml"

RESULTS_ROOT="$PROJ/results_pipeline"

N_RUNS="${1:-3}"

CENARIOS=(1 2)
RSUS=(com sem)
TESTES=(1 2 3 4)

# ---------------------------------------------------------------------------
# Backup + restauro dos ficheiros originais (live)
# ---------------------------------------------------------------------------
BKP_ROUTES="$(mktemp)"
BKP_MAP="$(mktemp)"
cp "$ROUTES_LIVE" "$BKP_ROUTES"
cp "$MAP_LIVE" "$BKP_MAP"

restaurar() {
    echo ""
    echo "[CLEANUP] A restaurar ficheiros originais (routes.rou.xml, mapping_config.json)..."
    cp "$BKP_ROUTES" "$ROUTES_LIVE" 2>/dev/null && echo "  routes.rou.xml restaurado."
    cp "$BKP_MAP" "$MAP_LIVE" 2>/dev/null && echo "  mapping_config.json restaurado."
    rm -f "$BKP_ROUTES" "$BKP_MAP"
}
trap restaurar EXIT INT TERM

# ---------------------------------------------------------------------------
# Execucao da matriz
# ---------------------------------------------------------------------------
TOTAL_CELULAS=$(( ${#CENARIOS[@]} * ${#RSUS[@]} * ${#TESTES[@]} ))
celula=0
ok=0
fail=0

echo "==========================================================="
echo " PIPELINE V2X - matriz $TOTAL_CELULAS celulas x $N_RUNS runs"
echo " Output: $RESULTS_ROOT"
echo "==========================================================="

for C in "${CENARIOS[@]}"; do
    ROUTES_VARIANT="$SUMO_DIR/routes_cenario${C}.rou.xml"
    for rsu in "${RSUS[@]}"; do
        MAP_VARIANT="$MAP_DIR/mapping_${rsu}rsu.json"
        for T in "${TESTES[@]}"; do
            celula=$(( celula + 1 ))
            echo ""
            echo "-----------------------------------------------------------"
            echo "[COMBINACAO $celula/$TOTAL_CELULAS] cenario=$C rsu=$rsu teste=$T"
            echo "-----------------------------------------------------------"

            if [ ! -f "$ROUTES_VARIANT" ]; then
                echo "[ERRO] Falta $ROUTES_VARIANT - a saltar celula."
                fail=$(( fail + N_RUNS )); continue
            fi
            if [ ! -f "$MAP_VARIANT" ]; then
                echo "[ERRO] Falta $MAP_VARIANT - a saltar celula."
                fail=$(( fail + N_RUNS )); continue
            fi

            # Aplica a variante correta para esta celula
            cp "$ROUTES_VARIANT" "$ROUTES_LIVE"
            cp "$MAP_VARIANT" "$MAP_LIVE"

            for (( r=1; r<=N_RUNS; r++ )); do
                OUTDIR="$RESULTS_ROOT/cen${C}_${rsu}rsu_T${T}/run_${r}"
                mkdir -p "$OUTDIR"

                # Seed aleatoria (0 .. 2^31-1)
                SEED=$(( RANDOM * 65536 + RANDOM ))

                echo "  [RUN $r/$N_RUNS] seed=$SEED -> $OUTDIR"

                export JAVA_TOOL_OPTIONS="-Dnpr.teste=$T -Dnpr.metrics.out=$OUTDIR/metrics_wrapper.json"

                # Corre o MOSAIC (log da run guardado no OUTDIR)
                (
                    cd "$MOSAIC_HOME" && \
                    ./mosaic.sh -c "$SCENARIO_CFG" -r "$SEED"
                ) > "$OUTDIR/mosaic.log" 2>&1
                rc=$?

                unset JAVA_TOOL_OPTIONS

                # Copia o tripinfo gerado pelo SUMO
                if [ -f "$TRIPINFO_SRC" ]; then
                    cp "$TRIPINFO_SRC" "$OUTDIR/tripinfo.xml"
                fi

                # Validacao: a run e' considerada OK se gerou metrics
                if [ -f "$OUTDIR/metrics_wrapper.json" ]; then
                    ok=$(( ok + 1 ))
                    echo "    OK (metrics gerado)."
                else
                    fail=$(( fail + 1 ))
                    echo "    FALHOU (sem metrics_wrapper.json, rc=$rc). A continuar."
                fi
            done
        done
    done
done

# ---------------------------------------------------------------------------
# Resumo
# ---------------------------------------------------------------------------
echo ""
echo "==========================================================="
echo " RESUMO PIPELINE"
echo "   Runs totais esperadas : $(( TOTAL_CELULAS * N_RUNS ))"
echo "   Runs OK               : $ok"
echo "   Runs falhadas         : $fail"
echo "   Resultados em         : $RESULTS_ROOT"
echo "==========================================================="

# (restauro feito pelo trap EXIT)
