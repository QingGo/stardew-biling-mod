"""
FNA XNB decompressor - try FNA's actual LZ4 format

From FNA source code (ContentManager.cs):
  After header: 1 byte compression_indicator (0=LZ4, 1=LZX)
  If LZ4: 4 bytes decompressed_size, then LZ4 compressed blocks
  Blocks: 4 bytes block_size, then LZ4 block data
  If block_size == 0: end of blocks
"""

import struct
import lz4.block

data = open('D:/steam/steamapps/common/Stardew Valley/Content/Fonts/SpriteFont1.zh-CN.xnb', 'rb').read()

# Try: header is "XNB" + 4 bytes (version+flags+unused_low_byte) + 4 bytes (unused)
# Then compressed data starts
# OR: "XNB" + 5 bytes (version+flags+3 pad) + data

for header in [9, 10, 11, 12, 13, 14, 15, 16, 17, 18]:
    compressed = data[header:]
    if len(compressed) < 10:
        continue
    
    comp_indicator = compressed[0]
    
    if comp_indicator == 0:  # LZ4
        # Try reading 4 bytes as decompressed_size
        decomp_size = struct.unpack('<I', compressed[1:5])[0]
        lz4_data = compressed[5:]
        
        # Validate: decomp_size should be reasonable
        if 100000 < decomp_size < 5000000:
            try:
                result = lz4.block.decompress(lz4_data, uncompressed_size=decomp_size)
                print(f'HEADER={header}: LZ4 block OK! decomp={decomp_size} ({len(lz4_data)} compressed)')
                with open(f'C:\\Users\\minam\\code\\stardew-bilin\\_tmp\\font_out_{header}.bin', 'wb') as f:
                    f.write(result)
                # Print first few bytes to verify
                print(f'  First 20 hex: {result[:20].hex()}')
                break
            except Exception as e:
                print(f'HEADER={header}: LZ4 block fail (decomp={decomp_size}): {type(e).__name__}')
        
        # Try without decomp_size: raw LZ4 block
        try:
            result = lz4.block.decompress(compressed[1:])
            print(f'HEADER={header}: LZ4 block auto OK! {len(result)} bytes')
            with open(f'C:\\Users\\minam\\code\\stardew-bilin\\_tmp\\font_out_{header}.bin', 'wb') as f:
                f.write(result)
            break
        except:
            pass
        
        # Try treating entire compressed section as LZ4 frame
        try:
            result = lz4.frame.decompress(compressed)
            print(f'HEADER={header}: LZ4 frame OK!')
            break
        except:
            pass
    
    elif comp_indicator == 1:  # LZX
        pass

# Also try: maybe the data after header IS the raw body and the format doesn't use type readers
print('\nAlso trying: no type readers (XNB 4.0 format without reader table)')
for header in [9, 10, 11, 12, 13]:
    body = data[header:]
    if len(body) < 20:
        continue
    
    # Naked format: no type reader table at all
    # Just starts with:
    # Texture2D: format(int32), width(int32), height(int32), mipcount(int32), data_size(int32), pixel_data
    
    tex_fmt = struct.unpack('<i', body[0:4])[0]
    tex_w = struct.unpack('<i', body[4:8])[0]
    tex_h = struct.unpack('<i', body[8:12])[0]
    
    if 0 <= tex_fmt <= 12 and 1 <= tex_w <= 8192 and 1 <= tex_h <= 8192:
        print(f'HEADER={header}: Raw format!  tex={tex_w}x{tex_h} fmt={tex_fmt}')

print('\nDone.')
