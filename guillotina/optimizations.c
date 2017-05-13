#include <Python.h>
#include <frameobject.h>

static PyObject *RequestNotFound, *Request;

/* current_request frame obtainer */

/*
  useful documentation
  - https://docs.python.org/3/c-api/intro.html
  - https://docs.python.org/3/c-api/object.html#c.PyObject_GetAttr
    - returns new reference
  - https://docs.python.org/3.6/c-api/dict.html#c.PyDict_GetItem
    - returns barrowed reference
*/
static PyObject*
current_request()
{
    PyFrameObject *f = PyThreadState_GET()->frame;
    int found = 0;
    PyObject *request = NULL;
    PyObject *self;
    while (found == 0 && f != NULL) {
      if (PyFrame_FastToLocalsWithError(f) < 0){
        return NULL;
      }
      Py_INCREF(f->f_locals);

      if (PyDict_CheckExact(f->f_locals)) {

        self = PyDict_GetItem(f->f_locals, PyUnicode_FromString("self"));
        if (self != NULL &&
            PyObject_HasAttr(self, PyUnicode_FromString("request"))) {
          request = PyObject_GetAttr(self, PyUnicode_FromString("request"));
          if(request != NULL){
            // PyObject_GetAttr does not require Py_INCREF
            found = 1;
            Py_DECCREF(f->f_locals);
            break;
          }
        }

        request = PyDict_GetItem(f->f_locals, PyUnicode_FromString("request"));
        if (request != NULL) {
          // If we return the value from a PyDict_GetItem
          // it is expected that you use Py_INCREF
          Py_INCREF(request);
          found = 1;
          Py_DECCREF(f->f_locals);
          break;
        }

      }
      Py_DECCREF(f->f_locals);
      f = f->f_back;
    }


    if (f == NULL) {
        PyErr_SetString(RequestNotFound,
                        "Could not find the request");
        return NULL;
    }

    return (PyObject*)request;
}


static PyMethodDef OptimizationsMethods[] =
{
     {"get_current_request", current_request, METH_VARARGS,
      "Return the current request by heuristically looking it up from stack"},
     {NULL, NULL, 0, NULL}
};


PyMODINIT_FUNC
PyInit_optimizations(void)
{

    PyObject* m;

  static struct PyModuleDef moduledef = {
         PyModuleDef_HEAD_INIT,
         "optimizations",
         "Optimizations guillotina server", -1, OptimizationsMethods, };
    PyObject* ob = PyModule_Create(&moduledef);

  if (ob == NULL)
  {
      return NULL;
  }

    if ((m = PyImport_ImportModule("guillotina.exceptions")) == NULL)
    {
      return NULL;
    }

    RequestNotFound = PyObject_GetAttrString(m, "RequestNotFound");
    if (RequestNotFound == NULL)
    {
      return NULL;
    }
    Py_DECREF(m);

    if ((m = PyImport_ImportModule("aiohttp.web")) == NULL)
    {
      return NULL;
    }
    if ((Request = PyObject_GetAttrString(m, "Request")) == NULL)
    {
      return NULL;
    }
    Py_DECREF(m);

  return ob;
}
