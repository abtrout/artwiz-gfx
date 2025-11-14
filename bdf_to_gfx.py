#!/usr/bin/env python3

import sys

from dataclasses import dataclass, field
from pathlib import Path


HEADER_TEMPLATE = """// Font: {font_name}
// Converted from BDF to Adafruit GFX format

#pragma once

#include <Adafruit_GFX.h>

const uint8_t {var_name}Bitmaps[] PROGMEM = {{
{bitmap_data}}};

const GFXglyph {var_name}Glyphs[] PROGMEM = {{
{glyph_data}
}};

const GFXfont {var_name} PROGMEM = {{
    (uint8_t*){var_name}Bitmaps,
    (GFXglyph*){var_name}Glyphs,
    {first_char}, {last_char}, {total_height}}};

// Approx. {total_bytes} bytes
"""


@dataclass
class BDFFont:
    """A BDF font."""
    name: str = ""
    font_ascent: int = 0
    font_descent: int = 0
    glyphs: dict = field(default_factory=dict)


@dataclass
class Glyph:
    """A single character."""
    encoding: int
    dwidth: int = 0
    bbx_width: int = 0
    bbx_height: int = 0
    bbx_xoff: int = 0
    bbx_yoff: int = 0
    bitmap: list[int] = field(default_factory=list)


def parse_bdf(path: Path) -> BDFFont:
    """Parse a BDF font file."""
    font = BDFFont()
    current_glyph = None
    in_bitmap = False

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith('FONT '):
                font.name = line.split(' ', 1)[1]
            elif line.startswith('FONT_ASCENT '):
                font.font_ascent = int(line.split()[1])
            elif line.startswith('FONT_DESCENT '):
                font.font_descent = int(line.split()[1])
            elif line.startswith('STARTCHAR '):
                current_glyph = None
                in_bitmap = False
            elif line.startswith('ENCODING '):
                encoding = int(line.split()[1])
                current_glyph = Glyph(encoding)
                font.glyphs[encoding] = current_glyph
            elif current_glyph and line.startswith('DWIDTH '):
                parts = line.split()
                current_glyph.dwidth = int(parts[1])
            elif current_glyph and line.startswith('BBX '):
                parts = line.split()
                current_glyph.bbx_width = int(parts[1])
                current_glyph.bbx_height = int(parts[2])
                current_glyph.bbx_xoff = int(parts[3])
                current_glyph.bbx_yoff = int(parts[4])
            elif line == 'BITMAP':
                in_bitmap = True
            elif in_bitmap and line == 'ENDCHAR':
                in_bitmap = False
                current_glyph = None
            elif in_bitmap and current_glyph and line:
                current_glyph.bitmap.append(int(line, 16))

    return font


def pack_glyph_bitmap(glyph: Glyph) -> list[int]:
    """Pack a glyph's bitmap into bytes."""
    if glyph.bbx_width == 0 or glyph.bbx_height == 0:
        return []

    all_bits = []
    for row_data in glyph.bitmap:
        # BDF pads to byte boundaries, so determine the total bit width
        byte_width = ((glyph.bbx_width + 7) // 8) * 8

        for bit_idx in range(glyph.bbx_width):
            # Extract bit from MSB side, accounting for multi-byte rows
            bit_position = byte_width - 1 - bit_idx
            bit_val = (row_data >> bit_position) & 1
            all_bits.append(bit_val)

    # Pack bits into bytes (8 bits per byte, MSB first)
    packed = []
    for byte_idx in range((len(all_bits) + 7) // 8):
        byte_val = 0
        for bit_idx in range(8):
            global_bit_idx = byte_idx * 8 + bit_idx
            if global_bit_idx < len(all_bits):
                byte_val |= (all_bits[global_bit_idx] << (7 - bit_idx))
        packed.append(byte_val)

    return packed


def generate_gfx_header(font: BDFFont, font_name: str) -> str:
    """Generate a complete Adafruit GFX font header file."""
    font_name = font_name.replace('-', '_').replace('.', '_')
    available_encodings = [e for e in font.glyphs.keys() if 32 <= e <= 126]
    if not available_encodings:
        raise ValueError("No printable ASCII glyphs found in font")

    sorted_encodings = sorted(available_encodings)
    first_char = sorted_encodings[0]
    last_char = sorted_encodings[-1]

    concatenated_bitmap = []
    glyph_descriptors = []

    for encoding in sorted_encodings:
        glyph = font.glyphs[encoding]
        bitmap_offset = len(concatenated_bitmap)
        packed = pack_glyph_bitmap(glyph)
        concatenated_bitmap.extend(packed)
        gfx_yoffset = -(glyph.bbx_yoff + glyph.bbx_height)

        glyph_descriptors.append({
            'encoding': encoding,
            'bitmap_offset': bitmap_offset,
            'width': glyph.bbx_width,
            'height': glyph.bbx_height,
            'xAdvance': glyph.dwidth,
            'xOffset': glyph.bbx_xoff,
            'yOffset': gfx_yoffset
        })

    bitmap_lines = []
    for i in range(0, len(concatenated_bitmap), 16):
        chunk = concatenated_bitmap[i:i+16]
        hex_values = ', '.join(f'0x{b:02X}' for b in chunk)
        comma = ',' if i + 16 < len(concatenated_bitmap) else ''
        bitmap_lines.append(f"    {hex_values}{comma}")
    bitmap_data = '\n'.join(bitmap_lines)

    glyph_parts = []
    for i, desc in enumerate(glyph_descriptors):
        char = chr(desc['encoding']) if 32 <= desc['encoding'] < 127 else '?'
        comma = ',' if i < len(glyph_descriptors) - 1 else ''
        data = (f"    {{{desc['bitmap_offset']}, {desc['width']}, {desc['height']}, "
                f"{desc['xAdvance']}, {desc['xOffset']}, {desc['yOffset']}}}{comma}")
        comment = f"// 0x{desc['encoding']:02X} '{char}'"
        glyph_parts.append((data, comment))

    max_width = max(len(data) for data, _ in glyph_parts)
    glyph_lines = [f"{data:<{max_width}} {comment}" for data,
                   comment in glyph_parts]
    glyph_data = '\n'.join(glyph_lines)
    total_bytes = len(concatenated_bitmap) + len(glyph_descriptors) * 7 + 7

    return HEADER_TEMPLATE.format(
        font_name=font.name,
        var_name=font_name,
        bitmap_data=bitmap_data,
        glyph_data=glyph_data,
        first_char=f"0x{first_char:02X}",
        last_char=f"0x{last_char:02X}",
        total_height=font.font_ascent + font.font_descent,
        total_bytes=total_bytes
    )


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(
            f"Usage: {sys.argv[0]} /path/to/font.bdf > /path/to/font.h", file=sys.stderr)
        sys.exit(1)

    bdf_path = Path(sys.argv[1])
    if not bdf_path.exists():
        print(f"Error: {bdf_path} not found", file=sys.stderr)
        sys.exit(1)

    font = parse_bdf(bdf_path)
    header = generate_gfx_header(font, bdf_path.stem)
    print(header, end='')
