#!/usr/bin/env python3
"""Generate Mount Sinai branded app icon with two-peak mountain (left peak higher).
Cyan and magenta as distinct filled shapes with violet at their intersection."""

from PIL import Image, ImageDraw
import os

# Mount Sinai brand colors
NAVY = (0, 0, 45)          # #00002D background
CYAN = (6, 171, 235)       # #06ABEB
MAGENTA = (217, 5, 141)    # #D9058D
VIOLET = (33, 35, 112)     # #212370 overlap
WHITE = (255, 255, 255)

SIZE = 1024


def generate_icon():
    w = h = SIZE
    img = Image.new('RGBA', (w, h), (*NAVY, 255))

    # Subtle radial glow behind mountain
    glow = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    for i in range(80, 0, -1):
        r = int(w * 0.38 * i / 80)
        alpha = int(15 * (80 - i) / 80)
        glow_draw.ellipse(
            [w // 2 - r, int(h * 0.40) - r, w // 2 + r, int(h * 0.40) + r],
            fill=(6, 171, 235, alpha)
        )
    img = Image.alpha_composite(img, glow)

    # ── Mountain geometry ──
    # Two peaks, left is taller. The cyan shape is offset slightly left,
    # magenta offset slightly right, so they overlap in the middle.

    offset = 28  # How far apart the two layers are

    # Shared silhouette control points
    left_peak = (int(w * 0.28), int(h * 0.20))
    right_peak = (int(w * 0.62), int(h * 0.34))
    saddle = (int(w * 0.44), int(h * 0.44))
    base_left = (int(w * 0.06), int(h * 0.72))
    base_right = (int(w * 0.86), int(h * 0.72))

    # Cyan mountain (shifted left)
    cyan_pts = [
        (base_left[0] - offset, base_left[1]),
        (left_peak[0] - offset, left_peak[1]),
        (saddle[0] - offset, saddle[1]),
        (right_peak[0] - offset, right_peak[1]),
        (base_right[0] - offset, base_right[1]),
    ]

    # Magenta mountain (shifted right)
    magenta_pts = [
        (base_left[0] + offset, base_left[1]),
        (left_peak[0] + offset, left_peak[1]),
        (saddle[0] + offset, saddle[1]),
        (right_peak[0] + offset, right_peak[1]),
        (base_right[0] + offset, base_right[1]),
    ]

    # Create layers
    cyan_layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(cyan_layer).polygon(cyan_pts, fill=(*CYAN, 255))

    magenta_layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(magenta_layer).polygon(magenta_pts, fill=(*MAGENTA, 255))

    # Composite with violet overlap using pixel logic
    mountain = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    cp = cyan_layer.load()
    mp = magenta_layer.load()
    mt = mountain.load()

    for y in range(h):
        for x in range(w):
            c_a = cp[x, y][3]
            m_a = mp[x, y][3]
            if c_a > 0 and m_a > 0:
                mt[x, y] = (*VIOLET, 255)
            elif c_a > 0:
                mt[x, y] = cp[x, y]
            elif m_a > 0:
                mt[x, y] = mp[x, y]

    img = Image.alpha_composite(img, mountain)

    # ── Snow highlight on left peak ──
    snow = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    snow_draw = ImageDraw.Draw(snow)
    pk = left_peak
    snow_pts = [
        (pk[0], pk[1]),
        (pk[0] - int(w * 0.035), pk[1] + int(h * 0.055)),
        (pk[0] + int(w * 0.035), pk[1] + int(h * 0.055)),
    ]
    snow_draw.polygon(snow_pts, fill=(*WHITE, 50))
    img = Image.alpha_composite(img, snow)

    # ── Capsule ──
    draw = ImageDraw.Draw(img)
    cap_w = int(w * 0.28)
    cap_h = int(h * 0.06)
    cx, cy = int(w * 0.50), int(h * 0.82)
    x1 = cx - cap_w // 2
    y1 = cy - cap_h // 2
    x2 = cx + cap_w // 2
    y2 = cy + cap_h // 2
    r = cap_h // 2

    # Full capsule outline
    draw.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=WHITE)
    # Right half cyan
    draw.rounded_rectangle([cx, y1, x2, y2], radius=r, fill=CYAN)
    # Clean join
    draw.rectangle([cx - 1, y1, cx + 1, y2], fill=CYAN)
    # Divider
    draw.line([(cx, y1), (cx, y2)], fill=NAVY, width=3)

    # ── Final RGB ──
    final = Image.new('RGB', (w, h), NAVY)
    final.paste(img, mask=img.split()[3])
    return final


def main():
    master = generate_icon()

    project = '/Users/habtamu/Documents/pharmacy_pickup_app_dev'
    ios_icon_dir = f'{project}/ios/Runner/Assets.xcassets/AppIcon.appiconset'

    master.save(f'{project}/app_icon_master.png', 'PNG')
    print('Saved master: app_icon_master.png')

    ios_sizes = {
        'Icon-App-20x20@1x.png': 20,
        'Icon-App-20x20@2x.png': 40,
        'Icon-App-20x20@3x.png': 60,
        'Icon-App-29x29@1x.png': 29,
        'Icon-App-29x29@2x.png': 58,
        'Icon-App-29x29@3x.png': 87,
        'Icon-App-40x40@1x.png': 40,
        'Icon-App-40x40@2x.png': 80,
        'Icon-App-40x40@3x.png': 120,
        'Icon-App-60x60@2x.png': 120,
        'Icon-App-60x60@3x.png': 180,
        'Icon-App-76x76@1x.png': 76,
        'Icon-App-76x76@2x.png': 152,
        'Icon-App-83.5x83.5@2x.png': 167,
        'Icon-App-1024x1024@1x.png': 1024,
    }

    for filename, size in ios_sizes.items():
        resized = master.resize((size, size), Image.LANCZOS)
        resized.save(f'{ios_icon_dir}/{filename}', 'PNG')
        print(f'  {filename} ({size}x{size})')

    print('\nDone!')


if __name__ == '__main__':
    main()
