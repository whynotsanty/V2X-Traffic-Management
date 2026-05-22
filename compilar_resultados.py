#!/usr/bin/env python3
import json
import csv
from pathlib import Path
from statistics import mean, median

def compile():
    base_dir = Path("/home/netsim/tpnpr/results")
    dados_totais = []

    print("A compilar as 30 runs...")

    for i in range(1, 31):
        file_path = base_dir / f"run_{i}" / "metrics_wrapper.json"
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    dados_totais.append(json.load(f))
            except json.JSONDecodeError:
                print(f"Run {i} tem um problema com JSON.")
        else:
            print(f"Run {i} não encontrada.")

    if not dados_totais:
        print("Nenhum dado encontrado para processar.")
        return

    # Listas para guardar os valores de cada run
    metrics = {
        "Trip_Time_Avg": [], "P50": [], "P95": [],
        "Queue_Max_M": [], "Queue_Duration_S": [],
        "Throughput": [], "V2X_Efficiency": [],
        "CO2_Avg": [], "Fuel_Avg": [], "Speed_Bottleneck": []
    }

    # Extração dos dados
    for d in dados_totais:
        try:
            # Tripmetrics
            t = d.get('trips', {})
            metrics["Trip_Time_Avg"].append(t.get('avg_trip_time_s', 0))
            metrics["P50"].append(t.get('percentile_50_s', 0))
            metrics["P95"].append(t.get('percentile_95_s', 0))
            metrics["CO2_Avg"].append(t.get('avg_co2_g', 0))
            metrics["Fuel_Avg"].append(t.get('avg_fuel_ml', 0))
            
            # Queue
            q = d.get('queue', {})
            metrics["Queue_Max_M"].append(q.get('max_queue_length_m', 0))
            metrics["Queue_Duration_S"].append(q.get('queue_duration_s', 0))
            
            # Throughput
            th = d.get('throughput', {})
            metrics["Throughput"].append(th.get('avg_throughput_vps', 0))
            
            # V2X
            v = d.get('v2x', {})
            metrics["V2X_Efficiency"].append(v.get('disseminationEfficiency', 0))
            
            # Bottleneck
            b = d.get('bottleneck', {})
            metrics["Speed_Bottleneck"].append(b.get('avg_speed_kmh', 0))
        except Exception as e:
            print(f"Erro ao processar um objeto de dados: {e}")

    # Criação do CSV
    csv_path = Path("/home/netsim/tpnpr/Resultados_Finais_30_Runs.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Métrica", "Média", "Mediana"])
        
        for key, values in metrics.items():
            if values:
                writer.writerow([key, round(mean(values), 3), round(median(values), 3)])

    print(f"Run realizada com sucesso! Estatísticas guardadas em {csv_path}")

if __name__ == "__main__":
    compile()