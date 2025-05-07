import struct
import binascii
from pathlib import Path
from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()
build_dir = Path(env.subst("$BUILD_DIR"))
firmware_bin = build_dir / "firmware.bin"
output_bin = build_dir / "firmware_with_crc.bin"

BOARD_ID = 1062  # Replace with your actual board ID
GIT_HASH = 0     # Set if known, otherwise 0
VERSION_MAJOR = 1
VERSION_MINOR = 0

# ArduPilot unsigned firmware descriptor signature
APP_DESCRIPTOR_SIGNATURE = bytes([0x40, 0xa2, 0xe4, 0xf1, 0x64, 0x68, 0x91, 0x06])

# Board flash memory layout (STM32L431CCUx: 256KB FLASH, first 40KB reserved)
FLASH_START = 0x0800A000
FLASH_SIZE  = (256 * 1024) - (40 * 1024)  # 216 KB
FLASH_END   = FLASH_START + FLASH_SIZE
DESC_SIZE   = 36  # unsigned descriptor length


def append_descriptor(source, target, env):
    # Read the raw firmware binary
    firmware = bytearray(firmware_bin.read_bytes())

    # Calculate padding so descriptor sits at FLASH_END - DESC_SIZE
    current_size = len(firmware)
    pad_len = (FLASH_END - DESC_SIZE) - (FLASH_START + current_size)
    if pad_len < 0:
        raise RuntimeError("Firmware is too big to fit descriptor at the end of flash")
    # Pad with 0xFF
    firmware += b'\xFF' * pad_len

    # firmware_size is the length before descriptor
    firmware_size = len(firmware)

    # CRC1: over firmware up to descriptor
    image_crc1 = binascii.crc32(firmware) & 0xFFFFFFFF

    # Build descriptor with placeholder for CRC2
    descriptor = bytearray(struct.pack(
        "<8sIIIIBBH8s",
        APP_DESCRIPTOR_SIGNATURE,
        image_crc1,
        0,                # placeholder for image_crc2
        firmware_size,
        GIT_HASH,
        VERSION_MAJOR,
        VERSION_MINOR,
        BOARD_ID,
        bytes(8)          # reserved
    ))

    # CRC2: from version_major (offset 8+4+4+4+4) to end of descriptor
    crc2_start = 8 + 4 + 4 + 4 + 4
    image_crc2 = binascii.crc32(descriptor[crc2_start:]) & 0xFFFFFFFF

    # Insert CRC2 into descriptor
    struct.pack_into("<I", descriptor, 12, image_crc2)

    # Append descriptor at end
    firmware += descriptor

    print("Appending ArduPilot descriptor:")
    print(f"  Image CRC1: 0x{image_crc1:08X}")
    print(f"  Image CRC2: 0x{image_crc2:08X}")
    print(f"  Size:       {firmware_size} bytes")
    print(f"  Board ID:   {BOARD_ID}")
    print(f"  Signature:  {APP_DESCRIPTOR_SIGNATURE.hex()}")

    # Write out new firmware
    with open(output_bin, "wb") as f:
        f.write(firmware)

    # Overwrite original firmware.bin so subsequent steps pick it up
    firmware_bin.write_bytes(firmware)

# Hook into the PlatformIO build
env.AddPostAction("buildprog", append_descriptor)
