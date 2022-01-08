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
import enum
from abc import ABCMeta, abstractmethod
import functools
import weakref

from wasp_c_extensions.ev_loop import WEventLoop

from wasp_general.verify import verify_type, verify_value, verify_subclass


class ASignalSourceProto(metaclass=ABCMeta):
    """ An entry class for an object that sends signals. Every callback is saved as a 'weak' reference. So in most
    cases in order to stop executing callback it is sufficient just to discard all callbacks references
    """

    @abstractmethod
    def signals(self):
        """ Return names of signals that may be sent

        :rtype: tuple of str
        """
        raise NotImplementedError('This method is abstract')

    @abstractmethod
    @verify_type('strict', signal_name=str)
    def send_signal(self, signal_name, signal_arg=None):
        """ Send a signal from this object

        :param signal_name: a name of a signal to send
        :type signal_name: str

        :param signal_arg: a signal argument that may be send with a signal
        :type signal_arg: any

        :rtype: None
        """
        raise NotImplementedError('This method is abstract')

    @abstractmethod
    @verify_type('strict', signal_name=str)
    @verify_value('strict', callback=lambda x: callable(x))
    def callback(self, signal_name, callback):
        """ Register a callback that will be executed when new signal is sent

        :param signal_name: signal that will trigger a callback
        :type signal_name: str

        :param callback: callback that must be executed
        :type callback: callable (like ASignalCallbackProto)

        :rtype: None
        """
        raise NotImplementedError('This method is abstract')

    @abstractmethod
    @verify_type('strict', signal_name=str)
    @verify_value('strict', callback=lambda x: callable(x))
    def remove_callback(self, signal_name, callback):
        """ Unregister the specified callback and prevent it to be executed when new signal is sent

        :param signal_name: signal that should be avoided
        :type signal_name: str

        :param callback: callback that should be unregistered
        :type callback: callable

        :rtype: None
        """
        raise NotImplementedError('This method is abstract')


class ASignalCallbackProto(metaclass=ABCMeta):
    """ An example of class that may receive signals
    """

    @abstractmethod
    @verify_type('strict', signal_source=ASignalSourceProto, signal_name=str)
    def __call__(self, signal_source, signal_name, signal_arg=None):
        """ A callback that will be called when a signal is sent

        :param signal_source: origin of a signal
        :type signal_source: ASignalSourceProto

        :param signal_name: name of a signal that was sent
        :type signal_name: str

        :param signal_arg: any argument that you want to pass with the specified signal. A specific signal
        may relay on this argument and may raise an exception if unsupported value is spotted
        :type signal_arg: any

        :rtype: None
        """
        raise NotImplementedError('This method is abstract')


class WUnknownSignalException(Exception):
    """ This exception may be raised if there was a request to signal source with unsupported signal name. Usually it
    means that signal source is not able to send such signal.
    """
    pass


class WSignalSource(ASignalSourceProto):
    """ :class:`.ASignalSourceProto` implementation
    """

    @verify_type('strict', signal_names=str)
    def __init__(self, *signal_names):
        """ Create new signal source

        :param signal_names: names of signals that this object may send
        :type signal_names: str
        """

        ASignalSourceProto.__init__(self)
        self.__signal_names = signal_names
        self.__callbacks = {x: weakref.WeakSet() for x in signal_names}

    @verify_type('strict', signal_name=str)
    def send_signal(self, signal_name, signal_arg=None):
        """ :meth:`.ASignalSourceProto.send_signal` implementation
        """
        try:
            for callback in self.__callbacks[signal_name]:
                if callback is not None:
                    callback(self, signal_name, signal_arg)
        except KeyError:
            raise WUnknownSignalException('Unknown signal "%s"' % signal_name)

    def signals(self):
        """ :meth:`.ASignalSourceProto.signals` implementation
        """
        return self.__signal_names

    @verify_type('strict', signal_name=str)
    @verify_value('strict', callback=lambda x: callable(x))
    def callback(self, signal_name, callback):
        """ :meth:`.ASignalSourceProto.callback` implementation
        """
        self.__callbacks[signal_name].add(callback)

    @verify_type('strict', signal_name=str)
    @verify_value('strict', callback=lambda x: callable(x))
    def remove_callback(self, signal_name, callback):
        """ :meth:`.ASignalSourceProto.remove_callback` implementation
        """
        try:
            self.__callbacks[signal_name].remove(callback)
        except KeyError:
            raise ValueError('Signal "%s" does not have the specified callback' % signal_name)


class WEventLoopSignalCallback(ASignalCallbackProto):
    """ :class:`.ASignalCallbackProto` implementation that runs callback in a dedicated loop
    """

    @verify_type('strict', ev_loop=WEventLoop)
    @verify_value('strict', callback=lambda x: callable(x))
    def __init__(self, ev_loop, callback):
        """ Create new callback

        :param ev_loop: a loop with which callbacks should be executed
        :type ev_loop: WEventLoop

        :param callback: callback that should be executed
        :type callback: callable (like ASignalCallbackProto or any)
        """
        ASignalCallbackProto.__init__(self)
        self.__ev_loop = ev_loop
        self.__callback = callback

    @verify_type('strict', signal_source=ASignalSourceProto, signal_name=str)
    def __call__(self, signal_source, signal_name, signal_arg=None):
        """ :meth:`.ASignalCallbackProto.__call__` implementation
        """
        self.__ev_loop.notify(functools.partial(self.__callback, signal_source, signal_name, signal_arg=signal_arg))


class WTypedSignalSource(WSignalSource):
    """ :class:`.ASignalSourceProto` implementation

    This implementation restricts signal's argument that may be sent
    """

    @verify_subclass('strict', signals=enum.Enum)
    def __init__(self, signals):
        """ Create new signal source

        :param signals: allowed signals (values are types that are allowed within signals)
        :type signals: enum.Enum
        """
        WSignalSource.__init__(self, *(x.name for x in signals))
        self.__signals = signals

    def send_signal(self, signal_name, signal_arg=None):
        """ :meth:`.ASignalSourceProto.send_signal` implementation

        :param signal_name: name of a signal that was sent
        :type signal_name: str | enum.Enum

        :param signal_arg: same as signal_arg in the :meth:`.ASignalSourceProto.send_signal` method
        :type signal_arg: any
        """

        if isinstance(signal_name, self.__signals):
            signal_name = signal_name.name
        signal_type = self.__signals[signal_name].value

        if signal_type is None:
            if signal_arg is not None:
                raise TypeError('The "%s" signal does not allowed any arguments' % signal_name)
        elif isinstance(signal_arg, signal_type) is False:
            raise TypeError(
                'The "%s" signal require argument that is "%s" type, but "%s" is given' %
                (signal_name, signal_type.__name__, signal_arg.__class__.__name__)
            )
        return WSignalSource.send_signal(self, signal_name, signal_arg=signal_arg)
