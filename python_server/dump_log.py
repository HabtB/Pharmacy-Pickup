import re

def parse_logs():
    log_file = "server.log"
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("Log file not found.")
        return

    # Find start of last session
    last_session_idx = -1
    for i in range(len(lines) - 1, -1, -1):
        if "NEW SCAN SESSION" in lines[i]:
            last_session_idx = i
            break
            
    if last_session_idx == -1:
        print("No scan session found.")
        return

    print(f"**Scan Session: {lines[last_session_idx].strip().split('SESSION: ')[1]}**\n")
    
    session_lines = lines[last_session_idx:]
    
    current_image = None
    meds_by_image = {}
    
    # Regex to capture medication lines
    # Format: 2025-.. INFO -   1. MedicationName - Strength ...
    med_pattern = re.compile(r'INFO -   \d+\. (.*)')
    
    # Format: [Image 1] Starting processing...
    image_start_pattern = re.compile(r'\[Image (\d+)\] Starting processing')
    
    # Format: [Image 1] ✓ Parsing complete
    protected_med_pattern = re.compile(r'INFO -   \d+\. .*')

    # Since the logs for parallel processing might be interleaved, 
    # and the medication list printing happens *inside* the thread,
    # the log lines *might* not strictly follow [Image X] prefix if the logger format doesn't include it.
    # However, docling_server.py lines 253-255 do NOT have [Image X] prefix in the med listing.
    # But correct extraction relies on the fact that "Parsed X medications" comes right before the list.
    
    # Actually, in parallel mode, the log entries from different threads might be mixed.
    # But usually `logger.info` is atomic.
    # The `docling_server.py` code at line 427 logs "[Image {index+1}] ✓ Parsing complete..."
    # BUT the specific list printing (lines 253-255) is inside `process_single_image`.
    # AND in `parse_documents_parallel` (line 348), it calls `process_single_image`.
    # `process_single_image` (line 140) logs the list.
    # It does NOT prefix with [Image X] inside `process_single_image`.
    # This makes separating them hard if they run in parallel!
    # Wait, `process_single_image` call in `parse_documents_parallel` (line 348) logs "[Image {index+1}] Starting...".
    # But the inner function `process_single_image` (the standalone one used by single endpoint, OR the helper?)
    # `docling_server.py` has `process_single_image` (line 348) defined INSIDE `parse_documents_parallel`.
    # It calls `parser.parse`.
    # The logging of the list happens... wait.
    # Lines 252-256 are in `parse_document` (single endpoint).
    # Lines 348+ is `parse_documents_parallel`.
    # Does `parse_documents_parallel` log the list details?
    # Let's check `process_single_image` (helper) implementation around line 400.
    
    # I need to check if the parallel function actually logs the individual items to the main log.
    # If not, I can't generate the list from logs.
    
    pass

if __name__ == "__main__":
    # Just dump the last session relevant lines for manual review first to be sure
    with open("server.log", 'r') as f:
        lines = f.readlines()
        
    last_session_idx = -1
    for i in range(len(lines) - 1, -1, -1):
        if "NEW SCAN SESSION" in lines[i]:
            last_session_idx = i
            break
            
    if last_session_idx != -1:
        print("".join(lines[last_session_idx:]))
