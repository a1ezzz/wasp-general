# -*- coding: utf-8 -*-

import pytest
import os
from tempfile import mktemp

from configparser import ConfigParser, NoOptionError, NoSectionError

from wasp_general.config import WConfig, WConfigSelection


@pytest.fixture
def tempfile(request):
	filename = mktemp('pytest-wasp-general-')

	def fin():
		if os.path.exists(filename):
			os.unlink(filename)
	request.addfinalizer(fin)
	return filename


class TestWConfig:

	def test_config(self, tempfile):
		conf = WConfig()
		assert(isinstance(conf, ConfigParser) is True)

		with pytest.raises(KeyError):
			print(conf['section1']['option1'])
		with pytest.raises(KeyError):
			print(conf['section1']['option2'])
		with pytest.raises(KeyError):
			print(conf['section1']['option3'])

		conf_parser = ConfigParser()
		conf_parser.add_section('section1')
		conf_parser.set('section1', 'option1', '1')

		conf.merge(conf_parser)
		assert(conf['section1']['option1'] == '1')
		with pytest.raises(KeyError):
			print(conf['section1']['option2'])
		with pytest.raises(KeyError):
			print(conf['section1']['option3'])

		with open(tempfile, 'w') as f:
			f.write('''
			[section1]
			option1 = 2
			option2 = foo, bar
			option3 =
			''')

		conf.merge(tempfile)
		assert (conf['section1']['option1'] == '2')
		assert (conf['section1']['option2'] == 'foo, bar')
		assert (conf['section1']['option3'] == '')

		assert(conf.split_option('section1', 'option2') == ['foo', 'bar'])
		assert(conf.split_option('section1', 'option3') == [])

	def test_merge(self):
		config1 = WConfig()
		config2 = WConfig()

		config1.add_section('section1.1')
		config1['section1.1']['option1'] = 'value1'
		config1['section1.1']['option2'] = '2'
		config1.add_section('section1.2')
		config1['section1.2']['option1'] = 'value1.2'
		config1['section1.2']['option2'] = '5'

		config2.add_section('section1.1')
		config2['section1.1']['option2'] = '7'
		config2['section1.1']['option3'] = '3'
		config2.add_section('section1.3')
		config2['section1.3']['option1'] = 'value2'
		config2.add_section('section1.4')
		config2['section1.4']['option'] = 'value'

		config1.merge_section(config2, 'section1.1')
		assert(config1['section1.1']['option1'] == 'value1')
		assert(config1['section1.1']['option2'] == '7')
		assert(config1['section1.2']['option1'] == 'value1.2')
		assert(config1['section1.2']['option2'] == '5')
		assert(config1.has_section('section1.4') is False)

		config1.merge_section(config2, 'section1.1', 'section1.3')

		assert(config1['section1.1']['option1'] == 'value2')
		assert(config1['section1.1']['option2'] == '7')
		assert(config1['section1.2']['option1'] == 'value1.2')
		assert(config1['section1.2']['option2'] == '5')
		assert(config1.has_section('section1.4') is False)

		config1.merge_section(config2, 'section1.4')
		assert(config1['section1.1']['option1'] == 'value2')
		assert(config1['section1.1']['option2'] == '7')
		assert(config1['section1.2']['option1'] == 'value1.2')
		assert(config1['section1.2']['option2'] == '5')
		assert(config1.has_section('section1.4') is True)

		pytest.raises(ValueError, config1.merge_section, config2, 'section1.2')


class TestWConfigSelection:

	def test(self):
		conf = WConfig()
		conf.add_section('section1')
		conf.add_section('section2')
		conf['section1']['option1'] = 'value1'
		conf['section1']['option1.sub-option1'] = '10'
		conf['section1']['option2'] = 'value2'
		conf['section2']['option2'] = 'true'

		pytest.raises(NoSectionError, conf.select_options, 'section0')

		conf_selection = conf.select_options('section1')
		assert(isinstance(conf_selection, WConfigSelection) is True)
		assert(conf_selection.config() == conf)
		assert(conf_selection.section() == 'section1')
		assert(conf_selection.option_prefix() == '')

		pytest.raises(NoOptionError, str, conf_selection)
		pytest.raises(NoOptionError, int, conf_selection)
		pytest.raises(NoOptionError, float, conf_selection)
		pytest.raises(NoOptionError, bool, conf_selection)

		conf_selection = conf_selection.select_options('option1')
		assert(isinstance(conf_selection, WConfigSelection) is True)
		assert(conf_selection.has_option() is True)
		assert(conf_selection['test_option'].has_option() is False)
		assert(str(conf_selection) == 'value1')
		pytest.raises(ValueError, int, conf_selection)
		pytest.raises(ValueError, float, conf_selection)
		pytest.raises(ValueError, bool, conf_selection)

		assert(int(conf_selection['.sub-option1']) == 10)
		assert(conf_selection.has_option('.sub-option1') is True)
		assert(conf_selection.has_option('.sub-option2') is False)
		assert(bool(conf.select_options('section2', 'option2')) is True)
