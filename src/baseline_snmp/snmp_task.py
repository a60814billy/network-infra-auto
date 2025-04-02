import os
import re
import ipaddress
from typing import Optional

from jinja2 import Template
from nornir.core.task import Task, Result
from nornir_netmiko import CONNECTION_NAME as NETMIKO_CONNECTION_NAME

template_dir_path = os.path.join(os.path.dirname(__file__), "templates/")

template_path = {
    "ios": "ios_snmp_config.j2",
    "nxos_ssh": "nxos_snmp_config.j2",
    "iosxr": "iosxr_snmp_config.j2",
}

# snmp_config_template = Template(template_content)


def get_snmp_vars_from_host(host) -> dict:
    snmp_vars = host.get("baseline_snmp", {})
    if "snmp_access_list" in snmp_vars:
        snmp_vars["_snmp_acl_allow_networks"] = []

        for access_list in snmp_vars["snmp_access_list"]:
            ip = ipaddress.ip_network(access_list)
            snmp_vars["_snmp_acl_allow_networks"].append(
                {"network": str(ip.network_address), "wildcard": str(ip.hostmask)}
            )
    return snmp_vars


def filter_hosts(host):
    return "baseline_snmp" in host.keys()


def generate_snmp_config(platform: str, snmp_vars: dict) -> list[str]:
    if platform not in template_path:
        raise ValueError(f"Unsupported platform: {platform}")

    template_file = template_path[platform]
    template_full_path = os.path.join(template_dir_path, template_file)

    try:
        with open(template_full_path, "r") as f:
            template_content = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Template file not found: {template_full_path}")

    snmp_config_template = Template(template_content)

    # Render the configuration using Jinja2
    rendered_config = snmp_config_template.render(**snmp_vars).splitlines()

    # Filter out comments and empty lines
    commend_regex = re.compile(r"(^\s*!.*)|(^\s*$)")
    filtered_config = [
        line for line in rendered_config if not commend_regex.match(line)
    ]
    return filtered_config


def task(task: Task, dry_run: Optional[bool] = False) -> Result:
    snmp_vars = get_snmp_vars_from_host(task.host)

    netmiko_con = task.host.get_connection(NETMIKO_CONNECTION_NAME, task.nornir.config)
    if not netmiko_con:
        return Result(
            host=task.host,
            result="Failed to get Netmiko connection",
            changed=False,
        )

    platform = task.host.platform
    try:
        filtered_config = generate_snmp_config(platform, snmp_vars)
    except (ValueError, FileNotFoundError) as e:
        return Result(
            host=task.host,
            result=f"Failed to generate config: {e}",
            changed=False,
        )

    if task.is_dry_run(dry_run):
        return Result(
            host=task.host,
            result="Dry run mode, no changes applied",
            diff="\n".join(filtered_config),
            changed=False,
        )

    result = netmiko_con.send_config_set(filtered_config)
    if "iosxr" in platform:
        netmiko_con.commit()
    if ["ios", "nxos_ssh"].__contains__(platform):
        netmiko_con.save_config()

    return Result(
        host=task.host,
        result=result,
        changed=True,
    )
