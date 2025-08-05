#!/bin/bash

# DBC Tools - Bulk Converter
# Usage: bash massconvert.sh [mode] [input_directory]
# Modes:
#   - 'export' (dbc to csv)
#   - 'import' (csv to dbc)
#   - On `import` you will want to use the name of the folder that you created for the exported CSV files.
#    Example usage:
#    bash massconvert.sh export dbcs
#    bash massconvert.sh import dbcs_csv

if [ $# -ne 2 ]; then
    echo "Usage: $0 [export|import] [input_directory]"
    exit 1
fi

MODE=$1
INPUT_DIR=$(realpath "$2")
SCRIPT_DIR=$(dirname "$(realpath "$0")")

# Python scripts must be in same directory
DBC2CSV="$SCRIPT_DIR/dbc2csv.py"
CSV2DBC="$SCRIPT_DIR/csv2dbc.py"

if [ ! -f "$DBC2CSV" ] || [ ! -f "$CSV2DBC" ]; then
    echo "Error: Python converters not found in $SCRIPT_DIR"
    exit 1
fi

case $MODE in
    export)
        OUTPUT_DIR="${INPUT_DIR}_csv"
        mkdir -p "$OUTPUT_DIR"

        echo "Converting DBC to CSV..."
        find "$INPUT_DIR" -type f -name '*.dbc' | while read -r dbc_file; do
            filename=$(basename "$dbc_file" .dbc)
            csv_file="$OUTPUT_DIR/${filename}.csv"
            echo "Converting $dbc_file → $csv_file"
            python3 "$DBC2CSV" "$dbc_file" "$csv_file"
        done
        echo "Conversion complete! CSV files saved to $OUTPUT_DIR"
        ;;

    import)
        OUTPUT_DIR="${INPUT_DIR}_dbc"
        mkdir -p "$OUTPUT_DIR"

        echo "Converting CSV to DBC..."
        find "$INPUT_DIR" -type f -name '*.csv' | while read -r csv_file; do
            filename=$(basename "$csv_file" .csv)
            original_dbc="${INPUT_DIR%_csv}/$filename.dbc"
            output_dbc="$OUTPUT_DIR/${filename}.dbc"

            if [ ! -f "$original_dbc" ]; then
                echo "Warning: Original $original_dbc not found, skipping $csv_file"
                continue
            fi

            echo "Converting $csv_file → $output_dbc (using $original_dbc as template)"
            python3 "$CSV2DBC" "$csv_file" "$original_dbc" "$output_dbc"
        done
        echo "Conversion complete! DBC files saved to $OUTPUT_DIR"
        ;;

    *)
        echo "Invalid mode. Use 'export' or 'import'"
        exit 1
        ;;
esac