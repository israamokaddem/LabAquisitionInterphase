# WaveLab — Setup & Launch Guide

> **Windows only. Read every step before doing anything.**
> This guide covers two independent interfaces:
> - **Acquisition** → `InterfaceAquisition.py`
> - **Interpretation** → `interface.py`
>
> They do not require the same hardware or the same drivers.
> Install only what applies to your use case.

---

## Table of Contents

1. [What you need before starting](#1-what-you-need-before-starting)
2. [Get the project on your computer](#2-get-the-project-on-your-computer)
3. [Install Python](#3-install-python)
4. [Install Python dependencies](#4-install-python-dependencies)
5. [Install hardware drivers](#5-install-hardware-drivers)
6. [Verify everything is installed](#6-verify-everything-is-installed)
7. [Launch the interfaces](#7-launch-the-interfaces)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. What you need before starting

| Requirement | Details |
|---|---|
| **Operating system** | Windows 10 or Windows 11 — 64-bit only |
| **RAM** | 8 GB minimum |
| **Internet connection** | Required once to download Python and dependencies |
| **Git** | Only if you use the Git clone option below |

**You do NOT need to know how to code.**
You only need to type a few commands in a terminal window.

---

## 2. Get the project on your computer

Choose **one** of the two options below.

---

### Option A — Clone from Git (recommended)

Use this if Git is installed on your computer.
To check, open a terminal and type:

```
git --version
```

If you see a version number, Git is installed. If you see an error, use Option B instead.

**Step 1 — Open a terminal**

Press `Windows + R`, type `cmd`, press Enter.

**Step 2 — Navigate to where you want to save the project**

Example — save it on your Desktop:

```
cd C:\Users\YourName\Desktop
```

Replace `YourName` with your actual Windows username.

**Step 3 — Clone the repository**

```
git clone https://github.com/YOUR_ORG/wavelab.git
```

Replace the URL with the actual repository URL given to you by the team.

**Step 4 — Enter the project folder**

```
cd wavelab
```

You are now inside the project. Go to Step 3.

---

### Option B — Download as ZIP

Use this if Git is not installed or you prefer not to use it.

**Step 1 — Download the ZIP**

- Open the repository page in your browser.
- Click the green button **Code**.
- Click **Download ZIP**.
- The file `wavelab-main.zip` will download to your Downloads folder.

**Step 2 — Extract the ZIP**

- Open your Downloads folder.
- Right-click the ZIP file.
- Click **Extract All...**
- Choose a destination, for example `C:\Users\YourName\Desktop\wavelab`.
- Click **Extract**.

**Step 3 — Open the project folder in a terminal**

Press `Windows + R`, type `cmd`, press Enter. Then type:

```
cd C:\Users\YourName\Desktop\wavelab
```

Replace the path with wherever you extracted the project.

---

## 3. Install Python

**Step 1 — Check if Python is already installed**

In your terminal, type:

```
python --version
```

If you see `Python 3.9.x` or higher, Python is already installed. Skip to Section 4.

If you see an error or a version below 3.9, continue below.

**Step 2 — Download Python**

Go to: `https://www.python.org/downloads/`

Click the yellow button **Download Python 3.x.x** (take the latest 3.x version).

**Step 3 — Install Python**

- Run the downloaded `.exe` file.
- **Critical:** On the first screen, tick the box **Add Python to PATH** before clicking anything else. If you miss this, Python will not work from the terminal.
- Click **Install Now**.
- Wait for installation to complete, then click **Close**.

**Step 4 — Confirm the installation**

Close your terminal, open a new one, and type:

```
python --version
```

You should see something like `Python 3.11.5`.
If you still see an error, restart your computer and try again.

---

## 4. Install Python dependencies

`requirements.txt` is a file included in the project.
It lists every Python library the project needs.
Running it once installs everything automatically.

**Step 1 — Make sure you are inside the project folder**

Your terminal prompt should show the project path.
If not, navigate there:

```
cd C:\Users\YourName\Desktop\wavelab
```

**Step 2 — Run the installation**

```
pip install -r requirements.txt
```

This reads `requirements.txt` and downloads and installs every library listed in it.
It may take 2 to 5 minutes. Lines will scroll — this is normal. Wait until the prompt returns.

**Step 3 — Confirm there are no errors**

The last lines should say `Successfully installed ...`.
If you see a red error line, go to Section 8 — Troubleshooting.

---

### What requirements.txt installs and why

| Library | Used by | What it does |
|---|---|---|
| `PyQt6` | Both interfaces | Draws the windows, buttons, and menus |
| `pyqtgraph` | Both interfaces | Draws the real-time signal graphs |
| `pandas` | Both interfaces | Reads and writes CSV files |
| `numpy` | Both interfaces | Numerical calculations |
| `mcculw` | **Acquisition only** | Communicates with MCC USB-1808X DAQ cards |
| `nidaqmx` | **Acquisition only** | Communicates with National Instruments DAQ cards |
| `opencv-python` | **Interpretation only** | Image processing for free-surface detection |
| `scipy` | **Interpretation only** | Signal processing and spectral analysis |

> `mcculw` and `nidaqmx` are installed by requirements.txt but they only work
> if the corresponding hardware driver is also installed on Windows (see Section 5).
> If you only use the Interpretation interface, you do not need any hardware driver at all.

---

## 5. Install hardware drivers

**This section is for the Acquisition interface only.**
If you only use `interface.py` (Interpretation), skip this entire section.

---

### 5.1 MCC USB-1808X — Acquisition only

**Step 1 — Disconnect the MCC card from the computer before installing the driver.**

**Step 2 — Download MCC DAQ Software**

Go to: `https://digilent.com/reference/software/mccdaq-cd/start`

Download the **MCC DAQ Software** package.
It includes InstaCal and the Universal Library, which mcculw needs to run.

**Step 3 — Install**

- Run the downloaded `.exe`.
- Leave all options checked by default.
- Click through until the installation is complete.
- Do NOT plug in the card yet.

**Step 4 — Connect the card**

After installation finishes, plug the MCC USB-1808X into a USB port.
Windows will recognise it automatically.

**Step 5 — Verify in InstaCal**

- Open the Start menu and search for **InstaCal**.
- Open it. Your card should appear as `Board 0 — USB-1808X`.
- If it does not appear, try a different USB port, close InstaCal, and reopen it.

**Step 6 — Verify in Python**

```
python verifier_installation.py
```

The MCC section should show `[OK]` with the card name and serial number.

> **No physical card?**
> You do not need this driver if you use Simulation mode.
> In the Acquisition interface, tick the **Simulation** checkbox next to MCC USB-1808X.
> The software generates realistic synthetic data without any hardware.

---

### 5.2 National Instruments — Acquisition only

**Step 1 — Download NI-DAQmx**

Go to: `https://www.ni.com/fr-fr/support/downloads/drivers/download.ni-daq-mx.html`

Download the latest version of **NI-DAQmx** for Windows.

**Step 2 — Install**

- Run the downloaded installer.
- Follow the wizard with default settings.
- **Restart your computer when prompted — this step is mandatory.**

**Step 3 — Verify in NI MAX**

- Open the Start menu and search for **NI MAX**.
- Your NI device should appear under **Devices and Interfaces**.
- If it does not appear, check the USB or chassis cable and rescan.

**Step 4 — Verify in Python**

```
python verifier_installation.py
```

The NI section should show `[OK]` with your device name.

---

### 5.3 Kistler LabAmp — Acquisition only

No driver installation is required for Kistler devices.

Requirements:
- The Kistler device must be on the **same local network** as your computer (Ethernet cable).
- You need the **IP address** of the device. It is written on the device or provided by the team (example: `169.254.77.238`).

In the Acquisition interface, tick **Kistler LabAmp (Réseau TCP/IP)** and type the IP address in the field that appears before clicking Scanner.

---

### 5.4 OpenCV — Interpretation only

OpenCV is installed automatically by `requirements.txt`.
No driver or separate installer is needed.

If after running requirements.txt you still get `ModuleNotFoundError: cv2`, run:

```
pip install opencv-python
```

---

## 6. Verify everything is installed

Run the verification script included in the project:

```
python verifier_installation.py
```

Expected output when everything is correct:

```
==================================================
  1. PYTHON VERSION
==================================================
  [OK]  Python 3.11.x — OK

==================================================
  2. COMMON LIBRARIES
==================================================
  [OK]  PyQt6
  [OK]  pyqtgraph
  [OK]  pandas
  [OK]  numpy

==================================================
  3. MCC USB-1808X
==================================================
  [OK]  mcculw (Python library)
  [OK]  MCC cards detected: 2
         Board 0 -> USB-1808X  SN: 21515B5
         Board 1 -> USB-1808X  SN: 2151534

==================================================
  4. NATIONAL INSTRUMENTS
==================================================
  [OK]  nidaqmx (Python library)
  [OK]  NI devices detected: 1
         -> cDAQ9184  (CompactDAQ Chassis)
```

Any line showing `[XX]` means something is missing.
The script prints the exact fix command next to each `[XX]` line.

---

## 7. Launch the interfaces

**Important:** Always open a terminal, navigate to the project folder, and launch the
interface from there. Do not double-click the `.py` file directly — it will not find
the other files it depends on and will crash immediately.

---

### 7.1 Launch the Acquisition interface

**Step 1 — Open a terminal**

Press `Windows + R`, type `cmd`, press Enter.

**Step 2 — Navigate to the project folder**

```
cd C:\Users\YourName\Desktop\wavelab
```

**Step 3 — Launch**

```
python InterfaceAquisition.py
```

The WaveLab Acquisition window opens.

**What this interface requires:**

| Feature | What must be installed |
|---|---|
| MCC USB-1808X (real card) | MCC DAQ Software + card connected via USB |
| MCC USB-1808X (simulation) | Nothing — just tick Simulation in the interface |
| National Instruments | NI-DAQmx driver + device connected |
| Kistler LabAmp | Device on the same network + IP address |
| Calibration and Visualisation | No hardware needed — works with any CSV file |

---

### 7.2 Launch the Interpretation interface

**Step 1 — Open a terminal**

Press `Windows + R`, type `cmd`, press Enter.

**Step 2 — Navigate to the project folder**

```
cd C:\Users\YourName\Desktop\wavelab
```

**Step 3 — Launch**

```
python interface.py
```

The Interpretation window opens.

**What this interface requires:**

| Feature | What must be installed |
|---|---|
| Wave decomposition (all methods) | A calibrated CSV file from WaveLab Acquisition |
| Imagerie mode | A calibration image + a folder of experiment images |
| Hardware | None — this interface never talks to any DAQ card |

---

### 7.3 Running both at the same time

Open two terminal windows and launch one interface in each.
They are completely independent and do not interfere with each other.

---

## 8. Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `'python' is not recognized` | Python not installed or not in PATH | Re-install Python and tick **Add Python to PATH** on the first screen |
| `'pip' is not recognized` | pip missing | Run `python -m ensurepip` then `python -m pip install --upgrade pip` |
| `ModuleNotFoundError: PyQt6` | requirements.txt not run | Run `pip install -r requirements.txt` from inside the project folder |
| `ModuleNotFoundError: mcculw` | Library not installed or MCC DAQ Software missing | Install MCC DAQ Software first, then `pip install mcculw` |
| `ModuleNotFoundError: nidaqmx` | Library not installed or NI-DAQmx missing | Install NI-DAQmx first, then `pip install nidaqmx` |
| `ModuleNotFoundError: cv2` | OpenCV not installed | Run `pip install opencv-python` |
| `0 MCC cards detected` | Driver not installed or card not plugged in | Install MCC DAQ Software, reconnect the card, verify in InstaCal |
| `0 NI devices detected` | Driver not installed or device not connected | Install NI-DAQmx, reconnect, verify in NI MAX |
| Window does not open, no error | Wrong folder in terminal | Make sure terminal is in the project folder before launching |
| `ImportError: cannot import name X` | Launched from wrong folder | `cd` into the project folder and try again |
| `PermissionError: temp_mcc.csv` | Previous acquisition did not close the file | Close WaveLab completely and relaunch |

---

## Quick Summary

```
Step 1  Get the project    git clone <url>   OR   extract the ZIP
Step 2  Install Python     python.org/downloads  ->  tick "Add to PATH"
Step 3  Install libraries  pip install -r requirements.txt
Step 4  Install drivers    MCC DAQ Software (MCC cards) / NI-DAQmx (NI cards)
                           Skip this step if you only use the Interpretation interface
Step 5  Verify             python verifier_installation.py
Step 6  Run Acquisition    python InterfaceAquisition.py
        Run Interpretation python interface.py
```
