# -*- coding: utf-8 -*-

import enum
import gc
from threading import Thread
import pytest

from wasp_c_extensions.ev_loop import WEventLoop

from wasp_general.api.signals import WSignal, ASignalSourceProto, ASignalCallbackProto, WUnknownSignalException
from wasp_general.api.signals import WSignalSourceMeta, WSignalSource, WEventLoopSignalCallback


def test_abstract():

    class Source(ASignalSourceProto):

        def emit(self, signal, signal_value=None):
            pass

        def callback(self, signal, callback):
            pass

        def remove_callback(self, signal, callback):
            pass

    signal = WSignal()

    pytest.raises(TypeError, ASignalSourceProto)
    pytest.raises(NotImplementedError, ASignalSourceProto.emit, None, signal)
    pytest.raises(NotImplementedError, ASignalSourceProto.callback, None, signal, lambda: None)
    pytest.raises(NotImplementedError, ASignalSourceProto.remove_callback, None, signal, lambda: None)

    pytest.raises(TypeError, ASignalCallbackProto)
    pytest.raises(NotImplementedError, ASignalCallbackProto.__call__, None, Source(), signal, 1)


class TestWSignal:

    def test(self):
        assert(WSignal() != WSignal())

        WSignal().check_value(1)
        WSignal().check_value('!')

        signal = WSignal(int, lambda x: x > 0)
        signal.check_value(10)

        with pytest.raises(TypeError):
            signal.check_value('!')

        with pytest.raises(ValueError):
            signal.check_value(-1)

        d = {signal: 1}  # check that signal is hashable
        assert(d[signal] == 1)


class TestWSignalSourceMeta:

    def test_inheritance(self):
        class A(metaclass=WSignalSourceMeta):
            signal1 = WSignal()
            signal3 = WSignal()

        class C:
            pass

        with pytest.raises(TypeError):
            class B(A, C):
                signal2 = WSignal()
                signal3 = WSignal()

        class D(A, C):
            signal2 = WSignal()


class TestWSignalSource:

    def test(self):
        s = WSignalSource()
        assert(isinstance(s, WSignalSource) is True)
        assert(isinstance(s, ASignalSourceProto) is True)
        pytest.raises(WUnknownSignalException, s.emit, WSignal())
        pytest.raises(WUnknownSignalException, s.callback, WSignal(), lambda: None)

        test_results = {'callback_called': 0}

        def signal_callback(signal_source, signal, signal_value):
            test_results['callback_called'] += (signal_value if signal_value is not None else 1)

        class Source(WSignalSource):
            signal1 = WSignal()
            signal2 = WSignal()
            signal3 = WSignal(int, lambda x: x > 0)

        s = Source()
        s.callback(Source.signal1, signal_callback)

        assert(test_results['callback_called'] == 0)
        s.emit(Source.signal2)
        assert(test_results['callback_called'] == 0)
        s.emit(Source.signal1)
        assert(test_results['callback_called'] == 1)
        s.emit(Source.signal1, 5)
        assert(test_results['callback_called'] == 6)

        pytest.raises(ValueError, s.remove_callback, Source.signal2, signal_callback)
        s.remove_callback(Source.signal1, signal_callback)
        s.emit(Source.signal1)
        assert(test_results['callback_called'] == 6)

        s.emit(Source.signal3, 10)
        with pytest.raises(TypeError):
            s.emit(Source.signal3)
        with pytest.raises(TypeError):
            s.emit(Source.signal3, '!')
        with pytest.raises(ValueError):
            s.emit(Source.signal3, -1)


    def test_weak_ref(self):

        callback_result = []

        class CallbackCls:
            def __call__(self, *args, **kwargs):
                callback_result.append(1)

        class Source(WSignalSource):
            signal1 = WSignal()

        callback_obj = CallbackCls()
        source = Source()
        assert(callback_result == [])
        source.callback(Source.signal1, callback_obj)
        source.emit(Source.signal1)
        callback_obj = None  # force
        gc.collect()
        source.emit(Source.signal1)

        assert(callback_result == [1])


class TestWEventLoopSignalCallback:

    def test(self):
        loop = WEventLoop()
        c = WEventLoopSignalCallback(loop, lambda x, y, z: None)
        assert(isinstance(c, ASignalCallbackProto) is True)

        thread = Thread(target=loop.start_loop)
        thread.start()
        loop.stop_loop()
        thread.join()

    def test_call(self):
        callback_result = []

        def callback_fn(c_source, c_signal, signal_value=None):
            callback_result.append({"source": c_source, "signal": c_signal, "signal_value": signal_value})

        class Source(WSignalSource):
            signal1 = WSignal()

        source = Source()
        loop = WEventLoop(immediate_stop=False)
        callback = WEventLoopSignalCallback(loop, callback_fn)
        thread = Thread(target=loop.start_loop)
        thread.start()

        try:
            assert(callback_result == [])
            source.callback(source.signal1, callback)
            source.emit(source.signal1)
            source.emit(Source.signal1)
            source.remove_callback(Source.signal1, callback)
            source.emit(Source.signal1)
        finally:
            loop.stop_loop()
            thread.join()

        assert(
            callback_result == [
                {"source": source, "signal": Source.signal1, "signal_value": None},
                {"source": source, "signal": Source.signal1, "signal_value": None}
            ]
        )
