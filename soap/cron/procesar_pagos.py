#!/usr/bin/env python
import threading
import time

from soap.models import PagoBanco


def ProcesaPago(id):
    # retrazo 20 minutos
    time.sleep(1200)
    ePagoBanco = PagoBanco.objects.get(pk=id)
    # ePagoBanco.save(actualiza=True)


class PagoThread(threading.Thread):
    def __init__(self, id):
        self.id = id
        threading.Thread.__init__(self)

    def run(self):
        if self.id:
            ProcesaPago(self.id)


def ActualizaPago(id):
    try:
        if id:
            PagoThread(id).start()
    except Exception as ex:
        pass

