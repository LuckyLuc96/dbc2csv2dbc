import struct
import csv
import os
'''
USAGE:
python csv2dbc.py modified.csv original.dbc output.dbc
I.E
python csv2dbc.py output.csv dbcs/SkillLineAbility.dbc SkillLineAbility.dbc

The conversion from .dbc to .csv does not transfer the header data.
So the conversion back to .dbc from the .csv actually overwrites the original dbc file and uses those headers
'''


def csv_to_dbc(csv_path, original_dbc, output_dbc):
    with open(original_dbc, 'rb') as f:
        header = f.read(20)
        magic, record_count, field_count, record_size, string_block_size = struct.unpack('<4s4I', header)

        if magic != b'WDBC':
            raise ValueError("Not a valid DBC file")

    # Process CSV data - SKIP HEADER ROW
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header row
        csv_records = list(reader)

        if len(csv_records) != record_count:
            print(f"Warning: Record count mismatch (DBC: {record_count}, CSV: {len(csv_records)})")

    records = []
    string_block_data = bytearray()
    string_offset_map = {0: 0}

    for row in csv_records:
        record = []
        for i, value in enumerate(row[:field_count]):
            try:
                # First try as integer
                int_val = int(value)
                record.append(int_val)
            except ValueError:
                try:
                    # Then try as float
                    float_val = float(value)
                    record.append(float_val)
                except ValueError:
                    if value == "":
                        record.append(0)
                    else:
                        if value not in string_offset_map:
                            offset = len(string_block_data)
                            string_offset_map[value] = offset
                            string_block_data += value.encode('utf-8') + b'\x00'
                        record.append(string_offset_map[value])
        records.append(record)


    with open(output_dbc, 'wb') as f:
        new_string_block_size = len(string_block_data)
        f.write(struct.pack('<4s4I', magic, len(records), field_count, record_size, new_string_block_size))

        for record in records:
            # Pack each value appropriately based on its type
            packed_values = []
            for value in record:
                if isinstance(value, float):
                    packed_values.append(struct.pack('<f', value))
                else:
                    packed_values.append(struct.pack('<i', value))
            f.write(b''.join(packed_values))

        f.write(string_block_data)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: python csv2dbc.py input.csv original.dbc output.dbc")
        print("Converts CSV back to DBC while preserving original header structure")
        sys.exit(1)

    csv_path = sys.argv[1]
    original_dbc = sys.argv[2]
    output_dbc = sys.argv[3]

    if not os.path.exists(csv_path):
        print(f"Error: Input CSV file {csv_path} not found")
        sys.exit(1)

    if not os.path.exists(original_dbc):
        print(f"Error: Original DBC file {original_dbc} not found")
        sys.exit(1)

    print(f"Converting {csv_path} using {original_dbc} as template...")
    csv_to_dbc(csv_path, original_dbc, output_dbc)
    print(f"Successfully created {output_dbc}")