# -*- coding: utf-8 -*-

import pytest

from wasp_general.os.linux.lvm import WLVMInfoCommand, WLVMInfo, WPhysicalVolume, WVolumeGroup, WLogicalVolume


class TestWLVMInfoCommand:

	def test(self):
		info_command = WLVMInfoCommand('command1', 10)
		assert(isinstance(info_command, WLVMInfoCommand) is True)
		assert(info_command.command() == 'command1')
		assert(info_command.fields_count() == 10)
		assert(info_command.cmd_timeout() > 0)
		assert(info_command.sudo() is False)

		info_command = WLVMInfoCommand('command2', 7, cmd_timeout=1, sudo=True)
		assert(isinstance(info_command, WLVMInfoCommand) is True)
		assert(info_command.command() == 'command2')
		assert(info_command.fields_count() == 7)
		assert(info_command.cmd_timeout() == 1)
		assert(info_command.sudo() is True)


class TestWLVMInfo:

	def test(self):
		lvm_info = WLVMInfo('command1', 3, ['field1', 'option2', 'value3'])
		assert(isinstance(lvm_info, WLVMInfo) is True)
		assert(lvm_info.lvm_entity() == ('field1', 'option2', 'value3'))
		assert(isinstance(lvm_info.lvm_command(), WLVMInfoCommand) is True)
		assert(lvm_info.lvm_command().command() == 'command1')
		assert (lvm_info.lvm_command().fields_count() == 3)
		assert (lvm_info.lvm_command().cmd_timeout() == WLVMInfo.__lvm_info_cmd_timeout__)
		assert (lvm_info.lvm_command().sudo() is False)

		class TestLVMInfo(WLVMInfo):
			__lvm_info_cmd_timeout__ = 10

		lvm_info = TestLVMInfo('command2', 4, ['field1', 'option2', 'value3', ''], sudo=True)
		assert(lvm_info.lvm_command().command() == 'command2')
		assert (lvm_info.lvm_command().fields_count() == 4)
		assert (lvm_info.lvm_command().cmd_timeout() == TestLVMInfo.__lvm_info_cmd_timeout__)
		assert (lvm_info.lvm_command().sudo() is True)

		pytest.raises(ValueError, WLVMInfo, 'command', 2, [])


class TestWPhysicalVolume:
	def test(self):
		example = \
			'/dev/sda1:test-vg:16287744:-1:8:8:-1:4096:1988:200:1788:GHskdS-776l-mFbq-UDkG-MqN9-rYTO-rNpHGy'
		phy_vol = WPhysicalVolume(example.split(':'))
		assert(isinstance(phy_vol, WPhysicalVolume) is True)
		assert(isinstance(phy_vol, WLVMInfo) is True)
		assert(phy_vol.lvm_command().sudo() is False)
		assert(phy_vol.device_name() == '/dev/sda1')
		assert(phy_vol.volume_group() == 'test-vg')
		assert(phy_vol.sectors_count() == 16287744)
		assert(phy_vol.extent_size() == 4096)
		assert(phy_vol.total_extents() == 1988)
		assert(phy_vol.free_extents() == 200)
		assert(phy_vol.allocated_extents() == 1788)
		assert(phy_vol.uuid() == 'GHskdS-776l-mFbq-UDkG-MqN9-rYTO-rNpHGy')

		phy_vol = WPhysicalVolume(example.split(':'), sudo=True)
		assert(phy_vol.lvm_command().sudo() is True)


class TestWVolumeGroup:

	def test(self):
		example = 'test-vg:r/w:772:-1:0:2:1:-1:0:1:1:8142848:4096:1988:1788:200:' \
			'KupnMx-Fizr-DxTk-2GTf-9ELZ-J4u9-82Muq7'
		vol_group = WVolumeGroup(example.split(':'))
		assert(isinstance(vol_group, WVolumeGroup) is True)
		assert(isinstance(vol_group, WLVMInfo) is True)
		assert(vol_group.lvm_command().sudo() is False)

		assert(vol_group.group_name() == 'test-vg')
		assert(vol_group.group_access() == 'r/w')
		assert(vol_group.maximum_logical_volumes() == 0)
		assert(vol_group.logical_volumes() == 2)
		assert(vol_group.opened_logical_volumes() == 1)
		assert(vol_group.maximum_physical_volumes() == 0)
		assert(vol_group.physical_volumes() == 1)
		assert(vol_group.maximum_physical_volumes() == 0)
		assert(vol_group.actual_volumes() == 1)
		assert(vol_group.size() == 8142848)
		assert(vol_group.extent_size() == 4096)
		assert(vol_group.total_extents() == 1988)
		assert(vol_group.allocated_extents() == 1788)
		assert(vol_group.free_extents() == 200)
		assert(vol_group.uuid() == 'KupnMx-Fizr-DxTk-2GTf-9ELZ-J4u9-82Muq7')

		vol_group = WVolumeGroup(example.split(':'), sudo=True)
		assert (vol_group.lvm_command().sudo() is True)


class TestWLogicalVolume:

	def test(self):
		example = '/dev/test-vg/test-lv:test-vg:3:1:-1:1:14647296:1788:-1:0:-1:254:0'
		log_vol = WLogicalVolume(example.split(':'))
		assert(isinstance(log_vol, WLogicalVolume) is True)
		assert(isinstance(log_vol, WLVMInfo) is True)
		assert(log_vol.lvm_command().sudo() is False)

		assert(log_vol.volume_path() == '/dev/test-vg/test-lv')
		assert(log_vol.volume_name() == 'test-lv')
		assert(log_vol.volume_group_name() == 'test-vg')
		assert(log_vol.sectors_count() == 14647296)
		assert(log_vol.extents_count() == 1788)
		assert (log_vol.device_number() == (254, 0))

		log_vol = WLogicalVolume(example.split(':'), sudo=True)
		assert(log_vol.lvm_command().sudo() is True)
