"""
Manual LZ4 token parsing to check if the data is valid LZ4.
"""
import struct

data = open('D:/steam/steamapps/common/Stardew Valley/Content/Fonts/SpriteFont1.zh-CN.xnb', 'rb').read()

# Header: 9 bytes, then 1 byte comp_type, then 4 bytes decomp_size
lz4_data = data[14:]  # 9 header + 1 comp_type + 4 decomp_size

print(f"LZ4 data: {len(lz4_data)} bytes")
print(f"First 64 bytes: {lz4_data[:64].hex()}")

def parse_lz4_block(d, pos, max_size):
    """Parse first few LZ4 tokens to check validity."""
    tokens = []
    while pos < len(d) and pos < max_size:
        token = d[pos]
        pos += 1
        
        lit_len = (token >> 4) & 0x0F
        match_len = (token & 0x0F) + 4  # minimum match is 4
        
        # Extended literal length
        if lit_len == 15:
            while True:
                extra = d[pos]
                pos += 1
                lit_len += extra
                if extra < 255:
                    break
        
        # Literals
        literals = d[pos:pos+lit_len]
        pos += lit_len
        
        if pos >= len(d):
            tokens.append({'type': 'last_literals', 'lit_len': lit_len, 'lits': literals[:8].hex()})
            break
        
        # Match offset (2 bytes LE)
        if pos + 2 > len(d):
            break
        match_offset = struct.unpack('<H', d[pos:pos+2])[0]
        pos += 2
        
        # Extended match length  
        if (token & 0x0F) == 15:
            while True:
                extra = d[pos]
                pos += 1
                match_len += extra
                if extra < 255:
                    break
        
        tokens.append({
            'type': 'match',
            'lit_len': lit_len,
            'match_offset': match_offset,
            'match_len': match_len,
            'lits': literals[:8].hex() if literals else ''
        })
        
        # Don't parse too many
        if len(tokens) >= 10:
            break
    
    return tokens

tokens = parse_lz4_block(lz4_data, 0, 2000)
print(f"\nFirst {len(tokens)} LZ4 tokens:")
for i, t in enumerate(tokens):
    if t['type'] == 'last_literals':
        print(f"  [{i}] LAST_LITERALS: len={t['lit_len']}, data={t['lits']}")
    else:
        print(f"  [{i}] MATCH: lit={t['lit_len']} off={t['match_offset']} ml={t['match_len']} lits={t['lits']}")
    
    if t.get('match_offset', 0) == 0:
        print(f"      ^ WARNING: zero match offset (invalid)")
    if t.get('match_offset', 0) > 0xFFFF:
        print(f"      ^ WARNING: match offset > 65535 (invalid)")

# Also check if this is using a different LZ4 variant
# LZ4 HC uses the same format but with different compression
# Maybe the data uses LZ4 with a dict preset?

# Check for LZ4 frame magic at any offset
LZ4_MAGIC = b'\x04\x22\x4D\x18'
for i in range(50):
    if lz4_data[i:i+4] == LZ4_MAGIC:
        print(f"\nLZ4 frame magic at offset {i}!")
        break
else:
    print("\nNo LZ4 frame magic found in first 50 bytes")
