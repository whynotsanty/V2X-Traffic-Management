import streamlit as st
import pandas as pd
import os
import json
import matplotlib.pyplot as plt

st.set_page_config(page_title="V2X Dashboard", layout="wide")

st.title("Dashboard de Resultados V2X — Manhattan")
st.caption("Trabalho NPR — Simulação V2X com Eclipse MOSAIC + SUMO")

RESULTS_DIR = "/home/netsim/opt/tpnpr/results"
RESUMO_CSV = os.path.join(RESULTS_DIR, "resumo.csv")


def carregar_runs():
    runs = []
    if not os.path.exists(RESULTS_DIR):
        return runs
    for nome in sorted(os.listdir(RESULTS_DIR)):
        if nome.startswith("run_"):
            caminho = os.path.join(RESULTS_DIR, nome, "metrics_wrapper.json")
            if os.path.exists(caminho):
                with open(caminho, "r") as f:
                    runs.append(json.load(f))
    return runs


def carregar_resumo():
    """Lê o resumo.csv produzido por compilar_resultados.py (com DP/IC95)."""
    if os.path.exists(RESUMO_CSV):
        try:
            return pd.read_csv(RESUMO_CSV)
        except Exception:
            return None
    return None


def main():
    runs = carregar_runs()
    if not runs:
        st.warning("Nenhum resultado encontrado em results/.")
        return

    st.subheader("Resumo das Métricas")

    # Tabela por run — usa o novo esquema v2x (suppressionRatio / retransmissions / suppressions)
    trip_data = []
    for i, r in enumerate(runs):
        trips = r.get("trips", {})
        v2x = r.get("v2x", {})
        trip_data.append({
            "Run": i + 1,
            "MeanTravelTime": trips.get("meanTravelTime"),
            "QueueLength": r.get("queue", {}).get("maxQueueLength"),
            "SuppressionRatio": v2x.get("suppressionRatio"),
            "Retransmissions": v2x.get("totalRetransmissions"),
            "Suppressions": v2x.get("totalSuppressions"),
        })

    df = pd.DataFrame(trip_data)
    st.dataframe(df)

    # Gráfico de barras: tempo médio de viagem por run
    st.subheader("Tempo Médio de Viagem por Run")
    fig, ax = plt.subplots()
    ax.bar(df["Run"].astype(str), df["MeanTravelTime"])
    ax.set_xlabel("Run")
    ax.set_ylabel("Tempo (s)")
    st.pyplot(fig)

    # Gráfico V2X: rácio de supressão por run
    st.subheader("Rácio de Supressão V2X (suppressionRatio)")
    fig2, ax2 = plt.subplots()
    ax2.bar(df["Run"].astype(str), df["SuppressionRatio"])
    ax2.set_xlabel("Run")
    ax2.set_ylabel("Suppression Ratio")
    st.pyplot(fig2)

    # Gráfico V2X: retransmissões vs supressões por run
    st.subheader("Retransmissões vs Supressões V2X")
    fig3, ax3 = plt.subplots()
    ax3.bar(df["Run"].astype(str), df["Retransmissions"], label="Retransmissões")
    ax3.bar(df["Run"].astype(str), df["Suppressions"], label="Supressões", alpha=0.6)
    ax3.set_xlabel("Run")
    ax3.set_ylabel("Contagem")
    ax3.legend()
    st.pyplot(fig3)

    # --- Resumo agregado com barras de erro (IC95) a partir do resumo.csv ---
    resumo = carregar_resumo()
    if resumo is not None and not resumo.empty:
        st.subheader("Médias Agregadas com Intervalo de Confiança 95%")
        st.dataframe(resumo)

        col_metrica = resumo.columns[0]
        if {"Média", "IC95_low", "IC95_high"}.issubset(resumo.columns):
            res = resumo.dropna(subset=["Média"]).copy()
            if not res.empty:
                # Erro simétrico para a barra: distância da média ao limite IC95
                yerr = (res["IC95_high"] - res["IC95_low"]) / 2.0
                fig4, ax4 = plt.subplots(figsize=(10, 5))
                ax4.bar(
                    res[col_metrica].astype(str),
                    res["Média"],
                    yerr=yerr,
                    capsize=4,
                )
                ax4.set_xlabel("Métrica")
                ax4.set_ylabel("Média (± IC95)")
                plt.setp(ax4.get_xticklabels(), rotation=45, ha="right")
                fig4.tight_layout()
                st.pyplot(fig4)
    else:
        st.info(
            "resumo.csv não encontrado — corre compilar_resultados.py "
            "para gerar as estatísticas agregadas (DP/IC95)."
        )

    # Secção de autoria
    st.markdown("---")
    st.markdown("**Autoria:** Trabalho NPR — Grupo V2X")
    st.markdown("Simulação baseada em Eclipse MOSAIC + SUMO")


if __name__ == "__main__":
    main()

# Nota: a métrica V2X passou de disseminationEfficiency (legado) para
# suppressionRatio / totalRetransmissions / totalSuppressions (novo esquema).
