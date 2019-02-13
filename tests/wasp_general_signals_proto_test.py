
import pytest

from wasp_general.signals.proto import WSignalSourceProto, WSignalCallbackProto


def test_abstract():

	class W(WSignalSourceProto.WatcherProto):

		def wait(self, timeout=None):
			pass

	class C(WSignalCallbackProto):

		def __call__(self, signal_name, signal_source, signal_args=None):
			pass

	class S(WSignalSourceProto):

		def send_signal(self, signal_name, signal_args=None):
			pass

		def signals(self):
			pass

		def watch(self, signal_name, watcher=None):
			pass

		def remove_watcher(self, signal_name, watcher):
			pass

		def callback(self, signal_name, callback):
			pass

		def remove_callback(self, signal_name, callback):
			pass

	pytest.raises(TypeError, WSignalSourceProto.WatcherProto)
	pytest.raises(NotImplementedError, WSignalSourceProto.WatcherProto.wait, None)
	pytest.raises(NotImplementedError, WSignalSourceProto.WatcherProto.wait, None, 1)

	pytest.raises(TypeError, WSignalSourceProto)
	pytest.raises(NotImplementedError, WSignalSourceProto.send_signal, None, 'signal')
	pytest.raises(NotImplementedError, WSignalSourceProto.send_signal, None, 'signal', 1)
	pytest.raises(NotImplementedError, WSignalSourceProto.signals, None)
	pytest.raises(NotImplementedError, WSignalSourceProto.watch, None, 'signal')
	pytest.raises(NotImplementedError, WSignalSourceProto.remove_watcher, None, 'signal', W())
	pytest.raises(NotImplementedError, WSignalSourceProto.callback, None, 'signal', C())
	pytest.raises(NotImplementedError, WSignalSourceProto.remove_callback, None, 'signal', C())

	pytest.raises(TypeError, WSignalCallbackProto)
	pytest.raises(NotImplementedError, WSignalCallbackProto.__call__, None, 'signal', S(), 1)
