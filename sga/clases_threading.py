#!/usr/bin/env python
import threading

from sga.models import MateriaAsignada


def ProcesaAsistencia(id):
    from sga.funciones import actualiza_asistencia
    # materiaasignada = MateriaAsignada.objects.get(pk=id)
    actualiza_asistencia(materiaasignada_id=id)
    # materiaasignada.save(actualiza=True)


class AsistenciaThread(threading.Thread):
    def __init__(self, id):
        self.id = id
        threading.Thread.__init__(self)

    def run(self):
        if self.id:
            ProcesaAsistencia(self.id)


def ActualizaAsistencia(id):
    try:
        if id:
            AsistenciaThread(id).start()
    except Exception as ex:
        pass
