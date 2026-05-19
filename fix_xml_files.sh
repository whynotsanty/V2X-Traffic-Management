#!/bin/bash
# Script para reparar XMLs corruptados

echo "🔧 Reparando XMLs corruptados..."

for run_dir in results/run_*/; do
    run_num=$(basename "$run_dir" | sed 's/run_//')
    
    # Fix netstate.xml
    if [ -f "$run_dir/netstate.xml" ]; then
        echo "  Reparando $run_dir/netstate.xml..."
        # Remover qualquer </netstate> que esteja no meio de uma tag
        sed -i 's/<\/netstate>//' "$run_dir/netstate.xml"
        # Remover tags abertas incompletas no fim
        sed -i '/<vehicle\s*$/d' "$run_dir/netstate.xml"
        sed -i '/<edge\s*$/d' "$run_dir/netstate.xml"
        sed -i '/<lane\s*$/d' "$run_dir/netstate.xml"
        sed -i '/<timestep\s*$/d' "$run_dir/netstate.xml"
        # Adicionar closing tags corretos
        echo "            </lane>" >> "$run_dir/netstate.xml"
        echo "        </edge>" >> "$run_dir/netstate.xml"
        echo "    </timestep>" >> "$run_dir/netstate.xml"
        echo "</netstate>" >> "$run_dir/netstate.xml"
    fi
    
    # Fix tripinfo.xml
    if [ -f "$run_dir/tripinfo.xml" ]; then
        echo "  Reparando $run_dir/tripinfo.xml..."
        # Remover qualquer </tripinfos> que esteja no meio
        sed -i 's/<\/tripinfos>//' "$run_dir/tripinfo.xml"
        # Remover tags abertas incompletas
        sed -i '/<tripinfo\s*$/d' "$run_dir/tripinfo.xml"
        sed -i '/<emission\s*$/d' "$run_dir/tripinfo.xml"
        # Adicionar closing tag
        echo "</tripinfos>" >> "$run_dir/tripinfo.xml"
    fi
    
    # Fix bottleneck_detector.xml (se tiver dados)
    if [ -f "$run_dir/bottleneck_detector.xml" ]; then
        echo "  Reparando $run_dir/bottleneck_detector.xml..."
        sed -i 's/<\/detector>//' "$run_dir/bottleneck_detector.xml"
        echo "</detector>" >> "$run_dir/bottleneck_detector.xml"
    fi
done

echo "✅ Reparação completa!"
