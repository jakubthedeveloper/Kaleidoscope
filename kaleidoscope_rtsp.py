import sys
import os
import re
import math
import time
import threading
from datetime import datetime

import pygame
import cv2

# =========================
# Config (window + visuals)
# =========================
WIDTH, HEIGHT = 900, 700
BG_COLOR = (14, 16, 20)

SLICES = 14                # even number works best\
SPEED_DEG_PER_SEC = 34.0   # rot speed (deg/s), can be +/-; 0 = still
TRAIL_FADE_ALPHA = 30      # higher = shorter trails (10–35 good)

ENV_PATH = ".env"          # Only numbered RTSP_URL_N keys are supported

# =========================
# .env loader (ONLY RTSP_URL_N)
# =========================
def _manual_load_env(path):
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k not in os.environ:  # don't override existing env
                    os.environ[k] = v
    except Exception:
        pass

def _load_dotenv_if_available(path):
    try:
        from dotenv import load_dotenv
        load_dotenv(path, override=False)
        return True
    except Exception:
        return False

def load_numbered_rtsp_sources():
    # Try python-dotenv first; fall back to manual parsing
    if not _load_dotenv_if_available(ENV_PATH):
        _manual_load_env(ENV_PATH)

    numbered = []
    for k, v in os.environ.items():
        m = re.fullmatch(r"RTSP_URL_(\d+)", k, flags=re.IGNORECASE)
        if m:
            idx = int(m.group(1))
            url = v.strip()
            if url:
                numbered.append((idx, url))

    # Sort by index and build (name,url) as (CamN,url)
    numbered.sort(key=lambda x: x[0])
    return [(f"Cam{idx}", url) for idx, url in numbered]

# =========================
# Pygame init
# =========================
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Kaleidoscope (RTSP from .env)")
clock = pygame.time.Clock()
pygame.font.init()
FONT = pygame.font.SysFont(None, 26)
TITLE_FONT = pygame.font.SysFont(None, 48)

# =========================
# RTSP Camera Reader
# =========================
class RTSPCamera:
    def __init__(self, url, name="Camera"):
        self.url = url
        self.name = name
        self.cap = None
        self.lock = threading.Lock()
        self.frame = None
        self.running = False
        self.thread = None
        self.last_ok = False

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    def _open(self):
        try:
            self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return self.cap.isOpened()
        except Exception:
            return False

    def _loop(self):
        retry_delay = 1.0
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                ok = self._open()
                if not ok:
                    self.last_ok = False
                    time.sleep(retry_delay)
                    retry_delay = min(5.0, retry_delay + 0.5)
                    continue
                retry_delay = 1.0

            ok, frame = self.cap.read()
            if not ok or frame is None:
                self.last_ok = False
                time.sleep(0.02)
                continue

            self.last_ok = True
            with self.lock:
                self.frame = frame

    def get_surface(self, target_size):
        with self.lock:
            frame = None if self.frame is None else self.frame.copy()
        if frame is None:
            return None
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if (frame.shape[1], frame.shape[0]) != target_size:
            frame = cv2.resize(frame, target_size, interpolation=cv2.INTER_LINEAR)
        return pygame.image.frombuffer(frame.tobytes(), target_size, "RGB").convert()

# =========================
# Kaleidoscope helpers
# =========================
def make_wedge_mask(size, angle_deg):
    w, h = size
    R = min(w, h) // 2
    cx, cy = w // 2, h // 2
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    steps = max(10, int(angle_deg))
    a0, a1 = -angle_deg / 2, angle_deg / 2
    pts = [(cx, cy)]
    for i in range(steps + 1):
        t = i / steps
        a = math.radians(a0 + t * (a1 - a0))
        x = cx + R * math.sin(a)
        y = cy - R * math.cos(a)
        pts.append((x, y))
    pygame.draw.polygon(mask, (255, 255, 255, 255), pts)
    return mask

def apply_alpha_mask(image_surf, mask_surf):
    out = image_surf.copy()
    out.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return out

def make_circle_mask(size):
    w, h = size
    R = min(w, h) // 2
    cx, cy = w // 2, h // 2
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (cx, cy), R)
    return mask

# =========================
# Geometry & trails
# =========================
def setup_geometry(width, height):
    global R, base_size, center, slice_angle, wedge_mask, circle_mask
    R = min(width, height) // 2 - 30
    base_size = (2 * R, 2 * R)
    center = (width // 2, height // 2)
    slice_angle = 360.0 / SLICES
    wedge_mask = make_wedge_mask(base_size, slice_angle)
    circle_mask = make_circle_mask(base_size)

def rebuild_trails():
    global trail_surface, fade_cover
    sw, sh = screen.get_width(), screen.get_height()
    trail_surface = pygame.Surface((sw, sh), pygame.SRCALPHA)
    trail_surface.fill(BG_COLOR)
    fade_cover = pygame.Surface((sw, sh), pygame.SRCALPHA)
    fade_cover.fill(BG_COLOR)
    fade_cover.set_alpha(TRAIL_FADE_ALPHA)

setup_geometry(WIDTH, HEIGHT)
rebuild_trails()

def render_kaleidoscope(source_img, theta_deg=0.0):
    src = pygame.transform.rotozoom(source_img, theta_deg, 1.0)
    src_canvas = pygame.Surface(base_size, pygame.SRCALPHA)
    rect = src.get_rect(center=(base_size[0] // 2, base_size[1] // 2))
    src_canvas.blit(src, rect)

    base_wedge = apply_alpha_mask(src_canvas, wedge_mask)

    out = pygame.Surface(base_size, pygame.SRCALPHA)
    for i in range(SLICES):
        wedge = pygame.transform.flip(base_wedge, True, False) if (i % 2) else base_wedge
        rotated = pygame.transform.rotozoom(wedge, -i * slice_angle, 1.0)
        rrect = rotated.get_rect(center=(base_size[0] // 2, base_size[1] // 2))
        out.blit(rotated, rrect)

    out = apply_alpha_mask(out, circle_mask)
    return out

# =========================
# UI helpers
# =========================
def draw_centered(surface, text, font, y, color=(230, 232, 236)):
    img = font.render(text, True, color)
    rect = img.get_rect(center=(surface.get_width() // 2, y))
    surface.blit(img, rect)

def splash_screen(lines):
    showing = True
    while showing:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    pygame.quit(); sys.exit(0)
                showing = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                showing = False

        screen.fill(BG_COLOR)
        draw_centered(screen, "Kaleidoscope — RTSP (.env)", TITLE_FONT, screen.get_height() // 2 - 120)
        y = screen.get_height() // 2 - 40
        for i, ln in enumerate(lines):
            draw_centered(screen, ln, FONT, y + i * 28)
        pygame.display.flip()
        clock.tick(60)

# =========================
# Build cameras from .env
# =========================
env_exists = os.path.isfile(ENV_PATH)
if not env_exists:
    screen.fill(BG_COLOR)
    draw_centered(screen, "Missing .env file", TITLE_FONT, screen.get_height() // 2 - 50, (255, 110, 110))
    draw_centered(screen, "Copy .env.dist to .env and tweak RTSP_URL_1, RTSP_URL_2, ...", FONT, screen.get_height() // 2 - 10)
    pygame.display.flip()
    pygame.time.wait(3500)
    pygame.quit()
    sys.exit(1)

CAM_SOURCES = load_numbered_rtsp_sources()
if not CAM_SOURCES:
    splash_screen([
        "No RTSP_URL_N entries found in .env",
        "Add lines like:",
        "RTSP_URL_1=rtsp://login:password@host/path",
        "RTSP_URL_2=rtsp://login:password@host/path",
        "Press any key to exit.",
    ])
    pygame.quit()
    sys.exit(1)

CAMERAS = []
for i, (name, url) in enumerate(CAM_SOURCES, start=1):
    print(url)
    cam = RTSPCamera(url, name)
    cam.start()
    CAMERAS.append(cam)

active_idx = 0

splash_screen([
    f"Loaded sources: {len(CAMERAS)}",
    "SPACE — switch camera",
    "ESC or Q — quit",
    "A — pause / resume animation",
    "LEFT/RIGHT or -/+ — change speed",
    "UP/DOWN — change slices (±2)",
    "P — save snapshot (PNG)",
    "F — toggle fullscreen",
    "Any key/mouse — start",
    "",
    "Author: Jakub Krysakowski"
])

# =========================
# Main loop
# =========================
running = True
t = 0.0
paused = False
fullscreen = False

while running:
    dt = clock.tick(60) / 1000.0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k in (pygame.K_ESCAPE, pygame.K_q):
                running = False
            elif k == pygame.K_SPACE:
                active_idx = (active_idx + 1) % len(CAMERAS)
                trail_surface.fill(BG_COLOR)  # reset trails on switch
            elif k == pygame.K_a:
                paused = not paused
            elif k in (pygame.K_RIGHT, pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                SPEED_DEG_PER_SEC += 2.0
            elif k in (pygame.K_LEFT, pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS):
                SPEED_DEG_PER_SEC -= 2.0
            elif k == pygame.K_p:
                cam = CAMERAS[active_idx]
                src_surf = cam.get_surface(base_size)
                if src_surf is not None:
                    snap = render_kaleidoscope(src_surf, t)
                    os.makedirs("snapshots", exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    cname = cam.name.replace(" ", "_")
                    fname = f"snapshots/{cname}_snap_{timestamp}.png"
                    pygame.image.save(snap, fname)
                    print(f"Saved snapshot: {fname}")
            elif k == pygame.K_UP:
                SLICES = max(2, SLICES + 2)
                setup_geometry(screen.get_width(), screen.get_height())
                trail_surface.fill(BG_COLOR)
            elif k == pygame.K_DOWN:
                SLICES = max(2, SLICES - 2)
                setup_geometry(screen.get_width(), screen.get_height())
                trail_surface.fill(BG_COLOR)
            elif k == pygame.K_f:
                fullscreen = not fullscreen
                if fullscreen:
                    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                else:
                    screen = pygame.display.set_mode((WIDTH, HEIGHT))
                setup_geometry(screen.get_width(), screen.get_height())
                rebuild_trails()

    if not paused:
        t = (t + SPEED_DEG_PER_SEC * dt) % 360.0

    # Trails composition
    trail_surface.blit(fade_cover, (0, 0))

    # Active camera frame
    cam = CAMERAS[active_idx]
    src_surf = cam.get_surface(base_size)
    if src_surf is None:
        trail_surface.fill(BG_COLOR)
        msg = f"Waiting for {cam.name}…"
        draw_centered(trail_surface, msg, FONT, screen.get_height() // 2, (200, 200, 210))
    else:
        kaleido = render_kaleidoscope(src_surf, t)
        trail_surface.blit(kaleido, (center[0] - R, center[1] - R))
        # HUD
        hud = FONT.render(
            f"{cam.name}  |  speed: {SPEED_DEG_PER_SEC:.1f}°/s  |  slices: {SLICES}  |  SPACE: switch",
            True, (225, 225, 230)
        )
        trail_surface.blit(hud, (10, screen.get_height() - 30))

    screen.blit(trail_surface, (0, 0))
    pygame.display.flip()

# =========================
# Cleanup
# =========================
for cam in CAMERAS:
    cam.stop()
pygame.quit()
sys.exit()
cat 
