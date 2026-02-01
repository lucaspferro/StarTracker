# 🌌 AstroPi Tracker

![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red)

**AstroPi Tracker** is a high-precision, Python-based firmware for controlling DIY Equatorial Mounts (Star Trackers).

It leverages the **Raspberry Pi GPIO** interface to drive Nema 17 stepper motors with microsecond-level precision, enabling long-exposure astrophotography by compensating for the Earth's rotation (Sidereal Tracking).

## 🚀 Technical Highlights

- **Drift Compensation Algorithm:** Utilizes `time.perf_counter()` to calculate and compensate for execution latency, ensuring zero cumulative drift over long tracking sessions.
- **Asynchronous Architecture:** The motor pulse generator runs on a dedicated background **Thread**, decoupling the real-time hardware control from the User Interface (CLI).
- **Smooth Ramping (Soft Start/Stop):** Implements acceleration and deceleration curves during the *Rewind* phase to prevent mechanical stress and camera shake.
- **Active Thermal Management:** Automatically toggles the stepper driver's `ENABLE` pin, cutting current to the coils during idle states to prevent motor overheating and conserve power.
- **Modern Packaging:** Built using the `src` layout and `pyproject.toml` standards (PEP 621), fully compatible with modern pip workflows.

---

## 🏗️ System Architecture

### Hardware Interface

The system is designed for the **A4988** or **DRV8825** stepper drivers interacting with the Raspberry Pi BCM GPIO.

| Driver Pin | RPi GPIO (BCM) | Physical Pin | Function |
| :--- | :--- | :--- | :--- |
| **DIR** | `GPIO 21` | Pin 40 | Direction Control (CW/CCW) |
| **STEP** | `GPIO 20` | Pin 38 | Pulse Signal (Square Wave) |
| **ENABLE** | `GPIO 16` | Pin 36 | Active Low Logic (LOW=ON, HIGH=OFF) |
| **VMOT** | 12V DC | - | Motor Power Supply |
| **VDD** | 3.3V | Pin 1 | Logic Voltage Reference |

> **⚠️ Critical:** Ensure the **GND** of the 12V Power Supply is tied to the **RPi GND** to complete the logic circuit.

### Directory Structure

```text
├── pyproject.toml       # Build system and dependencies definition
├── src/
│   └── astropi/
│       ├── __init__.py  # Package initialization
│       ├── cli.py       # Command Line Interface (Main Entry Point)
│       └── motor.py     # Hardware Abstraction Layer & Physics Engine