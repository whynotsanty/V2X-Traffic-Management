"""
Dashboard de análise pós-run da pipeline de testes V2X (Eclipse MOSAIC + SUMO).

Comparação COM RSU vs SEM RSU em 2 cenários de volume e 4 testes de cooperação.
Autoria: Gonçalo Ferreira, Gustavo Castro, Matilde Oliveira
Mestrado EI - Novos Paradigmas de Rede.
"""

import math
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------- #
# Configuração da página
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Dashboard V2X - MOSAIC/SUMO",
    layout="wide",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTADOS_CSV = os.path.join(BASE_DIR, "Resultados_Pipeline.csv")
SIGNIFICANCIA_CSV = os.path.join(BASE_DIR, "Significancia_Pipeline.csv")

# Cores consistentes para COM vs SEM RSU
COR_COM = "#d62728"   # vermelho -> RSU (que degrada)
COR_SEM = "#1f77b4"   # azul -> baseline

# Rótulos descritivos dos testes de cooperação
DESC_TESTES = {
    1: "T1 - 60% não-coop / 40% pouco-coop",
    2: "T2 - 25% de cada perfil",
    3: "T3 - 50% coop / 50% padrão",
    4: "T4 - 100% cooperativo",
}

# Rótulos amigáveis para as métricas
ROTULOS_METRICAS = {
    "tempoMedioViagem_real": "Tempo médio de viagem (s)",
    "tempoViagem_P95_real": "Tempo de viagem P95 (s)",
    "throughput_vps": "Throughput (veíc./s)",
    "throughput_total": "Throughput total (veíc.)",
    "velMediaGargalo_kmh": "Velocidade média no gargalo (km/h)",
    "comprimentoMaxFila_m": "Comprimento máx. de fila (m)",
    "duracaoFila_s": "Duração da fila (s)",
    "co2Medio_real_g": "CO2 médio (g)",
    "combustivelMedio_real_ml": "Combustível médio (ml)",
    "suppressionRatio": "Rácio de supressão",
    "totalDenmsReceived": "DENMs recebidas (total)",
    "totalCamsReceived": "CAMs recebidas (total)",
    "totalRetransmissions": "Retransmissões (total)",
    "totalSuppressions": "Supressões (total)",
    "stoppedVehicles": "Veículos parados",
}


def rotulo_metrica(m: str) -> str:
    return ROTULOS_METRICAS.get(m, m)


# --------------------------------------------------------------------------- #
# Leitura de dados (com cache)
# --------------------------------------------------------------------------- #
@st.cache_data
def carregar_csv(caminho: str) -> pd.DataFrame:
    return pd.read_csv(caminho)


def aviso_csv_em_falta(nome: str) -> None:
    st.warning(
        f"Ficheiro **{nome}** não encontrado. "
        "Gera os resultados primeiro com `python3 compilar_pipeline.py`."
    )


# --------------------------------------------------------------------------- #
# Funções auxiliares de gráfico
# --------------------------------------------------------------------------- #
def _serie_por_teste(df: pd.DataFrame, metrica: str, rsu: str):
    """Devolve (testes, medias, err_low, err_high) ordenados por teste."""
    sub = df[(df["metrica"] == metrica) & (df["rsu"] == rsu)].sort_values("teste")
    testes = [DESC_TESTES.get(int(t), f"T{int(t)}") for t in sub["teste"]]
    media = sub["Media"].tolist()
    low = (sub["Media"] - sub["IC95_low"]).clip(lower=0).tolist()
    high = (sub["IC95_high"] - sub["Media"]).clip(lower=0).tolist()
    return testes, media, low, high


def grafico_com_vs_sem(df: pd.DataFrame, metrica: str, titulo: str, eixo_y: str):
    """Barras agrupadas COM vs SEM RSU por teste, com barras de erro IC95."""
    fig = go.Figure()
    for rsu, cor, nome in (("sem", COR_SEM, "SEM RSU"), ("com", COR_COM, "COM RSU")):
        testes, media, low, high = _serie_por_teste(df, metrica, rsu)
        if not media:
            continue
        fig.add_trace(
            go.Bar(
                name=nome,
                x=testes,
                y=media,
                marker_color=cor,
                error_y=dict(type="data", symmetric=False, array=high, arrayminus=low),
            )
        )
    fig.update_layout(
        title=titulo,
        barmode="group",
        xaxis_title="Teste de cooperação",
        yaxis_title=eixo_y,
        legend_title="Configuração",
        height=420,
    )
    return fig


def grafico_so_com(df: pd.DataFrame, metricas, titulo: str, eixo_y: str):
    """Barras agrupadas por métrica (apenas COM RSU) por teste, com IC95."""
    fig = go.Figure()
    paleta = ["#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]
    for i, metrica in enumerate(metricas):
        testes, media, low, high = _serie_por_teste(df, metrica, "com")
        if not media:
            continue
        fig.add_trace(
            go.Bar(
                name=rotulo_metrica(metrica),
                x=testes,
                y=media,
                marker_color=paleta[i % len(paleta)],
                error_y=dict(type="data", symmetric=False, array=high, arrayminus=low),
            )
        )
    fig.update_layout(
        title=titulo,
        barmode="group",
        xaxis_title="Teste de cooperação",
        yaxis_title=eixo_y,
        legend_title="Métrica",
        height=420,
    )
    return fig


def valor_medio(df: pd.DataFrame, metrica: str, rsu: str):
    """Média da métrica (sobre todos os testes) para um dado rsu. None se vazio."""
    sub = df[(df["metrica"] == metrica) & (df["rsu"] == rsu)]
    if sub.empty:
        return None
    return float(sub["Media"].mean())


# --------------------------------------------------------------------------- #
# Cabeçalho
# --------------------------------------------------------------------------- #
st.title("Análise pós-run da pipeline V2X (Eclipse MOSAIC + SUMO)")
st.caption(
    "Comparação COM RSU vs SEM RSU em 2 cenários de volume e 4 testes de cooperação. "
    "Intervalos de confiança a 95% (IC95) representados como barras de erro."
)

# --------------------------------------------------------------------------- #
# Verificação de ficheiros
# --------------------------------------------------------------------------- #
faltam = []
if not os.path.exists(RESULTADOS_CSV):
    aviso_csv_em_falta("Resultados_Pipeline.csv")
    faltam.append("Resultados_Pipeline.csv")

tem_sig = os.path.exists(SIGNIFICANCIA_CSV)
if not tem_sig:
    aviso_csv_em_falta("Significancia_Pipeline.csv")

if faltam:
    st.stop()

df = carregar_csv(RESULTADOS_CSV)
df_sig = carregar_csv(SIGNIFICANCIA_CSV) if tem_sig else None

# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("Filtros")
    cenarios_disp = sorted(df["cenario"].unique())
    cenario = st.selectbox(
        "Cenário de volume",
        cenarios_disp,
        format_func=lambda c: (
            "1 - 1800 + 1800 veíc." if int(c) == 1 else "2 - 3600 + 1800 veíc."
        ),
    )

    metricas_disp = sorted(df["metrica"].unique())
    metrica_livre = st.selectbox(
        "Métrica (exploração livre)",
        metricas_disp,
        index=metricas_disp.index("tempoMedioViagem_real")
        if "tempoMedioViagem_real" in metricas_disp
        else 0,
        format_func=rotulo_metrica,
    )

    st.divider()
    st.subheader("Autoria")
    st.markdown(
        "**Gonçalo Ferreira**  \n**Gustavo Castro**  \n**Matilde Oliveira**\n\n"
        "Mestrado em Engenharia Informática  \n"
        "Novos Paradigmas de Rede"
    )
    for img in ("goncalo.png", "gustavo.png", "matilde.png"):
        caminho_img = os.path.join(BASE_DIR, img)
        if os.path.exists(caminho_img):
            try:
                st.image(caminho_img, width=120)
            except Exception:
                pass

# Subconjunto do cenário escolhido
df_c = df[df["cenario"] == cenario].copy()

# --------------------------------------------------------------------------- #
# KPIs de topo (média entre testes, COM vs SEM RSU)
# --------------------------------------------------------------------------- #
st.subheader(f"Indicadores-chave - Cenário {int(cenario)} (média entre os 4 testes)")


def kpi(coluna, label, metrica, unidade="", menor_melhor=True, casas=1):
    com = valor_medio(df_c, metrica, "com")
    sem = valor_medio(df_c, metrica, "sem")
    if com is None or sem is None:
        coluna.metric(label, "n/d")
        return
    valor = f"{com:.{casas}f}{unidade}"
    delta = com - sem
    # delta positivo = COM RSU maior que SEM. Com menor_melhor, maior é pior.
    coluna.metric(
        label + " (COM RSU)",
        valor,
        delta=f"{delta:+.{casas}f}{unidade} vs SEM",
        delta_color="inverse" if menor_melhor else "normal",
    )


c1, c2, c3, c4 = st.columns(4)
kpi(c1, "Tempo médio viagem", "tempoMedioViagem_real", " s", menor_melhor=True)
kpi(c2, "Tempo viagem P95", "tempoViagem_P95_real", " s", menor_melhor=True)
kpi(c3, "Throughput", "throughput_vps", " v/s", menor_melhor=False, casas=2)
kpi(c4, "CO2 médio", "co2Medio_real_g", " g", menor_melhor=True)

st.caption(
    "Delta = (COM RSU - SEM RSU). Onde menor é melhor (tempo, CO2), verde indica "
    "melhoria; aqui a RSU tende a piorar estes indicadores."
)

st.divider()

# --------------------------------------------------------------------------- #
# Gráficos de desempenho de tráfego
# --------------------------------------------------------------------------- #
st.subheader("Desempenho de tráfego - COM vs SEM RSU")

g1, g2 = st.columns(2)
with g1:
    st.plotly_chart(
        grafico_com_vs_sem(
            df_c, "tempoMedioViagem_real",
            "Tempo médio de viagem por teste", "Tempo (s)",
        ),
        use_container_width=True,
    )
with g2:
    st.plotly_chart(
        grafico_com_vs_sem(
            df_c, "throughput_vps",
            "Throughput por teste", "Veíc./s",
        ),
        use_container_width=True,
    )

g3, g4 = st.columns(2)
with g3:
    st.plotly_chart(
        grafico_com_vs_sem(
            df_c, "velMediaGargalo_kmh",
            "Velocidade média no gargalo por teste", "km/h",
        ),
        use_container_width=True,
    )
with g4:
    st.plotly_chart(
        grafico_com_vs_sem(
            df_c, "co2Medio_real_g",
            "CO2 médio por teste", "CO2 (g)",
        ),
        use_container_width=True,
    )

st.plotly_chart(
    grafico_com_vs_sem(
        df_c, "combustivelMedio_real_ml",
        "Combustível médio por teste", "Combustível (ml)",
    ),
    use_container_width=True,
)

st.divider()

# --------------------------------------------------------------------------- #
# Métricas V2X (apenas COM RSU)
# --------------------------------------------------------------------------- #
st.subheader("Métricas V2X (apenas COM RSU)")
st.caption(
    "Estas métricas só existem na configuração COM RSU (mensagens CAM/DENM, "
    "supressão e atividade V2X)."
)

metricas_existentes = set(df_c["metrica"].unique())


def primeiras_disponiveis(*candidatas):
    return [m for m in candidatas if m in metricas_existentes]


v1, v2 = st.columns(2)
with v1:
    st.plotly_chart(
        grafico_so_com(
            df_c, ["suppressionRatio"],
            "Rácio de supressão por teste", "Rácio",
        ),
        use_container_width=True,
    )
with v2:
    msgs = primeiras_disponiveis("totalDenmsReceived", "totalCamsReceived")
    st.plotly_chart(
        grafico_so_com(
            df_c, msgs,
            "Mensagens recebidas por teste", "Total",
        ),
        use_container_width=True,
    )

# Retransmissões vs supressões (esquema legado). Se ausentes, usa o esquema
# atual disponível (alertas despoletados / total de mensagens V2X).
ret_sup = primeiras_disponiveis("totalRetransmissions", "totalSuppressions")
if ret_sup:
    st.plotly_chart(
        grafico_so_com(
            df_c, ret_sup,
            "Retransmissões vs Supressões por teste", "Total",
        ),
        use_container_width=True,
    )
else:
    alt = primeiras_disponiveis("totalAlertsTriggered", "totalV2xMessages")
    if alt:
        st.plotly_chart(
            grafico_so_com(
                df_c, alt,
                "Atividade V2X por teste (alertas / mensagens)", "Total",
            ),
            use_container_width=True,
        )
        st.caption(
            "Nota: totalRetransmissions/totalSuppressions não estão presentes "
            "neste conjunto de dados; é apresentada a atividade V2X disponível "
            "(alertas despoletados e total de mensagens V2X)."
        )

st.divider()

# --------------------------------------------------------------------------- #
# Exploração livre da métrica escolhida
# --------------------------------------------------------------------------- #
st.subheader(f"Exploração livre: {rotulo_metrica(metrica_livre)}")
existe_sem = not df_c[
    (df_c["metrica"] == metrica_livre) & (df_c["rsu"] == "sem")
].empty
if existe_sem:
    fig_livre = grafico_com_vs_sem(
        df_c, metrica_livre,
        f"{rotulo_metrica(metrica_livre)} por teste",
        rotulo_metrica(metrica_livre),
    )
else:
    fig_livre = grafico_so_com(
        df_c, [metrica_livre],
        f"{rotulo_metrica(metrica_livre)} por teste (só COM RSU)",
        rotulo_metrica(metrica_livre),
    )
st.plotly_chart(fig_livre, use_container_width=True)

st.divider()

# --------------------------------------------------------------------------- #
# Tabela de significância estatística
# --------------------------------------------------------------------------- #
st.subheader(f"Significância estatística - Cenário {int(cenario)}")

if df_sig is None:
    aviso_csv_em_falta("Significancia_Pipeline.csv")
else:
    sig_c = df_sig[df_sig["cenario"] == cenario].copy()
    if sig_c.empty:
        st.info("Sem dados de significância para este cenário.")
    else:
        def marcar(p):
            try:
                pv = float(p)
            except (TypeError, ValueError):
                return "—"
            if math.isnan(pv) or math.isinf(pv):
                return "—"
            return "✅" if pv < 0.05 else "—"

        sig_c["significativo? (p<0.05)"] = sig_c["welch_p"].apply(marcar)
        sig_c["metrica"] = sig_c["metrica"].apply(rotulo_metrica)
        sig_c["teste"] = sig_c["teste"].apply(
            lambda t: DESC_TESTES.get(int(t), f"T{int(t)}")
        )

        # Formatação numérica graciosa (mantém inf/nan legíveis)
        def fmt(x):
            try:
                v = float(x)
            except (TypeError, ValueError):
                return x
            if math.isnan(v):
                return "—"
            if math.isinf(v):
                return "inf"
            return round(v, 4)

        for col in ("media_com", "media_sem", "welch_t", "welch_p", "mannwhitney_p"):
            if col in sig_c.columns:
                sig_c[col] = sig_c[col].apply(fmt)

        colunas = [
            "teste", "metrica", "n_com", "n_sem",
            "media_com", "media_sem", "welch_t", "welch_p",
            "mannwhitney_p", "significativo? (p<0.05)",
        ]
        colunas = [c for c in colunas if c in sig_c.columns]
        st.dataframe(
            sig_c[colunas].sort_values(["teste", "metrica"]),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "✅ indica diferença estatisticamente significativa entre COM e SEM RSU "
            "(teste de Welch, p < 0.05). Valores de p indefinidos são apresentados como '—'."
        )

st.divider()

# --------------------------------------------------------------------------- #
# Conclusão
# --------------------------------------------------------------------------- #
st.subheader("Conclusão")
st.info(
    "**A RSU não melhora o desempenho neste estudo - degrada-o.**\n\n"
    "Em ambos os cenários de volume, a configuração **COM RSU** apresenta tempos de "
    "viagem (médio e P95) mais elevados e menor throughput do que a configuração "
    "**SEM RSU**, acompanhados de maior consumo de combustível e mais emissões de CO2. "
    "Os testes de significância (Welch) confirmam que muitas destas diferenças são "
    "estatisticamente significativas (p < 0.05).\n\n"
    "**Efeito-dose:** quanto maior o grau de cooperação imposto (de T1 para T4, até "
    "100% cooperativo), pior se torna o desempenho na presença da RSU. Ou seja, "
    "aumentar a cooperação coordenada pela RSU agrava o congestionamento em vez de o "
    "aliviar. A leitura honesta é que, na configuração testada, a coordenação V2X via "
    "RSU introduz sobrecarga (supressões/retransmissões e manobras coordenadas) que se "
    "traduz numa penalização de desempenho de tráfego, em vez de um benefício."
)
