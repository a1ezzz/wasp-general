# -*- coding: utf-8 -*-

import gc
from threading import Thread
import pytest

from wasp_c_extensions.ev_loop import WEventLoop

from wasp_general.api.signals.proto import WSignalSourceProto, WSignalCallbackProto, WUnknownSignalException
from wasp_general.api.signals.impl import WSignalSource, WEventLoopSignalCallback


class TestWSignalSource:

    def test(self):
        s = WSignalSource("signal1", "signal2")

        assert(isinstance(s, WSignalSource) is True)
        assert(isinstance(s, WSignalSourceProto) is True)

        assert(s.signals() == ("signal1", "signal2"))
        pytest.raises(WUnknownSignalException, s.send_signal, "signal3")

        test_results = {'callback_called': 0}

        def signal_callback(signal_source, signal_name, signal_arg):
            test_results['callback_called'] += (signal_arg if signal_arg is not None else 1)

        s.callback("signal1", signal_callback)

        assert(test_results['callback_called'] == 0)
        s.send_signal("signal2")
        assert(test_results['callback_called'] == 0)
        s.send_signal("signal1")
        assert(test_results['callback_called'] == 1)
        s.send_signal("signal1", 5)
        assert(test_results['callback_called'] == 6)

        pytest.raises(ValueError, s.remove_callback, "signal2", signal_callback)
        s.remove_callback("signal1", signal_callback)
        s.send_signal("signal1")
        assert(test_results['callback_called'] == 6)

    def test_weak_ref(self):

        callback_result = []

        class CallbackCls:
            def __call__(self, *args, **kwargs):
                callback_result.append(1)

        callback_obj = CallbackCls()
        source = WSignalSource("signal1")
        assert(callback_result == [])
        source.callback("signal1", callback_obj)
        source.send_signal("signal1")
        callback_obj = None  # force
        gc.collect()
        source.send_signal("signal1")

        assert(callback_result == [1])


class TestWEventLoopSignalCallback:

    def test(self):
        loop = WEventLoop()
        c = WEventLoopSignalCallback(loop, lambda x, y, z: None)
        assert(isinstance(c, WSignalCallbackProto) is True)

        thread = Thread(target=loop.start_loop)
        thread.start()
        loop.stop_loop()
        thread.join()

    def test_call(self):

        callback_result = []
        def callback_fn(c_source, c_signal, signal_arg = None):
            callback_result.append({"source": c_source, "signal": c_signal, "signal_arg": signal_arg})

        source = WSignalSource("signal1")
        loop = WEventLoop(immediate_stop=False)
        callback = WEventLoopSignalCallback(loop, callback_fn)
        thread = Thread(target=loop.start_loop)
        thread.start()

        try:
            assert(callback_result == [])
            source.callback("signal1", callback)
            source.send_signal("signal1")
            source.send_signal("signal1")
            source.remove_callback("signal1", callback)
            source.send_signal("signal1")
        finally:
            loop.stop_loop()
            thread.join()

        assert(
            callback_result == [
                {"source": source, "signal": "signal1", "signal_arg": None},
                {"source": source, "signal": "signal1", "signal_arg": None}
            ]
        )
