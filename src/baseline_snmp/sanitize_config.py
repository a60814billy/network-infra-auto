import re  # Added import


def sanitize_ios_config(lines):
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
    in_call_home_block = False  # Flag for call-home block

    # Define start patterns
    gi1_interface_start = "interface GigabitEthernet1"
    call_home_start = "call-home"  # Added call-home start pattern
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

        # Check for call-home block end
        if in_call_home_block:
            if stripped_line == "!":
                in_call_home_block = False
                i += 1  # Skip the '!' line
                continue
            else:
                i += 1  # Skip line inside call-home block
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

        # Check for call-home start
        if stripped_line.startswith(call_home_start):
            in_call_home_block = True
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

        # Add check for the specific ip route line
        if stripped_line.startswith("ip route vrf Mgmt-intf 0.0.0.0 0.0.0.0"):
            i += 1  # Skip this specific route line
            continue

        # If none of the above matched, keep the original line (with its whitespace/ending)
        sanitized_lines.append(original_line)
        i += 1

    return sanitized_lines


def sanitize_nxos_config(lines):
    """
    Parses NX-OS configuration lines and removes specific sensitive/unwanted information.

    Args:
        lines (list): A list of strings, where each string is a line from the config file.

    Returns:
        list: A list of strings representing the sanitized configuration.
    """
    sanitized_lines = []
    in_vrf_management = False
    in_interface_mgmt0 = False
    in_class_map_block = False  # Flag for class-map blocks
    in_policy_map_block = False  # Flag for policy-map blocks
    in_vdc_block = False  # Flag for vdc blocks
    in_role_block = False  # Flag for role blocks
    in_copp_block = False  # Flag for copp blocks

    # Define start patterns
    vrf_management_start = "vrf context management"
    interface_mgmt0_start = "interface mgmt0"
    class_map_start_pattern = "class-map type "  # Pattern for class-map start
    policy_map_start_pattern = "policy-map type "  # Pattern for policy-map start
    vdc_start_pattern = "vdc "  # Pattern for vdc start
    role_start_pattern = "role name "  # Pattern for role start
    copp_start_pattern = "copp profile "  # Pattern for copp start

    # Define single lines/prefixes to remove
    username_admin_pattern = "username admin "
    boot_nxos_pattern = "boot nxos"  # Pattern for boot nxos lines

    i = 0
    while i < len(lines):
        original_line = lines[i]
        # Preserve original line endings, but strip leading/trailing whitespace for matching
        stripped_line = original_line.strip()
        # Check if the original line has leading whitespace (indicating indentation)
        leading_whitespace = len(original_line) > len(original_line.lstrip(" \t"))

        # --- Block Handling: Check for End Markers FIRST ---

        if stripped_line.startswith("!"):
            i += 1
            continue

        if re.compile(r"^\s*version\s.*").match(original_line):
            i += 1
            continue

        if re.compile(r"^\s*hostname\s.*").match(original_line):
            i += 1
            continue

        if in_vrf_management:
            # NX-OS blocks typically end when indentation stops.
            # Also check if the line is empty or just '!' which can sometimes delimit sections.
            if not leading_whitespace or stripped_line == "!":
                in_vrf_management = False
                # Don't skip this line yet, let it be evaluated by the rules below
            else:
                i += 1  # Skip line inside the block
                continue

        if in_interface_mgmt0:
            # NX-OS blocks typically end when indentation stops.
            # Also check if the line is empty or just '!' which can sometimes delimit sections.
            if not leading_whitespace or stripped_line == "!":
                in_interface_mgmt0 = False
                # Don't skip this line yet, let it be evaluated by the rules below
            else:
                i += 1  # Skip line inside the block
                continue

        if in_class_map_block:
            # NX-OS blocks typically end when indentation stops.
            if not leading_whitespace or stripped_line == "!":
                in_class_map_block = False
                # Don't skip this line yet, let it be evaluated by the rules below
            else:
                i += 1  # Skip line inside the block
                continue

        if in_policy_map_block:
            # NX-OS blocks typically end when indentation stops.
            if not leading_whitespace or stripped_line == "!":
                in_policy_map_block = False
                # Don't skip this line yet, let it be evaluated by the rules below
            else:
                i += 1  # Skip line inside the block
                continue

        if in_vdc_block:
            # NX-OS blocks typically end when indentation stops.
            if not leading_whitespace or stripped_line == "!":
                in_vdc_block = False
                # Don't skip this line yet, let it be evaluated by the rules below
            else:
                i += 1  # Skip line inside the block
                continue

        if in_role_block:
            # NX-OS blocks typically end when indentation stops.
            if not leading_whitespace or stripped_line == "!":
                in_role_block = False
                # Don't skip this line yet, let it be evaluated by the rules below
            else:
                i += 1  # Skip line inside the block
                continue

        if in_copp_block:
            # NX-OS blocks typically end when indentation stops.
            if not leading_whitespace or stripped_line == "!":
                in_copp_block = False
                # Don't skip this line yet, let it be evaluated by the rules below
            else:
                i += 1  # Skip line inside the block
                continue

        # --- Start Markers & Single Line Removals ---

        # Check for vrf context management start
        if stripped_line.startswith(vrf_management_start):
            in_vrf_management = True
            i += 1  # Skip the start line
            continue

        # Check for interface mgmt0 start
        if stripped_line.startswith(interface_mgmt0_start):
            in_interface_mgmt0 = True
            i += 1  # Skip the start line
            continue

        # Check for class-map start
        if stripped_line.startswith(class_map_start_pattern):
            in_class_map_block = True
            i += 1  # Skip the start line
            continue

        # Check for policy-map start
        if stripped_line.startswith(policy_map_start_pattern):
            in_policy_map_block = True
            i += 1  # Skip the start line
            continue

        # Check for vdc start
        if stripped_line.startswith(vdc_start_pattern):
            in_vdc_block = True
            i += 1  # Skip the start line
            continue

        # Check for role start
        if stripped_line.startswith(role_start_pattern):
            in_role_block = True
            i += 1  # Skip the start line
            continue

        # Check for copp start
        if stripped_line.startswith(copp_start_pattern):
            in_copp_block = True
            i += 1  # Skip the start line
            continue

        # Check for boot nxos line
        if stripped_line.startswith(boot_nxos_pattern):
            i += 1  # Skip boot nxos line
            continue

        # Check for username admin line
        if stripped_line.startswith(username_admin_pattern):
            i += 1  # Skip username admin line
            continue

        # If none of the above matched, keep the original line
        sanitized_lines.append(original_line)
        i += 1

    return sanitized_lines


if __name__ == "__main__":
    with open("cfg/tndo-n9k-1.cfg", "r") as f:
        lines = f.readlines()

    results = sanitize_nxos_config(lines)

    with open("cfg/tndo-n9k-1-sanitized.cfg", "w") as f:
        for line in results:
            f.write(line)
    print("Sanitization complete. Check the output file.")
