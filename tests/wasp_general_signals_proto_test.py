
import pytest

from wasp_general.signals.proto import WSignalSourceProto, WSignalReceiverProto, WSignalSenderProto


def test_abstract():

	class S(WSignalSourceProto):

		def send_signal(self, signal):
			pass

		def signals(self):
			pass

	class R(WSignalReceiverProto):

		def receive_signal(self, signal, signal_source):
			pass

	pytest.raises(TypeError, WSignalSourceProto)
	pytest.raises(NotImplementedError, WSignalSourceProto.send_signal, None, '')
	pytest.raises(NotImplementedError, WSignalSourceProto.signals, None)

	pytest.raises(TypeError, WSignalReceiverProto)
	pytest.raises(NotImplementedError, WSignalReceiverProto.receive_signal, None, '', S())

	assert(issubclass(WSignalSenderProto, WSignalSourceProto) is True)
	pytest.raises(TypeError, WSignalSenderProto)
	pytest.raises(NotImplementedError, WSignalSenderProto.connect, None, '', R())
	pytest.raises(NotImplementedError, WSignalSenderProto.disconnect, None, '', R())
