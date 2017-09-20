
import os
from setuptools import setup, find_packages

from wasp_general.version import __numeric_version__, __author__, __email__, __license__


class SetupPySpec:

	name = "wasp-general"
	version = __numeric_version__
	description = "Collection of unrelated functions and classes widely used in different wasp-projects"
	keywords = ["wasp", "cli", "network", "lvm", "threads", "validation"]
	url = "https://github.com/a1ezzz/wasp-general"
	classifiers= [
		"Development Status :: 2 - Pre-Alpha",
		"Intended Audience :: Developers",
		"License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
		"Operating System :: OS Independent",
		"Programming Language :: Python",
		"Programming Language :: Python :: 3.4",
		"Programming Language :: Python :: 3.5",
		"Programming Language :: Python :: 3.6",
		"Programming Language :: Python :: 3.7",
		"Programming Language :: Python :: 3 :: Only",
		"Topic :: Software Development :: Libraries",
		"Topic :: Software Development :: Libraries :: Python Modules",
	]
	# source - http://pypi.python.org/pypi?%3Aaction=list_classifiers

	zip_safe = False

	@staticmethod
	def require(fname):
		return open(fname).read().splitlines()

	@staticmethod
	def read(fname):
	    return open(os.path.join(os.path.dirname(__file__), fname)).read()

if __name__ == "__main__":
	setup(
		name = SetupPySpec.name,
		version = SetupPySpec.version,
		author = __author__,
		author_email = __email__,
		maintainer = __author__,
		maintainer_email = __email__,
		description = SetupPySpec.description,
		license = __license__,
		keywords = SetupPySpec.keywords,
		url = SetupPySpec.url,
		packages = find_packages(),
		include_package_data = True,
		long_description = SetupPySpec.read('README'),
		classifiers = SetupPySpec.classifiers,
		install_requires = SetupPySpec.require('requirements.txt'),
		zip_safe = SetupPySpec.zip_safe
	)
