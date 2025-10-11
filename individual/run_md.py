#!/usr/bin/env python3
"""
Genesis/Mega Drive Checksum Fixer
Scans directory for .bin and .md files and corrects checksums
"""

from pathlib import Path
from typing import Tuple


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


def process_rom(rom_path: Path) -> None:
    """Process ROM file."""
    try:
        with open(rom_path, "rb") as f:
            rom = bytearray(f.read())
        
        if not detect_genesis(rom):
            print(f"  ✗ {rom_path.name}: Not a Genesis ROM")
            return
        
        fixed, msg = fix_genesis_checksum(rom)
        
        if fixed:
            with open(rom_path, "wb") as f:
                f.write(rom)
            print(f"  ✓ {rom_path.name}: {msg}")
        else:
            print(f"  ○ {rom_path.name}: {msg}")
    
    except Exception as e:
        print(f"  ✗ {rom_path.name}: {e}")


def main():
    """Scan directory and fix Genesis ROMs."""
    current_dir = Path.cwd()
    extensions = {".bin", ".md"}
    roms = sorted([f for f in current_dir.iterdir() 
                   if f.is_file() and f.suffix.lower() in extensions])
    
    if not roms:
        print("No Genesis ROM files found (.bin, .md)")
        return
    
    print(f"Found {len(roms)} Genesis ROM(s)\n")
    for rom_path in roms:
        process_rom(rom_path)


if __name__ == "__main__":
    from typing import Tuple
    main()