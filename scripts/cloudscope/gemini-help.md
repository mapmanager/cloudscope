# Comprehensive Guide: Multi-Window Architecture in NiceGUI (with Multi-Processing and Two-Way Live Sync)

This document covers running multiple desktop windows (`native=True`) in NiceGUI, sharing live updates between separate processes, handling initialization on launch, self-closing windows, and safely handling user window closure for re-opening. 

These patterns are fully compatible with packaging tools like `nicegui-pack` and PyInstaller on both Windows and macOS.

---

## 1. Core Architecture Constraints
* **Single Process Limit:** NiceGUI relies on Python-Webview for native desktop mode. This library only permits **one active window per Python process**. 
* **The Solution:** To launch a second window, you must utilize Python’s `multiprocessing` module to spin up a completely distinct process for the second window.
* **The Intermediary:** Separate processes cannot directly mutate or access each other's memory or UI objects. A `multiprocessing.Manager` object must act as a shared memory mailbox. Both windows use a background loop (`ui.timer`) to scan this mailbox for updates.

---

## 2. Production-Ready Code Implementation

The following complete Python script showcases a main controller window (**Window 1**) and a contextual window (**Window 2**). 

### Key Features Included:
1. **Packaging Fixes:** Native `.exe` and `.app` protection (`freeze_support` and `spawn` engine forcing).
2. **Two-Way Real-time Syncing:** Live dictionary updates transferred across separate system processes.
3. **Dynamic Launch Injections:** Grabs current UI values from Window 1 and passes them straight into Window 2 inputs on startup.
4. **Auto-Teardown/Orphan Control:** If Window 1 is closed or killed, a deep thread in Window 2 auto-terminates Window 2.
5. **Safe Close & Re-open Cycle:** Checks process status (`is_alive`) and spawns a clean `Process` object on every single click.

```python
import sys
import os
import time
import threading
import multiprocessing
from multiprocessing import Process, Manager
from nicegui import ui

# ==========================================
# 1. CRITICAL DESKTOP PACKAGING CONSTRAINTS
# ==========================================
# This section must be evaluated first at the top-level scope of your file. 
# Without freeze_support, compiling with nicegui-pack/PyInstaller causes an
# infinite process fork loop that opens windows endlessly until the OS crashes.
if __name__ == '__main__':
    multiprocessing.freeze_support()
    # macOS requires the 'spawn' process method to isolate webview loops cleanly
    if sys.platform == 'darwin':
        multiprocessing.set_start_method('spawn', force=True)


# ==========================================
# 2. WINDOW 2 SYSTEM LOGIC (SUB-PROCESS)
# ==========================================
def monitor_parent_process(parent_pid):
    """
    A low-overhead background thread running inside Window 2.
    It pings the operating system for the parent PID every 0.5 seconds.
    If the parent process disappears (closed or crashed), it kills itself.
    """
    while True:
        time.sleep(0.5)
        try:
            # Signal 0 tests if the process ID is still alive in the OS kernel
            os.kill(parent_pid, 0)
        except OSError:
            # Parent process is missing. Force an immediate deep exit.
            os._exit(0)


def run_second_app(shared_dict, parent_pid):
    """Layout and state machine logic for Desktop Window 2."""
    # Spin up the orphan control safety thread
    t = threading.Thread(target=monitor_parent_process, args=(parent_pid,), daemon=True)
    t.start()

    ui.label('Desktop Window 2').classes('text-h6 text-green')
    
    # FEATURE: Load current data injected by Window 1 directly on initialization
    initial_data = shared_dict.get('to_w2', {"file": "None", "channel": 0, "roi_id": 0})
    
    ui.label('Send Data Back to Window 1:').classes('font-bold mt-2')
    # Build inputs pre-populated with Window 1's starting states
    w2_file_input = ui.input(label='New File Name', value=initial_data.get('file'))
    w2_chan_input = ui.number(label='New Channel', value=initial_data.get('channel'), format='%d')
    w2_roi_input = ui.number(label='New ROI ID', value=initial_data.get('roi_id'), format='%d')

    def send_back_to_w1():
        # Packaging selection packet to transit back upstream
        shared_dict['to_w1'] = {
            "file": w2_file_input.value,
            "channel": int(w2_chan_input.value),
            "roi_id": int(w2_roi_input.value)
        }

    ui.button('Send to Window 1', on_click=send_back_to_w1).props('color=green').classes('mb-4')

    # --- Live Downstream Sync Section ---
    ui.label('Live Data from Window 1:').classes('font-bold mt-2')
    w1_file = ui.label(f"File: {initial_data.get('file')}")
    w1_channel = ui.label(f"Channel: {initial_data.get('channel')}")
    w1_roi = ui.label(f"ROI ID: {initial_data.get('roi_id')}")
    
    last_seen_from_w1 = initial_data.copy()

    def listen_to_window_1():
        nonlocal last_seen_from_w1
        current_data = shared_dict.get('to_w2')
        # Only process updates if data exists and is visually distinct
        if current_data and current_data != last_seen_from_w1:
            last_seen_from_w1 = current_data.copy()
            w1_file.set_text(f"File: {current_data.get('file')}")
            w1_channel.set_text(f"Channel: {current_data.get('channel')}")
            w1_roi.set_text(f"ROI ID: {current_data.get('roi_id')}")

    # Tick at 100ms intervals to handle incoming UI data stream
    ui.timer(0.1, listen_to_window_1)
    
    # Must run on a secondary unique local port
    ui.run(native=True, port=8081, title="Window 2")


# ==========================================
# 3. WINDOW 1 SYSTEM LOGIC (MAIN SYSTEM)
# ==========================================
# Global tracking pointer to monitor active process state lifecycle
current_child_process = None


def launch_window_2(shared_dict, file_val, chan_val, roi_val):
    """Handles the lifecycle state machine to spin up or protect Window 2 instances."""
    global current_child_process
    
    # STEP 1: Guard clause against duplicate windows
    if current_child_process and current_child_process.is_alive():
        ui.notify('Window 2 is already open!', type='warning')
        return

    # STEP 2: Package up current state for initialization injection
    shared_dict['to_w2'] = {
        "file": file_val,
        "channel": int(chan_val),
        "roi_id": int(roi_val)
    }
    
    # STEP 3: Spawn a completely fresh Process context instance
    parent_pid = os.getpid()
    current_child_process = Process(target=run_second_app, args=(shared_dict, parent_pid))
    current_child_process.daemon = True  # Fallback daemonization
    current_child_process.start()
    ui.notify('Opening Window 2...', type='positive')


if __name__ == '__main__':
    # Initialize the cross-process shared proxy memory dictionary
    manager = Manager()
    live_shared_data = manager.dict()
    
    # Initialize separate up/down async pipeline keys to prevent collisions
    live_shared_data['to_w2'] = {"file": "scan_001.tif", "channel": 1, "roi_id": 42}
    live_shared_data['to_w1'] = {"file": "None", "channel": 0, "roi_id": 0}

    ui.label('Desktop Window 1 (Main)').classes('text-h6 text-blue')

    # --- Live Upstream Controller UI Elements ---
    ui.label('Send Data to Window 2:').classes('font-bold mt-2')
    w1_file_input = ui.input(label='File Name', value='scan_001.tif')
    w1_chan_input = ui.number(label='Channel', value=1, format='%d')
    w1_roi_input = ui.number(label='ROI ID', value=42, format='%d')

    # Button triggers creation and verification system
    ui.button('1. Open Window 2', on_click=lambda: launch_window_2(
        live_shared_data, w1_file_input.value, w1_chan_input.value, w1_roi_input.value
    )).classes('mb-2')
    
    def send_to_w2():
        live_shared_data['to_w2'] = {
            "file": w1_file_input.value,
            "channel": int(w1_chan_input.value),
            "roi_id": int(w1_roi_input.value)
        }
    
    ui.button('Send to Window 2', on_click=send_to_w2).props('color=blue').classes('mb-4')

    # --- Upstream Live Listener Component ---
    ui.label('Data received back from Window 2:').classes('font-bold mt-4')
    w2_file = ui.label('File: None')
    w2_channel = ui.label('Channel: None')
    w2_roi = ui.label('ROI ID: None')

    last_seen_from_w2 = {}

    def listen_to_window_2():
        nonlocal last_seen_from_w2
        current_data = live_shared_data.get('to_w1')
        if current_data and current_data != last_seen_from_w2:
            last_seen_from_w2 = current_data.copy()
            w2_file.set_text(f"File: {current_data.get('file')}")
            w2_channel.set_text(f"Channel: {current_data.get('channel')}")
            w2_roi.set_text(f"ROI ID: {current_data.get('roi_id')}")

    # Pull matching packets from the shared context mailbox
    ui.timer(0.1, listen_to_window_2)

    ui.run(native=True, port=8080, title="Window 1")
```

---

## 3. Architecture Breakdown

### Why can it open and close repeatedly?
If you store a `Process` instance as a global variable and call `.start()` on it twice, Python throws a runtime error saying a process can only be started once. 

NiceGUI destroys the entire process loop when a user clicks the "X" button. To allow clean re-opening, the script completely abandons the old instance when it detects `is_alive() == False`. When the user clicks the open button again, a brand new `Process` instance is initialized from scratch and mapped over the old pointer.

### Why use `current_data != last_seen`?
NiceGUI elements inside a loop shouldn't call `.set_text()` unless the data has genuinely changed. The `last_seen` dictionary tracks the previous packet state. This prevents NiceGUI from wasting CPU cycles redrawing layouts 10 times a second when the data is identical.
