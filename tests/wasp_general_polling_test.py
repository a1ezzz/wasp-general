# -*- coding: utf-8 -*-

import pytest
import socket
from enum import Enum
from threading import Event

from wasp_general.polling import WPollingHandlerProto, WSelectPollingHandler, __default_polling_handler_cls__


def test():
	assert(issubclass(__default_polling_handler_cls__, WPollingHandlerProto) is True)


def test_abstract():
	pytest.raises(TypeError, WPollingHandlerProto)
	pytest.raises(NotImplementedError, WPollingHandlerProto.polling_function, None)


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


class TestWSelectPollingHandler:

	__test_port__ = 22722

	def test(self):
		assert(issubclass(WSelectPollingHandler, WPollingHandlerProto) is True)

		read_handler = WSelectPollingHandler.create_handler()
		read_handler.setup_poll(WPollingHandlerProto.PollingEvent.read, 0.1)

		write_handler = WSelectPollingHandler.create_handler()
		write_handler.setup_poll(WPollingHandlerProto.PollingEvent.write, 0.1)

		socket_ln = socket.socket()
		socket_out = socket.socket()
		socket_in = None
		try:
			socket_ln.bind(('127.0.0.1', TestWSelectPollingHandler.__test_port__))
			socket_ln.listen()

			socket_out.connect(('127.0.0.1', TestWSelectPollingHandler.__test_port__))
			read_handler.poll_fd(socket_out)
			read_poll_fn = read_handler.polling_function()
			assert(read_poll_fn() is None)
			assert(read_poll_fn() is None)

			socket_in = socket_ln.accept()[0]
			write_handler.poll_fd(socket_in)
			write_poll_fn = write_handler.polling_function()
			assert(read_poll_fn() is None)
			assert(read_poll_fn() is None)
			assert(write_poll_fn() == ([], [socket_in]))
			assert(write_poll_fn() == ([], [socket_in]))

			socket_in.send(b'\x00')
			assert(read_poll_fn() == ([socket_out], []))
			assert(read_poll_fn() == ([socket_out], []))

			socket_out.recv(1)
			assert(read_poll_fn() is None)
			assert(read_poll_fn() is None)

			socket_in.send(b'\x01', socket.MSG_OOB)
			pytest.raises(WPollingHandlerProto.PollingError, read_poll_fn)

			socket_out.close()
			pytest.raises(WPollingHandlerProto.PollingError, read_poll_fn)

		finally:
			if socket_in is not None:
				socket_in.close()
			socket_out.close()
			socket_ln.close()
