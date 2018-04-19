# -*- coding: utf-8 -*-

import pytest
from enum import Enum
from threading import Event
from socket import socket

from wasp_general.network.service.proto import WPollingHandlerProto, WServiceWorkerProto, WServiceFactoryProto


def test_abstract():

	pytest.raises(TypeError, WPollingHandlerProto)
	pytest.raises(NotImplementedError, WPollingHandlerProto.polling_function, None)

	pytest.raises(TypeError, WServiceWorkerProto)
	pytest.raises(NotImplementedError, WServiceWorkerProto.process, None, socket())

	pytest.raises(TypeError, WServiceFactoryProto)
	pytest.raises(NotImplementedError, WServiceFactoryProto.worker, None, Event())
	pytest.raises(NotImplementedError, WServiceFactoryProto.terminate_workers, None)


class TestWPollingHandlerProto:

	class Handler(WPollingHandlerProto):

		def polling_function(self):
			return lambda: None

	def test_exception(self):
		assert(issubclass(WPollingHandlerProto.PollingError, Exception) is True)
		assert(WPollingHandlerProto.PollingError().file_objects() == tuple())
		assert(WPollingHandlerProto.PollingError(1, 2, 3).file_objects() == (1, 2, 3))

	def test_enum(self):
		assert(issubclass(WPollingHandlerProto.PollingEvent, Enum) is True)
		assert(WPollingHandlerProto.PollingEvent.read is not None)
		assert(WPollingHandlerProto.PollingEvent.write is not None)

	def test(self):
		handler = TestWPollingHandlerProto.Handler()

		assert(handler.file_obj() == tuple())
		assert(handler.event_mask() is None)
		assert(handler.timeout() is None)

		handler = TestWPollingHandlerProto.Handler.create_handler()
		assert(handler.file_obj() == tuple())
		assert(handler.event_mask() is None)
		assert(handler.timeout() is None)

		handler.setup_poll(WPollingHandlerProto.PollingEvent.read, 0.1)
		assert(0 < handler.timeout() < 0.2)
		assert(handler.event_mask() == WPollingHandlerProto.PollingEvent.read.value)

		handler.setup_poll(
			WPollingHandlerProto.PollingEvent.read.value + WPollingHandlerProto.PollingEvent.write.value, 1
		)
		assert(handler.timeout() == 1)
		event_mask = \
			WPollingHandlerProto.PollingEvent.read.value + WPollingHandlerProto.PollingEvent.write.value
		assert(handler.event_mask() == event_mask)

		handler.setup_poll(WPollingHandlerProto.PollingEvent.read)
		assert (handler.timeout() is None)

		pytest.raises(TypeError, handler.setup_poll, 0.1, 10)

		assert(handler.file_obj() == tuple())
		handler.poll_fd(1)
		assert(handler.file_obj() == (1,))
		handler.poll_fd(10)
		assert(handler.file_obj() == (1, 10))

		handler.reset()
		assert(handler.file_obj() == tuple())
		assert(handler.event_mask() is None)
		assert(handler.timeout() is None)


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
