# 🌌 AstroPi Tracker

![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)
![GUI](https://img.shields.io/badge/GUI-PyQt6-orange)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red)

**AstroPi Tracker** is a high-precision, Python-based firmware and Observatory Dashboard for controlling DIY Equatorial Mounts (Isosceles Barn Door Trackers). 

Engineered for the Raspberry Pi, it leverages the GPIO interface to drive NEMA 17 stepper motors with microsecond-level precision, enabling long-exposure astrophotography by mathematically compensating for the Earth's sidereal rotation.

## 🚀 Technical Highlights

- **Isosceles Tangential Compensation:** Unlike basic trackers running at a constant speed, this firmware dynamically calculates the required stepper RPM in real-time to compensate for the tangent error inherent in straight-rod push mechanisms.
- **Observatory Dashboard (PyQt6):** A dark-themed, data-rich graphical interface providing real-time telemetry (Time, Angle, RPM) and a live-rendering performance graph using `QPainter`.
- **Asynchronous Architecture:** The motor pulse generator runs on a dedicated background **Thread**, decoupling the real-time microsecond hardware loops from the UI event loop to ensure zero frame-drops in tracking.
- **Active Thermal Management:** Automatically toggles the stepper driver's `ENABLE` pin, cutting current to the coils during idle states (STOP) to prevent motor overheating and conserve battery power.

---

## 🧮 The Mathematics

To maintain a constant angular velocity of the mount matching the Earth's rotation ($0.25^\circ$/min), the linear speed of the threaded rod must decay over time as the isosceles triangle opens.

The firmware calculates the instantaneous target RPM dynamically using:

$$RPM = \frac{R \cdot \omega \cdot \cos(\frac{\omega \cdot t}{2})}{P}$$

Where:
* $R$ = Radius from hinge to rod ($300 \text{ mm}$)
* $\omega$ = Earth's angular velocity ($0.0043633 \text{ rad/min}$)
* $t$ = Tracking time elapsed (minutes)
* $P$ = Thread pitch of the rod ($0.7 \text{ mm}$ for M4)

---

## 🏗️ System Architecture

### Hardware Interface

The system is designed for **A4988** or **DRV8825** stepper drivers interacting with the Raspberry Pi BCM GPIO pins.

| Driver Pin | RPi GPIO (BCM) | Physical Pin | Function |
| :--- | :--- | :--- | :--- |
| **DIR** | `GPIO 21` | Pin 40 | Direction Control (CW/CCW) |
| **STEP** | `GPIO 20` | Pin 38 | Pulse Signal (Square Wave) |
| **ENABLE** | `GPIO 16` | Pin 36 | Active Low Logic (LOW=ON, HIGH=OFF) |
| **VMOT** | 12V DC | - | Motor Power Supply |
| **VDD** | 3.3V | Pin 1 | Logic Voltage Reference |

> **⚠️ Critical:** Ensure the **GND** of the 12V Power Supply is tied to the **RPi GND** to complete the logic circuit and prevent hardware damage.

---

## 💻 Getting Started

### Prerequisites
You will need a Raspberry Pi running a desktop environment (for the UI) and Python 3.7+.

1. Install the required system dependencies and Python libraries:
```bash
# Update system packages
sudo apt-get update

# Install PyQt6 and GPIO libraries
pip install RPi.GPIO PyQt6
