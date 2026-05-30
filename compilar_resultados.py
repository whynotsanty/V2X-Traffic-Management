import os
import json
import csv
import math
import statistics
import xml.etree.ElementTree as ET

# Diretório base dos resultados
# Cada subpasta "run_N" contém um metrics_wrapper.json e, opcionalmente, um tripinfo.xml
RESULTS_DIR = "/home/netsim/opt/tpnpr/results"

# Diretórios opcionais para a comparação ComRSU vs SemRSU.
# Se existirem, são usados pela função comparar(); caso contrário só se agrega RESULTS_DIR.
RESULTS_COMRSU_DIR = "/home/netsim/opt/tpnpr/results_comrsu"
RESULTS_SEMRSU_DIR = "/home/netsim/opt/tpnpr/results_semrsu"


def carregar_metricas(run_dir):
    """Lê o metrics_wrapper.json de uma pasta run_N."""
    caminho = os.path.join(run_dir, "metrics_wrapper.json")
    if not os.path.exists(caminho):
        return None
    with open(caminho, "r") as f:
        return json.load(f)


def parse_tripinfo(run_dir):
    """Faz parse de results/run_N/tripinfo.xml (saída real do SUMO), se existir.

    Devolve um dicionário com listas por veículo:
      {"duration": [...], "CO2_abs": [...], "fuel_abs": [...]}
    Devolve None se o ficheiro não existir ou não for parseável.
    As emissões dependem do device de emissões estar ativo no SUMO; quando
    ausentes ficam como listas vazias e o JSON serve de fonte alternativa.
    """
    caminho = os.path.join(run_dir, "tripinfo.xml")
    if not os.path.exists(caminho):
        return None
    try:
        tree = ET.parse(caminho)
    except (ET.ParseError, OSError):
        return None
    root = tree.getroot()

    duracoes = []
    co2 = []
    fuel = []
    for trip in root.iter("tripinfo"):
        d = trip.get("duration")
        if d is not None:
            try:
                duracoes.append(float(d))
            except ValueError:
                pass
        # As emissões aparecem como sub-elemento <emissions .../> quando o
        # device de emissões está ativo (device.emissions.probability=1.0).
        emi = trip.find("emissions")
        if emi is not None:
            c = emi.get("CO2_abs")
            fu = emi.get("fuel_abs")
            if c is not None:
                try:
                    co2.append(float(c))
                except ValueError:
                    pass
            if fu is not None:
                try:
                    fuel.append(float(fu))
                except ValueError:
                    pass

    return {"duration": duracoes, "CO2_abs": co2, "fuel_abs": fuel}


def percentil(valores, p):
    """Percentil p (0-100) por interpolação linear. Lista não vazia."""
    if not valores:
        return None
    dados = sorted(valores)
    if len(dados) == 1:
        return dados[0]
    k = (len(dados) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return dados[int(k)]
    return dados[f] + (dados[c] - dados[f]) * (k - f)


def estatisticas(valores):
    """Devolve (média, DP, IC95_low, IC95_high, mediana) para uma lista.

    DP é o desvio-padrão amostral (n-1); com n<2 assume-se 0.
    IC95 = média +/- 1.96 * DP / sqrt(n).
    """
    valores = [v for v in valores if v is not None]
    if not valores:
        return (None, None, None, None, None)
    n = len(valores)
    media = statistics.mean(valores)
    mediana = statistics.median(valores)
    dp = statistics.stdev(valores) if n >= 2 else 0.0
    erro = 1.96 * dp / math.sqrt(n) if n >= 1 else 0.0
    return (media, dp, media - erro, media + erro, mediana)


def extrair_metricas_run(m, tinfo):
    """Combina o metrics_wrapper.json (m) com o tripinfo real (tinfo, pode ser None).

    Fonte preferida: tripinfo real do SUMO. Cai para o JSON quando o tripinfo
    não existe ou não tem o valor correspondente.
    Devolve um dicionário {nome_metrica: valor} para esta run.
    """
    trips = m.get("trips", {}) if m else {}
    queue = m.get("queue", {}) if m else {}
    throughput = m.get("throughput", {}) if m else {}
    v2x = m.get("v2x", {}) if m else {}

    out = {}

    # --- Tempo de viagem: P50/P95 e média a partir do tripinfo real, se houver ---
    if tinfo and tinfo.get("duration"):
        dur = tinfo["duration"]
        out["meanTravelTime"] = statistics.mean(dur)
        out["travelTime_P50"] = percentil(dur, 50)
        out["travelTime_P95"] = percentil(dur, 95)
    else:
        # Alternativa: valores agregados do JSON (sem distribuição por veículo)
        mtt = trips.get("meanTravelTime")
        if mtt is not None:
            out["meanTravelTime"] = mtt
        p50 = trips.get("travelTimeP50") or trips.get("p50TravelTime")
        p95 = trips.get("travelTimeP95") or trips.get("p95TravelTime")
        if p50 is not None:
            out["travelTime_P50"] = p50
        if p95 is not None:
            out["travelTime_P95"] = p95

    # --- Emissões: preferir tripinfo real (média por veículo) ---
    if tinfo and tinfo.get("CO2_abs"):
        out["CO2_abs_mean"] = statistics.mean(tinfo["CO2_abs"])
    elif trips.get("meanCO2") is not None:
        out["CO2_abs_mean"] = trips.get("meanCO2")

    if tinfo and tinfo.get("fuel_abs"):
        out["fuel_abs_mean"] = statistics.mean(tinfo["fuel_abs"])
    elif trips.get("meanFuel") is not None:
        out["fuel_abs_mean"] = trips.get("meanFuel")

    # --- Filas / throughput ---
    if queue.get("maxQueueLength") is not None:
        out["maxQueueLength"] = queue.get("maxQueueLength")
    if throughput.get("vehiclesPerHour") is not None:
        out["throughput"] = throughput.get("vehiclesPerHour")
    elif throughput.get("total") is not None:
        out["throughput"] = throughput.get("total")

    # --- V2X (novo esquema do Agente A) ---
    for chave in (
        "totalCamsReceived",
        "totalDenmsReceived",
        "totalAlertsTriggered",
        "totalV2xMessages",
        "totalRetransmissions",
        "totalSuppressions",
        "suppressionRatio",
    ):
        if v2x.get(chave) is not None:
            out[chave] = v2x.get(chave)

    return out


def carregar_grupo(results_dir):
    """Carrega todas as runs de um diretório, devolvendo:
       (lista_de_dicts_por_run, dict_metrica->lista_de_valores).
    """
    por_run = []
    if not os.path.isdir(results_dir):
        return por_run, {}

    for nome in sorted(os.listdir(results_dir)):
        if not nome.startswith("run_"):
            continue
        run_dir = os.path.join(results_dir, nome)
        m = carregar_metricas(run_dir)
        tinfo = parse_tripinfo(run_dir)
        if m is None and tinfo is None:
            continue
        por_run.append(extrair_metricas_run(m or {}, tinfo))

    # Reorganiza por métrica
    por_metrica = {}
    for run in por_run:
        for chave, valor in run.items():
            if valor is None:
                continue
            por_metrica.setdefault(chave, []).append(valor)

    return por_run, por_metrica


# ---------------------------------------------------------------------------
# Teste de significância ComRSU vs SemRSU
# ---------------------------------------------------------------------------
try:
    from scipy import stats as _scipy_stats  # noqa: F401
    _TEM_SCIPY = True
except ImportError:
    _scipy_stats = None
    _TEM_SCIPY = False


def _welch_t_manual(a, b):
    """t de Welch implementado manualmente. Devolve (t, gl, p_aprox).

    p_aprox é uma aproximação two-sided baseada numa fórmula logística para
    a CDF da t de Student (não requer scipy). Serve para indicação grosseira.
    """
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return (None, None, None)
    ma, mb = statistics.mean(a), statistics.mean(b)
    va, vb = statistics.variance(a), statistics.variance(b)
    if va == 0 and vb == 0:
        return (0.0, na + nb - 2, 1.0)
    se = math.sqrt(va / na + vb / nb)
    if se == 0:
        return (0.0, na + nb - 2, 1.0)
    t = (ma - mb) / se
    # Graus de liberdade de Welch-Satterthwaite
    num = (va / na + vb / nb) ** 2
    den = (va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1)
    gl = num / den if den != 0 else (na + nb - 2)
    # Aproximação da CDF da t de Student via curva logística (Page, 1977-style).
    # Suficiente como p-value aproximado quando scipy não está disponível.
    x = abs(t)
    g = gl
    z = x * (1 - 1.0 / (4 * g)) / math.sqrt(1 + x * x / (2 * g))
    p_uma_cauda = 1.0 / (1.0 + math.exp(1.5976 * z + 0.070566 * z ** 3))
    p = 2.0 * p_uma_cauda
    return (t, gl, min(1.0, p))


def comparar(grupo_com, grupo_sem):
    """Compara dois grupos de runs (ComRSU vs SemRSU) métrica a métrica.

    Argumentos:
      grupo_com, grupo_sem: dicionários {metrica: [valores_por_run]}
                            (formato devolvido por carregar_grupo()[1]).
    Devolve uma lista de dicionários, um por métrica comum, com:
      metrica, n_com, n_sem, media_com, media_sem,
      welch_t, welch_p, mannwhitney_u, mannwhitney_p, metodo.

    Robustez:
      - Se uma das listas tiver menos de 2 valores, a métrica é ignorada.
      - Se scipy existir usa Welch t-test + Mann-Whitney; caso contrário usa
        o t de Welch manual (p aproximado) e omite o Mann-Whitney.
    """
    resultados = []
    metricas = sorted(set(grupo_com) & set(grupo_sem))
    for metrica in metricas:
        a = [v for v in grupo_com[metrica] if v is not None]
        b = [v for v in grupo_sem[metrica] if v is not None]
        if len(a) < 2 or len(b) < 2:
            continue

        linha = {
            "metrica": metrica,
            "n_com": len(a),
            "n_sem": len(b),
            "media_com": statistics.mean(a),
            "media_sem": statistics.mean(b),
            "welch_t": None,
            "welch_p": None,
            "mannwhitney_u": None,
            "mannwhitney_p": None,
        }

        if _TEM_SCIPY:
            t, p = _scipy_stats.ttest_ind(a, b, equal_var=False)
            linha["welch_t"] = float(t)
            linha["welch_p"] = float(p)
            try:
                u, pu = _scipy_stats.mannwhitneyu(a, b, alternative="two-sided")
                linha["mannwhitney_u"] = float(u)
                linha["mannwhitney_p"] = float(pu)
            except ValueError:
                pass
            linha["metodo"] = "scipy"
        else:
            t, gl, p = _welch_t_manual(a, b)
            linha["welch_t"] = t
            linha["welch_p"] = p
            linha["metodo"] = "welch_manual"

        resultados.append(linha)

    return resultados


def main():
    por_run, por_metrica = carregar_grupo(RESULTS_DIR)

    if not por_run:
        print("Nenhum resultado encontrado.")
        return

    print(f"Total de runs: {len(por_run)}")

    if "meanTravelTime" in por_metrica:
        tt = por_metrica["meanTravelTime"]
        print(f"Tempo médio de viagem: {statistics.mean(tt):.2f}")
        print(f"Mediana: {statistics.median(tt):.2f}")

    # --- CSV de resumo com estatística completa ---
    out_csv = os.path.join(RESULTS_DIR, "resumo.csv")
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Métrica", "Média", "DP", "IC95_low", "IC95_high", "Mediana"])
        for metrica in sorted(por_metrica):
            media, dp, ic_low, ic_high, mediana = estatisticas(por_metrica[metrica])
            if media is None:
                continue
            w.writerow([metrica, media, dp, ic_low, ic_high, mediana])
    print(f"Resumo escrito em {out_csv}")

    # --- Comparação ComRSU vs SemRSU, se ambos os grupos existirem ---
    _, grupo_com = carregar_grupo(RESULTS_COMRSU_DIR)
    _, grupo_sem = carregar_grupo(RESULTS_SEMRSU_DIR)

    if grupo_com and grupo_sem:
        comparacoes = comparar(grupo_com, grupo_sem)
        cmp_csv = os.path.join(RESULTS_DIR, "comparacao_rsu.csv")
        with open(cmp_csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow([
                "Métrica", "n_ComRSU", "n_SemRSU", "Média_ComRSU", "Média_SemRSU",
                "Welch_t", "Welch_p", "MannWhitney_U", "MannWhitney_p", "Método",
            ])
            for linha in comparacoes:
                w.writerow([
                    linha["metrica"], linha["n_com"], linha["n_sem"],
                    linha["media_com"], linha["media_sem"],
                    linha["welch_t"], linha["welch_p"],
                    linha["mannwhitney_u"], linha["mannwhitney_p"],
                    linha["metodo"],
                ])
        metodo = "scipy" if _TEM_SCIPY else "Welch manual (p aproximado)"
        print(f"Comparação ComRSU vs SemRSU escrita em {cmp_csv} (método: {metodo})")
    else:
        print(
            "Comparação ComRSU vs SemRSU ignorada: "
            "não existem ambos os grupos (results_comrsu/ e results_semrsu/)."
        )


if __name__ == "__main__":
    main()
