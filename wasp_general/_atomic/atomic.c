//wasp_general/_atomic/atomic.py
//
//Copyright (C) 2016 the wasp-general authors and contributors
//<see AUTHORS file>
//
//This file is part of wasp-general.
//
//Wasp-general is free software: you can redistribute it and/or modify
//it under the terms of the GNU Lesser General Public License as published by
//the Free Software Foundation, either version 3 of the License, or
//(at your option) any later version.
//
//Wasp-general is distributed in the hope that it will be useful,
//but WITHOUT ANY WARRANTY; without even the implied warranty of
//MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//GNU Lesser General Public License for more details.
//
//You should have received a copy of the GNU Lesser General Public License
//along with wasp-general.  If not, see <http://www.gnu.org/licenses/>.

// TODO: add documentation

#include <Python.h>
#include <stddef.h>

typedef struct {
	PyObject_HEAD
	PyLongObject* __int_value;
	PyObject *weakreflist;
} WAtomicCounterObject;

PyObject* __int_add_fn__ = 0;

PyMODINIT_FUNC PyInit_atomic(void);
static PyObject* WAtomicCounterType_new(PyTypeObject* type, PyObject* args, PyObject* kwargs);
static int WAtomicCounterObject_init(WAtomicCounterObject *self, PyObject *args, PyObject *kwargs);
static void WAtomicCounterType_dealloc(WAtomicCounterObject* self);
static PyObject* WAtomicCounterObject____int__(WAtomicCounterObject* self, PyObject *args);
static PyObject* WAtomicCounterObject_increase_counter(WAtomicCounterObject* self, PyObject* args);

static struct PyModuleDef wasp_general_atomic_module = {
	PyModuleDef_HEAD_INIT,
	.m_name = __MODULE_NAME__,
	.m_doc =
		"This module "__MODULE_NAME__" contains a "__ATOMIC_COUNTER_NAME__" class that may be used as a"
		" counter which modification via "__ATOMIC_COUNTER_NAME__".increase method call is atomic (is"
		" thread safe)"
	,
	.m_size = -1,
};

static PyMethodDef WAtomicCounterType_methods[] = {
	{
		"__int__", (PyCFunction) WAtomicCounterObject____int__, METH_NOARGS,
		"Return reference to integer object that is used for internal counter value"
	},
	{
		"increase_counter", (PyCFunction) WAtomicCounterObject_increase_counter, METH_VARARGS,
		"Increase current counter value and return a result\n"
		"\n"
		":param value: increment with which counter value should be increased (may be negative)\n"
		":return: int"
	},

	{NULL}
};

static PyTypeObject WAtomicCounterType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	.tp_name = __MODULE_NAME__"."__ATOMIC_COUNTER_NAME__,
	.tp_doc = "Counter with atomic increase operation",
	.tp_basicsize = sizeof(WAtomicCounterType),
	.tp_itemsize = 0,
	//.tp_flags = Py_TPFLAGS_DEFAULT,
	.tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
	.tp_new = WAtomicCounterType_new,
	.tp_init = (initproc) WAtomicCounterObject_init,
	.tp_dealloc = (destructor) WAtomicCounterType_dealloc,
	.tp_methods = WAtomicCounterType_methods,
	.tp_weaklistoffset = offsetof(WAtomicCounterObject, weakreflist)
};

PyMODINIT_FUNC PyInit_atomic(void) {

	__int_add_fn__ = PyObject_GetAttrString((PyObject*) &PyLong_Type, "__add__");
        if (__int_add_fn__ == NULL) {
		return NULL;
        }

	PyObject *m;

	if (PyType_Ready(&WAtomicCounterType) < 0)
		return NULL;

	m = PyModule_Create(&wasp_general_atomic_module);
	if (m == NULL)
		return NULL;

	Py_INCREF(&WAtomicCounterType);
	PyModule_AddObject(m, __ATOMIC_COUNTER_NAME__, (PyObject*) &WAtomicCounterType);

	return m;
}

static PyObject* WAtomicCounterType_new(PyTypeObject* type, PyObject* args, PyObject* kwargs) {

	WAtomicCounterObject* self;
	self = (WAtomicCounterObject *) type->tp_alloc(type, 0);

	if (self != NULL) {
		self->__int_value = (PyLongObject*) PyLong_FromLong(0);
		if (self->__int_value == NULL) {
			Py_DECREF(self);
			return NULL;
		}
	}

	return (PyObject *) self;
}

static int WAtomicCounterObject_init(WAtomicCounterObject *self, PyObject *args, PyObject *kwargs) {

	static char *kwlist[] = {"value", NULL};
	PyObject* value = NULL;

	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|O!", kwlist,  &PyLong_Type, &value))
		return -1;

	if (value) {
		Py_DECREF(self->__int_value);
		self->__int_value = (PyLongObject*) value;
		Py_INCREF(self->__int_value);
	}
	return 0;
}

static void WAtomicCounterType_dealloc(WAtomicCounterObject* self) {
	if (self->weakreflist != NULL)
        	PyObject_ClearWeakRefs((PyObject *) self);

	Py_DECREF(self->__int_value);
	Py_TYPE(self)->tp_free((PyObject *) self);
}

static PyObject* WAtomicCounterObject____int__(WAtomicCounterObject* self, PyObject *args) {
	Py_INCREF(self->__int_value);
	return (PyObject*) self->__int_value;
}

static PyObject* WAtomicCounterObject_increase_counter(WAtomicCounterObject* self, PyObject* args)
{
	PyObject* increment;
	if (!PyArg_ParseTuple(args, "O!", &PyLong_Type, &increment))
		return NULL;
	Py_INCREF(increment);

	PyObject* increase_fn_args = PyTuple_Pack(2, self->__int_value, increment);
	if (increase_fn_args == NULL){
		return NULL;
	}

	PyObject* increment_result = PyObject_CallObject(__int_add_fn__, increase_fn_args);
	if (increment_result == NULL){
		return NULL;
	}

	Py_DECREF(self->__int_value);
	self->__int_value = (PyLongObject*) increment_result;
	Py_DECREF(increment);
	Py_DECREF(increase_fn_args);

	Py_INCREF(self->__int_value);
	return (PyObject*) self->__int_value;
}
