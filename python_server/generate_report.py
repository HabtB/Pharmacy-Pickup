import re
import os

def generate_report():
    log_file = "server.log"
    if not os.path.exists(log_file):
        print("server.log not found")
        return

    with open(log_file, 'r') as f:
        lines = f.readlines()

    # Find the last TWO "NEW SCAN SESSION"
    session_start_idx = -1
    sessions_found = 0
    for i in range(len(lines) - 1, -1, -1):
        if "NEW SCAN SESSION" in lines[i]:
            session_start_idx = i
            sessions_found += 1
            if sessions_found == 2:
                break
    
    if session_start_idx == -1:
        print("No scan session found")
        return

    # Extract all logs from that point on
    session_logs = lines[session_start_idx:]
    
    # We want to group medications by Image.
    # The logs look like: 
    # [Image X] ...
    # ...
    # [Image X] ✓ Parsing complete...
    #   1. MedName ...
    #   2. MedName ...
    
    # However, in parallel execution, valid med lines might not have [Image X] prefix directly on them if printed by a sub-function.
    # But usually the logger call itself might not include it unless added explicitly.
    # Let's rely on the order. The lines "  1. ...", "  2. ..." usually proceed "Parsing complete" block for a specific image thread.
    # But threads mix.
    # Wait, the log lines I saw in grep were: `INFO -   1. ferrous sulfate ...`
    # They DO NOT have [Image X].
    # But usually a block is printed atomically? No, logging is thread-safe but lines interleave.
    # IF the code does `logger.info('\n'.join(lines))`, it's one block.
    # IF it does `for med in meds: logger.info(...)`, they can interleave.
    # The code does the loop.
    
    # However, in step 1607, I saw clusters of meds.
    # I can group them by timestamp proximity or just list them all.
    # The user asked for "Page by Page".
    # Without the [Image X] prefix on the individual med lines, strict page assignment is hard if they interleaved perfectly.
    # But usually, 1 image finishes, prints its meds, then another finishes.
    # I will group them by "Cluster".
    
    clusters = []
    current_cluster = []
    last_idx = 0
    
    med_pattern = re.compile(r'INFO -   \d+\. (.*)')
    
    for line in session_logs:
        match = med_pattern.search(line)
        if match:
            # Check if this resets the count (e.g. back to 1)
            content = match.group(1)
            # If it starts with "1.", it might be a new cluster, UNLESS it's just "11."
            if " 1. " in line:
                if current_cluster:
                    clusters.append(current_cluster)
                    current_cluster = []
            
            # Additional heuristic: checking time diff? No, just list them.
            # Actually, the grep shows:
            # 02:15:01 -> Image A meds (1..11) all same second
            # 02:15:10 -> Image B meds (1..8) all same second
            # This confirms they are clustered by time.
            
            current_cluster.append(line.strip())
            
    if current_cluster:
        clusters.append(current_cluster)
        
    print(f"Found {len(clusters)} pages of medications in last session.\n")
    
    for i, cluster in enumerate(clusters):
        print(f"### Page {i+1}")
        for item in cluster:
            # Clean up the log prefix "2025... INFO -   "
            clean_item = item.split("INFO -   ")[1]
            print(clean_item)
        print("")

if __name__ == "__main__":
    generate_report()
