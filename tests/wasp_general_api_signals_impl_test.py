# -*- coding: utf-8 -*-

import weakref
import pytest

from wasp_general.api.signals.proto import WSignalSourceProto, WUnknownSignalException, WSignalWatcherProto
from wasp_general.api.signals.proto import WSignalProxyProto
from wasp_general.api.signals.impl import WSignalSource, anonymous_source, WSignalProxy, WSignal


def test_imports():
	import wasp_general.api.signals
	assert(wasp_general.api.signals.WSignalSource is WSignalSource)
	assert(wasp_general.api.signals.anonymous_source is anonymous_source)
	assert(wasp_general.api.signals.WSignalProxy is WSignalProxy)
	assert(wasp_general.api.signals.WSignal is WSignal)


class TestWSignalSource:

	class SignalSource(WSignalSource):

		@classmethod
		def signals(cls):
			return 'signal1', 'signal2', 'signal3'

	def test(self):
		assert(WSignalSource.signals() == tuple())

		class CorruptedClass(WSignalSource):

			@classmethod
			def signals(cls):
				return 1, 1

		pytest.raises(ValueError, CorruptedClass)

		s = TestWSignalSource.SignalSource()

		assert(isinstance(s, WSignalSource) is True)
		assert(isinstance(s, WSignalSourceProto) is True)

		pytest.raises(WUnknownSignalException, s.send_signal, "unknown_signal")

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

		w = s.watch("signal1")
		assert(isinstance(w, WSignalWatcherProto) is True)

		assert(w.has_next() is False)
		pytest.raises(KeyError, w.next)

		assert(w.wait(timeout=1) is False)

		s.send_signal("signal1")
		assert(w.wait() is True)
		assert(w.next() is None)
		assert(w.wait(timeout=1) is False)

		s.send_signal("signal1", 'zzz')
		assert(w.wait() is True)
		assert(w.next() == 'zzz')

		s.remove_watcher(w)
		pytest.raises(RuntimeError, w.has_next)
		pytest.raises(RuntimeError, w.next)


def test_anonymous_source():
	s1 = anonymous_source()
	assert(isinstance(s1, WSignalSource) is True)
	assert(tuple(s1.signals()) == tuple())

	s2 = anonymous_source('signal1', 'signal2')
	assert(isinstance(s2, WSignalSource) is True)
	s2_signals = tuple(s2.signals())
	assert(len(s2_signals) == 2)
	assert('signal1' in s2_signals)
	assert('signal2' in s2_signals)

	assert(s1.__class__ is not s2.__class__)


class TestWSignalProxy:

	def test_proxy_message(self):
		s = anonymous_source('signal1')

		m = WSignalProxy.ProxiedSignal(s, 'signal1', 'foo')
		assert(isinstance(m, WSignalProxy.ProxiedSignal) is True)
		assert(isinstance(m, WSignalProxyProto.ProxiedSignalProto) is True)
		assert(m.signal_source() == s)
		assert(m.signal_id() == 'signal1')
		assert(m.payload() == 'foo')

		m = WSignalProxy.ProxiedSignal(weakref.ref(s), 'signal1', 'foo')
		assert(m.signal_source()() == s)
		assert(m.signal_id() == 'signal1')
		assert(m.payload() == 'foo')

	def test(self):
		p = WSignalProxy()
		assert(isinstance(p, WSignalProxy) is True)
		assert(isinstance(p, WSignalProxyProto) is True)

		s1 = anonymous_source('signal1', 'signal2', 'signal3')
		s2 = anonymous_source('signal1', 'signal2', 'signal3')

		p.proxy(s1, 'signal1', 'signal3')
		p.proxy(s2, 'signal2', weak_ref=True)

		assert(p.has_next() is False)
		pytest.raises(Exception, p.next)

		s2.send_signal("signal1")
		assert(p.has_next() is False)

		s2.send_signal("signal2", 'zzz')
		assert(p.has_next() is True)
		n = p.next()
		assert(isinstance(n, WSignalProxy.ProxiedSignal) is True)
		assert(isinstance(n.signal_source(), weakref.ReferenceType) is True)
		assert(n.signal_source()() == s2)
		assert(n.signal_id() == 'signal2')
		assert(n.payload() == 'zzz')

		assert(p.wait(timeout=1) is False)

		s1.send_signal("signal1")
		assert(p.wait() is True)
		assert(p.next().payload() is None)
		assert(p.wait(timeout=1) is False)

		s1.send_signal("signal3", 'zzz')
		assert(p.wait() is True)
		assert(p.next().payload() == 'zzz')

		p.stop_proxying(s1, 'signal1')
		assert(p.has_next() is False)
		s1.send_signal('signal1', 1)
		assert(p.has_next() is False)

		pytest.raises(Exception, p.stop_proxying, s1, 'signal3', weak_ref=True)
		s1.send_signal('signal3', 1)
		assert(p.has_next() is True)
		assert(p.next().payload() == 1)


class TestWSignal:

	def test(self):
		signal_foo = WSignal()  # may have any payload
		signal_bar = WSignal(payload_type_spec=int)  # payload must be int
		signal_zzz = WSignal(payload_type_spec=(str, int, float, None))  # optional payload str, int, float
		signal_www = WSignal(payload_type_spec=None)  # payload is not supported

		source = anonymous_source(signal_foo, signal_bar, signal_zzz, signal_www)
		foo_watcher = source.watch(signal_foo)
		bar_watcher = source.watch(signal_bar)

		assert(foo_watcher.has_next() is False)
		assert(bar_watcher.has_next() is False)

		signal_foo(source)
		assert(foo_watcher.has_next() is True)
		assert(foo_watcher.next() is None)
		assert(bar_watcher.has_next() is False)

		pytest.raises(TypeError, signal_bar, source)
		pytest.raises(TypeError, signal_bar, source, '1')
		pytest.raises(TypeError, signal_bar, source, 0.1)
		signal_bar(source, 1)
		assert(foo_watcher.has_next() is False)
		assert(bar_watcher.has_next() is True)
		assert(bar_watcher.next() is 1)

		signal_zzz(source)
		signal_zzz(source, 1)
		signal_zzz(source, 0.1)
		signal_zzz(source, '')
		pytest.raises(TypeError, signal_zzz, source, object())

		signal_foo(source, 1)
		signal_foo(source, object())

		pytest.raises(TypeError, signal_www, source, object())
		signal_www(source)
