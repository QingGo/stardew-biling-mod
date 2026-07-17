"""
Merge Chinese and Japanese SpriteFont XNBs into one combined CJK font.

The game's Chinese font (SpriteFont1.zh-CN.xnb) has Latin + CJK + some kana.
The Japanese font (SpriteFont1.ja-JP.xnb) has Latin + Japanese kanji + kana.

We merge the Japanese kana glyphs into the Chinese font so that
ja-zh bilingual mode renders both languages correctly.

XNB Format (MonoGame):
  Header: "XNB" + version(byte) + flags(byte) + file_size(uint32 LE)
  If compressed: data is LZ4/LZX compressed (not implemented here - we use uncompressed)
  Object data: type_readers(int32) + type_names + actual_data

  SpriteFontReader reads:
    - Texture2D (embedded: format+width+height+mipcount+data)
    - GlyphBounds: List<Rectangle> (int32 count + 4*int32 each)
    - Characters: List<char> (int32 count + char each)
    - LineSpacing: int32
    - Spacing: float
    - DefaultCharacter: char? (optional, not present in zh-CN)
"""

import struct
import sys
from pathlib import Path

GAME_DIR = Path("D:/steam/steamapps/common/Stardew Valley")
CONTENT_DIR = GAME_DIR / "Content"
OUTPUT_DIR = Path(__file__).parent.parent / "BilingualMod" / "assets"

def read_7bit_int(data, offset):
    """Read a 7-bit encoded integer from MonoGame format."""
    result = 0
    shift = 0
    while True:
        byte = data[offset]
        result |= (byte & 0x7F) << shift
        shift += 7
        offset += 1
        if (byte & 0x80) == 0:
            break
    return result, offset

def write_7bit_int(value):
    """Write a 7-bit encoded integer in MonoGame format."""
    result = []
    while value >= 0x80:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)

def parse_xnb_header(data):
    """Parse XNB file header."""
    magic = data[0:3]
    if magic != b'XNB':
        raise ValueError(f"Not an XNB file: {magic}")
    version = data[3]
    flags = data[4]
    file_size = struct.unpack_from('<I', data, 5)[0]
    return {
        'version': version,
        'flags': flags,
        'file_size': file_size,
        'compressed': bool(flags & 0x01) or bool(flags & 0x02),
        'hdef': bool(flags & 0x04),
    }

def parse_spritefont(data):
    """Parse SpriteFont XNB data - extract texture info and character lists."""
    header = parse_xnb_header(data)
    
    offset = 9  # header size
    
    if header['compressed']:
        print("  XNB is compressed. Attempting decompression...")
        # The compressed data starts at offset 9
        # For LZ4 (flags & 0x02), decompress
        # For now, skip - we'll use the raw decompressed data if available
        try:
            import lz4.block
            decompressed = lz4.block.decompress(data[9:])
            print(f"  Decompressed: {len(data[9:])} -> {len(decompressed)} bytes")
            data = data[:9] + decompressed
            offset = 9
        except ImportError:
            print("  No lz4 module available, trying to proceed...")
            return None
    
    # Read type reader count (7-bit encoded int in MonoGame)
    reader_count, offset = read_7bit_int(data, offset)
    # print(f"  Reader count: {reader_count}")
    
    # Skip type reader names
    for i in range(reader_count):
        # Reader name length (7-bit encoded) + name string
        name_len, offset = read_7bit_int(data, offset)
        offset += name_len
        # Version number - int32
        reader_version = struct.unpack_from('<i', data, offset)[0]
        offset += 4
    
    # Read shared resource count (7-bit encoded, always 0 for embedded fonts)
    shared_count, offset = read_7bit_int(data, offset)
    
    # Read type reader ID for the object (7-bit encoded)
    type_id, offset = read_7bit_int(data, offset)
    
    # Now we're at the SpriteFont data
    # The data is read by SpriteFontReader.Read()
    
    # 1. Texture2D
    # First: surface format (int32)
    surface_format = struct.unpack_from('<i', data, offset)[0]
    offset += 4
    
    # Texture width, height (int32)
    width = struct.unpack_from('<i', data, offset)[0]
    offset += 4
    height = struct.unpack_from('<i', data, offset)[0]
    offset += 4
    
    # Mip count (int32)
    mip_count = struct.unpack_from('<i', data, offset)[0]
    offset += 4
    
    # Texture data size (int32 for each mip)
    tex_data_size = struct.unpack_from('<i', data, offset)[0]
    offset += 4
    
    # Texture pixel data
    tex_data = data[offset:offset + tex_data_size]
    offset += tex_data_size
    
    # 2. Glyph bounds: List<Rectangle>
    rect_count, offset = read_7bit_int(data, offset)
    glyph_bounds = []
    for _ in range(rect_count):
        x = struct.unpack_from('<i', data, offset)[0]
        offset += 4
        y = struct.unpack_from('<i', data, offset)[0]
        offset += 4
        w = struct.unpack_from('<i', data, offset)[0]
        offset += 4
        h = struct.unpack_from('<i', data, offset)[0]
        offset += 4
        glyph_bounds.append((x, y, w, h))
    
    # 3. Characters: List<char>
    char_count, offset = read_7bit_int(data, offset)
    characters = []
    for _ in range(char_count):
        ch = struct.unpack_from('<H', data, offset)[0]
        offset += 2
        characters.append(chr(ch))
    
    # 4. Line spacing: int32
    line_spacing = struct.unpack_from('<i', data, offset)[0]
    offset += 4
    
    # 5. Spacing: float
    spacing = struct.unpack_from('<f', data, offset)[0]
    offset += 4
    
    # 6. Default character: char? (optional)
    default_char = None
    if offset < len(data):
        has_default = data[offset]
        offset += 1
        if has_default:
            default_char = chr(struct.unpack_from('<H', data, offset)[0])
            offset += 2
    
    print(f"  Texture: {width}x{height}, format={surface_format}")
    print(f"  Glyphs: {len(glyph_bounds)}, Chars: {len(characters)}")
    print(f"  Line spacing: {line_spacing}, Spacing: {spacing}")
    if default_char:
        print(f"  Default char: U+{ord(default_char):04X}")
    
    return {
        'header': header,
        'surface_format': surface_format,
        'width': width,
        'height': height,
        'mip_count': mip_count,
        'tex_data': tex_data,
        'glyph_bounds': glyph_bounds,
        'characters': characters,
        'line_spacing': line_spacing,
        'spacing': spacing,
        'default_char': default_char,
        'reader_count': reader_count,
        'shared_count': shared_count,
        'type_id': type_id,
        # Full raw data after header for reconstruction
        'body_start': 9,
        'raw_body': data[9:offset],
        'total_body_size': offset - 9,
    }


def find_missing_kana(chinese_data, japanese_data):
    """Find Japanese kana characters not present in Chinese font."""
    zh_chars = set(c for c in chinese_data['characters'])
    ja_chars = set(c for c in japanese_data['characters'])
    
    # Kana ranges in Unicode
    hiragana = set(chr(cp) for cp in range(0x3040, 0x309F + 1))  # Hiragana
    katakana = set(chr(cp) for cp in range(0x30A0, 0x30FF + 1))  # Katakana
    kana_ext = set(chr(cp) for cp in range(0x31F0, 0x31FF + 1))  # Katakana Phonetic Ext
    
    all_kana = hiragana | katakana | kana_ext
    
    kana_in_zh = all_kana & zh_chars
    kana_in_ja = all_kana & ja_chars
    missing = kana_in_ja - kana_in_zh
    
    # Also find characters that exist in both but might have different glyphs
    # For now, just find the kana
    return sorted(missing, key=ord)


def main():
    print("=" * 60)
    print("SpriteFont CJK Merger")
    print("=" * 60)
    
    # Load font XNB files  
    print("\nLoading Chinese font...")
    ch_path = CONTENT_DIR / "Fonts" / "SpriteFont1.zh-CN.xnb"
    zh_data = ch_path.read_bytes()
    zh_font = parse_spritefont(zh_data)
    
    print("\nLoading Japanese font...")
    ja_path = CONTENT_DIR / "Fonts" / "SpriteFont1.ja-JP.xnb"
    ja_data = ja_path.read_bytes()
    ja_font = parse_spritefont(ja_data)
    
    if not zh_font or not ja_font:
        print("Failed to parse font files")
        return
    
    # Find missing characters
    missing = find_missing_kana(zh_font, ja_font)
    print(f"\nMissing characters: {len(missing)}")
    if missing:
        print("Sample missing:")
        for ch in missing[:10]:
            print(f"  U+{ord(ch):04X} {ch}")
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more")
    
    # Print character range info
    print(f"\nChinese font char count: {len(zh_font['characters'])}")
    print(f"Japanese font char count: {len(ja_font['characters'])}")
    
    # Get kana stats
    all_kana = set(chr(cp) for cp in range(0x3040, 0x309F + 1)) | \
               set(chr(cp) for cp in range(0x30A0, 0x30FF + 1)) | \
               set(chr(cp) for cp in range(0x31F0, 0x31FF + 1))
    zh_kana = all_kana & set(zh_font['characters'])
    ja_kana = all_kana & set(ja_font['characters'])
    print(f"Kana in Chinese font: {len(zh_kana)} / {len(all_kana)}")
    print(f"Kana in Japanese font: {len(ja_kana)} / {len(all_kana)}")


if __name__ == "__main__":
    main()
