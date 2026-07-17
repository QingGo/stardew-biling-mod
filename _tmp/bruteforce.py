"""
Brute-force the XNB header size by trying different offsets.
The character list has a known signature: a 7-bit encoded count followed by 2-byte char values.
"""

import struct

path = 'D:/steam/steamapps/common/Stardew Valley/Content/Fonts/SpriteFont1.zh-CN.xnb'
data = open(path, 'rb').read()

def read_7bit(data, pos):
    val = 0
    shift = 0
    while True:
        b = data[pos]
        val |= (b & 0x7F) << shift
        shift += 7
        pos += 1
        if (b & 0x80) == 0:
            break
    return val, pos

# Try every possible header offset from 1 to 50
print("Looking for valid XNB body structure...")
print("(looking for: reader_count, texture_dimensions, char_list_count)")

for header_size in range(3, 50):
    body = data[header_size:]
    pos = 0
    
    if len(body) < 20:
        continue
    
    # Try reading type reader count
    try:
        reader_count, pos = read_7bit(body, pos)
    except:
        continue
    
    # reader count should be small (0-10)
    if reader_count > 20:
        continue
    
    # Record position for checking
    rc_pos = pos
    
    # Skip type readers (if any)
    try:
        for _ in range(reader_count):
            name_len, pos = read_7bit(body, pos)
            pos += name_len
            rv = struct.unpack('<i', body[pos:pos+4])[0]
            pos += 4
    except:
        continue
    
    # Read shared resource count
    try:
        shared_count, pos = read_7bit(body, pos)
    except:
        continue
    
    if shared_count > 1000:
        continue
    
    # Read type ID
    try:
        type_id, pos = read_7bit(body, pos)
    except:
        continue
    
    if type_id > 20:
        continue
    
    # Now try to read texture data (next should be format int32)
    if pos + 20 > len(body):
        continue
    
    tex_fmt = struct.unpack('<i', body[pos:pos+4])[0]
    if tex_fmt < 0 or tex_fmt > 20:
        continue
    
    tex_w = struct.unpack('<i', body[pos+4:pos+8])[0]
    tex_h = struct.unpack('<i', body[pos+8:pos+12])[0]
    
    if tex_w < 1 or tex_w > 16384 or tex_h < 1 or tex_h > 16384:
        continue
    
    mips = struct.unpack('<i', body[pos+12:pos+16])[0]
    px_size = struct.unpack('<i', body[pos+16:pos+20])[0]
    
    # Check pixel data doesn't exceed body
    if pos + 20 + px_size > len(body):
        continue
    
    # This looks valid! Print all candidate headers
    print(f'\nVALID STRUCTURE at header_size={header_size}:')
    print(f'  Reader count: {reader_count}')
    print(f'  Shared count: {shared_count}')
    print(f'  Type ID: {type_id}')
    print(f'  Texture: {tex_w}x{tex_h} fmt={tex_fmt} mips={mips} px={px_size}')
    
    # Check also the English font
    en_data = open(path.replace('zh-CN', ''), 'rb').read()
    en_body = en_data[header_size:]
    en_pos = 0
    en_rc, en_pos = read_7bit(en_body, en_pos)
    print(f'  English font at same header: reader_count={en_rc}')

print('\nDone')
