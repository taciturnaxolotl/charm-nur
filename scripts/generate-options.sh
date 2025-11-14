#!/usr/bin/env nix-shell
#!nix-shell -i bash -p python3 alejandra

set -euo pipefail

# Get the version from the crush package
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION=$(grep -oP 'version = "\K[^"]+' "$SCRIPT_DIR/../pkgs/crush/default.nix" | head -1)

# Build schema URL from version
SCHEMA_URL="${1:-https://raw.githubusercontent.com/charmbracelet/crush/refs/tags/v${VERSION}/schema.json}"

# Call the Python script
TEMP_FILE=$(mktemp --suffix=.nix)
trap 'rm -f "$TEMP_FILE"' EXIT

python3 "$SCRIPT_DIR/generate-options.py" "$SCHEMA_URL" > "$TEMP_FILE"

# Format with alejandra (it modifies the file in place)
alejandra "$TEMP_FILE" 2>&1 | grep -v "Checking style" | grep -v "Congratulations" | grep -v "Special thanks" | grep -v "^$" || true

# Output the formatted result
cat "$TEMP_FILE"

