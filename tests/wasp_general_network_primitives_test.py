# -*- coding: utf-8 -*-

import pytest

from wasp_general.types.binarray import WBinArray

from wasp_general.network.primitives import WMACAddress, WIPV4Address, WNetworkIPV4, WNetworkIPV4Iterator, WFQDN
from wasp_general.network.primitives import WIPPort, WIPV4SocketInfo


class TestWMACAddress:

	def test_from_string(self):

		pytest.raises(ValueError, WMACAddress, "01:23:45:ab")
		pytest.raises(ValueError, WMACAddress, "01:23:45:ab:cd:ZZ")

		assert(
			str(WMACAddress("01:23:45:ab:cd:ef").bin_address()) ==
			"000000010010001101000101101010111100110111101111"
		)
		assert(
			str(WMACAddress.from_string("01-23-45-ab-cd-ef").bin_address()) ==
			"000000010010001101000101101010111100110111101111"
		)
		assert(
			str(WMACAddress.from_string("01:23:45:ab:cd:ef").bin_address()) ==
			"000000010010001101000101101010111100110111101111"
		)
		assert(
			str(WMACAddress.from_string("0123.45ab.cdef").bin_address()) ==
			"000000010010001101000101101010111100110111101111"
		)
		assert(
			str(WMACAddress.from_string("012345abcdef").bin_address()) ==
			"000000010010001101000101101010111100110111101111"
		)

	def test_to_string(self):
		assert(
			str(WMACAddress(WBinArray(0b000000010010001101000101101010111100110111101111))) ==
			"01:23:45:ab:cd:ef"
		)

	def test_to_bytes(self):
		assert(
			bytes(WMACAddress(WBinArray(0b000000010010001101000101101010111100110111101111))) ==
			b"\x01\x23\x45\xab\xcd\xef"
		)


class TestWIPV4Address:

	def test_init(self):
		pytest.raises(TypeError, WIPV4Address, 0.1)
		assert(isinstance(WIPV4Address("10.192.0.1"), WIPV4Address) is True)
		assert(isinstance(WIPV4Address(WBinArray(1)), WIPV4Address) is True)
		assert(isinstance(WIPV4Address(1), WIPV4Address) is True)

	def test_bin_address(self):
		assert(len(WIPV4Address(0).bin_address()) == (4 * 8))
		assert(str(WIPV4Address("10.192.0.1").bin_address()) == "00001010110000000000000000000001")

	def test_from_string(self):
		pytest.raises(ValueError, WIPV4Address.from_string, '11.1.1')
		assert(str(WIPV4Address.from_string("10.192.0.1").bin_address()) == "00001010110000000000000000000001")

	def test_to_string(self):
		pytest.raises(TypeError, WIPV4Address.to_string, '10.192.0.1')
		address = WIPV4Address(WBinArray(0b00001010110000000000000000000001))
		assert(WIPV4Address.to_string(address) == "10.192.0.1")
		assert(WIPV4Address.to_string(address, dns_format=True) == "1.0.192.10.in-addr.arpa")

	def test_str(self):
		assert(str(WIPV4Address(WBinArray(0b00001010110000000000000000000001))) == "10.192.0.1")

	def test_bytes(self):
		assert(bytes(WIPV4Address(WBinArray(0b00001010110000000000000000000001))) == b"\x0a\xc0\x00\x01")


class TestNetworkIPV4:

	def test_init(self):
		assert(isinstance(WNetworkIPV4('10.0.0.0/24'), WNetworkIPV4) is True)
		pytest.raises(ValueError, WNetworkIPV4, '10.0.0.0/33')
		assert(isinstance(WNetworkIPV4('0.0.0.0/0'), WNetworkIPV4) is True)
		pytest.raises(ValueError, WNetworkIPV4, '10.0.0.0/-1')
		pytest.raises(ValueError, WNetworkIPV4, '10.0.0.1/24')
		assert(isinstance(WNetworkIPV4('10.0.0.1/24', network_address=False), WNetworkIPV4) is True)
		assert(isinstance(WNetworkIPV4((WIPV4Address('192.168.0.0'), 24)), WNetworkIPV4) is True)

	def test_address(self):
		assert(isinstance(WNetworkIPV4('10.0.0.0/24').address(), WIPV4Address) is True)
		assert(int(WNetworkIPV4('0.0.1.0/24').address().bin_address()) == 256)
		assert(int(WNetworkIPV4((WIPV4Address('0.0.1.0'), 24)).address().bin_address()) == 256)

	def test_mask(self):
		assert(isinstance(WNetworkIPV4('10.0.0.0/24').mask(), int) is True)
		assert(int(WNetworkIPV4('0.0.1.0/24').mask()) == 24)

	def test_first_address(self):
		assert(str(WNetworkIPV4('10.0.0.0/24').first_address()) == '10.0.0.1')
		assert(str(WNetworkIPV4('10.0.0.0/24').first_address(skip_network_address=False)) == '10.0.0.0')
		assert(str(WNetworkIPV4('10.0.0.1/24', network_address=False).first_address()) == '10.0.0.1')
		net = WNetworkIPV4('10.0.0.1/24', network_address=False)
		assert(str(net.first_address(skip_network_address=False)) == '10.0.0.0')

	def test_last_address(self):
		assert(str(WNetworkIPV4('10.0.0.0/23').last_address()) == '10.0.1.254')
		assert(str(WNetworkIPV4('10.0.0.0/23').last_address(skip_broadcast_address=False)) == '10.0.1.255')
		assert(str(WNetworkIPV4('10.0.0.1/23', network_address=False).last_address()) == '10.0.1.254')
		net = WNetworkIPV4('10.0.0.1/23', network_address=False)
		assert(str(net.last_address(skip_broadcast_address=False)) == '10.0.1.255')

	def test_iterator(self):
		assert(len(list(WNetworkIPV4('10.0.0.0/32').iterator())) == 1)
		assert(str(list(WNetworkIPV4('10.0.0.0/32').iterator())[0]) == '10.0.0.0')
		assert(len(list(WNetworkIPV4('10.0.0.0/32').iterator(skip_network_address=False))) == 1)
		assert(len(list(WNetworkIPV4('10.0.0.0/32').iterator(skip_broadcast_address=False))) == 1)
		net = WNetworkIPV4('10.0.0.0/32')
		assert(len(list(net.iterator(skip_broadcast_address=False, skip_network_address=False))) == 1)

		assert(len(list(WNetworkIPV4('10.0.0.0/31').iterator())) == 2)
		assert(str(list(WNetworkIPV4('10.0.0.0/31').iterator())[0]) == '10.0.0.0')
		assert(str(list(WNetworkIPV4('10.0.0.0/31').iterator())[1]) == '10.0.0.1')
		assert(len(list(WNetworkIPV4('10.0.0.0/31').iterator(skip_network_address=False))) == 2)
		assert(len(list(WNetworkIPV4('10.0.0.0/31').iterator(skip_broadcast_address=False))) == 2)
		net = WNetworkIPV4('10.0.0.0/31')
		assert(len(list(net.iterator(skip_broadcast_address=False, skip_network_address=False))) == 2)

		assert(len(list(WNetworkIPV4('10.0.0.0/28').iterator())) == 14)
		assert(str(list(WNetworkIPV4('10.0.0.0/28').iterator())[0]) == '10.0.0.1')
		assert(str(list(WNetworkIPV4('10.0.0.0/28').iterator(skip_network_address=False))[0]) == '10.0.0.0')
		assert(str(list(WNetworkIPV4('10.0.0.0/28').iterator())[13]) == '10.0.0.14')
		assert(str(list(WNetworkIPV4('10.0.0.0/28').iterator(skip_broadcast_address=False))[14]) == '10.0.0.15')
		assert(len(list(WNetworkIPV4('10.0.0.0/28').iterator(skip_network_address=False))) == 15)
		assert(len(list(WNetworkIPV4('10.0.0.0/28').iterator(skip_broadcast_address=False))) == 15)
		net = WNetworkIPV4('10.0.0.0/28')
		assert(len(list(net.iterator(skip_broadcast_address=False, skip_network_address=False))) == 16)

		it = WNetworkIPV4Iterator(WIPV4Address('10.0.0.0'))
		assert(len(list(it)) == 1)

	def test_contains(self):
		assert((WIPV4Address('192.168.0.1') in WNetworkIPV4('192.168.0.0/24')) is True)
		assert((WIPV4Address('192.168.0.1') in WNetworkIPV4('192.0.0.0/24')) is False)
		assert((WIPV4Address('192.168.0.0') in WNetworkIPV4('192.0.0.0/24')) is False)

	def test_multicast(self):
		assert(WNetworkIPV4.is_multicast(WIPV4Address('192.168.0.1')) is False)
		assert(WNetworkIPV4.is_multicast(WIPV4Address('239.200.200.1')) is True)


class TestWFQDN:
	def test_fqdn(self):
		assert(str(WFQDN() == ''))
		assert(str(WFQDN('site1.org2.fld.') == 'site1.org2.fld'))
		assert(str(WFQDN(['site1', 'org2', 'fld', '']) == 'site1.org2.fld'))

		pytest.raises(ValueError, WFQDN, 'a' * 1000)
		pytest.raises(ValueError, WFQDN, '\ud13f')

		assert(WFQDN.to_string(WFQDN('site1.org2.fld'), leading_dot=True) == 'site1.org2.fld.')
		pytest.raises(TypeError, WFQDN.to_string, 'site1.org2.fld')
		assert(WFQDN.to_string(WFQDN.from_string(''), leading_dot=True) == '.')

		assert(isinstance(WFQDN.punycode('\ud13f'), WFQDN) is True)
		assert(str(WFQDN.punycode('\ud13f')) == 'xn--3v7b')


class TestWIPPort:

	def test_port(self):
		pytest.raises(ValueError, WIPPort, 0)
		pytest.raises(ValueError, WIPPort, 70000)

		assert(int(WIPPort(70)) == 70)
		assert(str(WIPPort(70)) == "70")


class TestWIPV4SocketInfo:

	def test_socket_info(self):
		si = WIPV4SocketInfo('192.168.0.200', 2020)
		assert(isinstance(si.address(), WIPV4Address) is True)
		assert(str(si.address()) == '192.168.0.200')
		assert(isinstance(si.port(), WIPPort) is True)
		assert(int(si.port()) == 2020)

		assert(si.pair() == ('192.168.0.200', 2020))
		assert(WIPV4SocketInfo('10.20.30.40').pair() == ('10.20.30.40', 0))
		assert(WIPV4SocketInfo(None, 80).pair() == ('', 80))
		assert(WIPV4SocketInfo().pair() == ('', 0))

		assert(WIPV4SocketInfo(1).pair() == ('0.0.0.1', 0))

		assert(WIPV4SocketInfo(WFQDN('site1.org')).pair() == ('site1.org', 0))
		assert(WIPV4SocketInfo('site1.org').pair() == ('site1.org', 0))

		pytest.raises(ValueError, WIPV4SocketInfo, '!')

		assert(WIPV4SocketInfo('').address() is None)
		assert(WIPV4SocketInfo('').pair() == ('', 0))

		result = WIPV4SocketInfo.parse_socket_info('127.1.2.3:1020')
		assert(isinstance(result, WIPV4SocketInfo) is True)
		assert(str(result.address()) == '127.1.2.3')
		assert(int(result.port()) == 1020)

		result = WIPV4SocketInfo.parse_socket_info('127.1.2.5')
		assert(isinstance(result, WIPV4SocketInfo) is True)
		assert(str(result.address()) == '127.1.2.5')
		assert(result.port() is None)

		pytest.raises(ValueError, WIPV4SocketInfo.parse_socket_info, '127.1.2.5:11:')
