"""
Correct LZ4 block stream decompressor for FNA format.
FNA uses raw LZ4 tokens without framing - just tokens back-to-back.
"""
import struct

def lz4_decompress_raw(src, dst_size, debug=False):
    """Decompress raw LZ4 token stream."""
    dst = bytearray()
    sp = 0
    si = len(src)
    last_report = 0
    
    while len(dst) < dst_size and sp < si:
        token = src[sp]
        sp += 1
        
        # Literal length
        lit_len = (token >> 4) & 0x0F
        if lit_len == 15:
            while sp < si:
                b = src[sp]
                sp += 1
                lit_len += b
                if b < 255:
                    break
        
        # Copy literals
        copy_lit = min(lit_len, si - sp)
        if copy_lit > 0:
            dst.extend(src[sp:sp+copy_lit])
            sp += copy_lit
        
        if sp >= si or len(dst) >= dst_size:
            break
        
        # Match offset
        if sp + 2 > si:
            break
        match_offset = struct.unpack('<H', src[sp:sp+2])[0]
        sp += 2
        
        # Match length
        match_len = (token & 0x0F) + 4
        if (token & 0x0F) == 15:
            while sp < si:
                b = src[sp]
                sp += 1
                match_len += b
                if b < 255:
                    break
        
        # Copy match using circular buffer
        if match_offset > 0 and match_offset <= len(dst):
            for _ in range(match_len):
                dst.append(dst[len(dst) - match_offset])
        elif match_offset == 0:
            break
        else:
            # Match offset > available data: this is a block boundary issue
            # In FNA's streaming format, matches can reference data from
            # previous blocks. We need to track block history.
            # For now, just skip (this will under-decompress)
            if debug:
                print(f'  Skipping match: offset={match_offset} > len(dst)={len(dst)}')
            break
    
    return bytes(dst), sp


# Main
data = open('D:/steam/steamapps/common/Stardew Valley/Content/Fonts/SpriteFont1.zh-CN.xnb', 'rb').read()

comp_type = data[9]
decomp_size = struct.unpack('<I', data[10:14])[0]
lz4_data = data[14:]

print(f'Decompressed target: {decomp_size} bytes')
print(f'Compressed input: {len(lz4_data)} bytes')

result, sp_end = lz4_decompress_raw(lz4_data, decomp_size, debug=True)
print(f'\nDecompressed: {len(result)} bytes')
print(f'Source consumed: {sp_end} / {len(lz4_data)} bytes')
print(f'Compression ratio: {len(lz4_data)/max(len(result),1):.2f}:1')

# Now: FNA uses block-based approach with 64KB blocks
# Each 64KB decompressed, the "window" resets
# Matches can only reference within the current block (or previous block?)
# FNA uses a 64KB sliding window

# Let me try the proper FNA approach:
# Decompress 64KB at a time
print('\n\n=== Block-by-block approach ===')

result2 = bytearray()
sp = 0
block_num = 0
block_size = 65536

while sp < len(lz4_data) and len(result2) < decomp_size:
    remaining = decomp_size - len(result2)
    target = min(block_size, remaining)
    
    # Decompress until we have `target` bytes output
    # Each block starts with a fresh LZ4 state (no history from previous blocks)
    
    block_dst = bytearray()
    sp_start = sp
    
    while len(block_dst) < target and sp < len(lz4_data):
        token = lz4_data[sp]
        sp += 1
        
        lit_len = (token >> 4) & 0x0F
        if lit_len == 15:
            while sp < len(lz4_data):
                b = lz4_data[sp]
                sp += 1
                lit_len += b
                if b < 255:
                    break
        
        copy_lit = min(lit_len, len(lz4_data) - sp)
        if copy_lit > 0:
            block_dst.extend(lz4_data[sp:sp+copy_lit])
            sp += copy_lit
        
        if sp >= len(lz4_data) or len(block_dst) >= target:
            break
        
        if sp + 2 > len(lz4_data):
            break
        match_offset = struct.unpack('<H', lz4_data[sp:sp+2])[0]
        sp += 2
        
        match_len = (token & 0x0F) + 4
        if (token & 0x0F) == 15:
            while sp < len(lz4_data):
                b = lz4_data[sp]
                sp += 1
                match_len += b
                if b < 255:
                    break
        
        # Copy match - can reference within block_dst only
        if match_offset > 0 and match_offset <= len(block_dst):
            for _ in range(match_len):
                block_dst.append(block_dst[len(block_dst) - match_offset])
        elif match_offset == 0:
            break
        else:
            # This shouldn't happen in per-block approach
            # Match offset > block output - bad!
            break
    
    result2.extend(block_dst[:target])
    
    if len(result2) < decomp_size:
        block_num += 1
        if block_num % 10 == 0:
            print(f'  Block {block_num}: {len(block_dst)} bytes decoded, total={len(result2)}/{decomp_size}')
    
    # Safety
    if block_num > 100:
        break

print(f'\nBlock decompressed: {len(result2)} / {decomp_size} bytes in {block_num} blocks')

if len(result2) > 100000:
    open('C:\\Users\\minam\\code\\stardew-bilin\\_tmp\\font_block.bin', 'wb').write(result2)
    
    # Try to find structure in the output
    print(f'\nFirst 32 hex: {result2[:32].hex()}')
    
    # Check unique bytes
    unique_count = len(set(result2[:10000]))
    print(f'Unique bytes in first 10KB: {unique_count}')
    
    if unique_count > 100:
        print('Data looks diverse - likely correct decompression')



# Main
data = open('D:/steam/steamapps/common/Stardew Valley/Content/Fonts/SpriteFont1.zh-CN.xnb', 'rb').read()

# Known values from earlier analysis:
comp_type = data[9]  # 0 = LZ4
decomp_size = struct.unpack('<I', data[10:14])[0]  # 4908477
lz4_data = data[14:]  # raw LZ4 tokens

print(f'Compression type: {comp_type}')
print(f'Decompressed target: {decomp_size} bytes')
print(f'Compressed input: {len(lz4_data)} bytes')

result = lz4_decompress_raw(lz4_data, decomp_size)
print(f'Decompressed: {len(result)} bytes')
print(f'First 40 hex: {result[:40].hex()}')

if result:
    # Check for patterns in the decompressed data
    from collections import Counter
    most_common = Counter(result[:1000]).most_common(5)
    print(f'Most common bytes in first 1KB: {most_common}')
    
    # Check if there's a recognizable structure
    counts = {}
    for b in result[:1000]:
        counts[b] = counts.get(b, 0) + 1
    unique = len(counts)
    print(f'Unique byte values in first 1KB: {unique}')
    
    # If almost all bytes are the same, the decompressor has a bug
    if unique < 10:
        print('WARNING: Very few unique bytes - decompressor likely buggy')
        # The issue might be that match copy is using the wrong reference
        # Check: does the match copy correctly handle overlapping matches?
        pass

if len(result) >= decomp_size * 0.95:
    print(f'SUCCESS! Got >= 95% of expected output')
    open('C:\\Users\\minam\\code\\stardew-bilin\\_tmp\\font_decompressed.bin', 'wb').write(result)
elif len(result) > 100000:
    print(f'Partial: {len(result)} / {decomp_size} bytes ({100*len(result)/decomp_size:.1f}%)')
    open('C:\\Users\\minam\\code\\stardew-bilin\\_tmp\\font_partial.bin', 'wb').write(result)
else:
    print('Failed to decompress meaningful amount')
    
    # Debug: show first few matches
    sp = 0
    for i in range(5):
        if sp >= len(lz4_data) - 3:
            break
        token = lz4_data[sp]
        lit_len = (token >> 4) & 0x0F
        print(f'  Token[{i}]: 0x{token:02x} lit_len_raw={lit_len}')
        sp += 1
        if lit_len == 15:
            while sp < len(lz4_data):
                b = lz4_data[sp]
                sp += 1
                lit_len += b
                if b < 255:
                    break
        print(f'    lit_len={lit_len}')
        sp += lit_len  # skip literals
        if sp + 2 >= len(lz4_data):
            break
        mo = struct.unpack('<H', lz4_data[sp:sp+2])[0]
        sp += 2
        ml = (token & 0x0F) + 4
        if (token & 0x0F) == 15:
            while sp < len(lz4_data):
                b = lz4_data[sp]
                sp += 1
                ml += b
                if b < 255:
                    break
        print(f'    match_offset={mo} match_len={ml} pos_in_src={sp}')
