# -*- coding: utf-8 -*-
# wasp_general/api/signals.py
#
# Copyright (C) 2019, 2021, 2022 the wasp-general authors and contributors
# <see AUTHORS file>
#
# This file is part of wasp-general.
#
# Wasp-general is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Wasp-general is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with wasp-general.  If not, see <http://www.gnu.org/licenses/>.

from abc import ABCMeta, abstractmethod
import functools
from inspect import isclass, isfunction, ismethod
from weakref import WeakSet, WeakKeyDictionary

from wasp_c_extensions.ev_loop import WEventLoop

from wasp_general.verify import verify_type, verify_value


class WSignal:
    """ A signal that may be sent within wasp_general.api.signals methods
    """

    def __init__(self, *checks):
        """ Create a new (and unique) signal. Every object represent a unique signal

        :param checks: types or callables that signal value (that sent with a signal) must comply. Types are optional
        classes that signal value must be derivied from. Callables (functions or methods) checks values, each function
        return True if value is suitable and False otherwise
        :type checks: type | callable
        """
        self.__check_types = tuple({x for x in checks if isclass(x)})
        self.__check_functions = tuple({x for x in checks if isfunction(x) or ismethod(x)})

    def check_value(self, value):
        """ Check value and raise exceptions (TypeError or ValueError) is value is invalid

        :param value: value that is checked whether it may or may not be sent with this signal
        :type value: any

        :rtype: None
        """
        if self.__check_types and isinstance(value, self.__check_types) is False:
            raise TypeError('Signal value is invalid (type mismatch)')
        for c in self.__check_functions:
            if not c(value):
                raise ValueError('Signal value is invalid (value mismatch)')

    def __hash__(self):
        """ Hash function in order to use this class as a dict key
        :rtype: int
        """
        return id(self)

    def __eq__(self, other):
        """ Comparison function in order to use this class as a dict key
        :rtype: bool
        """
        return id(other) == id(self)


class WSignalSourceProto(metaclass=ABCMeta):
    """ An entry class for an object that sends signals. Every callback is saved as a 'weak' reference. So in most
    cases in order to stop executing callback it is sufficient just to discard all callback's references
    """

    @abstractmethod
    @verify_type('strict', signal=WSignal)
    def emit(self, signal, signal_value=None):
        """ Send a signal from this object

        :param signal: a signal (an object) to send
        :type signal: WSignal

        :param signal_value: a signal argument that may be sent within a signal (this value should be checked first)
        :type signal_value: any

        :rtype: None
        """
        raise NotImplementedError('This method is abstract')

    @abstractmethod
    @verify_type('strict', signal=WSignal)
    @verify_value('strict', callback=lambda x: callable(x))
    def callback(self, signal, callback):
        """ Register a callback that will be executed when new signal is sent

        :param signal: signal that will trigger a callback
        :type signal:WSignal

        :param callback: callback that must be executed
        :type callback: callable (like WSignalCallbackProto)

        :rtype: None
        """
        raise NotImplementedError('This method is abstract')

    @abstractmethod
    @verify_type('strict', signal=WSignal)
    @verify_value('strict', callback=lambda x: callable(x) and not ismethod(x))
    def remove_callback(self, signal, callback):
        """ Unregister the specified callback and prevent it to be executed when new signal is sent

        :param signal: signal that should be avoided by the specified callback
        :type signal: WSignal

        :param callback: callback that should be unregistered
        :type callback: callable

        :rtype: None
        """
        raise NotImplementedError('This method is abstract')


class WSignalCallbackProto(metaclass=ABCMeta):
    """ An example of class that may receive signals
    """

    @abstractmethod
    @verify_type('strict', signal_source=WSignalSourceProto, signal=WSignal)
    def __call__(self, signal_source, signal, signal_value=None):
        """ A callback that will be called when a signal is sent

        :param signal_source: origin of a signal
        :type signal_source: WSignalSourceProto

        :param signal: a signal that was sent
        :type signal: WSignal

        :param signal_value: any argument that you want to pass with the specified signal. A specific signal
        may relay on this argument and may raise an exception if unsupported value is spotted
        :type signal_value: any

        :rtype: None
        """
        raise NotImplementedError('This method is abstract')


class WUnknownSignalException(Exception):
    """ This exception may be raised if there was a request to signal source with unsupported signal name. Usually it
    means that signal source is not able to send such signal.
    """
    pass


class WSignalSourceMeta(ABCMeta):
    """ This class helps to track signals defined for the class
    """

    def __new__(mcs, name, bases, namespace, **kwargs):
        """ Generate new class with this metaclass

        :param name: same as 'name' in :meth:`.ABCMeta.__init__` method
        :param bases: same as 'bases' in :meth:`.ABCMeta.__init__` method
        :param namespace: same as 'namespace' in :meth:`.ABCMeta.__init__` method
        """
        obj = ABCMeta.__new__(mcs, name, bases, namespace, **kwargs)
        obj.__wasp_signals__ = set()
        return obj

    def __init__(cls, name, bases, namespace):
        """ Initialize class with this metaclass

        :param name: same as 'name' in :meth:`.ABCMeta.__init__` method
        :param bases: same as 'bases' in :meth:`.ABCMeta.__init__` method
        :param namespace: same as 'namespace' in :meth:`.ABCMeta.__init__` method
        """
        ABCMeta.__init__(cls, name, bases, namespace)

        for class_attr in dir(cls):
            class_attr_value = ABCMeta.__getattribute__(cls, class_attr)
            if isinstance(class_attr_value, WSignal) is True:
                for base_class in bases:
                    try:
                        base_class_attr_value = ABCMeta.__getattribute__(base_class, class_attr)
                        if class_attr_value != base_class_attr_value:
                            raise TypeError(
                                'Signals may not be overridden! Duplicated signal (%s) spotted for the class "%s"'
                                ' (found at the base class %s)'
                                % (class_attr, str(cls), str(base_class))
                            )
                    except AttributeError:
                        pass
                cls.__wasp_signals__.add(class_attr_value)


class WSignalSource(WSignalSourceProto, metaclass=WSignalSourceMeta):
    """ :class:`.WSignalSourceProto` implementation
    """

    def __init__(self):
        """ Create new signal source
        """

        WSignalSourceProto.__init__(self)
        self.__callbacks = {x: WeakSet() for x in self.__class__.__wasp_signals__}

    @verify_type('strict', signal=WSignal)
    def emit(self, signal, signal_value=None):
        """ :meth:`.WSignalSourceProto.emit` implementation
        """
        try:
            callbacks = self.__callbacks[signal]
        except KeyError:
            raise WUnknownSignalException('Unknown signal emitted')

        try:
            signal.check_value(signal_value)
        except TypeError:
            raise TypeError('Unable to send a signal. Signal type is invalid')
        except ValueError:
            raise ValueError('Unable to send a signal. Signal value is invalid')

        for c in callbacks:
            if c is not None:
                c(self, signal, signal_value)

    @verify_type('strict', signal=WSignal)
    @verify_value('strict', callback=lambda x: callable(x))
    def callback(self, signal, callback):
        """ :meth:`.WSignalSourceProto.callback` implementation
        """
        try:
            self.__callbacks[signal].add(callback)
            if callback not in self.__callbacks[signal]:
                raise ValueError('Unable to save a callback. Callback may be a bounded method, which is unsupported')
        except KeyError:
            raise WUnknownSignalException('Unknown signal subscribed')

    @verify_type('strict', signal=WSignal)
    @verify_value('strict', callback=lambda x: callable(x))
    def remove_callback(self, signal, callback):
        """ :meth:`.WSignalSourceProto.remove_callback` implementation
        """
        try:
            callbacks = self.__callbacks[signal]
            callbacks.remove(callback)
        except KeyError:
            raise ValueError('Signal does not have the specified callback')


class WEventLoopSignalCallback(WSignalCallbackProto):
    """ :class:`.WSignalCallbackProto` implementation that runs callback in a dedicated loop
    """

    @verify_type('strict', ev_loop=WEventLoop)
    @verify_value('strict', callback=lambda x: callable(x))
    def __init__(self, ev_loop, callback):
        """ Create new callback

        :param ev_loop: a loop with which callbacks should be executed
        :type ev_loop: WEventLoop

        :param callback: callback that should be executed
        :type callback: callable (like WSignalCallbackProto or any)
        """
        WSignalCallbackProto.__init__(self)
        self.__ev_loop = ev_loop
        self.__callback = callback

    def is_callback(self, callback):
        return self.__callback is callback or (ismethod(callback) and self.__callback == callback)

    @verify_type('strict', signal_source=WSignalSourceProto, signal=WSignal)
    def __call__(self, signal_source, signal, signal_value=None):
        """ :meth:`.WSignalCallbackProto.__call__` implementation
        """
        self.__ev_loop.notify(functools.partial(self.__callback, signal_source, signal, signal_value=signal_value))


class WEventLoopCallbacks:

    def __init__(self, loop=None):
        self.__loop = loop if loop is not None else WEventLoop()
        self.__callbacks = WeakKeyDictionary()

    def loop(self):
        return self.__loop

    def clear(self):
        self.__callbacks.clear()

    def register(self, source, signal, callback):
        callback = WEventLoopSignalCallback(self.__loop, callback)
        source.callback(signal, callback)
        source_callbacks = self.__callbacks.setdefault(source, [])
        source_callbacks.append((signal, callback))

    def unregister(self, source, signal, callback):
        source_callbacks = self.__callbacks.get(source)
        if source_callbacks:
            for i, callback_pair in enumerate(source_callbacks):
                stored_signal, stored_event_callback = callback_pair
                if stored_signal is signal and stored_event_callback.is_callback(callback):
                    source.remove_callback(signal, stored_event_callback)
                    source_callbacks.pop(i)
                    if not source_callbacks:
                        self.__callbacks.pop(source)
                    return
        raise ValueError('Callback was not found')

    def proxy(self, source, source_signal, proxy, proxy_signal):
        def callback_fn(signal_source, signal, signal_value=None):
            proxy.emit(proxy_signal, signal_value)
        callback = WEventLoopSignalCallback(self.__loop, callback_fn)
        self.register(source, source_signal, callback)
