#!/usr/bin/env python3
"""
Script para reconstruir XMLs corruptados das 30 runs
Remove config SUMO e reconstrói estrutura válida
"""

import xml.etree.ElementTree as ET
from pathlib import Path

def rebuild_netstate(filepath):
    """Reconstrói netstate.xml limpo"""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        output = []
        output.append('<?xml version="1.0" encoding="UTF-8"?>')
        output.append('<netstate>')
        
        for timestep in root.findall('timestep'):
            time = timestep.get('time')
            output.append(f'    <timestep time="{time}">')
            
            for edge in timestep.findall('edge'):
                edge_id = edge.get('id')
                output.append(f'        <edge id="{edge_id}">')
                
                for lane in edge.findall('lane'):
                    lane_id = lane.get('id')
                    output.append(f'            <lane id="{lane_id}">')
                    
                    for vehicle in lane.findall('vehicle'):
                        v_id = vehicle.get('id')
                        pos = vehicle.get('pos')
                        speed = vehicle.get('speed')
                        output.append(f'                <vehicle id="{v_id}" pos="{pos}" speed="{speed}"/>')
                    
                    output.append('            </lane>')
                
                output.append('        </edge>')
            
            output.append('    </timestep>')
        
        output.append('</netstate>')
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(output))
        
        return True
    except Exception as e:
        print(f"  ❌ Erro netstate: {e}")
        return False

def rebuild_detector(filepath):
    """Reconstrói bottleneck_detector.xml (extrai só intervals)"""
    try:
        intervals = []
        with open(filepath, 'r') as f:
            for line in f:
                if '<interval' in line:
                    intervals.append(line.strip())
        
        output = []
        output.append('<?xml version="1.0" encoding="UTF-8"?>')
        output.append('<detector>')
        for interval in intervals:
            output.append(f'    {interval}')
        output.append('</detector>')
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(output))
        
        return len(intervals)
    except Exception as e:
        print(f"  ❌ Erro detector: {e}")
        return 0

def rebuild_tripinfo(filepath):
    """Reconstrói tripinfo.xml limpo"""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        output = []
        output.append('<?xml version="1.0" encoding="UTF-8"?>')
        output.append('<tripinfos>')
        
        for tripinfo in root.findall('tripinfo'):
            attrs = ' '.join([f'{k}="{v}"' for k, v in tripinfo.attrib.items()])
            output.append(f'    <tripinfo {attrs}>')
            
            for child in tripinfo:
                child_attrs = ' '.join([f'{k}="{v}"' for k, v in child.attrib.items()])
                output.append(f'        <{child.tag} {child_attrs}/>')
            
            output.append('    </tripinfo>')
        
        output.append('</tripinfos>')
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(output))
        
        return True
    except Exception as e:
        print(f"  ❌ Erro tripinfo: {e}")
        return False

def main():
    print("🔧 RECONSTRUINDO XMLs para as 30 runs...")
    print("=" * 60)
    
    for run_num in range(1, 31):
        run_dir = Path(f"results/run_{run_num}")
        
        if not run_dir.exists():
            continue
        
        print(f"Run {run_num:2d}... ", end='', flush=True)
        
        # Tripinfo
        tripinfo_file = run_dir / "tripinfo.xml"
        if tripinfo_file.exists():
            rebuild_tripinfo(tripinfo_file)
        
        # Netstate
        netstate_file = run_dir / "netstate.xml"
        if netstate_file.exists():
            rebuild_netstate(netstate_file)
        
        # Detector
        detector_file = run_dir / "bottleneck_detector.xml"
        if detector_file.exists():
            intervals = rebuild_detector(detector_file)
            print(f"✓ ({intervals} detector intervals)")
        else:
            print("✓")
    
    print("\n✅ Todos os XMLs reconstruídos!")

if __name__ == "__main__":
    main()
