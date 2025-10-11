#!/usr/bin/env python3
"""
ROM Checksum Fixer - Automatically detects and corrects Genesis/SNES ROM checksums.
Supports: Mega Drive (.bin, .md) and SNES (.sfc, .smc)
"""

import struct
import sys
from pathlib import Path
from typing import Tuple, Optional


# Genesis/Mega Drive constants
GENESIS_CHECKSUM_OFFSET = 0x18E
GENESIS_CALC_START = 0x200
GENESIS_SIGNATURES = ["SEGA MEGA DRIVE", "SEGA GENESIS"]
GENESIS_SIG_OFFSET = 0x100

# SNES constants
SNES_HEADER_LOCS = [0x7F00, 0xFF00, 0x407F00, 0x40FF00]
SNES_HEADER_NAMES = ["LoROM", "HiROM", "Ex-LoROM", "Ex-HiROM"]


def detect_rom_type(data: bytes) -> Optional[str]:
    """Detect if ROM is Genesis or SNES."""
    if len(data) < 0x110:
        return None
    
    # Check for Genesis/Mega Drive signature
    if len(data) >= 0x110:
        try:
            sig = data[GENESIS_SIG_OFFSET:0x110].decode('utf-8', errors='ignore').strip()
            if any(genesis_sig in sig for genesis_sig in GENESIS_SIGNATURES):
                return "genesis"
        except:
            pass
    
    # Check for SNES header
    for header_loc in SNES_HEADER_LOCS:
        if header_loc + 0xDF < len(data):
            if _is_valid_snes_header(data, header_loc):
                return "snes"
    
    return None


def _is_valid_snes_header(rom: bytes, base: int) -> bool:
    """Validate SNES header at given offset."""
    try:
        map_mode = rom[base + 0xD5]
        rom_type = rom[base + 0xD6]
        rom_size = rom[base + 0xD7]
        ram_size = rom[base + 0xD8]
        region = rom[base + 0xD9]
        
        valid_map = map_mode in {0x20, 0x21, 0x22, 0x23, 0x25, 0x30, 0x31, 0x32, 0x33, 0x35, 0x3A}
        valid_type = rom_type < 3 or (rom_type >> 4) in {0x0, 0x1, 0x2, 0x3, 0x4, 0x5, 0xE, 0xF}
        valid_size = 6 < rom_size < 0x0E
        valid_ram = ram_size < 8
        valid_region = region < 0x15
        
        return valid_map and valid_type and valid_size and valid_ram and valid_region
    except:
        return False


def fix_genesis_checksum(rom_data: bytearray) -> Tuple[bool, str]:
    """Fix Genesis/Mega Drive ROM checksum."""
    if len(rom_data) < GENESIS_CHECKSUM_OFFSET + 2:
        return False, "ROM too small for Genesis checksum"
    
    # Read header checksum
    header_checksum = (rom_data[GENESIS_CHECKSUM_OFFSET] << 8) | rom_data[GENESIS_CHECKSUM_OFFSET + 1]
    
    # Calculate correct checksum
    checksum = 0
    for i in range(GENESIS_CALC_START, len(rom_data), 2):
        if i + 1 < len(rom_data):
            word = (rom_data[i] << 8) | rom_data[i + 1]
            checksum = (checksum + word) & 0xFFFF
    
    if header_checksum == checksum:
        return False, f"Genesis checksum already correct: 0x{checksum:04X}"
    
    # Write new checksum
    rom_data[GENESIS_CHECKSUM_OFFSET] = (checksum >> 8) & 0xFF
    rom_data[GENESIS_CHECKSUM_OFFSET + 1] = checksum & 0xFF
    
    return True, f"Genesis checksum fixed: 0x{header_checksum:04X} → 0x{checksum:04X}"


def find_snes_header(rom: bytes) -> Tuple[Optional[int], Optional[int], int]:
    """Find valid SNES header and return (base, index, map_mode)."""
    for i, header_loc in enumerate(SNES_HEADER_LOCS):
        if header_loc + 0xDF < len(rom) and _is_valid_snes_header(rom, header_loc):
            map_mode = rom[header_loc + 0xD5]
            return header_loc, i, map_mode
    return None, None, 0


def calculate_snes_checksum(rom: bytes, header_base: int, map_mode: int) -> Tuple[int, int]:
    """Calculate SNES checksum and complement."""
    size = len(rom)
    s = 0x01FE - sum(rom[header_base + 0xDC:header_base + 0xE0])
    s += sum(rom)
    
    declared_bytes = 1 << (rom[header_base + 0xD7] + 10)
    
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


def fix_snes_checksum(rom_data: bytearray) -> Tuple[bool, str]:
    """Fix SNES ROM checksum."""
    has_copier = (len(rom_data) % 1024) == 512
    offset = 512 if has_copier else 0
    content = rom_data[offset:]
    
    base, idx, map_mode = find_snes_header(content)
    if base is None:
        return False, "Valid SNES ROM header not found"
    
    checksum, complement = calculate_snes_checksum(content, base, map_mode)
    
    old_checksum = (content[base + 0xDE] | (content[base + 0xDF] << 8))
    if old_checksum == checksum:
        return False, f"SNES ({SNES_HEADER_NAMES[idx]}) checksum already correct: 0x{checksum:04X}"
    
    # Apply checksum
    content[base + 0xDC] = complement & 0xFF
    content[base + 0xDD] = (complement >> 8) & 0xFF
    content[base + 0xDE] = checksum & 0xFF
    content[base + 0xDF] = (checksum >> 8) & 0xFF
    
    return True, f"SNES ({SNES_HEADER_NAMES[idx]}) checksum fixed: 0x{old_checksum:04X} → 0x{checksum:04X}"


def process_rom(rom_path: Path) -> None:
    """Process a single ROM file."""
    try:
        with open(rom_path, "r+b") as f:
            rom_data = bytearray(f.read())
        
        rom_type = detect_rom_type(rom_data)
        
        if not rom_type:
            print(f"  ✗ {rom_path.name}: Unknown ROM type")
            return
        
        if rom_type == "genesis":
            fixed, msg = fix_genesis_checksum(rom_data)
        else:
            fixed, msg = fix_snes_checksum(rom_data)
        
        if fixed:
            with open(rom_path, "wb") as f:
                f.write(rom_data)
            print(f"  ✓ {rom_path.name}: {msg}")
        else:
            print(f"  ○ {rom_path.name}: {msg}")
    
    except Exception as e:
        print(f"  ✗ {rom_path.name}: Error - {str(e)}")


def main():
    """Main function - scan and process ROMs in current directory."""
    current_dir = Path.cwd()
    rom_extensions = {".bin", ".md", ".sfc", ".smc"}
    
    rom_files = [f for f in current_dir.iterdir() if f.is_file() and f.suffix.lower() in rom_extensions]
    
    if not rom_files:
        print("No ROM files found (.bin, .md, .sfc, .smc)")
        return
    
    print(f"Found {len(rom_files)} ROM file(s). Processing...\n")
    
    for rom_path in sorted(rom_files):
        process_rom(rom_path)


if __name__ == "__main__":
    main()