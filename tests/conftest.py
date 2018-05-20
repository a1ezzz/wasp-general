
from tempfile import mktemp, mkdtemp
import os
import pytest
import shutil


@pytest.fixture
def temp_file(request):
	filename = mktemp('-pytest-wasp-general')

	def fin():
		if os.path.exists(filename):
			os.unlink(filename)
	request.addfinalizer(fin)
	return filename


@pytest.fixture
def temp_dir(request):
	dir_name = mkdtemp('-pytest-wasp-general')

	def fin():
		if os.path.exists(dir_name):
			shutil.rmtree(dir_name)
	request.addfinalizer(fin)
	return dir_name
