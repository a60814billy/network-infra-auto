import pytest
import ipaddress
from unittest.mock import MagicMock

# Adjust the import path based on your project structure and how pytest discovers tests
# Adjust the import path based on your project structure and how pytest discovers tests
# Since the test is now inside src/baseline_snmp/tests, use a relative import.
from ..snmp_task import get_snmp_vars_from_host


# Mock host object for testing
class MockHost:
    def __init__(self, data):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)

    # Add other methods/attributes if needed by the function under test in the future
    # For get_snmp_vars_from_host, only .get() is used.


def test_get_snmp_vars_from_host_no_baseline_data():
    """Test when the host has no 'baseline_snmp' key."""
    mock_host = MockHost({})  # Host data without 'baseline_snmp'
    expected_vars = {}
    result_vars = get_snmp_vars_from_host(mock_host)
    assert result_vars == expected_vars


def test_get_snmp_vars_from_host_basic():
    """Test with basic baseline_snmp data, no access list."""
    host_data = {
        "baseline_snmp": {
            "snmp_community_ro": "public",
            "snmp_community_rw": "private",
            "snmp_location": "Data Center A",
            "snmp_contact": "Net Admin",
        }
    }
    mock_host = MockHost(host_data)
    # Expected vars should be the same as the input baseline_snmp dict
    expected_vars = host_data["baseline_snmp"]
    result_vars = get_snmp_vars_from_host(mock_host)
    assert result_vars == expected_vars
    # Ensure the original dict wasn't modified if no ACL processing happened
    assert "_snmp_acl_allow_networks" not in result_vars


def test_get_snmp_vars_from_host_with_access_list():
    """Test with baseline_snmp data including snmp_access_list."""
    host_data = {
        "baseline_snmp": {
            "snmp_community_ro": "public",
            "snmp_access_list": [
                "192.168.1.0/24",
                "10.0.0.0/8",
                "172.16.10.5/32",  # Single host
            ],
        }
    }
    mock_host = MockHost(host_data)

    # Calculate expected network/wildcard pairs
    ip1 = ipaddress.ip_network("192.168.1.0/24")
    ip2 = ipaddress.ip_network("10.0.0.0/8")
    ip3 = ipaddress.ip_network("172.16.10.5/32")

    expected_acl_networks = [
        {"network": str(ip1.network_address), "wildcard": str(ip1.hostmask)},
        {"network": str(ip2.network_address), "wildcard": str(ip2.hostmask)},
        {"network": str(ip3.network_address), "wildcard": str(ip3.hostmask)},
    ]

    # The result should contain original keys plus the processed ACL list
    expected_vars = {
        "snmp_community_ro": "public",
        "snmp_access_list": [
            "192.168.1.0/24",
            "10.0.0.0/8",
            "172.16.10.5/32",
        ],
        "_snmp_acl_allow_networks": expected_acl_networks,
    }

    result_vars = get_snmp_vars_from_host(mock_host)
    assert result_vars == expected_vars
    assert "_snmp_acl_allow_networks" in result_vars
    assert result_vars["_snmp_acl_allow_networks"] == expected_acl_networks


def test_get_snmp_vars_from_host_empty_access_list():
    """Test with baseline_snmp data including an empty snmp_access_list."""
    host_data = {
        "baseline_snmp": {
            "snmp_community_ro": "public",
            "snmp_access_list": [],  # Empty list
        }
    }
    mock_host = MockHost(host_data)
    expected_vars = {
        "snmp_community_ro": "public",
        "snmp_access_list": [],
        "_snmp_acl_allow_networks": [],  # Should be initialized as empty
    }
    result_vars = get_snmp_vars_from_host(mock_host)
    assert result_vars == expected_vars
    assert result_vars["_snmp_acl_allow_networks"] == []


# Add more tests here for other functions in snmp_task.py later
