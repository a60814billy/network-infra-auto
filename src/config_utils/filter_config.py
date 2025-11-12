import re
from typing import List
import ipaddress


def filter_config(
    platform: str, config_lines: List[str], testbed_data: dict
) -> List[str]:
    """
    Filter configuration lines to remove specific commands/blocks based on platform.

    Args:
        platform: Platform identifier ('nxos', 'hpe', 'comware', etc.)
        config_lines: List of configuration lines

    Returns:
        Filtered list of configuration lines
    """
    if platform in ["nxos", "nxos_ssh"]:
        return replace_nxos_config_to_testbed(config_lines, testbed_data)
    elif platform in ["hpe", "comware"]:
        return filter_hpe_config(config_lines)
    else:
        raise ValueError(f"Unsupported platform: {platform}")


def combine_ip_subnetmask(ip: str, netmask: str) -> str:
    """
    "Combine IP address and subnet mask into CIDR notation.

    Args:
        ip: IP address as string
        netmask: Subnet mask as string
    Returns:
        CIDR notation string

    Example:
        combine_ip_subnetmask("192.168.1.1", "255.255.255.0")
        returns "192.168.1.1/24"
    """
    try:
        interface = ipaddress.ip_interface(f"{ip}/{netmask}")
        return str(interface.with_prefixlen)
    except ValueError as e:
        print(f"Error: Invalid IP or netmask provided - {e}")
        raise


def replace_nxos_config_to_testbed(
    lines: List[str], testbed_data: dict = {}
) -> List[str]:
    testbed_hostname = testbed_data.get("hostname", "tndo-n9k-2")
    mgmt_ip = testbed_data.get("mgmt_ip", "10.192.4.184")
    netmask = testbed_data.get("netmask", "255.255.255.0")
    default_gateway = testbed_data.get("default_gateway", "10.192.4.1")

    mgmt_ip = combine_ip_subnetmask(mgmt_ip, netmask)

    filtered_lines = []
    in_block = False
    block_indent = -1
    skip_block_type = None

    i = 0
    while i < len(lines):
        original_line = lines[i]
        stripped_line = original_line.strip()
        leading_whitespace = len(original_line) - len(original_line.lstrip(" \t"))

        # Check if we're currently in a block to skip
        if in_block:
            # Block ends when indentation returns to original level or less
            if leading_whitespace <= block_indent:
                in_block = False
                skip_block_type = None
                block_indent = -1
                # Don't skip this line, re-evaluate it
            else:
                i += 1
                continue

        # Filter hostname
        if re.match(r"^hostname\s+", stripped_line):
            # Replace with testbed hostname
            filtered_lines.append(f"hostname {testbed_hostname}")
            i += 1
            continue

        # Filter tacacs-server commands
        if stripped_line.startswith("tacacs-server"):
            i += 1
            continue

        # Filter ip access-list blocks
        if re.match(r"^ip access-list\s+", stripped_line):
            in_block = True
            block_indent = leading_whitespace
            skip_block_type = "acl"
            i += 1
            continue

        # Filter aaa group server tacacs+ blocks
        if re.match(r"^aaa group server tacacs\+", stripped_line):
            in_block = True
            block_indent = leading_whitespace
            skip_block_type = "aaa_group"
            i += 1
            continue

        # Filter snmp-server user
        # if stripped_line.startswith("snmp-server user"):
        #     i += 1
        #     continue

        # Filter ip route 0.0.0.0/0
        if re.match(r"^ip route 0\.0\.0\.0/0\s+", stripped_line):
            if lines[i - 1].strip() == "vrt context management":
                # Replace with testbed default route
                filtered_lines.append(
                    f"  ip route 0.0.0.0/0 mgmt0 {default_gateway} 254"
                )
                i += 1
                continue

        if re.match(r"^vdc \S+ id 1", stripped_line):
            # Replace with testbed vdc
            filtered_lines.append(f"vdc {testbed_hostname} id 1")
            i += 1
            continue
        # Filter boot mode lxc
        if stripped_line.startswith("boot mode lxc"):
            i += 1
            continue

        # Filter boot nxos
        if stripped_line.startswith("boot nxos"):
            # add back testbed boot nxos line
            filtered_lines.append("boot nxos bootflash:/nxos.9.3.13.bin")
            i += 1
            continue

        # Filter interface mgmt0 block
        if stripped_line.startswith("interface mgmt0"):
            in_block = True
            block_indent = leading_whitespace
            skip_block_type = "interface_mgmt0"
            # Add back testbed mgmt0 configuration
            filtered_lines.append("interface mgmt0")
            filtered_lines.append("  vrf member management")
            filtered_lines.append(f"  ip address {mgmt_ip}")
            i += 1
            continue

        # Keep this line
        filtered_lines.append(original_line)
        i += 1

    return filtered_lines


def filter_nxos_config(lines: List[str]) -> List[str]:
    """
    Filter NX-OS configuration to exclude:
    - hostname
    - tacacs-server (all lines)
    - acl/ip access-list blocks
    - snmp-server user
    - ip route 0.0.0.0/0
    - boot mode lxc
    - boot nxos
    - interface mgmt0 block

    Args:
        lines: List of configuration lines

    Returns:
        Filtered configuration lines
    """
    filtered_lines = []
    in_block = False
    block_indent = -1
    skip_block_type = None

    i = 0
    while i < len(lines):
        original_line = lines[i]
        stripped_line = original_line.strip()
        leading_whitespace = len(original_line) - len(original_line.lstrip(" \t"))

        # Skip empty lines and comments
        if not stripped_line or stripped_line.startswith("!"):
            i += 1
            continue

        # Check if we're currently in a block to skip
        if in_block:
            # Block ends when indentation returns to original level or less
            if leading_whitespace <= block_indent and stripped_line:
                in_block = False
                skip_block_type = None
                block_indent = -1
                # Don't skip this line, re-evaluate it
            else:
                i += 1
                continue

        # Filter hostname
        if re.match(r"^hostname\s+", stripped_line):
            i += 1
            continue

        # Filter tacacs-server commands
        if stripped_line.startswith("tacacs-server"):
            i += 1
            continue

        # Filter ip access-list blocks
        if re.match(r"^ip access-list\s+", stripped_line):
            in_block = True
            block_indent = leading_whitespace
            skip_block_type = "acl"
            i += 1
            continue

        # Filter aaa group server tacacs+ blocks
        if re.match(r"^aaa group server tacacs\+", stripped_line):
            in_block = True
            block_indent = leading_whitespace
            skip_block_type = "aaa_group"
            i += 1
            continue

        # Filter snmp-server user
        # if stripped_line.startswith("snmp-server user"):
        #     i += 1
        #     continue

        # Filter ip route 0.0.0.0/0
        if re.match(r"^ip route 0\.0\.0\.0/0\s+", stripped_line):
            i += 1
            continue

        # Filter boot mode lxc
        if stripped_line.startswith("boot mode lxc"):
            i += 1
            continue

        # Filter boot nxos
        if stripped_line.startswith("boot nxos"):
            i += 1
            continue

        # Filter interface mgmt0 block
        if stripped_line.startswith("interface mgmt0"):
            in_block = True
            block_indent = leading_whitespace
            skip_block_type = "interface_mgmt0"
            i += 1
            continue

        # Keep this line
        filtered_lines.append(original_line)
        i += 1

    return filtered_lines


def filter_hpe_config(lines: List[str]) -> List[str]:
    """
    Filter HPE Comware configuration to exclude:
    - sysname
    - line vty 0 63 block (continues until next # or next top-level command)
    - ip route-static 0.0.0.0 0
    - ssh server
    - local-user blocks (with password hash)

    Args:
        lines: List of configuration lines

    Returns:
        Filtered configuration lines

    Note:
        HPE Comware configs use '#' as section delimiters.
        Blocks like 'line vty 0 63' are NOT indented - they continue
        until the next '#' comment line.
    """
    filtered_lines = []
    skip_until_hash = False
    skip_block_type = None

    # Top-level commands that start new sections (not part of previous block)
    top_level_patterns = [
        r"^interface\s+",
        r"^vlan\s+",
        r"^acl\s+",
        r"^ip\s+",
        r"^router\s+",
        r"^line\s+",
        r"^local-user\s+",
        r"^ssh\s+",
        r"^telnet\s+",
        r"^sysname\s+",
        r"^return$",
        r"^quit$",
    ]

    i = 0
    while i < len(lines):
        original_line = lines[i]
        stripped_line = original_line.strip()

        # Empty lines are always skipped
        if not stripped_line:
            i += 1
            continue

        # '#' terminates any block we're skipping
        if stripped_line.startswith("#"):
            if skip_until_hash:
                skip_until_hash = False
                skip_block_type = None
            i += 1
            continue

        # If we're skipping a block, check if we hit a top-level command
        if skip_until_hash:
            # Check if this is a new top-level command
            is_top_level = any(
                re.match(pattern, stripped_line) for pattern in top_level_patterns
            )
            if is_top_level:
                # End the skip block
                skip_until_hash = False
                skip_block_type = None
                # Re-evaluate this line
            else:
                # Still in the block, skip it
                i += 1
                continue

        # Filter sysname
        if re.match(r"^sysname\s+", stripped_line):
            i += 1
            continue

        # Filter line vty 0 63 block (until next #)
        if re.match(r"^line vty 0 63", stripped_line):
            skip_until_hash = True
            skip_block_type = "line_vty"
            i += 1
            continue

        # Filter ip route-static 0.0.0.0 0
        if re.match(r"^ip route-static 0\.0\.0\.0 0\s+", stripped_line):
            i += 1
            continue

        # Filter ssh server commands
        if re.match(r"^ssh server", stripped_line):
            i += 1
            continue

        # Filter local-user blocks (until next #)
        if re.match(r"^local-user\s+\S+\s+class\s+manage", stripped_line):
            skip_until_hash = True
            skip_block_type = "local_user"
            i += 1
            continue

        # Keep this line
        filtered_lines.append(original_line)
        i += 1

    return filtered_lines
