# DBC/CSV Conversion Tools

## Overview

This repository contains tools for converting between DBC (Blizzard Data Binary Container) and CSV (Comma-Separated Values) file formats. The package includes:

1. `dbc2csv.py` - Converts DBC files to CSV format
2. `csv2dbc.py` - Converts CSV files back to DBC format
3. `convertfolder.sh` - Bash script for bulk conversion of multiple files

## Requirements

- Python 3
- Bash (for bulk operations)

## Installation

1. Clone or download this repository
2. Ensure all files (`dbc2csv.py`, `csv2dbc.py`, and `convertfolder.sh`) are in the same directory
3. Make the bash script executable:
   ```bash
   chmod +x convertfolder.sh
   ```

## Individual File Conversion

### Convert DBC to CSV

# python3 dbc2csv.py input.dbc output.csv

### Convert CSV back to DBC

# python3 csv2dbc.py input.csv original.dbc output.dbc

Note: The original DBC file is required to maintain the proper file structure.

## Bulk Conversion

### Convert all DBC files in a directory to CSV

# bash convertfolder.sh export path/to/dbc_files

- Creates a new folder named `[original_folder]_csv` with all converted CSV files
- Preserves original filenames (e.g., `spells.dbc` → `spells.csv`)

### Convert all CSV files back to DBC
# bash convertfolder.sh import path/to/csv_files

- Creates a new folder named `[original_folder]_dbc` with converted DBC files
- Requires original DBC files to be in the folder without `_csv` suffix
- Preserves all original DBC header information

### Conversion Process
1. **DBC to CSV**:
   - Extracts all records and converts them to CSV format
   - Resolves string references from the string block
   - Preserves numeric values when possible

2. **CSV to DBC**:
   - Uses the original DBC as a template for header structure
   - Rebuilds the string block from CSV string values
   - Maintains proper offsets and record alignment

## Notes

- The bulk conversion script will skip files if matching originals aren't found during import
- Numeric values are preserved when converting back to DBC
- Empty strings are properly handled in both directions
- The tools maintain all original DBC structure requirements

## License

GNU General Public License v3.0