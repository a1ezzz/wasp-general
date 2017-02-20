# -*- coding: utf-8 -*-
# wasp_general/mime.py
#
# Copyright (C) 2016 the wasp-general authors and contributors
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


# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

import mimetypes
import magic
from threading import Lock


__mime_lock = Lock()


def mime_type(filename):
	""" Guess mime type for the given file name

	Note: this implementation uses python_magic package which is not thread-safe, as a workaround global lock is
	used for the ability to work in threaded environment

	:param filename: file name to guess
	:return: str
	"""
	# TODO: write lock-free mime_type function
	try:
		__mime_lock.acquire()

		extension = filename.split(".")
		extension = extension[len(extension) - 1]

		if extension == "woff2":
			return "application/font-woff2"
		if extension == "css":
			return "text/css"

		m = magic.from_file(filename, mime=True)
		m = m.decode() if isinstance(m, bytes) else m  # compatibility fix, some versions return bytes some - str
		if m == "text/plain":
			guessed_type = mimetypes.guess_type(filename)[0]  # for js-detection
			if guessed_type:
				return guessed_type
		return m
	finally:
		__mime_lock.release()
