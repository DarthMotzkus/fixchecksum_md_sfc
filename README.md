# Unified ROM Checksum Fixer

Automatically detects and corrects checksums for Sega Genesis/Mega Drive and Super Nintendo (SNES) ROMs.

## Features

- 🎮 Supports Genesis/Mega Drive (.bin, .md) and SNES (.sfc, .smc)
- 🔍 Automatic ROM type detection
- ⚙️ Batch processing of all ROMs in directory
- 📝 No external dependencies (Python standard library only)
- ✅ Validates headers before modifying

## Requirements

- Python 3.6+

## Installation

Clone the repository:

```bash
git clone <your-repo>
cd rom-checksum-fixer
```

## Usage

Place ROM files in the script directory or subdirectories and run:

```bash
python run.py
```

The script will recursively scan the directory and all subdirectories to:
1. Detect ROM type (Genesis or SNES)
2. Validate ROM header
3. Calculate correct checksum
4. Update if necessary

## Output

```
Found 3 ROM file(s)

  ✓ game1.bin (Genesis): Fixed: 0x1234 → 0x5678
  ○ game2.sfc (SNES): LoROM - OK (0xABCD)
  ✗ game3.rom: Unknown ROM type
```

### Symbols

- `✓` - Checksum corrected successfully
- `○` - Checksum already correct
- `✗` - Error or unknown ROM type

## ROM Support

### Genesis/Mega Drive

- Extensions: .bin, .md
- Detects: "SEGA MEGA DRIVE" or "SEGA GENESIS" signature
- Calculates: 16-bit checksum from offset 0x200
- Writes to: offset 0x18E

### SNES

- Extensions: .sfc, .smc
- Supports: LoROM, HiROM, Ex-LoROM, Ex-HiROM
- Detects: All valid SNES header configurations
- Preserves: 512-byte copier headers if present
- Calculates: 16-bit checksum with 16-bit complement

## Safety

- ✅ Validates ROM type before modifying
- ✅ Compares old vs new checksum
- ✅ Only writes if checksum differs
- ✅ Robust error handling

## License

MIT