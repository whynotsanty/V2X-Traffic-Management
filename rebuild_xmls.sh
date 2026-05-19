#!/bin/bash
# Script para CORRIGIR os XMLs danificados das 30 runs

echo "🔧 RECONSTRUINDO XMLs para as 30 runs..."
echo "================================================"

for run_num in {1..30}; do
    run_dir="results/run_$run_num"
    
    if [ ! -d "$run_dir" ]; then
        continue
    fi
    
    echo "Run $run_num..."
    
    # ===== FIX NETSTATE.XML =====
    if [ -f "$run_dir/netstate.xml" ]; then
        # Remove linhas de config SUMO que aparecem no início
        # Extrai apenas as linhas com tags XML válidas
        # Remove duplicatas de </lane>
        
        cat > "$run_dir/netstate.xml.tmp" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<netstate>
EOF
        
        # Extrai só os timesteps válidos
        grep '<timestep' "$run_dir/netstate.xml" | while read line; do
            echo "    $line" >> "$run_dir/netstate.xml.tmp"
            # Extrai edges/lanes/vehicles desse timestep
            timestep_num=$(echo "$line" | grep -o 'time="[^"]*"' | head -1)
            
            # Procura pelo próximo timestep ou fechamento
            grep -A 500 "time=\".*\"" "$run_dir/netstate.xml" | grep -B 500 '<timestep' | tail -499 | grep -v '<timestep' | while read subline; do
                echo "        $subline" >> "$run_dir/netstate.xml.tmp"
                # Para quando encontrar próximo timestep
                if echo "$subline" | grep -q '<timestep'; then
                    break
                fi
                if echo "$subline" | grep -q '</timestep>'; then
                    break
                fi
            done
        done
        
        echo "</netstate>" >> "$run_dir/netstate.xml.tmp"
        
        # Mais simples: extrai só o que é válido
        # Remove o header de config SUMO
        python3 << PYSCRIPT
import xml.etree.ElementTree as ET

input_file = "$run_dir/netstate.xml"
output_file = "$run_dir/netstate.xml.tmp"

try:
    tree = ET.parse(input_file)
    root = tree.getroot()
    
    # Reconstrói o XML limpo
    with open(output_file, 'w') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<netstate>\n')
        
        for timestep in root.findall('timestep'):
            time = timestep.get('time')
            f.write(f'    <timestep time="{time}">\n')
            
            for edge in timestep.findall('edge'):
                edge_id = edge.get('id')
                f.write(f'        <edge id="{edge_id}">\n')
                
                for lane in edge.findall('lane'):
                    lane_id = lane.get('id')
                    f.write(f'            <lane id="{lane_id}">\n')
                    
                    for vehicle in lane.findall('vehicle'):
                        v_id = vehicle.get('id')
                        pos = vehicle.get('pos')
                        speed = vehicle.get('speed')
                        f.write(f'                <vehicle id="{v_id}" pos="{pos}" speed="{speed}"/>\n')
                    
                    f.write('            </lane>\n')
                
                f.write('        </edge>\n')
            
            f.write('    </timestep>\n')
        
        f.write('</netstate>\n')
    
    print(f"  ✓ netstate.xml limpo")
except Exception as e:
    print(f"  ❌ Erro ao limpar netstate: {e}")
PYSCRIPT
        
        mv "$run_dir/netstate.xml.tmp" "$run_dir/netstate.xml"
    fi
    
    # ===== FIX BOTTLENECK_DETECTOR.XML =====
    if [ -f "$run_dir/bottleneck_detector.xml" ]; then
        python3 << PYSCRIPT
input_file = "$run_dir/bottleneck_detector.xml"
output_file = "$run_dir/bottleneck_detector.xml.tmp"

# Lê o arquivo e extrai só as linhas com <interval
intervals = []
with open(input_file, 'r') as f:
    for line in f:
        if '<interval' in line:
            intervals.append(line.strip())

# Reconstrói o XML
with open(output_file, 'w') as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<detector>\n')
    for interval in intervals:
        f.write(f'    {interval}\n')
    f.write('</detector>\n')

print(f"  ✓ bottleneck_detector.xml limpo ({len(intervals)} intervals)")
PYSCRIPT
        
        mv "$run_dir/bottleneck_detector.xml.tmp" "$run_dir/bottleneck_detector.xml"
    fi
    
    # ===== FIX TRIPINFO.XML =====
    if [ -f "$run_dir/tripinfo.xml" ]; then
        python3 << PYSCRIPT
import xml.etree.ElementTree as ET

input_file = "$run_dir/tripinfo.xml"
output_file = "$run_dir/tripinfo.xml.tmp"

try:
    tree = ET.parse(input_file)
    root = tree.getroot()
    
    with open(output_file, 'w') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<tripinfos>\n')
        
        for tripinfo in root.findall('tripinfo'):
            attrs = ' '.join([f'{k}="{v}"' for k, v in tripinfo.attrib.items()])
            f.write(f'    <tripinfo {attrs}>\n')
            
            for child in tripinfo:
                child_attrs = ' '.join([f'{k}="{v}"' for k, v in child.attrib.items()])
                f.write(f'        <{child.tag} {child_attrs}/>\n')
            
            f.write('    </tripinfo>\n')
        
        f.write('</tripinfos>\n')
    
    print(f"  ✓ tripinfo.xml limpo")
except Exception as e:
    print(f"  ❌ Erro ao limpar tripinfo: {e}")
PYSCRIPT
        
        mv "$run_dir/tripinfo.xml.tmp" "$run_dir/tripinfo.xml"
    fi
done

echo ""
echo "✅ XMLs reconstruídos com sucesso!"
