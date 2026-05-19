#!/usr/bin/env python3
"""
Agregador de Métricas SUMO + MOSAIC
Processa: tripinfo.xml, netstate.xml (fila em -E17), bottleneck_detector.xml
Saída: metrics_sumo_X.json (métricas SUMO) + metrics_wrapper_X.json (MetricsCollector)
"""

import xml.etree.ElementTree as ET
import json
from pathlib import Path
from statistics import mean, stdev, quantiles

class MetricsAggregator:
    def __init__(self, base_path="/home/netsim/tpnpr"):
        self.base_path = Path(base_path)
        self.metrics = {}
        
    def process_tripinfo(self, filepath):
        """Processa tripinfo.xml para métricas de viagem"""
        print(f"  Processando tripinfo.xml...")
        
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
        except ET.ParseError as e:
            print(f"  ❌ Erro ao parsear tripinfo: {e}")
            return
        
        trips = []
        for tripinfo in root.findall('tripinfo'):
            trip = {
                'duration': float(tripinfo.get('duration')),
                'waitingTime': float(tripinfo.get('waitingTime')),
                'routeLength': float(tripinfo.get('routeLength')),
            }
            emissions = tripinfo.find('emissions')
            if emissions is not None:
                trip['CO2'] = float(emissions.get('CO2_abs', 0))
                trip['fuel'] = float(emissions.get('fuel_abs', 0))
            trips.append(trip)
        
        if not trips:
            print("  ⚠️ Nenhuma viagem encontrada")
            return
        
        durations = [t['duration'] for t in trips]
        waiting_times = [t['waitingTime'] for t in trips]
        co2_emissions = [t.get('CO2', 0) for t in trips]
        fuel_consumption = [t.get('fuel', 0) for t in trips]
        
        # Calcular percentis
        q = quantiles(durations, n=100)
        
        self.metrics['trips'] = {
            'total_vehicles': len(trips),
            'avg_trip_time_s': round(mean(durations), 2),
            'std_trip_time_s': round(stdev(durations) if len(durations) > 1 else 0, 2),
            'min_trip_time_s': round(min(durations), 2),
            'max_trip_time_s': round(max(durations), 2),
            'p25_trip_time_s': round(q[24], 2),
            'p50_trip_time_s': round(q[49], 2),
            'p75_trip_time_s': round(q[74], 2),
            'p95_trip_time_s': round(q[94], 2),
            'avg_waiting_time_s': round(mean(waiting_times), 2),
            'avg_co2_g': round(mean(co2_emissions), 2),
            'total_co2_g': round(sum(co2_emissions), 2),
            'avg_fuel_ml': round(mean(fuel_consumption), 2),
            'total_fuel_ml': round(sum(fuel_consumption), 2),
        }
        
        print(f"  ✓ {len(trips)} viagens processadas")
        
    def process_bottleneck_queue(self, filepath):
        """Processa netstate.xml para fila no gargalo (-E17)"""
        print(f"  Processando netstate.xml para fila e throughput...")
        
        if not filepath.exists():
            print(f"  ⚠️ {filepath} não encontrado")
            return
        
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
        except ET.ParseError as e:
            print(f"  ❌ Erro ao parsear netstate: {e}")
            return
        
        max_queue = 0
        avg_queue_list = []
        vehicle_times = {}  # Track vehicle entry/exit for throughput
        timestamps = []
        
        for timestep in root.findall('timestep'):
            time = float(timestep.get('time', 0))
            timestamps.append(time)
            
            for edge in timestep.findall('edge'):
                if edge.get('id') == '-E17':
                    vehicle_count = len(edge.findall('.//vehicle'))
                    max_queue = max(max_queue, vehicle_count)
                    avg_queue_list.append(vehicle_count)
                    
                    # Track vehicles on lane -E17_1 for throughput
                    for lane in edge.findall('lane'):
                        if lane.get('id') == '-E17_1':
                            for vehicle in lane.findall('vehicle'):
                                vid = vehicle.get('id')
                                if vid not in vehicle_times:
                                    vehicle_times[vid] = {'entry': time}
                                vehicle_times[vid]['exit'] = time
        
        # Queue metrics
        if max_queue > 0:
            max_queue_m = max_queue * 5.0  # 5m por veículo
            avg_queue = mean(avg_queue_list) if avg_queue_list else 0
            
            self.metrics['queue'] = {
                'max_queue_length_m': round(max_queue_m, 2),
                'max_queue_length_vehicles': max_queue,
                'avg_queue_vehicles': round(avg_queue, 2),
                'queue_duration_s': len(avg_queue_list)
            }
            print(f"  ✓ Fila máxima: {max_queue} veículos ({round(max_queue_m, 2)}m)")
        else:
            print(f"  ⚠️ Sem dados de fila em -E17")
        
        # Calculate throughput from vehicle tracking
        if vehicle_times and timestamps:
            total_time = max(timestamps) - min(timestamps)
            vehicle_count = len(vehicle_times)
            
            if total_time > 0:
                throughput = vehicle_count / total_time
                self.metrics['bottleneck'] = {
                    'throughput_vehicles_per_s': round(throughput, 3),
                    'total_vehicles_measured': vehicle_count,
                    'avg_speed_bottleneck_kmh': 0,  # Will be updated if detector works
                    'measurement_duration_s': round(total_time, 2)
                }
                print(f"  ✓ Throughput calculado: {round(throughput, 3)} veíc/s ({vehicle_count} veículos em {round(total_time, 1)}s)")
    
    def process_bottleneck_detector(self, filepath):
        """Processa bottleneck_detector.xml para throughput e velocidade"""
        print(f"  Processando bottleneck_detector.xml...")
        
        if not filepath.exists():
            print(f"  ⚠️ {filepath} não encontrado")
            return
        
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
        except ET.ParseError as e:
            print(f"  ❌ Erro ao parsear detector: {e}")
            return
        
        total_vehicles = 0
        total_time = 0
        speeds = []
        
        for interval in root.findall('interval'):
            vehicles = int(interval.get('nVehEntered', 0))
            begin = float(interval.get('begin', 0))
            end = float(interval.get('end', 0))
            duration = end - begin
            speed = float(interval.get('speed', 0))
            
            total_vehicles += vehicles
            total_time += duration
            if speed > 0:
                speeds.append(speed)
        
        if total_time > 0 and total_vehicles > 0:
            throughput = total_vehicles / total_time
            avg_speed_mps = mean(speeds) if speeds else 0
            
            self.metrics['bottleneck'] = {
                'throughput_vehicles_per_s': round(throughput, 3),
                'total_vehicles_passed': total_vehicles,
                'avg_speed_bottleneck_kmh': round(avg_speed_mps * 3.6, 2),
                'avg_speed_bottleneck_mps': round(avg_speed_mps, 2),
                'measurement_duration_s': round(total_time, 2)
            }
            print(f"  ✓ Throughput: {round(throughput, 3)} veíc/s | Velocidade: {round(avg_speed_mps * 3.6, 2)} km/h")
        else:
            print(f"  ⚠️ Sem dados de detector (tentando netstate...)")
            # Fallback: calcular do netstate.xml
            netstate_file = self.base_path / 'netstate.xml'
            self.process_bottleneck_from_netstate(netstate_file)
    
    def process_bottleneck_from_netstate(self, filepath):
        """Calcula throughput e velocidade do netstate.xml para lane -E17_1"""
        print(f"  Processando bottleneck a partir de netstate.xml...")
        
        if not filepath.exists():
            print(f"  ⚠️ {filepath} não encontrado")
            return
        
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
        except ET.ParseError as e:
            print(f"  ❌ Erro ao parsear netstate: {e}")
            return
        
        vehicles_on_lane = {}  # track vehicles per timestep on lane -E17_1
        vehicle_speeds = []
        
        for timestep in root.findall('timestep'):
            time = float(timestep.get('time', 0))
            vehicles_on_lane[time] = 0
            
            for edge in timestep.findall('edge'):
                if edge.get('id') == '-E17':
                    for lane in edge.findall('lane'):
                        if lane.get('id') == '-E17_1':
                            for vehicle in lane.findall('vehicle'):
                                vehicles_on_lane[time] += 1
                                speed = float(vehicle.get('speed', 0))
                                if speed > 0:
                                    vehicle_speeds.append(speed)
        
        if vehicles_on_lane and vehicle_speeds:
            timesteps = sorted(vehicles_on_lane.keys())
            if len(timesteps) > 1:
                simulation_time = timesteps[-1] - timesteps[0]
                total_vehicles = max(vehicles_on_lane.values())
                throughput = total_vehicles / (simulation_time + 1) if simulation_time > 0 else 0
                avg_speed_mps = mean(vehicle_speeds)
                
                self.metrics['bottleneck'] = {
                    'throughput_vehicles_per_s': round(throughput, 3),
                    'total_vehicles_measured': total_vehicles,
                    'avg_speed_bottleneck_kmh': round(avg_speed_mps * 3.6, 2),
                    'avg_speed_bottleneck_mps': round(avg_speed_mps, 2),
                    'measurement_duration_s': round(simulation_time, 2)
                }
                print(f"  ✓ Throughput (netstate): {round(throughput, 3)} veíc/s | Velocidade: {round(avg_speed_mps * 3.6, 2)} km/h")
            else:
                print(f"  ⚠️ Dados insuficientes no netstate")
        else:
            print(f"  ⚠️ Nenhum veículo na lane -E17_1")
    
    def merge_wrapper_metrics(self, wrapper_file):
        """Merge com métricas do MetricsCollector (wrapper)"""
        if not wrapper_file.exists():
            print(f"  ⚠️ {wrapper_file} não encontrado - pulando V2X e outros")
            return
        
        try:
            with open(wrapper_file, 'r') as f:
                wrapper_data = json.load(f)
            
            # Adicionar métricas do wrapper
            self.metrics['v2x'] = wrapper_data.get('v2x', {})
            self.metrics['v2x_summary'] = {
                'total_messages': wrapper_data.get('v2x', {}).get('totalV2xMessages', 0),
                'dissemination_efficiency': wrapper_data.get('v2x', {}).get('disseminationEfficiency', 0),
                'alerts_triggered': wrapper_data.get('v2x', {}).get('totalAlertsTriggered', 0)
            }
            
            # Adicionar CO2 do wrapper se disponível
            if 'trips' in wrapper_data:
                wrapper_trips = wrapper_data.get('trips', {})
                if 'avg_co2_g' in wrapper_trips:
                    self.metrics['wrapper_emissions'] = {
                        'avg_co2_g': wrapper_trips.get('avg_co2_g', 0),
                        'total_co2_g': wrapper_trips.get('total_co2_g', 0)
                    }
            
            print(f"  ✓ Métricas V2X integradas")
        except Exception as e:
            print(f"  ⚠️ Erro ao processar wrapper: {e}")
    
    def save_report(self, output_file="metrics_sumo.json"):
        """Salva relatório em JSON"""
        output_path = self.base_path / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Relatório salvo: {output_path}")
    
    def print_summary(self):
        """Imprime resumo"""
        print("\n" + "="*70)
        print(" MÉTRICAS FINAIS")
        print("="*70)
        
        if 'trips' in self.metrics:
            t = self.metrics['trips']
            print(f"\n VIAGENS:")
            print(f"  • Total: {t['total_vehicles']} veículos")
            print(f"  • Tempo médio: {t['avg_trip_time_s']}s")
            print(f"  • Percentis: P25={t['p25_trip_time_s']}s | P50={t['p50_trip_time_s']}s | P75={t['p75_trip_time_s']}s | P95={t['p95_trip_time_s']}s")
            print(f"  • Espera: {t['avg_waiting_time_s']}s")
        
        if 'queue' in self.metrics:
            q = self.metrics['queue']
            print(f"\n FILA (Gargalo -E17):")
            print(f"  • Máxima: {q['max_queue_length_m']}m ({q['max_queue_length_vehicles']} veículos)")
            print(f"  • Duração: {q['queue_duration_s']}s")
        
        if 'bottleneck' in self.metrics:
            b = self.metrics['bottleneck']
            print(f"\n GARGALO (-E17):")
            print(f"  • Throughput: {b['throughput_vehicles_per_s']} veíc/s")
            print(f"  • Velocidade: {b['avg_speed_bottleneck_kmh']} km/h")
        
        if 'v2x_summary' in self.metrics:
            v = self.metrics['v2x_summary']
            print(f"\n V2X:")
            print(f"  • Mensagens: {v['total_messages']}")
            print(f"  • Eficiência disseminação: {v['dissemination_efficiency']:.2f}")
            print(f"  • Alertas acionados: {v['alerts_triggered']}")
        
        if 'wrapper_emissions' in self.metrics:
            e = self.metrics['wrapper_emissions']
            print(f"\n EMISSÕES:")
            print(f"  • CO2 médio: {e['avg_co2_g']}g")
            print(f"  • CO2 total: {e['total_co2_g']}g")


def process_run(run_number):
    """Processa uma run única"""
    base_path = Path(f"/home/netsim/tpnpr/results/run_{run_number}")
    
    print(f"\n📊 Processando run_{run_number}...")
    
    aggregator = MetricsAggregator(str(base_path))
    
    # Processar ficheiros
    aggregator.process_tripinfo(base_path / "tripinfo.xml")
    aggregator.process_bottleneck_queue(base_path / "netstate.xml")
    aggregator.process_bottleneck_detector(base_path / "bottleneck_detector.xml")
    
    # Merge com wrapper (MetricsCollector)
    aggregator.merge_wrapper_metrics(base_path / "metrics_wrapper.json")
    
    # Salvar
    aggregator.save_report(f"metrics_sumo_{run_number}.json")
    aggregator.print_summary()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Processar run específica
        try:
            run_num = int(sys.argv[1])
            process_run(run_num)
        except ValueError:
            print(f"❌ Uso: python3 metrics_aggregator.py <run_number>")
            sys.exit(1)
    else:
        print("❌ Uso: python3 metrics_aggregator.py <run_number>")
        sys.exit(1)
