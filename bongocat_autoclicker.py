#!/usr/bin/env python3
import ctypes
from ctypes import wintypes
import math
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import font as tkFont

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("bongocat.autoclicker.v1")
except Exception:
    pass

try:
    from PIL import Image, ImageDraw, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
winmm = ctypes.windll.winmm

VK_F8 = 0x77
VK_F10 = 0x79

PIPE_ACCESS_DUPLEX = 0x00000003
PIPE_TYPE_BYTE = 0x00000000
PIPE_READMODE_BYTE = 0x00000000
PIPE_WAIT = 0x00000000
INVALID_HANDLE_VALUE = -1

MAX_INT32_CAP = 2_147_483_646
FONT_FAMILY = "Bahnschrift"

def parse_taps_input(raw: str) -> int:
    s = raw.strip().lower().replace(",", "").replace(" ", "").replace("_", "")
    if not s:
        return 1000
    if s == "max":
        return MAX_INT32_CAP
    mult = 1
    if s.endswith("k"):
        mult = 1_000
        s = s[:-1]
    elif s.endswith("m"):
        mult = 1_000_000
        s = s[:-1]
    elif s.endswith("b"):
        mult = 1_000_000_000
        s = s[:-1]

    try:
        val = int(float(s) * mult)
        return max(1, min(MAX_INT32_CAP, val))
    except (ValueError, OverflowError):
        return 1000

PRESETS = {
    "1k": {
        "title": "1,000",
        "badge": "~11k CPS",
        "taps_per_tick": 1_000,
    },
    "100k": {
        "title": "100,000",
        "badge": "~1.1M CPS",
        "taps_per_tick": 100_000,
    },
    "1m": {
        "title": "1,000,000",
        "badge": "~11.1M CPS",
        "taps_per_tick": 1_000_000,
    },
    "100m": {
        "title": "100,000,000",
        "badge": "~1.1B CPS",
        "taps_per_tick": 100_000_000,
    },
    "max": {
        "title": "MAX",
        "badge": "2.14B / tap",
        "taps_per_tick": MAX_INT32_CAP,
    },
}

def format_duration(seconds: float) -> str:
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

def render_rounded_box(width: int, height: int, radius: int, fill: str, outline: str = None, outline_width: int = 1):
    if not HAS_PIL or width <= 0 or height <= 0:
        return None
    scale = 2
    im = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle(
        (0, 0, width * scale - 1, height * scale - 1),
        radius=radius * scale,
        fill=fill,
        outline=outline,
        width=outline_width * scale,
    )
    return ImageTk.PhotoImage(im.resize((width, height), Image.Resampling.LANCZOS))

class BongoDirectIPC:
    def __init__(self, pipe_name=r"\\.\pipe\BongoCatxTheFarmerWasReplaced"):
        self.pipe_name = pipe_name
        self.h_pipe = None
        self.connected = False
        self._lock = threading.Lock()

    def listen(self):
        with self._lock:
            if self.h_pipe:
                try:
                    kernel32.DisconnectNamedPipe(self.h_pipe)
                    kernel32.CloseHandle(self.h_pipe)
                except Exception:
                    pass
                self.h_pipe = None
                self.connected = False

            self.h_pipe = kernel32.CreateNamedPipeW(
                self.pipe_name,
                PIPE_ACCESS_DUPLEX,
                PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
                1,
                4096,
                4096,
                1000,
                None,
            )

            if self.h_pipe == INVALID_HANDLE_VALUE or self.h_pipe == 0xFFFFFFFFFFFFFFFF:
                self.h_pipe = None
                return False

        res = kernel32.ConnectNamedPipe(self.h_pipe, None)
        err = kernel32.GetLastError()
        if res or err == 535:
            with self._lock:
                self.connected = True
            return True
        else:
            with self._lock:
                self.connected = False
            return False

    def send_taps(self, count: int) -> bool:
        with self._lock:
            if not self.connected or not self.h_pipe:
                return False

            text = str(count)
            raw = text.encode("utf-16le")
            length = len(raw)
            packet = bytes([length // 256, length & 255]) + raw
            written = wintypes.DWORD()
            success = kernel32.WriteFile(self.h_pipe, packet, len(packet), ctypes.byref(written), None)
            if not success:
                self.connected = False
                return False
            return True

    def close(self):
        with self._lock:
            if self.h_pipe:
                try:
                    kernel32.DisconnectNamedPipe(self.h_pipe)
                    kernel32.CloseHandle(self.h_pipe)
                except Exception:
                    pass
                self.h_pipe = None
                self.connected = False

class ClickerEngine:
    def __init__(self, preset_key="1k"):
        self.ipc = BongoDirectIPC()
        self.preset_key = preset_key
        self.taps_per_tick = PRESETS[preset_key]["taps_per_tick"]
        self.tick_interval_ms = 90

        self.running = False
        self.shutdown_requested = False
        self.total_clicks = 0
        self.active_duration = 0.0
        self.last_state_change = time.perf_counter()
        self.ipc_status_text = "Waiting..."
        self.target_pid = None

    def set_preset(self, preset_key: str):
        self.preset_key = preset_key
        self.taps_per_tick = PRESETS.get(preset_key, PRESETS["1k"])["taps_per_tick"]

    def set_custom_taps(self, taps: int):
        self.taps_per_tick = max(1, min(MAX_INT32_CAP, int(taps)))

    def toggle(self):
        now = time.perf_counter()
        if self.running:
            self.running = False
            self.active_duration += now - self.last_state_change
        else:
            self.running = True
            self.last_state_change = now

    def shutdown(self):
        self.shutdown_requested = True
        self.running = False
        self.ipc.close()

    def pipe_worker(self):
        while not self.shutdown_requested:
            if not self.ipc.connected:
                self.ipc_status_text = "Waiting..."
                if self.ipc.listen():
                    self.ipc_status_text = "Connected"
                else:
                    time.sleep(0.5)
            else:
                time.sleep(0.2)

    def run_loop(self):
        while not self.shutdown_requested:
            if self.running and self.ipc.connected:
                batch = self.taps_per_tick
                if self.ipc.send_taps(batch):
                    self.total_clicks += batch
                else:
                    self.ipc_status_text = "Reconnecting..."
                time.sleep(self.tick_interval_ms / 1000.0)
            else:
                time.sleep(0.040)

def hotkey_listener(engine: ClickerEngine):
    last_f8 = False
    last_f10 = False
    while not engine.shutdown_requested:
        f8_down = bool(user32.GetAsyncKeyState(VK_F8) & 0x8000)
        if f8_down and not last_f8:
            engine.toggle()
        last_f8 = f8_down

        f10_down = bool(user32.GetAsyncKeyState(VK_F10) & 0x8000)
        if f10_down and not last_f10:
            engine.shutdown()
            break
        last_f10 = f10_down

        time.sleep(0.005)

class LogSlider(tk.Canvas):
    def __init__(self, parent, min_val=1, max_val=MAX_INT32_CAP, initial_val=100, on_change=None, **kwargs):
        super().__init__(parent, height=26, bg="#FFFFFF", highlightthickness=0, **kwargs)
        self.min_val = min_val
        self.max_val = max_val
        self.log_min = math.log10(max(1, min_val))
        self.log_max = math.log10(max_val)
        self.on_change = on_change
        self.current_val = initial_val
        self.padding = 14
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Button-1>", self.on_interact)
        self.bind("<B1-Motion>", self.on_interact)

    def val_to_pos(self, val):
        lv = math.log10(max(self.min_val, min(self.max_val, val)))
        return (lv - self.log_min) / (self.log_max - self.log_min)

    def pos_to_val(self, pos):
        lv = self.log_min + pos * (self.log_max - self.log_min)
        return max(self.min_val, min(self.max_val, int(round(10 ** lv))))

    def set_val(self, val):
        self.current_val = max(self.min_val, min(self.max_val, int(val)))
        self.draw()

    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        if w < 50:
            return
        track_w = w - 2 * self.padding
        pos = self.val_to_pos(self.current_val)
        tx = self.padding + pos * track_w
        cy = 13
        self.create_line(self.padding, cy, w - self.padding, cy, fill="#E2E8F0", width=6, capstyle=tk.ROUND)
        if tx > self.padding:
            self.create_line(self.padding, cy, tx, cy, fill="#3B82F6", width=6, capstyle=tk.ROUND)
        r = 8
        self.create_oval(tx - r, cy - r, tx + r, cy + r, fill="#FFFFFF", outline="#2563EB", width=2)

    def on_interact(self, event):
        w = self.winfo_width()
        track_w = max(1, w - 2 * self.padding)
        pos = min(1.0, max(0.0, (event.x - self.padding) / track_w))
        new_val = self.pos_to_val(pos)
        self.current_val = new_val
        self.draw()
        if self.on_change:
            self.on_change(new_val)

class RoundedStatCard:
    def __init__(self, parent, title: str, initial_val: str, accent_color: str, width: int = 154, height: int = 66, radius: int = 10):
        self.width = width
        self.height = height
        self.accent_color = accent_color
        self.bg_photo = render_rounded_box(width, height, radius, "#FFFFFF", outline="#E2E8F0", outline_width=1)

        self.canvas = tk.Canvas(parent, width=width, height=height, bg="#F8FAFC", highlightthickness=0)
        if self.bg_photo:
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.bg_photo)
        else:
            self.canvas.configure(bg="#FFFFFF", highlightthickness=1, highlightbackground="#E2E8F0")

        self.title_id = self.canvas.create_text(width // 2, 18, text=title, font=(FONT_FAMILY, 8, "bold"), fill=accent_color)
        self.val_id = self.canvas.create_text(width // 2, 42, text=initial_val, font=(FONT_FAMILY, 14, "bold"), fill="#0F172A")

    def pack(self, **kwargs):
        self.canvas.pack(**kwargs)

    def set_value(self, val_str: str):
        if len(val_str) > 13:
            font = (FONT_FAMILY, 9, "bold")
        elif len(val_str) > 9:
            font = (FONT_FAMILY, 11, "bold")
        else:
            font = (FONT_FAMILY, 14, "bold")
        self.canvas.itemconfig(self.val_id, text=val_str, font=font)

class BongoApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Bongo Cat Auto Clicker")
        self.root.geometry("520x480")
        self.root.resizable(False, False)
        self.root.configure(bg="#F8FAFC")

        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        ico_path = os.path.join(assets_dir, "bongo.ico")
        png_path = os.path.join(assets_dir, "bongo_icon.png")
        if os.path.exists(ico_path):
            try:
                self.root.iconbitmap(ico_path)
            except Exception:
                pass
        if HAS_PIL and os.path.exists(png_path):
            try:
                self.app_icon = ImageTk.PhotoImage(Image.open(png_path).resize((64, 64), Image.Resampling.LANCZOS))
                self.root.iconphoto(True, self.app_icon)
            except Exception:
                pass

        winmm.timeBeginPeriod(1)
        self.engine = ClickerEngine(preset_key="1k")

        self.pipe_thread = threading.Thread(target=self.engine.pipe_worker, daemon=True)
        self.pipe_thread.start()

        self.click_thread = threading.Thread(target=self.engine.run_loop, daemon=True)
        self.click_thread.start()

        self.hotkey_thread = threading.Thread(target=hotkey_listener, args=(self.engine,), daemon=True)
        self.hotkey_thread.start()

        self.show_settings = False
        self.build_ui()
        self.update_loop()

    def build_ui(self):
        # 1. Header Banner
        banner_loaded = False
        banner_path = os.path.join(os.path.dirname(__file__), "assets", "banner.png")

        if HAS_PIL and os.path.exists(banner_path):
            try:
                im = Image.open(banner_path)
                im_crop = im.crop((0, 0, im.width, 292))
                w = 520
                h = int(im_crop.height * (w / im_crop.width))
                im_res = im_crop.resize((w, h), Image.Resampling.LANCZOS)
                self.banner_photo = ImageTk.PhotoImage(im_res)
                self.lbl_banner = tk.Label(self.root, image=self.banner_photo, bd=0, highlightthickness=0)
                self.lbl_banner.pack(fill=tk.X, side=tk.TOP)
                banner_loaded = True
            except Exception:
                banner_loaded = False

        if not banner_loaded:
            self.lbl_banner = tk.Canvas(self.root, width=520, height=120, bg="#F43F5E", highlightthickness=0)
            self.lbl_banner.pack(fill=tk.X, side=tk.TOP)
            self.lbl_banner.create_text(260, 60, text="🐾 Bongo Cat Auto Clicker 🐾", font=(FONT_FAMILY, 20, "bold"), fill="#FFFFFF")

        # 2. Main Content
        self.content = tk.Frame(self.root, bg="#F8FAFC")
        self.content.pack(fill=tk.BOTH, expand=True, padx=18, pady=(12, 16))

        # Status Bar Row
        status_bar = tk.Frame(self.content, bg="#F8FAFC")
        status_bar.pack(fill=tk.X, pady=(0, 10))

        status_left = tk.Frame(status_bar, bg="#F8FAFC")
        status_left.pack(side=tk.LEFT)

        self.status_dot = tk.Label(status_left, text="●", font=(FONT_FAMILY, 10), fg="#94A3B8", bg="#F8FAFC")
        self.status_dot.pack(side=tk.LEFT, padx=(0, 5))

        self.status_text = tk.Label(
            status_left,
            text="CONNECTING...",
            font=(FONT_FAMILY, 9, "bold"),
            fg="#64748B",
            bg="#F8FAFC",
        )
        self.status_text.pack(side=tk.LEFT)

        self.lbl_preset_tag = tk.Label(
            status_bar,
            text="~11k CPS",
            font=(FONT_FAMILY, 8, "bold"),
            fg="#0F172A",
            bg="#FFFFFF",
            padx=8,
            pady=2,
            bd=0,
            highlightthickness=1,
            highlightbackground="#E2E8F0",
        )
        self.lbl_preset_tag.pack(side=tk.RIGHT)

        # 3. Stat Cards Row
        stats_frame = tk.Frame(self.content, bg="#F8FAFC")
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        self.card_clicks = RoundedStatCard(stats_frame, "TOTAL CLICKS", "0", "#E11D48", width=156, height=66)
        self.card_clicks.pack(side=tk.LEFT, padx=(0, 4))

        self.card_cps = RoundedStatCard(stats_frame, "CURRENT CPS", "0 CPS", "#2563EB", width=156, height=66)
        self.card_cps.pack(side=tk.LEFT, padx=2)

        self.card_time = RoundedStatCard(stats_frame, "TIME ACTIVE", "00:00", "#7C3AED", width=156, height=66)
        self.card_time.pack(side=tk.LEFT, padx=(4, 0))

        # 4. Primary Big Action Button
        self.img_btn_active = render_rounded_box(484, 44, 12, "#10B981")
        self.img_btn_paused = render_rounded_box(484, 44, 12, "#EF4444")

        self.btn_toggle = tk.Button(
            self.content,
            text="▶  START FARMING  (F8)",
            font=(FONT_FAMILY, 11, "bold"),
            fg="#FFFFFF",
            bg="#F8FAFC",
            activebackground="#F8FAFC",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            image=self.img_btn_paused,
            compound=tk.CENTER,
            command=self.engine.toggle,
        )
        self.btn_toggle.pack(fill=tk.X, pady=(0, 10))

        # 5. Quick Controls Row
        ctrl_bar = tk.Frame(self.content, bg="#F8FAFC")
        ctrl_bar.pack(fill=tk.X)

        self.btn_settings = tk.Button(
            ctrl_bar,
            text="⚙️  Speed Settings",
            font=(FONT_FAMILY, 8, "bold"),
            bg="#FFFFFF",
            fg="#334155",
            activebackground="#F1F5F9",
            activeforeground="#0F172A",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground="#CBD5E1",
            cursor="hand2",
            padx=12,
            pady=4,
            command=self.toggle_settings_panel,
        )
        self.btn_settings.pack(side=tk.LEFT)

        self.top_var = tk.BooleanVar(value=False)
        self.chk_top = tk.Checkbutton(
            ctrl_bar,
            text="📌 Always on Top",
            variable=self.top_var,
            font=(FONT_FAMILY, 8, "bold"),
            fg="#64748B",
            bg="#F8FAFC",
            activebackground="#F8FAFC",
            command=self.update_always_on_top,
        )
        self.chk_top.pack(side=tk.RIGHT)

        # 6. Settings Panel
        self.build_settings_panel()

    def build_settings_panel(self):
        self.settings_frame = tk.Frame(self.content, bg="#FFFFFF", highlightbackground="#CBD5E1", highlightthickness=1, bd=0)

        hdr = tk.Frame(self.settings_frame, bg="#F1F5F9", padx=12, pady=6)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="SPEED & BATCH SETTINGS", font=(FONT_FAMILY, 8, "bold"), fg="#475569", bg="#F1F5F9").pack(side=tk.LEFT)

        inner = tk.Frame(self.settings_frame, bg="#FFFFFF", padx=14, pady=10)
        inner.pack(fill=tk.BOTH, expand=True)

        # Speed Presets Bar
        presets_bar = tk.Frame(inner, bg="#FFFFFF")
        presets_bar.pack(fill=tk.X, pady=(0, 8))

        self.preset_buttons = {}
        for key in ["1k", "100k", "1m", "100m", "max"]:
            cfg = PRESETS[key]
            btn = tk.Button(
                presets_bar,
                text=f"{cfg['title']}\n{cfg['badge']}",
                font=(FONT_FAMILY, 8, "bold"),
                relief=tk.FLAT,
                bd=0,
                cursor="hand2",
                pady=4,
                command=lambda k=key: self.select_preset(k),
            )
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            self.preset_buttons[key] = btn

        # Batch Size Entry Row
        taps_row = tk.Frame(inner, bg="#FFFFFF")
        taps_row.pack(fill=tk.X, pady=(2, 6))

        tk.Label(taps_row, text="Batch size:", font=(FONT_FAMILY, 8, "bold"), fg="#334155", bg="#FFFFFF").pack(side=tk.LEFT)

        self.entry_taps = tk.Entry(
            taps_row, width=16, font=(FONT_FAMILY, 9, "bold"), justify=tk.CENTER,
            bg="#FFFFFF", fg="#0F172A", insertbackground="#0F172A", bd=0,
            highlightthickness=1, highlightbackground="#CBD5E1", highlightcolor="#2563EB"
        )
        self.entry_taps.insert(0, f"{self.engine.taps_per_tick:,}")
        self.entry_taps.pack(side=tk.LEFT, padx=(8, 4))
        self.entry_taps.bind("<Return>", self.on_entry_taps_submit)
        self.entry_taps.bind("<FocusOut>", self.on_entry_taps_submit)

        self.lbl_calculated_cps = tk.Label(taps_row, text="", font=(FONT_FAMILY, 8, "bold"), fg="#059669", bg="#FFFFFF")
        self.lbl_calculated_cps.pack(side=tk.RIGHT)

        # Smooth Logarithmic Slider
        slider_frame = tk.Frame(inner, bg="#FFFFFF")
        slider_frame.pack(fill=tk.X, pady=(2, 4))
        self.log_slider = LogSlider(slider_frame, initial_val=self.engine.taps_per_tick, on_change=self.on_slider_change)
        self.log_slider.pack(fill=tk.X)

        self.update_preset_buttons_ui()

    def select_preset(self, preset_key):
        self.engine.set_preset(preset_key)
        val = self.engine.taps_per_tick
        self.set_batch_value(val)

    def set_batch_value(self, val: int):
        val = max(1, min(MAX_INT32_CAP, int(val)))
        self.engine.set_custom_taps(val)
        self.entry_taps.delete(0, tk.END)
        self.entry_taps.insert(0, f"{val:,}")
        self.log_slider.set_val(val)
        self.update_preset_buttons_ui()

    def update_preset_buttons_ui(self):
        cur_taps = self.engine.taps_per_tick
        for key, btn in self.preset_buttons.items():
            if PRESETS[key]["taps_per_tick"] == cur_taps:
                btn.configure(bg="#2563EB", fg="#FFFFFF", activebackground="#1D4ED8", activeforeground="#FFFFFF", highlightthickness=0)
            else:
                btn.configure(bg="#F8FAFC", fg="#475569", activebackground="#E2E8F0", activeforeground="#0F172A", highlightthickness=1, highlightbackground="#E2E8F0")

        cps = int(self.engine.taps_per_tick / (self.engine.tick_interval_ms / 1000.0))
        if self.engine.taps_per_tick == MAX_INT32_CAP:
            cps_str = "2.14B / tap"
            desc_str = "2,147,483,646 taps per tick (BongoCat hard game cap)."
        elif cps >= 1_000_000_000:
            cps_str = f"~{cps / 1_000_000_000:.2f}B CPS"
            desc_str = f"{self.engine.taps_per_tick:,} clicks per {self.engine.tick_interval_ms}ms ({cps_str})."
        elif cps >= 1_000_000:
            cps_str = f"~{cps / 1_000_000:.2f}M CPS"
            desc_str = f"{self.engine.taps_per_tick:,} clicks per {self.engine.tick_interval_ms}ms ({cps_str})."
        elif cps >= 10_000:
            cps_str = f"~{cps / 1_000:.1f}k CPS"
            desc_str = f"{self.engine.taps_per_tick:,} clicks per {self.engine.tick_interval_ms}ms ({cps_str})."
        else:
            cps_str = f"~{cps:,} CPS"
            desc_str = f"{self.engine.taps_per_tick:,} clicks per {self.engine.tick_interval_ms}ms ({cps_str})."

        self.lbl_calculated_cps.configure(text=f"≈ {cps_str}")
        self.lbl_preset_tag.configure(text=cps_str)

    def on_slider_change(self, val):
        self.engine.set_custom_taps(val)
        self.entry_taps.delete(0, tk.END)
        self.entry_taps.insert(0, f"{val:,}")
        self.update_preset_buttons_ui()

    def on_entry_taps_submit(self, event=None):
        raw = self.entry_taps.get().strip()
        val = parse_taps_input(raw)
        self.set_batch_value(val)

    def toggle_settings_panel(self):
        self.show_settings = not self.show_settings
        if self.show_settings:
            self.settings_frame.pack(fill=tk.X, pady=(10, 0))
            self.root.geometry("520x665")
            self.btn_settings.configure(text="▲  Close Settings", bg="#E2E8F0")
        else:
            self.settings_frame.pack_forget()
            self.root.geometry("520x480")
            self.btn_settings.configure(text="⚙️  Speed Settings", bg="#FFFFFF")

    def update_always_on_top(self):
        self.root.attributes("-topmost", self.top_var.get())

    def update_loop(self):
        if self.engine.shutdown_requested:
            self.root.destroy()
            return

        now = time.perf_counter()
        active_time = self.engine.active_duration
        if self.engine.running:
            active_time += now - self.engine.last_state_change

        actual_cps = 0.0
        if active_time > 0 and self.engine.running:
            actual_cps = self.engine.total_clicks / active_time

        # Update Primary Button & Status Bar
        if self.engine.running:
            self.btn_toggle.configure(text="⏸  PAUSE FARMING  (F8)", image=self.img_btn_active)
            self.status_dot.configure(fg="#10B981")
            self.status_text.configure(text="ACTIVE", fg="#059669")
        else:
            self.btn_toggle.configure(text="▶  START FARMING  (F8)", image=self.img_btn_paused)
            if self.engine.ipc.connected:
                self.status_dot.configure(fg="#3B82F6")
                self.status_text.configure(text="READY", fg="#2563EB")
            else:
                self.status_dot.configure(fg="#F59E0B")
                self.status_text.configure(text="CONNECTING...", fg="#D97706")

        # Update Stats Cards
        clicks_str = f"{self.engine.total_clicks:,}"
        self.card_clicks.set_value(clicks_str)

        if not self.engine.running:
            self.card_cps.set_value("0 CPS")
        elif actual_cps >= 1_000_000_000:
            self.card_cps.set_value(f"{actual_cps / 1_000_000_000:.2f}B CPS")
        elif actual_cps >= 1_000_000:
            self.card_cps.set_value(f"{actual_cps / 1_000_000:.2f}M CPS")
        elif actual_cps >= 10_000:
            self.card_cps.set_value(f"{actual_cps / 1_000:.1f}k CPS")
        else:
            self.card_cps.set_value(f"{int(actual_cps):,} CPS")

        self.card_time.set_value(format_duration(active_time))

        self.root.after(35, self.update_loop)

    def on_close(self):
        self.engine.shutdown()
        winmm.timeEndPeriod(1)
        self.root.destroy()

def run_gui():
    root = tk.Tk()
    app = BongoApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

def run_cli():
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11)
    mode = wintypes.DWORD()
    if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)

    winmm.timeBeginPeriod(1)
    engine = ClickerEngine(preset_key="1k")

    pipe_thread = threading.Thread(target=engine.pipe_worker, daemon=True)
    pipe_thread.start()

    click_thread = threading.Thread(target=engine.run_loop, daemon=True)
    click_thread.start()

    hotkey_thread = threading.Thread(target=hotkey_listener, args=(engine,), daemon=True)
    hotkey_thread.start()

    print("=" * 66)
    print("           Bongo Cat Auto Clicker (CLI Mode)")
    print("=" * 66)
    print(" Controls:")
    print("   [F8]  - Start / Pause")
    print("   [F10] - Quit program")
    print("=" * 66)
    print(" Ready. Connecting to BongoCat named pipe...\n")

    try:
        while not engine.shutdown_requested:
            time.sleep(0.25)
            now = time.perf_counter()
            active_time = engine.active_duration
            if engine.running:
                active_time += now - engine.last_state_change

            actual_cps = (engine.total_clicks / active_time) if active_time > 0 else 0.0
            status_color = "\033[92m[ACTIVE]\033[0m" if engine.running else "\033[93m[PAUSED]\033[0m"
            print(
                f"\rStatus: {status_color:<18} "
                f"Clicks: \033[96m{engine.total_clicks:,}\033[0m  "
                f"CPS: \033[95m{int(actual_cps):,}\033[0m  "
                f"Time: {format_duration(active_time)}   ",
                end="",
                flush=True,
            )
    except KeyboardInterrupt:
        pass
    finally:
        engine.shutdown()
        winmm.timeEndPeriod(1)
        print("\nClean exit.")

def main():
    if "--cli" in sys.argv or "--headless" in sys.argv:
        run_cli()
    else:
        run_gui()

if __name__ == "__main__":
    main()
