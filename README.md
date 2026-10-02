# Bongo Cat Turbo Clicker 🐾

> High-throughput, zero-dependency click farming engine for **BongoCat** (Steam). Powered by native internal Named Pipe Direct IPC (`\\.\pipe\BongoCatxTheFarmerWasReplaced`). Delivers **1,000–2,000+ verified CPS** with **zero synthetic keystrokes**, zero shell hotkey conflicts, zero ghost characters, and undisturbed desktop multitasking.

![Bongo Cat Preview](assets/banner.png)

[![Platform](https://img.shields.io/badge/Platform-Windows_10_|_11-0078D6?logo=windows)](https://github.com)
[![Python](https://img.shields.io/badge/Python-3.7+-3776AB?logo=python)](https://python.org)
[![Dependencies](https://img.shields.io/badge/Dependencies-Zero_(Standard_Library)-brightgreen)](https://github.com)
[![Protocol](https://img.shields.io/badge/Protocol-Named_Pipe_IPC-FF6B6B)](https://github.com)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 🔬 Reverse Engineering Field Notes

Standard mouse macros (Razer Synapse, Logitech G Hub, WLmouse) and conventional autoclickers suffer from severe packet loss or introduce breaking operating system side effects. The evolution of this project addresses each technical hurdle discovered inside BongoCat's binary architecture.

### Phase 1: Why Hardware Macros & Standard Clickers Fail

Analysis of BongoCat’s binary (`BongoCat_Data/Managed/Assembly-CSharp.dll` $\rightarrow$ `GlobalKeyHook`) reveals that the game does **not** consume standard Windows input events (`WM_LBUTTONDOWN` or low-level hooks `WH_MOUSE_LL`). Instead, it executes an internal thread timer polling Win32 `GetAsyncKeyState`:

```csharp
new Timer(Process, null, 0, 16); // Polling loop running at ~60 Hz (16ms)
```

Inside each 16ms tick, the engine inspects an array of 221 supported virtual keys:

```csharp
short state = WinKeyHook.GetAsyncKeyState(vk);
if (!WasPressed[i]) {
    if (state == -32768) { // 0x8000: Transition to DOWN
        WasPressed[i] = true;
        IsDown[i] = true;
    }
} else {
    if (state == 0) {      // Transition to UP
        WasPressed[i] = false;
    }
}
```

* **The Sub-Millisecond Drop:** Hardware mouse macros send `MouseDown` followed by `MouseUp` within 1–2 ms. Because the game only samples input state once every 16 ms, bursts occurring between timer ticks vanish without registering.
* **The State Machine Trap:** For a second click to register, the input **must be sampled in the `UP` state** by at least one polling tick to reset the `WasPressed` latch.

---

### Phase 2: Why Synthetic Key Injection (`keybd_event` / `SendInput`) Is Flawed

Injecting synthetic keystrokes to satisfy the 16ms polling state machine inevitably pollutes the Windows desktop environment:

1. **YouTube 2x Playback Interruption:** Holding `LMB` or `Space` in Chromium browsers to speed up video playback relies on uninterrupted mouse/keyboard down-state tracking. Any global key event broadcasted via `keybd_event` dispatches `WM_KEYDOWN` to the active window, resetting Chromium's hold gesture timer.
2. **The `Win + P` Projector Loop:** Obscure OEM virtual key codes share legacy hardware scancodes. Specifically, `VK_OEM_PA1` (`0xEB`) and `VK_PA1` (`0xFD`) resolve to the hardware display switcher. When pressed while tapping the `Windows` key, Windows fires the display project switcher menu in an infinite cycle.
3. **Ghost Characters & Explorer Drift:** Virtual codes such as `0xE7` or `0xE4` emit character `0` or null bytes into Electron/Chromium text inputs, while unassigned OEM keys trigger navigation skips in Windows Explorer file lists.
4. **Start Menu Cancellation:** Windows cancels Start menu activation if any synthetic key state transition occurs while the physical `Win` key is depressed.

---

### Phase 3: The Breakthrough — Native Named Pipe Direct IPC

Binary inspection of `BongoCat_Data/Managed/Assembly-CSharp.dll` uncovered an official, undocumented IPC client: **`BongoCat.TapTapLootIntegration.Ipc`**.

When BongoCat starts, it launches an internal background worker:
```csharp
private void TheFarmerWasReplacedThread()
{
    while (!_cancellationToken.IsCancellationRequested)
    {
        using (NamedPipeClientStream namedPipeClientStream = 
            new NamedPipeClientStream(".", "BongoCatxTheFarmerWasReplaced", PipeDirection.In))
        {
            namedPipeClientStream.Connect();
            using (StreamReader streamReader = new StreamReader(namedPipeClientStream))
            {
                StreamString streamString = new StreamString(namedPipeClientStream);
                while (!_cancellationToken.IsCancellationRequested)
                {
                    string text = streamString.ReadString();
                    if (!string.IsNullOrEmpty(text))
                    {
                        int num = int.Parse(text);
                        _taps += num;
                    }
                    Thread.Sleep(90);
                }
            }
        }
    }
}
```

On every 90 ms iteration, the received taps are directly pushed into BongoCat's event dispatcher:
```csharp
GlobalKeyHook.Instance.OnKeyPressed.Invoke(_taps);
// -> Cat.Instance.Tap(_taps);
// -> Pets.AddPet(_taps);
```

#### Protocol Specification
* **Pipe Name:** `\\.\pipe\BongoCatxTheFarmerWasReplaced`
* **Transport:** Win32 Named Pipe (Duplex, Byte Stream)
* **Framing:** 
  - `Header`: 2 bytes Big-Endian unsigned integer representing payload byte length (`length // 256`, `length & 255`).
  - `Payload`: UTF-16LE encoded string of the integer tap count (`count.ToString()`).

By hosting this Named Pipe server, our engine delivers batch taps **directly into the game's core click accumulator**.

#### Advantages of Direct IPC
* **Zero Keystrokes:** No virtual keys are sent to Windows. Zero interference with typing, chatting, or gaming.
* **Flawless YouTube 2x Speed:** Holding `LMB` or `Space` on YouTube works 100% without interruptions.
* **Untouched Shell:** Start menu, `Win + P`, `Alt + Tab`, and Explorer selection function completely normally.
* **Deterministic Throughput:** BongoCat consumes exact tap counts with zero dropped clicks.

---

## ⚡ Performance Specs & Presets

| Preset | Batch Size | Frequency | Delivered Throughput | Notes |
| :--- | :---: | :---: | :---: | :--- |
| **🌌 God Mode** | 10,000 taps | 90 ms | **~111,111 CPS** | Millions of clicks in seconds. Zero dropped inputs. |
| **⚡ Hyper** | 1,000 taps | 90 ms | **~11,111 CPS** | Extreme acceleration for instant progression. |
| **🚀 Overdrive** | 100 taps | 90 ms | **~1,111 CPS** | High throughput. Standard fast farming. |
| **💨 Turbo** | 50 taps | 90 ms | **~555 CPS** | Balanced high-speed direct injection. |
| **🎛️ Custom** | 1–1,000,000 taps | 90 ms | **Up to Millions CPS** | Set via direct numerical entry, Quick Jump buttons, or slider. |

$$\text{Throughput (CPS)} = \frac{\text{Taps per Tick}}{0.090\text{ s}}$$

---

## 🎮 Interface & Hotkeys

- **Per-Monitor High-DPI:** Uses Windows `SetProcessDpiAwareness(2)` for razor-sharp rendering on 2K/4K displays at 125–175% scaling.
- **Authentic Artwork:** Embedded high-resolution Bongo Cat art with Lanczos antialiasing.
- **Real-Time Live Telemetry:** Tracks total clicks, instantaneous CPS, and active session duration.
- **Hardware Timer Resolution:** Enforces `timeBeginPeriod(1)` to eliminate Windows sleep jitter.

### Hotkeys

| Hotkey | Function |
| :---: | :--- |
| **`F8`** | **Start / Pause** (Edge-detected background polling thread, instant response) |
| **`F10`** | **Emergency Exit** (Cleanly closes IPC handle and terminates process) |

---

## 🚀 Quickstart

### Prerequisites
* Windows 10 / 11
* Python 3.7+ installed and added to `PATH`
* [BongoCat on Steam](https://store.steampowered.com)

### Launching the Application
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/bongocat-turbo-clicker.git
   cd bongocat-turbo-clicker
   ```
2. Run via launcher:
   - Double-click **`run.bat`** (launches windowed GUI with zero background console window).
   - Or run from terminal: `python bongocat_autoclicker.py`
3. Launch BongoCat (the autoclicker automatically establishes the Named Pipe handshake).
4. Press **`F8`** to start farming.

### Headless / CLI Mode
For automated, minimalist, or SSH environments:
```bash
python bongocat_autoclicker.py --cli
```

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
