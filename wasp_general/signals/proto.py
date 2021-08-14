# -*- coding: utf-8 -*-
# wasp_general/signals/proto.py
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

from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type, verify_value


class WSignalSourceProto(metaclass=ABCMeta):
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
        :type callback: callable (like WSignalCallbackProto)

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


class WSignalCallbackProto(metaclass=ABCMeta):
    """ An example of class that may receive signals
    """

    @abstractmethod
    @verify_type('strict', signal_source=WSignalSourceProto, signal_name=str)
    def __call__(self, signal_source, signal_name, signal_arg=None):
        """ A callback that will be called when a signal is sent

        :param signal_source: origin of a signal
        :type signal_source: WSignalSourceProto

        :param signal_name: name of a signal that was send
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
