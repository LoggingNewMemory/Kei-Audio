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

import pystray
from PIL import Image

from kei_services import KeiAudioManager
from kei_presets import PRESETS


STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_preset.txt")
SPATIAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spatial_state.txt")
ICON_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Design", "Icon.png")


class KeiTray:
    """System tray backend — always runs regardless of mode."""

    def __init__(self, manager, on_preset_changed=None):
        self.manager = manager
        self.current_preset = PRESETS[0]
        self.spatial_audio = False
        self.tray = None
        self._on_preset_changed = on_preset_changed  # callback for GUI sync

        self._load_saved_preset()
        self.manager.apply_preset(self.current_preset, spatial_audio=self.spatial_audio)

    # ── State persistence ─────────────────────────────────────────────────────
    def _load_saved_preset(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE) as f:
                    name = f.read().strip()
                for p in PRESETS:
                    if p["name"] == name:
                        self.current_preset = p
                        return
            except Exception:
                pass
        if os.path.exists(SPATIAL_FILE):
            try:
                with open(SPATIAL_FILE) as f:
                    self.spatial_audio = f.read().strip() == "1"
            except Exception:
                pass

    def _save_preset(self):
        try:
            with open(STATE_FILE, "w") as f:
                f.write(self.current_preset["name"])
        except Exception:
            pass
        try:
            with open(SPATIAL_FILE, "w") as f:
                f.write("1" if self.spatial_audio else "0")
        except Exception:
            pass

    # ── Preset switching (called from tray menu) ──────────────────────────────
    def _select_preset(self, preset):
        def action(icon, item):
            self.select_preset(preset)
        return action

    def select_preset(self, preset):
        """Public method — can be called by tray menu or GUI."""
        self.current_preset = preset
        self.manager.apply_preset(preset, spatial_audio=self.spatial_audio)
        self._save_preset()
        if self.tray:
            self.tray.title = f"ケイ Audio — {preset['displayName']}"
            self.tray.update_menu()
        if self._on_preset_changed:
            self._on_preset_changed(preset, self.spatial_audio)

    def _toggle_spatial(self, icon, item):
        self.set_spatial_audio(not self.spatial_audio)
        
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
    def quit(self, icon=None, item=None):
        self.manager.cleanup()
        if self.tray:
            self.tray.stop()

    # ── Build menu ────────────────────────────────────────────────────────────
    def _build_menu(self):
        items = []
        for p in PRESETS:
            items.append(
                pystray.MenuItem(
                    f"{p['emoji']}  {p['displayName']}",
                    self._select_preset(p),
                    checked=self._is_selected(p),
                    radio=True
                )
            )
        items.append(pystray.Menu.SEPARATOR)
        items.append(
            pystray.MenuItem(
                "🎧  Spatial Audio",
                self._toggle_spatial,
                checked=lambda item: self.spatial_audio
            )
        )
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("Quit", self.quit))
        return pystray.Menu(*items)

    # ── Run (blocks on current thread) ────────────────────────────────────────
    def run(self):
        icon_image = Image.open(ICON_PATH).convert("RGBA")
        self.tray = pystray.Icon(
            name="kei-audio",
            icon=icon_image,
            title=f"ケイ Audio — {self.current_preset['displayName']}",
            menu=self._build_menu()
        )
        self.tray.run()

    def run_detached(self):
        """Start tray in a background thread (for GUI mode)."""
        threading.Thread(target=self.run, daemon=True).start()


def main():
    tray_only = "--tray" in sys.argv

    manager = KeiAudioManager()

    def handle_signal(*args):
        manager.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    atexit.register(manager.cleanup)

    if tray_only:
        # ── Tray-only mode (autostart) ────────────────────────────────────────
        app = KeiTray(manager)
        print(f"ケイ Audio running in system tray (Preset: {app.current_preset['displayName']})")
        app.run()
    else:
        # ── GUI + Tray mode (manual launch) ───────────────────────────────────
        import tkinter as tk
        from kei_gui import KeiAudioApp

        root = tk.Tk()
        gui = KeiAudioApp(root, manager)

        # Wire tray ↔ GUI: tray preset changes update the GUI
        def on_tray_state_changed(preset, spatial_audio):
            root.after(0, lambda: gui.sync_state(preset, spatial_audio))

        tray = KeiTray(manager, on_preset_changed=on_tray_state_changed)

        # Wire GUI → tray: GUI preset changes update the tray
        original_select = gui.select_preset
        def gui_select_wrapper(preset, save=True):
            original_select(preset, save=save)
            tray.current_preset = preset
            if tray.tray:
                tray.tray.title = f"ケイ Audio — {preset['displayName']}"
                tray.tray.update_menu()
        gui.select_preset = gui_select_wrapper
        
        # Wire GUI → tray: GUI spatial audio toggle updates the tray
        original_toggle_spatial = gui.toggle_spatial_audio
        def gui_toggle_spatial_wrapper(enabled):
            original_toggle_spatial(enabled)
            tray.spatial_audio = enabled
            if tray.tray:
                tray.tray.update_menu()
        gui.toggle_spatial_audio = gui_toggle_spatial_wrapper

        # Restore saved preset into GUI
        gui.sync_state(tray.current_preset, tray.spatial_audio)

        tray.run_detached()

        root.protocol("WM_DELETE_WINDOW", lambda: (tray.quit(), sys.exit(0)))
        root.mainloop()


if __name__ == "__main__":
    main()
