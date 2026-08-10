# Kei Audio

Kei Audio is a system-wide audio equalizer and enhancer for Linux. It provides a graphical user interface and a system tray applet to easily manage your audio presets and enable spatial audio.

## Features

- **System-Wide Equalizer:** Apply audio enhancements across all applications.
- **Audio Presets:** Switch between different audio profiles quickly.
- **Spatial Audio:** Enhance your listening experience with spatial audio support.
- **System Tray Integration:** Run in the background and access controls directly from the system tray.
- **Autostart Support:** Can be configured to start automatically on login.

## Requirements

Kei Audio relies on `pulseaudio` (or `pipewire-pulse`) and Python. The following dependencies are required:

- `python3`
- `tk` (for the graphical interface)
- `libpulse` (for system audio manipulation)
- `python-pystray` (for the system tray icon)
- `python-pillow` (for tray icon image processing)

## Installation

An installation script is provided for Arch Linux and its derivatives (using `pacman`).

1. Clone or download this repository to your local machine.
2. Open a terminal and navigate to the project directory.
3. Make the installation script executable:
   ```bash
   chmod +x Install.sh
   ```
4. Run the installation script:
   ```bash
   ./Install.sh
   ```
   The script will ask for root privileges to install the required packages via `pacman` and then create a desktop entry so you can launch Kei Audio from your application menu.

### Manual Installation (Other Distributions)

If you are not using an Arch-based distribution, you can install the dependencies manually using your package manager and `pip`:

1. Install `tk` (often provided by a package like `python3-tk`) and `libpulse` using your distribution's package manager (e.g., `apt`, `dnf`, `zypper`).
2. Install the Python dependencies using `pip`:
   ```bash
   pip install pystray pillow
   ```
3. Run the application directly:
   ```bash
   python3 kei_main.py
   ```

## Usage

- **Launch from Menu:** If you used the installation script, find "Kei Audio" in your application launcher.
- **Command Line:**
  - Launch with UI and tray: `python3 kei_main.py`
  - Launch minimized to tray only: `python3 kei_main.py --tray`
- **System Tray:** When running, Kei Audio resides in your system tray. Right-click the icon to switch presets, toggle spatial audio, show the main window, or quit the application.

## Support Me

- https://sociabuzz.com/kanagawa_yamada/tribe (Global)
- https://t.me/KLAGen2/86 (QRIS)
- https://www.paypal.me/KanagawaYamada (PayPal)
