import tkinter as tk
import os
from PIL import Image, ImageTk, ImageDraw
from kei_presets import PRESETS

# ── Color Palette (dark navy + lavender cards + pink accent from icon) ────────
BG          = "#2e3440"
HEADER_BG   = "#262b36"
CARD_FILL   = "#c5c5e0"
CARD_HOVER  = "#d6d6ee"
CARD_SEL    = "#ffffff"
ACCENT      = "#e06090"   # pink-magenta from the icon
ACCENT_DIM  = "#c05080"
TEXT_WHITE  = "#eceff4"
TEXT_DIM    = "#7b839c"
TEXT_DARK   = "#2e3440"

# ── Card geometry ─────────────────────────────────────────────────────────────
CARD_W  = 152
CARD_H  = 112
CARD_R  = 16
COLS    = 4
FONT    = "Helvetica"


class KeiAudioApp:
    def __init__(self, root, eq_manager):
        self.root = root
        self.eq_manager = eq_manager
        self.current_preset = tk.StringVar(value="OFF")
        self.cards = {}
        self._img_refs = []  # prevent garbage collection

        root.title("ケイ Audio")
        root.geometry("780x500")
        root.configure(bg=BG)
        root.resizable(False, False)

        self.icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "Design", "Icon.png"
        )

        # Pre-render card background images (PIL anti-aliased rounded rects)
        self._card_normal = self._render_rounded_rect(CARD_W, CARD_H, CARD_R, CARD_FILL)
        self._card_hover  = self._render_rounded_rect(CARD_W, CARD_H, CARD_R, CARD_HOVER)
        self._card_sel    = self._render_rounded_rect(CARD_W, CARD_H, CARD_R, CARD_SEL, ACCENT, 3)

        self._set_window_icon()
        self.avatar_img = self._make_circle_avatar(64)
        self._build_ui()

        # ── Restore last saved preset ─────────────────────────────────────────
        self.state_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "last_preset.txt"
        )
        saved = "OFF"
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file) as f:
                    saved = f.read().strip()
            except Exception:
                pass
        initial = next((p for p in PRESETS if p["name"] == saved), PRESETS[0])
        self.select_preset(initial, save=False)

    # ══════════════════════════════════════════════════════════════════════════
    #  Image helpers
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _hex_rgb(h):
        return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

    def _render_rounded_rect(self, w, h, r, fill, outline=None, ow=0):
        """PIL-rendered rounded rectangle at 2× for anti-aliased edges."""
        s = 2  # supersampling factor
        img = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        fc = self._hex_rgb(fill)

        if outline and ow:
            oc = self._hex_rgb(outline)
            draw.rounded_rectangle((0, 0, w * s - 1, h * s - 1),
                                   radius=r * s, fill=oc)
            inset = ow * s
            draw.rounded_rectangle((inset, inset,
                                    w * s - 1 - inset, h * s - 1 - inset),
                                   radius=max(1, (r - ow) * s), fill=fc)
        else:
            draw.rounded_rectangle((0, 0, w * s - 1, h * s - 1),
                                   radius=r * s, fill=fc)

        img = img.resize((w, h), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self._img_refs.append(photo)
        return photo

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

            # circular mask
            mask = Image.new("L", (size, size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)

            # subtle pink ring (2 passes for soft glow)
            ring = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            rd = ImageDraw.Draw(ring)
            rd.ellipse((0, 0, size - 1, size - 1),
                       outline=(224, 96, 144, 200), width=2)
            rd.ellipse((1, 1, size - 2, size - 2),
                       outline=(224, 96, 144, 90), width=1)

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
        # ── Header bar ────────────────────────────────────────────────────────
        header = tk.Frame(self.root, bg=HEADER_BG)
        header.pack(fill=tk.X, ipady=14)

        hpad = tk.Frame(header, bg=HEADER_BG)
        hpad.pack(fill=tk.BOTH, expand=True, padx=28)

        if self.avatar_img:
            tk.Label(hpad, image=self.avatar_img, bg=HEADER_BG).pack(
                side=tk.LEFT, padx=(0, 14))

        tf = tk.Frame(hpad, bg=HEADER_BG)
        tf.pack(side=tk.LEFT)
        tk.Label(tf, text="ケイ Audio", fg=TEXT_WHITE, bg=HEADER_BG,
                 font=(FONT, 21, "bold")).pack(anchor="w")
        tk.Label(tf, text="By: 神奈川 山田", fg=TEXT_DIM, bg=HEADER_BG,
                 font=(FONT, 10)).pack(anchor="w")

        # ── Accent separator ─────────────────────────────────────────────────
        tk.Frame(self.root, bg=ACCENT, height=2).pack(fill=tk.X)

        # ── Section label row ─────────────────────────────────────────────────
        sec = tk.Frame(self.root, bg=BG)
        sec.pack(fill=tk.X, padx=30, pady=(20, 4))

        tk.Label(sec, text="Audio Presets", fg=TEXT_DIM, bg=BG,
                 font=(FONT, 11)).pack(side=tk.LEFT)

        self._active_var = tk.StringVar(value="")
        tk.Label(sec, textvariable=self._active_var, fg=ACCENT, bg=BG,
                 font=(FONT, 10, "bold")).pack(side=tk.RIGHT)

        # ── Preset card grid ─────────────────────────────────────────────────
        grid = tk.Frame(self.root, bg=BG)
        grid.pack(fill=tk.BOTH, expand=True, padx=24, pady=(6, 0))

        for i, preset in enumerate(PRESETS):
            row, col = divmod(i, COLS)
            self._make_card(grid, preset, row, col)
            grid.grid_columnconfigure(col, weight=1, uniform="c")
        grid.grid_rowconfigure(0, weight=1)
        grid.grid_rowconfigure(1, weight=1)

        # ── Bottom status bar ─────────────────────────────────────────────────
        status = tk.Frame(self.root, bg=HEADER_BG, height=38)
        status.pack(fill=tk.X, side=tk.BOTTOM)
        status.pack_propagate(False)

        self._desc_var = tk.StringVar(value="")
        tk.Label(status, textvariable=self._desc_var, fg=TEXT_DIM, bg=HEADER_BG,
                 font=(FONT, 10), anchor="w", padx=30).pack(
            fill=tk.BOTH, expand=True)

    # ── Card factory ──────────────────────────────────────────────────────────

    def _make_card(self, parent, preset, row, col):
        c = tk.Canvas(parent, width=CARD_W, height=CARD_H,
                      bg=BG, highlightthickness=0, cursor="hand2")
        c.grid(row=row, column=col, padx=10, pady=8)

        # background image (rounded rect)
        img_id = c.create_image(CARD_W // 2, CARD_H // 2,
                                image=self._card_normal)
        # emoji
        emoji_id = c.create_text(CARD_W // 2, CARD_H // 2 - 14,
                                 text=preset["emoji"],
                                 font=(FONT, 24), fill=TEXT_DARK)
        # label
        name_id = c.create_text(CARD_W // 2, CARD_H // 2 + 22,
                                text=preset["displayName"],
                                font=(FONT, 10, "bold"), fill=TEXT_DARK)

        self.cards[preset["name"]] = {
            "canvas": c, "img": img_id, "emoji": emoji_id, "name": name_id
        }

        # hover / click
        def on_enter(e, n=preset["name"]):
            if self.current_preset.get() != n:
                c.itemconfigure(img_id, image=self._card_hover)

        def on_leave(e, n=preset["name"]):
            if self.current_preset.get() != n:
                c.itemconfigure(img_id, image=self._card_normal)

        def on_click(e, p=preset):
            self.select_preset(p)

        c.bind("<Enter>", on_enter)
        c.bind("<Leave>", on_leave)
        c.bind("<Button-1>", on_click)

    # ══════════════════════════════════════════════════════════════════════════
    #  Selection logic
    # ══════════════════════════════════════════════════════════════════════════

    def select_preset(self, preset, save=True):
        name = preset["name"]
        self.current_preset.set(name)
        self._desc_var.set(f"  {preset['description']}")
        self._active_var.set(f"● {preset['displayName']}")
        self.eq_manager.apply_preset(preset)
        self._refresh_cards(name)

        if save and hasattr(self, "state_file"):
            try:
                with open(self.state_file, "w") as f:
                    f.write(name)
            except Exception:
                pass

    def _refresh_cards(self, selected):
        for name, refs in self.cards.items():
            c = refs["canvas"]
            if name == selected:
                c.itemconfigure(refs["img"], image=self._card_sel)
                c.itemconfigure(refs["emoji"], fill=ACCENT)
                c.itemconfigure(refs["name"], fill=TEXT_DARK)
            else:
                c.itemconfigure(refs["img"], image=self._card_normal)
                c.itemconfigure(refs["emoji"], fill=TEXT_DARK)
                c.itemconfigure(refs["name"], fill=TEXT_DARK)


if __name__ == "__main__":
    from kei_main import main
    main()
