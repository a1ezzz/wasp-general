
from tempfile import mktemp
import os
import pytest


@pytest.fixture
def temp_file(request):
	filename = mktemp('pytest-wasp-general-')

	def fin():
		if os.path.exists(filename):
			os.unlink(filename)
	request.addfinalizer(fin)
	return filename
