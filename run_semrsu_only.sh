#!/bin/bash
# Re-corre APENAS as 8 células SEM RSU (as COM RSU já estão válidas).
MOSAIC_HOME="/home/netsim/opt/eclipse-mosaic-24.1"
PROJECT="/home/netsim/opt/tpnpr"
SCENARIO="$PROJECT/cenario_manhattan"
CFG_ARG="$SCENARIO/scenario_config.json"
SUMO_DIR="$SCENARIO/sumo"
MAP_DIR="$SCENARIO/mapping"
ROUTES_LIVE="$SUMO_DIR/routes.rou.xml"
MAP_LIVE="$MAP_DIR/mapping_config.json"
BACKUP_DIR="$PROJECT/.pipeline_backup"
set -u
mkdir -p "$BACKUP_DIR"
cp "$ROUTES_LIVE" "$BACKUP_DIR/routes.rou.xml.bak2" 2>/dev/null
cp "$MAP_LIVE" "$BACKUP_DIR/mapping_config.json.bak2" 2>/dev/null
restaurar() {
  echo ""; echo "[CLEANUP] restaurar ficheiros live..."
  [ -f "$BACKUP_DIR/routes.rou.xml.bak2" ] && cp "$BACKUP_DIR/routes.rou.xml.bak2" "$ROUTES_LIVE"
  [ -f "$BACKUP_DIR/mapping_config.json.bak2" ] && cp "$BACKUP_DIR/mapping_config.json.bak2" "$MAP_LIVE"
  echo "  restaurado."
}
trap restaurar EXIT INT TERM
N_RUNS="${1:-3}"
OK=0; FAIL=0; TOTAL=0
OUT_BASE="$PROJECT/results_pipeline"
for C in 1 2; do
  ROUTES_SRC="$SUMO_DIR/routes_cenario${C}.rou.xml"
  MAP_SRC="$MAP_DIR/mapping_semrsu.json"
  for T in 1 2 3 4; do
    CELL="cen${C}_semrsu_T${T}"
    CELL_DIR="$OUT_BASE/$CELL"
    mkdir -p "$CELL_DIR"
    echo ""; echo "[CELL $((++TOTAL))/8] $CELL"
    cp "$ROUTES_SRC" "$ROUTES_LIVE"
    cp "$MAP_SRC" "$MAP_LIVE"
    for r in $(seq 1 "$N_RUNS"); do
      RUN_DIR="$CELL_DIR/run_${r}"; mkdir -p "$RUN_DIR"
      SEED=$RANDOM
      OUT_JSON="$RUN_DIR/metrics_wrapper.json"
      echo "  [RUN $r/$N_RUNS] seed=$SEED"
      export JAVA_TOOL_OPTIONS="-Dnpr.teste=$T -Dnpr.metrics.out=$OUT_JSON"
      ( cd "$MOSAIC_HOME" && ./mosaic.sh -c "$CFG_ARG" -r "$SEED" > "$RUN_DIR/mosaic.log" 2>&1 )
      unset JAVA_TOOL_OPTIONS
      if [ -f "$OUT_JSON" ]; then
        [ -f "$PROJECT/tripinfo.xml" ] && cp "$PROJECT/tripinfo.xml" "$RUN_DIR/tripinfo.xml"
        OK=$((OK+1)); echo "    OK"
      else
        FAIL=$((FAIL+1)); echo "    FALHOU (sem metrics)"
      fi
    done
  done
done
echo ""; echo "=== RESUMO SEM-RSU: OK=$OK FAIL=$FAIL (esperado $((N_RUNS*8))) ==="
