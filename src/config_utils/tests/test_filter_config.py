import pytest
from config_utils.filter_config import filter_config, filter_nxos_config, filter_hpe_config


class TestFilterNxosConfig:
    """Test NX-OS configuration filtering"""

    def test_filter_hostname(self):
        """Test that hostname is filtered out"""
        lines = [
            "hostname 08-D93180-2-49-TOR\n",
            "vlan 1\n",
        ]
        result = filter_nxos_config(lines)
        assert "hostname" not in "".join(result)
        assert "vlan 1" in "".join(result)

    def test_filter_tacacs_server(self):
        """Test that all tacacs-server commands are filtered"""
        lines = [
            'tacacs-server key 7 ""\n',
            "tacacs-server deadtime 15\n",
            'tacacs-server host 10.66.164.188 key 7 ""\n',
            "tacacs-server host 10.66.164.189 test username healthcheck idle-time 5\n",
            "vlan 1\n",
        ]
        result = filter_nxos_config(lines)
        assert "tacacs-server" not in "".join(result)
        assert "vlan 1" in "".join(result)

    def test_filter_ip_access_list_block(self):
        """Test that ip access-list blocks are filtered"""
        lines = [
            "ip access-list NETWORK_ADMIN\n",
            "  10 remark TW Admin Zone\n",
            "  630 permit ip 10.22.154.0/24 any\n",
            "  990 permit ip any any\n",
            "vlan 1\n",
        ]
        result = filter_nxos_config(lines)
        assert "ip access-list" not in "".join(result)
        assert "630 permit" not in "".join(result)
        assert "vlan 1" in "".join(result)

    def test_filter_aaa_group_server_tacacs_block(self):
        """Test that aaa group server tacacs+ blocks are filtered"""
        lines = [
            "aaa group server tacacs+ nwadmin\n",
            "    server 10.66.14.188\n",
            "    server 10.66.164.19\n",
            "    source-interface mgmt0\n",
            "vlan 1\n",
        ]
        result = filter_nxos_config(lines)
        assert "aaa group server tacacs+" not in "".join(result)
        assert "server 10.66.14.188" not in "".join(result)
        assert "vlan 1" in "".join(result)

    def test_filter_snmp_server_user(self):
        """Test that snmp-server user commands are filtered"""
        lines = [
            "snmp-server user admin network-admin auth md5 7214da239 priv des a239 localizedkey\n",
            "snmp-server host 10.11.34.100 traps version 2c puc\n",
            "vlan 1\n",
        ]
        result = filter_nxos_config(lines)
        assert "snmp-server user" not in "".join(result)
        # snmp-server host should be kept
        assert "snmp-server host" in "".join(result)
        assert "vlan 1" in "".join(result)

    def test_filter_ip_route_default(self):
        """Test that default route is filtered"""
        lines = [
            "ip route 0.0.0.0/0 10.49.2.1\n",
            "vlan 1\n",
        ]
        result = filter_nxos_config(lines)
        assert "ip route 0.0.0.0/0" not in "".join(result)
        assert "vlan 1" in "".join(result)

    def test_filter_boot_mode_lxc(self):
        """Test that boot mode lxc is filtered"""
        lines = [
            "boot mode lxc\n",
            "vlan 1\n",
        ]
        result = filter_nxos_config(lines)
        assert "boot mode lxc" not in "".join(result)
        assert "vlan 1" in "".join(result)

    def test_filter_boot_nxos(self):
        """Test that boot nxos commands are filtered"""
        lines = [
            "boot nxos bootflash:/nxos64-cs.10.3.6.M.bin\n",
            "vlan 1\n",
        ]
        result = filter_nxos_config(lines)
        assert "boot nxos" not in "".join(result)
        assert "vlan 1" in "".join(result)

    def test_filter_interface_mgmt0_block(self):
        """Test that interface mgmt0 block is filtered"""
        lines = [
            "interface mgmt0\n",
            "  vrf member management\n",
            "  ip address 10.62.108.61/22\n",
            "interface Vlan1\n",
            "  no shutdown\n",
        ]
        result = filter_nxos_config(lines)
        assert "interface mgmt0" not in "".join(result)
        assert "10.62.108.61" not in "".join(result)
        assert "interface Vlan1" in "".join(result)

    def test_filter_complex_nxos_config(self):
        """Test filtering on a complex NX-OS configuration"""
        lines = [
            "version 10.3(6) Bios:version 07.69\n",
            "hostname 08-D93180-2-49-TOR\n",
            "vdc 08-D93180-2-49-TOR id 1\n",
            "  limit-resource vlan minimum 16 maximum 4094\n",
            "tacacs-server key 7 \"\"\n",
            "tacacs-server host 10.66.164.188 key 7 \"\"\n",
            "aaa group server tacacs+ nwadmin\n",
            "    server 10.66.14.188\n",
            "    source-interface mgmt0\n",
            "ip access-list NETWORK_ADMIN\n",
            "  10 remark TW Admin Zone\n",
            "  630 permit ip 10.22.154.0/24 any\n",
            "snmp-server user admin network-admin auth md5 123 priv des 456\n",
            "snmp-server host 10.11.34.100 traps version 2c puc\n",
            "ip route 0.0.0.0/0 10.49.2.1\n",
            "vlan 1,700-703\n",
            "interface mgmt0\n",
            "  vrf member management\n",
            "  ip address 10.62.108.61/22\n",
            "interface Vlan1\n",
            "  no shutdown\n",
            "boot mode lxc\n",
            "boot nxos bootflash:/nxos64-cs.10.3.6.M.bin\n",
        ]
        result = filter_nxos_config(lines)
        result_str = "".join(result)

        # Verify filtered items are removed
        assert "hostname" not in result_str
        assert "tacacs-server" not in result_str
        assert "aaa group server tacacs+" not in result_str
        assert "ip access-list" not in result_str
        assert "snmp-server user" not in result_str
        assert "ip route 0.0.0.0/0" not in result_str
        assert "interface mgmt0" not in result_str
        assert "10.62.108.61" not in result_str
        assert "boot mode lxc" not in result_str
        assert "boot nxos" not in result_str

        # Verify kept items remain
        assert "version" in result_str
        assert "vdc" in result_str
        assert "limit-resource" in result_str
        assert "snmp-server host" in result_str
        assert "vlan 1,700-703" in result_str
        assert "interface Vlan1" in result_str
        assert "no shutdown" in result_str


class TestFilterHpeConfig:
    """Test HPE Comware configuration filtering"""

    def test_filter_sysname(self):
        """Test that sysname is filtered out"""
        lines = [
            "sysname F8-D-EDGE-ADM\n",
            "#\n",
            "vlan 1\n",
        ]
        result = filter_hpe_config(lines)
        assert "sysname" not in "".join(result)
        assert "vlan 1" in "".join(result)

    def test_filter_line_vty_block(self):
        """Test that line vty 0 63 block is filtered"""
        lines = [
            "line vty 0 63\n",
            "authentication-mode scheme\n",
            "user-role network-admin\n",
            "user-role network-operator\n",
            "idle-timeout 60 0\n",
            "command authorization\n",
            "#\n",
            "vlan 1\n",
        ]
        result = filter_hpe_config(lines)
        assert "line vty 0 63" not in "".join(result)
        assert "authentication-mode scheme" not in "".join(result)
        assert "vlan 1" in "".join(result)

    def test_filter_ip_route_static_default(self):
        """Test that default static route is filtered"""
        lines = [
            "ip route-static 0.0.0.0 0 10.63.48.1\n",
            "#\n",
            "vlan 1\n",
        ]
        result = filter_hpe_config(lines)
        assert "ip route-static 0.0.0.0 0" not in "".join(result)
        assert "vlan 1" in "".join(result)

    def test_filter_ssh_server(self):
        """Test that ssh server commands are filtered"""
        lines = [
            "ssh server enable\n",
            "ssh server acl 3010\n",
            "#\n",
            "vlan 1\n",
        ]
        result = filter_hpe_config(lines)
        assert "ssh server" not in "".join(result)
        assert "vlan 1" in "".join(result)

    def test_filter_local_user_block(self):
        """Test that local-user blocks are filtered"""
        lines = [
            "local-user nn class manage\n",
            "password hash $h$6$ZhD+zRTCkaQJiPqrS9fQ02dpUI+FoyiuQ45pUiK9WUqGhXWW/Q==\n",
            "service-type telnet ssh terminal\n",
            "authorization-attribute user-role network-admin\n",
            "authorization-attribute user-role network-operator\n",
            "#\n",
            "vlan 1\n",
        ]
        result = filter_hpe_config(lines)
        assert "local-user nn" not in "".join(result)
        assert "password hash" not in "".join(result)
        assert "vlan 1" in "".join(result)

    def test_filter_multiple_local_users(self):
        """Test filtering multiple local-user blocks"""
        lines = [
            "local-user nn class manage\n",
            "password hash $h$6$ZhD+zRTCkaQJiPqrS9fQ==\n",
            "service-type telnet ssh terminal\n",
            "#\n",
            "local-user ns class manage\n",
            "password hash $h$6$vzaFckXgmtRXG0tPQ80JEBU==\n",
            "service-type telnet ssh terminal\n",
            "#\n",
            "vlan 1\n",
        ]
        result = filter_hpe_config(lines)
        assert "local-user nn" not in "".join(result)
        assert "local-user ns" not in "".join(result)
        assert "password hash" not in "".join(result)
        assert "vlan 1" in "".join(result)

    def test_filter_complex_hpe_config(self):
        """Test filtering on a complex HPE configuration"""
        lines = [
            "#\n",
            "version 7.1.070, Release 6628P47\n",
            "#\n",
            "sysname F8-D-EDGE-ADM\n",
            "#\n",
            "clock timezone Taiwan add 08:00:00\n",
            "#\n",
            "vlan 1\n",
            "#\n",
            "vlan 999\n",
            "name Dummy\n",
            "#\n",
            "interface Vlan-interface1048\n",
            "ip address 10.63.48.198 255.255.255.0\n",
            "#\n",
            "line vty 0 63\n",
            "authentication-mode scheme\n",
            "user-role network-admin\n",
            "idle-timeout 60 0\n",
            "#\n",
            "ip route-static 0.0.0.0 0 10.63.48.1\n",
            "#\n",
            "ssh server enable\n",
            "ssh server acl 3010\n",
            "#\n",
            "local-user nn class manage\n",
            "password hash $h$6$ZhD+zRTCkaQJiPqrS9fQ==\n",
            "service-type telnet ssh terminal\n",
            "#\n",
            "local-user ns class manage\n",
            "password hash $h$6$vzaFckXgmtRXG0tPQ80JEBU==\n",
            "service-type telnet ssh terminal\n",
            "#\n",
            "return\n",
        ]
        result = filter_hpe_config(lines)
        result_str = "".join(result)

        # Verify filtered items are removed
        assert "sysname" not in result_str
        assert "line vty 0 63" not in result_str
        assert "authentication-mode scheme" not in result_str
        assert "ip route-static 0.0.0.0 0" not in result_str
        assert "ssh server" not in result_str
        assert "local-user nn" not in result_str
        assert "local-user ns" not in result_str
        assert "password hash" not in result_str

        # Verify kept items remain
        assert "version" in result_str
        assert "clock timezone" in result_str
        assert "vlan 1" in result_str
        assert "vlan 999" in result_str
        assert "interface Vlan-interface1048" in result_str
        assert "10.63.48.198" in result_str
        assert "return" in result_str


class TestFilterConfigMainFunction:
    """Test the main filter_config function"""

    def test_nxos_platform(self):
        """Test that nxos platform routes to correct filter"""
        lines = [
            "hostname test\n",
            "vlan 1\n",
        ]
        result = filter_config("nxos", lines)
        assert "hostname" not in "".join(result)
        assert "vlan 1" in "".join(result)

    def test_nxos_ssh_platform(self):
        """Test that nxos_ssh platform routes to correct filter"""
        lines = [
            "hostname test\n",
            "vlan 1\n",
        ]
        result = filter_config("nxos_ssh", lines)
        assert "hostname" not in "".join(result)
        assert "vlan 1" in "".join(result)

    def test_hpe_platform(self):
        """Test that hpe platform routes to correct filter"""
        lines = [
            "sysname test\n",
            "vlan 1\n",
        ]
        result = filter_config("hpe", lines)
        assert "sysname" not in "".join(result)
        assert "vlan 1" in "".join(result)

    def test_comware_platform(self):
        """Test that comware platform routes to correct filter"""
        lines = [
            "sysname test\n",
            "vlan 1\n",
        ]
        result = filter_config("comware", lines)
        assert "sysname" not in "".join(result)
        assert "vlan 1" in "".join(result)

    def test_unsupported_platform(self):
        """Test that unsupported platform raises ValueError"""
        lines = ["vlan 1\n"]
        with pytest.raises(ValueError, match="Unsupported platform: unknown"):
            filter_config("unknown", lines)
