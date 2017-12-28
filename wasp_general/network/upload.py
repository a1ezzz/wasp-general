# -*- coding: utf-8 -*-
# wasp_general/network/upload.py
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

import os
import ftplib
from enum import Enum
from abc import ABCMeta, abstractmethod
from urllib.parse import urlparse

from wasp_general.verify import verify_type


class WUploaderProto(metaclass=ABCMeta):

	class URLOption(Enum):
		hostname = 0
		username = 1
		password = 2
		port = 3
		path = 4
		params = 5
		query = 6
		fragment = 7

	@abstractmethod
	def is_capable(self, scheme, options):
		raise NotImplementedError('This method is abstract')

	def upload(self, file_obj, options):
		raise NotImplementedError('This method is abstract')


class WBasicUploader(WUploaderProto):

	def __init__(self, scheme, supported_options, required_options):
		WUploaderProto.__init__(self,)
		self.__scheme = scheme
		self.__supported_options = supported_options
		self.__required_options = required_options

	def scheme(self):
		return self.__scheme

	def supported_options(self):
		return self.__supported_options

	def required_options(self):
		return self.__required_options

	def is_capable(self, scheme, options):
		if scheme != self.scheme():
			return False

		options = options.keys()

		supported_options = self.supported_options()
		for option in options:
			if option not in supported_options:
				return False

		required_options = self.required_options()
		for option in required_options:
			if option not in options:
				return False

		return True

	def upload(self, file_obj, options):
		if self.is_capable(self.scheme(), options) is False:
			raise RuntimeError(
				'Invalid options specified (required options may be missing, or unsupported options '
				'was specified)'
			)
		return self._upload(file_obj, options)

	@abstractmethod
	def _upload(self, file_obj, options):
		raise NotImplementedError('This method is abstract')


class WFTPUploader(WBasicUploader):

	def __init__(self):
		WBasicUploader.__init__(
			self,
			'ftp',
			(
				WUploaderProto.URLOption.hostname,
				WUploaderProto.URLOption.username,
				WUploaderProto.URLOption.password,
				# WUploaderProto.URLOption.port,
				# TODO: FTP class in python3.6 has port argument. But 3.4 doesn't
				WUploaderProto.URLOption.path
			),
			(
				WUploaderProto.URLOption.hostname,
				WUploaderProto.URLOption.path
			)
		)

	def is_capable(self, scheme, options):
		result = WBasicUploader.is_capable(self, scheme, options)
		if result is False:
			return result

		file_name = os.path.basename(options[WUploaderProto.URLOption.path])
		return len(file_name) > 0

	def _upload(self, file_obj, options):
		try:
			ftp_args = {'host': options[WUploaderProto.URLOption.hostname]}
			# TODO: FTP class in python3.6 has port argument. But 3.4 doesn't
			'''
			if WUploaderProto.URLOption.port in options:
				ftp_args['port'] = int(options[WUploaderProto.URLOption.port])
			'''

			ftp_client = ftplib.FTP(**ftp_args)

			login_args = {}
			if WUploaderProto.URLOption.username in options:
				login_args['user'] = options[WUploaderProto.URLOption.username]
			if WUploaderProto.URLOption.password in options:
				login_args['passwd'] = options[WUploaderProto.URLOption.password]
			ftp_client.login(**login_args)

			path = options[WUploaderProto.URLOption.path]
			dir_name, file_name = os.path.dirname(path), os.path.basename(path)
			self.__change_dir(ftp_client, dir_name)
			ftp_client.storbinary('STOR ' + file_name, file_obj)
			ftp_client.quit()
		except (ftplib.error_perm, ftplib.error_proto, ftplib.error_reply, ftplib.error_temp):
			return False
		except OSError:  # no route to host and so on
			return False

		return True

	def __change_dir(self, ftp_client, dir_name):
		dir_name, entry = os.path.split(dir_name)
		dir_entries = []

		while entry != '':
			dir_entries.append(entry)
			dir_name, entry = os.path.split(dir_name)

		dir_entries.reverse()
		ftp_client.cwd('/')

		for entry in dir_entries:
			if entry not in ftp_client.nlst():
				ftp_client.mkd(entry)
			ftp_client.cwd(entry)


class WUploaderCollection(WUploaderProto):

	__urlparse_options__ = {
		WUploaderProto.URLOption.hostname: 'hostname',
		WUploaderProto.URLOption.username: 'username',
		WUploaderProto.URLOption.password: 'password',
		WUploaderProto.URLOption.port: 'port',
		WUploaderProto.URLOption.path: 'path',
		WUploaderProto.URLOption.params: 'params',
		WUploaderProto.URLOption.query: 'query',
		WUploaderProto.URLOption.fragment: 'fragment',
	}

	@verify_type(uploaders=WUploaderProto)
	def __init__(self, *uploaders):
		WUploaderProto.__init__(self)
		self.__uploaders = list(uploaders)

	def uploaders(self):
		return tuple(self.__uploaders)

	def is_capable(self, scheme, options):
		for uploader in self.uploaders():
			if uploader.is_capable(scheme, options) is True:
				return True
		return False

	def upload(self, url, file_name):
		if os.path.exists(file_name) is False:
			raise ValueError('No such file %s' % file_name)
		if os.path.isfile(file_name) is False:
			raise ValueError('Regular file should be specified (original file name: %s)' % file_name)

		parsed_url = urlparse(url)

		scheme = parsed_url.scheme
		options = {}
		for option, option_name in self.__urlparse_options__.items():
			option_value = getattr(parsed_url, option_name)
			if option_value is not None and option_value != '':
				options[option] = option_value

		for uploader in self.uploaders():
			if uploader.is_capable(scheme, options) is True:
				with open(file_name, mode='rb') as f:
					return uploader.upload(f, options)

		return False
