#!/usr/bin/env python3
import ctypes
from ctypes import wintypes
import os
import sys
import threading
import time

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
    1: {
        "name": "Stealth (~300 CPS)",
        "keys": F_KEYS,
    },
    2: {
        "name": "Turbo (~700 CPS)",
        "keys": F_KEYS + NAV_KEYS + OEM_KEYS[:8],
    },
    3: {
        "name": "Overdrive (~1,450 CPS)",
        "keys": F_KEYS + NAV_KEYS + GAMEPAD_KEYS + OEM_KEYS,
    },
}

def enable_ansi_support():
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11) # STD_OUTPUT_HANDLE
    mode = wintypes.DWORD()
    if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        kernel32.SetConsoleMode(handle, mode.value | 0x0004) # ENABLE_VIRTUAL_TERMINAL_PROCESSING

def split_groups(keys):
    half = len(keys) // 2
    return keys[:half], keys[half:]

def press_keys(keys):
    for vk in keys:
        user32.keybd_event(vk, 0, 0, 0)

def release_keys(keys):
    for vk in keys:
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

class ClickerController:
    def __init__(self, mode_idx: int = 3):
        self.preset = PRESETS.get(mode_idx, PRESETS[3])
        all_keys = self.preset["keys"]
        self.group_a, self.group_b = split_groups(all_keys)
        self.all_keys = all_keys

        self.running = False
        self.shutdown_requested = False
        self.total_clicks = 0
        self.start_time = None
        self.active_duration = 0.0
        self.last_state_change = time.perf_counter()

    def toggle(self):
        now = time.perf_counter()
        if self.running:
            self.running = False
            self.active_duration += now - self.last_state_change
            release_keys(self.group_a)
            release_keys(self.group_b)
        else:
            self.running = True
            if self.start_time is None:
                self.start_time = now
            self.last_state_change = now

    def shutdown(self):
        self.shutdown_requested = True
        self.running = False
        release_keys(self.group_a)
        release_keys(self.group_b)

def hotkey_listener(controller: ClickerController):
    last_f8 = False
    last_f10 = False

    while not controller.shutdown_requested:
        # Check MSB for key-down state to ensure reliable edge detection
        f8_down = bool(user32.GetAsyncKeyState(VK_F8) & 0x8000)
        if f8_down and not last_f8:
            controller.toggle()
        last_f8 = f8_down

        f10_down = bool(user32.GetAsyncKeyState(VK_F10) & 0x8000)
        if f10_down and not last_f10:
            controller.shutdown()
            break
        last_f10 = f10_down

        time.sleep(0.005)

def format_duration(seconds: float) -> str:
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

def main():
    enable_ansi_support()
    winmm.timeBeginPeriod(1)

    print("\033[2J\033[H", end="") # Clear screen
    print("=" * 66)
    print("           BongoCat High-Speed Input Injector")
    print("=" * 66)
    print(" Select speed preset:")
    print("   [1] Stealth   (~300 CPS   | 12 keys  | Ultra-light)")
    print("   [2] Turbo     (~700 CPS   | 28 keys  | Balanced)")
    print("   [3] Overdrive (~1,450 CPS | 58 keys  | Maximum throughput)")
    print("-" * 66)

    selected_mode = 3
    user_choice = input(" Choose mode (1-3) [default: 3]: ").strip()
    if user_choice in ("1", "2", "3"):
        selected_mode = int(user_choice)

    controller = ClickerController(mode_idx=selected_mode)
    listener_thread = threading.Thread(target=hotkey_listener, args=(controller,), daemon=True)
    listener_thread.start()

    print("\033[2J\033[H", end="")
    print("=" * 66)
    print("           BongoCat High-Speed Input Injector")
    print("=" * 66)
    print(f" Mode: {controller.preset['name']} ({len(controller.all_keys)} simulated keys)")
    print(" Controls:")
    print("   [F8]  - Start / Pause")
    print("   [F10] - Quit program")
    print("=" * 66)
    print(" Ready. Press [F8] to begin farming clicks.\n")

    cycle = 0
    step_clicks = len(controller.group_a)
    last_ui_update = time.perf_counter()
    cps_samples = []

    try:
        while not controller.shutdown_requested:
            if controller.running:
                # Alternate key groups every 20ms to match BongoCat's 16ms poll loop
                if cycle % 2 == 0:
                    release_keys(controller.group_b)
                    press_keys(controller.group_a)
                else:
                    release_keys(controller.group_a)
                    press_keys(controller.group_b)

                controller.total_clicks += step_clicks
                cycle += 1
                time.sleep(0.020)
            else:
                time.sleep(0.040)

            now = time.perf_counter()
            if now - last_ui_update >= 0.25:
                active_time = controller.active_duration
                if controller.running:
                    active_time += now - controller.last_state_change

                actual_cps = 0.0
                if active_time > 0:
                    actual_cps = controller.total_clicks / active_time

                status_color = "\033[92m[ACTIVE]\033[0m" if controller.running else "\033[93m[PAUSED]\033[0m"
                print(
                    f"\rStatus: {status_color:<18} "
                    f"Clicks: \033[96m{controller.total_clicks:,}\033[0m  "
                    f"CPS: \033[95m{int(actual_cps):,}\033[0m  "
                    f"Time: {format_duration(active_time)}   ",
                    end="",
                    flush=True,
                )
                last_ui_update = now

    except KeyboardInterrupt:
        pass
    finally:
        controller.shutdown()
        winmm.timeEndPeriod(1)
        print("\n\nInjector stopped cleanly. Final count: " f"{controller.total_clicks:,} clicks.")

if __name__ == "__main__":
    main()
