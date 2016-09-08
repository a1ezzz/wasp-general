# -*- coding: utf-8 -*-

import pytest
import os
from tempfile import mktemp

from configparser import ConfigParser

from wasp_general.config import WConfig


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
		# noinspection PyUnresolvedReferences
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

		# noinspection PyUnresolvedReferences
		conf.merge(tempfile)
		assert (conf['section1']['option1'] == '2')
		assert (conf['section1']['option2'] == 'foo, bar')
		assert (conf['section1']['option3'] == '')

		# noinspection PyUnresolvedReferences
		assert(conf.split_option('section1', 'option2') == ['foo', 'bar'])
		# noinspection PyUnresolvedReferences
		assert(conf.split_option('section1', 'option3') == [])
