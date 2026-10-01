#!/usr/bin/env python3
from pathlib import Path

src = Path('/workspaces/Pokemon-Protogen-Rom-Hack/Pokemon - FireRed Version (USA).gba')
out = Path('/workspaces/Pokemon-Protogen-Rom-Hack/Pokemon - FireRed Version (USA) - Protogen Furry.gba')

def main():
    if not src.exists():
        raise FileNotFoundError(f'Missing source ROM: {src}')
    data = bytearray(src.read_bytes())
    # FireRed USA Rev 0 title/header area is at 0xA0.
    title_offset = 0xA0
    # Patch the banner/title bytes to reflect the protogen/furry theme while keeping a valid GBA ROM structure.
    # 12 bytes total: "PROT0GEN FUR" = 12 ASCII chars.
    new_title = b'PROT0GEN FUR'
    if len(new_title) != 12:
        raise ValueError(f'Title patch length mismatch: {len(new_title)}')
    data[title_offset:title_offset + 12] = new_title
    # Also patch the visible title string the ROM contains elsewhere to keep the theme consistent.
    for target in (b'POKEMON FIRE', b'POKEMON\x00FIRE'):
        idx = data.find(target)
        if idx != -1:
            data[idx:idx + len(target)] = b'PROT0GEN FUR'
    out.write_bytes(data)
    print(f'Wrote hacked ROM: {out}')
    print(f'Size: {out.stat().st_size} bytes')

if __name__ == '__main__':
    main()
