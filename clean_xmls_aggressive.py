#!/usr/bin/env python3
"""
Limpeza AGRESSIVA de XMLs - remove tudo que não é válido
"""

from pathlib import Path
import re

def clean_netstate_aggressive(filepath):
    """Remove tudo que não é XML válido do netstate"""
    with open(filepath, 'r', errors='ignore') as f:
        content = f.read()
    
    # Remove header de config SUMO (tudo antes de <netstate>)
    if '<netstate>' in content:
        content = content[content.find('<netstate>'):]
    
    # Remove tudo depois de </netstate>
    if '</netstate>' in content:
        content = content[:content.rfind('</netstate>') + len('</netstate>')]
    
    # Reconstrói limpo
    output = ['<?xml version="1.0" encoding="UTF-8"?>', '<netstate>']
    
    # Extrai todos os timesteps
    timestep_pattern = r'<timestep time="([^"]*)">'
    for match in re.finditer(timestep_pattern, content):
        time = match.group(1)
        output.append(f'    <timestep time="{time}">')
        
        # Extrai edges/lanes/vehicles deste timestep
        start_pos = match.end()
        # Procura próximo timestep
        next_match = re.search(timestep_pattern, content[start_pos:])
        if next_match:
            end_pos = start_pos + next_match.start()
        else:
            end_pos = content.find('</netstate>', start_pos)
        
        section = content[start_pos:end_pos]
        
        # Extrai edges
        edge_pattern = r'<edge id="([^"]*)">'
        for edge_match in re.finditer(edge_pattern, section):
            edge_id = edge_match.group(1)
            output.append(f'        <edge id="{edge_id}">')
            
            # Extrai lanes deste edge
            edge_start = edge_match.end()
            edge_next = re.search(r'<edge|</timestep>', section[edge_start:])
            if edge_next:
                edge_end = edge_start + edge_next.start()
            else:
                edge_end = len(section)
            
            edge_section = section[edge_start:edge_end]
            
            lane_pattern = r'<lane id="([^"]*)">'
            for lane_match in re.finditer(lane_pattern, edge_section):
                lane_id = lane_match.group(1)
                output.append(f'            <lane id="{lane_id}">')
                
                # Extrai vehicles deste lane
                lane_start = lane_match.end()
                lane_next = re.search(r'<lane|</edge>', edge_section[lane_start:])
                if lane_next:
                    lane_end = lane_start + lane_next.start()
                else:
                    lane_end = len(edge_section)
                
                lane_section = edge_section[lane_start:lane_end]
                
                vehicle_pattern = r'<vehicle id="([^"]*)" pos="([^"]*)" speed="([^"]*)"/>'
                for vehicle_match in re.finditer(vehicle_pattern, lane_section):
                    v_id, pos, speed = vehicle_match.groups()
                    output.append(f'                <vehicle id="{v_id}" pos="{pos}" speed="{speed}"/>')
                
                output.append('            </lane>')
            
            output.append('        </edge>')
        
        output.append('    </timestep>')
    
    output.append('</netstate>')
    
    with open(filepath, 'w') as f:
        f.write('\n'.join(output))

def clean_detector_aggressive(filepath):
    """Remove tudo que não é interval do detector"""
    with open(filepath, 'r', errors='ignore') as f:
        content = f.read()
    
    output = ['<?xml version="1.0" encoding="UTF-8"?>', '<detector>']
    
    # Extrai todos os intervals
    interval_pattern = r'<interval[^>]*>'
    for match in re.finditer(interval_pattern, content):
        output.append(f'    {match.group(0)}')
    
    output.append('</detector>')
    
    with open(filepath, 'w') as f:
        f.write('\n'.join(output))
    
    return len(re.findall(interval_pattern, content))

def clean_tripinfo_aggressive(filepath):
    """Remove tudo que não é tripinfo válido"""
    with open(filepath, 'r', errors='ignore') as f:
        content = f.read()
    
    output = ['<?xml version="1.0" encoding="UTF-8"?>', '<tripinfos>']
    
    # Extrai todos os tripinfo
    tripinfo_pattern = r'<tripinfo[^>]*>.*?</tripinfo>'
    for match in re.finditer(tripinfo_pattern, content, re.DOTALL):
        lines = match.group(0).split('\n')
        for line in lines:
            output.append('    ' + line.strip())
    
    output.append('</tripinfos>')
    
    with open(filepath, 'w') as f:
        f.write('\n'.join(output))

def main():
    print("🔧 LIMPEZA AGRESSIVA dos XMLs...")
    print("=" * 60)
    
    for run_num in range(1, 31):
        run_dir = Path(f"results/run_{run_num}")
        
        if not run_dir.exists():
            continue
        
        print(f"Run {run_num:2d}... ", end='', flush=True)
        
        try:
            # Tripinfo
            tripinfo_file = run_dir / "tripinfo.xml"
            if tripinfo_file.exists():
                clean_tripinfo_aggressive(tripinfo_file)
            
            # Detector
            detector_file = run_dir / "bottleneck_detector.xml"
            intervals = 0
            if detector_file.exists():
                intervals = clean_detector_aggressive(detector_file)
            
            # Netstate (mais complexo, por isso por último)
            netstate_file = run_dir / "netstate.xml"
            if netstate_file.exists():
                clean_netstate_aggressive(netstate_file)
            
            print(f"✓")
        except Exception as e:
            print(f"❌ {e}")
    
    print("\n✅ Limpeza agressiva completa!")

if __name__ == "__main__":
    main()
