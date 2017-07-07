# -*- coding: utf-8 -*-

import pytest

from wasp_general.os.linux.mounts import WMountPoint


class TestWMountPoint:

	class NullFileMP(WMountPoint):
		__mounts_file__ = '/dev/null'

	__mounts_file_example__ = """/dev/sda1 / ext4 rw,noatime,discard,data=ordered 0 0
devtmpfs /dev devtmpfs rw,relatime,size=5854588k,nr_inodes=1463647,mode=755 0 0
sysfs /sys sysfs rw,nosuid,nodev,noexec,relatime 0 0
proc /proc proc rw,nosuid,nodev,noexec,relatime 0 0
tmpfs /dev/shm tmpfs rw,nosuid,nodev 0 0
devpts /dev/pts devpts rw,nosuid,noexec,relatime,gid=5,mode=620,ptmxmode=000 0 0
tmpfs /run tmpfs rw,nosuid,nodev,mode=755 0 0
"""

	def test(self, temp_file):
		mp = WMountPoint('/dev/sda1 / ext4 rw,noatime,discard,data=ordered 1 1')
		assert(isinstance(mp, WMountPoint) is True)
		assert(mp.device() == '/dev/sda1')
		assert(mp.device_name() == 'sda1')
		assert(mp.path() == '/')
		assert(mp.fs() == 'ext4')
		assert(mp.options() == ('rw', 'noatime', 'discard', 'data=ordered'))
		assert(mp.dump_flag() is True)
		assert(mp.fsck_order() == 1)

		pytest.raises(RuntimeError, WMountPoint, '')
		pytest.raises(RuntimeError, WMountPoint, '/dev/ fat32')
		pytest.raises(RuntimeError, WMountPoint, '/dev/sda1 / ext4 rw,noatime,discard,data=ordered 2 1')

		assert(TestWMountPoint.NullFileMP.mounts() == tuple())

		with open(temp_file, 'w') as f:
			f.write(TestWMountPoint.__mounts_file_example__)

		class MountsExample(WMountPoint):
			__mounts_file__ = temp_file

		mounts = MountsExample.mounts()
		assert(len(mounts) == 7)

		assert(isinstance(mounts[0], WMountPoint) is True)
		assert(mounts[0].device() == '/dev/sda1')

		assert(isinstance(mounts[1], WMountPoint) is True)
		assert(mounts[1].device_name() == 'devtmpfs')

		assert(isinstance(mounts[2], WMountPoint) is True)
		assert(mounts[2].path() == '/sys')

		assert(isinstance(mounts[3], WMountPoint) is True)
		assert(mounts[3].fs() == 'proc')

		assert(isinstance(mounts[4], WMountPoint) is True)
		assert(mounts[4].options() == ('rw', 'nosuid', 'nodev'))

		assert(isinstance(mounts[5], WMountPoint) is True)
		assert(mounts[5].dump_flag() is False)

		assert(isinstance(mounts[6], WMountPoint) is True)
		assert(mounts[6].fsck_order() == 0)

		assert(TestWMountPoint.NullFileMP.mount_point('/foo') is None)

		mp = MountsExample.mount_point('/foo/bar')
		assert(isinstance(mp, WMountPoint) is True)
		assert(mp.device() == '/dev/sda1')

		mp = MountsExample.mount_point('/dev/file1')
		assert(isinstance(mp, WMountPoint) is True)
		assert(mp.device() == 'devtmpfs')

		mp = MountsExample.mount_point('/dev/pts/file1')
		assert(isinstance(mp, WMountPoint) is True)
		assert(mp.device() == 'devpts')
