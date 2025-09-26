# Pygame Kaleidoscope — two flavors: Images & RTSP

https://irok84.itch.io/kaleidoscope-projection

Read images from files or a stream from your camera and make eye-candy Kaleidoscope effect.

---

## 🍨 Variants

### 1) `kaleidoscope.py` — Images folder
- Loads still images from `./images/`
- Saves snapshots to `./snapshots/` (auto-created)
- Great for artwork, textures, and pattern experiments

### 2) `kaleidoscope_rtsp.py` — RTSP streams
- Reads **one or more** RTSP camera streams
- Sources are defined in `.env` as numbered keys:  
  `RTSP_URL_1=...`, `RTSP_URL_2=...`, etc.
- Full screen mode
- Snapshot to png files

---

## 📦 Requirements

- **Python 3.9+**
- Common:
  - `pygame`
- RTSP version only:
  - `opencv-python`
  - *(optional)* `python-dotenv` (auto-load `.env`; manual loader included)

Install:

```bash
pip install pygame
# for RTSP version:
pip install opencv-python python-dotenv
```

## 📁 Folders & Files
```bash
.
├─ kaleidoscope.py           # images version
├─ kaleidoscope_rtsp.py      # RTSP version
├─ images/                   # put source images here (png/jpg/webp/...)
├─ snapshots/                # auto-created for saved PNG snapshots
├─ .env                      # RTSP config (not committed)
├─ .env.dist                 # example to copy
└─ README.md                 # this file
```

## ⚙️ Configuration
### Images version (kaleidoscope.py)
Drop your images into ./images/.

Supported: .png .jpg .jpeg .bmp .gif .webp

Snapshots go to ./snapshots/ as snap_YYYYMMDD_HHMMSS.png.

### RTSP version (kaleidoscope_rtsp.py)
Format of the .env file:

```dotenv
RTSP_URL_1=rtsp://login:password@ip_or_host.one/path
RTSP_URL_2=rtsp://login:password@ip_or_host.two/path
# RTSP_URL_3=...
# RTSP_URL_4=...
```

If .env is missing, the app shows:

Copy .env.dist to .env and tweak RTSP_URL_1, RTSP_URL_2, ...

Sample .env.dist:

```dotenv
# Copy to .env and edit:
RTSP_URL_1=rtsp://user:pass@192.168.0.10:554/stream1
RTSP_URL_2=rtsp://user:pass@192.168.0.11:554/stream2
```

## ▶️ Run
```bash
# Images variant
python kaleidoscope.py

# RTSP variant
python kaleidoscope_rtsp.py
```

On launch you’ll see a splash screen with controls. Press any key to start.

## 🎛️ Controls

| Key         | Action                               |
| ----------- | ------------------------------------ |
| ENTER       | switch to next camera (RTSP version) |
| SPACE       | next image or stream                 |
| A           | pause, resume                        |
| up, down    | slices                               |
| left, right | speed                                |
| F           | full screen                          |
| P           | snapshot                             |
| ESC, Q      | quit                                 |

## 🔧 Tips
Fewer SLICES ⇒ faster rendering.

RTSP: ensure FFmpeg support in OpenCV; test URLs with VLC/ffplay.

## 📄 License

MIT

## 🙌 Credits

Built with Pygame and OpenCV. FFmpeg powers RTSP decoding.

## 🥷🏻Author

Jakub Krysakowski
