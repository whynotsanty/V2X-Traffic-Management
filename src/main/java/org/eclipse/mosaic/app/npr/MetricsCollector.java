package org.eclipse.mosaic.app.npr;

import java.io.FileWriter;
import java.io.IOException;
import java.util.*;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

/**
 * Recolhe as métricas durante a simulação
 * Output: metrics_from_wrapper.json
 */
public class MetricsCollector {
    
    private static final String OUTPUT_FILE = "/home/netsim/tpnpr/metrics_from_wrapper.json";
    private static final double VEHICLE_LENGTH_M = 5.0;
    
    // Dados de Viagens (Coletados pelos veículos no onShutdown)
    private List<VehicleMetric> vehicleMetrics = new ArrayList<>();
    
    // Dados de Filas (Coletados pela RSU no processEvent)
    private int maxQueueVehicles = 0;
    private List<Integer> queueHistory = new ArrayList<>();
    private List<Double> velocidadesGargalo = new ArrayList<>();
    
    // Dados de V2X (Coletados pela RSU e veículos)
    private int totalCamsReceived = 0;
    private int totalDenmsReceived = 0;
    private int totalAlertsTriggered = 0;
    
    private static MetricsCollector instance;
    
    private MetricsCollector() {}
    
    public static synchronized MetricsCollector getInstance() {
        if (instance == null) {
            instance = new MetricsCollector();
        }
        return instance;
    }
      
    // Regista métrica de uma viagem (chamado pelo NprVehicleApp no onShutdown)
    public synchronized void recordVehicleTrip(String vehicleId, double tripDuration, 
                                               double avgSpeed, double estimatedEmissions,
                                               double estimatedFuel, double routeLength) {
        vehicleMetrics.add(new VehicleMetric(vehicleId, tripDuration, avgSpeed, 
                                            estimatedEmissions, estimatedFuel, routeLength));
    }
    
    // Regista comprimento da fila (chamado pela RSU no processEvent)
    public synchronized void recordQueueLength(int vehicleCount) {
        queueHistory.add(vehicleCount);
        maxQueueVehicles = Math.max(maxQueueVehicles, vehicleCount);
    }
    
    // Regista velocidade no gargalo (chamado pela RSU)
    public synchronized void recordBottleneckSpeed(double speedKmh) {
        if (speedKmh >= 0) {
            velocidadesGargalo.add(speedKmh);
        }
    }
    
    // Regista CAM recebida
    public synchronized void recordCamReceived() {
        totalCamsReceived++;
    }
    
    // Regista DENM recebida
    public synchronized void recordDenmReceived() {
        totalDenmsReceived++;
    }
    
    // Regista alerta de trânsito
    public synchronized void recordAlertTriggered() {
        totalAlertsTriggered++;
    }
    
    // Gera relatório final e escreve em JSON
    public synchronized void generateReport() {
        try {
            // Calcular estatísticas
            Map<String, Object> report = new HashMap<>();
            
            // Trips Metrics
            if (!vehicleMetrics.isEmpty()) {
                report.put("trips", generateTripsMetrics());
            }
            
            // Queue Metrics
            if (!queueHistory.isEmpty()) {
                report.put("queue", generateQueueMetrics());
            }
            
            // Throughput Metrics
            report.put("throughput", generateThroughputMetrics());
            
            // V2X Metrics
            report.put("v2x", generateV2xMetrics());
            
            // Bottleneck Metrics
            if (!velocidadesGargalo.isEmpty()) {
                report.put("bottleneck", generateBottleneckMetrics());
            }
            
            // Escrever JSON
            Gson gson = new GsonBuilder().setPrettyPrinting().create();
            String json = gson.toJson(report);
            
            try (FileWriter writer = new FileWriter(OUTPUT_FILE)) {
                writer.write(json);
                System.out.println("Relatório de métricas gerado com sucesso");
            }
        } catch (IOException e) {
            System.err.println("Erro ao escrever o relatório de métricas");
        }
    }
    
    // Gera estatísticas de viagens
    private Map<String, Object> generateTripsMetrics() {
        Map<String, Object> trips = new HashMap<>();
        
        if (vehicleMetrics.isEmpty()) {
            return trips;
        }
        
        List<Double> durations = new ArrayList<>();
        List<Double> speeds = new ArrayList<>();
        List<Double> co2List = new ArrayList<>();
        List<Double> fuelList = new ArrayList<>();
        
        for (VehicleMetric vm : vehicleMetrics) {
            durations.add(vm.tripDuration);
            speeds.add(vm.avgSpeed);
            co2List.add(vm.co2);
            fuelList.add(vm.fuel);
        }
        
        trips.put("total_vehicles", vehicleMetrics.size());
        trips.put("avg_trip_time_s", round(mean(durations), 2));
        trips.put("std_trip_time_s", round(stdev(durations), 2));
        trips.put("min_trip_time_s", round(min(durations), 2));
        trips.put("max_trip_time_s", round(max(durations), 2));
        
        // Percentis
        trips.put("percentile_25_s", round(percentile(durations, 0.25), 2));
        trips.put("percentile_50_s", round(percentile(durations, 0.50), 2));
        trips.put("percentile_75_s", round(percentile(durations, 0.75), 2));
        trips.put("percentile_90_s", round(percentile(durations, 0.90), 2));
        trips.put("percentile_95_s", round(percentile(durations, 0.95), 2));
        trips.put("percentile_99_s", round(percentile(durations, 0.99), 2));
        
        // Velocidades
        trips.put("avg_speed_kmh", round(mean(speeds), 2));
        trips.put("max_speed_kmh", round(max(speeds), 2));
        
        // Emissões e combustível
        trips.put("avg_co2_g", round(mean(co2List), 2));
        trips.put("total_co2_g", round(sum(co2List), 2));
        trips.put("avg_fuel_ml", round(mean(fuelList), 2));
        trips.put("total_fuel_ml", round(sum(fuelList), 2));
        
        return trips;
    }
    
    // Gera métricas de fila (baseado na monitorização da RSU)
    private Map<String, Object> generateQueueMetrics() {
        Map<String, Object> queue = new HashMap<>();
        
        if (queueHistory.isEmpty()) {
            return queue;
        }
        
        double avgQueue = mean(queueHistory.stream()
                .mapToDouble(Integer::doubleValue).toArray());
        double maxQueueM = maxQueueVehicles * VEHICLE_LENGTH_M;
        
        queue.put("max_queue_length_vehicles", maxQueueVehicles);
        queue.put("max_queue_length_m", round(maxQueueM, 2));
        queue.put("avg_queue_vehicles", round(avgQueue, 2));
        queue.put("queue_duration_s", queueHistory.size());
        queue.put("measurement_unit", "vehicles in bottleneck");
        
        return queue;
    }
    
    // Gera métricas de throughput (baseado nas viagens dos veículos)
    private Map<String, Object> generateThroughputMetrics() {
        Map<String, Object> throughput = new HashMap<>();
        
        int totalVehicles = vehicleMetrics.size();
        double avgDuration = vehicleMetrics.isEmpty() ? 0 : 
            mean(vehicleMetrics.stream()
                .mapToDouble(v -> v.tripDuration).toArray());
        
        double throughputVps = avgDuration > 0 ? totalVehicles / avgDuration : 0;
        
        throughput.put("total_vehicles_passed", totalVehicles);
        throughput.put("avg_throughput_vps", round(throughputVps, 3));
        throughput.put("simulation_duration_s", (int)avgDuration);
        
        return throughput;
    }
    
    // Gera métricas do gargalo (baseado nas velocidades medidas pela RSU)
    private Map<String, Object> generateBottleneckMetrics() {
        Map<String, Object> bottleneck = new HashMap<>();
        
        if (velocidadesGargalo.isEmpty()) {
            return bottleneck;
        }
        
        double[] speeds = velocidadesGargalo.stream()
                .mapToDouble(Double::doubleValue).toArray();
        
        bottleneck.put("avg_speed_kmh", round(mean(speeds), 2));
        bottleneck.put("max_speed_kmh", round(max(speeds), 2));
        bottleneck.put("min_speed_kmh", round(min(speeds), 2));
        bottleneck.put("measurements", velocidadesGargalo.size());
        
        return bottleneck;
    }
    
    // Gera métricas de V2X (baseado nas mensagens CAM/DENM e alertas)
    private Map<String, Object> generateV2xMetrics() {
        Map<String, Object> v2x = new HashMap<>();
        
        v2x.put("totalCamsReceived", totalCamsReceived);
        v2x.put("totalDenmsReceived", totalDenmsReceived);
        v2x.put("totalAlertsTriggered", totalAlertsTriggered);
        v2x.put("totalV2xMessages", totalCamsReceived + totalDenmsReceived);
        v2x.put("disseminationEfficiency", calculateDisseminationEfficiency());
        
        return v2x;
    }
    
    // Calcula a eficiência da disseminação de alertas (quantos alertas foram disparados em relação às mensagens recebidas)
    private double calculateDisseminationEfficiency() {
        int totalMessages = totalCamsReceived + totalDenmsReceived;
        if (totalMessages == 0) return 0;
        
        // Quantos alertas foram disparados em relação às mensagens recebidas
        return round((double)totalAlertsTriggered / totalMessages * 100, 2);
    }
    
    // Funções auxiliares para estatísticas
    
    private double mean(double[] values) {
        if (values.length == 0) return 0;
        double sum = 0;
        for (double v : values) sum += v;
        return sum / values.length;
    }
    
    private double mean(List<Double> values) {
        if (values.isEmpty()) return 0;
        return values.stream().mapToDouble(Double::doubleValue).average().orElse(0);
    }
    
    private double stdev(List<Double> values) {
        if (values.size() <= 1) return 0;
        double avg = mean(values);
        double sumSq = 0;
        for (double v : values) {
            sumSq += (v - avg) * (v - avg);
        }
        return Math.sqrt(sumSq / (values.size() - 1));
    }
    
    private double sum(List<Double> values) {
        return values.stream().mapToDouble(Double::doubleValue).sum();
    }
    
    private double min(List<Double> values) {
        return values.stream().mapToDouble(Double::doubleValue).min().orElse(0);
    }
    
    private double min(double[] values) {
        return Arrays.stream(values).min().orElse(0);
    }
    
    private double max(List<Double> values) {
        return values.stream().mapToDouble(Double::doubleValue).max().orElse(0);
    }
    
    private double max(double[] values) {
        return Arrays.stream(values).max().orElse(0);
    }
    
    private double percentile(List<Double> values, double p) {
        if (values.isEmpty()) return 0;
        List<Double> sorted = new ArrayList<>(values);
        Collections.sort(sorted);
        int index = (int) Math.ceil(p * sorted.size()) - 1;
        return sorted.get(Math.max(0, Math.min(index, sorted.size() - 1)));
    }
    
    private double round(double value, int decimals) {
        double multiplier = Math.pow(10, decimals);
        return Math.round(value * multiplier) / multiplier;
    }
    
    // Classe interna para armazenar métricas de cada veículo
    
    static class VehicleMetric {
        String vehicleId;
        double tripDuration;
        double avgSpeed;
        double co2;
        double fuel;
        double routeLength;
        
        VehicleMetric(String vehicleId, double tripDuration, double avgSpeed,
                     double co2, double fuel, double routeLength) {
            this.vehicleId = vehicleId;
            this.tripDuration = tripDuration;
            this.avgSpeed = avgSpeed;
            this.co2 = co2;
            this.fuel = fuel;
            this.routeLength = routeLength;
        }
    }
}
