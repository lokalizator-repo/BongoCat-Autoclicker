# BongoCat High-Speed Input Injector

A lightweight, zero-dependency Windows utility designed to farm clicks in **BongoCat** at speeds exceeding **1,400+ CPS (Clicks Per Second)** without interfering with everyday PC usage.

---

## ⚡ The Problem: Why Standard Macros Fail

Many users attempt to use mouse macros (e.g., WLmouse, Razer Synapse, Logitech G Hub, or typical autoclickers) to farm clicks in BongoCat, only to find that **clicks are completely ignored** or register at an agonizingly low rate.

### Root Cause Analysis (BongoCat Internals)
Under the hood, BongoCat's input handler (`GlobalKeyHook` in `Assembly-CSharp.dll`) does not use Windows low-level mouse hooks (`WH_MOUSE_LL`). Instead, it runs a background timer:
```csharp
new Timer(Process, null, 0, 16); // Polling loop firing every ~16ms (~60 Hz)
```
Inside each tick, the game queries `GetAsyncKeyState(vk)` across an array of 221 supported keys (`BUTTONS`):

1. **Sub-millisecond Timing Mismatch:** Mouse macros typically press and release buttons with a delay of 0–2 ms. Because BongoCat only inspects `GetAsyncKeyState` once every 16 ms, fast macro clicks occur entirely *between* ticks and are completely missed.
2. **State Transition Requirement:** To increment the click counter, a button must transition from `Released` to `Pressed` on one tick, and then back to `Released` on a subsequent tick before it can trigger again.
3. **"Ignore Mouse" Flag:** If the game's internal `Ignore Mouse` toggle is enabled, mouse buttons (`VK_LBUTTON`, `VK_RBUTTON`, `VK_MBUTTON`, etc.) are filtered out entirely by the hook.

---

## 🚀 How This Injector Works

Instead of simulating a single mouse button with long delays, this tool takes advantage of how BongoCat aggregates input:
```csharp
_keysDown += platformHook.ProcessInput(ignoreMouse);
```
Every 16 ms, BongoCat **sums every single key** that transitioned to the down state.

### Multi-Key Alternating Injection
1. **58 Harmless Virtual Keys:** We selected virtual keys present in BongoCat's `BUTTONS` table that **never produce text characters** and **do not trigger desktop shortcuts** (e.g., `F13`–`F24`, virtual Gamepad codes, and OEM control codes).
2. **Alternating Batches:** The keys are partitioned into two groups (Group A and Group B).
   - **Step 1 (20 ms):** Release Group B, Press Group A (29 keys down $\rightarrow$ **+29 clicks**).
   - **Step 2 (20 ms):** Release Group A, Press Group B (29 keys down $\rightarrow$ **+29 clicks**).
3. **Throughput:** 29 clicks every 20 ms yields **~1,450 clicks per second**, all while allowing you to type, browse the web, or play games in the background without phantom keystrokes.

---

## ✨ Features

- **Blazing Fast Throughput:** Delivers up to **1,450+ CPS** reliably.
- **Zero Dependencies:** Pure Python standard library (`ctypes`). No `pip install` required.
- **Zero Text Intrusion:** Uses non-typing virtual keys (`F13`–`F24`, `Gamepad`, `OEM`), meaning you can chat in Discord, browse, or code while farming.
- **Instant Hotkey Response:** Edge-detected `F8` and `F10` polling thread guarantees trigger on the very first tap.
- **Live Terminal Dashboard:** Real-time ANSI dashboard showing active status, total clicks, live CPS counter, and elapsed time.
- **High-Precision Windows Timing:** Enforces `timeBeginPeriod(1)` to eliminate timer jitter on Windows.

---

## 🎮 Presets

| Preset | Keys | Approximate CPS | Description |
| :--- | :---: | :---: | :--- |
| **[1] Stealth** | 12 | **~300 CPS** | Minimal footprint (`F13`–`F24`). |
| **[2] Turbo** | 28 | **~700 CPS** | Balanced mix of functional keys. |
| **[3] Overdrive** | 58 | **~1,450 CPS** | Full harmless matrix for maximum throughput. |

---

## ⌨️ Hotkeys

| Key | Action |
| :---: | :--- |
| **`F8`** | **Toggle Start / Pause** (instant edge-triggered response) |
| **`F10`** | **Quit Program** (cleanly releases all simulated keys and exits) |

---

## 📥 Installation & Running

### Requirements
- Windows 10 / 11
- Python 3.7+ (ensure Python is added to your system `PATH`)

### Quick Start
1. Clone or download the repository:
   ```bash
   git clone https://github.com/your-username/bongocat-autoclicker.git
   cd bongocat-autoclicker
   ```
2. Double-click **`run.bat`** (or execute from terminal):
   ```bash
   python bongocat_autoclicker.py
   ```
3. Select your desired speed preset (`1`, `2`, or `3`).
4. Press **`F8`** to start farming clicks.

---

## ⚠️ Notes & Troubleshooting

- **BongoCat Must Be Running:** Make sure BongoCat is open before or after starting the script.
- **Run as Administrator (if needed):** If BongoCat or Steam was launched with Administrator privileges, Windows User Interface Privilege Isolation (UIPI) will block keystrokes from non-elevated scripts. If clicks do not register, right-click `run.bat` and select **"Run as Administrator"**.
- **Clean Termination:** Always pause with `F8` or exit with `F10` so the injector can cleanly release all virtual keys before closing.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
