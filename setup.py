
import os
from setuptools import setup, find_packages

from wasp_general.version import __package_data__, __license__


def read(fname):
	return open(os.path.join(os.path.dirname(__file__), fname)).read()


if __name__ == "__main__":
	setup(
		name=__package_data__['package'],
		version=__package_data__['numeric_version'],
		author=__package_data__['author'],
		author_email=__package_data__['author_email'],
		maintainer=__package_data__['maintainer'],
		maintainer_email=__package_data__['maintainer_email'],
		description=__package_data__['brief_description'],
		license=__license__,
		keywords=__package_data__['pypi']['keywords'],
		url=__package_data__['homepage'],
		packages=find_packages(),
		include_package_data=True,
		long_description=read(__package_data__['readme_file']),
		classifiers=__package_data__['pypi']['classifiers'],
		install_requires=read(__package_data__['requirements.txt']).splitlines(),
		zip_safe=__package_data__['pypi']['zip_safe'] if 'zip_safe' in __package_data__['pypi'] else False,
		scripts=__package_data__['scripts'] if 'scripts' in __package_data__ else [],
		extras_require= \
			__package_data__['pypi']['extra_require'] if 'extra_require' in __package_data__['pypi'] else {}
	)
