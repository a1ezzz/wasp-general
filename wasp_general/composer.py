# -*- coding: utf-8 -*-
# wasp_general/composer.py
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

from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type, verify_value


class WComposerProto(metaclass=ABCMeta):

	@abstractmethod
	def compose(self, obj_spec):
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def decompose(self, obj):
		raise NotImplementedError('This method is abstract')


class WPlainComposer(WComposerProto):

	@verify_type(strict_cls=(int, float, str, None))
	def __init__(self, strict_cls=None):
		WComposerProto.__init__(self)
		self.__strict_cls = strict_cls

	def strict_cls(self):
		return self.__strict_cls

	@verify_type(obj_spec=(int, float, str))
	def compose(self, obj_spec):
		self.__check(obj_spec)
		return obj_spec

	@verify_type(obj_spec=(int, float, str))
	def decompose(self, obj):
		self.__check(obj)
		return obj

	def __check(self, obj):
		strict_cls = self.strict_cls()
		if strict_cls is not None and isinstance(obj, strict_cls) is False:
			raise TypeError('Invalid type')


# noinspection PyAbstractClass
class WProxyComposer(WComposerProto):

	@verify_type(basic_composer=WComposerProto)
	def __init__(self, basic_composer):
		WComposerProto.__init__(self)
		self.__basic_composer = basic_composer

	def basic_composer(self):
		return self.__basic_composer


class WIterComposer(WProxyComposer):

	@verify_type(obj_spec=(list, set, tuple))
	def compose(self, obj_spec):
		return [self.basic_composer().compose(x) for x in obj_spec]

	@verify_type(obj_spec=(list, set, tuple))
	def decompose(self, obj):
		return [self.basic_composer().decompose(x) for x in obj]


class WCompositeComposer(WComposerProto):

	# noinspection PyAbstractClass
	class CompositeKey(WProxyComposer):

		@verify_type('paranoid', basic_composer=WComposerProto)
		@verify_type(required=bool)
		def __init__(self, key, basic_composer, required=False):
			WProxyComposer.__init__(self, basic_composer)
			self.__key = key
			self.__required = required

		def key(self):
			return self.__key

		def required(self):
			return self.__required

	@verify_type('paranoid', composite_keys=CompositeKey)
	def __init__(self, *composite_keys):
		self.__required_keys = []
		self.__optional_keys = []

		for key in composite_keys:
			self.add_key(key)

	@verify_type(composite_key=CompositeKey)
	def add_key(self, composite_key):
		keys_list = self.__required_keys if composite_key.required() else self.__optional_keys
		keys_list.append(composite_key)

	def required_keys(self):
		return self.__required_keys.copy()

	def optional_keys(self):
		return self.__optional_keys.copy()

	@verify_type(obj_spec=dict)
	def compose(self, obj_spec):
		obj_spec = obj_spec.copy()
		result = self.create_obj()

		for composite_key in self.required_keys():
			key, value = composite_key.decompose(obj_spec)
			obj_spec.pop(key)
			result = self.set_key(result, key, value)

		for composite_key in self.optional_keys():
			key_result = composite_key.decompose(obj_spec)
			if key_result is not None:
				key, value = key_result
				obj_spec.pop(key)
				result = self.set_key(result, key, value)

		if len(obj_spec) > 0:
			raise TypeError('Unable to process every fields')
		return result

	def decompose(self, obj):
		result = {}

		for composite_key in self.required_keys():
			key, value = composite_key.decompose(obj)
			result[key] = value

		for composite_key in self.optional_keys():
			key_result = composite_key.decompose(obj)
			if key_result is not None:
				key, value = key_result
				result[key] = value
		return result

	@abstractmethod
	def create_obj(self):
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def set_key(self, obj, key, value):
		raise NotImplementedError('This method is abstract')


class WDictComposer(WCompositeComposer):

	class DictKey(WCompositeComposer.CompositeKey):

		@verify_type(obj_spec=dict)
		def compose(self, obj_spec):
			key = self.key()
			if key in obj_spec:
				return key, self.basic_composer().compose(obj_spec)
			elif self.required() is True:
				raise TypeError('Required key not found')

		@verify_type(obj=dict)
		def decompose(self, obj):
			key = self.key()
			if key in obj:
				return key, self.basic_composer().decompose(obj[key])
			elif self.required() is True:
				raise TypeError('Required key not found')

	@verify_type('paranoid', composite_keys=DictKey)
	def __init__(self, *composite_keys):
		WCompositeComposer.__init__(self, *composite_keys)

	@verify_type(composite_key=DictKey)
	def add_key(self, composite_key):
		WCompositeComposer.add_key(self, composite_key)

	def create_obj(self):
		return {}

	def set_key(self, obj, key, value):
		obj[key] = value
		return obj


class WClassComposer(WCompositeComposer):

	class ClassKey(WDictComposer.DictKey):

		@verify_type('paranoid', basic_composer=WComposerProto, required=bool)
		@verify_type(key=str)
		@verify_value(key=lambda x: len(x) > 0)
		def __init__(self, key, basic_composer, required=False):
			WDictComposer.DictKey.__init__(self, key, basic_composer, required=required)

		@verify_type(obj=object)
		def decompose(self, obj):
			key = self.key()
			if hasattr(obj, key) is True:
				return key, self.basic_composer().decompose(getattr(obj, key))
			elif self.required() is True:
				raise TypeError('Required key not found')

	@verify_type('paranoid', composite_keys=ClassKey)
	@verify_type(basic_cls=type)
	def __init__(self, basic_cls, *composite_keys):
		WCompositeComposer.__init__(self, *composite_keys)
		self.__basic_cls = basic_cls

	def basic_cls(self):
		return self.__basic_cls

	@verify_type(composite_key=ClassKey)
	def add_key(self, composite_key):
		WCompositeComposer.add_key(self, composite_key)

	def create_obj(self):
		return self.basic_cls()

	def set_key(self, obj, key, value):
		setattr(obj, key, value)
		return obj


class WComposerFactory(WComposerProto):

	class Entry:

		@verify_type(composer=WClassComposer, name=(str, None))
		@verify_value(name=lambda x: x is None or len(x) > 0)
		def __init__(self, composer, name=None):
			self.__composer = composer
			self.__name = name if name is not None else composer.basic_cls().__name__

		def composer(self):
			return self.__composer

		def name(self):
			return self.__name

	__default_name_field__ = '__cls__'
	__default_value_field__ = '__instance__'

	@verify_type('paranoid', entries=Entry)
	@verify_type(name_field=(str, None), value_field=(str, None))
	@verify_value(name_field=lambda x: x is None or len(x) > 0)
	@verify_value(value_field=lambda x: x is None or len(x) > 0)
	def __init__(self, *entries, name_field=None, value_field=None):
		WComposerProto.__init__(self)

		self.__entries = {}
		for entry in entries:
			self.add_entry(entry)

		self.__name_field = name_field if name_field is not None else self.__default_name_field__
		self.__value_field = value_field if value_field is not None else self.__default_value_field__

	@verify_type(entry=Entry)
	def add_entry(self, entry):
		entry_name = entry.name()
		if entry_name in self.__entries.keys():
			raise RuntimeError('Multiple entries with the same name "%s" spotted' % entry_name)
		self.__entries[entry_name] = entry

	def entries(self):
		return self.__entries.copy()

	def name_field(self):
		return self.__name_field

	def value_field(self):
		return self.__value_field

	@verify_type(obj_spec=dict)
	def compose(self, obj_spec):
		name_field = self.name_field()
		value_field = self.value_field()
		if len(obj_spec) != 2 or name_field not in obj_spec.keys() or value_field not in obj_spec.keys():
			raise TypeError('Data malformed')

		entries = self.entries()
		entry_name = obj_spec[name_field]
		entry_value = obj_spec[value_field]

		if entry_name not in entries:
			raise TypeError('Invalid class "%s" was specified' % entry_name)

		entry = entries[entry_name]
		return entry.composer().compose(entry_value)

	@verify_type(obj=object)
	def decompose(self, obj):

		suitable_entries = []
		for entry in self.entries():
			if isinstance(obj, entry.composer().basic_cls()) is True:
				suitable_entries.append(entry)

		entries_count = len(suitable_entries)
		if entries_count == 0:
			raise TypeError(
				'Unable to find suitable entry for "%s" (no one matched)' % obj.__class__.__name__
			)
		elif entries_count > 1:
			reduced_subcls_entries = []
			for i_entry in suitable_entries:
				is_subcls = False
				i_subcls = i_entry.composer().basic_cls()
				for j_entry in suitable_entries:
					j_subcls = j_entry.composer().basic_cls()
					if issubclass(i_subcls, j_subcls) is True:
						is_subcls = True
						break
				if is_subcls is False:
					reduced_subcls_entries.append(is_subcls)

			subcls_entries_count = len(reduced_subcls_entries)
			if subcls_entries_count == 0:
				raise RuntimeError('Internal Error')
			elif subcls_entries_count > 1:
				raise TypeError(
					'Unable to find suitable entry for "%s" (matched two or more entries)' %
					obj.__class__.__name__
				)
			suitable_entries = reduced_subcls_entries

		entry = suitable_entries[0]
		return entry.composer().decompose(obj)
