#!/usr/bin/env python
import threading

from sga.models import Periodo, RespuestaEvaluacionAcreditacion, RespuestaRubrica, Profesor


def ProcesaEvaluacion(id, idp):
    profesor = Profesor.objects.get(pk=id)
    periodo = Periodo.objects.get(pk=idp)
    # distributivo = profesor.distributivohoraseval(periodo)
    # resumen = distributivo.resumen_evaluacion_acreditacion()
    # resumen.actualizar_resumen()

class EvaluacionThread(threading.Thread):
    def __init__(self, id, idp):
        self.id = id
        self.idp = idp
        threading.Thread.__init__(self)

    def run(self):
        if self.id and self.idp:
            ProcesaEvaluacion(self.id, self.idp)

def ActualizaEvaluacion(id, idp):
    try:
        if id and idp:
            EvaluacionThread(id, idp).start()
    except Exception as ex:
        pass


def RespuestaEvaluacion(id):
    evaluacion = RespuestaEvaluacionAcreditacion.objects.get(pk=id)
    evaluacion.save(actualiza=True)


class RespuestaEvaluacionThread(threading.Thread):
    def __init__(self, id):
        self.id = id
        threading.Thread.__init__(self)

    def run(self):
        if self.id:
            RespuestaEvaluacion(self.id)


def ActualizaRespuestaEvaluacion(id):
    try:
        if id:
            RespuestaEvaluacionThread(id).start()
    except Exception as ex:
        pass

def RespuestaRubricaEvaluacion(id):
    evaluacion = RespuestaRubrica.objects.get(pk=id)
    evaluacion.save(actualiza=True)


class RespuestaRubricaThread(threading.Thread):
    def __init__(self, id):
        self.id = id
        threading.Thread.__init__(self)

    def run(self):
        if self.id:
            RespuestaRubricaEvaluacion(self.id)


def ActualizaRespuestaRubrica(id):
    try:
        if id:
            RespuestaRubricaThread(id).start()
    except Exception as ex:
        pass
