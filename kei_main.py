#!/usr/bin/env python3
"""
Kei Audio — Main Entry Point
  python3 kei_main.py          → UI window + system tray
  python3 kei_main.py --tray   → system tray only (used by autostart)
"""
import signal
import sys
import os
import atexit
import threading
import socket

import pystray
from PIL import Image

from kei_services import KeiAudioManager
from kei_presets import PRESETS


def get_base_path():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()
CONFIG_DIR = os.path.expanduser("~/.config/kei-audio")
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(CONFIG_DIR, "KeiConfig.txt")
ICON_PATH  = os.path.join(BASE_PATH, "Design", "Icon.png")
AUTOSTART_FILE = os.path.expanduser("~/.config/autostart/kei-audio.desktop")

def is_autostart_enabled():
    return os.path.exists(AUTOSTART_FILE)

def set_autostart(enabled):
    if enabled:
        os.makedirs(os.path.dirname(AUTOSTART_FILE), exist_ok=True)
        if getattr(sys, 'frozen', False):
            exec_cmd = f"{sys.executable} --tray"
        else:
            exec_cmd = f"{sys.executable} {os.path.abspath(__file__)} --tray"
        desktop_entry = f"""[Desktop Entry]
Type=Application
Name=ケイ Audio
Comment=System-wide audio equalizer and enhancer
Exec={exec_cmd}
Icon={ICON_PATH}
Terminal=false
Categories=Audio;AudioVideo;
StartupNotify=false
X-GNOME-Autostart-enabled=true
"""
        with open(AUTOSTART_FILE, "w") as f:
            f.write(desktop_entry)
    else:
        if os.path.exists(AUTOSTART_FILE):
            os.remove(AUTOSTART_FILE)



class KeiTray:
    """System tray backend — always runs regardless of mode."""

    def __init__(self, manager, on_preset_changed=None, on_show_window=None, on_quit=None):
        self.manager = manager
        self.current_preset = PRESETS[0]
        self.spatial_audio = False
        self.tray = None
        self._on_preset_changed = on_preset_changed  # callback for GUI sync
        self._on_show_window = on_show_window
        self._on_quit = on_quit

        self._load_saved_preset()
        self.manager.apply_preset(self.current_preset, spatial_audio=self.spatial_audio)
        self._save_preset()

    # ── State persistence ─────────────────────────────────────────────────────
    def _load_saved_preset(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE) as f:
                    for line in f:
                        if line.startswith("LAST_PRESET="):
                            name = line.strip().split("=")[1]
                            for p in PRESETS:
                                if p["name"] == name:
                                    self.current_preset = p
                        elif line.startswith("SPATIAL="):
                            self.spatial_audio = (line.strip().split("=")[1] == "1")
            except Exception:
                pass

    def _save_preset(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                f.write(f"LAST_PRESET={self.current_preset['name']}\n")
                f.write(f"SPATIAL={'1' if self.spatial_audio else '0'}\n")
        except Exception:
            pass

    # ── Preset switching (called from tray menu) ──────────────────────────────
    def _select_preset(self, preset):
        def action(icon, item):
            self.select_preset(preset)
        return action

    def _get_display_name(self, preset=None, spatial_audio=None):
        p = preset or self.current_preset
        s = spatial_audio if spatial_audio is not None else self.spatial_audio
        if p["name"] == "OFF" and s:
            return "Spatial"
        return p["displayName"]

    def select_preset(self, preset):
        """Public method — can be called by tray menu or GUI."""
        self.current_preset = preset
        self.manager.apply_preset(preset, spatial_audio=self.spatial_audio)
        self._save_preset()
        if self.tray:
            self.tray.title = f"ケイ Audio — {self._get_display_name()}"
            self.tray.update_menu()
        if self._on_preset_changed:
            self._on_preset_changed(preset, self.spatial_audio)

    def _toggle_spatial(self, icon, item):
        self.set_spatial_audio(not self.spatial_audio)

    def _toggle_autostart(self, icon, item):
        set_autostart(not is_autostart_enabled())
        
    def set_spatial_audio(self, enabled):
        """Public method — can be called by tray menu or GUI."""
        self.spatial_audio = enabled
        self.manager.apply_preset(self.current_preset, spatial_audio=self.spatial_audio)
        self._save_preset()
        if self.tray:
            self.tray.update_menu()
        if self._on_preset_changed:
            self._on_preset_changed(self.current_preset, self.spatial_audio)

    def _is_selected(self, preset):
        def check(item):
            return self.current_preset["name"] == preset["name"]
        return check

    # ── Quit ──────────────────────────────────────────────────────────────────
    # ── Actions ───────────────────────────────────────────────────────────────
    def _show_window_action(self, icon, item):
        if self._on_show_window:
            self._on_show_window()

    def quit(self, icon=None, item=None):
        self.manager.cleanup()
        if self.tray:
            self.tray.stop()
        if self._on_quit:
            self._on_quit()

    # ── Build menu ────────────────────────────────────────────────────────────
    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem("Show Window", self._show_window_action),
            pystray.MenuItem("Quit", self.quit)
        )

    # ── Run (blocks on current thread) ────────────────────────────────────────
    def run(self):
        icon_image = Image.open(ICON_PATH).convert("RGBA")
        self.tray = pystray.Icon(
            name="kei-audio",
            icon=icon_image,
            title=f"Kei Audio - {self._get_display_name()}",
            menu=self._build_menu()
        )
        self.tray.run()

    def run_detached(self):
        """Start tray in a background thread (for GUI mode)."""
        threading.Thread(target=self.run, daemon=True).start()


def main():
    SOCKET_PATH = "/tmp/kei-audio.sock"
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(SOCKET_PATH)
        s.send(b"SHOW")
        s.close()
        print("An instance is already running. Requesting it to show the window.")
        sys.exit(0)
    except Exception:
        pass

    if os.path.exists(SOCKET_PATH):
        os.remove(SOCKET_PATH)

    tray_only = "--tray" in sys.argv

    manager = KeiAudioManager()

    import tkinter as tk
    from kei_gui import KeiAudioApp

    root = tk.Tk()
    if tray_only:
        root.withdraw()

    def socket_listener():
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(SOCKET_PATH)
        server.listen(1)
        while True:
            try:
                conn, _ = server.accept()
                data = conn.recv(1024)
                if data == b"SHOW":
                    root.after(0, lambda: (root.deiconify(), root.lift(), root.focus_force()))
                conn.close()
            except Exception:
                break

    listener_thread = threading.Thread(target=socket_listener, daemon=True)
    listener_thread.start()

    def cleanup():
        manager.cleanup()
        if os.path.exists(SOCKET_PATH):
            try:
                os.remove(SOCKET_PATH)
            except:
                pass

    def handle_signal(*args):
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    atexit.register(cleanup)

    gui = KeiAudioApp(root, manager)

    def on_tray_state_changed(preset, spatial_audio):
        root.after(0, lambda: gui.sync_state(preset, spatial_audio))
        
    def on_show_window():
        root.after(0, lambda: (root.deiconify(), root.lift(), root.focus_force()))
        
    def on_quit():
        root.after(0, root.quit)

    tray = KeiTray(manager, on_preset_changed=on_tray_state_changed, 
                   on_show_window=on_show_window, on_quit=on_quit)

    original_select = gui.select_preset
    def gui_select_wrapper(preset, save=True):
        original_select(preset, save=save)
        tray.current_preset = preset
        tray._save_preset()
        if tray.tray:
            tray.tray.title = f"ケイ Audio — {tray._get_display_name()}"
            tray.tray.update_menu()
    gui.select_preset = gui_select_wrapper
    
    original_toggle_spatial = gui.toggle_spatial_audio
    def gui_toggle_spatial_wrapper(enabled):
        original_toggle_spatial(enabled)
        tray.spatial_audio = enabled
        tray._save_preset()
        if tray.tray:
            tray.tray.title = f"ケイ Audio — {tray._get_display_name()}"
            tray.tray.update_menu()
    gui.toggle_spatial_audio = gui_toggle_spatial_wrapper

    gui.sync_state(tray.current_preset, tray.spatial_audio)
    tray.run_detached()

    root.protocol("WM_DELETE_WINDOW", lambda: root.withdraw())
    root.mainloop()

if __name__ == "__main__":
    main()
