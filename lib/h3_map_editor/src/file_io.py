#!/usr/bin/env python3

in_file  = None
out_file = None

# String encoding: Try GBK (Chinese) first, fall back to latin-1
# HoMM3 maps use different encodings depending on the game's localization
STRING_ENCODINGS = ['gbk', 'latin-1']

def read_raw(length: int) -> bytes:
    global in_file
    return in_file.read(length)

def read_int(length: int) -> int:
    global in_file
    return int.from_bytes(in_file.read(length), 'little')

def read_str(length: int) -> str:
    global in_file
    raw_bytes = in_file.read(length)
    # Try encodings in order
    for encoding in STRING_ENCODINGS:
        try:
            return raw_bytes.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    # Last resort: decode with errors replaced
    return raw_bytes.decode('latin-1', errors='replace')

def read_bits(length: int) -> list:
    temp_bits = []
    raw_data  = read_raw(length)

    for c in raw_data:
        bits = format(int(c), '#010b').removeprefix('0b')[::-1]
        for b in bits:
            temp_bits.append(1 if b == '1' else 0)

    return temp_bits

def write_raw(data: bytes):
    global out_file
    out_file.write(data)

def write_int(data: int, length: int) -> None:
    global out_file
    out_file.write(data.to_bytes(length, 'little'))

def encode_str(data: str) -> bytes:
    """Encode string to bytes using the appropriate encoding."""
    for encoding in STRING_ENCODINGS:
        try:
            return data.encode(encoding)
        except (UnicodeEncodeError, LookupError):
            continue
    return data.encode('latin-1', errors='replace')

def str_byte_len(data: str) -> int:
    """Get the byte length of a string when encoded."""
    return len(encode_str(data))

def write_str(data: str) -> None:
    global out_file
    out_file.write(encode_str(data))

def write_bits(data: list) -> None:
    for i in range(0, len(data), 8):
        s = ""
        for b in range(8):
            s += '1' if data[i + b] else '0'
        write_int(int(s[::-1], 2), 1)

def seek(length: int) -> None:
    global in_file
    in_file.seek(length, 1)

def peek(length: int) -> None:
    global in_file
    data = read_raw(length)

    s = "\n"
    i = 1
    for b in data:
        n = str(b)
        s += ("  " if i < 10 else " ") + str(i) + ": "
        s += ' ' * (3-len(n))  + n + ' '
        s += format(int(n), '#010b').removeprefix('0b')
        s += '\n'
        i += 1

    print(s)
    in_file.seek(-length, 1)
