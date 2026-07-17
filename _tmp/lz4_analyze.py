"""
FNA LZ4 format: each block has a 4-byte uncompressed size prefix.
The LZ4 tokens are followed by more tokens. No explicit block boundary markers.
Each 64KB of OUTPUT data starts a new conceptual "block".
But the LZ4 stream has NO size prefixes, just continuous tokens.
So the first match at offset 14112 can't reference valid data.

UNLESS: FNA loads the font texture into a pre-allocated buffer 
and the matches reference data from the buffer's prior content.
Or: there's a different header size I'm missing.

Let me try with the RAW data starting at offset 9 (no size field).
"""
import struct

path = 'D:/steam/steamapps/common/Stardew Valley/Content/Fonts/SpriteFont1.zh-CN.xnb'
data = open(path, 'rb').read()

# Try: what if the compressed data starts at offset 13?
# "XNB" (3) + 1 unknown + 1 flags + 4 = 9, then 4 more = 13
# Or: FNA's header includes the decomp_size AFTER the compressed data

for data_start in range(9, 20):
    # Extract potential LZ4 data
    lz4_data = data[data_start:]
    
    # First byte is token or compression type?
    first = lz4_data[0]
    
    if first == 0:
        # Skip compression type byte, read decomp_size (4 bytes)
        ds = struct.unpack('<I', lz4_data[1:5])[0]
        token_start = 5
    else:
        # No compression type - first byte is LZ4 token
        ds = decomp_size  # use known size
        token_start = 0
    
    if 'ds' not in dir():
        continue
    
    # Try with different assumptions
    for extra_skip in [0, 1, 2, 3, 4]:
        actual_start = token_start + extra_skip
        tokens = lz4_data[actual_start:]
        
        # Parse first few tokens and check match offsets
        sp = 0
        ok = True
        dst_len = 0
        
        for i in range(5):
            if sp + 1 >= len(tokens):
                ok = False
                break
            token = tokens[sp]
            sp += 1
            
            lit_len = (token >> 4) & 0x0F
            if lit_len == 15:
                while sp < len(tokens):
                    b = tokens[sp]
                    sp += 1
                    lit_len += b
                    if b < 255:
                        break
            
            dst_len += lit_len
            sp += min(lit_len, max(0, len(tokens) - sp))
            
            if sp + 2 >= len(tokens):
                break
            
            match_offset = struct.unpack('<H', tokens[sp:sp+2])[0]
            sp += 2
            
            if match_offset <= dst_len:
                # Valid! Match references existing data
                pass
            elif match_offset > dst_len and i == 0:
                # First match with offset > dst_len: bad for continuous stream
                pass
            
            match_len = (token & 0x0F) + 4
            if (token & 0x0F) == 15:
                while sp < len(tokens):
                    b = tokens[sp]
                    sp += 1
                    match_len += b
                    if b < 255:
                        break
            
            dst_len += match_len
        
        if ok:
            print(f'data_start={data_start} skip={extra_skip}: first match offset {match_offset} vs dst_len {dst_len} valid={match_offset <= dst_len}')

# Also check: maybe the data uses a fixed-size ring buffer (64KB)
# where each match is within the buffer
print()
print("Try: ring buffer approach (64KB sliding window)")
print("If the decompressor maintains a 64KB window, first match at 14112")
print("would reference the 14112th byte of the initial buffer (zeros)")

# Maybe I need to initialize the output buffer with zeros and then
# fill it with the decompressed data
# This is how LZ4 works with a dictionary or preset
