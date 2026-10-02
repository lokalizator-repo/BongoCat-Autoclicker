<div align="center">
  <img src="assets/bongo_icon.png" width="160" alt="Bongo Cat Auto Clicker Icon">
  <h1>Bongo Cat Auto Clicker 🐾</h1>
  <p><b>High-throughput, zero-input clicker for BongoCat (Steam)</b></p>

  <p>
    <a href="https://github.com/lokalizator-repo/BongoCat-Autoclicker/releases/latest"><img src="https://img.shields.io/github/v/release/lokalizator-repo/BongoCat-Autoclicker?color=brightgreen&label=Download%20EXE" alt="Download EXE"></a>
    <img src="https://img.shields.io/badge/Platform-Windows_10_|_11-0078D6?logo=windows" alt="Platform">
    <img src="https://img.shields.io/badge/Dependencies-Zero-success" alt="Zero Dependencies">
    <img src="https://img.shields.io/badge/License-MIT-blue" alt="License">
  </p>
</div>

---

### 🐾 How It Works

Conventional autoclickers and mouse macros (Razer, Logitech) simulate physical mouse or keyboard clicks. This causes key conflicts, input lag, and caps out around 60 clicks per second due to the game's polling loop.

**Bongo Cat Auto Clicker connects directly to the game's internal IPC pipe (`Named Pipe`):**
- ⚡ **Zero OS interference** — Does not send virtual keystrokes or mouse clicks. You can type, game, or browse freely while it runs in the background.
- 🚀 **Extreme throughput** — From a gentle 1,000 taps to the game's hard cap of 2.14 billion per tick.
- 🎛️ **Smooth controls** — Real-time telemetry, logarithmic speed slider, and global hotkey control.

---

### 🚀 Quickstart

#### Option 1: Standalone `.exe` (Recommended)
1. Download **[BongoCatAutoClicker.exe](https://github.com/lokalizator-repo/BongoCat-Autoclicker/releases/latest)** from the [Releases](https://github.com/lokalizator-repo/BongoCat-Autoclicker/releases) page.
2. Launch **BongoCat** on Steam.
3. Open `BongoCatAutoClicker.exe` and press **F8** to start / pause.

#### Option 2: Run from Source
Requires Python 3.8+:
```bash
git clone https://github.com/lokalizator-repo/BongoCat-Autoclicker.git
cd BongoCat-Autoclicker
run.bat
```

---

### ⌨️ Hotkeys

| Key | Action |
| :---: | :--- |
| **`F8`** | **Start / Pause** (Works globally in the background) |
| **`F10`** | **Quick Exit** |

---

### ⚡ Speed Presets

Click **Speed Settings** to pick a preset or enter any custom batch size (supports `k`, `m`, `b`, `max` suffixes):

| Preset | Taps / Batch | Estimated Rate | Description |
| :---: | :---: | :---: | :--- |
| **1,000** | 1,000 | ~11,000 CPS | Steady baseline farming |
| **100,000** | 100,000 | ~1.1M CPS | Rapid progression |
| **1,000,000** | 1,000,000 | ~11.1M CPS | Tens of millions in seconds |
| **100,000,000** | 100,000,000 | ~1.11B CPS | Over a billion clicks per second |
| **MAX** | 2,147,483,646 | 2.14B / tap | Game's hard integer cap |

> 💡 **Why does the score stop increasing at ~2.14 Billion?**  
> BongoCat stores points as a 32-bit signed integer (`int32`), which hard-caps at `2,147,483,646`. Spending points in the in-game shop frees up balance to farm more.

---

### 📄 License

Distributed under the [MIT](LICENSE) License.
