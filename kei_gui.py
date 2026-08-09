import tkinter as tk
import os
from PIL import Image, ImageTk, ImageDraw
from kei_presets import PRESETS

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
        self.icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Design", "Icon.png")
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
        
        # Avatar and Window Icon
        self.avatar_img = self.create_circle_icon(size=70)
        if self.avatar_img:
            avatar_lbl = tk.Label(header_frame, image=self.avatar_img, bg=self.bg_color)
            avatar_lbl.pack(side=tk.LEFT, padx=(0, 15))
            try:
                # Set the window taskbar icon
                icon_img = tk.PhotoImage(file=self.icon_path)
                self.root.iconphoto(True, icon_img)
            except Exception:
                pass
            
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
    from kei_main import main
    main()
