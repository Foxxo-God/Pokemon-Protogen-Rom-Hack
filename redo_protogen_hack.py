#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path('/tmp/pokefirered-decomp')
TARGET_DIRS = [
    ROOT / 'graphics' / 'object_events' / 'pics',
    ROOT / 'graphics' / 'battle_anims' / 'sprites',
]


def apply_visor(image: Image.Image) -> Image.Image:
    rgba = image.convert('RGBA')
    w, h = rgba.size
    if w < 8 or h < 8:
        return rgba

    alpha = rgba.getchannel('A')
    bbox = alpha.getbbox()
    if not bbox:
        return rgba

    x0, y0, x1, y1 = bbox
    width = max(1, x1 - x0)
    height = max(1, y1 - y0)

    face_x0 = max(0, x0 + width // 8)
    face_x1 = min(w, x1 - width // 8)
    face_y0 = max(0, y0 + height // 6)
    face_y1 = min(h, y0 + max(4, height // 3))

    if face_x1 <= face_x0 or face_y1 <= face_y0:
        face_x0 = max(0, x0 + width // 10)
        face_x1 = min(w, x1 - width // 10)
        face_y0 = max(0, y0 + height // 7)
        face_y1 = min(h, y0 + max(4, height // 2))

    overlay = Image.new('RGBA', rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    radius = max(2, (face_x1 - face_x0) // 10)
    draw.rounded_rectangle(
        (face_x0, face_y0, face_x1, face_y1),
        radius=radius,
        fill=(0, 0, 0, 220),
    )

    # Add a slightly brighter edge to keep a crisp visor silhouette.
    draw.rounded_rectangle(
        (face_x0, face_y0, face_x1, face_y1),
        radius=radius,
        outline=(18, 18, 18, 220),
        width=max(1, min(3, (face_x1 - face_x0) // 16)),
    )

    return Image.alpha_composite(rgba, overlay).convert('P', palette=Image.ADAPTIVE, colors=256)


def main():
    modified = 0
    for target_dir in TARGET_DIRS:
        if not target_dir.exists():
            continue
        for png in sorted(target_dir.rglob('*.png')):
            original = Image.open(png)
            patched = apply_visor(original)
            if patched.mode != 'P':
                patched = patched.convert('P', palette=Image.ADAPTIVE, colors=256)
            if patched.tobytes() != original.convert('P', palette=Image.ADAPTIVE, colors=256).tobytes():
                patched.save(png, format='PNG')
                modified += 1
            original.close()

    print(f'Modified {modified} sprite PNGs in {len(TARGET_DIRS)} directories.')

    # Final ROM title patch. Keep the file valid while matching the protogen theme.
    rom_path = ROOT / 'pokefirered.gba'
    if rom_path.exists():
        data = bytearray(rom_path.read_bytes())
        title_offset = 0xA0
        new_title = b'PROT0GEN FUR'
        data[title_offset:title_offset + len(new_title)] = new_title
        for target in (b'POKEMON FIRE', b'POKEMON\x00FIRE'):
            idx = data.find(target)
            if idx != -1:
                data[idx:idx + len(target)] = b'PROT0GEN FUR'
        rom_path.write_bytes(data)
        print(f'Patched title in {rom_path}')


if __name__ == '__main__':
    main()
