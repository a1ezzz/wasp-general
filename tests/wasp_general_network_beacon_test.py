# -*- coding: utf-8 -*-

import asyncio
import pytest

from wasp_general.network.aio_service import __default_network_services_collection__
from wasp_general.network.aio_client import __default_network_client_collection__
from wasp_general.network.beacon import WBeaconServerProtocol, WBeaconClientProtocol


@pytest.mark.asyncio
async def test_beacon():
	beacon_uri = 'udp://127.0.0.1:30000'
	loop = asyncio.get_event_loop()

	beacon_service = __default_network_services_collection__.network_handler(
		beacon_uri, WBeaconServerProtocol, aio_loop=loop
	)
	beacon_client = __default_network_client_collection__.network_handler(
		beacon_uri, WBeaconClientProtocol, aio_loop=loop
	)

	async def test_response():
		response = await beacon_client.connect()
		assert(isinstance(response, dict) is True)

	await asyncio.gather(beacon_service.start(), test_response(), test_response(), test_response())
	await beacon_service.stop()
