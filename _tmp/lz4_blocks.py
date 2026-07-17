"""
FNA LZ4 block format:
  Blocks of 64KB. Each block:
    4 bytes: uncompressed_size of this block (LE uint32)
    4 bytes: compressed_size of this block (LE uint32)
    N bytes: LZ4 compressed data (if compressed_size < uncompressed_size)
             or raw data (if compressed_size == uncompressed_size)
  Block with uncompressed_size=0 = end
"""

import struct
import lz4.block

data = open('D:/steam/steamapps/common/Stardew Valley/Content/Fonts/SpriteFont1.zh-CN.xnb', 'rb').read()

# Header: 9 bytes "XNB" + more
# Then: 1 byte compression type + 4 bytes decomp_size
header_size = 9
compressed = data[header_size:]

# Read compression type (offset 0)
comp_type = compressed[0]
decomp_total = struct.unpack('<I', compressed[1:5])[0]

print(f'Compression type: {comp_type} (0=LZ4)')
print(f'Total decompressed size: {decomp_total} bytes ({decomp_total/1024/1024:.1f} MB)')

# Start parsing blocks at offset 5
pos = 5
lz4_data = compressed[pos:]
print(f'LZ4 block data: {len(lz4_data)} bytes')

# Try parsing blocks
blocks = []
bp = 0
result_parts = []

while bp < len(lz4_data):
    if bp + 8 > len(lz4_data):
        break
    
    block_uncomp = struct.unpack('<I', lz4_data[bp:bp+4])[0]
    block_comp = struct.unpack('<I', lz4_data[bp+4:bp+8])[0]
    
    if block_uncomp == 0 or block_uncomp > 100000:
        # Maybe not block format - try treating as raw LZ4 stream
        break
    
    blocks.append((block_uncomp, block_comp))
    
    if bp + 8 + block_comp > len(lz4_data):
        break
    
    block_data = lz4_data[bp+8:bp+8+block_comp]
    
    try:
        if block_comp < block_uncomp:
            decomp = lz4.block.decompress(block_data, uncompressed_size=block_uncomp)
        else:
            decomp = block_data  # uncompressed block
        result_parts.append(decomp)
    except Exception as e:
        print(f'  Block {len(blocks)}: LZ4 decompress fail: {e}')
        result_parts.append(block_data)  # Use raw as fallback
    
    bp += 8 + block_comp

if blocks:
    print(f'Found {len(blocks)} blocks')
    total = sum(len(p) for p in result_parts)
    print(f'Total decompressed: {total} bytes')
    
    if result_parts:
        combined = b''.join(result_parts)
        print(f'First 30 bytes: {combined[:30].hex()}')
        
        # Check if this is valid XNB
        if combined[:3] == b'XNB':
            print('Has XNB magic! Double-wrapped!')
        else:
            print('Raw data - no XNB magic')
        
        # Check for Texture2D-like structure
        if len(combined) > 20:
            tex_fmt = struct.unpack('<i', combined[0:4])[0]
            tex_w = struct.unpack('<i', combined[4:8])[0]
            tex_h = struct.unpack('<i', combined[8:12])[0]
            print(f'Tex candidate: fmt={tex_fmt} w={tex_w} h={tex_h}')
        
        # Save
        with open('C:\\Users\\minam\\code\\stardew-bilin\\_tmp\\font_out.bin', 'wb') as f:
            f.write(combined)
else:
    print('No valid blocks found. Trying different format...')
    
    # Try: maybe no block headers, just raw LZ4 stream
    # FNA might use LZ4 streaming format:
    # 4 bytes: uncompressed_size of next block
    # Then LZ4 compressed data of that size (implicit)
    # 0 = end
    
    bp = 0
    result_parts2 = []
    while bp < len(lz4_data):
        if bp + 4 > len(lz4_data):
            break
        block_uncomp = struct.unpack('<I', lz4_data[bp:bp+4])[0]
        if block_uncomp == 0 or block_uncomp > decomp_total:
            break
        bp += 4
        # The rest of the data is the LZ4 compressed stream
        # LZ4 stream format: (token, literal_length, match_offset, match_length)*
        # No explicit block boundaries - lz4.block.decompress handles this
        try:
            decomp = lz4.block.decompress(lz4_data[bp:], uncompressed_size=block_uncomp)
            result_parts2.append(decomp)
            bp += len(lz4_data) - (len(lz4_data) - bp)  # advance past consumed data
            print(f'Stream block decompressed: {len(decomp)} bytes')
        except:
            # Single-stream decompression
            try:
                result = lz4.block.decompress(lz4_data[bp:], uncompressed_size=decomp_total)
                print(f'Single stream decompressed: {len(result)} bytes')
                with open('C:\\Users\\minam\\code\\stardew-bilin\\_tmp\\font_out.bin', 'wb') as f:
                    f.write(result)
                break
            except Exception as e:
                print(f'Single stream failed: {e}')
            break
    
    # Try: use python-lz4's streaming decompressor
    try:
        from lz4 import stream
        # Try LZ4 frame decompression with custom parameters
        pass
    except ImportError:
        pass
    
    # Try: LZ4 frame
    import lz4.frame
    for skip in [0, 1, 5, 9]:
        try:
            result = lz4.frame.decompress(compressed[skip:])
            print(f'LZ4 frame at skip={skip}: {len(result)} bytes')
            with open('C:\\Users\\minam\\code\\stardew-bilin\\_tmp\\font_out.bin', 'wb') as f:
                f.write(result)
            break
        except:
            pass
