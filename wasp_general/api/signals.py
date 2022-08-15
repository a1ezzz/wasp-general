# -*- coding: utf-8 -*-
# wasp_general/api/signals.py
#
# Copyright (C) 2019, 2021-2022 the wasp-general authors and contributors
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

    __wasp_signal_name__ = None

    def __init__(self, *checks):
        """ Create a new (and unique) signal. Every object represent a unique signal

        :param checks: types or callables that signal value (that sent within a signal) must comply. Types are optional
        classes that signal value must be derived from. Callables (functions or methods) check values, each function
        return True if value is suitable and False otherwise
        :type checks: type | callable
        """
        self.__check_types = tuple({x for x in checks if isclass(x)})
        self.__check_functions = tuple({x for x in checks if isfunction(x) or ismethod(x)})

    def check_value(self, value):
        """ Check value and raise exceptions (TypeError or ValueError) if value is invalid

        :param value: value that is checked whether it may or may not be sent with this signal
        :type value: any

        :raises TypeError: if a value's type differ from types that are specified for this signal
        :raises ValueError: if a value's value does not comply with checks functions

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

    def __repr__(self):
        """ Because each signal is unique, it is much simpler to show its identifier in debug messages instead of an
        object's memory location

        :rtype: str
        """
        if self.__wasp_signal_name__:
            return self.__wasp_signal_name__
        return object.__repr__(self)


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
        :type signal: WSignal

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
    """ An example of class that may receive signals (callback signature)
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
    """ This exception may be raised if there was a request to amit an unknown signal. Usually it means that signal
    source is not able to send such signal.
    """
    pass


class WSignalSourceMeta(ABCMeta):
    """ This class helps to manage signals defined for the class
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
                        base_class_attr_value.__wasp_signal_name__ = '{}.{}'.format(base_class.__name__, class_attr)
                    except AttributeError:
                        pass
                if not class_attr_value.__wasp_signal_name__:
                    class_attr_value.__wasp_signal_name__ = '{}.{}'.format(cls.__name__, class_attr)
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

        :type signal: WSignal
        :type signal_value: any
        :rtype: None
        """
        try:
            callbacks = self.__callbacks[signal]
        except KeyError:
            raise WUnknownSignalException('Unknown signal emitted')

        signal.check_value(signal_value)

        for c in callbacks:
            if c is not None:
                c(self, signal, signal_value)

    @verify_type('strict', signal=WSignal)
    @verify_value('strict', callback=lambda x: callable(x))
    def callback(self, signal, callback):
        """ :meth:`.WSignalSourceProto.callback` implementation
        :type signal: WSignal
        :type callback: callable (like WSignalCallbackProto)
        :rtype: None
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

        :type signal: WSignal
        :type callback: callable
        :rtype: None
        """
        try:
            callbacks = self.__callbacks[signal]
            callbacks.remove(callback)
        except KeyError:
            raise WUnknownSignalException('Signal does not have the specified callback')


class WExceptionHandler(metaclass=ABCMeta):
    """ This handler helps to react for exceptions that were caused by calling a callback

    see also :class:`.WEventLoopSignalCallback`, :class:`.WEventLoopCallbacksStorage`
    """

    @abstractmethod
    @verify_type('strict', exception=Exception, source=WSignalSourceProto, signal=WSignal)
    @verify_value('strict', callback=lambda x: callable(x))
    def __call__(self, exception, callback, signal_source, signal, signal_value=None):
        """ Handle a raised exception

        :param exception: exception that was raised
        :type exception: Exception

        :param callback: callback that caused an exception
        :type callback: callable

        :param signal_source: signal source that cause a calling callback that cause an exception
        :type signal_source: WSignalSourceProto

        :param signal: signal that cause a calling callback that cause an exception
        :type signal: WSignal

        :param signal_value: signal value that was passed within a signal
        :type signal_value: any
        """
        raise NotImplementedError('This method is abstract')


class WEventLoopSignalCallback(WSignalCallbackProto):
    """ :class:`.WSignalCallbackProto` implementation that runs callback in a dedicated event loop
    """

    @verify_type('strict', ev_loop=WEventLoop, exc_handler=(WExceptionHandler, None))
    @verify_value('strict', callback=lambda x: callable(x))
    def __init__(self, ev_loop, callback, exc_handler=None):
        """ Create new callback

        :param ev_loop: a loop with which callbacks should be executed
        :type ev_loop: WEventLoop

        :param callback: callback that should be executed
        :type callback: callable (like WSignalCallbackProto or any)

        :param exc_handler: if specified, then this handler will be used to manage exceptions from a callback
        :type exc_handler: WExceptionHandler | None
        """
        WSignalCallbackProto.__init__(self)
        self.__ev_loop = ev_loop
        self.__callback = callback
        self.__exc_handler = exc_handler

    @verify_value('strict', callback=lambda x: callable(x))
    def is_callback(self, callback):
        """ Check that the given callback is the same as this object holds

        :param callback: callback to check
        :type callback: callable

        :rtype: bool
        """
        return self.__callback is callback or (ismethod(callback) and self.__callback == callback)

    @verify_type('strict', signal_source=WSignalSourceProto, signal=WSignal)
    def __call__(self, signal_source, signal, signal_value=None):
        """ :meth:`.WSignalCallbackProto.__call__` implementation

        :type signal_source: WSignalSourceProto
        :type signal: WSignal
        :type signal_value: any
        :rtype: None
        """
        self.__ev_loop.notify(
            functools.partial(self.__exec_callback, signal_source, signal, signal_value=signal_value)
        )

    @verify_type('strict', signal_source=WSignalSourceProto, signal=WSignal)
    def __exec_callback(self, signal_source, signal, signal_value=None):
        """ A real callback for an event loop. This callback may manage all exceptions that were raised by a callback
        Method signature is the same as the `.WSignalCallbackProto.__call__` method

        :type signal_source: WSignalSourceProto
        :type signal: WSignal
        :type signal_value: any
        :rtype: None
        """
        try:
            self.__callback(signal_source, signal, signal_value=signal_value)
        except Exception as e:
            if self.__exc_handler:
                self.__exc_handler(e, self.__callback, signal_source, signal, signal_value=signal_value)
            else:
                raise


class WEventLoopCallbacksStorage:
    """ Sometimes callbacks are generated during a runtime, it means that such callback may be difficult to use because
    signal sources linked with callbacks via weak references. This class helps to store and manage such callbacks.
    Besides that, sometimes it is better to have in a single place where some set of callbacks are stored

    :note: When an original source is removed (garbage collected) callbacks to that source are removed from this
    class also.

    :note: All the callbacks that were registered with this class will be executed in a dedicated event loop
    """

    @verify_type('strict', loop=(WEventLoop, None), exc_handler=(WExceptionHandler, None))
    def __init__(self, loop=None, exc_handler=None):
        """ Create a storage

        :param loop: a loop with which callbacks will be executed, if not set, then a new one is created
        :type loop: WEventLoop | None

        :param exc_handler: handler to manage exceptions (optional)
        :type exc_handler: WExceptionHandler | None
        """
        self.__loop = loop if loop is not None else WEventLoop()
        self.__callbacks = WeakKeyDictionary()
        self.__exc_handler = exc_handler

    def loop(self):
        """ Return a loop with which callbacks are executed

        :rtype: WEventLoop
        """
        return self.__loop

    def clear(self):
        """ Remove all the callbacks that this object holds

        :rtype: None
        """
        self.__callbacks.clear()

    @verify_type('strict', source=WSignalSourceProto, signal=WSignal)
    @verify_value('strict', callback=lambda x: callable(x))
    def register(self, source, signal, callback):
        """ Save a callback and "subscribe" a callback to a signal

        :param source: signal source that emits a signal to handle
        :type source: WSignalSourceProto

        :param signal: signal which should be handled by a callback
        :type signal: WSignal

        :param callback: callback for a signal
        :type callback: callable

        :rtype: None
        """
        callback = WEventLoopSignalCallback(self.__loop, callback, exc_handler=self.__exc_handler)
        source.callback(signal, callback)
        source_callbacks = self.__callbacks.setdefault(source, [])
        source_callbacks.append((signal, callback))

    @verify_type('strict', source=WSignalSourceProto, signal=WSignal)
    @verify_value('strict', callback=lambda x: callable(x))
    def unregister(self, source, signal, callback):
        """ Forget about a callback and "unsubscribe" it from a signal

        :param source: signal source that was "subscribed" before
        :type source: WSignalSourceProto

        :param signal: signal that was "subscribed" before
        :type signal: WSignal

        :param callback: callback to remove
        :type callback: callable

        :raise ValueError: if callback is not linked with the signal

        :rtype: None
        """
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

    @verify_type('strict', source=WSignalSourceProto, source_signal=WSignal)
    @verify_type('strict', proxy=WSignalSourceProto, proxy_signal=WSignal)
    def proxy(self, source, source_signal, proxy, proxy_signal):
        """ Generate, save and return a callback that will resend a signal from other source. Signal value will be
        passed as is

        :param source: original source of a signal
        :type source: WSignalSourceProto

        :param source_signal: original signal
        :type source_signal: WSignal

        :param proxy: signal source that should emit a new signal
        :type proxy: WSignalSourceProto

        :param proxy_signal: a new signal to send from a new source
        :type proxy_signal: WSignal

        :rtype: callable
        """
        def callback_fn(signal_source, signal, signal_value=None):
            proxy.emit(proxy_signal, signal_value)
        callback = WEventLoopSignalCallback(self.__loop, callback_fn, exc_handler=self.__exc_handler)
        self.register(source, source_signal, callback)
        return callback_fn
