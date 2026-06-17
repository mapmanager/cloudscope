import sys
import os
import subprocess
from nicegui import ui
import state_manager

# Ensure base state is ready on startup
state_manager.init_database_store()
IS_NATIVE = state_manager.IS_NATIVE

# Handle to safely monitor child process lifecycle pointers locally
child_process_handle = None

def setup_main_ui():
    ui.label('Main Controller / Page 1').classes('text-h6 text-blue')
    
    current_state = state_manager.get_store_state()
    initial_sel = current_state.get('selection_state', {})
    
    w1_file = ui.input(label='File Name', value=initial_sel.get('file'))
    w1_chan = ui.number(label='Channel', value=initial_sel.get('channel'), format='%d')
    w1_roi = ui.number(label='ROI ID', value=initial_sel.get('roi_id'), format='%d')

    def handle_open_pool():
        global child_process_handle
        
        # Sync current parent settings to mailbox store database first
        current_sel = {"file": w1_file.value, "channel": int(w1_chan.value), "roi_id": int(w1_roi.value)}
        state_manager.update_store_state(current_sel, 'page1')

        if IS_NATIVE:
            if child_process_handle and child_process_handle.poll() is None:
                ui.notify('Pool window is already open!', type='warning')
                return
            
            # DECNATIVE ADVANTAGE: Execute script as an independent operating system process
            # We pass our current PID as a simple string command argument
            script_dir = os.path.dirname(os.path.abspath(__file__))
            pool_script_path = os.path.join(script_dir, "pool_window.py")
            parent_pid_str = str(os.getpid())
            
            child_process_handle = subprocess.Popen([
                sys.executable, pool_script_path, parent_pid_str, "--native"
            ])
            ui.notify('Opening Pool Window Desktop Frame...', type='positive')
        else:
            ui.navigate.to('/pool', new_tab=True)

    ui.button('Open Pool View', on_click=handle_open_pool).classes('mb-2')

    def push_update():
        current_sel = {"file": w1_file.value, "channel": int(w1_chan.value), "roi_id": int(w1_roi.value)}
        state_manager.update_store_state(current_sel, 'page1')

    ui.button('Push Update', on_click=push_update).props('color=blue').classes('mb-4')

    row_id_input = ui.number(label='Target Pool Row ID', value=1, format='%d')
    status_input = ui.input(label='New Status', value='Validated')

    def mutate_row():
        state = state_manager.get_store_state()
        rows = list(state.get('pool_rows', []))
        for row in rows:
            if row['pool_row_id'] == int(row_id_input.value):
                row['status'] = status_input.value
        state_manager.update_pool_rows_state(rows)

    ui.button('Dispatch UpdatePoolRowIntent', on_click=mutate_row).props('color=orange')

    last_version = current_state.get('version', 0)
    def listen_for_pool_changes():
        nonlocal last_version
        state = state_manager.get_store_state()
        cur_ver = state.get('version', 0)
        
        if cur_ver != last_version:
            last_version = cur_ver
            if state.get('last_updated_by') == 'page2':
                sel = state.get('selection_state', {})
                w1_file.value = sel.get('file')
                w1_chan.value = sel.get('channel')
                w1_roi.value = sel.get('roi_id')

    ui.timer(0.1, listen_for_pool_changes)


# =====================================================================
# INTERFACE REGISTRATIONS AND SERVER DEPLOYMENT
# =====================================================================
if IS_NATIVE:
    if __name__ == '__main__':
        setup_main_ui()
        ui.run(native=True, port=8080, title="Main Window", reload=False)
else:
    @ui.page('/')
    def web_route_main():
        setup_main_ui()

    @ui.page('/pool')
    def web_pool_page_route():
        # Leverage our identical script element views straight inside web routes
        import pool_window
        pool_window.render_pool_layout()

    if __name__ == '__main__':
        ui.run(port=8080, title="Web Interface", reload=False)
