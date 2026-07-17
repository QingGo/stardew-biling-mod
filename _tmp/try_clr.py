"""
Try decompressing using FNA's embedded LZ4 via Python ctypes.
MonoGame.Framework.dll might have exportable LZ4 functions.
"""

import ctypes, struct, os

dll_path = 'D:/steam/steamapps/common/Stardew Valley/MonoGame.Framework.dll'

# Check if it has any LZ4-related exports
try:
    dll = ctypes.CDLL(dll_path)
    print("Loaded DLL via CDLL")
except:
    print("CDLL failed (expected - it's a .NET dll)")
    pass

# The .NET dll isn't a native DLL, so ctypes can't load it.

# But maybe there's another way using clr (pythonnet)
# Since we don't have it installed, let's try install it
import subprocess
result = subprocess.run(
    ['python', '-m', 'pip', 'install', 'pythonnet', '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple'],
    capture_output=True, text=True, timeout=30
)
print('install stdout:', result.stdout[-200:] if result.stdout else '')
print('install stderr:', result.stderr[-200:] if result.stderr else '')

# Try importing after install attempt
try:
    import clr
    clr.AddReference(dll_path)
    print('CLR loaded MonoGame.Framework.dll')
except ImportError:
    print('pythonnet not available (install failed)')
except Exception as e:
    print(f'CLR error: {e}')
