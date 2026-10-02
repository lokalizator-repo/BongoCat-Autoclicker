# Bongo Cat Turbo Clicker 🐾

A beautiful, lightweight Windows desktop app designed to farm clicks in **BongoCat** at **~1,000+ real CPS (Clicks Per Second)** with **100% registration accuracy**, zero external dependencies, and zero text intrusion.

![Bongo Cat Preview](https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/3110780/header.jpg)

---

## ⚡ Why Standard Macros Fail & The ~50% Dropped Click Mystery

Many players try using mouse macros (WLmouse, Razer, Logitech) and notice clicks are either completely ignored or register only partially.

### 1. The 16ms Polling Timer
In BongoCat's code (`GlobalKeyHook` in `Assembly-CSharp.dll`), inputs are polled via a background thread timer firing every **~16 ms (~60 Hz)**:
```csharp
new Timer(Process, null, 0, 16);
```
Inside each tick, the game inspects `GetAsyncKeyState(vk)` across an array of 221 keys (`BUTTONS`).
* **Sub-millisecond macro clicks:** If a macro presses and releases a button in 0–2 ms, it almost always lands between 16ms timer ticks and is completely ignored.
* **Why fast 20ms clickers drop ~40–50% of clicks:** If an injector toggles keys every 20ms, it clashes with BongoCat's ~16ms timer (beat frequency / phase drift). Because a key must be detected in the `UP` state to reset its trigger flag, consecutive ticks catching the key in the same state result in lost clicks.

### 2. The 28ms Calibration Fix (100% Sync)
By calibrating the state hold duration to **28 ms** (roughly 1.75x BongoCat's 16ms timer period):
* Every `DOWN` phase is mathematically guaranteed to be sampled by BongoCat.
* Every `UP` phase is guaranteed to reset the key flag.
* **Result:** **100% of sent clicks register in BongoCat** with zero drops.

---

## 🚀 How It Achieves 1,000+ CPS

BongoCat accumulates all keys pressed during each timer tick:
```csharp
_keysDown += platformHook.ProcessInput(ignoreMouse);
```
Instead of clicking a single mouse button, this injector alternates between two groups of **harmless virtual keys**:
1. **58 Non-Intrusive Keys:** `F13`–`F24`, virtual Gamepad buttons, navigation codes, and OEM control codes. None of these keys type characters in Discord, browsers, or text editors.
2. **Alternating Batch Injection:**
   - **Step 1 (28 ms):** Release Group B, Press Group A (29 keys down $\rightarrow$ **+29 clicks**).
   - **Step 2 (28 ms):** Release Group A, Press Group B (29 keys down $\rightarrow$ **+29 clicks**).
3. **Throughput:** $29 \text{ keys} / 0.028 \text{ s} \approx \mathbf{1,035\text{ CPS}}$, with **100% registered** in BongoCat.

---

## ✨ Features

- 🎨 **Authentic Pastel Aesthetic:** Styled directly after the official Bongo Cat pastel sunset theme.
- 🐾 **Animated Bongo Cat Mascot:** Cat paws tap alternately in real time when farming is active!
- ⚡ **1,000+ Real CPS:** Maximum speed with 100% click registration.
- 🎛️ **Settings & Calibration Slider:** Easily adjust the hold delay (18ms – 40ms) or switch presets.
- 📌 **Always on Top:** Pin the compact window near your cat.
- ⌨️ **Instant Global Hotkeys:** `F8` (Start / Pause) and `F10` (Exit) work system-wide even while minimized.
- 📦 **Zero External Dependencies:** Built with pure Python standard library (`ctypes` + `tkinter`). No `pip install` required.
- 💻 **CLI Mode Supported:** Run with `--cli` for headless / terminal-only environments.

---

## ⌨️ Controls

| Key | Action |
| :---: | :--- |
| **`F8`** | **Start / Pause** (instant edge-detected hotkey) |
| **`F10`** | **Exit** (cleanly releases all keys and quits) |

---

## 📥 Installation & Running

### Requirements
- Windows 10 / 11
- Python 3.7+ installed

### Quick Start
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/bongocat-autoclicker.git
   cd bongocat-autoclicker
   ```
2. Double-click **`run.bat`** (or execute `python bongocat_autoclicker.py`).
3. Press **`F8`** to start farming!

---

## ⚙️ Settings & Presets

Click the **⚙️ Settings** button inside the app to customize:
* **Input Hold Delay:** Defaults to **28 ms (100% Sync)**. Lower values increase theoretical CPS but may drop clicks if BongoCat cannot keep up.
* **Speed Presets:**
  - **Overdrive (58 keys):** Maximum speed (~1,035 CPS).
  - **Turbo (28 keys):** Balanced (~500 CPS).
  - **Stealth (12 keys):** Light mode (`F13`–`F24`, ~215 CPS).

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
