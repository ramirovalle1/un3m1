# -*- coding: UTF-8 -*-
import sys
from sga.funciones import ModeloBase


def api_list_classes():
    listclass = []
    current_module = sys.modules[__name__]
    for key in dir(current_module):
        if isinstance(getattr(current_module, key), type):
            try:
                a = eval(key + '.objects')
                listclass.append(key)
            except:
                pass
    return listclass

