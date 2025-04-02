from ..snmp_task import generate_snmp_config, get_snmp_vars_from_host

host = {
    "baseline_snmp": {
        "location": "DC1",
        "contact": "netadmin@example.com",
        "v2c": {"ro_community": "public", "rw_community": "private"},
        "snmp_access_list": ["10.0.0.0/24", "192.168.0.0/16"],
    }
}


def test_generate_ios_snmp_config():
    expected_config = """
no snmp-server
no ip access-list standard snmp_acl
snmp-server location DC1
snmp-server contact netadmin@example.com
ip access-list standard snmp_acl
  permit 10.0.0.0 0.0.0.255
  permit 192.168.0.0 0.0.255.255
snmp-server community public ro snmp_acl
snmp-server community private rw snmp_acl
"""
    vars = get_snmp_vars_from_host(host)
    config = generate_snmp_config("ios", vars)
    assert "\n".join(config) == expected_config.strip()


def test_generate_nxos_snmp_config():
    expected_config = """
snmp-server location DC1
snmp-server contact netadmin@example.com
no ip access-list snmp_acl
ip access-list snmp_acl
  permit ip 10.0.0.0/24 any
  permit ip 192.168.0.0/16 any
snmp-server community public ro
snmp-server community public use-ipv4acl snmp_acl
snmp-server community private rw
snmp-server community private use-ipv4acl snmp_acl
"""
    vars = get_snmp_vars_from_host(host)
    config = generate_snmp_config("nxos_ssh", vars)
    assert "\n".join(config) == expected_config.strip()


def test_generate_ioxr_snmp_config():
    expected_config = """
snmp-server location DC1
snmp-server contact netadmin@example.com
no ip access-list snmp_acl
ip access-list snmp_acl
  permit 10.0.0.0/24
  permit 192.168.0.0/16
snmp-server community public RO Ipv4 snmp_acl
snmp-server community private RW Ipv4 snmp_acl
"""
    vars = get_snmp_vars_from_host(host)
    config = generate_snmp_config("iosxr", vars)
    assert "\n".join(config) == expected_config.strip()
