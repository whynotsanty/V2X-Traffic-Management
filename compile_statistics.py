#!/usr/bin/env python3
"""
Calcula média e mediana das métricas de todas as 30 runs
Gera: Métricas_Finais.csv
"""

import json
from pathlib import Path
from statistics import mean, median, stdev

def extract_metrics(run_number):
    """Extrai métricas de uma run"""
    metrics_file = Path(f"/home/netsim/tpnpr/results/run_{run_number}/metrics_sumo_{run_number}.json")
    
    if not metrics_file.exists():
        return None
    
    try:
        with open(metrics_file, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"⚠️ Erro ao ler run_{run_number}: {e}")
        return None


def compile_statistics():
    """Compila estatísticas de todas as runs"""
    print("📊 Compilando estatísticas de 30 runs...\n")
    
    all_metrics = {
        'trip_time_avg': [],
        'trip_time_p50': [],
        'trip_time_p95': [],
        'waiting_time_avg': [],
        'queue_max_m': [],
        'queue_duration_s': [],
        'throughput': [],
        'speed_bottleneck': [],
        'v2x_messages': [],
        'v2x_efficiency': [],
        'co2_avg': [],
        'fuel_avg': [],
    }
    
    valid_runs = 0
    
    for run_num in range(1, 31):
        metrics = extract_metrics(run_num)
        if metrics is None:
            continue
        
        valid_runs += 1
        
        try:
            # Viagens
            if 'trips' in metrics:
                t = metrics['trips']
                all_metrics['trip_time_avg'].append(t['avg_trip_time_s'])
                all_metrics['trip_time_p50'].append(t['p50_trip_time_s'])
                all_metrics['trip_time_p95'].append(t['p95_trip_time_s'])
                all_metrics['waiting_time_avg'].append(t['avg_waiting_time_s'])
                all_metrics['co2_avg'].append(t['avg_co2_g'])
                all_metrics['fuel_avg'].append(t['avg_fuel_ml'])
            
            # Fila
            if 'queue' in metrics:
                q = metrics['queue']
                all_metrics['queue_max_m'].append(q['max_queue_length_m'])
                all_metrics['queue_duration_s'].append(q['queue_duration_s'])
            
            # Gargalo
            if 'bottleneck' in metrics:
                b = metrics['bottleneck']
                all_metrics['throughput'].append(b['throughput_vehicles_per_s'])
                all_metrics['speed_bottleneck'].append(b['avg_speed_bottleneck_kmh'])
            
            # V2X
            if 'v2x_summary' in metrics:
                v = metrics['v2x_summary']
                all_metrics['v2x_messages'].append(v['total_messages'])
                all_metrics['v2x_efficiency'].append(v['dissemination_efficiency'])
            
            print(f"  ✓ Run {run_num:2d} processada")
        except Exception as e:
            print(f"  ❌ Run {run_num:2d}: {e}")
            valid_runs -= 1
    
    print(f"\n✓ {valid_runs} runs válidas processadas\n")
    
    # Calcular estatísticas
    results = {
        'runs_validas': valid_runs,
        'trip_time_avg_mean': round(mean(all_metrics['trip_time_avg']), 2) if all_metrics['trip_time_avg'] else 0,
        'trip_time_avg_median': round(median(all_metrics['trip_time_avg']), 2) if all_metrics['trip_time_avg'] else 0,
        'trip_time_p50_mean': round(mean(all_metrics['trip_time_p50']), 2) if all_metrics['trip_time_p50'] else 0,
        'trip_time_p50_median': round(median(all_metrics['trip_time_p50']), 2) if all_metrics['trip_time_p50'] else 0,
        'trip_time_p95_mean': round(mean(all_metrics['trip_time_p95']), 2) if all_metrics['trip_time_p95'] else 0,
        'trip_time_p95_median': round(median(all_metrics['trip_time_p95']), 2) if all_metrics['trip_time_p95'] else 0,
        'waiting_time_avg_mean': round(mean(all_metrics['waiting_time_avg']), 2) if all_metrics['waiting_time_avg'] else 0,
        'waiting_time_avg_median': round(median(all_metrics['waiting_time_avg']), 2) if all_metrics['waiting_time_avg'] else 0,
        'queue_max_m_mean': round(mean(all_metrics['queue_max_m']), 2) if all_metrics['queue_max_m'] else 0,
        'queue_max_m_median': round(median(all_metrics['queue_max_m']), 2) if all_metrics['queue_max_m'] else 0,
        'queue_duration_s_mean': round(mean(all_metrics['queue_duration_s']), 0) if all_metrics['queue_duration_s'] else 0,
        'queue_duration_s_median': round(median(all_metrics['queue_duration_s']), 0) if all_metrics['queue_duration_s'] else 0,
        'throughput_mean': round(mean(all_metrics['throughput']), 3) if all_metrics['throughput'] else 0,
        'throughput_median': round(median(all_metrics['throughput']), 3) if all_metrics['throughput'] else 0,
        'speed_bottleneck_mean': round(mean(all_metrics['speed_bottleneck']), 2) if all_metrics['speed_bottleneck'] else 0,
        'speed_bottleneck_median': round(median(all_metrics['speed_bottleneck']), 2) if all_metrics['speed_bottleneck'] else 0,
        'v2x_messages_mean': round(mean(all_metrics['v2x_messages']), 0) if all_metrics['v2x_messages'] else 0,
        'v2x_messages_median': round(median(all_metrics['v2x_messages']), 0) if all_metrics['v2x_messages'] else 0,
        'v2x_efficiency_mean': round(mean(all_metrics['v2x_efficiency']), 2) if all_metrics['v2x_efficiency'] else 0,
        'v2x_efficiency_median': round(median(all_metrics['v2x_efficiency']), 2) if all_metrics['v2x_efficiency'] else 0,
        'co2_avg_mean': round(mean(all_metrics['co2_avg']), 2) if all_metrics['co2_avg'] else 0,
        'co2_avg_median': round(median(all_metrics['co2_avg']), 2) if all_metrics['co2_avg'] else 0,
        'fuel_avg_mean': round(mean(all_metrics['fuel_avg']), 2) if all_metrics['fuel_avg'] else 0,
        'fuel_avg_median': round(median(all_metrics['fuel_avg']), 2) if all_metrics['fuel_avg'] else 0,
    }
    
    return results


def save_csv(results):
    """Salva resultados em CSV"""
    csv_path = Path("/home/netsim/tpnpr/Metricas_Finais.csv")
    
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write("Métrica,Média,Mediana,Unidade\n")
        f.write(f"Runs Válidas,{results['runs_validas']},N/A,número\n")
        f.write("\n=== TEMPO DE VIAGEM ===\n")
        f.write(f"Tempo Médio de Viagem,{results['trip_time_avg_mean']},{results['trip_time_avg_median']},s\n")
        f.write(f"P50 (Mediana) Tempo de Viagem,{results['trip_time_p50_mean']},{results['trip_time_p50_median']},s\n")
        f.write(f"P95 Tempo de Viagem,{results['trip_time_p95_mean']},{results['trip_time_p95_median']},s\n")
        f.write("\n=== TEMPO DE ESPERA ===\n")
        f.write(f"Tempo Médio de Espera,{results['waiting_time_avg_mean']},{results['waiting_time_avg_median']},s\n")
        f.write("\n=== FILA ===\n")
        f.write(f"Comprimento Máximo da Fila,{results['queue_max_m_mean']},{results['queue_max_m_median']},m\n")
        f.write(f"Duração da Fila,{results['queue_duration_s_mean']},{results['queue_duration_s_median']},s\n")
        f.write("\n=== GARGALO (-E17) ===\n")
        f.write(f"Throughput,{results['throughput_mean']},{results['throughput_median']},veículos/s\n")
        f.write(f"Velocidade Média,{results['speed_bottleneck_mean']},{results['speed_bottleneck_median']},km/h\n")
        f.write("\n=== V2X (COMUNICAÇÃO VEICULAR) ===\n")
        f.write(f"Mensagens V2X Total,{results['v2x_messages_mean']},{results['v2x_messages_median']},número\n")
        f.write(f"Eficiência de Disseminação,{results['v2x_efficiency_mean']},{results['v2x_efficiency_median']},taxa\n")
        f.write("\n=== EMISSÕES ===\n")
        f.write(f"CO2 Médio,{results['co2_avg_mean']},{results['co2_avg_median']},g\n")
        f.write(f"Combustível Médio,{results['fuel_avg_mean']},{results['fuel_avg_median']},ml\n")
    
    print(f"✅ CSV salvo: {csv_path}\n")
    
    # Imprimir tabela
    print("="*70)
    print("ESTATÍSTICAS FINAIS (30 RUNS)")
    print("="*70)
    print(f"\nRuns Válidas: {results['runs_validas']}\n")
    
    print("TEMPO DE VIAGEM:")
    print(f"  • Tempo médio: {results['trip_time_avg_mean']}s (med: {results['trip_time_avg_median']}s)")
    print(f"  • P50: {results['trip_time_p50_mean']}s (med: {results['trip_time_p50_median']}s)")
    print(f"  • P95: {results['trip_time_p95_mean']}s (med: {results['trip_time_p95_median']}s)")
    
    print("\nTEMPO DE ESPERA:")
    print(f"  • Tempo médio: {results['waiting_time_avg_mean']}s (med: {results['waiting_time_avg_median']}s)")
    
    print("\nFILA (Gargalo -E17):")
    print(f"  • Máxima: {results['queue_max_m_mean']}m (med: {results['queue_max_m_median']}m)")
    print(f"  • Duração: {results['queue_duration_s_mean']}s (med: {results['queue_duration_s_median']}s)")
    
    print("\nGARGALO:")
    print(f"  • Throughput: {results['throughput_mean']} veíc/s (med: {results['throughput_median']} veíc/s)")
    print(f"  • Velocidade: {results['speed_bottleneck_mean']} km/h (med: {results['speed_bottleneck_median']} km/h)")
    
    print("\nV2X:")
    print(f"  • Mensagens: {results['v2x_messages_mean']} (med: {results['v2x_messages_median']})")
    print(f"  • Eficiência: {results['v2x_efficiency_mean']} (med: {results['v2x_efficiency_median']})")
    
    print("\nEMISSÕES:")
    print(f"  • CO2: {results['co2_avg_mean']}g (med: {results['co2_avg_median']}g)")
    print(f"  • Combustível: {results['fuel_avg_mean']}ml (med: {results['fuel_avg_median']}ml)")
    print("\n" + "="*70)


if __name__ == "__main__":
    results = compile_statistics()
    if results:
        save_csv(results)
