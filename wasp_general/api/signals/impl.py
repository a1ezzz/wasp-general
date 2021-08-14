# -*- coding: utf-8 -*-
# wasp_general/signals/signals.py
#
# Copyright (C) 2019, 2021 the wasp-general authors and contributors
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

import weakref
import functools

from wasp_c_extensions.ev_loop import WEventLoop

from wasp_general.verify import verify_type, verify_value

from wasp_general.signals.proto import WSignalSourceProto, WSignalCallbackProto
from wasp_general.signals.proto import WUnknownSignalException


class WSignalSource(WSignalSourceProto):
    """ :class:`.WSignalSourceProto` implementation
    """

    @verify_type('strict', signal_names=str)
    def __init__(self, *signal_names):
        """ Create new signal source

        :param signal_names: names of signals that this object may send
        :type signal_names: str
        """

        WSignalSourceProto.__init__(self)
        self.__signal_names = signal_names
        self.__callbacks = {x: weakref.WeakSet() for x in signal_names}

    @verify_type('strict', signal_name=str)
    def send_signal(self, signal_name, signal_args=None):
        """ :meth:`.WSignalSourceProto.send_signal` implementation
        """
        try:
            for callback in self.__callbacks[signal_name]:
                if callback is not None:
                    callback(self, signal_name, signal_args)
        except KeyError:
            raise WUnknownSignalException('Unknown signal "%s"' % signal_name)

    def signals(self):
        """ :meth:`.WSignalSourceProto.signals` implementation
        """
        return self.__signal_names

    @verify_type('strict', signal_name=str)
    @verify_value('strict', callback=lambda x: callable(x))
    def callback(self, signal_name, callback):
        """ :meth:`.WSignalSourceProto.callback` implementation
        """
        self.__callbacks[signal_name].add(callback)

    @verify_type('strict', signal_name=str)
    @verify_value('strict', callback=lambda x: callable(x))
    def remove_callback(self, signal_name, callback):
        """ :meth:`.WSignalSourceProto.remove_callback` implementation
        """
        try:
            self.__callbacks[signal_name].remove(callback)
        except KeyError:
            raise ValueError('Signal "%s" does not have the specified callback' % signal_name)


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

    @verify_type('strict', signal_source=WSignalSourceProto, signal_name=str)
    def __call__(self, signal_source, signal_name, signal_arg=None):
        """ :meth:`.WSignalCallbackProto.__call__` implementation
        """
        self.__ev_loop.notify(functools.partial(self.__callback, signal_source, signal_name, signal_arg=signal_arg))
