# -*- coding: utf-8 -*-
# wasp_general/api/serialize.py
#
# Copyright (C) 2017, 2021, 2022 the wasp-general authors and contributors
# <see AUTHORS file>
#
# This file is part of wasp-general.
#
# wasp-general is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# wasp-general is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with wasp-general.  If not, see <http://www.gnu.org/licenses/>.

import json.encoder
from datetime import datetime

from wasp_general.datetime import utc_datetime


class WJSONEncoder(json.encoder.JSONEncoder):
    """ This class helps to convert some python-specific classes to a json-structure
    """

    def default(self, o):
        if isinstance(o, set) is True:
            return list(o)
        elif isinstance(o, bytes):
            return [x for x in o]
        elif isinstance(o, datetime):
            return utc_datetime(o, local_value=False).isoformat()
        return json.encoder.JSONEncoder.default(self, o)
