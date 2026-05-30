#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compilar_pipeline.py - Compilador da matriz de resultados do pipeline V2X.

Percorre  results_pipeline/cen{C}_{rsu}rsu_T{T}/run_*/  e, por celula, agrega
as metricas de  metrics_wrapper.json  e (se existir)  tripinfo.xml  (saida real
do SUMO: tempos/emissoes por veiculo).

Reutiliza as funcoes de compilar_resultados.py:
  - parse_tripinfo()  (tripinfo real do SUMO)
  - percentil(), estatisticas()
  - comparar()        (Welch t-test, COM vs SEM RSU)

Produz:
  - Resultados_Pipeline.csv     : 1 linha por (cenario, RSU, teste, metrica) com
                                  Media, DP, IC95_low, IC95_high, Mediana, n_runs
  - Significancia_Pipeline.csv  : p-values COM vs SEM RSU por (cenario, teste, metrica)

Robusto: nao rebenta se faltarem celulas/ficheiros (regista aviso).
As metricas do metrics_wrapper.json tem estrutura aninhada
(trips / bottleneck / throughput / v2x / queue); metricas ausentes sao saltadas.
"""

import os
import csv
import glob
import json
import math
import statistics

# Reutiliza as funcoes ja existentes no compilador base.
import compilar_resultados as base

PROJ = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(PROJ, "results_pipeline")
OUT_CSV = os.path.join(PROJ, "Resultados_Pipeline.csv")
SIG_CSV = os.path.join(PROJ, "Significancia_Pipeline.csv")

CENARIOS = [1, 2]
RSUS = ["com", "sem"]
TESTES = [1, 2, 3, 4]

avisos = []

# ---------------------------------------------------------------------------
# Mapeamento (seccao, chave_json) -> nome_final_da_metrica.
# As chaves seguem a estrutura real do metrics_wrapper.json produzido pelo
# MetricsCollector. Quando ausentes, a metrica e simplesmente saltada.
# ---------------------------------------------------------------------------
METRICAS_JSON = [
    # (seccao, chave, nome_final)
    ("trips", "avg_trip_time_s", "tempoMedioViagem"),
    ("trips", "percentile_50_s", "tempoViagem_P50"),
    ("trips", "percentile_90_s", "tempoViagem_P90"),
    ("trips", "percentile_95_s", "tempoViagem_P95"),
    ("trips", "avg_co2_g", "co2Medio_g"),
    ("trips", "avg_fuel_ml", "combustivelMedio_ml"),
    ("queue", "max_queue_length_vehicles", "comprimentoMaxFila"),
    ("queue", "max_queue_length_m", "comprimentoMaxFila_m"),
    ("queue", "queue_duration_s", "duracaoFila_s"),
    ("throughput", "avg_throughput_vps", "throughput_vps"),
    ("throughput", "total_vehicles_passed", "throughput_total"),
    ("bottleneck", "avg_speed_kmh", "velMediaGargalo_kmh"),
    # --- V2X ---
    ("v2x", "suppressionRatio", "suppressionRatio"),
    ("v2x", "totalDenmsReceived", "totalDenmsReceived"),
    ("v2x", "totalCamsReceived", "totalCamsReceived"),
    ("v2x", "totalV2xMessages", "totalV2xMessages"),
    ("v2x", "totalAlertsTriggered", "totalAlertsTriggered"),
    ("v2x", "disseminationEfficiency", "disseminationEfficiency"),
]

# Ordem preferida das metricas no CSV de saida.
ORDEM_METRICAS = [nome for (_, _, nome) in METRICAS_JSON]
# Metricas vindas do tripinfo real (substituem/complementam as do JSON).
ORDEM_METRICAS = [
    "tempoMedioViagem_real", "tempoViagem_P50_real",
    "tempoViagem_P90_real", "tempoViagem_P95_real",
    "co2Medio_real_g", "combustivelMedio_real_ml",
] + ORDEM_METRICAS


def metricas_de_run(run_dir):
    """Devolve {metrica: valor} para uma run, combinando JSON + tripinfo real."""
    out = {}

    # --- metrics_wrapper.json (estrutura aninhada) ---
    mpath = os.path.join(run_dir, "metrics_wrapper.json")
    if os.path.isfile(mpath):
        try:
            d = json.load(open(mpath))
        except Exception as e:
            avisos.append("Falha a ler %s: %s" % (mpath, e))
            d = {}
        for seccao, chave, nome in METRICAS_JSON:
            sec = d.get(seccao, {})
            if isinstance(sec, dict) and isinstance(sec.get(chave), (int, float)):
                out[nome] = float(sec[chave])
    else:
        avisos.append("Run sem metrics: %s" % run_dir)

    # --- tripinfo.xml (saida real do SUMO; preferida quando existe) ---
    tinfo = base.parse_tripinfo(run_dir)
    if tinfo:
        dur = tinfo.get("duration") or []
        if dur:
            out["tempoMedioViagem_real"] = statistics.mean(dur)
            out["tempoViagem_P50_real"] = base.percentil(dur, 50)
            out["tempoViagem_P90_real"] = base.percentil(dur, 90)
            out["tempoViagem_P95_real"] = base.percentil(dur, 95)
        co2 = tinfo.get("CO2_abs") or []
        if co2:
            out["co2Medio_real_g"] = statistics.mean(co2)
        fuel = tinfo.get("fuel_abs") or []
        if fuel:
            out["combustivelMedio_real_ml"] = statistics.mean(fuel)

    return out


def recolher_celula(C, rsu, T):
    """Devolve {metrica: [valores_por_run]} para a celula (C, rsu, T)."""
    celula_dir = os.path.join(ROOT, "cen%d_%srsu_T%d" % (C, rsu, T))
    por_metrica = {}
    runs = sorted(glob.glob(os.path.join(celula_dir, "run_*")))
    if not runs:
        avisos.append("Celula sem runs: %s" % celula_dir)
        return por_metrica
    for run in runs:
        for k, v in metricas_de_run(run).items():
            if v is not None:
                por_metrica.setdefault(k, []).append(v)
    return por_metrica


def main():
    if not os.path.isdir(ROOT):
        print("[ERRO] Pasta nao encontrada: %s" % ROOT)
        print("       Corre primeiro run_pipeline.sh.")
        return

    dados = {}          # (C, rsu, T) -> {metrica: [valores]}
    metricas_vistas = set()
    for C in CENARIOS:
        for rsu in RSUS:
            for T in TESTES:
                cel = recolher_celula(C, rsu, T)
                dados[(C, rsu, T)] = cel
                metricas_vistas.update(cel.keys())

    ordenadas = [m for m in ORDEM_METRICAS if m in metricas_vistas]
    extras = sorted(m for m in metricas_vistas if m not in ORDEM_METRICAS)
    todas = ordenadas + extras

    # --- Resultados_Pipeline.csv ---
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cenario", "rsu", "teste", "metrica",
                    "Media", "DP", "IC95_low", "IC95_high", "Mediana", "n_runs"])
        for C in CENARIOS:
            for rsu in RSUS:
                for T in TESTES:
                    cel = dados[(C, rsu, T)]
                    for m in todas:
                        vals = cel.get(m)
                        if not vals:
                            continue
                        media, dp, lo, hi, mediana = base.estatisticas(vals)
                        if media is None:
                            continue
                        w.writerow([C, rsu, T, m,
                                    "%.6g" % media, "%.6g" % dp,
                                    "%.6g" % lo, "%.6g" % hi,
                                    "%.6g" % mediana, len(vals)])
    print("[OK] Escrito %s" % OUT_CSV)

    # --- Significancia_Pipeline.csv (COM vs SEM RSU, por cenario/teste) ---
    with open(SIG_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cenario", "teste", "metrica",
                    "n_com", "n_sem", "media_com", "media_sem",
                    "welch_t", "welch_p", "mannwhitney_p", "metodo"])
        for C in CENARIOS:
            for T in TESTES:
                grupo_com = dados[(C, "com", T)]
                grupo_sem = dados[(C, "sem", T)]
                # comparar() de compilar_resultados.py: {metrica:[valores]} x2
                for linha in base.comparar(grupo_com, grupo_sem):
                    w.writerow([C, T, linha["metrica"],
                                linha["n_com"], linha["n_sem"],
                                "%.6g" % linha["media_com"],
                                "%.6g" % linha["media_sem"],
                                linha["welch_t"], linha["welch_p"],
                                linha.get("mannwhitney_p"),
                                linha.get("metodo", "")])
    print("[OK] Escrito %s" % SIG_CSV)

    if avisos:
        print("\n[AVISOS] %d:" % len(avisos))
        for a in avisos[:50]:
            print("  - %s" % a)
        if len(avisos) > 50:
            print("  ... (+%d)" % (len(avisos) - 50))
    else:
        print("\n[OK] Sem avisos.")


if __name__ == "__main__":
    main()
