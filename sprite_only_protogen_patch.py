#!/usr/bin/env python3
from collections import deque
from pathlib import Path

from PIL import Image

TARGET_ROOT = Path('/tmp/pokefirered-decomp')
POKEMON_ROOT = TARGET_ROOT / 'graphics/pokemon'
TRAINER_ROOT = TARGET_ROOT / 'graphics/trainers'
PEOPLE_ROOT = TARGET_ROOT / 'graphics/object_events/pics/people'


def palette_indices(image: Image.Image) -> tuple[int, int, int]:
    palette = image.getpalette() or []
    transparent = image.info.get('transparency', 0)
    if not isinstance(transparent, int):
        transparent = 0
    indexes = [index for index in range(16) if index != transparent and len(palette) >= (index + 1) * 3]
    if not indexes:
        return 1, 1, transparent
    black = min(indexes, key=lambda index: sum(palette[index * 3:index * 3 + 3]))
    highlight = max(indexes, key=lambda index: sum(palette[index * 3:index * 3 + 3]))
    return black, highlight, transparent


def bounds(image: Image.Image, transparent: int) -> tuple[int, int, int, int] | None:
    pixels = image.load()
    occupied = [
        (x, y)
        for y in range(image.height)
        for x in range(image.width)
        if pixels[x, y] != transparent
    ]
    if not occupied:
        return None
    xs, ys = zip(*occupied)
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def dark_components(image: Image.Image, black: int, box: tuple[int, int, int, int]) -> list[tuple[float, float, int]]:
    x0, y0, x1, y1 = box
    y_limit = min(y1, y0 + int((y1 - y0) * 0.78))
    pixels = image.load()
    seen: set[tuple[int, int]] = set()
    components = []

    for y in range(y0, y_limit):
        for x in range(x0, x1):
            if pixels[x, y] != black or (x, y) in seen:
                continue
            queue = deque([(x, y)])
            seen.add((x, y))
            points = []
            while queue:
                current_x, current_y = queue.popleft()
                points.append((current_x, current_y))
                for next_y in range(current_y - 1, current_y + 2):
                    for next_x in range(current_x - 1, current_x + 2):
                        point = (next_x, next_y)
                        if (
                            x0 <= next_x < x1
                            and y0 <= next_y < y_limit
                            and point not in seen
                            and pixels[next_x, next_y] == black
                        ):
                            seen.add(point)
                            queue.append(point)
            if 1 <= len(points) <= 10:
                components.append((
                    sum(point[0] for point in points) / len(points),
                    sum(point[1] for point in points) / len(points),
                    len(points),
                ))
    return components


def pokemon_face_anchor(image: Image.Image, black: int, box: tuple[int, int, int, int]) -> tuple[int, int, int]:
    x0, y0, x1, y1 = box
    width = x1 - x0
    height = y1 - y0
    components = dark_components(image, black, box)
    rows = image.load()
    pairs = []

    for index, first in enumerate(components):
        for second in components[index + 1:]:
            dx = abs(first[0] - second[0])
            dy = abs(first[1] - second[1])
            center_x = (first[0] + second[0]) / 2
            center_y = (first[1] + second[1]) / 2
            if not (3 <= dx <= 22 and dy <= 4 and y0 + height * 0.12 <= center_y <= y0 + height * 0.78):
                continue

            row = round(center_y)
            occupied_x = [x for x in range(x0, x1) if rows[x, row] != 0]
            row_center = (min(occupied_x) + max(occupied_x)) / 2 if occupied_x else (x0 + x1) / 2
            sprite_center = (x0 + x1) / 2
            score = (
                abs(center_x - row_center) * 0.55
                + abs(center_x - sprite_center) * 0.15
                + abs(dx - 9) * 0.15
                + (first[2] + second[2]) * 0.45
            )
            pairs.append((score, center_x, center_y, dx))

    if pairs:
        _, center_x, center_y, eye_spacing = min(pairs)
        visor_width = max(10, min(17, round(eye_spacing + 8)))
    else:
        center_x = (x0 + x1) / 2
        center_y = y0 + height * 0.38
        visor_width = max(9, min(16, round(width * 0.36)))

    return round(center_x), round(center_y) - 2, visor_width


def draw_visor(
    image: Image.Image,
    center_x: int,
    top: int,
    width: int,
    black: int,
    highlight: int,
    transparent: int,
) -> bool:
    pixels = image.load()
    left = center_x - width // 2
    right = left + width - 1
    rows = (
        (top, left + 2, right - 2),
        (top + 1, left + 1, right - 1),
        (top + 2, left, right),
        (top + 3, left + 1, right - 1),
    )
    changed = False

    for y, start_x, end_x in rows:
        for x in range(start_x, end_x + 1):
            if 0 <= x < image.width and 0 <= y < image.height and pixels[x, y] != transparent:
                pixels[x, y] = black
                changed = True

    for x in (center_x - 2, center_x + 2):
        y = top + 1
        if 0 <= x < image.width and 0 <= y < image.height and pixels[x, y] != transparent:
            pixels[x, y] = highlight
            changed = True
    return changed


def process_pokemon(path: Path, is_icon: bool = False, is_back: bool = False) -> bool:
    image = Image.open(path).copy()
    black, highlight, transparent = palette_indices(image)
    frame_height = 32 if is_icon else image.height
    changed = False

    for frame_top in range(0, image.height, frame_height):
        frame = image.crop((0, frame_top, image.width, min(frame_top + frame_height, image.height)))
        frame_box = bounds(frame, transparent)
        if frame_box is None:
            continue
        x0, y0, x1, y1 = frame_box

        if is_back:
            row_y = min(y1 - 1, y0 + max(2, int((y1 - y0) * 0.22)))
            occupied_x = [x for x in range(x0, x1) if frame.getpixel((x, row_y)) != transparent]
            center_x = round((min(occupied_x) + max(occupied_x)) / 2) if occupied_x else (x0 + x1) // 2
            visor_width = max(7, min(13, round((x1 - x0) * 0.3)))
            top = row_y - 1
        else:
            center_x, top, visor_width = pokemon_face_anchor(frame, black, frame_box)

        changed |= draw_visor(frame, center_x, top, visor_width, black, highlight, transparent)
        image.paste(frame, (0, frame_top))

    if changed:
        image.save(path)
    return changed


def process_portrait(path: Path, is_back: bool = False) -> bool:
    image = Image.open(path).copy()
    black, highlight, transparent = palette_indices(image)
    frame_height = 64
    changed = False

    for frame_top in range(0, image.height, frame_height):
        frame = image.crop((0, frame_top, image.width, min(frame_top + frame_height, image.height)))
        frame_box = bounds(frame, transparent)
        if frame_box is None:
            continue
        x0, y0, x1, y1 = frame_box
        if is_back:
            row_y = min(y1 - 1, y0 + max(2, int((y1 - y0) * 0.2)))
            occupied_x = [x for x in range(x0, x1) if frame.getpixel((x, row_y)) != transparent]
            center_x = round((min(occupied_x) + max(occupied_x)) / 2) if occupied_x else (x0 + x1) // 2
            top = row_y - 1
            width = max(8, min(15, round((x1 - x0) * 0.3)))
        else:
            center_x = (x0 + x1) // 2
            top = y0 + max(4, min(9, round((y1 - y0) * 0.12)))
            width = max(10, min(16, round((x1 - x0) * 0.34)))
        changed |= draw_visor(frame, center_x, top, width, black, highlight, transparent)
        image.paste(frame, (0, frame_top))

    if changed:
        image.save(path)
    return changed


def process_people_sheet(path: Path) -> bool:
    image = Image.open(path).copy()
    black, highlight, transparent = palette_indices(image)
    frame_height = 32 if image.height >= 32 else 16
    changed = False

    for frame_top in range(0, image.height, frame_height):
        for frame_left in range(0, image.width, 16):
            frame = image.crop((frame_left, frame_top, min(frame_left + 16, image.width), min(frame_top + frame_height, image.height)))
            frame_box = bounds(frame, transparent)
            if frame_box is None:
                continue
            x0, y0, x1, y1 = frame_box
            if x1 - x0 < 5 or y1 - y0 < 7:
                continue
            row_y = min(y1 - 1, y0 + max(2, int((y1 - y0) * 0.28)))
            occupied_x = [x for x in range(x0, x1) if frame.getpixel((x, row_y)) != transparent]
            center_x = round((min(occupied_x) + max(occupied_x)) / 2) if occupied_x else (x0 + x1) // 2
            width = max(6, min(10, round((x1 - x0) * 0.72)))
            changed |= draw_visor(frame, center_x, row_y - 1, width, black, highlight, transparent)
            image.paste(frame, (frame_left, frame_top))

    if changed:
        image.save(path)
    return changed


def main() -> None:
    if not TARGET_ROOT.exists():
        raise FileNotFoundError(f'Missing decomp repo: {TARGET_ROOT}')

    totals = {'pokemon': 0, 'trainers': 0, 'overworld': 0}
    for path in sorted(POKEMON_ROOT.glob('*/front.png')):
        totals['pokemon'] += process_pokemon(path)
    for path in sorted(POKEMON_ROOT.glob('*/back.png')):
        totals['pokemon'] += process_pokemon(path, is_back=True)
    for path in sorted(POKEMON_ROOT.glob('*/icon.png')):
        totals['pokemon'] += process_pokemon(path, is_icon=True)

    for path in sorted((TRAINER_ROOT / 'front_pics').glob('*.png')):
        totals['trainers'] += process_portrait(path)
    for path in sorted((TRAINER_ROOT / 'back_pics').glob('*.png')):
        totals['trainers'] += process_portrait(path, is_back=True)

    for path in sorted(PEOPLE_ROOT.glob('*.png')):
        totals['overworld'] += process_people_sheet(path)

    print(
        'Added black protogen visors to '
        f"{totals['pokemon']} Pokemon sprite sheets, "
        f"{totals['trainers']} trainer portraits, and "
        f"{totals['overworld']} overworld character sheets."
    )


if __name__ == '__main__':
    main()
