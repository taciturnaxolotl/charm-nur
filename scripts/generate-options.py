#!/usr/bin/env python3

import json
import sys
import urllib.request

# Get schema URL from argument or default
schema_url = sys.argv[1] if len(sys.argv) > 1 else "https://charm.land/crush.json"

try:
    with urllib.request.urlopen(schema_url, timeout=10) as response:
        schema = json.loads(response.read().decode())
except Exception as e:
    print(f"Error fetching schema: {e}", file=sys.stderr)
    sys.exit(1)


def nix_type(json_type):
    """Convert JSON schema type to Nix type."""
    if json_type == "string":
        return "lib.types.str"
    elif json_type == "number":
        return "lib.types.number"
    elif json_type == "integer":
        return "lib.types.int"
    elif json_type == "boolean":
        return "lib.types.bool"
    elif json_type == "array":
        return "lib.types.listOf lib.types.str"
    elif json_type == "object":
        return "lib.types.attrsOf lib.types.anything"
    else:
        return "lib.types.anything"


def nix_default(value):
    """Convert a default value to Nix syntax."""
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    elif isinstance(value, list):
        return "[]"
    elif isinstance(value, dict):
        return "{}"
    else:
        return str(value)


def escape_description(desc):
    """Escape description for Nix."""
    if not desc:
        return ""
    return desc.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def resolve_ref(ref):
    """Resolve $ref to actual schema."""
    if not ref.startswith("#/$defs/"):
        return {}
    def_name = ref.split("/")[-1]
    return schema.get("$defs", {}).get(def_name, {})


def is_valid_nix_identifier(name):
    """Check if name is a valid Nix identifier."""
    if not name:
        return False
    if name[0].isdigit() or name[0] in ("$",):
        return False
    return all(c.isalnum() or c in ("_", "-") for c in name)


def generate_options(properties, indent="      "):
    """Generate Nix option declarations from schema properties."""
    if not properties:
        return ""

    lines = []
    for name, schema_prop in properties.items():
        # Skip invalid Nix identifiers like $schema
        if not is_valid_nix_identifier(name):
            continue

        # Resolve $ref if present
        if "$ref" in schema_prop:
            schema_prop = resolve_ref(schema_prop["$ref"])

        desc = schema_prop.get("description", "")
        default = schema_prop.get("default")
        json_type = schema_prop.get("type", "string")

        # Handle enums
        if "enum" in schema_prop and schema_prop["enum"]:
            lines.append(f"{indent}{name} = lib.mkOption {{")
            lines.append(f"{indent}  type = lib.types.enum [")
            for val in schema_prop["enum"]:
                lines.append(f'{indent}    "{val}"')
            lines.append(f"{indent}  ];")
            if default is not None:
                lines.append(f'{indent}  default = "{default}";')
            if desc:
                lines.append(f'{indent}  description = "{escape_description(desc)}";')
            lines.append(f"{indent}}};")

        # Handle nested objects with properties
        elif json_type == "object" and "properties" in schema_prop:
            lines.append(f"{indent}{name} = lib.mkOption {{")
            lines.append(f"{indent}  type = lib.types.submodule {{")
            lines.append(f"{indent}    options = {{")
            lines.append(generate_options(schema_prop["properties"], indent + "      "))
            lines.append(f"{indent}    }};")
            lines.append(f"{indent}  }};")
            if default is not None:
                lines.append(f"{indent}  default = {{}};")
            if desc:
                lines.append(f'{indent}  description = "{escape_description(desc)}";')
            lines.append(f"{indent}}};")

        # Handle arrays of objects
        elif json_type == "array" and "items" in schema_prop:
            items = schema_prop["items"]
            if "$ref" in items:
                items = resolve_ref(items["$ref"])

            if (
                isinstance(items, dict)
                and items.get("type") == "object"
                and "properties" in items
            ):
                lines.append(f"{indent}{name} = lib.mkOption {{")
                lines.append(
                    f"{indent}  type = lib.types.listOf (lib.types.submodule {{"
                )
                lines.append(f"{indent}    options = {{")
                lines.append(generate_options(items["properties"], indent + "      "))
                lines.append(f"{indent}    }};")
                lines.append(f"{indent}  }});")
                if default is not None:
                    lines.append(f"{indent}  default = [];")
                if desc:
                    lines.append(
                        f'{indent}  description = "{escape_description(desc)}";'
                    )
                lines.append(f"{indent}}};")
            else:
                # Simple array
                lines.append(f"{indent}{name} = lib.mkOption {{")
                lines.append(f"{indent}  type = lib.types.listOf lib.types.str;")
                if default is not None:
                    lines.append(f"{indent}  default = [];")
                if desc:
                    lines.append(
                        f'{indent}  description = "{escape_description(desc)}";'
                    )
                lines.append(f"{indent}}};")

        # Handle additionalProperties (attrs of objects)
        elif json_type == "object" and "additionalProperties" in schema_prop:
            additional_props = schema_prop["additionalProperties"]
            if "$ref" in additional_props:
                additional_props = resolve_ref(additional_props["$ref"])

            if (
                isinstance(additional_props, dict)
                and additional_props.get("type") == "object"
            ):
                if "properties" in additional_props:
                    lines.append(f"{indent}{name} = lib.mkOption {{")
                    lines.append(
                        f"{indent}  type = lib.types.attrsOf (lib.types.submodule {{"
                    )
                    lines.append(f"{indent}    options = {{")
                    lines.append(
                        generate_options(
                            additional_props["properties"], indent + "      "
                        )
                    )
                    lines.append(f"{indent}    }};")
                    lines.append(f"{indent}  }});")
                    if default is not None:
                        lines.append(f"{indent}  default = {{}};")
                    if desc:
                        lines.append(
                            f'{indent}  description = "{escape_description(desc)}";'
                        )
                    lines.append(f"{indent}}};")
                else:
                    # Simple attrsOf
                    lines.append(f"{indent}{name} = lib.mkOption {{")
                    lines.append(
                        f"{indent}  type = lib.types.attrsOf lib.types.anything;"
                    )
                    if default is not None:
                        lines.append(f"{indent}  default = {{}};")
                    if desc:
                        lines.append(
                            f'{indent}  description = "{escape_description(desc)}";'
                        )
                    lines.append(f"{indent}}};")
            else:
                # Simple attrsOf
                lines.append(f"{indent}{name} = lib.mkOption {{")
                lines.append(f"{indent}  type = lib.types.attrsOf lib.types.anything;")
                if default is not None:
                    lines.append(f"{indent}  default = {{}};")
                if desc:
                    lines.append(
                        f'{indent}  description = "{escape_description(desc)}";'
                    )
                lines.append(f"{indent}}};")

        # Simple types
        else:
            lines.append(f"{indent}{name} = lib.mkOption {{")
            lines.append(f"{indent}  type = {nix_type(json_type)};")
            if default is not None:
                lines.append(f"{indent}  default = {nix_default(default)};")
            if desc:
                lines.append(f'{indent}  description = "{escape_description(desc)}";')
            lines.append(f"{indent}}};")

    return "\n".join(lines)


# Generate the Nix module
output = []
output.append("{lib}:")
output.append("lib.mkOption {")
output.append("  type = lib.types.submodule {")
output.append("    options = {")

# Get the root Config definition
if "$ref" in schema:
    root_def = resolve_ref(schema["$ref"])
else:
    root_def = schema

if "properties" in root_def:
    output.append(generate_options(root_def["properties"], "      "))

output.append("    };")
output.append("  };")
output.append("  default = {};")
output.append("}")

print("\n".join(output))
