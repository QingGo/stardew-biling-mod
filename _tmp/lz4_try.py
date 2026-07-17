"""
Try multiple XNB parsing strategies.
The files are confirmed not standard XNB format.
Let me try FNA-specific approach.
"""

import struct
import lz4.block

def try_decompress(data_path):
    raw = open(data_path, 'rb').read()
    
    # Strategy 1: FNA header (10 bytes? 13 bytes?)
    # FNA uses "XNB" + target_byte + flags_byte
    # If HiDef: data starts with 1-byte compression type (0=LZ4, 1=LZX)
    # Then LZ4 or LZX compressed data
    # decompressed_size is embedded in the compression header
    
    for header_size in range(9, 30):
        compressed = raw[header_size:]
        if len(compressed) < 10:
            continue
        
        comp_type = compressed[0]
        lz4_data = compressed[1:]
        
        # Try various uncompressed sizes
        for target_size in [500000, 1000000, 1500000, 2000000, 306379393]:
            try:
                result = lz4.block.decompress(lz4_data, uncompressed_size=target_size)
                print(f'  LZ4 block OK (header={header_size}, target={target_size}): {len(result)} bytes')
                
                # Check if result has valid XNB-like structure
                if result[:3] == b'XNB':
                    print(f'    Result starts with XNB! Double-wrapped!')
                else:
                    print(f'    First bytes: {result[:20].hex()}')
                return result
            except:
                pass
        
        # Try LZ4 frame
        try:
            result = lz4.frame.decompress(compressed)
            print(f'  LZ4 frame OK (header={header_size}): {len(result)} bytes')
            return result
        except:
            pass
        
        # Try without compression type byte
        try:
            result = lz4.block.decompress(compressed, uncompressed_size=306379393)
            print(f'  LZ4 block raw (header={header_size}): {len(result)} bytes')
            return result
        except:
            pass

    return None

print("=== Chinese Font ===")
result = try_decompress(
    'D:/steam/steamapps/common/Stardew Valley/Content/Fonts/SpriteFont1.zh-CN.xnb'
)

if result:
    print(f'\nDecompressed: {len(result)} bytes')
    # Save for analysis
    with open('C:\\Users\\minam\\code\\stardew-bilin\\_tmp\\decompressed.bin', 'wb') as f:
        f.write(result)

print("\n=== English Font ===")
try_decompress(
    'D:/steam/steamapps/common/Stardew Valley/Content/Fonts/SpriteFont1.xnb'
)
