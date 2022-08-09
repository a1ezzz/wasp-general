# -*- coding: utf-8 -*-
# wasp_general/api/task/launcher.py
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

import functools

from wasp_general.verify import verify_value, verify_type, verify_subclass
from wasp_general.thread import WCriticalResource
from wasp_general.api.registry import WAPIRegistryProto, register_api
from wasp_general.api.task.proto import WLauncherProto, WTaskProto, WLauncherTaskProto, WTaskStopMode, WTaskStartError
from wasp_general.api.task.proto import WNoSuchTaskError, WRequirementsLoopError, WDependenciesLoopError


class WLauncher(WLauncherProto, WCriticalResource):
    """ Thread safe :class:`.WLauncherProto` class implementation
    """

    __critical_section_timeout__ = 5
    """ Timeout for capturing a lock for critical sections
    """

    @verify_type('strict', registry=WAPIRegistryProto)
    def __init__(self, registry):
        """ Create a new launcher

        :param registry: a linked registry that will be used for requesting a task class by it's tag
        :type registry: WTaskRegistryProto
        """
        WLauncherProto.__init__(self)
        WCriticalResource.__init__(self)
        self.__started_tasks = {}
        self.__registry = registry

    @verify_type('strict', task_tag=str)
    @verify_value('strict', task_tag=lambda x: len(x) > 0)
    def is_started(self, task_tag):
        """ :meth:`.WLauncherProto.is_started` method implementation

        :type task_tag: str

        :rtype: bool
        """
        return task_tag in self.__started_tasks

    def started_tasks(self):
        """ :meth:`.WLauncherProto.started_tasks` method implementation
        :rtype: generator
        """
        return (x for x in self.__started_tasks.copy().keys())

    def __iter__(self):
        """ Return generator that will iterate over all tasks
        :rtype: generator
        """
        return self.started_tasks()

    def __len__(self):
        """ Return number of running tasks

        :rtype: int
        """
        return len(self.__started_tasks)

    def __contains__(self, item):
        """ Check that a specified task is running

        :param item: task tag to check
        :type item: str

        :rtype: bool
        """
        return item in self.__started_tasks

    @verify_type('strict', task_tag=str, skip_unresolved=bool)
    @verify_value('strict', task_tag=lambda x: len(x) > 0)
    def __single_task_requirements(self, task_tag, skip_unresolved=False):
        """ Check requirements of a single task

        :param task_tag: task to check
        :type task_tag: str

        :param skip_unresolved: whether to raise the WNoSuchTaskError exception if task wasn't found or not
        :type skip_unresolved: bool

        :raise WNoSuchTask: raises if the specified task can not be found

        :return: Return tuple of tags that haven't been started yet
        :rtype: tuple
        """
        if self.__registry.has(task_tag) is False:
            if skip_unresolved is True:
                return False, set()
            raise WNoSuchTaskError('Unable to find a required task with tag "%s"', task_tag)

        task_cls = self.__registry.get(task_tag)
        task_req = task_cls.requirements()
        if task_req is None:
            task_req = []

        return True, {x for x in task_req if (x not in self.__started_tasks)}

    @verify_type('strict', task_tag=str, skip_unresolved=bool)
    @verify_value('strict', task_tag=lambda x: len(x) > 0)
    def __recursive_requirements(self, task_tag, skip_unresolved=False):
        """ Return ordered task's requirements. Tags order allows to be confident that all the requirements
        are met before starting following tasks

        note: No mutual dependencies are allowed

        :param task_tag: same as 'task_tag' in :meth:`.WLauncherProto.start_task`
        :type task_tag: str

        :param skip_unresolved: same as 'skip_unresolved' in :meth:`.WLauncherProto.start_task`
        :type skip_unresolved: bool

        :rtype: tuple

        :raise WNoSuchTask: raises if requirements for a task can not be found
        :raise WRequirementsLoopError: raises if some tasks require each other
        """

        task_found, raw_reqs = self.__single_task_requirements(task_tag, skip_unresolved=skip_unresolved)
        result_reqs = []

        while len(raw_reqs):  # there are some requirements that needs to be checked
            next_raw_reqs = set()

            for iter_task_tag in raw_reqs:
                iter_task_found, iter_task_req = self.__single_task_requirements(
                    iter_task_tag, skip_unresolved=skip_unresolved
                )
                iter_task_req = list(filter(lambda x: x not in result_reqs, iter_task_req))  # skip stopped
                # requirements that are known already

                if iter_task_found:
                    if not iter_task_req:  # there are no unresolved requirements
                        result_reqs.append(iter_task_tag)
                        if iter_task_tag in next_raw_reqs:
                            next_raw_reqs.remove(iter_task_tag)
                    else:  # we should check as this task as it's requirements
                        next_raw_reqs.add(iter_task_tag)
                        next_raw_reqs.update(iter_task_req)

            if raw_reqs == next_raw_reqs:
                raise WRequirementsLoopError()

            raw_reqs = next_raw_reqs

        return task_found, tuple(result_reqs)

    @verify_type('strict', task_tag=str, skip_unresolved=bool)
    @verify_value('strict', task_tag=lambda x: len(x) > 0)
    @WCriticalResource.critical_section(timeout=__critical_section_timeout__)
    def start_task(self, task_tag, skip_unresolved=False):
        """ This is a thread safe :meth:`.WLauncherProto.start_task` method implementation. A task
        or requirements that are going to be started must not call this or any 'stop' methods due to
        lock primitive

        :type task_tag: str
        :type skip_unresolved: bool
        :rtype: int

        :raise WTaskStartError: if a task is started already
        :raise WNoSuchTask: raises if a task or one of its requirement can not be found
        :raise WRequirementsLoopError: raises if some tasks require each other
        """
        if task_tag in self.__started_tasks:
            raise WTaskStartError('A task "%s" is started already', task_tag)

        _, task_tags = self.__recursive_requirements(task_tag, skip_unresolved=skip_unresolved)

        task_tags = task_tags + (task_tag, )

        for task_tag in task_tags:
            task_cls = self.__registry.get(task_tag)
            instance = task_cls.launcher_task()
            instance.start()
            self.__started_tasks[task_tag] = instance

        return len(task_tags)

    @verify_type('strict', task_tag=str, stop_mode=WTaskStopMode)
    @verify_value('strict', task_tag=lambda x: len(x) > 0)
    def __stop_task(self, task_tag, stop_mode=WTaskStopMode.stop):
        """ Stop required tasks and return a number of stopped instances

        :param task_tag: same as 'task_tag' in :meth:`.WLauncherProto.stop_task`
        :type task_tag: str

        :param stop_mode: same as 'stop_mode' in :meth:`.WLauncherProto.stop_task`
        :type stop_mode: WTaskStopMode

        :rtype: int
        """
        task_instance = self.__started_tasks.get(task_tag, None)
        if task_instance is not None:
            if stop_mode == WTaskStopMode.stop and WTaskProto.stop in task_instance:
                task_instance.stop()
            elif stop_mode == WTaskStopMode.terminate and WTaskProto.terminate in task_instance:
                task_instance.terminate()
            self.__started_tasks.pop(task_tag)
            return 1
        return 0

    @verify_type('strict', task_tag=str, stop_mode=WTaskStopMode)
    @verify_value('strict', task_tag=lambda x: len(x) > 0)
    @WCriticalResource.critical_section(timeout=__critical_section_timeout__)
    def stop_task(self, task_tag, stop_mode=WTaskStopMode.stop):
        """ This is a thread safe :meth:`.WLauncherProto.stop` method implementation. Task
        or requirements that are going to be stopped must not call this or any 'start' or 'stop' methods due to
        lock primitive

        :type task_tag: str
        :type stop_mode: WTaskStopMode
        :rtype: None

        :raise WNoSuchTask: raises if task isn't running
        """
        if self.__stop_task(task_tag, stop_mode=stop_mode) == 0:
            raise WNoSuchTaskError('Unable to find a task "%s" to stop', task_tag)

    @verify_type('strict', task_tag=str)
    @verify_value('strict', task_tag=lambda x: len(x) > 0)
    def __dependent_tasks(self, task_tag):
        """ Return ordered tuple of tasks that depend on a specified task. Tags order allows to be confident
        that tasks that are not required to other tasks will be stopped first

        note: No mutual dependencies are allowed

        :param task_tag: same as 'task_tag' in :meth:`.WLauncherProto.stop_dependent_tasks`
        :type task_tag: str

        :rtype: tuple

        :raise WDependenciesLoopError: raises if there is a mutual dependency between tasks
        """
        started_tasks = set(self.__started_tasks.keys())
        current_run = {task_tag}
        prev_run = set()
        result = []

        while prev_run != current_run and current_run:
            prev_run = current_run
            next_run = set()

            for running_tag in started_tasks.difference([task_tag] + result):  # scan through all tasks except
                # "remembered"

                task_req = self.__registry.get(running_tag).requirements()
                if not task_req:  # no requirements, no dependencies
                    if running_tag in current_run:  # this task should be saved (stopped) as this task don't have any
                        # unresolved dependencies now
                        result.append(running_tag)
                        if running_tag in next_run:  # dependency is resolved, do not check this task anymore
                            next_run.remove(running_tag)
                    continue  # no requirements, no dependencies -- check next task

                task_req = set(filter(lambda x: x in started_tasks, task_req))  # only started tasks are good

                if task_req.intersection(current_run):  # there is a requirements, it means that task with
                    # "running_tag" depends on tasks that we interested in
                    task_req = set(filter(lambda x: x not in result, task_req))  # skip dependencies that are
                    # remembered already

                    next_run.add(running_tag)

                    if not task_req.difference([task_tag] + result):  # there are no requirements other that
                        # "remembered"
                        result.append(running_tag)
                    else:
                        next_run.update(task_req)

            current_run = next_run

        if len(current_run):
            raise WDependenciesLoopError(
                'A loop of dependencies was detected. The following tasks depend on each other: %s' %
                ', '.join(current_run)
            )

        return tuple(result)

    @verify_type('paranoid', task_tag=str, stop_mode=WTaskStopMode)
    @verify_value('paranoid', task_tag=lambda x: len(x) > 0)
    @WCriticalResource.critical_section(timeout=__critical_section_timeout__)
    def stop_dependent_tasks(self, task_tag, stop_mode=WTaskStopMode.stop):
        """ This is a thread safe :meth:`.WLauncherProto.stop_dependent_tasks` method implementation. Task
        or requirements that are going to be stopped must not call this or any 'start' or 'stop' methods due to
        lock primitive

        :type task_tag: str
        :type stop_mode: WTaskStopMode
        :rtype: int

        :raise WDependenciesLoopError: raises if there is a mutual dependency between tasks
        """
        result = 0
        for task_tag in self.__dependent_tasks(task_tag):
            result += self.__stop_task(task_tag, stop_mode=stop_mode)
        return result

    @verify_type('strict', stop_mode=WTaskStopMode)
    def all_stop(self, stop_mode=WTaskStopMode.stop):
        """ This is a thread safe :meth:`.WLauncherProto.all_stop` method implementation. Task
        or requirements that are going to be stopped must not call this or any 'start' or 'stop' methods due to
        lock primitive

        :type stop_mode: WTaskStopMode
        :rtype: int

        :raise WDependenciesLoopError: raises if there is a mutual dependency between tasks
        """
        with self.critical_context(timeout=self.__critical_section_timeout__) as c:
            result = 0
            while len(self.__started_tasks) > 0:
                task_tag = next(iter(self.__started_tasks))
                result += c.stop_dependent_tasks(task_tag, stop_mode=stop_mode)
                result += self.__stop_task(task_tag, stop_mode=stop_mode)

            return result


@verify_subclass('strict', launcher_task=WLauncherTaskProto)
def __launcher_task_api_id(launcher_task):
    """ This is an accessor that return a valid task tag from a task. The only purpose is to generate api_id for
    register_api function

    :param launcher_task: a task class which tag should be returned
    :type launcher_task: WLauncherTaskProto

    :rtype: str

    :raise ValueError: raises if there isn't a task_tag, or it has invalid type
    """
    task_tag = launcher_task.__task_tag__
    if task_tag is None or not isinstance(task_tag, str):
        raise ValueError('Unable to get an api_id from task - it is None or has invalid type')
    return task_tag


register_task = functools.partial(register_api, api_id=__launcher_task_api_id, callable_api_id=True)  # this is
# a shortcut for a task registration
