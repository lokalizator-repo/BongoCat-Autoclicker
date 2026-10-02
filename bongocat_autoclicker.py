#!/usr/bin/env python3
import ctypes
from ctypes import wintypes
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

# Enable Per-Monitor High-DPI awareness on Windows to prevent blurry rendering
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

try:
    from PIL import Image, ImageTk
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

PRESETS = {
    "overdrive": {
        "title": "Overdrive",
        "badge": "1,111 CPS",
        "taps_per_tick": 100,
        "desc": "Direct memory pipe injection (100 taps / 90ms). Zero Windows keystrokes, zero YouTube interruptions, 100% click registration.",
    },
    "turbo": {
        "title": "Turbo",
        "badge": "555 CPS",
        "taps_per_tick": 50,
        "desc": "Moderate direct injection (50 taps / 90ms). Balanced rate with minimal memory traffic.",
    },
    "stealth": {
        "title": "Stealth",
        "badge": "277 CPS",
        "taps_per_tick": 25,
        "desc": "Low-profile injection (25 taps / 90ms). Ultra-smooth background progression.",
    },
}

def format_duration(seconds: float) -> str:
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

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
                None
            )

            if self.h_pipe == INVALID_HANDLE_VALUE or self.h_pipe == 0xFFFFFFFFFFFFFFFF:
                self.h_pipe = None
                return False

        # Wait for BongoCat client to connect
        res = kernel32.ConnectNamedPipe(self.h_pipe, None)
        err = kernel32.GetLastError()
        if res or err == 535: # ERROR_PIPE_CONNECTED
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
            raw = text.encode('utf-16le')
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
    def __init__(self, preset_key="overdrive"):
        self.ipc = BongoDirectIPC()
        self.preset_key = preset_key
        self.taps_per_tick = PRESETS[preset_key]["taps_per_tick"]
        self.tick_interval = 0.090 # 90ms matches BongoCat's internal IPC thread

        self.running = False
        self.shutdown_requested = False
        self.total_clicks = 0
        self.active_duration = 0.0
        self.last_state_change = time.perf_counter()
        self.ipc_status_text = "Connecting to BongoCat..."

    def set_preset(self, preset_key: str):
        self.preset_key = preset_key
        self.taps_per_tick = PRESETS.get(preset_key, PRESETS["overdrive"])["taps_per_tick"]

    def set_custom_taps(self, taps: int):
        self.taps_per_tick = max(1, min(500, int(taps)))

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
                self.ipc_status_text = "Waiting for BongoCat..."
                if self.ipc.listen():
                    self.ipc_status_text = "Connected (Direct IPC Active)"
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
                    self.ipc_status_text = "Reconnecting to BongoCat..."
                time.sleep(self.tick_interval)
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

class BongoApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Bongo Cat Turbo Clicker (Direct IPC)")
        self.root.geometry("520x540")
        self.root.resizable(False, False)
        self.root.configure(bg="#FFF9F5")

        winmm.timeBeginPeriod(1)
        self.engine = ClickerEngine(preset_key="overdrive")

        # Worker threads
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
        # 1. Authentic Header Banner
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
            self.lbl_banner = tk.Canvas(self.root, width=520, height=120, bg="#E77471", highlightthickness=0)
            self.lbl_banner.pack(fill=tk.X, side=tk.TOP)
            self.lbl_banner.create_text(260, 60, text="🐾 Bongo Cat Turbo Clicker 🐾", font=("Segoe UI", 20, "bold"), fill="#FFFFFF")

        # 2. Main Content
        self.content = tk.Frame(self.root, bg="#FFF9F5")
        self.content.pack(fill=tk.BOTH, expand=True, padx=20, pady=(12, 16))

        # Status Badge Row
        status_bar = tk.Frame(self.content, bg="#FFF9F5")
        status_bar.pack(fill=tk.X, pady=(0, 10))

        self.status_dot = tk.Label(status_bar, text="●", font=("Segoe UI", 12), fg="#A0AEC0", bg="#FFF9F5")
        self.status_dot.pack(side=tk.LEFT, padx=(0, 6))

        self.status_text = tk.Label(
            status_bar,
            text="Connecting to BongoCat...",
            font=("Segoe UI", 9, "bold"),
            fg="#4A5568",
            bg="#FFF9F5",
        )
        self.status_text.pack(side=tk.LEFT)

        self.lbl_preset_tag = tk.Label(
            status_bar,
            text="Direct IPC (1,111 CPS)",
            font=("Segoe UI", 8, "bold"),
            fg="#2B6CB0",
            bg="#EBF8FF",
            padx=8,
            pady=2,
            bd=1,
            relief=tk.SOLID,
        )
        self.lbl_preset_tag.pack(side=tk.RIGHT)

        # 3. Stat Cards Row
        stats_frame = tk.Frame(self.content, bg="#FFF9F5")
        stats_frame.pack(fill=tk.X, pady=(0, 12))

        self.card_clicks = self.create_stat_card(stats_frame, "🐾 TOTAL CLICKS", "0", "#E05D52")
        self.card_clicks.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        self.card_cps = self.create_stat_card(stats_frame, "⚡ CURRENT CPS", "0 CPS", "#3182CE")
        self.card_cps.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)

        self.card_time = self.create_stat_card(stats_frame, "⏱️ TIME ACTIVE", "00:00", "#805AD5")
        self.card_time.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        # 4. Primary Big Action Button
        self.btn_toggle = tk.Button(
            self.content,
            text="▶  START FARMING  (F8)",
            font=("Segoe UI", 12, "bold"),
            bg="#FF6B6B",
            fg="#FFFFFF",
            activebackground="#FA5252",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            pady=11,
            command=self.engine.toggle,
        )
        self.btn_toggle.pack(fill=tk.X, pady=(0, 10))

        # 5. Quick Controls Row
        ctrl_bar = tk.Frame(self.content, bg="#FFF9F5")
        ctrl_bar.pack(fill=tk.X)

        self.btn_settings = tk.Button(
            ctrl_bar,
            text="⚙️  Speed & Settings",
            font=("Segoe UI", 9, "bold"),
            bg="#EDF2F7",
            fg="#2D3748",
            activebackground="#E2E8F0",
            activeforeground="#1A202C",
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=5,
            command=self.toggle_settings_panel,
        )
        self.btn_settings.pack(side=tk.LEFT)

        self.top_var = tk.BooleanVar(value=False)
        self.chk_top = tk.Checkbutton(
            ctrl_bar,
            text="📌 Always on Top",
            variable=self.top_var,
            font=("Segoe UI", 9, "bold"),
            fg="#4A5568",
            bg="#FFF9F5",
            activebackground="#FFF9F5",
            command=self.update_always_on_top,
        )
        self.chk_top.pack(side=tk.RIGHT)

        # 6. Settings Panel
        self.build_settings_panel()

    def create_stat_card(self, parent, title, initial_val, color):
        frame = tk.Frame(parent, bg="#FFFFFF", bd=1, relief=tk.SOLID)
        lbl_title = tk.Label(frame, text=title, font=("Segoe UI", 8, "bold"), fg=color, bg="#FFFFFF")
        lbl_title.pack(anchor=tk.CENTER, pady=(8, 0))
        lbl_val = tk.Label(frame, text=initial_val, font=("Segoe UI", 14, "bold"), fg="#1A202C", bg="#FFFFFF")
        lbl_val.pack(anchor=tk.CENTER, pady=(0, 8))
        frame.val_label = lbl_val
        return frame

    def build_settings_panel(self):
        self.settings_frame = tk.Frame(self.content, bg="#FFFFFF", bd=1, relief=tk.SOLID)

        # Header
        hdr = tk.Frame(self.settings_frame, bg="#F7FAFC", padx=12, pady=8)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="⚙️ DIRECT IPC SPEED & CALIBRATION", font=("Segoe UI", 9, "bold"), fg="#2D3748", bg="#F7FAFC").pack(side=tk.LEFT)

        inner = tk.Frame(self.settings_frame, bg="#FFFFFF", padx=14, pady=10)
        inner.pack(fill=tk.BOTH, expand=True)

        # Preset selection
        tk.Label(inner, text="Select Speed Preset:", font=("Segoe UI", 9, "bold"), fg="#2D3748", bg="#FFFFFF").pack(anchor=tk.W, pady=(0, 6))

        presets_bar = tk.Frame(inner, bg="#FFFFFF")
        presets_bar.pack(fill=tk.X, pady=(0, 8))

        self.preset_buttons = {}
        for key in ["overdrive", "turbo", "stealth"]:
            cfg = PRESETS[key]
            btn = tk.Button(
                presets_bar,
                text=f"{cfg['title']} ({cfg['badge']})",
                font=("Segoe UI", 9, "bold"),
                relief=tk.FLAT,
                cursor="hand2",
                pady=6,
                command=lambda k=key: self.select_preset(k),
            )
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            self.preset_buttons[key] = btn

        # Dynamic Description Card
        self.card_desc = tk.Frame(inner, bg="#F8FAFC", bd=1, relief=tk.SOLID, padx=10, pady=8)
        self.card_desc.pack(fill=tk.X, pady=(0, 10))

        self.lbl_desc_speed = tk.Label(self.card_desc, text="", font=("Segoe UI", 9, "bold"), fg="#3182CE", bg="#F8FAFC")
        self.lbl_desc_speed.pack(anchor=tk.W)

        self.lbl_desc_body = tk.Label(self.card_desc, text="", font=("Segoe UI", 8), fg="#4A5568", bg="#F8FAFC", wraplength=440, justify=tk.LEFT)
        self.lbl_desc_body.pack(anchor=tk.W, pady=(2, 0))

        # Direct Taps Input & Slider
        taps_row = tk.Frame(inner, bg="#FFFFFF")
        taps_row.pack(fill=tk.X, pady=(0, 4))

        tk.Label(taps_row, text="Clicks Per Batch (every 90ms):", font=("Segoe UI", 9, "bold"), fg="#2D3748", bg="#FFFFFF").pack(side=tk.LEFT)

        btn_minus = tk.Button(
            taps_row, text="−10", font=("Segoe UI", 8, "bold"), width=3, bg="#EDF2F7", relief=tk.FLAT,
            command=lambda: self.adjust_taps(-10)
        )
        btn_minus.pack(side=tk.LEFT, padx=(10, 4))

        self.entry_taps = tk.Entry(taps_row, width=4, font=("Segoe UI", 10, "bold"), justify=tk.CENTER, bd=1, relief=tk.SOLID)
        self.entry_taps.insert(0, str(self.engine.taps_per_tick))
        self.entry_taps.pack(side=tk.LEFT, padx=2)
        self.entry_taps.bind("<Return>", self.on_entry_taps_submit)
        self.entry_taps.bind("<FocusOut>", self.on_entry_taps_submit)

        btn_plus = tk.Button(
            taps_row, text="+10", font=("Segoe UI", 8, "bold"), width=3, bg="#EDF2F7", relief=tk.FLAT,
            command=lambda: self.adjust_taps(+10)
        )
        btn_plus.pack(side=tk.LEFT, padx=(4, 10))

        self.lbl_calculated_cps = tk.Label(taps_row, text="", font=("Segoe UI", 9, "bold"), fg="#38A169", bg="#FFFFFF")
        self.lbl_calculated_cps.pack(side=tk.RIGHT)

        self.slider = tk.Scale(
            inner,
            from_=10,
            to=250,
            orient=tk.HORIZONTAL,
            showvalue=False,
            bg="#FFFFFF",
            highlightthickness=0,
            command=self.on_slider_change,
        )
        self.slider.set(self.engine.taps_per_tick)
        self.slider.pack(fill=tk.X, pady=(0, 8))

        # Technical Note
        note_frame = tk.Frame(inner, bg="#E6FFFA", bd=1, relief=tk.SOLID, padx=8, pady=6)
        note_frame.pack(fill=tk.X)
        lbl_note = tk.Label(
            note_frame,
            text="✨ Native Direct IPC Mode: Injects clicks directly into BongoCat's memory through its native internal named pipe (BongoCatxTheFarmerWasReplaced). Zero keyboard simulation, zero interference with YouTube 2x speed, zero Windows key conflicts, and 100% click registration.",
            font=("Segoe UI", 8),
            fg="#234E52",
            bg="#E6FFFA",
            wraplength=440,
            justify=tk.LEFT,
        )
        lbl_note.pack(anchor=tk.W)

        self.update_preset_buttons_ui()

    def select_preset(self, preset_key):
        self.engine.set_preset(preset_key)
        self.slider.set(self.engine.taps_per_tick)
        self.entry_taps.delete(0, tk.END)
        self.entry_taps.insert(0, str(self.engine.taps_per_tick))
        self.update_preset_buttons_ui()

    def update_preset_buttons_ui(self):
        cur = self.engine.preset_key
        for key, btn in self.preset_buttons.items():
            if key == cur:
                btn.configure(bg="#2B6CB0", fg="#FFFFFF", activebackground="#2C5282", activeforeground="#FFFFFF")
            else:
                btn.configure(bg="#EDF2F7", fg="#4A5568", activebackground="#E2E8F0", activeforeground="#1A202C")

        cfg = PRESETS.get(cur, PRESETS["overdrive"])
        cps = int(self.engine.taps_per_tick / 0.090)
        self.lbl_desc_speed.configure(text=f"Direct IPC Throughput: ~{cps:,} CPS")
        self.lbl_desc_body.configure(text=cfg["desc"])
        self.lbl_calculated_cps.configure(text=f"≈ {cps:,} CPS")
        self.lbl_preset_tag.configure(text=f"Direct IPC (~{cps:,} CPS)")

    def on_slider_change(self, val):
        taps = int(val)
        self.engine.set_custom_taps(taps)
        self.entry_taps.delete(0, tk.END)
        self.entry_taps.insert(0, str(taps))
        self.update_preset_buttons_ui()

    def on_entry_taps_submit(self, event=None):
        raw = self.entry_taps.get().strip()
        if raw.isdigit():
            taps = max(1, min(500, int(raw)))
            self.slider.set(taps)
            self.engine.set_custom_taps(taps)
            self.update_preset_buttons_ui()

    def adjust_taps(self, delta):
        cur = self.engine.taps_per_tick
        new_val = max(1, min(500, cur + delta))
        self.slider.set(new_val)
        self.engine.set_custom_taps(new_val)
        self.entry_taps.delete(0, tk.END)
        self.entry_taps.insert(0, str(new_val))
        self.update_preset_buttons_ui()

    def toggle_settings_panel(self):
        self.show_settings = not self.show_settings
        if self.show_settings:
            self.settings_frame.pack(fill=tk.X, pady=(10, 0))
            self.root.geometry("520x860")
            self.btn_settings.configure(text="▲  Close Settings", bg="#CBD5E0")
        else:
            self.settings_frame.pack_forget()
            self.root.geometry("520x540")
            self.btn_settings.configure(text="⚙️  Speed & Settings", bg="#EDF2F7")

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
            self.btn_toggle.configure(text="⏸  PAUSE FARMING  (F8)", bg="#20C997", activebackground="#12B886")
            self.status_dot.configure(fg="#38A169")
            self.status_text.configure(text=f"FARMING ACTIVE - {self.engine.ipc_status_text}", fg="#276749")
        else:
            self.btn_toggle.configure(text="▶  START FARMING  (F8)", bg="#FF6B6B", activebackground="#FA5252")
            if self.engine.ipc.connected:
                self.status_dot.configure(fg="#3182CE")
                self.status_text.configure(text="READY - Connected (Press [F8] to start)", fg="#2B6CB0")
            else:
                self.status_dot.configure(fg="#DD6B20")
                self.status_text.configure(text="WAITING - Launch BongoCat to connect", fg="#C05621")

        # Update Stats Cards
        self.card_clicks.val_label.configure(text=f"{self.engine.total_clicks:,}")
        self.card_cps.val_label.configure(text=f"{int(actual_cps):,} CPS" if self.engine.running else "0 CPS")
        self.card_time.val_label.configure(text=format_duration(active_time))

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
    engine = ClickerEngine(preset_key="overdrive")

    pipe_thread = threading.Thread(target=engine.pipe_worker, daemon=True)
    pipe_thread.start()

    click_thread = threading.Thread(target=engine.run_loop, daemon=True)
    click_thread.start()

    hotkey_thread = threading.Thread(target=hotkey_listener, args=(engine,), daemon=True)
    hotkey_thread.start()

    print("=" * 66)
    print("       Bongo Cat Turbo Clicker (Direct IPC Mode)")
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
