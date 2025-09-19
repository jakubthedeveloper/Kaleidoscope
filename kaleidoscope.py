import sys
import math
import pygame

# --- Config ---
WIDTH, HEIGHT = 900, 700
BG_COLOR = (14, 16, 20)
IMAGE_PATH = "image.png"  # put your image here
SLICES = 20               # number of triangular wedges (even number works best)
SPEED_DEG_PER_SEC = 10

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Kaleidoscope")
clock = pygame.time.Clock()

def load_image(size):
    img = pygame.image.load(IMAGE_PATH).convert_alpha()
    return img

def make_wedge_mask(size, angle_deg):
    """
    Create a mask for a triangular 'wedge' centered vertically:
    The wedge spans from -angle/2 to +angle/2 degrees around the vertical axis (pointing up).
    """
    w, h = size
    R = min(w, h) // 2
    cx, cy = w // 2, h // 2

    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    # Approximate arc with polyline
    steps = max(10, int(angle_deg))  # one vertex per degree (min 10)
    a0 = -angle_deg / 2
    a1 = +angle_deg / 2

    points = [(cx, cy)]
    for i in range(steps + 1):
        t = i / steps
        a = math.radians(a0 + t * (a1 - a0))
        x = cx + R * math.sin(a)    # sin for x so 0deg points up along vertical
        y = cy - R * math.cos(a)    # cos for y (screen y grows down)
        points.append((x, y))
    pygame.draw.polygon(mask, (255, 255, 255, 255), points)
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

# --- Prepare base geometry ---
R = min(WIDTH, HEIGHT) // 2 - 30
base_size = (2*R, 2*R)
center = (WIDTH // 2, HEIGHT // 2)
slice_angle = 360.0 / SLICES

# Base image (scaled to the kaleidoscope square)
raw_image = load_image(base_size)
if raw_image.get_size() != base_size:
    raw_image = pygame.transform.smoothscale(raw_image, base_size)

# Precompute masks
wedge_mask = make_wedge_mask(base_size, slice_angle)
circle_mask = make_circle_mask(base_size)

def render_kaleidoscope(source_img, theta_deg=0.0):
    """
    Render the kaleidoscope into a (2R x 2R) surface centered on the screen.
    theta_deg rotates the source image (for animation).
    """
    # Rotate source image for motion effect
    src = pygame.transform.rotozoom(source_img, theta_deg, 1.0)

    # Recenter/resize rotated source back to base_size canvas
    # Make a fresh canvas and blit rotated image centered.
    src_canvas = pygame.Surface(base_size, pygame.SRCALPHA)
    rect = src.get_rect(center=(base_size[0]//2, base_size[1]//2))
    src_canvas.blit(src, rect)

    # Compute a single wedge from the (possibly rotated) source
    base_wedge = apply_alpha_mask(src_canvas, wedge_mask)

    # Compose all wedges onto a target canvas
    out = pygame.Surface(base_size, pygame.SRCALPHA)
    for i in range(SLICES):
        # Mirror every other slice across the wedge axis to get the classic kaleidoscope reversal
        if i % 2 == 1:
            wedge = pygame.transform.flip(base_wedge, True, False)  # horizontal flip (around vertical axis)
        else:
            wedge = base_wedge

        # Rotate the wedge to its sector i
        rotated = pygame.transform.rotozoom(wedge, -i * slice_angle, 1.0)
        rrect = rotated.get_rect(center=(base_size[0]//2, base_size[1]//2))
        out.blit(rotated, rrect)

    # Clip to a circle so the result looks like a scope
    out = apply_alpha_mask(out, circle_mask)
    return out

running = True
t = 0.0
while running:
    dt = clock.tick(60) / 1000.0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # ANIMATE
    t = (t + SPEED_DEG_PER_SEC * dt) % 360.0

    screen.fill(BG_COLOR)
    kaleido = render_kaleidoscope(raw_image, t)
    screen.blit(kaleido, (center[0] - R, center[1] - R))

    pygame.display.flip()

pygame.quit()
sys.exit()

