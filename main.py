import struct
import sys
import csv

def read_dbc(file_path):
    with open(file_path, 'rb') as f:
        header = f.read(20)
        magic, record_count, field_count, record_size, string_block_size = struct.unpack('<4s4I', header)

        if magic != b'WDBC':
            raise ValueError("Not a valid DBC file")

        print(f"Records: {record_count}, Fields: {field_count}, Record size: {record_size}, String block size: {string_block_size}")

        records_data = f.read(record_count * record_size)
        string_block = f.read(string_block_size)

        records = []
        for i in range(record_count):
            offset = i * record_size
            record = struct.unpack('<' + 'I' * field_count, records_data[offset:offset + record_size])
            records.append(record)

        # Resolve strings
        def get_string(offset):
            end = string_block.find(b'\x00', offset)
            return string_block[offset:end].decode('utf-8')

        return records, get_string

def save_csv(records, get_string_fn, output_path, use_strings=False):
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        for row in records:
            if use_strings:
                row = [get_string_fn(x) if i == 0 else x for i, x in enumerate(row)]  # only first column is stringref
            writer.writerow(row)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python dbc2csv.py input.dbc output.csv")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    records, get_string = read_dbc(input_path)
    save_csv(records, get_string, output_path, use_strings=True)
