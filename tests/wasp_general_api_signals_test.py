
import gc
import pytest
import weakref

from wasp_c_extensions.ev_loop import WEventLoop

from wasp_general.platform import WPlatformThreadEvent
from wasp_general.api.signals import WSignal, WSignalSourceProto, WSignalCallbackProto, WUnknownSignalException
from wasp_general.api.signals import WSignalSourceMeta, WSignalSource, WExceptionHandler, WEventLoopSignalCallback
from wasp_general.api.signals import WEventLoopCallbacksStorage


class CallbackClass:
    def __init__(self):
        self.results = []
        self.raise_exception = False
        self.exception = ValueError('!')
        self.event = WPlatformThreadEvent()

    def __call__(self, source, signal, signal_value=None):
        self.event.set()
        if self.raise_exception:
            raise self.exception
        self.results.append((source, signal, signal_value))


class ExceptionHandler(WExceptionHandler):
    def __init__(self):
        self.results = []

    def __call__(self, exception, callback, source, signal, signal_value=None):
        self.results.append((exception, callback, source, signal, signal_value))


def test_exceptions():
    assert(issubclass(WUnknownSignalException, Exception) is True)


def test_abstract():
    pytest.raises(TypeError, WSignalSourceProto)
    pytest.raises(NotImplementedError, WSignalSourceProto.emit, None, WSignal())
    pytest.raises(NotImplementedError, WSignalSourceProto.callback, None, WSignal(), lambda: None)
    pytest.raises(NotImplementedError, WSignalSourceProto.remove_callback, None, WSignal(), lambda: None)

    pytest.raises(TypeError, WSignalCallbackProto)
    pytest.raises(NotImplementedError, WSignalCallbackProto.__call__, None, WSignalSource(), WSignal())

    pytest.raises(TypeError, WExceptionHandler)
    pytest.raises(
        NotImplementedError,
        WExceptionHandler.__call__,
        None,
        ValueError('!'),
        lambda: None,
        WSignalSource(),
        WSignal()
    )


class TestWSignal:

    def test(self):
        signal = WSignal()
        _ = {signal: 1}  # check that signals may be used as dict keys
        assert(signal != WSignal())
        assert(signal == signal)

        assert(repr(signal) == object.__repr__(signal))

        signal.__wasp_signal_name__ = 'foo'
        assert (repr(signal) == 'foo')

        signal.__wasp_signal_name__ = 'bar'
        assert (repr(signal) == 'bar')

    @pytest.mark.parametrize('signal_args,signal_value,exc', [
        (tuple(), 1, None),
        (tuple(), 'foo', None),
        ((int, ), 1, None),
        ((int, ), 'foo', TypeError),
        ((int, lambda x: x < 10), 1, None),
        ((int, lambda x: x > 10), 1, ValueError),
    ])
    def test_check(self, signal_args, signal_value, exc):
        signal = WSignal(*signal_args)
        if exc:
            pytest.raises(exc, signal.check_value, signal_value)
        else:
            signal.check_value(signal_value)  # raises nothing


class TestWSignalSourceMeta:

    def test(self):

        class A(metaclass=WSignalSourceMeta):
            pass

        assert(A.__wasp_signals__ == set())

        class B(metaclass=WSignalSourceMeta):
            signal1 = WSignal()
            signal2 = WSignal()

        assert(B.__wasp_signals__ == {B.signal1, B.signal2})
        assert(B.signal1.__wasp_signal_name__ == 'B.signal1')
        assert(B.signal2.__wasp_signal_name__ == 'B.signal2')

        class C(B):
            signal3 = WSignal()

        assert(C.signal1.__wasp_signal_name__ == 'B.signal1')
        assert(C.signal2.__wasp_signal_name__ == 'B.signal2')

        with pytest.raises(TypeError):
            class D(B):
                signal1 = WSignal()  # signals may not be overridden


class TestWSignalSource:

    def test(self):
        source = WSignalSource()
        assert(isinstance(source, WSignalSource) is True)
        assert(isinstance(source, WSignalSourceProto) is True)

        pytest.raises(WUnknownSignalException, source.emit, WSignal())
        pytest.raises(WUnknownSignalException, source.callback, WSignal(), lambda: None)
        pytest.raises(WUnknownSignalException, source.remove_callback, WSignal(), lambda: None)

    def test_emit(self):
        class Source(WSignalSource):
            signal1 = WSignal()
            signal2 = WSignal(int)

        results = []

        def callback(source, signal, value):
            nonlocal results
            results.append((source, signal, value))

        s = Source()
        s.callback(Source.signal1, callback)
        assert(results == [])
        s.emit(Source.signal1)
        s.emit(Source.signal2, 1)
        assert(results == [(s, Source.signal1, None)])

        pytest.raises(TypeError, s.emit, Source.signal2, 'foo')

        results.clear()
        s.callback(Source.signal2, callback)
        s.emit(Source.signal1)
        s.emit(Source.signal2, 1)
        assert(results == [(s, Source.signal1, None), (s, Source.signal2, 1)])

        results.clear()
        s.remove_callback(Source.signal1, callback)
        s.emit(Source.signal1)
        s.emit(Source.signal2, 1)
        assert(results == [(s, Source.signal2, 1)])


class TestWEventLoopSignalCallback:

    def test(self, wasp_signals):
        callback_obj = CallbackClass()
        loop_callback = WEventLoopSignalCallback(wasp_signals.loop, callback_obj)
        assert(isinstance(loop_callback, WEventLoopSignalCallback) is True)
        assert(isinstance(loop_callback, WSignalCallbackProto) is True)

        assert(loop_callback.is_callback(callback_obj) is True)
        assert(loop_callback.is_callback(lambda: None) is False)

    def test_call(self, wasp_signals):
        callback_obj = CallbackClass()
        loop_callback = WEventLoopSignalCallback(wasp_signals.loop, callback_obj)

        source = WSignalSource()
        signal = WSignal()
        assert(callback_obj.results == [])
        loop_callback(source, signal)
        wasp_signals.stop()  # force callbacks to execute
        assert(callback_obj.results == [(source, signal, None)])

    def test_exc_handler_raise(self, wasp_signals):
        callback_obj = CallbackClass()
        callback_obj.raise_exception = True
        loop_callback = WEventLoopSignalCallback(wasp_signals.loop, callback_obj)

        source = WSignalSource()
        signal = WSignal()
        assert(callback_obj.results == [])
        loop_callback(source, signal)
        wasp_signals.stop()  # force callbacks to be executed
        assert(callback_obj.results == [])

    def test_exc_handler_process(self, wasp_signals):
        callback_obj = CallbackClass()
        callback_obj.raise_exception = True
        exc_handler = ExceptionHandler()
        loop_callback = WEventLoopSignalCallback(wasp_signals.loop, callback_obj, exc_handler=exc_handler)

        source = WSignalSource()
        signal = WSignal()
        assert(callback_obj.results == [])
        loop_callback(source, signal)
        wasp_signals.stop()  # force callbacks to be executed
        assert(callback_obj.results == [])
        assert(exc_handler.results == [
            (callback_obj.exception, callback_obj, source, signal, None)
        ])


class TestWEventLoopCallbacksStorage:

    class Source(WSignalSource):
        signal1 = WSignal()
        signal2 = WSignal()

    @pytest.fixture
    def callbacks_fixture(self, wasp_signals):
        callbacks_storage = WEventLoopCallbacksStorage(loop=wasp_signals.loop)
        source = TestWEventLoopCallbacksStorage.Source()
        source.callback(TestWEventLoopCallbacksStorage.Source.signal1, wasp_signals)
        source.callback(TestWEventLoopCallbacksStorage.Source.signal2, wasp_signals)

        return wasp_signals, callbacks_storage, source

    def test(self, wasp_signals):
        callbacks_storage = WEventLoopCallbacksStorage()
        assert(isinstance(callbacks_storage, WEventLoopCallbacksStorage) is True)
        assert(callbacks_storage.loop() is not None)
        assert(isinstance(callbacks_storage.loop(), WEventLoop) is True)

        callbacks_storage = WEventLoopCallbacksStorage(loop=wasp_signals.loop)
        assert(callbacks_storage.loop() is wasp_signals.loop)

    def test_proxy(self, callbacks_fixture):
        wasp_signals, callbacks_storage, source1 = callbacks_fixture
        source2 = TestWEventLoopCallbacksStorage.Source()
        source2.callback(TestWEventLoopCallbacksStorage.Source.signal1, wasp_signals)
        source2.callback(TestWEventLoopCallbacksStorage.Source.signal2, wasp_signals)

        callbacks_storage.proxy(
            source1, TestWEventLoopCallbacksStorage.Source.signal1,
            source2, TestWEventLoopCallbacksStorage.Source.signal2
        )

        source1.emit(TestWEventLoopCallbacksStorage.Source.signal1)
        wasp_signals.wait(TestWEventLoopCallbacksStorage.Source.signal1)
        wasp_signals.wait(TestWEventLoopCallbacksStorage.Source.signal2)

        assert(wasp_signals.dump() == {
            TestWEventLoopCallbacksStorage.Source.signal1: (None, ),
            TestWEventLoopCallbacksStorage.Source.signal2: (None, ),  # also emitted
        })

    def test_register(self, callbacks_fixture):
        wasp_signals, callbacks_storage, source = callbacks_fixture

        callback_obj = CallbackClass()
        callback_ref = weakref.ref(callback_obj)
        callbacks_storage.register(source, TestWEventLoopCallbacksStorage.Source.signal1, callback_obj)
        callback_obj = None
        gc.collect()  # force callback_obj to be cleaned

        source.emit(TestWEventLoopCallbacksStorage.Source.signal1)
        callback_ref().event.wait()
        assert(callback_ref().results == [
            (source, TestWEventLoopCallbacksStorage.Source.signal1, None),
        ])

    def test_unregister_exception(self, callbacks_fixture):
        wasp_signals, callbacks_storage, source = callbacks_fixture
        with pytest.raises(ValueError):
            callbacks_storage.unregister(source, TestWEventLoopCallbacksStorage.Source.signal1, CallbackClass())

    def test_unregister(self, callbacks_fixture):
        wasp_signals, callbacks_storage, source = callbacks_fixture

        callback_obj = CallbackClass()
        callback_ref = weakref.ref(callback_obj)
        callbacks_storage.register(source, TestWEventLoopCallbacksStorage.Source.signal1, callback_obj)
        callback_obj = None
        gc.collect()  # force callback_obj to be cleaned
        callbacks_storage.unregister(source, TestWEventLoopCallbacksStorage.Source.signal1, callback_ref())
        gc.collect()  # force callback_obj to be cleaned at all

        source.emit(TestWEventLoopCallbacksStorage.Source.signal1)
        assert(callback_ref() is None)  # there is no object and no callbacks will be called

    def test_clear(self, callbacks_fixture):
        wasp_signals, callbacks_storage, source = callbacks_fixture

        callback_obj = CallbackClass()
        callback_ref = weakref.ref(callback_obj)
        callbacks_storage.register(source, TestWEventLoopCallbacksStorage.Source.signal1, callback_obj)
        callback_obj = None
        gc.collect()  # force callback_obj to be cleaned
        callbacks_storage.clear()  # does the same as unregister all
        gc.collect()  # force callback_obj to be cleaned at all

        source.emit(TestWEventLoopCallbacksStorage.Source.signal1)
        assert(callback_ref() is None)  # there is no object and no callbacks will be called

    def test_exc_handler(self, wasp_signals):
        exc_handler = ExceptionHandler()
        callbacks_storage = WEventLoopCallbacksStorage(loop=wasp_signals.loop, exc_handler=exc_handler)
        source = TestWEventLoopCallbacksStorage.Source()
        callback_obj = CallbackClass()
        callback_obj.raise_exception = True
        callbacks_storage.register(source, TestWEventLoopCallbacksStorage.Source.signal1, callback_obj)

        source.emit(TestWEventLoopCallbacksStorage.Source.signal1)
        wasp_signals.stop()  # force callbacks to be executed
        assert(callback_obj.results == [])
        assert(exc_handler.results == [
            (callback_obj.exception, callback_obj, source, TestWEventLoopCallbacksStorage.Source.signal1, None)
        ])
