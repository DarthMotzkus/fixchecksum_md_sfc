# ROM Checksum Fixer

Automated tool to detect and correct checksums for Mega Drive/Genesis and Super Nintendo (SNES) ROMs.

## Features

- 🎮 Supports **Mega Drive/Genesis** (.bin, .md) and **SNES** (.sfc, .smc)
- 🔍 Automatic ROM type detection
- ⚙️ Batch processing of all ROMs in directory
- 📝 No external dependencies (Python standard library only)
- ✅ Complete header validation before modification

## Requirements

- Python 3.6+

## Installation

Clone the repository:

```bash
git clone <your-repo>
cd rom-checksum-fixer
```

## Usage

Place ROM files in the same directory as the script and run:

```bash
python rom_checksum_fixer.py
```

The script will:
1. Scan all ROMs (.bin, .md, .sfc, .smc)
2. Validate ROM type
3. Calculate correct checksum
4. Update header if necessary

## Output

```
Found 3 ROM file(s). Processing...

  ✓ game1.bin: Genesis checksum fixed: 0x1234 → 0x5678
  ○ game2.sfc: SNES (HiROM) checksum already correct: 0xABCD
  ✗ game3.rom: Unknown ROM type
```

### Symbols

- `✓` - Checksum successfully corrected
- `○` - Checksum was already correct
- `✗` - Error or unknown ROM type

## Support

### Genesis/Mega Drive

- Detects by signature at offset 0x100
- Validates signatures: "SEGA MEGA DRIVE" or "SEGA GENESIS"
- Recalculates 16-bit checksum from offset 0x200
- Writes to offset 0x18E

### SNES

- Supports all mapping types: LoROM, HiROM, Ex-LoROM, Ex-HiROM
- Preserves 512-byte copier headers
- Calculates checksum with declared size compensation
- Updates complement + checksum (4 bytes in header)

## Safety

- ✅ Validates header before modifying
- ✅ Correctly detects ROM type
- ✅ Checks checksums only once
- ✅ Robust error handling

## License

MIT

## Credits

Based on original Genesis and SNES checksum validation scripts, modernized and unified.