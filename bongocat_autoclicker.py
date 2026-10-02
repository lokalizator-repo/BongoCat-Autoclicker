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

KEYEVENTF_KEYUP = 0x0002
VK_LBUTTON = 0x01
VK_SPACE = 0x20
VK_F8 = 0x77
VK_F10 = 0x79

# --- VIRTUAL KEY MATRIX ---
# Strictly filtered harmless keys supported by BongoCat's BUTTONS array.
# Explicitly excluded:
# - VK_NAVIGATION_* (0x88-0x8F): causes cursor/selection jumping in Windows Explorer.
# - Gamepad buttons (0xC3-0xDA): triggers Windows Touch/On-Screen Keyboard when Win key is pressed.
# - VK_PLAY (0xFA) & VK_ZOOM (0xFB): triggers Windows media/accessibility tools.

SAFE_F_KEYS = list(range(0x7C, 0x88)) # F13 - F24 (12 keys)
DORMANT_SYSTEM_KEYS = [                # Fujitsu & dormant ICO codes (6 keys)
    0x93, 0x94, 0x95, 0x96, 0xE3, 0xE4
]
DORMANT_OEM_KEYS = [                   # Completely unassigned / non-interactive OEM codes (22 keys)
    0xE6, 0xE7, 0xE9, 0xEA, 0xEB, 0xEC, 0xED, 0xEE, 0xEF, 0xF0,
    0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFC,
    0xFD, 0xFE
]

PRESETS = {
    "overdrive": {
        "title": "Overdrive",
        "badge": "40 keys",
        "approx_cps": "~715 – 800 CPS",
        "desc": "Full dormant key matrix (F13-F24 + Fujitsu + Clean OEM). Maximum clean throughput with zero Windows Explorer or Game Bar conflicts.",
        "keys": SAFE_F_KEYS + DORMANT_SYSTEM_KEYS + DORMANT_OEM_KEYS,
    },
    "turbo": {
        "title": "Turbo",
        "badge": "24 keys",
        "approx_cps": "~430 CPS",
        "desc": "Balanced mode using 24 isolated virtual keys (F13-F24 + Select OEM). Moderate event frequency.",
        "keys": SAFE_F_KEYS + DORMANT_SYSTEM_KEYS + DORMANT_OEM_KEYS[:6],
    },
    "stealth": {
        "title": "Stealth",
        "badge": "12 keys",
        "approx_cps": "~215 CPS",
        "desc": "Uses only standard F13-F24 function keys. Minimal event generation, ultra-light background farming.",
        "keys": SAFE_F_KEYS,
    },
}

def split_groups(keys):
    half = len(keys) // 2
    return keys[:half], keys[half:]

def press_keys(keys):
    for vk in keys:
        user32.keybd_event(vk, 0, 0, 0)

def release_keys(keys):
    for vk in keys:
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

def format_duration(seconds: float) -> str:
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

class ClickerEngine:
    def __init__(self, preset_key="overdrive", delay_ms=28, smart_pause=True):
        self.preset_key = preset_key
        self.delay_ms = delay_ms
        self.delay_sec = delay_ms / 1000.0
        self.smart_pause = smart_pause
        self.update_keys(preset_key)

        self.running = False
        self.shutdown_requested = False
        self.total_clicks = 0
        self.active_duration = 0.0
        self.last_state_change = time.perf_counter()
        self.paw_step = 0

    def update_keys(self, preset_key):
        self.preset_key = preset_key
        keys = PRESETS.get(preset_key, PRESETS["overdrive"])["keys"]
        self.group_a, self.group_b = split_groups(keys)
        self.step_clicks = len(self.group_a)

    def set_delay_ms(self, delay_ms):
        self.delay_ms = max(16, min(50, int(delay_ms)))
        self.delay_sec = self.delay_ms / 1000.0

    def toggle(self):
        now = time.perf_counter()
        if self.running:
            self.running = False
            self.active_duration += now - self.last_state_change
            release_keys(self.group_a)
            release_keys(self.group_b)
            self.paw_step = 0
        else:
            self.running = True
            self.last_state_change = now

    def shutdown(self):
        self.shutdown_requested = True
        self.running = False
        release_keys(self.group_a)
        release_keys(self.group_b)

    def run_loop(self):
        cycle = 0
        while not self.shutdown_requested:
            if self.running:
                # Smart Pause: If user is actively holding Left Mouse Button (e.g. YouTube 2x, drag)
                # or holding Spacebar (YouTube 2x), yield input to prevent interrupting user actions.
                if self.smart_pause:
                    lmb_held = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
                    space_held = bool(user32.GetAsyncKeyState(VK_SPACE) & 0x8000)
                    if lmb_held or space_held:
                        if self.paw_step != 0:
                            release_keys(self.group_a)
                            release_keys(self.group_b)
                            self.paw_step = 0
                        time.sleep(0.015)
                        continue

                # Alternating injection
                if cycle % 2 == 0:
                    release_keys(self.group_b)
                    press_keys(self.group_a)
                    self.paw_step = 1
                else:
                    release_keys(self.group_a)
                    press_keys(self.group_b)
                    self.paw_step = 2

                self.total_clicks += self.step_clicks
                cycle += 1
                time.sleep(self.delay_sec)
            else:
                self.paw_step = 0
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
        self.root.title("Bongo Cat Turbo Clicker")
        self.root.geometry("520x540")
        self.root.resizable(False, False)
        self.root.configure(bg="#FFF9F5")

        winmm.timeBeginPeriod(1)
        self.engine = ClickerEngine(preset_key="overdrive", delay_ms=28, smart_pause=True)

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
            text="READY - Press [F8] to start farming",
            font=("Segoe UI", 9, "bold"),
            fg="#4A5568",
            bg="#FFF9F5",
        )
        self.status_text.pack(side=tk.LEFT)

        self.lbl_preset_tag = tk.Label(
            status_bar,
            text="Overdrive (40 keys)",
            font=("Segoe UI", 8, "bold"),
            fg="#E05D52",
            bg="#FFEBE8",
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
        tk.Label(hdr, text="⚙️ SPEED PRESETS & BEHAVIOR", font=("Segoe UI", 9, "bold"), fg="#2D3748", bg="#F7FAFC").pack(side=tk.LEFT)

        inner = tk.Frame(self.settings_frame, bg="#FFFFFF", padx=14, pady=10)
        inner.pack(fill=tk.BOTH, expand=True)

        # Preset selection
        tk.Label(inner, text="Select Mode Preset:", font=("Segoe UI", 9, "bold"), fg="#2D3748", bg="#FFFFFF").pack(anchor=tk.W, pady=(0, 6))

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

        # Direct Delay / Speed Input & Slider
        delay_row = tk.Frame(inner, bg="#FFFFFF")
        delay_row.pack(fill=tk.X, pady=(0, 4))

        tk.Label(delay_row, text="Hold Delay (ms):", font=("Segoe UI", 9, "bold"), fg="#2D3748", bg="#FFFFFF").pack(side=tk.LEFT)

        btn_minus = tk.Button(
            delay_row, text="−", font=("Segoe UI", 10, "bold"), width=2, bg="#EDF2F7", relief=tk.FLAT,
            command=lambda: self.adjust_delay(-1)
        )
        btn_minus.pack(side=tk.LEFT, padx=(10, 4))

        self.entry_delay = tk.Entry(delay_row, width=4, font=("Segoe UI", 10, "bold"), justify=tk.CENTER, bd=1, relief=tk.SOLID)
        self.entry_delay.insert(0, str(self.engine.delay_ms))
        self.entry_delay.pack(side=tk.LEFT, padx=2)
        self.entry_delay.bind("<Return>", self.on_entry_delay_submit)
        self.entry_delay.bind("<FocusOut>", self.on_entry_delay_submit)

        btn_plus = tk.Button(
            delay_row, text="+", font=("Segoe UI", 10, "bold"), width=2, bg="#EDF2F7", relief=tk.FLAT,
            command=lambda: self.adjust_delay(+1)
        )
        btn_plus.pack(side=tk.LEFT, padx=(4, 10))

        self.lbl_sync_indicator = tk.Label(delay_row, text="28 ms (100% Sync)", font=("Segoe UI", 9, "bold"), fg="#38A169", bg="#FFFFFF")
        self.lbl_sync_indicator.pack(side=tk.RIGHT)

        self.slider = tk.Scale(
            inner,
            from_=18,
            to=42,
            orient=tk.HORIZONTAL,
            showvalue=False,
            bg="#FFFFFF",
            highlightthickness=0,
            command=self.on_slider_change,
        )
        self.slider.set(self.engine.delay_ms)
        self.slider.pack(fill=tk.X, pady=(0, 8))

        # Smart Auto-Pause Toggle
        self.smart_pause_var = tk.BooleanVar(value=True)
        chk_pause = tk.Checkbutton(
            inner,
            text="⚡ Smart Auto-Pause: Yield when holding LMB or Space (fixes YouTube 2x)",
            variable=self.smart_pause_var,
            font=("Segoe UI", 8, "bold"),
            fg="#2D3748",
            bg="#FFFFFF",
            activebackground="#FFFFFF",
            command=self.on_smart_pause_toggle,
        )
        chk_pause.pack(anchor=tk.W, pady=(0, 8))

        # Explanatory Technical Note
        note_frame = tk.Frame(inner, bg="#FEFCBF", bd=1, relief=tk.SOLID, padx=8, pady=6)
        note_frame.pack(fill=tk.X)
        lbl_note = tk.Label(
            note_frame,
            text="💡 Sync Guarantee: BongoCat samples keys every 16 ms. A 28 ms delay guarantees 100% click registration without dropped inputs. Keys are strictly isolated so they never interfere with Windows Explorer, Touch Keyboard, or gaming.",
            font=("Segoe UI", 8),
            fg="#744210",
            bg="#FEFCBF",
            wraplength=440,
            justify=tk.LEFT,
        )
        lbl_note.pack(anchor=tk.W)

        self.update_preset_buttons_ui()

    def select_preset(self, preset_key):
        self.engine.update_keys(preset_key)
        self.lbl_preset_tag.configure(text=f"{PRESETS[preset_key]['title']} ({PRESETS[preset_key]['badge']})")
        self.update_preset_buttons_ui()

    def update_preset_buttons_ui(self):
        cur = self.engine.preset_key
        for key, btn in self.preset_buttons.items():
            if key == cur:
                btn.configure(bg="#E05D52", fg="#FFFFFF", activebackground="#C53030", activeforeground="#FFFFFF")
            else:
                btn.configure(bg="#EDF2F7", fg="#4A5568", activebackground="#E2E8F0", activeforeground="#1A202C")

        cfg = PRESETS[cur]
        self.lbl_desc_speed.configure(text=f"Estimated Throughput: {cfg['approx_cps']} ({cfg['badge']})")
        self.lbl_desc_body.configure(text=cfg["desc"])

    def on_slider_change(self, val):
        ms = int(val)
        self.engine.set_delay_ms(ms)
        self.entry_delay.delete(0, tk.END)
        self.entry_delay.insert(0, str(ms))
        self.update_sync_label(ms)

    def on_entry_delay_submit(self, event=None):
        raw = self.entry_delay.get().strip()
        if raw.isdigit():
            ms = max(16, min(50, int(raw)))
            self.slider.set(ms)
            self.engine.set_delay_ms(ms)
            self.update_sync_label(ms)

    def adjust_delay(self, delta):
        cur = self.engine.delay_ms
        new_val = max(16, min(50, cur + delta))
        self.slider.set(new_val)
        self.engine.set_delay_ms(new_val)
        self.entry_delay.delete(0, tk.END)
        self.entry_delay.insert(0, str(new_val))
        self.update_sync_label(new_val)

    def on_smart_pause_toggle(self):
        self.engine.smart_pause = self.smart_pause_var.get()

    def update_sync_label(self, ms):
        if ms in range(26, 32):
            self.lbl_sync_indicator.configure(text=f"{ms} ms (100% Sync)", fg="#38A169")
        elif ms < 26:
            self.lbl_sync_indicator.configure(text=f"{ms} ms (Fast - May drop ~30%)", fg="#DD6B20")
        else:
            self.lbl_sync_indicator.configure(text=f"{ms} ms (Safe & Stable)", fg="#3182CE")

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
            self.status_text.configure(text="FARMING ACTIVE - Injecting inputs...", fg="#276749")
        else:
            self.btn_toggle.configure(text="▶  START FARMING  (F8)", bg="#FF6B6B", activebackground="#FA5252")
            self.status_dot.configure(fg="#A0AEC0")
            self.status_text.configure(text="PAUSED - Press [F8] or button to resume", fg="#4A5568")

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
    engine = ClickerEngine(preset_key="overdrive", delay_ms=28, smart_pause=True)

    click_thread = threading.Thread(target=engine.run_loop, daemon=True)
    click_thread.start()

    hotkey_thread = threading.Thread(target=hotkey_listener, args=(engine,), daemon=True)
    hotkey_thread.start()

    print("=" * 66)
    print("           Bongo Cat Turbo Clicker (CLI Mode)")
    print("=" * 66)
    print(" Controls:")
    print("   [F8]  - Start / Pause")
    print("   [F10] - Quit program")
    print("=" * 66)
    print(" Ready. Press [F8] to start farming.\n")

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
