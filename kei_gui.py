import tkinter as tk
import os
from PIL import Image, ImageTk, ImageDraw, ImageFilter
from kei_presets import PRESETS

# ── Helpers ───────────────────────────────────────────────────────────────────
def _hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

# ── Palette ───────────────────────────────────────────────────────────────────
BG          = "#2e3440"
HEADER_BG   = "#252a35"
CARD_FILL   = "#c8c8e2"
CARD_HOVER  = "#d8d8ee"
CARD_SEL    = "#ffffff"
ACCENT      = "#e06090"
TEXT_WHITE  = "#eceff4"
TEXT_DIM    = "#7b839c"
TEXT_DARK   = "#2e3440"
BAR_NORMAL  = "#8585b0"
BAR_ACCENT  = "#e06090"

# ── Card dimensions ──────────────────────────────────────────────────────────
CARD_W     = 160
CARD_H     = 126
CARD_R     = 16
SHADOW_PAD = 12          # extra space around card for shadow / glow
IMG_W      = CARD_W + SHADOW_PAD * 2
IMG_H      = CARD_H + SHADOW_PAD * 2
COLS       = 4
FONT       = "Helvetica"


class KeiAudioApp:
    def __init__(self, root, eq_manager):
        self.root = root
        self.eq_manager = eq_manager
        self.current_preset = tk.StringVar(value="OFF")
        self.spatial_audio_var = tk.BooleanVar(value=False)
        self.cards = {}
        self._img_refs = []           # prevent garbage-collection

        root.title("ケイ Audio")
        root.geometry("840x540")
        root.configure(bg=BG)
        root.resizable(False, False)

        self.icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "Design", "Icon.png"
        )

        # Pre-render card images (rounded rects + drop shadows via PIL)
        self._card_imgs = {
            "normal":   self._render_card_image(CARD_FILL),
            "hover":    self._render_card_image(CARD_HOVER),
            "selected": self._render_card_image(CARD_SEL, outline=ACCENT, ow=3,
                                                 glow_color=ACCENT),
        }

        self._set_window_icon()
        self.avatar_img = self._make_circle_avatar(64)
        self._build_ui()

        self.select_preset(PRESETS[0], save=False)

    # ══════════════════════════════════════════════════════════════════════════
    #  PIL rendering
    # ══════════════════════════════════════════════════════════════════════════

    def _render_card_image(self, fill, outline=None, ow=0, glow_color=None):
        """Anti-aliased rounded rectangle with soft drop shadow (or glow)."""
        w, h, r, pad = CARD_W, CARD_H, CARD_R, SHADOW_PAD
        tw, th = IMG_W, IMG_H
        S = 2                                     # supersample factor

        canvas = Image.new("RGBA", (tw * S, th * S), (0, 0, 0, 0))

        # ── Shadow / Glow layer ───────────────────────────────────────────────
        shadow = Image.new("RGBA", (tw * S, th * S), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)

        if glow_color:
            gc = _hex_rgb(glow_color)
            sd.rounded_rectangle(
                (pad * S, pad * S, (pad + w) * S - 1, (pad + h) * S - 1),
                radius=r * S, fill=(*gc, 45)
            )
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10 * S))
        else:
            ox, oy = (pad + 2) * S, (pad + 4) * S     # shadow offset
            sd.rounded_rectangle(
                (ox, oy, ox + w * S - 1, oy + h * S - 1),
                radius=r * S, fill=(0, 0, 0, 50)
            )
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=6 * S))

        canvas = Image.alpha_composite(canvas, shadow)

        # ── Card body ─────────────────────────────────────────────────────────
        draw = ImageDraw.Draw(canvas)
        cx, cy = pad * S, pad * S
        fc = _hex_rgb(fill)

        if outline and ow:
            oc = _hex_rgb(outline)
            draw.rounded_rectangle(
                (cx, cy, cx + w * S - 1, cy + h * S - 1),
                radius=r * S, fill=oc
            )
            ins = ow * S
            draw.rounded_rectangle(
                (cx + ins, cy + ins,
                 cx + w * S - 1 - ins, cy + h * S - 1 - ins),
                radius=max(1, (r - ow) * S), fill=fc
            )
        else:
            draw.rounded_rectangle(
                (cx, cy, cx + w * S - 1, cy + h * S - 1),
                radius=r * S, fill=fc
            )

        canvas = canvas.resize((tw, th), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(canvas)
        self._img_refs.append(photo)
        return photo

    # ── Icon helpers ──────────────────────────────────────────────────────────

    def _set_window_icon(self):
        try:
            ico = tk.PhotoImage(file=self.icon_path)
            self.root.iconphoto(True, ico)
            self._img_refs.append(ico)
        except Exception:
            pass

    def _make_circle_avatar(self, size):
        try:
            img = Image.open(self.icon_path).convert("RGBA")
            s = min(img.size)
            img = img.crop(((img.width - s) // 2, (img.height - s) // 2,
                            (img.width + s) // 2, (img.height + s) // 2))
            img = img.resize((size, size), Image.Resampling.LANCZOS)

            mask = Image.new("L", (size, size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)

            ring = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            rd = ImageDraw.Draw(ring)
            rd.ellipse((0, 0, size - 1, size - 1),
                       outline=(224, 96, 144, 200), width=2)
            rd.ellipse((1, 1, size - 2, size - 2),
                       outline=(224, 96, 144, 80), width=1)

            result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            result.paste(img, mask=mask)
            result = Image.alpha_composite(result, ring)

            photo = ImageTk.PhotoImage(result)
            self._img_refs.append(photo)
            return photo
        except Exception as e:
            print(f"Icon error: {e}")
            return None

    # ══════════════════════════════════════════════════════════════════════════
    #  Layout
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────────
        header = tk.Frame(self.root, bg=HEADER_BG)
        header.pack(fill=tk.X, ipady=14)

        hpad = tk.Frame(header, bg=HEADER_BG)
        hpad.pack(fill=tk.BOTH, expand=True, padx=28)

        if self.avatar_img:
            tk.Label(hpad, image=self.avatar_img, bg=HEADER_BG) \
                .pack(side=tk.LEFT, padx=(0, 14))

        tf = tk.Frame(hpad, bg=HEADER_BG)
        tf.pack(side=tk.LEFT)
        tk.Label(tf, text="ケイ Audio", fg=TEXT_WHITE, bg=HEADER_BG,
                 font=(FONT, 21, "bold")).pack(anchor="w")
        tk.Label(tf, text="By: 神奈川 山田", fg=TEXT_DIM, bg=HEADER_BG,
                 font=(FONT, 10)).pack(anchor="w")

        import kei_main
        
        self.autostart_enabled = kei_main.is_autostart_enabled()
        self.btn_autostart = tk.Label(hpad, text="", bg=HEADER_BG, fg=TEXT_WHITE,
                                      font=(FONT, 10, "bold"), cursor="hand2", padx=12, pady=6)
        
        def update_autostart_btn():
            if self.autostart_enabled:
                self.btn_autostart.config(text="Autostart: ON", fg=ACCENT)
            else:
                self.btn_autostart.config(text="Autostart: OFF", fg=TEXT_DIM)
                
        def on_autostart_click(e):
            self.autostart_enabled = not self.autostart_enabled
            kei_main.set_autostart(self.autostart_enabled)
            update_autostart_btn()
            
        def on_autostart_enter(e):
            self.autostart_enabled = kei_main.is_autostart_enabled()
            update_autostart_btn()
            self.btn_autostart.config(bg=BG)
            
        def on_autostart_leave(e):
            self.btn_autostart.config(bg=HEADER_BG)
            
        self.btn_autostart.bind("<Button-1>", on_autostart_click)
        self.btn_autostart.bind("<Enter>", on_autostart_enter)
        self.btn_autostart.bind("<Leave>", on_autostart_leave)
        update_autostart_btn()
        self.btn_autostart.pack(side=tk.RIGHT, padx=10)

        # ── Accent separator ─────────────────────────────────────────────────
        tk.Frame(self.root, bg=ACCENT, height=2).pack(fill=tk.X)

        # ── Section header ────────────────────────────────────────────────────
        sec = tk.Frame(self.root, bg=BG)
        sec.pack(fill=tk.X, padx=32, pady=(20, 2))

        tk.Label(sec, text="Audio Presets", fg=TEXT_DIM, bg=BG,
                 font=(FONT, 11)).pack(side=tk.LEFT)

        self._active_var = tk.StringVar(value="")
        tk.Label(sec, textvariable=self._active_var, fg=ACCENT, bg=BG,
                 font=(FONT, 10, "bold")).pack(side=tk.RIGHT)

        # ── Card grid ─────────────────────────────────────────────────────────
        grid = tk.Frame(self.root, bg=BG)
        grid.pack(fill=tk.BOTH, expand=True, padx=18, pady=(2, 0))

        for i, preset in enumerate(PRESETS):
            row, col = divmod(i, COLS)
            self._make_card(grid, preset, row, col)
            grid.grid_columnconfigure(col, weight=1, uniform="c")
        grid.grid_rowconfigure(0, weight=1)
        grid.grid_rowconfigure(1, weight=1)

        # ── Status bar ────────────────────────────────────────────────────────
        status = tk.Frame(self.root, bg=HEADER_BG, height=38)
        status.pack(fill=tk.X, side=tk.BOTTOM)
        status.pack_propagate(False)

        self._desc_var = tk.StringVar(value="")
        tk.Label(status, textvariable=self._desc_var, fg=TEXT_DIM, bg=HEADER_BG,
                 font=(FONT, 10), anchor="w", padx=30) \
            .pack(fill=tk.BOTH, expand=True)

    # ── Card factory ──────────────────────────────────────────────────────────

    def _make_card(self, parent, preset, row, col):
        c = tk.Canvas(parent, width=IMG_W, height=IMG_H,
                      bg=BG, highlightthickness=0, cursor="hand2")
        c.grid(row=row, column=col, padx=4, pady=2)

        # rounded-rect background (PIL image with baked-in shadow)
        img_id = c.create_image(IMG_W // 2, IMG_H // 2,
                                image=self._card_imgs["normal"])

        # text origin (center of the card body)
        cx = SHADOW_PAD + CARD_W // 2

        emoji_id = c.create_text(cx, SHADOW_PAD + 38,
                                 text=preset["emoji"],
                                 font=(FONT, 26), fill=TEXT_DARK)

        name_id = c.create_text(cx, SHADOW_PAD + 70,
                                text=preset["displayName"],
                                font=(FONT, 10, "bold"), fill=TEXT_DARK)

        # ── EQ bars (5-band visualisation at bottom of card) ──────────────────
        bands = preset.get("bands", [0, 0, 0, 0, 0])
        bar_ids = []
        bar_w, gap = 8, 6
        total_bw = 5 * bar_w + 4 * gap
        start_x = SHADOW_PAD + (CARD_W - total_bw) // 2
        bar_base = SHADOW_PAD + CARD_H - 16

        for j, gain in enumerate(bands):
            norm = max(0.1, min(1.0, (gain + 300) / 1100))
            bar_h = int(3 + norm * 20)
            bx = start_x + j * (bar_w + gap)
            by = bar_base - bar_h
            bid = c.create_rectangle(bx, by, bx + bar_w, bar_base,
                                     fill=BAR_NORMAL, outline="")
            bar_ids.append(bid)

        self.cards[preset["name"]] = {
            "canvas": c, "img": img_id, "emoji": emoji_id,
            "name": name_id, "bars": bar_ids,
        }

        # ── Hover / Click ─────────────────────────────────────────────────────
        is_toggle = preset.get("isToggle", False)
        def on_enter(e, n=preset["name"], t=is_toggle):
            active = self.spatial_audio_var.get() if t else (self.current_preset.get() == n)
            if not active:
                c.itemconfigure(img_id, image=self._card_imgs["hover"])

        def on_leave(e, n=preset["name"], t=is_toggle):
            active = self.spatial_audio_var.get() if t else (self.current_preset.get() == n)
            if not active:
                c.itemconfigure(img_id, image=self._card_imgs["normal"])

        def on_click(e, p=preset, t=is_toggle):
            if t:
                self.toggle_spatial_audio(not self.spatial_audio_var.get())
            else:
                self.select_preset(p)

        c.bind("<Enter>", on_enter)
        c.bind("<Leave>", on_leave)
        c.bind("<Button-1>", on_click)

    # ══════════════════════════════════════════════════════════════════════════
    #  Selection
    # ══════════════════════════════════════════════════════════════════════════

    def _get_display_name(self, preset=None, spatial_audio=None):
        p = preset or next(pr for pr in PRESETS if pr["name"] == self.current_preset.get())
        s = spatial_audio if spatial_audio is not None else self.spatial_audio_var.get()
        if p["name"] == "OFF" and s:
            return "Spatial"
        return p["displayName"]

    def toggle_spatial_audio(self, enabled):
        self.spatial_audio_var.set(enabled)
        preset = next(p for p in PRESETS if p["name"] == self.current_preset.get())
        self.eq_manager.apply_preset(preset, spatial_audio=enabled)
        self._active_var.set(f"● {self._get_display_name(preset, enabled)}")
        self._refresh_cards(preset["name"])

    def sync_state(self, preset, spatial_audio):
        self.spatial_audio_var.set(spatial_audio)
        self.select_preset(preset, save=False)

    def select_preset(self, preset, save=True):
        name = preset["name"]
        self.current_preset.set(name)
        self._desc_var.set(f"  {preset['description']}")
        self._active_var.set(f"● {self._get_display_name(preset, self.spatial_audio_var.get())}")
        self.eq_manager.apply_preset(preset, spatial_audio=self.spatial_audio_var.get())
        self._refresh_cards(name)

    def _refresh_cards(self, selected):
        for name, refs in self.cards.items():
            c = refs["canvas"]
            
            p = next((pr for pr in PRESETS if pr["name"] == name), None)
            is_toggle = p.get("isToggle", False) if p else False
            
            if is_toggle:
                is_sel = self.spatial_audio_var.get()
            else:
                is_sel = (name == selected)

            c.itemconfigure(refs["img"],
                            image=self._card_imgs["selected" if is_sel else "normal"])
            c.itemconfigure(refs["emoji"],
                            fill=ACCENT if is_sel else TEXT_DARK)

            bar_color = BAR_ACCENT if is_sel else BAR_NORMAL
            for bid in refs["bars"]:
                c.itemconfigure(bid, fill=bar_color)


if __name__ == "__main__":
    from kei_main import main
    main()
