# Pipeline MOSAIC - 30 Runs

## Estrutura Limpa

```
/home/netsim/tpnpr/
├── run_30_simulations.sh        # Script principal (executa 30 runs)
├── metrics_aggregator.py        # Processa XMLs de uma run
├── compile_statistics.py        # Calcula média/mediana (30 runs) → CSV
├── cenario_manhattan/
│   ├── application/tp-app-1.0.jar
│   └── sumo/simulation.add.xml  # Detector: -E17 (bottleneck)
├── results/
│   ├── run_1/
│   ├── run_2/
│   └── ... run_30/
└── src/main/java/.../MetricsCollector.java
```

## Como Executar

### 1. Fazer 30 simulações (≈30-40 min)
```bash
cd /home/netsim/tpnpr
./run_30_simulations.sh
```

**Resultado:** 30 pastas `results/run_1` até `results/run_30`
Cada pasta contém:
- `metrics_sumo_X.json` - Métricas processadas
- `tripinfo.xml` - Dados de viagem SUMO
- `netstate.xml` - Filas ao longo do tempo
- `bottleneck_detector.xml` - Detector -E17
- `metrics_wrapper.json` - Métricas do wrapper (V2X, CO2, etc)

### 2. Compilar estatísticas finais (≈10 segundos)
```bash
python3 compile_statistics.py
```

**Resultado:** `Metricas_Finais.csv`

## Métricas Coletadas

### De SUMO (tripinfo.xml)
- ✅ Tempo médio de viagem
- ✅ Percentis: P25, P50 (mediana), P95
- ✅ Tempo médio de espera
- ✅ Emissões CO2 (g) e Consumo Combustível (ml)

### De SUMO (netstate.xml + detector)
- ✅ Comprimento máximo da fila (m)
- ✅ Duração da fila (s)
- ✅ Throughput no gargalo (-E17): veículos/s
- ✅ Velocidade média no gargalo: km/h

### De MOSAIC (MetricsCollector.java)
- ✅ Mensagens V2X (total)
- ✅ Eficiência de disseminação V2X

## Saída Final: Metricas_Finais.csv

```
Métrica,Média,Mediana,Unidade
Runs Válidas,30,N/A,número

=== TEMPO DE VIAGEM ===
Tempo Médio de Viagem,XXX.XX,XXX.XX,s
P50 (Mediana) Tempo de Viagem,XXX.XX,XXX.XX,s
P95 Tempo de Viagem,XXX.XX,XXX.XX,s

=== TEMPO DE ESPERA ===
Tempo Médio de Espera,XXX.XX,XXX.XX,s

=== FILA ===
Comprimento Máximo da Fila,XXX.XX,XXX.XX,m
Duração da Fila,XXXX,XXXX,s

=== GARGALO (-E17) ===
Throughput,X.XXX,X.XXX,veículos/s
Velocidade Média,XX.XX,XX.XX,km/h

=== V2X ===
Mensagens V2X Total,XXXXX,XXXXX,número
Eficiência de Disseminação,X.XX,X.XX,taxa

=== EMISSÕES ===
CO2 Médio,XXX.XX,XXX.XX,g
Combustível Médio,XXX.XX,XXX.XX,ml
```

## Detalhes Técnicos

### Detector: -E17 (Lane -E17_0)
- Localização: Zona Sul do cenário Manhattan
- Posição: pos=96 (metros)
- Frequência: 5 segundos
- Mede: Veículos passando (throughput) e velocidade média

### MetricsCollector.java
- Singleton que coleta métricas durante a simulação
- Registra: Viagens de veículos, dados de fila (RSU), mensagens V2X
- Output: `/home/netsim/tpnpr/metrics_from_wrapper.json`

### SUMO
- Simula tráfego da rede Manhattan
- Produz: tripinfo.xml (viagens), netstate.xml (estado rede), detector XML
- Tempo de simulação: ~60s por run
- XML fixing: Adiciona tags de fechamento (SUMO trunca ficheiros)

### Scripts Python
- **metrics_aggregator.py**: Processa uma run
  - Input: tripinfo.xml, netstate.xml, bottleneck_detector.xml, metrics_wrapper.json
  - Output: metrics_sumo_X.json
  
- **compile_statistics.py**: Processa todas as 30 runs
  - Input: Todas as runs em results/run_X/
  - Output: Metricas_Finais.csv (média + mediana)

## Troubleshooting

Se alguma run falhar:
- Verificar `results/run_X/mosaic.log`
- MOSAIC timeout: verificar SUMO_HOME
- XML parsing error: ficheiros podem estar truncados (script trata isto)

Se compile_statistics.py falhar:
- Verificar se todas as runs têm `metrics_sumo_X.json`
- Output do script mostra quais runs falharam
