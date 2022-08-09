# -*- coding: utf-8 -*-
# wasp_general/api/task/proto.py
#
# Copyright (C) 2016-2019, 2022 the wasp-general authors and contributors
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
import enum
from dataclasses import dataclass
import typing

from wasp_general.verify import verify_type, verify_value

from wasp_general.api.capability import WCapabilitiesHolder, capability, WCapabilitiesHolderMeta
from wasp_general.api.registry import WAPIRegistry
from wasp_general.api.signals import WSignal, WSignalSource, WSignalSourceMeta


class WRequirementsLoopError(Exception):
    """ This exception is raised when there is an attempt to start tasks with mutual dependencies
    """
    pass


class WDependenciesLoopError(Exception):
    """ This exception is raised when there is an attempt to stop tasks with mutual dependencies
    """
    pass


class WTaskStartError(Exception):
    """ This exception is raised when there is an error in starting a task
    """
    pass


class WTaskStopError(Exception):
    """ This exception is raised when there is an error in stopping a task
    """
    pass


class WNoSuchTaskError(Exception):
    """ This exception is raised when there is no requested task (it may be a request to start unknown task or
    request to stop already stopped task)
    """
    pass


class WCapabilitiesSignalsMeta(WSignalSourceMeta, WCapabilitiesHolderMeta):
    """ This metaclass is for classes that may send signals and may have capabilities
    """

    def __init__(cls, name, bases, namespace):
        """ Initialize class with this metaclass

        :param name: same as 'name' in :meth:`.WSignalSourceMeta.__init__` method
        :param bases: same as 'bases' in :meth:`.WSignalSourceMeta.__init__` method
        :param namespace: same as 'namespace' in :meth:`.WSignalSourceMeta.__init__` method
        """
        WSignalSourceMeta.__init__(cls, name, bases, namespace)
        WCapabilitiesHolderMeta.__init__(cls, name, bases, namespace)


@dataclass
class WTaskResult:
    """ This class is used along with a completion signal defining a result of a completed task. In order to check
    whether a task was completed successfully the 'exception' property should be checked

    :note: the 'result' property should be the same as the result from the original :meth:`WTaskProto.start`
    method call
    """
    result: typing.Any = None        # a result of completed record (if any)
    exception: BaseException = None  # an exception raised within a task (if any)


class WTaskProto(WSignalSource, WCapabilitiesHolder, metaclass=WCapabilitiesSignalsMeta):
    """ Basic task prototype. Derived classes must implement the only thing - :meth:`WTaskProto.start`
    """

    task_started = WSignal(None)           # a task started
    task_completed = WSignal(WTaskResult)  # a task completed
    task_stopped = WSignal(None)           # a task stopped
    task_terminated = WSignal(None)        # a task terminated

    @abstractmethod
    def start(self):
        """ Start a task

        :rtype: any
        """
        raise NotImplementedError('This method is abstract')

    @capability
    def stop(self):
        """ Try to stop this task gracefully.

        :raise NotImplementedError: if this task can not be stopped

        :rtype: None
        """
        raise NotImplementedError('The "stop" method is not supported')

    @capability
    def terminate(self):
        """ Try to stop this task at all costs

        :raise NotImplementedError: if this task can not be terminated

        :rtype: None
        """
        raise NotImplementedError('The "terminate" method is not supported')


@enum.unique
class WTaskStopMode(enum.Flag):
    """ Defines a way to stop a task
    """
    stop = enum.auto()       # stop a task gracefully
    terminate = enum.auto()  # terminate a task


# noinspection PyAbstractClass
class WLauncherTaskProto(WTaskProto):
    """ This is a task prototype that may be launched by an :class:`.WLauncherProto` instance. Each type of tasks
    identified by unique string (called tag) this tag must be redefined in derived classes
    """

    __task_tag__ = None  # this is a unique identifier of a task. Must be redefined in derived classes

    @classmethod
    @abstractmethod
    def launcher_task(cls):
        """ Create and return a task that later will be started by a specified launcher (:class:`.WLauncherProto`)

        :rtype: WTaskProto
        """

        raise NotImplementedError('This method is abstract')

    @classmethod
    def requirements(cls):
        """ Return task's tags that are required to start in order this task to work. Or return
        None if this task may be started without any prerequisites

        :rtype: tuple of str | None
        """
        return None


class WLauncherProto(WAPIRegistry):
    """ This launcher starts and tracks :class:`.WLauncherTaskProto` tasks
    """

    @abstractmethod
    @verify_type('strict', task_tag=str)
    @verify_value('strict', task_tag=lambda x: len(x) > 0)
    def is_started(self, task_tag):
        """ Check whether a task with a specified tag has been started

        :param task_tag: tag to check
        :type task_tag: str

        :rtype: bool
        """
        raise NotImplementedError('This method is abstract')

    @abstractmethod
    def started_tasks(self):
        """ Return a generator that will yield tags of tasks that has been started

        :rtype: generator
        """
        raise NotImplementedError('This method is abstract')

    @abstractmethod
    @verify_type('strict', task_tag=str, skip_unresolved=bool)
    @verify_value('strict', task_tag=lambda x: len(x) > 0)
    def start_task(self, task_tag, skip_unresolved=False):
        """ Star a task and its requirements. Return number of tasks that were started

        :param task_tag: tag of task that should be started
        :type task_tag: str

        :param skip_unresolved: whether a task should be started if all the requirements was not met
        :type skip_unresolved: bool

        :raise WNoSuchTaskError: raises if the specified task or it's requirements can not be found
        :raise WTaskStartError: if a task is started already
        :raise WRequirementsLoopError: raises if some tasks require each other

        :rtype: int
        """
        raise NotImplementedError('This method is abstract')

    @abstractmethod
    @verify_type('strict', task_tag=str, stop_mode=WTaskStopMode)
    @verify_value('strict', task_tag=lambda x: len(x) > 0)
    def stop_task(self, task_tag, stop_mode=WTaskStopMode.stop):
        """ Stop a previously started task

        :param task_tag: a tag of task that should be stopped
        :type task_tag: str

        :param stop_mode: whether a task should be stopped gracefully
        :type stop_mode: WTaskStopMode

        :raise WNoSuchTask: raises if task isn't running

        :rtype: None
        """
        raise NotImplementedError('This method is abstract')

    @abstractmethod
    @verify_type('strict', task_tag=str, stop_mode=WTaskStopMode)
    @verify_value('strict', task_tag=lambda x: len(x) > 0)
    def stop_dependent_tasks(self, task_tag, stop_mode=WTaskStopMode.stop):
        """ Stop tasks that are dependent of a specified one or tasks that are dependent of found dependencies.
        And return number of tasks that were stopped

        :param task_tag: task that will be searched in a requirements of running tasks
        :type task_tag: str

        :param stop_mode: whether tasks should be stopped gracefully
        :type stop_mode: WTaskStopMode

        :raise WDependenciesLoopError: raises if there is a mutual dependency between tasks

        :rtype: int
        """
        raise NotImplementedError('This method is abstract')

    @abstractmethod
    @verify_type('strict', stop_mode=WTaskStopMode)
    def all_stop(self, stop_mode=WTaskStopMode.stop):
        """ Stop all the started tasks and return number of tasks that were stopped

        :param stop_mode: whether tasks should be stopped gracefully
        :type stop_mode: WTaskStopMode

        :raise WDependenciesLoop: raises if there is a mutual dependency between tasks

        :rtype: int
        """
        raise NotImplementedError('This method is abstract')


@enum.unique
class WScheduledTaskPostponePolicy(enum.Flag):
    """ This is a policy that describes what should be done with a task if a scheduler won't be able to run
    it (like if the scheduler's limit of running tasks is reached).
    """
    wait = enum.auto()        # will postpone the task to execute it later
    drop = enum.auto()        # drop this task if it can't be executed at the moment
    keep_first = enum.auto()  # if there are postponed tasks, then drop this task
    keep_last = enum.auto()   # if there are postponed tasks, drop them and keep this task


class WScheduleRecordProto(metaclass=ABCMeta):
    """ This class describes a single request that scheduler (:class:`.WSchedulerProto`) should process
    (should start). It has a :class:`.WScheduledTaskProto` task to be started and postpone policy
    (:class:`.WTaskPostponePolicy`)

    Postpone policy is a recommendation for a scheduler and a scheduler can omit it if (for example) a scheduler queue
    is full. 'WScheduledTaskPostponePolicy.keep_first' and 'WScheduledTaskPostponePolicy.keep_last' postpone policies
    (so as simultaneous policy) will be applied to this task and to tasks with the same group id (if it was set).
    """

    @abstractmethod
    def task(self):
        """ Return a task that should be started

        :rtype: WTaskProto
        """
        raise NotImplementedError('This method is abstract')

    # noinspection PyMethodMayBeStatic
    def group_id(self):
        """ Return group id that unite records (in order 'WScheduledTaskPostponePolicy.keep_first' and
        'WScheduledTaskPostponePolicy.keep_last' to work; :meth:`.WScheduleRecordProto.simultaneous_policy` depends on
        this id also)

        :return: group id or None if this record is standalone
        :rtype: str | None
        """
        return None

    # noinspection PyMethodMayBeStatic
    def ttl(self):
        """ Return unix time when this record should be discarded

        :return: unix time in seconds or None if this record can not be expired
        :rtype: int | float | None
        """
        return None

    # noinspection PyMethodMayBeStatic
    def simultaneous_policy(self):
        """ Return how many records with the same group id may be run simultaneously. If non-positive value is return
        then there is no restrictions

        :rtype: int
        """
        return 0

    # noinspection PyMethodMayBeStatic
    def postpone_policy(self):
        """ Return a postpone policy

        :rtype: WScheduledTaskPostponePolicy
        """
        return WScheduledTaskPostponePolicy.wait


class WScheduleSourceProto(WSignalSource):
    """ This class may generate :class:`.WScheduleRecordProto` requests for a scheduler (:class:`.WSchedulerProto`).
    This class decides what tasks and when should be run. When a time is come then this source emits
    a WScheduleSourceProto.task_scheduled signal
    """

    task_scheduled = WSignal(WScheduleRecordProto)   # a new task should be started


@dataclass
class WScheduledTaskResult:
    """ This class is used by scheduler signal defining a result of a completed record
    """
    record: WScheduleRecordProto  # completed record
    task_result: WTaskResult      # a result of completed record


# noinspection PyAbstractClass
class WSchedulerProto(WTaskProto):
    """ Represent a scheduler. A class that is able to execute tasks (:class:`.WScheduleRecordProto`) scheduled
    by sources (:class:`.WScheduleSourceProto`). This class tracks state of tasks that are running
    """

    task_scheduled = WSignal(WScheduleRecordProto)            # a new task received from some source
    scheduled_task_dropped = WSignal(WScheduleRecordProto)    # a scheduled task dropped and would not start
    scheduled_task_postponed = WSignal(WScheduleRecordProto)  # a scheduled task dropped and will start later
    scheduled_task_expired = WSignal(WScheduleRecordProto)    # a scheduled task dropped because of expired ttl
    scheduled_task_started = WSignal(WScheduleRecordProto)    # a scheduled task started
    scheduled_task_completed = WSignal(WScheduledTaskResult)  # a scheduled task completed
    scheduled_task_stopped = WSignal(WScheduleRecordProto)    # a stop request for a scheduled task completed

    @abstractmethod
    @verify_type('strict', schedule_source=WScheduleSourceProto)
    def subscribe(self, schedule_source):
        """ Subscribe this scheduler to a specified source in order to start tasks from it

        :param schedule_source: source of records that should be subscribed
        :type schedule_source: WScheduleSourceProto

        :rtype: None
        """
        raise NotImplementedError('This method is abstract')

    @abstractmethod
    @verify_type('strict', schedule_source=WScheduleSourceProto)
    def unsubscribe(self, schedule_source):
        """ Unsubscribe this scheduler from a specified sources and do process tasks from it

        :param schedule_source: source of records to unsubscribe from
        :type schedule_source: WTaskSourceProto

        :rtype: None
        """
        raise NotImplementedError('This method is abstract')
