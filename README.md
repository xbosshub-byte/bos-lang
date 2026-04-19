# BOS Language (bos-lang) v2.5

**BOS (Board Operating Script)** is a lightweight, cross-platform programming language designed specifically for IoT devices, POS terminals, and Smart Vending Machines. 

It provides seamless hardware control, built-in networking, and an intuitive syntax, allowing developers to focus on business logic rather than low-level configurations.

## 🌟 Key Features
- **Cross-Platform Auto-Detect:** Runs perfectly on PC (Windows/Linux), Raspberry Pi 5, and MicroPython boards (ESP32, Pico W) using the exact same script.
- **Built-in MQTT & Wi-Fi:** Native commands to connect to networks and publish MQTT messages.
- **Hardware I/O Ready:** Read analog/digital sensors and control relays/motors directly via simple commands (`read_sensor`, `pin_on`, `pin_off`).
- **TM1637 Display Support:** Built-in support for 7-Segment displays with auto-downloading libraries from BOSSHUB.
- **Interactive POS/Vending:** Wait for physical button presses (`wait_btn`) or accept keyboard/barcode scanner inputs (`input`).

## 🚀 Quick Installation
```bash
git clone [https://github.com/xbosshu/bos-lang.git](https://github.com/xbosshu/bos-lang.git)
cd bos-lang
pip install -e .
