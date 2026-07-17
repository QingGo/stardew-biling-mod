"""
Raw LZ4 block stream decompressor.
FNA dumps raw LZ4 tokens without standard framing.
"""
import struct

def lz4_decompress(src, dst_size, block_size=65536):
    """Decompress raw LZ4 block stream (FNA format).
    
    FNA splits the data into blocks of `block_size` (default 64KB).
    Each block is independently LZ4 compressed.
    """
    dst = bytearray()
    src_pos = 0
    
    while src_pos < len(src) and len(dst) < dst_size:
        remaining = dst_size - len(dst)
        target = min(block_size, remaining)
        
        # Parse LZ4 tokens until we've output `target` bytes for this block
        block_start_len = len(dst)
        
        while len(dst) - block_start_len < target and src_pos < len(src):
            token = src[src_pos]
            src_pos += 1
            
            # Literal length
            lit_len = (token >> 4) & 0x0F
            if lit_len == 15:
                while True:
                    extra = src[src_pos]
                    src_pos += 1
                    lit_len += extra
                    if extra < 255:
                        break
            
            # Copy literals
            if lit_len > 0:
                copy_len = min(lit_len, len(src) - src_pos)
                dst.extend(src[src_pos:src_pos + copy_len])
                src_pos += copy_len
            
            if src_pos >= len(src):
                break
            
            # Match offset
            match_offset = struct.unpack('<H', src[src_pos:src_pos + 2])[0]
            src_pos += 2
            
            if match_offset == 0 or match_offset > len(dst):
                continue  # skip invalid matches (shouldn't happen in valid data)
            
            # Match length
            match_len = (token & 0x0F) + 4
            if (token & 0x0F) == 15:
                while True:
                    extra = src[src_pos]
                    src_pos += 1
                    match_len += extra
                    if extra < 255:
                        break
            
            # Copy match
            for i in range(match_len):
                dst.append(dst[len(dst) - match_offset])
        
        # If we didn't make progress, stop
        if len(dst) == block_start_len:
            break
    
    return bytes(dst)

# Read the file
data = open('D:/steam/steamapps/common/Stardew Valley/Content/Fonts/SpriteFont1.zh-CN.xnb', 'rb').read()

# Try different header sizes
for header in [9, 10, 13, 14]:
    lz4_data = data[header:]
    
    # Try reading decompress size from different offsets
    for size_offset in [0, 1, 5]:
        if size_offset + 4 >= len(lz4_data):
            continue
        decomp_size = struct.unpack('<I', lz4_data[size_offset:size_offset+4])[0]
        
        if decomp_size < 100000 or decomp_size > 50000000:
            continue
        
        # LZ4 data starts after size_offset + 4
        start = size_offset + 4
        if lz4_data[0] == 0:
            start = size_offset + 5  # skip comp type byte
        
        for skip in range(0, 5):
            actual_start = start + skip
            if actual_start >= len(lz4_data):
                continue
            
            try:
                result = lz4_decompress(lz4_data[actual_start:], decomp_size)
                if len(result) == decomp_size or (len(result) > 100000 and len(result) < decomp_size * 1.1):
                    print(f'HEADER={header} size_off={size_offset} skip={skip}: decompressed {len(result)} bytes!')
                    print(f'  Expected: {decomp_size}')
                    
                    # Check if result looks valid
                    print(f'  First 40 bytes hex: {result[:40].hex()}')
                    
                    # Try to parse as XNB object
                    if result[:3] == b'XNB':
                        print('  Contains XNB magic (double-wrapped!)')
                    elif len(result) > 20:
                        # Check for texture data
                        tex_fmt = struct.unpack('<i', result[0:4])[0]
                        tex_w = struct.unpack('<i', result[4:8])[0]
                        tex_h = struct.unpack('<i', result[8:12])[0]
                        print(f'  Texture format={tex_fmt} w={tex_w} h={tex_h}')
                    
                    # Save
                    out_path = f'C:\\Users\\minam\\code\\stardew-bilin\\_tmp\\font_{header}_{size_offset}.bin'
                    open(out_path, 'wb').write(result)
                    print(f'  Saved to {out_path}')
                    
                    # If valid, also try parsing the Japanese font
                    if len(result) > 10000:
                        print('  SUCCESS!')
            except Exception as e:
                pass

print('\nDone')
