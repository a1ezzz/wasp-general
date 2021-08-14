
import pytest

from wasp_general.signals.proto import WSignalSourceProto, WSignalCallbackProto


def test_abstract():

    class Source(WSignalSourceProto):

        def signals(self):
            pass

        def send_signal(self, signal_name, signal_arg=None):
            pass

        def callback(self, signal_name, callback):
            pass

        def remove_callback(self, signal_name, callback):
            pass

    pytest.raises(TypeError, WSignalSourceProto)
    pytest.raises(NotImplementedError, WSignalSourceProto.signals, None)
    pytest.raises(NotImplementedError, WSignalSourceProto.send_signal, None, 'signal')
    pytest.raises(NotImplementedError, WSignalSourceProto.callback, None, 'signal', lambda: None)
    pytest.raises(NotImplementedError, WSignalSourceProto.remove_callback, None, 'signal', lambda: None)

    pytest.raises(TypeError, WSignalCallbackProto)
    pytest.raises(NotImplementedError, WSignalCallbackProto.__call__, None, Source(), 'signal', 1)
