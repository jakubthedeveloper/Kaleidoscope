import sys
import os
import math
import pygame
from datetime import datetime

# --- Config ---
WIDTH, HEIGHT = 900, 700
BG_COLOR = (14, 16, 20)
IMAGES_DIR = "images"
SLICES = 14
SPEED_DEG_PER_SEC = 14.0
FADE_ALPHA = 15  # trail fade strength (0–255), higher = shorter trail

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Kaleidoscope")
clock = pygame.time.Clock()
pygame.font.init()
FONT = pygame.font.SysFont(None, 26)
TITLE_FONT = pygame.font.SysFont(None, 48)

# --- Trail surface ---
trail_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
trail_surface.fill((0, 0, 0, 255))

# --- Helpers ---
VALID_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}

def list_images(folder):
    return [
        os.path.join(folder, f)
        for f in sorted(os.listdir(folder))
        if os.path.splitext(f.lower())[1] in VALID_EXTS
    ] if os.path.isdir(folder) else []

def load_and_scale(path, size):
    img = pygame.image.load(path).convert_alpha()
    if img.get_size() != size:
        img = pygame.transform.smoothscale(img, size)
    return img.convert_alpha()

def make_wedge_mask(size, angle_deg):
    w, h = size
    R = min(w, h) // 2
    cx, cy = w // 2, h // 2
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    steps = max(10, int(angle_deg))
    a0, a1 = -angle_deg / 2, angle_deg / 2
    pts = [(cx, cy)] + [
        (
            cx + R * math.sin(math.radians(a0 + i * (a1 - a0) / steps)),
            cy - R * math.cos(math.radians(a0 + i * (a1 - a0) / steps))
        )
        for i in range(steps + 1)
    ]
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

def setup_geometry(width, height):
    global R, base_size, center, slice_angle, wedge_mask, circle_mask
    R = min(width, height) // 2 - 30
    base_size = (2 * R, 2 * R)
    center = (width // 2, height // 2)
    slice_angle = 360.0 / SLICES
    wedge_mask = make_wedge_mask(base_size, slice_angle)
    circle_mask = make_circle_mask(base_size)

def render_kaleidoscope(source_img, theta_deg=0.0):
    src = pygame.transform.rotozoom(source_img, theta_deg, 1.0)
    canvas = pygame.Surface(base_size, pygame.SRCALPHA)
    canvas.blit(src, src.get_rect(center=(base_size[0] // 2, base_size[1] // 2)))
    base_wedge = apply_alpha_mask(canvas, wedge_mask)

    out = pygame.Surface(base_size, pygame.SRCALPHA)
    for i in range(SLICES):
        wedge = pygame.transform.flip(base_wedge, True, False) if i % 2 else base_wedge
        rotated = pygame.transform.rotozoom(wedge, -i * slice_angle, 1.0)
        out.blit(rotated, rotated.get_rect(center=(base_size[0] // 2, base_size[1] // 2)))
    return apply_alpha_mask(out, circle_mask)

def draw_centered(surface, text, font, y, color=(230, 232, 236)):
    img = font.render(text, True, color)
    rect = img.get_rect(center=(surface.get_width() // 2, y))
    surface.blit(img, rect)

def splash_screen():
    lines = [
        "Controls",
        "SPACE — next source image",
        "ESC or Q — quit",
        "A — pause/resume",
        "LEFT/RIGHT or -/+ — change speed",
        "UP/DOWN — change slices",
        "P — save snapshot",
        "F — toggle fullscreen",
        "Any key/mouse — start",
        "",
        "Author: Jakub Krysakowski"
    ]
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    pygame.quit(); sys.exit(0)
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                return
        screen.fill(BG_COLOR)
        draw_centered(screen, "Kaleidoscope", TITLE_FONT, screen.get_height() // 2 - 120)
        for i, ln in enumerate(lines):
            draw_centered(screen, ln, FONT, screen.get_height() // 2 - 40 + i * 28)
        pygame.display.flip()
        clock.tick(60)

# --- Initialize ---
setup_geometry(WIDTH, HEIGHT)
image_paths = list_images(IMAGES_DIR)
if not image_paths:
    screen.fill(BG_COLOR)
    draw_centered(screen, "No images found in ./images", TITLE_FONT, HEIGHT // 2 - 20, (255, 110, 110))
    draw_centered(screen, "Supported: .png .jpg .jpeg .bmp .gif .webp", FONT, HEIGHT // 2 + 20)
    pygame.display.flip(); pygame.time.wait(2500); pygame.quit(); sys.exit(1)

current_idx = 0
raw_image = load_and_scale(image_paths[current_idx], base_size)

splash_screen()

# --- Main loop ---
running = True
paused = False
fullscreen = False
t = 0.0

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
                current_idx = (current_idx + 1) % len(image_paths)
                raw_image = load_and_scale(image_paths[current_idx], base_size)
            elif k == pygame.K_a:
                paused = not paused
            elif k in (pygame.K_RIGHT, pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                SPEED_DEG_PER_SEC += 2.0
            elif k in (pygame.K_LEFT, pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS):
                SPEED_DEG_PER_SEC -= 2.0
            elif k == pygame.K_UP:
                SLICES = max(2, SLICES + 2)
                setup_geometry(screen.get_width(), screen.get_height())
                raw_image = load_and_scale(image_paths[current_idx], base_size)
            elif k == pygame.K_DOWN:
                SLICES = max(2, SLICES - 2)
                setup_geometry(screen.get_width(), screen.get_height())
                raw_image = load_and_scale(image_paths[current_idx], base_size)
            elif k == pygame.K_f:
                fullscreen = not fullscreen
                screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN) if fullscreen else pygame.display.set_mode((WIDTH, HEIGHT))
                setup_geometry(screen.get_width(), screen.get_height())
                raw_image = load_and_scale(image_paths[current_idx], base_size)
                trail_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            elif k == pygame.K_p:
                os.makedirs("snapshots", exist_ok=True)
                fname = f"snapshots/snap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                pygame.image.save(trail_surface, fname)
                print(f"Saved snapshot: {fname}")

    if not paused:
        t = (t + SPEED_DEG_PER_SEC * dt) % 360.0

    # fade old trails
    trail_surface.fill((0, 0, 0, FADE_ALPHA), special_flags=pygame.BLEND_RGBA_SUB)

    # render new kaleidoscope frame
    kaleido = render_kaleidoscope(raw_image, t)
    trail_surface.blit(kaleido, (center[0] - R, center[1] - R))

    screen.blit(trail_surface, (0, 0))
    pygame.display.flip()

pygame.quit()
sys.exit()

