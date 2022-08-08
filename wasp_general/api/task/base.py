# -*- coding: utf-8 -*-
# wasp_general/api/task/base.py
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

from decorator import decorator
import enum
from threading import Lock

from wasp_general.api.capability import WCapabilityDescriptor
from wasp_general.thread import acquire_lock
from wasp_general.verify import verify_type, verify_value

from wasp_general.api.task.proto import WTaskResult, WTaskProto, WTaskStartError, WTaskStopError


# noinspection PyAbstractClass
class WSingleStateTask(WTaskProto):
    """ This class helps to implement a basic task. Response for signals routine and "locks" start, stop and terminate
    methods in order to protect simultaneous calls
    """

    @enum.unique
    class TaskState(enum.Flag):
        """ A possible states of a :class:`WSingleStateTask` objects. Values are corresponding signals
        """
        stopped = enum.auto()     # Task is stopped
        terminated = enum.auto()  # Task is terminated
        started = enum.auto()     # Task is started
        completed = enum.auto()   # Task is completed

    @verify_type('strict', detachable=bool)
    def __init__(self, detachable=False):
        """ Create a new task

        :param detachable: When the 'detachable' is True it means that the :meth:`. WTaskProto.start` method does not
        return a real task result, but instead start a job with a separate process/thread/async. When the 'detachable'
        is False then an exception raised within the :meth:`. WTaskProto.start` method (or it's result) will be sent
        with the 'WTaskProto.task_completed' signal
        :type detachable: bool
        """
        WTaskProto.__init__(self)
        self.__detachable = detachable
        self.__lock = Lock()
        self.__state = WSingleStateTask.TaskState.stopped

    def __getattribute__(self, item):
        """ Decorate basic WTaskProto methods and emit appropriate signals
        """
        result = WTaskProto.__getattribute__(self, item)
        if item == 'start' and not isinstance(result, WCapabilityDescriptor):
            return self.__decorate_start_call(result)
        if item == 'stop' and not isinstance(result, WCapabilityDescriptor):
            return self.__decorate_stop_call(result, WSingleStateTask.TaskState.stopped)
        if item == 'terminate' and not isinstance(result, WCapabilityDescriptor):
            return self.__decorate_stop_call(result, WSingleStateTask.TaskState.terminated)
        return result

    @verify_value('strict', decorated_fn=lambda x: callable(x))
    def __decorate_start_call(self, decorated_fn):
        """ Decorate the :meth:`. WTaskProto.start` method
        """
        def decorator_fn(original_fn, *args, **kwargs):
            if acquire_lock(self.__lock, timeout=-1):
                try:
                    self._switch_task_state(WSingleStateTask.TaskState.started)
                    result = original_fn(*args, **kwargs)
                except Exception as e:
                    if not self.__detachable:
                        self._switch_task_state(
                            WSingleStateTask.TaskState.completed, task_result=WTaskResult(exception=e)
                        )
                    raise
                else:
                    if not self.__detachable:
                        self._switch_task_state(
                            WSingleStateTask.TaskState.completed, task_result=WTaskResult(result=result)
                        )
                    return result
                finally:
                    self.__lock.release()
            raise WTaskStartError('Unable to start task because other start/stop/terminate request in progress')
        return decorator(decorator_fn)(decorated_fn)

    @verify_type('strict', state=TaskState)
    @verify_value('strict', decorated_fn=lambda x: callable(x))
    def __decorate_stop_call(self, decorated_fn, state):
        """ Decorate the :meth:`. WTaskProto.stop` or the :meth:`. WTaskProto.terminate` methods
        """

        def decorator_fn(original_fn, *args, **kwargs):

            if acquire_lock(self.__lock, timeout=-1):
                try:
                    result = original_fn(*args, **kwargs)
                    self._switch_task_state(state)
                    return result
                finally:
                    self.__lock.release()
            raise WTaskStopError(
                'Unable to stop/terminate task because other start/stop/terminate request in progress'
            )
        return decorator(decorator_fn)(decorated_fn)

    def task_state(self):
        """ Return current state of this task

        :rtype: WSingleStateTask.TaskState
        """
        return self.__state

    @verify_type('strict', new_state=TaskState, task_result=(WTaskResult, None))
    def _switch_task_state(self, new_state, task_result=None):
        """ Switch current status and send a signal

        :param new_state: new status
        :type new_state: WSingleStateTask.State

        :param task_result: a result of the 'WSingleStateTask.TaskState.completed' state. In case of stopped/terminated
        states this parameter is ignored
        :type task_result: WTaskResult

        :rtype: None
        """

        if self.__state != new_state:
            self.__state = new_state

            if self.__state == WSingleStateTask.TaskState.stopped:
                self.emit(WSingleStateTask.task_stopped)
            if self.__state == WSingleStateTask.TaskState.terminated:
                self.emit(WSingleStateTask.task_terminated)
            elif self.__state == WSingleStateTask.TaskState.started:
                self.emit(WSingleStateTask.task_started)
            elif self.__state == WSingleStateTask.TaskState.completed:
                self.emit(WSingleStateTask.task_completed, task_result)
