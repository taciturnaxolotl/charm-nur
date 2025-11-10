#!/usr/bin/env nix-shell
#!nix-shell -i bash -p python3 alejandra

set -euo pipefail

# Get schema URL from argument or default
SCHEMA_URL="${1:-https://charm.land/crush.json}"

# Call the Python script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_FILE=$(mktemp --suffix=.nix)
trap 'rm -f "$TEMP_FILE"' EXIT

python3 "$SCRIPT_DIR/generate-options.py" "$SCHEMA_URL" > "$TEMP_FILE"

# Format with alejandra (it modifies the file in place)
alejandra "$TEMP_FILE" 2>&1 | grep -v "Checking style" | grep -v "Congratulations" | grep -v "Special thanks" | grep -v "^$" || true

# Output the formatted result
cat "$TEMP_FILE"

