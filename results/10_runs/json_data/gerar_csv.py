import json
import statistics
import glob
import os

# 1. Tentar encontrar os ficheiros JSON em várias pastas possíveis
pastas_possiveis = ["json-data", "json_data", "."]
ficheiros_json = []

for pasta in pastas_possiveis:
    ficheiros_json = glob.glob(os.path.join(pasta, "*.json"))
    if ficheiros_json:
        print(f"✓ Encontrados {len(ficheiros_json)} ficheiros JSON na pasta '{pasta}'.")
        break

if not ficheiros_json:
    print("ERRO: Não encontrei ficheiros JSON. Verifica se estás na pasta correta.")
    exit(1)

# 2. O mapeamento exato que pediste para o formato final
mapping = {
    "Trip_Time_Avg": ("trips", "avg_trip_time_s"),
    "P50": ("trips", "percentile_50_s"),
    "P95": ("trips", "percentile_95_s"),
    "Queue_Max_M": ("queue", "max_queue_length_m"),
    "Queue_Duration_S": ("queue", "queue_duration_s"),
    "Throughput": ("throughput", "avg_throughput_vps"),
    "V2X_Efficiency": ("v2x", "disseminationEfficiency"),
    "CO2_Avg": ("trips", "avg_co2_g"),
    "Fuel_Avg": ("trips", "avg_fuel_ml"),
    "Speed_Bottleneck": ("bottleneck", "avg_speed_kmh")
}

data_store = {key: [] for key in mapping.keys()}

# 3. Ler os dados de cada ficheiro
for f in ficheiros_json:
    with open(f, 'r') as jf:
        try:
            d = json.load(jf)
            for name, (cat, field) in mapping.items():
                val = d.get(cat, {}).get(field)
                if val is not None:
                    data_store[name].append(val)
        except Exception as e:
            print(f"Erro ao ler o ficheiro {f}: {e}")

# 4. Calcular Média e Mediana e escrever no CSV
ficheiro_csv = "resultados_finais.csv"
with open(ficheiro_csv, "w") as out:
    out.write("Métrica,Média,Mediana\n")
    for name in mapping.keys():
        vals = data_store[name]
        if vals:
            avg = statistics.mean(vals)
            med = statistics.median(vals)
            # Formatar para ter 2 a 3 casas decimais conforme o teu exemplo
            out.write(f"{name},{avg:.2f},{med:.2f}\n")
        else:
            out.write(f"{name},N/A,N/A\n")

print(f"✓ SUCESSO! CSV gerado: {ficheiro_csv}")