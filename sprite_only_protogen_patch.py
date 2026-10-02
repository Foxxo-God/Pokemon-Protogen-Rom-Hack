#!/usr/bin/env python3
from pathlib import Path

TARGET_ROOT = Path('/tmp/pokefirered-decomp')


def is_target_palette(path: Path) -> bool:
    if path.suffix != '.pal':
        return False
    rel = str(path)
    return (
        'graphics/pokemon/' in rel
        or '/graphics/trainers/palettes/' in rel
        or '/graphics/object_events/palettes/' in rel
    )


def protogenize_color(color):
    r, g, b = color
    avg = (r + g + b) / 3
    if avg < 35:
        # Black / near-black accents: keep them crisp, but add a cool cyan edge
        r = max(0, r - 8)
        g = min(255, g + 12)
        b = min(255, b + 18)
    elif avg < 90:
        r = max(0, r - 12)
        g = min(255, g + 18)
        b = min(255, b + 22)
    elif avg < 170:
        r = max(0, r - 18)
        g = min(255, g + 20)
        b = min(255, b + 28)
    elif avg < 220:
        r = max(0, r - 8)
        g = min(255, g + 10)
        b = min(255, b + 15)
    else:
        # Keep the brighter palette natural but subtly cooler
        r = max(0, r - 4)
        g = min(255, g + 5)
        b = min(255, b + 8)

    # Preserve natural skin / warm tones by softening the shift on warm colors.
    if r >= g + 20 and b <= g + 12:
        r = min(255, r + 4)
        g = max(0, g - 4)
        b = max(0, b - 6)

    return (r, g, b)


def process_palette(path: Path) -> bool:
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines()
    if len(lines) < 4 or lines[0].strip() != 'JASC-PAL':
        return False
    try:
        count = int(lines[2].strip())
    except ValueError:
        return False
    color_lines = lines[3:3 + count]
    if len(color_lines) < count:
        return False

    updated = []
    changed = False
    for line in color_lines:
        parts = line.strip().split()
        if len(parts) != 3:
            updated.append(line)
            continue
        rr, gg, bb = (int(p) for p in parts)
        nn = protogenize_color((rr, gg, bb))
        if nn != (rr, gg, bb):
            changed = True
        updated.append(f'{nn[0]} {nn[1]} {nn[2]}')

    if not changed:
        return False

    new_lines = lines[:3] + updated + lines[3 + count:]
    path.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')
    return True


def main() -> None:
    repo = TARGET_ROOT
    if not repo.exists():
        raise FileNotFoundError(f'Missing repo: {repo}')

    modified = 0
    for path in sorted(repo.rglob('*.pal')):
        if is_target_palette(path):
            if process_palette(path):
                modified += 1
                print(f'Updated {path.relative_to(repo)}')

    print(f'Finished. Updated {modified} sprite palettes.')


if __name__ == '__main__':
    main()
