import struct
import binascii
from pathlib import Path
from SCons.Script import ARGUMENTS, COMMAND_LINE_TARGETS, DefaultEnvironment

env = DefaultEnvironment()
build_dir = Path(env.subst("$BUILD_DIR"))
firmware_bin = build_dir / "firmware.bin"
output_bin = build_dir / "firmware_with_crc.bin"

def append_crc(source, target, env):
    with open(firmware_bin, "rb") as f:
        data = f.read()

    crc = binascii.crc32(data) & 0xFFFFFFFF
    print(f"Appending CRC32: 0x{crc:08X}")
    data += struct.pack("<I", crc)

    with open(output_bin, "wb") as f:
        f.write(data)

    # Copy result to final .pio/build/.../firmware.bin so upload tools pick it up
    firmware_bin.unlink()
    output_bin.rename(firmware_bin)

env.AddPostAction("buildprog", append_crc)