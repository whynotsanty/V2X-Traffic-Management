# TP NPR — Gestão Cooperativa de Tráfego V2X (Opção A)

Trabalho Prático da unidade curricular de **Novos Paradigmas de Rede (NPR)** da
**Universidade do Minho (UMinho)**.

Este projeto implementa um sistema de **gestão cooperativa de tráfego** baseado em
comunicação **V2X** (Vehicle-to-Everything), recorrendo a um cenário de simulação em
malha urbana ("Manhattan"). A simulação é orquestrada pelo **Eclipse MOSAIC** acoplado ao
simulador de tráfego **SUMO**, sendo a lógica das aplicações (veículos e RSU) desenvolvida em
**Java**. Trata-se da **Opção A** do enunciado.

Os veículos trocam mensagens entre si e com uma RSU (Road-Side Unit); a RSU agrega a
informação recebida e, no final da simulação, gera um relatório de métricas que é depois
processado para análise estatística e visualização num dashboard.

## Autores

- Gonçalo Ferreira
- Gustavo Castro
- Matilde Oliveira

## Pré-requisitos

- **Eclipse MOSAIC 24.1** (instalado em `/home/netsim/opt/eclipse-mosaic-24.1`, com `mosaic.sh`)
- **SUMO** (em `/usr/bin/sumo`)
- **JDK 21** (a aplicação compila com `maven.compiler.release=21`)
- **Apache Maven**
- **Python 3** com as bibliotecas:
  - `pandas`
  - `plotly`
  - `streamlit`
  - opcionalmente `scipy` (para testes estatísticos adicionais)

Instalação das dependências Python:

```bash
pip install pandas plotly streamlit scipy
```

## Estrutura do projeto

```
tpnpr/
├── src/main/java/org/eclipse/mosaic/app/npr/
│   ├── NprRsuApp.java              # Aplicação da Road-Side Unit (agrega métricas, gera relatório)
│   ├── NprVehicleApp.java          # Aplicação dos veículos (envio/receção de mensagens V2X)
│   ├── NprCamMessage.java          # Mensagem V2X do tipo CAM
│   ├── NprDenmMessage.java         # Mensagem V2X do tipo DENM
│   └── MetricsCollector.java       # Recolha/escrita das métricas
├── cenario/                        # Cenário base do MOSAIC/SUMO
├── cenario_manhattan/              # Cenário em malha urbana (usado nas simulações)
│   ├── scenario_config.json        # Configuração do cenário MOSAIC
│   ├── application/                # JAR da aplicação (tp-app-1.0.jar)
│   └── lib/                        # JAR da aplicação (tp-app-1.0.jar)
├── pom.xml                         # Configuração de build Maven
├── run_single_demo.sh             # Corre 1 simulação de demonstração
├── run_30_simulations.sh          # Corre 30 simulações com seeds aleatórias
├── compilar_resultados.py         # Compila/estatísticas dos resultados das runs
├── dashboard.py                   # Dashboard interativo (Streamlit)
└── README.md
```

## Como compilar

A aplicação é compilada com Maven, gerando o artefacto em `target/`:

```bash
mvn clean package
```

O JAR resultante fica em:

```
target/tp-app-1.0.jar
```

**Importante:** o MOSAIC carrega a aplicação a partir do cenário, pelo que o JAR tem de ser
copiado para dentro do cenário, tanto para a pasta `application/` como para a pasta `lib/`:

```bash
cp target/tp-app-1.0.jar cenario_manhattan/application/tp-app-1.0.jar
cp target/tp-app-1.0.jar cenario_manhattan/lib/tp-app-1.0.jar
```

> Nota: as aplicações MOSAIC **não** são lançadas por uma `main-class`; são instanciadas pela
> framework MOSAIC com base na configuração do cenário. Por isso o JAR não define nenhum
> `Main-Class` no manifest.

## Como correr

### Simulação única (demonstração)

```bash
./run_single_demo.sh
```

Corre uma única simulação com uma seed aleatória e mostra as métricas resultantes. Os
resultados ficam em `results/run_test/`.

### 30 simulações

```bash
./run_30_simulations.sh
```

Corre 30 simulações, cada uma com uma seed aleatória diferente. Cada run é guardada em
`results/run_N/` (com `N` de 1 a 30), contendo:

- `metrics_wrapper.json` — métricas geradas pela aplicação Java (a RSU)
- `tripinfo.xml` — saída de viagens do SUMO (usada na análise)
- `mosaic.log` — log da execução do MOSAIC

### System property opcional

O código Java escreve as métricas para o caminho indicado pela system property
`npr.metrics.out` (por omissão `/home/netsim/opt/tpnpr/metrics_from_wrapper.json`). É possível
redirecionar essa saída, por exemplo:

```bash
./mosaic.sh -c cenario_manhattan/scenario_config.json -r 1234 \
    -Dnpr.metrics.out=/caminho/alternativo/metrics.json
```

## Como gerar estatísticas

Depois de correr as simulações, compila os resultados e calcula as estatísticas com:

```bash
python3 compilar_resultados.py
```

## Como abrir o dashboard

Para visualizar os resultados de forma interativa:

```bash
streamlit run dashboard.py
```
