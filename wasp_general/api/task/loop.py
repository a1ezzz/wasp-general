# -*- coding: utf-8 -*-
# wasp_general/api/task/loop.py
#
# Copyright (C) 2022 the wasp-general authors and contributors
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

from wasp_general.verify import verify_type
from wasp_general.api.task.proto import WTaskProto, WTaskResult
from wasp_general.api.task.thread import WThreadTask
from wasp_c_extensions.ev_loop import WEventLoop
from wasp_general.platform import WPlatformThreadEvent


class WEventLoopTask(WTaskProto):
    """ A simple task that runs even loop inside
    """

    @verify_type('strict', loop=(WEventLoop, None))
    def __init__(self, loop=None):
        """ Create a new task

        :param loop: a loop that will start. If not defined a new loop is created
        :type loop: WEventLoop | None
        """
        WTaskProto.__init__(self)
        self.__loop = loop if loop else WEventLoop()
        self.__start_event = WPlatformThreadEvent()
        self.__stop_event = WPlatformThreadEvent()

    def event_loop(self):
        """ Return a loop that this task will run

        :rtype: WEventLoop
        """
        return self.__loop

    def start(self):
        """ :meth:`.WTaskProto.start` implementation
        :rtype: None
        """
        self.__stop_event.clear()
        self.emit(WTaskProto.task_started)
        self.__loop.start_loop()
        self.__stop_event.set()
        self.emit(WTaskProto.task_completed, WTaskResult())
        self.emit(WTaskProto.task_stopped)

    def stop(self):
        """ :meth:`.WTaskProto.stop` implementation
        :rtype: None
        """
        self.__loop.stop_loop()
        self.__stop_event.wait()

    @verify_type(timeout=(int, float, None))
    def await_loop_start(self, timeout=None):
        """ Wait for a loop to start

        :param timeout: a timeout to wait for a loop to start (None for a forever waiting)
        :type timeout: int | float | None

        :rtype: None

        :note: Not thread safe!
        """
        self.__start_event.clear()
        self.__loop.notify(self.__start_event.set)
        self.__start_event.wait(timeout=timeout)
        if not self.__loop.is_started():
            raise RuntimeError('Loop is not started')


class WEventLoopThread(WThreadTask):
    """ A shortcut for a threaded task that runs :class:`.WEventLoopTask`
    """

    @verify_type('strict', loop=(WEventLoop, None), thread_name=(str, None), join_timeout=(int, float, None))
    def __init__(self, loop=None, thread_name=None, join_timeout=None):
        """ Create a threaded task

        :param loop: a loop with which a :class:`.WEventLoopTask` object should be created
        :type loop: WEventLoop | None

        :param thread_name: the same as 'thread_name' in the :meth:`.WThreadTask.__init__` method
        :type thread_name: str | None

        :param join_timeout: the same as 'join_timeout' in the :meth:`.WThreadTask.__init__` method
        :type join_timeout: int | float | None
        """
        WThreadTask.__init__(
            self, WEventLoopTask(loop=loop), thread_name=thread_name, join_timeout=join_timeout
        )
