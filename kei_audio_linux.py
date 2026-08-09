#!/usr/bin/env python3
"""
Kei Audio - Linux Native Port
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
from PIL import Image, ImageTk, ImageDraw

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
class KeiAudioManager:
    def __init__(self):
        self.ffmpeg_process = None
        self.ffmpeg_pids = set()
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
        if "KeiAudio" in self.original_default_sink:
            print("KeiAudio is already the default sink. Please reset your audio manually first.")
            sys.exit(1)

        # Load the virtual sink
        out = self.run_cmd('pactl load-module module-null-sink sink_name=KeiAudio sink_properties=device.description="KeiAudio"')
        if out.isdigit():
            self.null_sink_module_id = out

        # DO NOT set KeiAudio as default sink. This ensures volume keys control the physical hardware sink!
        # Instead, we run a background router thread to move app streams to KeiAudio automatically.
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
        if getattr(self, 'is_cleaning_up', False):
            return
            
        kei_sink_id = None
        
        try:
            out = self.run_cmd("pactl list short sinks")
            for line in out.strip().split('\n'):
                if "KeiAudio" in line:
                    kei_sink_id = line.split()[0]
                    break
                    
            if not kei_sink_id:
                return
                
            out = self.run_cmd("pactl list sink-inputs")
            current_input = None
            is_ffmpeg = False
            current_sink = None
            
            for line in out.split('\n'):
                if line.startswith("Sink Input #"):
                    if current_input and not is_ffmpeg and current_sink != kei_sink_id:
                        subprocess.run(f"pactl move-sink-input {current_input} {kei_sink_id}", shell=True)
                    current_input = line.split('#')[1]
                    is_ffmpeg = False
                    current_sink = None
                elif "Sink:" in line.strip():
                    current_sink = line.split(":")[1].strip()
                elif "application.process.id = " in line:
                    try:
                        pid_str = line.split('"')[1]
                        if pid_str in self.ffmpeg_pids:
                            is_ffmpeg = True
                    except IndexError:
                        pass
                    
            if current_input and not is_ffmpeg and current_sink != kei_sink_id:
                subprocess.run(f"pactl move-sink-input {current_input} {kei_sink_id}", shell=True)
        except Exception:
            pass

    def cleanup(self):
        if getattr(self, 'is_cleaning_up', False):
            return
        self.is_cleaning_up = True
        print("Cleaning up audio subsystem...")
        
        # Restore all active audio streams to the original hardware sink before shutting down
        if self.original_default_sink:
            try:
                out = self.run_cmd("pactl list short sink-inputs")
                for line in out.strip().split('\n'):
                    if line:
                        input_id = line.split()[0]
                        subprocess.run(f"pactl move-sink-input {input_id} {self.original_default_sink}", shell=True, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            self.ffmpeg_process.wait()
        if self.original_default_sink:
            self.run_cmd(f'pactl set-default-sink {self.original_default_sink}')
        if self.null_sink_module_id:
            self.run_cmd(f'pactl unload-module {self.null_sink_module_id}')

    def _fade_and_kill(self, proc):
        if not proc:
            return
        def task():
            try:
                out = self.run_cmd("pactl list sink-inputs")
                sink_input = None
                current_input = None
                for line in out.split('\n'):
                    if line.startswith("Sink Input #"):
                        current_input = line.split('#')[1]
                    elif f'application.process.id = "{proc.pid}"' in line:
                        sink_input = current_input
                        break
                
                if sink_input:
                    # Fade out over ~500ms
                    for i in range(20, -1, -1):
                        vol = int((i / 20.0) * 100)
                        subprocess.run(f"pactl set-sink-input-volume {sink_input} {vol}%", shell=True, stderr=subprocess.DEVNULL)
                        time.sleep(0.025)
            except Exception:
                pass
            finally:
                try:
                    proc.terminate()
                    proc.wait(timeout=1)
                except Exception:
                    proc.kill()
                # Clean up pid from set
                pid_str = str(proc.pid)
                if pid_str in self.ffmpeg_pids:
                    self.ffmpeg_pids.remove(pid_str)

        threading.Thread(target=task, daemon=True).start()

    def apply_preset(self, preset):
        old_process = self.ffmpeg_process
        self.ffmpeg_process = None
        
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

        # Add fade in for smooth transition
        filters_list.append("afade=t=in:d=0.5")

        # Fallback filter to prevent empty graph
        if not filters_list:
            filter_str = "afade=t=in:d=0.5"
        else:
            filter_str = ",".join(filters_list)

        # Spawn ffmpeg to process audio from KeiAudio sink and push it to original sink
        cmd = [
            "ffmpeg", "-nostats", "-loglevel", "error", "-y",
            "-fflags", "nobuffer", "-flags", "low_delay",
            "-f", "pulse", "-i", "KeiAudio.monitor",
            "-af", filter_str,
            "-f", "pulse", "-device", self.original_default_sink, "pulse"
        ]
        
        self.ffmpeg_process = subprocess.Popen(cmd)
        self.ffmpeg_pids.add(str(self.ffmpeg_process.pid))
        
        # Now safely fade out and kill the old process
        if old_process:
            self._fade_and_kill(old_process)
            
        print(f"Applied Preset: {preset['displayName']}")

# ==========================================
# GUI
# ==========================================
class KeiAudioApp:
    def __init__(self, root, eq_manager):
        self.root = root
        self.eq_manager = eq_manager
        self.current_preset = tk.StringVar(value="OFF")
        
        self.root.title("ケイ Audio")
        self.root.geometry("750x450")
        self.bg_color = "#3b4252"
        self.tile_color = "#d8d8eb"
        self.tile_sel_color = "#ffffff"
        self.text_color = "#ffffff"
        self.tile_text_color = "#3b4252"
        self.root.configure(bg=self.bg_color)
        self.root.resizable(False, False)
        
        # Ensure icon exists
        self.icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Design", "Key IMG", "Kei_Icon.png")
        self.avatar_img = None
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

    def create_circle_icon(self, size=80):
        try:
            img = Image.open(self.icon_path).convert("RGBA")
            # Crop to square first
            min_dim = min(img.width, img.height)
            left = (img.width - min_dim) / 2
            top = (img.height - min_dim) / 2
            right = (img.width + min_dim) / 2
            bottom = (img.height + min_dim) / 2
            img = img.crop((left, top, right, bottom))
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            
            # Create a circular mask
            mask = Image.new("L", (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)
            
            # Apply mask
            circular_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            circular_img.paste(img, (0, 0), mask)
            
            return ImageTk.PhotoImage(circular_img)
        except Exception as e:
            print(f"Could not load icon: {e}")
            return None

    def setup_ui(self):
        # Header Frame
        header_frame = tk.Frame(self.root, bg=self.bg_color)
        header_frame.pack(fill=tk.X, padx=30, pady=(20, 10))
        
        # Avatar
        self.avatar_img = self.create_circle_icon(size=70)
        if self.avatar_img:
            avatar_lbl = tk.Label(header_frame, image=self.avatar_img, bg=self.bg_color)
            avatar_lbl.pack(side=tk.LEFT, padx=(0, 15))
            
        # Title Texts
        title_text_frame = tk.Frame(header_frame, bg=self.bg_color)
        title_text_frame.pack(side=tk.LEFT, fill=tk.Y, pady=5)
        
        title_lbl = tk.Label(title_text_frame, text="ケイ Audio", fg=self.text_color, bg=self.bg_color, 
                             font=("Helvetica", 24, "bold"))
        title_lbl.pack(anchor="w")
        
        author_lbl = tk.Label(title_text_frame, text="By: 神奈川 山田", fg="#d8dee9", bg=self.bg_color, 
                              font=("Helvetica", 12))
        author_lbl.pack(anchor="w")
        
        # Mid Section
        mid_frame = tk.Frame(self.root, bg=self.bg_color)
        mid_frame.pack(fill=tk.X, pady=(5, 5))
        
        presets_lbl = tk.Label(mid_frame, text="Audio Presets", fg=self.text_color, bg=self.bg_color,
                               font=("Helvetica", 18))
        presets_lbl.pack()

        self.desc_label = tk.Label(self.root, text=PRESETS[0]["description"], fg="#e5e9f0", bg=self.bg_color,
                                   font=("Helvetica", 11))
        self.desc_label.pack(pady=(5, 10))

        # Grid container
        grid_frame = tk.Frame(self.root, bg=self.bg_color)
        grid_frame.pack(padx=30, fill=tk.BOTH, expand=True)

        self.buttons = {}
        
        for i, preset in enumerate(PRESETS):
            # Layout 4 items in first row, 3 in second
            row = i // 4
            col = i % 4
            btn = self.create_tile(grid_frame, preset)
            btn.grid(row=row, column=col, sticky="nsew", padx=10, pady=10)
            grid_frame.grid_columnconfigure(col, weight=1)
            self.buttons[preset["name"]] = btn
            
        self.update_selection("OFF")

    def create_tile(self, parent, preset):
        frame = tk.Frame(parent, bg=self.tile_color, cursor="hand2")
        frame.pack_propagate(False)
        frame.configure(height=110)
        
        lbl_emoji = tk.Label(frame, text=preset["emoji"], fg=self.tile_text_color, bg=self.tile_color, font=("Helvetica", 28))
        lbl_emoji.pack(pady=(15, 0))
        
        lbl_name = tk.Label(frame, text=preset["displayName"], fg=self.tile_text_color, bg=self.tile_color, font=("Helvetica", 11, "bold"))
        lbl_name.pack(pady=(5, 0))

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
                frame.configure(bg=self.tile_sel_color, highlightbackground="#4F86F7", highlightthickness=2)
                frame.lbl_emoji.configure(bg=self.tile_sel_color)
                frame.lbl_name.configure(bg=self.tile_sel_color)
            else:
                frame.configure(bg=self.tile_color, highlightbackground=self.tile_color, highlightthickness=2)
                frame.lbl_emoji.configure(bg=self.tile_color)
                frame.lbl_name.configure(bg=self.tile_color)

if __name__ == "__main__":
    manager = KeiAudioManager()
    
    def handle_exit(*args):
        manager.cleanup()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    atexit.register(manager.cleanup)

    root = tk.Tk()
    app = KeiAudioApp(root, manager)
    
    # Handle window close button
    root.protocol("WM_DELETE_WINDOW", lambda: handle_exit())
    
    root.mainloop()
