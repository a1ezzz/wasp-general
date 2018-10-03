
import pytest

from wasp_general.signals.proto import WSignalSourceProto, WSignalReceiverProto, WSignalConnectionMatrixProto


def test_abstract():

	class S(WSignalSourceProto):

		def send_signal(self, signal):
			pass

		def signals(self):
			pass

		def connection_matrix(self):
			pass

	class R(WSignalReceiverProto):

		def receive_signal(self, signal, signal_source, count):
			pass

	pytest.raises(TypeError, WSignalSourceProto)
	pytest.raises(NotImplementedError, WSignalSourceProto.send_signal, None, '')
	pytest.raises(NotImplementedError, WSignalSourceProto.signals, None)
	pytest.raises(NotImplementedError, WSignalSourceProto.connection_matrix, None)

	pytest.raises(TypeError, WSignalReceiverProto)
	pytest.raises(NotImplementedError, WSignalReceiverProto.receive_signal, None, '', S(), 1)

	pytest.raises(TypeError, WSignalConnectionMatrixProto)
	pytest.raises(NotImplementedError, WSignalConnectionMatrixProto.connect, None, S(), '', R())
	pytest.raises(NotImplementedError, WSignalConnectionMatrixProto.disconnect, None, S(), '', R())
