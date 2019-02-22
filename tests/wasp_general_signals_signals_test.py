# -*- coding: utf-8 -*-

import weakref
import pytest

from wasp_general.signals.proto import WSignalSourceProto, WUnknownSignalException, WSignalWatcherProto
from wasp_general.signals.proto import WSignalProxyProto
from wasp_general.signals.signals import WSignalSource, WSignalProxy


class TestWSignalSource:

	def test(self):
		s = WSignalSource("signal1", "signal2")

		assert(isinstance(s, WSignalSource) is True)
		assert (isinstance(s, WSignalSourceProto) is True)

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

		w = s.watch("signal1")
		assert(isinstance(w, WSignalWatcherProto) is True)

		assert(w.has_next() is False)
		pytest.raises(Exception, w.next)

		assert(w.wait(timeout=1) is False)

		s.send_signal("signal1")
		assert(w.wait() is True)
		assert(w.next() is None)
		assert(w.wait(timeout=1) is False)

		s.send_signal("signal1", 'zzz')
		assert(w.wait() is True)
		assert(w.next() == 'zzz')

		s.remove_watcher(w)
		pytest.raises(Exception, w.has_next)
		pytest.raises(Exception, w.next)


class TestWSignalProxy:

	def test_proxy_message(self):
		s = WSignalSource('signal1')

		m = WSignalProxy.ProxiedSignal(s, 'signal1', 'foo')
		assert(isinstance(m, WSignalProxy.ProxiedSignal) is True)
		assert(isinstance(m, WSignalProxyProto.ProxiedSignalProto) is True)
		assert(m.signal_source() == s)
		assert(m.signal_name() == 'signal1')
		assert(m.signal_arg() == 'foo')

		m = WSignalProxy.ProxiedSignal(weakref.ref(s), 'signal1', 'foo')
		assert(m.signal_source()() == s)
		assert(m.signal_name() == 'signal1')
		assert(m.signal_arg() == 'foo')

	def test(self):
		p = WSignalProxy()
		assert(isinstance(p, WSignalProxy) is True)
		assert(isinstance(p, WSignalProxyProto) is True)

		s1 = WSignalSource('signal1', 'signal2', 'signal3')
		s2 = WSignalSource('signal1', 'signal2', 'signal3')

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
		assert(n.signal_name() == 'signal2')
		assert(n.signal_arg() == 'zzz')

		assert(p.wait(timeout=1) is False)

		s1.send_signal("signal1")
		assert(p.wait() is True)
		assert(p.next().signal_arg() is None)
		assert(p.wait(timeout=1) is False)

		s1.send_signal("signal3", 'zzz')
		assert(p.wait() is True)
		assert(p.next().signal_arg() == 'zzz')

		p.stop_proxying(s1, 'signal1')
		assert(p.has_next() is False)
		s1.send_signal('signal1', 1)
		assert(p.has_next() is False)

		pytest.raises(Exception, p.stop_proxying, s1, 'signal3', weak_ref=True)
		s1.send_signal('signal3', 1)
		assert(p.has_next() is True)
		assert(p.next().signal_arg() == 1)
