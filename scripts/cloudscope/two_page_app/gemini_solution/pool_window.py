import sys
import os
import time
import threading
from nicegui import ui
import state_manager

# Ensure database store tables are valid on initialization
state_manager.init_database_store()

def monitor_parent_process(parent_pid):
    """Monitor loop that forces the pool process to close if the main parent dies."""
    while True:
        time.sleep(0.5)
        try:
            os.kill(parent_pid, 0)
        except OSError:
            os._exit(0)

def render_pool_layout():
    ui.label('Pool View / Window 2').classes('text-h6 text-green')
    
    current_state = state_manager.get_store_state()
    initial_sel = current_state.get('selection_state', {})
    
    ui.label('Modify State & Send Back:').classes('font-bold mt-2')
    w2_file = ui.input(label='File Name', value=initial_sel.get('file'))
    w2_chan = ui.number(label='Channel', value=initial_sel.get('channel'), format='%d')
    w2_roi = ui.number(label='ROI ID', value=initial_sel.get('roi_id'), format='%d')

    def send_intent_back():
        new_sel = {"file": w2_file.value, "channel": int(w2_chan.value), "roi_id": int(w2_roi.value)}
        state_manager.update_store_state(new_sel, 'page2')

    ui.button('Update Selection State', on_click=send_intent_back).props('color=green')

    grid_container = ui.element('div').classes('p-2 border rounded bg-gray-50')
    def refresh_grid(rows):
        grid_container.clear()
        with grid_container:
            for row in rows:
                ui.label(f"ID: {row['pool_row_id']} | Status: {row['status']}")

    refresh_grid(current_state.get('pool_rows', []))
    last_version = current_state.get('version', 0)

    def listen_for_changes():
        nonlocal last_version
        state = state_manager.get_store_state()
        cur_ver = state.get('version', 0)
        
        if cur_ver != last_version:
            last_version = cur_ver
            refresh_grid(state.get('pool_rows', []))
            if state.get('last_updated_by') == 'page1':
                sel = state.get('selection_state', {})
                w2_file.value = sel.get('file')
                w2_chan.value = sel.get('channel')
                w2_roi.value = sel.get('roi_id')

    ui.timer(0.1, listen_for_changes)

# Look for parent PID arguments passed during native script subprocess initialization
if len(sys.argv) > 1 and sys.argv[1].isdigit():
    parent_pid = int(sys.argv[1])
    t = threading.Thread(target=monitor_parent_process, args=(parent_pid,), daemon=True)
    t.start()

if __name__ in {"__main__", "__mp_main__"}:
    if state_manager.IS_NATIVE:
        render_pool_layout()
        ui.run(native=True, port=8081, title="Pool Window", reload=False)
