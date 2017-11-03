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

from wasp_general.verify import verify_type, verify_value, verify_subclass


class WComposerProto(metaclass=ABCMeta):

	@abstractmethod
	def compose(self, obj_spec):
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def decompose(self, obj):
		raise NotImplementedError('This method is abstract')


class WPlainComposer(WComposerProto):

	@verify_subclass(strict_cls=(int, float, str, None))
	def __init__(self, strict_cls=None, permit_none=False):
		WComposerProto.__init__(self)
		self.__strict_cls = strict_cls
		self.__permit_none = permit_none

	def strict_cls(self):
		return self.__strict_cls

	def permit_none(self):
		return self.__permit_none

	@verify_type(obj_spec=(int, float, str, None))
	def compose(self, obj_spec):
		self.__check(obj_spec)
		return obj_spec

	@verify_type(obj_spec=(int, float, str, None))
	def decompose(self, obj):
		self.__check(obj)
		return obj

	def __check(self, obj):
		if obj is None:
			if self.permit_none() is False:
				raise TypeError('None value spotted')
		else:
			strict_cls = self.strict_cls()
			if strict_cls is not None and isinstance(obj, strict_cls) is False:
				raise TypeError(
					'Invalid type ("%s" should be "%s")' %
					(obj.__class__.__name__, strict_cls.__name__)
				)


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

		def compose(self, key_value):
			return self.basic_composer().compose(key_value)

		def decompose(self, key_value):
			return self.basic_composer().decompose(key_value)

		@abstractmethod
		def has_key(self, obj):
			raise NotImplementedError('This method is abstract')

		@abstractmethod
		def get_key(self, obj):
			raise NotImplementedError('This method is abstract')

		@abstractmethod
		def set_key(self, obj, value):
			raise NotImplementedError('This method is abstract')

	class KeyInstance:

		def __init__(self, composite_key, value):
			if isinstance(composite_key, WCompositeComposer.CompositeKey) is False:
				raise TypeError('Invalid composite_key type')

			self.composite_key = composite_key
			self.value = value

	class ConstructionKeys:

		def __init__(self, *key_instances):
			self.__key_instances = []
			for instance in key_instances:
				self.add(instance)

		def add(self, key_instance):
			if isinstance(key_instance, WCompositeComposer.KeyInstance) is False:
				raise TypeError('Invalid construction pair type')
			self.__key_instances.append(key_instance)

		def key_instances(self):
			return self.__key_instances.copy()

		def __getitem__(self, key):
			for instance in self.key_instances():
				if instance.composite_key.key() == key:
					return instance
			raise KeyError('Invalid key: "%s"' % str(key))

		def has_key(self, key):
			for instance in self.key_instances():
				if instance.composite_key.key() == key:
					return True
			return False

		def __iter__(self):
			for pair in self.key_instances():
				yield pair

	class InstanceConstructor(metaclass=ABCMeta):

		def construct_obj(self, construction_keys):
			if isinstance(construction_keys, WCompositeComposer.ConstructionKeys) is False:
				raise TypeError('Invalid construction_keys type')

			result = self.create_obj(construction_keys)
			for instance in construction_keys:
				instance.composite_key.set_key(result, instance.value)
			return result

		@abstractmethod
		def create_obj(self, construction_keys):
			raise NotImplementedError('This method is abstract')


	@verify_type('paranoid', composite_keys=CompositeKey)
	@verify_type(constructor=(InstanceConstructor, None))
	def __init__(self, *composite_keys, constructor=None):
		self.__constructor = \
			constructor if constructor is not None else WCompositeComposer.InstanceConstructor()
		self.__required_keys = []
		self.__optional_keys = []

		for key in composite_keys:
			self.add_composite_key(key)

	def constructor(self):
		return self.__constructor

	@verify_type(composite_key=CompositeKey)
	def add_composite_key(self, composite_key):
		keys_list = self.__required_keys if composite_key.required() else self.__optional_keys
		keys_list.append(composite_key)

	def required_keys(self):
		return self.__required_keys.copy()

	def optional_keys(self):
		return self.__optional_keys.copy()

	@verify_type(obj_spec=dict)
	def compose(self, obj_spec):
		obj_spec = obj_spec.copy()
		construction_keys = WCompositeComposer.ConstructionKeys()

		for composite_key in self.required_keys():
			key = composite_key.key()
			if key not in obj_spec.keys():
				raise TypeError('Required key not found')
			value = composite_key.compose(obj_spec[key])
			obj_spec.pop(key)
			construction_keys.add(WCompositeComposer.KeyInstance(composite_key, value))

		for composite_key in self.optional_keys():
			key = composite_key.key()
			if key in obj_spec.keys():
				value = composite_key.compose(obj_spec[key])
				obj_spec.pop(key)
				construction_keys.add(WCompositeComposer.KeyInstance(composite_key, value))

		if len(obj_spec) > 0:
			raise TypeError('Unable to process every fields')

		return self.constructor().construct_obj(construction_keys)

	def decompose(self, obj):
		result = {}

		for composite_key in self.required_keys():
			if composite_key.has_key(obj) is False:
				raise TypeError('Required key not found')
			value = composite_key.decompose(composite_key.get_key(obj))
			result[composite_key.key()] = value

		for composite_key in self.optional_keys():
			if composite_key.has_key(obj) is True:
				value = composite_key.decompose(composite_key.get_key(obj))
				result[composite_key.key()] = value

		return result


class WDictComposer(WCompositeComposer):

	class DictKey(WCompositeComposer.CompositeKey):

		def has_key(self, obj):
			return self.key() in obj.keys()

		def get_key(self, obj):
			return obj[self.key()]

		def set_key(self, obj, value):
			obj[self.key()] = value
			return obj

	class DictConstructor(WCompositeComposer.InstanceConstructor):

		def create_obj(self, construction_keys):
			return {}

	@verify_type('paranoid', composite_keys=DictKey)
	def __init__(self, *composite_keys):
		WCompositeComposer.__init__(self, *composite_keys, constructor=WDictComposer.DictConstructor())

	@verify_type(composite_key=DictKey)
	def add_composite_key(self, composite_key):
		WCompositeComposer.add_composite_key(self, composite_key)


class WClassComposer(WCompositeComposer):

	class ClassKey(WCompositeComposer.CompositeKey):

		@verify_type('paranoid', basic_composer=WComposerProto, required=bool)
		@verify_type(key=str)
		@verify_value(key=lambda x: len(x) > 0)
		@verify_value(has_key_fn=lambda x: x is None or callable(x))
		@verify_value(get_key_fn=lambda x: x is None or callable(x))
		@verify_value(set_key_fn=lambda x: x is None or callable(x))
		def __init__(
			self, key, basic_composer, has_key_fn=None, get_key_fn=None, set_key_fn=None, required=False
		):
			WCompositeComposer.CompositeKey.__init__(self, key, basic_composer, required=required)
			self.__get_key_fn = get_key_fn
			self.__set_key_fn = set_key_fn
			self.__has_key_fn = has_key_fn

		def has_key(self, obj):
			if self.__has_key_fn is not None:
				return self.__has_key_fn(obj, self.key())
			return hasattr(obj, self.key())

		def get_key(self, obj):
			if self.__get_key_fn is not None:
				return self.__get_key_fn(obj, self.key())
			return getattr(obj, self.key())

		def set_key(self, obj, value):
			if self.__set_key_fn is not None:
				return self.__set_key_fn(obj, self.key(), value)
			setattr(obj, self.key(), value)
			return obj

	class GetterKey(ClassKey):

		def __init__(self, key, basic_composer, required=False):
			WClassComposer.ClassKey.__init__(self, key, basic_composer=basic_composer, required=required)

		def get_key(self, obj):
			return WClassComposer.ClassKey.get_key(self, obj)()

		def set_key(self, obj, value):
			return obj

	class ClassConstructor(WCompositeComposer.InstanceConstructor):

		@verify_type(basic_cls=type)
		@verify_value(create_obj_fn=(lambda x: x is None or callable(x)))
		def __init__(self, basic_cls, create_obj_fn=None):
			self.__basic_cls = basic_cls
			self.__create_obj_fn = create_obj_fn

		def basic_cls(self):
			return self.__basic_cls

		def create_obj(self, construction_keys):
			if self.__create_obj_fn is not None:
				return self.__create_obj_fn(construction_keys)
			return self.basic_cls()()

	@verify_type('paranoid', composite_keys=ClassKey)
	@verify_type(constructor=ClassConstructor)
	def __init__(self, *composite_keys, constructor=None):
		WCompositeComposer.__init__(self, *composite_keys, constructor=constructor)

	@verify_type(composite_key=ClassKey)
	def add_composite_key(self, composite_key):
		WCompositeComposer.add_composite_key(self, composite_key)

	def basic_cls(self):
		return self.constructor().basic_cls()


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

		if entry_name not in entries.keys():
			raise TypeError('Invalid class "%s" was specified' % entry_name)

		entry = entries[entry_name]
		return entry.composer().compose(entry_value)

	@verify_type(obj=object)
	def decompose(self, obj):

		suitable_entries = []
		for entry in self.entries().values():
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
					if issubclass(i_subcls, j_subcls) is True and i_subcls != j_subcls:
						is_subcls = True
						break
				if is_subcls is False:
					reduced_subcls_entries.append(i_entry)

			subcls_entries_count = len(reduced_subcls_entries)
			if subcls_entries_count == 0:
				raise TypeError('Unable to find suitable entry for "%s"' % obj.__class__.__name__)
			elif subcls_entries_count > 1:
				raise TypeError(
					'Unable to find suitable entry for "%s" (matched two or more entries)' %
					obj.__class__.__name__
				)
			suitable_entries = reduced_subcls_entries

		entry = suitable_entries[0]
		decompose_result = {
			self.name_field(): entry.name(),
			self.value_field(): entry.composer().decompose(obj)
		}
		return decompose_result
