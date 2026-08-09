#!/usr/bin/env python3
"""
Kei Audio - Main Entry Point
"""
import tkinter as tk
import signal
import sys
import atexit
from kei_services import KeiAudioManager
from kei_gui import KeiAudioApp

def main():
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

if __name__ == "__main__":
    main()
