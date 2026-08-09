import subprocess
import threading
import time
import sys

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
            
        if not self.ffmpeg_pids:
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

    def _force_ffmpeg_volume(self, proc):
        def task():
            for _ in range(20):
                time.sleep(0.1)
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
                        subprocess.run(f"pactl set-sink-input-volume {sink_input} 100%", shell=True, stderr=subprocess.DEVNULL)
                        break
                except Exception:
                    pass
        threading.Thread(target=task, daemon=True).start()

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
        
        self._force_ffmpeg_volume(self.ffmpeg_process)
        
        # Now safely fade out and kill the old process
        if old_process:
            self._fade_and_kill(old_process)
            
        print(f"Applied Preset: {preset['displayName']}")
