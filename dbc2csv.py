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

        print(f"Records: {record_count}, Fields: {field_count}, Record size: {record_size}, String block size: {string_block_size}")

        records_data = f.read(record_count * record_size)
        string_block = f.read(string_block_size)

        records = []
        for i in range(record_count):
            offset = i * record_size
            record = list(struct.unpack('<' + 'I' * field_count,
                                     records_data[offset:offset + record_size]))
            records.append(record)

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
        print(f"Found {len(string_dict)} strings in string block")

        return records, string_dict, field_count

def save_csv(records, string_dict, field_count, output_path, convert_numbers=True):
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        writer.writerow([f"Column_{i}" for i in range(field_count)])

        for row in records:
            processed_row = []
            for value in row:
                if value in string_dict:
                    processed_row.append(string_dict[value])
                else:
                    str_val = str(value)
                    processed_row.append(str_val)
            writer.writerow(processed_row)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python dbc2csv.py input.dbc output.csv")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    records, string_dict, field_count = read_dbc(input_path)
    save_csv(records, string_dict, field_count, output_path)