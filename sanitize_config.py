import re  # Added import


def sanitize_config(lines):
    """
    Parses IOS XE configuration lines and removes specific sensitive information.

    Args:
        lines (list): A list of strings, where each string is a line from the config file.

    Returns:
        list: A list of strings representing the sanitized configuration.
    """
    sanitized_lines = []
    in_gi1_interface = False
    in_crypto_cert_block = False  # Flag for crypto pki cert/trustpoint/raw cert blocks

    # Define start patterns
    gi1_interface_start = "interface GigabitEthernet1"
    crypto_cert_start_patterns = [
        "crypto pki certificate chain",
        "crypto pki trustpoint",
        "-----BEGIN CERTIFICATE-----",
    ]
    # Define patterns indicating the end of a crypto block
    crypto_cert_end_patterns = [
        "quit",
        "exit",  # Some blocks might use exit
        "-----END CERTIFICATE-----",
    ]
    # Define single lines/prefixes to remove
    license_pattern = "license "
    enable_secret_pattern = "enable secret "
    username_admin_pattern = "username admin "

    i = 0
    while i < len(lines):
        original_line = lines[i]
        # Preserve original line endings, but strip whitespace for matching
        stripped_line = original_line.strip()

        # --- Block Handling: Check for End Markers FIRST ---

        if in_gi1_interface:
            # Gi1 interface block ends if line is '!' or indentation decreases significantly (e.g., not starting with space)
            # or another interface definition starts.
            if stripped_line == "!" or (
                not original_line.startswith(" ")
                and not original_line.startswith("\t")
                and not stripped_line.startswith("interface ")
                and not stripped_line.startswith(gi1_interface_start)
            ):
                in_gi1_interface = False
                # Don't skip this line yet, let it be evaluated by the rules below
            else:
                i += 1  # Skip line inside Gi1 block
                continue

        if in_crypto_cert_block:
            ended = False
            # Check explicit end patterns
            for pattern in crypto_cert_end_patterns:
                # Use startswith for potentially indented end markers like ' quit'
                if stripped_line.startswith(pattern):
                    in_crypto_cert_block = False
                    ended = True
                    # Skip the end marker line itself (quit, exit, END CERTIFICATE)
                    i += 1
                    break
            if ended:
                continue

            # Check for '!' as a general block ender, common in IOS
            if stripped_line == "!":
                in_crypto_cert_block = False
                # Skip the '!' line as well
                i += 1
                continue

            # If still in block and no end marker found, skip the line
            i += 1
            continue

        # --- Start Markers & Single Line Removals ---

        # Check for Gi1 start
        if stripped_line.startswith(gi1_interface_start):
            in_gi1_interface = True
            i += 1  # Skip the start line
            continue

        # Check for crypto start
        crypto_match = False
        for pattern in crypto_cert_start_patterns:
            if stripped_line.startswith(pattern):
                in_crypto_cert_block = True
                crypto_match = True
                break
        if crypto_match:
            i += 1  # Skip the start line
            continue

        # Check for single lines to remove (using startswith on stripped line)
        if stripped_line.startswith(license_pattern):
            i += 1  # Skip license line
            continue

        if stripped_line.startswith(enable_secret_pattern):
            i += 1  # Skip enable secret line
            continue

        if stripped_line.startswith(username_admin_pattern):
            i += 1  # Skip username admin line
            continue

        # If none of the above matched, keep the original line (with its whitespace/ending)
        sanitized_lines.append(original_line)
        i += 1

    return sanitized_lines


# Example Usage (optional - can be uncommented for testing)
if __name__ == "__main__":
    input_file = "cfg/tndo-c8k-1.cfg"
    output_file = "cfg/tndo-c8k-1_sanitized.cfg"
    try:
        with open(input_file, "r") as f:
            config_lines = f.readlines()  # Read lines with endings preserved
        sanitized_config = sanitize_config(config_lines)
        with open(output_file, "w") as f:
            f.writelines(sanitized_config)  # Write lines with endings preserved
        print(f"Sanitized config written to {output_file}")
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
