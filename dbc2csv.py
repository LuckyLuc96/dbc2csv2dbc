import struct
import sys
import csv
'''
USAGE:
python dbc2csv.py input.dbc output.csv
'''

def read_dbc_header(file_handle):
    header = file_handle.read(20)
    magic, record_count, field_count, record_size, string_block_size = struct.unpack('<4s4I', header)

    if magic != b'WDBC':
        raise ValueError("Not a valid DBC file")

    return record_count, field_count, record_size, string_block_size

def read_raw_records(file_handle, record_count, record_size, field_count):
    records_data = file_handle.read(record_count * record_size)

    raw_records = []
    for i in range(record_count):
        offset = i * record_size
        expected_data_size = field_count * 4
        record_bytes = records_data[offset:offset + expected_data_size]
        raw_records.append(record_bytes)

    return raw_records

def parse_string_block(string_block):
    strings = {}
    offset = 0
    while offset < len(string_block):
        end = string_block.find(b'\x00', offset)
        if end == -1:
            break
        string = string_block[offset:end].decode('utf-8', errors='replace')
        strings[offset] = string
        offset = end + 1
    return strings

def extract_column_bytes(raw_records, field_count):
    column_bytes = []

    for col in range(field_count):
        col_bytes = []
        for record_bytes in raw_records:
            byte_offset = col * 4
            if byte_offset + 4 <= len(record_bytes):
                col_bytes.append(record_bytes[byte_offset:byte_offset + 4])
            else:
                # If we don't have enough bytes, pad with zeros
                padded_bytes = record_bytes[byte_offset:] + b'\x00' * (4 - (len(record_bytes) - byte_offset))
                if len(padded_bytes) == 4:
                    col_bytes.append(padded_bytes)
                else:
                    col_bytes.append(b'\x00\x00\x00\x00')
        column_bytes.append(col_bytes)

    return column_bytes

def detect_string_column(col_bytes, string_dict, string_block_size):
    int_values = []
    for byte_chunk in col_bytes:
        if len(byte_chunk) == 4:
            int_val = struct.unpack('<i', byte_chunk)[0]
            int_values.append(int_val)
        else:
            int_values.append(0)

    string_match_count = sum(
        1 for v in int_values if v in string_dict and 0 <= v < string_block_size)

    return string_match_count == len(int_values)

def detect_float_column(col_bytes):
    int_values = []
    for byte_chunk in col_bytes:
        if len(byte_chunk) == 4:
            int_val = struct.unpack('<i', byte_chunk)[0]
            int_values.append(int_val)
        else:
            int_values.append(0)

    float_values = []
    for byte_chunk in col_bytes:
        float_val = struct.unpack('<f', byte_chunk)[0]
        float_values.append(float_val)

    invalid_floats = sum(1 for v in float_values if v != v or abs(v) == float('inf') or (v != 0 and (abs(v) < 1e-30 or abs(v) > 1e30)))
    reasonable_ints = sum(1 for v in int_values if abs(v) < 100000000)  # less than 100 million

    # Prefer integers unless we have strong evidence for floats
    if (invalid_floats < len(float_values) * 0.1 and
        reasonable_ints < len(int_values) * 0.3 and
        len(int_values) > 0):
        return True

    return False

def detect_column_types(column_bytes, string_dict, string_block_size):
    """Detect the data type for each column."""
    col_types = []

    for col, col_bytes in enumerate(column_bytes):
        if detect_string_column(col_bytes, string_dict, string_block_size):
            col_types.append("string")
            print(f"Debug: Column {col} detected as string")
        elif detect_float_column(col_bytes):
            col_types.append("float")
            print(f"Debug: Column {col} detected as FLOAT")
        else:
            col_types.append("int")
            print(f"Debug: Column {col} detected as INT")

    return col_types

def parse_record_values(raw_records, field_count, col_types):
    """Parse raw record bytes into typed values."""
    records = []

    for record_bytes in raw_records:
        record = []
        for col in range(field_count):
            byte_offset = col * 4
            if byte_offset + 4 <= len(record_bytes):
                byte_chunk = record_bytes[byte_offset:byte_offset + 4]
            else:
                # Pad with zeros if not enough data
                padded_bytes = record_bytes[byte_offset:] + b'\x00' * (4 - (len(record_bytes) - byte_offset))
                if len(padded_bytes) == 4:
                    byte_chunk = padded_bytes
                else:
                    byte_chunk = b'\x00\x00\x00\x00'

            if len(byte_chunk) == 4:
                if col_types[col] == "float":
                    value = struct.unpack('<f', byte_chunk)[0]
                else:
                    value = struct.unpack('<i', byte_chunk)[0]
            else:
                value = 0
            record.append(value)
        records.append(record)

    return records

def read_dbc(file_path):
    """Main function to read and parse a DBC file."""
    with open(file_path, 'rb') as f:
        record_count, field_count, record_size, string_block_size = read_dbc_header(f)

        raw_records = read_raw_records(f, record_count, record_size, field_count)
        string_block = f.read(string_block_size)

        string_dict = parse_string_block(string_block)
        column_bytes = extract_column_bytes(raw_records, field_count)
        col_types = detect_column_types(column_bytes, string_dict, string_block_size)
        records = parse_record_values(raw_records, field_count, col_types)
        return records, string_dict, field_count, col_types

def save_csv(records, string_dict, field_count, column_types, output_path):
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
        writer.writerow([f"Column_{i}" for i in range(field_count)])

        for row in records:
            processed_row = []
            for i, value in enumerate(row):
                col_type = column_types[i]

                if value is None:
                    processed_row.append("")
                    continue

                if col_type == "string":
                    resolved = string_dict.get(value, str(value))
                    processed_row.append(resolved)
                elif col_type == "int":
                    processed_row.append(str(int(value)))
                elif col_type == "float":
                    processed_row.append(str(float(value)))
                else:
                    processed_row.append(str(value))

            writer.writerow(processed_row)
    print(f"File converted and saved as {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python dbc2csv.py input.dbc output.csv\n - Consider using the BASH script for converting many files at once.")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    try:
        records, string_dict, field_count, col_type = read_dbc(input_path)
        save_csv(records, string_dict, field_count, col_type, output_path)
    except Exception as e:
        print(f"Error processing {input_path}: {e}")
        # Try to read header info for debugging
        try:
            with open(input_path, 'rb') as f:
                header = f.read(20)
                magic, record_count, field_count, record_size, string_block_size = struct.unpack('<4s4I', header)
                print(f"Debug info - Magic: {magic}, Records: {record_count}, Fields: {field_count}, Record size: {record_size}, String block: {string_block_size}")
                print(f"Expected record size based on fields: {field_count * 4}")
        except:
            pass
        raise