# -*- coding: utf-8 -*-
# wasp_general/os/linux/lvm.py
#
# Copyright (C) 2017 the wasp-general authors and contributors
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

# TODO: document the code
# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

import subprocess
import os
import math

from wasp_general.verify import verify_type, verify_value
from wasp_general.os.linux.mounts import WMountPoint


class WLVMInfoCommand:
	""" This is a helper, with which it is easier to call for pvdisplay, vgdisplay or lvdisplay program.

	This class uses subprocess.check_output method for a program calling. And when non-zero code is returned by
	the program, an subprocess.CalledProcessError exception is raised. There is a timeout for a program to be
	complete. If a program wasn't completed for that period of time, subprocess.TimeoutExpired exception is
	raised
	"""

	__lvm_cmd_default_timeout__ = 0.5
	""" Default timeout for command to process
	"""

	@verify_type(command=str, fields_count=int, cmd_timeout=(int, float, None), sudo=bool)
	@verify_value(cmd_timeout=lambda x: x is None or x > 0)
	def __init__(self, command, fields_count, cmd_timeout=None, sudo=False):
		""" Create new command

		:param command: program to execute
		:param fields_count: fields in a program output
		:param cmd_timeout: timeout for a program (if it is None - then default value is used)
		:param sudo: flag - whether to run this program with sudo or not
		"""
		self.__command = command
		self.__fields_count = fields_count
		self.__cmd_timeout = cmd_timeout if cmd_timeout is not None else self.__lvm_cmd_default_timeout__
		self.__sudo = sudo

	def command(self):
		""" Return target program

		:return: str
		"""
		return self.__command

	def fields_count(self):
		""" Return number of fields in a program output

		:return: int
		"""
		return self.__fields_count

	def cmd_timeout(self):
		""" Timeout for a program to complete

		:return: int, float
		"""
		return self.__cmd_timeout

	def sudo(self):
		""" Return 'sudo' flag (whether to run this program with sudo or not)

		:return: bool
		"""
		return self.__sudo

	@verify_type(name=(str, None))
	def lvm_info(self, name=None):
		""" Call a program

		:param name: if specified - program will return information for that lvm-entity only. otherwise -
		all available entries are returned

		:return: tuple of str (fields)
		"""
		cmd = [] if self.sudo() is False else ['sudo']
		cmd.extend([self.command(), '-c'])
		if name is not None:
			cmd.append(name)

		output = subprocess.check_output(cmd, timeout=self.cmd_timeout())
		output = output.decode()
		result = []
		fields_count = self.fields_count()
		for line in output.split('\n'):
			line = line.strip()
			fields = line.split(':')
			if len(fields) == fields_count:
				result.append(fields)
		if name is not None and len(result) != 1:
			raise RuntimeError('Unable to parse command result')
		return tuple(result)


class WLVMInfo:
	""" Basic class for actual LVM information. This class creates :class:`.WLVMInfoCommand` object
	which may be called on an object creation (it depends on constructor parameters)
	"""

	__lvm_info_cmd_timeout__ = 0.5
	""" Timeout for a program to complete
	"""

	@verify_type('paranoid', command=str, fields_count=int, sudo=bool)
	@verify_type(lvm_entity=(str, tuple, list, set))
	@verify_value(lvm_entity=lambda x: len(x) > 0 if isinstance(x, str) else True)
	def __init__(self, command, fields_count, lvm_entity, sudo=False):
		""" Create new info-object

		:param command: same as command in :meth:`.WLVMInfoCommand.__init__`
		:param fields_count: same as fields_count in :meth:`.WLVMInfoCommand.__init__`
		:param lvm_entity: if this is a list/tuple/set - then it is a collection of fields (collection length \
		must be the same as 'fields_count'). If it is a string, then command is executed to get corresponding \
		fields
		:param sudo: same as sudo in :meth:`.WLVMInfoCommand.__init__`
		"""
		self.__lvm_command = WLVMInfoCommand(
			command, fields_count, cmd_timeout=self.__class__.__lvm_info_cmd_timeout__, sudo=sudo
		)
		if isinstance(lvm_entity, (tuple, list, set)) is True:
			if len(lvm_entity) != fields_count:
				raise ValueError(
					'Invalid lvm entity fields count: %i (expected: %i)' %
					(len(lvm_entity), fields_count)
				)
			self.__lvm_entity = tuple(lvm_entity)
		else:
			self.__lvm_entity = (self.lvm_command().lvm_info(lvm_entity)[0])

	def lvm_command(self):
		""" Return LVM-command object

		:return: WLVMInfoCommand
		"""
		return self.__lvm_command

	def lvm_entity(self):
		""" Return object fields

		:return: tuple of str (fields)
		"""
		return self.__lvm_entity


class WPhysicalVolume(WLVMInfo):
	""" Class represent a physical volume
	"""

	@verify_type('paranoid', physical_volume=(str, tuple, list, set), sudo=bool)
	@verify_value('paranoid', physical_volume=lambda x: len(x) > 0 if isinstance(x, str) else True)
	def __init__(self, physical_volume, sudo=False):
		""" Create new physical volume descriptor

		:param physical_volume: same as 'lvm_entity' in :meth:`.WLVMInfo.__init__`
		:param sudo: same as 'sudo' in :meth:`.WLVMInfo.__init__`
		"""
		WLVMInfo.__init__(self, 'pvdisplay', 12, physical_volume, sudo=sudo)

	def all(self):
		""" Return every physical volume in the system

		:return: tuple of WPhysicalVolume
		"""
		return tuple([WPhysicalVolume(x) for x in self.lvm_command().lvm_info()])

	def device_name(self):
		""" Return physical volume device name

		:return: str
		"""
		return self.lvm_entity()[0]

	def volume_group(self):
		""" Return related volume group name (may be empty string if this volume is not allocated to any)

		:return: str
		"""
		return self.lvm_entity()[1]

	def sectors_count(self):
		""" Return physical volume size in sectors

		:return: int
		"""
		return int(self.lvm_entity()[2])

	def extent_size(self):
		""" Return physical extent size in kilobytes (may have 0 value if this volume is not allocated to any)

		:return: int
		"""
		return int(self.lvm_entity()[7])

	def total_extents(self):
		""" Return total number of physical extents (may have 0 value if this volume is not allocated to any)

		:return: int
		"""
		return int(self.lvm_entity()[8])

	def free_extents(self):
		""" Return free number of physical extents (may have 0 value if this volume is not allocated to any)

		:return: int
		"""
		return int(self.lvm_entity()[9])

	def allocated_extents(self):
		""" Return allocated number of physical extents (may have 0 value if this volume is not allocated to \
		any)

		:return: int
		"""
		return int(self.lvm_entity()[10])

	def uuid(self):
		""" Return physical volume UUID

		:return: str
		"""
		return self.lvm_entity()[11]


class WVolumeGroup(WLVMInfo):
	""" Class represent a volume group
	"""

	@verify_type('paranoid', volume_group=(str, tuple, list, set), sudo=bool)
	@verify_value('paranoid', volume_group=lambda x: len(x) > 0 if isinstance(x, str) else True)
	def __init__(self, volume_group, sudo=False):
		""" Create new volume group descriptor

		:param volume_group: same as 'lvm_entity' in :meth:`.WLVMInfo.__init__`
		:param sudo: same as 'sudo' in :meth:`.WLVMInfo.__init__`
		"""
		WLVMInfo.__init__(self, 'vgdisplay', 17, volume_group, sudo=sudo)

	def all(self):
		""" Return every volume group in the system

		:return: tuple of WVolumeGroup
		"""
		return tuple([WVolumeGroup(x) for x in self.lvm_command().lvm_info()])

	def group_name(self):
		""" Return volume group name

		:return: str
		"""
		return self.lvm_entity()[0]

	def group_access(self):
		""" Return volume group access

		:return: str
		"""
		return self.lvm_entity()[1]

	def maximum_logical_volumes(self):
		""" Return maximum number of logical volumes (0 - for unlimited)

		:return: int
		"""
		return int(self.lvm_entity()[4])

	def logical_volumes(self):
		""" Return current number of logical volumes

		:return: int
		"""
		return int(self.lvm_entity()[5])

	def opened_logical_volumes(self):
		""" Return open count of all logical volumes in this volume group

		:return: int
		"""
		return int(self.lvm_entity()[6])

	def maximum_physical_volumes(self):
		""" Return maximum number of physical volumes (0 - for unlimited)

		:return: int
		"""
		return int(self.lvm_entity()[8])

	def physical_volumes(self):
		""" Return current number of physical volumes

		:return: int
		"""
		return int(self.lvm_entity()[9])

	def actual_volumes(self):
		""" Return actual number of physical volumes

		:return: int
		"""
		return int(self.lvm_entity()[10])

	def size(self):
		""" Return size of volume group in kilobytes

		:return: int
		"""
		return int(self.lvm_entity()[11])

	def extent_size(self):
		""" Return physical extent size in kilobytes

		:return: int
		"""
		return int(self.lvm_entity()[12])

	def total_extents(self):
		""" Return total number of physical extents for this volume group

		:return: int
		"""
		return int(self.lvm_entity()[13])

	def allocated_extents(self):
		""" Return allocated number of physical extents for this volume group

		:return: int
		"""
		return int(self.lvm_entity()[14])

	def free_extents(self):
		""" Return free number of physical extents for this volume group

		:return: int
		"""
		return int(self.lvm_entity()[15])

	def uuid(self):
		""" Return UUID of volume group

		:return: str
		"""
		return self.lvm_entity()[16]


class WLogicalVolume(WLVMInfo):
	""" Class represent a logical volume
	"""

	__lvm_snapshot_create_cmd_timeout__ = 0.5
	""" Timeout for snapshot creation command to complete
	"""

	__lvm_snapshot_remove_cmd_timeout__ = 0.5
	""" Timeout for snapshot removing command to complete
	"""

	__lvm_snapshot_check_cmd_timeout__ = 0.5
	""" Timeout for snapshot checking (getting parameters) command to complete
	"""

	__snapshot_maximum_allocation__ = 99
	""" Maximum space usage for snapshot, till that value snapshot is treated as valid
	"""

	@verify_type('paranoid', logical_volume=(str, tuple, list, set), sudo=bool)
	@verify_value('paranoid', logical_volume=lambda x: len(x) > 0 if isinstance(x, str) else True)
	def __init__(self, logical_volume, sudo=False):
		""" Create new logical volume descriptor

		:param logical_volume: same as 'lvm_entity' in :meth:`.WLVMInfo.__init__`
		:param sudo: same as 'sudo' in :meth:`.WLVMInfo.__init__`
		"""
		WLVMInfo.__init__(self, 'lvdisplay', 13, logical_volume, sudo=sudo)

	def all(self):
		""" Return every logical volume in the system

		:return: tuple of WLogicalVolume
		"""
		return tuple([WLogicalVolume(x) for x in self.lvm_command().lvm_info()])

	def volume_path(self):
		""" Return logical volume path

		:return: str
		"""
		return self.lvm_entity()[0]

	def volume_name(self):
		""" Return logical volume name

		:return: str
		"""
		return os.path.basename(self.volume_path())

	def volume_group_name(self):
		""" Return volume group name

		:return: str
		"""
		return self.lvm_entity()[1]

	def volume_group(self):
		""" Return volume group

		:return: WVolumeGroup
		"""
		return WVolumeGroup(self.volume_group_name())

	def sectors_count(self):
		""" Return logical volume size in sectors

		:return: int
		"""
		return int(self.lvm_entity()[6])

	def extents_count(self):
		""" Return current logical extents associated to logical volume

		:return: int
		"""
		return int(self.lvm_entity()[7])

	def device_number(self):
		""" Return tuple of major and minor device number of logical volume

		:return: tuple of int
		"""
		return int(self.lvm_entity()[11]), int(self.lvm_entity()[12])

	def uuid(self):
		""" Return UUID of logical volume

		:return: str
		"""
		uuid_file = '/sys/block/%s/dm/uuid' % os.path.realpath(self.volume_path())
		lv_uuid = open(uuid_file).read().strip()
		if lv_uuid.startswith('LVM-') is True:
			return lv_uuid[4:]
		return lv_uuid

	@verify_type(snapshot_size=(int, float), snapshot_suffix=str)
	@verify_value(snapshot_size=lambda x: x > 0, snapshot_suffix=lambda x: len(x) > 0)
	def create_snapshot(self, snapshot_size, snapshot_suffix):
		""" Create snapshot for this logical volume.

		:param snapshot_size: size of newly created snapshot volume. This size is a fraction of the source \
		logical volume space (of this logical volume)
		:param snapshot_suffix: suffix for logical volume name (base part is the same as the original volume \
		name)

		:return: WLogicalVolume
		"""
		size_extent = math.ceil(self.extents_count() * snapshot_size)
		size_kb = self.volume_group().extent_size() * size_extent
		snapshot_name = self.volume_name() + snapshot_suffix

		lvcreate_cmd = [
			'lvcreate', '-L', '%iK' % size_kb, '-s', '-n', snapshot_name, '-p', 'r', self.volume_path()
		]
		subprocess.check_output(lvcreate_cmd, timeout=self.__class__.__lvm_snapshot_create_cmd_timeout__)
		return WLogicalVolume(self.volume_path() + snapshot_suffix)

	def remove_volume(self):
		""" Remove this volume

		:return: None
		"""
		lvremove_cmd = ['lvremove', '-f', self.volume_path()]
		subprocess.check_output(lvremove_cmd, timeout=self.__class__.__lvm_snapshot_remove_cmd_timeout__)

	def snapshot_allocation(self):
		""" Return allocated size (fraction of total snapshot volume space). If this is not a snapshot volume,
		than RuntimeError exception is raised.

		:return: float
		"""
		check_cmd = ['lvs', self.volume_path(), '-o', 'snap_percent', '--noheadings']
		output = subprocess.check_output(check_cmd, timeout=self.__class__.__lvm_snapshot_check_cmd_timeout__)
		output = output.decode().strip()
		if len(output) == 0:
			raise RuntimeError('Unable to check general logical volume')
		return float(output.replace(',', '.', 1))

	def snapshot_corrupted(self):
		""" Check if this snapshot volume is corrupted or not

		:return: bool (True if corrupted, False - otherwise)
		"""
		return self.snapshot_allocation() > self.__class__.__snapshot_maximum_allocation__

	@classmethod
	@verify_type('paranoid', file_path=str, sudo=bool)
	@verify_value('paranoid', file_path=lambda x: len(x) > 0)
	def logical_volume(cls, file_path, sudo=False):
		""" Return logical volume that stores the given path

		:param file_path: target path to search
		:param sudo: same as 'sudo' in :meth:`.WLogicalVolume.__init__`
		:return: WLogicalVolume or None (if file path is outside current mount points)
		"""
		mp = WMountPoint.mount_point(file_path)
		if mp is not None:
			name_file = '/sys/block/%s/dm/name' % mp.device_name()
			if os.path.exists(name_file):
				lv_path = '/dev/mapper/%s' % open(name_file).read().strip()
				return WLogicalVolume(lv_path, sudo=sudo)
