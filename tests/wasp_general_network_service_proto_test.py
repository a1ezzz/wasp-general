# -*- coding: utf-8 -*-

import pytest
from enum import Enum
from threading import Event
from socket import socket

from wasp_general.network.service.proto import WServiceWorkerProto, WServiceFactoryProto


def test_abstract():

	pytest.raises(TypeError, WServiceWorkerProto)
	pytest.raises(NotImplementedError, WServiceWorkerProto.process, None, socket())

	pytest.raises(TypeError, WServiceFactoryProto)
	pytest.raises(NotImplementedError, WServiceFactoryProto.worker, None, Event())
	pytest.raises(NotImplementedError, WServiceFactoryProto.terminate_workers, None)


class TestWServiceFactoryProto:

	class Factory(WServiceFactoryProto):

		def worker(self, timeout=None):
			pass

		def terminate_workers(self):
			pass

	def test(self):
		factory = TestWServiceFactoryProto.Factory()
		assert(factory.stop_event() is None)

		event = Event()
		factory.configure(event)
		assert(factory.stop_event() == event)
