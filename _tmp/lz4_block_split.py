"""
Try another approach: split the LZ4 data into 64KB blocks and
decompress each separately.
FNA likely uses 64KB (65536) block size.
"""
import struct
from lz4 import block as lz4block

data = open('D:/steam/steamapps/common/Stardew Valley/Content/Fonts/SpriteFont1.zh-CN.xnb', 'rb').read()

# Header: 9 bytes
lz4_data = data[14:]  # skip "XNB" + target + flags(3) + comp_type(1) + decomp_size(4)

comp_type = data[9]
decomp_size = struct.unpack('<I', data[10:14])[0]
print(f'Compression type: {comp_type}')
print(f'Decompressed size: {decomp_size}')
print(f'LZ4 data: {len(lz4_data)} bytes')

# Strategy: try to decompress as raw LZ4 stream with block size awareness
# lz4.block.decompress expects ONE complete block.
# We need to feed it one block at a time.

# FNA approach: read 4 bytes uncompressed_block_size, then feed to LZ4
# OR: just iterate and decompress block by block using lz4.block.decompress

result = bytearray()
pos = 0
block_size = 65536
block_num = 0

while pos < len(lz4_data):
    # Each block: decompress until we have `block_size` output bytes
    # Using lz4.block.decompress to handle one block
    # But we don't know the compressed size of each block
    
    # Alternative: try decompressing with different uncompressed sizes
    # Start from end and work backwards
    for try_size in [block_size, 131072, 262144, 524288, 1048576]:
        remaining = decomp_size - len(result)
        if remaining <= 0:
            break
        test_size = min(try_size, remaining)
        
        try:
            block_out = lz4block.decompress(lz4data, uncompressed_size=test_size)
            # This worked! But it consumed all data...
            result.extend(block_out)
            print(f'Block {block_num}: {len(block_out)} bytes (consumed all remaining data)')
            pos = len(lz4_data)
            break
        except:
            pass
    
    if len(result) >= decomp_size or pos >= len(lz4_data):
        break
    block_num += 1
    
    if block_num > 100:  # safety
        break

# Try: use the lz4framing approach
if len(result) < decomp_size:
    print(f'\nBlock approach gave {len(result)} bytes. Trying frame approach...')
    from lz4 import frame
    try:
        result2 = frame.decompress(data[14:])  # Skip entire header
        print(f'Frame decompress at offset 14: {len(result2)} bytes')
        result = bytearray(result2)
    except:
        try:
            result2 = frame.decompress(data[9:])  # Skip just XNB header
            print(f'Frame decompress at offset 9: {len(result2)} bytes')
            result = bytearray(result2)
        except:
            pass

if len(result) > 1000:
    print(f'\nFinal result: {len(result)} bytes')
    with open('C:\\Users\\minam\\code\\stardew-bilin\\_tmp\\font_decompressed.bin', 'wb') as f:
        f.write(result)
    
    # Try parsing
    body = bytes(result)
    print(f'First 16 hex: {body[:16].hex()}')
    
    # Check for type reader count at various offsets
    def read_7bit(d, p):
        v, s = 0, 0
        while True:
            b = d[p]
            v |= (b & 0x7F) << s
            s += 7
            p += 1
            if (b & 0x80) == 0:
                break
        return v, p
    
    for offset in range(0, 50):
        try:
            rc, _ = read_7bit(body, offset)
            if 0 <= rc <= 20:
                # Check if texture format follows
                tex_candidate = struct.unpack('<i', body[offset+1:offset+5])[0]
                if 0 <= tex_candidate <= 12:
                    print(f'  Valid reader_count={rc} at offset {offset}')
                    break
        except:
            pass
