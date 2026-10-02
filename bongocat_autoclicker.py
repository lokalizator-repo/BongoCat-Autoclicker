#!/usr/bin/env python3
import ctypes
from ctypes import wintypes
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
winmm = ctypes.windll.winmm

KEYEVENTF_KEYUP = 0x0002
VK_F8 = 0x77
VK_F10 = 0x79

# Virtual keys supported by BongoCat's BUTTONS array that produce no visible
# characters in Windows text editors or browsers.
F_KEYS = list(range(0x7C, 0x88))       # F13 - F24 (12 keys)
NAV_KEYS = list(range(0x88, 0x90))     # Navigation keys (8 keys)
GAMEPAD_KEYS = list(range(0xC3, 0xDB)) # Virtual Gamepad keys (24 keys)
OEM_KEYS = [                           # Harmless OEM/Control virtual keys (14 keys)
    0xEB, 0xEC, 0xED, 0xEE, 0xEF,
    0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE
]

PRESETS = {
    "overdrive": {
        "name": "Overdrive (58 keys)",
        "keys": F_KEYS + NAV_KEYS + GAMEPAD_KEYS + OEM_KEYS,
    },
    "turbo": {
        "name": "Turbo (28 keys)",
        "keys": F_KEYS + NAV_KEYS + OEM_KEYS[:8],
    },
    "stealth": {
        "name": "Stealth (12 keys)",
        "keys": F_KEYS,
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
    def __init__(self, preset_key="overdrive", delay_ms=28):
        self.preset_key = preset_key
        self.delay_sec = delay_ms / 1000.0
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
        self.delay_sec = max(0.018, min(0.050, delay_ms / 1000.0))

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
                # Alternate key groups
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

class BongoCanvas(tk.Canvas):
    def __init__(self, master, width=480, height=200, **kwargs):
        super().__init__(master, width=width, height=height, highlightthickness=0, **kwargs)
        self.w = width
        self.h = height
        self.paw_state = 0
        self.build_scene()

    def build_scene(self):
        # Warm sunset pastel gradient: Coral -> Peach -> Cream
        r1, g1, b1 = 233, 118, 114
        r2, g2, b2 = 244, 160, 134
        r3, g3, b3 = 252, 226, 204

        steps = 50
        for i in range(steps):
            t = i / steps
            if t < 0.5:
                st = t * 2
                r = int(r1 + (r2 - r1) * st)
                g = int(g1 + (r2 - g1) * st)
                b = int(b1 + (r2 - b1) * st)
            else:
                st = (t - 0.5) * 2
                r = int(r2 + (r3 - r2) * st)
                g = int(g2 + (r3 - g2) * st)
                b = int(b2 + (r3 - b2) * st)

            y1 = int(i * (self.h / steps))
            y2 = int((i + 1) * (self.h / steps))
            c = f"#{r:02x}{g:02x}{b:02x}"
            self.create_rectangle(0, y1, self.w, y2, fill=c, outline=c)

        # "Bongo Cat" Logo lettering with 3D drop-shadow
        self.create_text(138, 48, text="Bongo Cat", font=("Arial Rounded MT Bold", 32, "bold"), fill="#3E2723")
        self.create_text(136, 46, text="Bongo Cat", font=("Arial Rounded MT Bold", 32, "bold"), fill="#5D4037")
        self.create_text(135, 44, text="Bongo Cat", font=("Arial Rounded MT Bold", 32, "bold"), fill="#BFE3F7")

        # Pill badge
        self.create_oval(60, 68, 76, 84, fill="#FFFFFF", outline="")
        self.create_oval(194, 68, 210, 84, fill="#FFFFFF", outline="")
        self.create_rectangle(68, 68, 202, 84, fill="#FFFFFF", outline="")
        self.create_text(135, 76, text="TURBO CLICKER", font=("Arial Rounded MT Bold", 8, "bold"), fill="#E06A66")

        # Cat positioning
        cx, cy = 345, 130

        # Ears
        self.create_polygon(cx - 58, cy - 20, cx - 40, cy - 72, cx - 12, cy - 38, fill="#FFFFFF", outline="#3E2723", width=3)
        self.create_polygon(cx - 51, cy - 26, cx - 39, cy - 64, cx - 18, cy - 39, fill="#FFAAA6")

        self.create_polygon(cx + 58, cy - 20, cx + 40, cy - 72, cx + 12, cy - 38, fill="#FFFFFF", outline="#3E2723", width=3)
        self.create_polygon(cx + 51, cy - 26, cx + 39, cy - 64, cx + 18, cy - 39, fill="#FFAAA6")

        # Head / Body
        self.create_oval(cx - 68, cy - 40, cx + 68, cy + 50, fill="#FFFFFF", outline="#3E2723", width=3)

        # Cheeks (blush)
        self.create_oval(cx - 48, cy + 8, cx - 32, cy + 20, fill="#FFB7B4", outline="")
        self.create_oval(cx + 32, cy + 8, cx + 48, cy + 20, fill="#FFB7B4", outline="")

        # Eyes • •
        self.create_oval(cx - 34, cy - 6, cx - 24, cy + 6, fill="#3E2723", outline="")
        self.create_oval(cx + 24, cy - 6, cx + 34, cy + 6, fill="#3E2723", outline="")

        # Mouth ω
        self.create_arc(cx - 14, cy + 4, cx, cy + 18, start=180, extent=180, style=tk.ARC, outline="#3E2723", width=3)
        self.create_arc(cx, cy + 4, cx + 14, cy + 18, start=180, extent=180, style=tk.ARC, outline="#3E2723", width=3)

        # Desk shelf surface
        self.create_rectangle(0, 168, self.w, self.h, fill="#D9E2EC", outline="#BAC7D5", width=2)

        # Paw base positions
        self.cx = cx
        self.base_l_y = 164
        self.base_r_y = 164
        self.draw_left_paw(cx, self.base_l_y)
        self.draw_right_paw(cx, self.base_r_y)

    def draw_left_paw(self, cx, y):
        self.delete("paw_l")
        self.create_oval(cx - 78, y - 18, cx - 40, y + 14, fill="#FFFFFF", outline="#3E2723", width=3, tags="paw_l")
        self.create_oval(cx - 66, y - 10, cx - 52, y + 2, fill="#FFAAA6", outline="", tags="paw_l")
        self.create_oval(cx - 73, y - 16, cx - 65, y - 8, fill="#FFAAA6", outline="", tags="paw_l")
        self.create_oval(cx - 63, y - 18, cx - 55, y - 10, fill="#FFAAA6", outline="", tags="paw_l")
        self.create_oval(cx - 53, y - 16, cx - 45, y - 8, fill="#FFAAA6", outline="", tags="paw_l")

    def draw_right_paw(self, cx, y):
        self.delete("paw_r")
        self.create_oval(cx + 40, y - 18, cx + 78, y + 14, fill="#FFFFFF", outline="#3E2723", width=3, tags="paw_r")
        self.create_oval(cx + 52, y - 10, cx + 66, y + 2, fill="#FFAAA6", outline="", tags="paw_r")
        self.create_oval(cx + 45, y - 16, cx + 53, y - 8, fill="#FFAAA6", outline="", tags="paw_r")
        self.create_oval(cx + 55, y - 18, cx + 63, y - 10, fill="#FFAAA6", outline="", tags="paw_r")
        self.create_oval(cx + 65, y - 16, cx + 73, y - 8, fill="#FFAAA6", outline="", tags="paw_r")

    def update_paws(self, paw_state):
        if self.paw_state == paw_state:
            return
        self.paw_state = paw_state

        ly = self.base_l_y - (18 if paw_state == 1 else 0)
        ry = self.base_r_y - (18 if paw_state == 2 else 0)
        self.draw_left_paw(self.cx, ly)
        self.draw_right_paw(self.cx, ry)

class BongoApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Bongo Cat Turbo Clicker")
        self.root.geometry("480x470")
        self.root.resizable(False, False)
        self.root.configure(bg="#F6EFEA")

        winmm.timeBeginPeriod(1)
        self.engine = ClickerEngine(preset_key="overdrive", delay_ms=28)

        # Start worker and hotkey threads
        self.click_thread = threading.Thread(target=self.engine.run_loop, daemon=True)
        self.click_thread.start()

        self.hotkey_thread = threading.Thread(target=hotkey_listener, args=(self.engine,), daemon=True)
        self.hotkey_thread.start()

        self.show_settings = False
        self.build_ui()
        self.update_loop()

    def build_ui(self):
        # 1. Mascot Canvas
        self.canvas = BongoCanvas(self.root, width=480, height=200)
        self.canvas.pack(fill=tk.X, side=tk.TOP)

        # Main content container
        content = tk.Frame(self.root, bg="#F6EFEA")
        content.pack(fill=tk.BOTH, expand=True, padx=18, pady=10)

        # 2. Stat Cards Row
        stats_frame = tk.Frame(content, bg="#F6EFEA")
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        # Card 1: Clicks
        self.card_clicks = self.create_stat_card(stats_frame, "🐾 CLICKS", "0", "#E87A6E")
        self.card_clicks.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        # Card 2: CPS
        self.card_cps = self.create_stat_card(stats_frame, "⚡ SPEED", "0 CPS", "#4A89DC")
        self.card_cps.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)

        # Card 3: Time
        self.card_time = self.create_stat_card(stats_frame, "⏱️ TIME", "00:00", "#7E6DB0")
        self.card_time.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        # 3. Big Action Button
        self.btn_toggle = tk.Button(
            content,
            text="▶ START FARMING (F8)",
            font=("Arial Rounded MT Bold", 13, "bold"),
            bg="#FF766D",
            fg="#FFFFFF",
            activebackground="#E5635B",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            pady=10,
            command=self.engine.toggle,
        )
        self.btn_toggle.pack(fill=tk.X, pady=(0, 8))

        # 4. Secondary Row: Settings Toggle & Always on Top
        bar = tk.Frame(content, bg="#F6EFEA")
        bar.pack(fill=tk.X)

        self.btn_settings = tk.Button(
            bar,
            text="⚙️ Settings",
            font=("Segoe UI", 9, "bold"),
            bg="#E2DCD5",
            fg="#4A4540",
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
            pady=4,
            command=self.toggle_settings_panel,
        )
        self.btn_settings.pack(side=tk.LEFT)

        self.top_var = tk.BooleanVar(value=False)
        self.chk_top = tk.Checkbutton(
            bar,
            text="📌 Always on Top",
            variable=self.top_var,
            font=("Segoe UI", 9),
            bg="#F6EFEA",
            fg="#504B46",
            activebackground="#F6EFEA",
            command=self.update_always_on_top,
        )
        self.chk_top.pack(side=tk.RIGHT)

        # 5. Collapsible Settings Panel
        self.settings_frame = tk.Frame(content, bg="#EDE6E0", bd=1, relief=tk.SOLID)

        # Delay calibration slider
        lbl_delay = tk.Label(
            self.settings_frame,
            text="Input Hold Delay (Sync with BongoCat 16ms timer):",
            font=("Segoe UI", 8, "bold"),
            bg="#EDE6E0",
            fg="#3E3834",
        )
        lbl_delay.pack(anchor=tk.W, padx=10, pady=(6, 0))

        slider_row = tk.Frame(self.settings_frame, bg="#EDE6E0")
        slider_row.pack(fill=tk.X, padx=10, pady=(2, 6))

        self.slider_val = tk.IntVar(value=28)
        self.slider = tk.Scale(
            slider_row,
            from_=18,
            to=40,
            orient=tk.HORIZONTAL,
            variable=self.slider_val,
            bg="#EDE6E0",
            highlightthickness=0,
            command=self.on_delay_change,
        )
        self.slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.lbl_delay_val = tk.Label(slider_row, text="28 ms (100% Sync)", font=("Segoe UI", 8, "bold"), bg="#EDE6E0", fg="#E87A6E")
        self.lbl_delay_val.pack(side=tk.RIGHT, padx=6)

        # Mode Selection
        lbl_mode = tk.Label(self.settings_frame, text="Speed Preset:", font=("Segoe UI", 8, "bold"), bg="#EDE6E0", fg="#3E3834")
        lbl_mode.pack(anchor=tk.W, padx=10, pady=(2, 0))

        modes_row = tk.Frame(self.settings_frame, bg="#EDE6E0")
        modes_row.pack(fill=tk.X, padx=10, pady=(0, 6))

        self.mode_var = tk.StringVar(value="overdrive")
        for key, title in [("overdrive", "Overdrive (58 keys)"), ("turbo", "Turbo (28 keys)"), ("stealth", "Stealth (12 keys)")]:
            rb = tk.Radiobutton(
                modes_row,
                text=title,
                value=key,
                variable=self.mode_var,
                font=("Segoe UI", 8),
                bg="#EDE6E0",
                command=self.on_mode_change,
            )
            rb.pack(side=tk.LEFT, padx=(0, 6))

    def create_stat_card(self, parent, title, initial_val, color):
        frame = tk.Frame(parent, bg="#FFFFFF", bd=1, relief=tk.SOLID)
        lbl_title = tk.Label(frame, text=title, font=("Segoe UI", 8, "bold"), fg=color, bg="#FFFFFF")
        lbl_title.pack(anchor=tk.CENTER, pady=(6, 0))
        lbl_val = tk.Label(frame, text=initial_val, font=("Arial Rounded MT Bold", 13, "bold"), fg="#2E2824", bg="#FFFFFF")
        lbl_val.pack(anchor=tk.CENTER, pady=(0, 6))
        frame.val_label = lbl_val
        return frame

    def toggle_settings_panel(self):
        self.show_settings = not self.show_settings
        if self.show_settings:
            self.settings_frame.pack(fill=tk.X, pady=(6, 0))
            self.root.geometry("480x560")
            self.btn_settings.configure(text="▲ Close Settings")
        else:
            self.settings_frame.pack_forget()
            self.root.geometry("480x470")
            self.btn_settings.configure(text="⚙️ Settings")

    def on_delay_change(self, val):
        ms = int(val)
        self.engine.set_delay_ms(ms)
        sync_text = "100% Sync" if ms in range(26, 32) else "Fast"
        self.lbl_delay_val.configure(text=f"{ms} ms ({sync_text})")

    def on_mode_change(self):
        m = self.mode_var.get()
        self.engine.update_keys(m)

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

        # Update button visual
        if self.engine.running:
            self.btn_toggle.configure(text="⏸ PAUSE (F8)", bg="#42BA82", activebackground="#38A271")
        else:
            self.btn_toggle.configure(text="▶ START FARMING (F8)", bg="#FF766D", activebackground="#E5635B")

        # Update animated paws
        self.canvas.update_paws(self.engine.paw_step)

        # Update stats
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
    engine = ClickerEngine(preset_key="overdrive", delay_ms=28)

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
