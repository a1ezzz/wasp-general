# -*- coding: utf-8 -*-

import os
from wasp_general.mime import mime_type


def test_mime():
	path = os.path.dirname(__file__)
	assert(mime_type(os.path.join(path, 'mime_test_files', 'test.html')) == 'text/html')
	assert(
		mime_type(os.path.join(path, 'mime_test_files', 'test.js')) in
		['application/x-javascript', 'application/javascript']
	)
	assert(mime_type(os.path.join(path, 'mime_test_files', 'test.css')) == 'text/css')
	assert(mime_type(os.path.join(path, 'mime_test_files', 'test.woff2')) == 'application/font-woff2')
