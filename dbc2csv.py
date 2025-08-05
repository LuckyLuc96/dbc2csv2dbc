import struct
import sys
import csv
'''
USAGE:
python dbc2csv.py input.dbc output.csv
'''

def read_dbc(file_path):
    with open(file_path, 'rb') as f:
        # Read header
        header = f.read(20)
        magic, record_count, field_count, record_size, string_block_size = struct.unpack('<4s4I', header)

        if magic != b'WDBC':
            raise ValueError("Not a valid DBC file")

        records_data = f.read(record_count * record_size)
        string_block = f.read(string_block_size)

        # First pass: read all records as raw bytes
        raw_records = []
        for i in range(record_count):
            offset = i * record_size
            record_bytes = records_data[offset:offset + record_size]
            raw_records.append(record_bytes)

        def get_all_strings():
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

        string_dict = get_all_strings()

        # Determine field types by analyzing the data
        col_type = []
        records = []

        print(f"Debug: Analyzing {field_count} fields from {record_count} records")
        for col in range(field_count):
            # Extract raw bytes for this column from all records
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

            # Try as integers first
            int_values = []
            for byte_chunk in col_bytes:
                if len(byte_chunk) == 4:
                    int_val = struct.unpack('<i', byte_chunk)[0]
                    int_values.append(int_val)
                else:
                    int_values.append(0)

            # Check if values look like string offsets
            string_match_count = sum(
                1 for v in int_values if v in string_dict and 0 <= v < string_block_size)

            if string_match_count == len(int_values):
                col_type.append("string")
            else:
                # Try as floats and see if they look more reasonable
                float_values = []
                for byte_chunk in col_bytes:
                    float_val = struct.unpack('<f', byte_chunk)[0]
                    float_values.append(float_val)

                # Better heuristic: check if values make sense as floats vs integers
                # Count invalid floats (NaN, inf, very large exponents)
                invalid_floats = sum(1 for v in float_values if v != v or abs(v) == float('inf') or (v != 0 and (abs(v) < 1e-30 or abs(v) > 1e30)))

                # Count reasonable integers (not suspiciously large bit patterns)
                reasonable_ints = sum(1 for v in int_values if abs(v) < 100000000)  # less than 100 million

                # Prefer integers unless we have strong evidence for floats
                # Only use float if: few invalid floats AND most integers look like random bit patterns
                if (invalid_floats < len(float_values) * 0.1 and
                    reasonable_ints < len(int_values) * 0.3 and
                    len(int_values) > 0):
                    col_type.append("float")
                    print(f"Debug: Column {col} detected as FLOAT (invalid_floats: {invalid_floats}/{len(float_values)}, reasonable_ints: {reasonable_ints}/{len(int_values)})")
                    if len(int_values) > 0:
                        print(f"  Sample int values: {int_values[:5]}")
                        print(f"  Sample float values: {float_values[:5]}")
                else:
                    col_type.append("int")
                    if invalid_floats > len(float_values) * 0.5:
                        print(f"Debug: Column {col} detected as INT (many invalid floats: {invalid_floats}/{len(float_values)})")
                        if len(int_values) > 0:
                            print(f"  Sample int values: {int_values[:5]}")
                            print(f"  Sample float values: {float_values[:5]}")

        # Now parse records using determined types
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
                    if col_type[col] == "float":
                        value = struct.unpack('<f', byte_chunk)[0]
                    else:
                        value = struct.unpack('<i', byte_chunk)[0]
                else:
                    value = 0
                record.append(value)
            records.append(record)

        return records, string_dict, field_count, col_type

def save_csv(records, string_dict, field_count, column_types, output_path):
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
        writer.writerow([f"Column_{i}" for i in range(field_count)])

        for row in records:
            processed_row = []
            for i, value in enumerate(row):
                col_type = column_types[i]
                if col_type == "string":
                    processed_row.append(string_dict.get(value, ""))
                elif col_type == "empty":
                    processed_row.append("")
                elif col_type == "float":
                    processed_row.append(str(value))
                else:
                    processed_row.append(str(value))
            writer.writerow(processed_row)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python dbc2csv.py input.dbc output.csv\n - Consider using the BASH script for many files at once.")
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