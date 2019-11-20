
import pytest

from wasp_general.api.signals.proto import WSignalWatcherProto, WSignalSourceProto, WSignalCallbackProto
from wasp_general.api.signals.proto import WSignalProxyProto


def test_imports():
	import wasp_general.api.signals
	assert(wasp_general.api.signals.WSignalCallbackProto is WSignalCallbackProto)


def test_abstract():

	class W(WSignalWatcherProto):

		def wait(self, timeout=None):
			pass

		def has_next(self):
			pass

		def next(self):
			pass

	class C(WSignalCallbackProto):

		def __call__(self, signal_id, signal_source, signal_args=None):
			pass

	class S(WSignalSourceProto):

		def signals(cls):
			return tuple()

		def send_signal(self, signal_id, signal_args=None):
			pass

		def watch(self, signal_id, watcher=None):
			pass

		def remove_watcher(self, watcher):
			pass

		def callback(self, signal_id, callback):
			pass

		def remove_callback(self, signal_id, callback):
			pass

	pytest.raises(TypeError, WSignalWatcherProto)
	pytest.raises(NotImplementedError, WSignalWatcherProto.wait, None)
	pytest.raises(NotImplementedError, WSignalWatcherProto.wait, None, 1)
	pytest.raises(NotImplementedError, WSignalWatcherProto.has_next, None)
	pytest.raises(NotImplementedError, WSignalWatcherProto.next, None)

	pytest.raises(TypeError, WSignalSourceProto)
	pytest.raises(NotImplementedError, WSignalSourceProto.signals)
	pytest.raises(NotImplementedError, WSignalSourceProto.send_signal, None, 'signal')
	pytest.raises(NotImplementedError, WSignalSourceProto.send_signal, None, 'signal', 1)
	pytest.raises(NotImplementedError, WSignalSourceProto.watch, None, 'signal')
	pytest.raises(NotImplementedError, WSignalSourceProto.remove_watcher, None, W())
	pytest.raises(NotImplementedError, WSignalSourceProto.callback, None, 'signal', C())
	pytest.raises(NotImplementedError, WSignalSourceProto.remove_callback, None, 'signal', C())

	pytest.raises(TypeError, WSignalCallbackProto)
	pytest.raises(NotImplementedError, WSignalCallbackProto.__call__, None, S(), 'signal', 1)

	pytest.raises(TypeError, WSignalProxyProto.ProxiedSignalProto)
	pytest.raises(NotImplementedError, WSignalProxyProto.ProxiedSignalProto.signal_source, None)
	pytest.raises(NotImplementedError, WSignalProxyProto.ProxiedSignalProto.signal_id, None)
	pytest.raises(NotImplementedError, WSignalProxyProto.ProxiedSignalProto.payload, None)

	pytest.raises(TypeError, WSignalProxyProto)
	assert(issubclass(WSignalProxyProto, WSignalWatcherProto) is True)

	pytest.raises(NotImplementedError, WSignalProxyProto.proxy, None, S(), 'signal')
	pytest.raises(NotImplementedError, WSignalProxyProto.stop_proxying, None, S(), 'signal')
	pytest.raises(NotImplementedError, WSignalProxyProto.wait, None)
	pytest.raises(NotImplementedError, WSignalProxyProto.wait, None, 1)
	pytest.raises(NotImplementedError, WSignalProxyProto.has_next, None)
	pytest.raises(NotImplementedError, WSignalProxyProto.next, None)
