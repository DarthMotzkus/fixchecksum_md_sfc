#!/usr/bin/env python3
"""
Unified ROM Checksum Fixer
Detects and fixes checksums for Genesis/Mega Drive and SNES ROMs
"""

from pathlib import Path
from typing import Tuple, Optional

# SNES constants
HEADER_LOCS = [0x7F00, 0xFF00, 0x407F00, 0x40FF00]
HEADER_NAME = ["LoROM", "HiROM", "Ex-LoROM", "Ex-HiROM"]


# ============================================================================
# GENESIS/MEGA DRIVE FUNCTIONS
# ============================================================================

def detect_genesis(data: bytes) -> bool:
    """Check if ROM is Genesis/Mega Drive."""
    if len(data) >= 0x110:
        try:
            sig = data[0x100:0x110].decode('utf-8', errors='ignore').strip()
            return sig == "SEGA MEGA DRIVE" or sig == "SEGA GENESIS"
        except:
            pass
    return False


def read_word(data: bytes, offset: int) -> int:
    """Read big-endian word."""
    if offset + 1 >= len(data):
        return 0
    return (data[offset] << 8) | data[offset + 1]


def fix_genesis_checksum(rom: bytearray) -> Tuple[bool, str]:
    """Fix Genesis checksum."""
    CHECKSUM_OFFSET = 0x18E
    CALC_START = 0x200
    
    if len(rom) < CHECKSUM_OFFSET + 2:
        return False, "ROM too small"
    
    # Read header checksum
    header_cs = read_word(rom, CHECKSUM_OFFSET)
    
    # Compute checksum
    checksum = 0
    for i in range(CALC_START, len(rom), 2):
        word = read_word(rom, i)
        checksum += word
    
    checksum = checksum & 0xFFFF
    
    if header_cs == checksum:
        return False, f"OK: 0x{checksum:04X}"
    
    # Write new checksum
    rom[CHECKSUM_OFFSET] = (checksum >> 8) & 0xFF
    rom[CHECKSUM_OFFSET + 1] = checksum & 0xFF
    
    return True, f"Fixed: 0x{header_cs:04X} → 0x{checksum:04X}"


# ============================================================================
# SNES FUNCTIONS
# ============================================================================

def check_map_mode(m: int) -> bool:
    """Return True if map mode looks valid for SNES ROMs."""
    return m in {0x20, 0x21, 0x22, 0x23, 0x25, 0x30, 0x31, 0x32, 0x33, 0x35, 0x3A}


def check_rom_type(t: int) -> bool:
    """Return True if ROM type code looks valid."""
    if t < 3:
        return True
    hi = t >> 4
    if hi in {0x0, 0x1, 0x2, 0x3, 0x4, 0x5, 0xE, 0xF}:
        lo = t & 0x0F
        return lo in {3, 4, 5, 6, 9}
    return False


def check_bsx_map(m: int) -> bool:
    """BSX-compatible map modes."""
    return m in {0x20, 0x21, 0x30, 0x31}


def check_bsx_type(t: int) -> bool:
    """BSX-compatible type has low nibble == 0."""
    return (t & 0xF) == 0


def find_snes_header_base(rom: bytes) -> Tuple[Optional[int], Optional[int], Optional[int], bool]:
    """
    Find a plausible SNES header.
    Returns: (header_base, header_index, map_mode, is_bsx)
    """
    size = len(rom)

    def valid_at(b: int) -> bool:
        if b + 0xDF >= size:
            return False
        return (
            check_map_mode(rom[b + 0xD5]) and
            check_rom_type(rom[b + 0xD6]) and
            (rom[b + 0xD7] > 6 and rom[b + 0xD7] < 0x0E) and
            (rom[b + 0xD8] < 8) and
            (rom[b + 0xD9] < 0x15)
        )

    for i in range(4):
        base = HEADER_LOCS[i]
        if base >= size:
            break

        mm = rom[base + 0xD5]

        if valid_at(base):
            if (mm == 0x25 or mm == 0x35) and i < 2:
                newi = mm >> 4
                newbase = HEADER_LOCS[newi]
                if newbase < size and valid_at(newbase):
                    return newbase, newi, rom[newbase + 0xD5], False
            return base, i, mm, False

        if (base + 0xD9) < size:
            if check_bsx_map(rom[base + 0xD8]) and check_bsx_type(rom[base + 0xD9]):
                return base, i, mm, True

    return None, None, None, False


def rom_size_from_header_byte(sz_code: int) -> int:
    """Header ROM size code to bytes: 1 << (sz_code + 10)."""
    return 1 << (sz_code + 10)


def calculate_snes_checksum(rom: bytes, header_base: int, map_mode: int) -> Tuple[int, int]:
    """Compute the 16-bit checksum and its complement as stored in the SNES header."""
    size = len(rom)
    s = 0x01FE - sum(rom[header_base + 0xDC: header_base + 0xE0])
    s += sum(rom)

    declared_bytes = rom_size_from_header_byte(rom[header_base + 0xD7])

    if map_mode == 0x3A and rom[header_base + 0xD7] < 0x0D and size < declared_bytes:
        s <<= 1
    elif size < declared_bytes and size > 0x20000 and map_mode != 0x3A:
        missing = declared_bytes - size
        data_repeat = declared_bytes
        while data_repeat > size:
            data_repeat >>= 1
        data_repeat_offset = size - data_repeat
        if data_repeat < size and data_repeat_offset > 0:
            for j in range(missing):
                idx = (j % data_repeat_offset) + data_repeat
                s += rom[idx]

    checksum = s & 0xFFFF
    complement = (~checksum) & 0xFFFF
    return checksum, complement


def apply_snes_checksum(rom: bytearray, header_base: int, checksum: int, complement: int, offset: int = 0) -> None:
    """Write complement and checksum to 0xDC..0xDF in the selected header."""
    rom[offset + header_base + 0xDC] = complement & 0xFF
    rom[offset + header_base + 0xDD] = (complement >> 8) & 0xFF
    rom[offset + header_base + 0xDE] = checksum & 0xFF
    rom[offset + header_base + 0xDF] = (checksum >> 8) & 0xFF


def fix_snes_checksum(patched: bytearray, offset: int) -> Tuple[bool, str]:
    """Fix SNES checksum."""
    content = patched[offset:]

    base, idx, map_mode, is_bsx = find_snes_header_base(content)
    if base is None:
        return False, "SNES header not found"
    if is_bsx:
        return False, "BSX ROM - skipped"

    # Get old checksum
    old_cs = content[base + 0xDE] | (content[base + 0xDF] << 8)
    old_complement = content[base + 0xDC] | (content[base + 0xDD] << 8)

    # Calculate new
    checksum, complement = calculate_snes_checksum(content, base, map_mode)

    if old_cs == checksum and old_complement == complement:
        return False, f"{HEADER_NAME[idx]} - OK (0x{checksum:04X})"

    # Apply checksum
    apply_snes_checksum(patched, base, checksum, complement, offset)

    return True, f"{HEADER_NAME[idx]} - Fixed (0x{old_cs:04X} → 0x{checksum:04X})"


# ============================================================================
# MAIN PROCESSING
# ============================================================================

def detect_rom_type(data: bytes) -> Optional[str]:
    """Detect ROM type: 'genesis' or 'snes'."""
    if detect_genesis(data):
        return "genesis"
    
    # Check for SNES
    has_copier = (len(data) % 1024) == 512
    offset = 512 if has_copier else 0
    content = data[offset:]
    
    base, _, _, _ = find_snes_header_base(content)
    if base is not None:
        return "snes"
    
    return None


def process_rom(rom_path: Path) -> None:
    """Process a ROM file (Genesis or SNES)."""
    try:
        with open(rom_path, "rb") as f:
            data = f.read()
        
        rom_type = detect_rom_type(data)
        
        if rom_type == "genesis":
            rom = bytearray(data)
            fixed, msg = fix_genesis_checksum(rom)
            
            if fixed:
                with open(rom_path, "wb") as f:
                    f.write(rom)
                print(f"  ✓ {rom_path.name} (Genesis): {msg}")
            else:
                print(f"  ○ {rom_path.name} (Genesis): {msg}")
        
        elif rom_type == "snes":
            patched = bytearray(data)
            has_copier = (len(patched) % 1024) == 512
            offset = 512 if has_copier else 0
            
            fixed, msg = fix_snes_checksum(patched, offset)
            
            if fixed:
                with open(rom_path, "wb") as f:
                    f.write(patched)
                print(f"  ✓ {rom_path.name} (SNES): {msg}")
            else:
                print(f"  ○ {rom_path.name} (SNES): {msg}")
        
        else:
            print(f"  ✗ {rom_path.name}: Unknown ROM type")
    
    except Exception as e:
        print(f"  ✗ {rom_path.name}: Error - {e}")


def main():
    """Scan directory and subdirectories for ROM checksums."""
    current_dir = Path.cwd()
    extensions = {".bin", ".md", ".sfc", ".smc"}
    roms = sorted([f for f in current_dir.rglob("*") 
                   if f.is_file() and f.suffix.lower() in extensions])
    
    if not roms:
        print("No ROM files found (.bin, .md, .sfc, .smc)")
        return
    
    print(f"Found {len(roms)} ROM file(s)\n")
    for rom_path in roms:
        process_rom(rom_path)


if __name__ == "__main__":
    main()