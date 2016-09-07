# -*- coding: utf-8 -*-

import pytest
import os
from tempfile import mkdtemp

from wasp_general.version import revision


@pytest.fixture()
def cwd(request):
	curdir = os.path.curdir

	def fin():
		os.chdir(curdir)
	request.addfinalizer(fin)


@pytest.mark.usefixtures('cwd')
def test_revision():
	revision()
	try:
		d = mkdtemp()
		os.chdir(d)
		assert(revision() == '--')
	finally:
		os.rmdir(d)
