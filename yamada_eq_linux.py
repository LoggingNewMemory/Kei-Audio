#!/usr/bin/env python3
"""
Yamada EQ - Linux Native Port
Copyright (C) 2026 Kanagawa Yamada (Ported to Python/Linux)

This script implements a system-wide equalizer for Linux using PulseAudio/PipeWire
and FFmpeg. It creates a virtual audio sink to intercept system audio, applies
the requested EQ profile (including the multiband compressor and limiter for the
"Smart Tunnel" preset), and routes the processed audio back to your hardware.

Prerequisites:
  sudo apt install ffmpeg python3-tk
  (or equivalent for your distribution)
"""

import tkinter as tk
from tkinter import font
import subprocess
import sys
import atexit
import signal
import threading
import time
import os

# ==========================================
# EQ PRESET MODELS
# ==========================================
PRESETS = [
    {
        "name": "OFF",
        "displayName": "Off",
        "emoji": "✕",
        "description": "Bypass all EQ",
        "bands": [0, 0, 0, 0, 0],
        "loudnessGainMb": 0,
        "smartTunnel": False
    },
    {
        "name": "SMART",
        "displayName": "Smart",
        "emoji": "◈",
        "description": "Dynamic audio tunnel — boosts volume on beat drops and lifts",
        "bands": [200, 100, 0, 100, 150],
        "loudnessGainMb": 600,
        "smartTunnel": True
    },
    {
        "name": "ROCK",
        "displayName": "Rock",
        "emoji": "♟",
        "description": "Punchy bass, scooped mids, crisp highs",
        "bands": [500, 300, -200, 200, 400],
        "loudnessGainMb": 500,
        "smartTunnel": False
    },
    {
        "name": "JAZZ",
        "displayName": "Jazz",
        "emoji": "♫",
        "description": "Warm low-mids, airy top end",
        "bands": [300, 200, 100, 0, 200],
        "loudnessGainMb": 400,
        "smartTunnel": False
    },
    {
        "name": "CLASSIC",
        "displayName": "Classic",
        "emoji": "𝄞",
        "description": "Flat response, natural dynamics",
        "bands": [0, 0, 0, 0, 0],
        "loudnessGainMb": 300,
        "smartTunnel": False
    },
    {
        "name": "POP",
        "displayName": "Pop",
        "emoji": "♪",
        "description": "Boosted vocals & presence, tight bass",
        "bands": [-100, 200, 300, 200, 100],
        "loudnessGainMb": 400,
        "smartTunnel": False
    },
    {
        "name": "BASS",
        "displayName": "Bass",
        "emoji": "◉",
        "description": "Heavy sub & bass boost for earphones",
        "bands": [800, 600, 0, -100, -100],
        "loudnessGainMb": 600,
        "smartTunnel": False
    }
]

# ==========================================
# AUDIO BACKEND MANAGER
# ==========================================
class YamadaEQManager:
    def __init__(self):
        self.ffmpeg_process = None
        self.null_sink_module_id = None
        self.original_default_sink = None
        self.setup_audio()

    def run_cmd(self, cmd):
        try:
            return subprocess.check_output(cmd, shell=True, text=True).strip()
        except subprocess.CalledProcessError:
            return ""

    def setup_audio(self):
        print("Initializing audio subsystem...")
        self.original_default_sink = self.run_cmd("pactl get-default-sink")
        
        # Avoid nesting null sinks
        if "YamadaEQ" in self.original_default_sink:
            print("YamadaEQ is already the default sink. Please reset your audio manually first.")
            sys.exit(1)

        # Load the virtual sink
        out = self.run_cmd('pactl load-module module-null-sink sink_name=YamadaEQ sink_properties=device.description="YamadaEQ"')
        if out.isdigit():
            self.null_sink_module_id = out

        # DO NOT set YamadaEQ as default sink. This ensures volume keys control the physical hardware sink!
        # Instead, we run a background router thread to move app streams to YamadaEQ automatically.
        self._start_audio_router()

    def _start_audio_router(self):
        def router():
            # Initial route
            self._route_streams()
            # Subscribe to changes
            p = subprocess.Popen(["pactl", "subscribe"], stdout=subprocess.PIPE, text=True)
            for line in iter(p.stdout.readline, ''):
                if "on sink-input" in line:
                    self._route_streams()

        self.router_thread = threading.Thread(target=router, daemon=True)
        self.router_thread.start()

    def _route_streams(self):
        if not hasattr(self, 'ffmpeg_process') or self.ffmpeg_process is None:
            return
            
        ff_pid = str(self.ffmpeg_process.pid)
        yamada_sink_id = None
        
        try:
            out = self.run_cmd("pactl list short sinks")
            for line in out.strip().split('\n'):
                if "YamadaEQ" in line:
                    yamada_sink_id = line.split()[0]
                    break
                    
            if not yamada_sink_id:
                return
                
            out = self.run_cmd("pactl list sink-inputs")
            current_input = None
            is_ffmpeg = False
            current_sink = None
            
            for line in out.split('\n'):
                if line.startswith("Sink Input #"):
                    if current_input and not is_ffmpeg and current_sink != yamada_sink_id:
                        subprocess.run(f"pactl move-sink-input {current_input} {yamada_sink_id}", shell=True)
                    current_input = line.split('#')[1]
                    is_ffmpeg = False
                    current_sink = None
                elif "Sink:" in line.strip():
                    current_sink = line.split(":")[1].strip()
                elif f'application.process.id = "{ff_pid}"' in line:
                    is_ffmpeg = True
                    
            if current_input and not is_ffmpeg and current_sink != yamada_sink_id:
                subprocess.run(f"pactl move-sink-input {current_input} {yamada_sink_id}", shell=True)
        except Exception:
            pass

    def cleanup(self):
        print("Cleaning up audio subsystem...")
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            self.ffmpeg_process.wait()
        if self.original_default_sink:
            self.run_cmd(f'pactl set-default-sink {self.original_default_sink}')
        if self.null_sink_module_id:
            self.run_cmd(f'pactl unload-module {self.null_sink_module_id}')

    def apply_preset(self, preset):
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            self.ffmpeg_process.wait()
            
        filters_list = []

        if preset["name"] != "OFF":
            freqs = [60, 230, 910, 3600, 14000]
            
            # 1. Equalizer bands
            for i, gainMb in enumerate(preset["bands"]):
                gain_db = gainMb / 100.0
                if gain_db != 0:
                    filters_list.append(f"equalizer=f={freqs[i]}:width_type=o:width=1:g={gain_db}")

            # 2. Smart Audio Tunnel (DynamicsProcessing)
            if preset.get("smartTunnel", False):
                # Pre-gain
                filters_list.append("volume=5dB")
                # Sophisticated Parallel Compression: 
                # - release=60: Faster recovery prevents audible volume "holes" after loud bass hits
                # - mix=0.85: blends 15% of the dry signal back in for natural punch
                filters_list.append("acompressor=threshold=-20dB:ratio=2.5:attack=2:release=60:makeup=8.5dB:knee=6:mix=0.85")
                # Post-gain lift (reduced to 2dB to avoid pushing the limiter too hard, which causes ducking)
                filters_list.append("volume=2dB")
                # Limiter (Removed asc=1 because Auto Send-Clip acts as an aggressive volume rider that causes noticeable volume drops)
                filters_list.append("alimiter=limit=-0.5dB:attack=2:release=50")
            # 3. Loudness Enhancer fallback
            elif preset.get("loudnessGainMb", 0) > 0:
                gain_db = preset["loudnessGainMb"] / 100.0
                filters_list.append(f"volume={gain_db}dB")
            
            # Universal safety limiter for non-smart presets to prevent digital clipping from EQ boosts
            if not preset.get("smartTunnel", False):
                filters_list.append("alimiter=limit=-0.5dB:attack=2:release=50")

        # Fallback filter to prevent empty graph
        if not filters_list:
            filter_str = "anull"
        else:
            filter_str = ",".join(filters_list)

        # Spawn ffmpeg to process audio from YamadaEQ sink and push it to original sink
        cmd = [
            "ffmpeg", "-nostats", "-loglevel", "error", "-y",
            "-fflags", "nobuffer", "-flags", "low_delay",
            "-f", "pulse", "-i", "YamadaEQ.monitor",
            "-af", filter_str,
            "-f", "pulse", "-device", self.original_default_sink, "pulse"
        ]
        
        self.ffmpeg_process = subprocess.Popen(cmd)
        print(f"Applied Preset: {preset['displayName']}")

# ==========================================
# GUI
# ==========================================
class YamadaEQApp:
    def __init__(self, root, eq_manager):
        self.root = root
        self.eq_manager = eq_manager
        self.current_preset = tk.StringVar(value="OFF")
        
        self.root.title("Yamada EQ")
        self.root.geometry("450x450")
        self.root.configure(bg="#1A1010")
        self.root.resizable(False, False)

        self.setup_ui()
        
        self.state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_preset.txt")
        saved_preset_name = "OFF"
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    saved_preset_name = f.read().strip()
            except Exception:
                pass
                
        initial_preset = PRESETS[0]
        for p in PRESETS:
            if p["name"] == saved_preset_name:
                initial_preset = p
                break
                
        self.select_preset(initial_preset)

    def setup_ui(self):
        # Header
        title = tk.Label(self.root, text="Yamada EQ", fg="#B8355B", bg="#1A1010", 
                         font=("Helvetica", 20, "bold"))
        title.pack(pady=(20, 0))

        self.desc_label = tk.Label(self.root, text=PRESETS[0]["description"], fg="#888888", bg="#1A1010",
                                   font=("Helvetica", 11))
        self.desc_label.pack(pady=(0, 20))

        # Grid container
        grid_frame = tk.Frame(self.root, bg="#1A1010")
        grid_frame.pack(padx=20, fill=tk.BOTH, expand=True)

        self.buttons = {}
        
        # First row (OFF)
        off_preset = PRESETS[0]
        btn = self.create_tile(grid_frame, off_preset)
        btn.grid(row=0, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        self.buttons[off_preset["name"]] = btn

        # Other presets (3 per row)
        other_presets = PRESETS[1:]
        for i, preset in enumerate(other_presets):
            row = 1 + (i // 3)
            col = i % 3
            btn = self.create_tile(grid_frame, preset)
            btn.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
            grid_frame.grid_columnconfigure(col, weight=1)
            self.buttons[preset["name"]] = btn
            
        self.update_selection("OFF")

    def create_tile(self, parent, preset):
        frame = tk.Frame(parent, bg="#251818", highlightbackground="#3A2020", highlightthickness=1, cursor="hand2")
        frame.pack_propagate(False)
        frame.configure(height=90)
        
        lbl_emoji = tk.Label(frame, text=preset["emoji"], fg="white", bg="#251818", font=("Helvetica", 24))
        lbl_emoji.pack(pady=(10, 0))
        
        lbl_name = tk.Label(frame, text=preset["displayName"], fg="white", bg="#251818", font=("Helvetica", 10))
        lbl_name.pack()

        # Bind click events
        def on_click(e, p=preset):
            self.select_preset(p)
            
        frame.bind("<Button-1>", on_click)
        lbl_emoji.bind("<Button-1>", on_click)
        lbl_name.bind("<Button-1>", on_click)
        
        # Store internal references for updating colors
        frame.lbl_emoji = lbl_emoji
        frame.lbl_name = lbl_name
        
        return frame

    def select_preset(self, preset):
        self.current_preset.set(preset["name"])
        self.desc_label.configure(text=preset["description"])
        self.eq_manager.apply_preset(preset)
        self.update_selection(preset["name"])
        
        if hasattr(self, 'state_file'):
            try:
                with open(self.state_file, "w") as f:
                    f.write(preset["name"])
            except Exception:
                pass

    def update_selection(self, selected_name):
        for name, frame in self.buttons.items():
            if name == selected_name:
                frame.configure(bg="#B8355B", highlightbackground="#D4577A")
                frame.lbl_emoji.configure(bg="#B8355B")
                frame.lbl_name.configure(bg="#B8355B", font=("Helvetica", 10, "bold"))
            else:
                frame.configure(bg="#251818", highlightbackground="#3A2020")
                frame.lbl_emoji.configure(bg="#251818")
                frame.lbl_name.configure(bg="#251818", font=("Helvetica", 10, "normal"))

if __name__ == "__main__":
    manager = YamadaEQManager()
    
    def handle_exit(*args):
        manager.cleanup()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    atexit.register(manager.cleanup)

    root = tk.Tk()
    app = YamadaEQApp(root, manager)
    
    # Handle window close button
    root.protocol("WM_DELETE_WINDOW", lambda: handle_exit())
    
    root.mainloop()
