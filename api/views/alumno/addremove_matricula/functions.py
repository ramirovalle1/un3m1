# coding=utf-8

from sga.funciones import convertir_fecha_hora, convertir_fecha, convertir_hora
from sga.models import Clase


unicode = str


def to_unicode(s):
    if isinstance(s, unicode):
        return s
    from locale import getpreferredencoding
    for cp in (getpreferredencoding(), "cp1255", "cp1250"):
        try:
            return unicode(s, cp)
        except UnicodeDecodeError:
            pass
        raise Exception("Conversion to unicode failed")


def valida_conflicto_materias_estudiante_enroll(mis_clases):
    clases = []
    for c in mis_clases:
        if c['horarios']:
            for h in c['horarios']:
                clase = h
                if int(clase['tipohorario']) == 1:
                    clases.append({'inicio_comienza': convertir_fecha_hora(f"{clase['inicio']} {clase['comienza']}"),
                                   'inicio': convertir_fecha(f"{clase['inicio']}"),
                                   'comienza': convertir_hora(f"{clase['comienza']}"),
                                   'fin_termina': convertir_fecha_hora(f"{clase['fin']} {clase['termina']}"),
                                   'fin': convertir_fecha(f"{clase['fin']}"),
                                   'termina': convertir_hora(f"{clase['termina']}"),
                                   'id': int(clase['id']),
                                   'tipohorario': int(clase['tipohorario']),
                                   'dia': int(clase['dia']),
                                   })
        if c['mispracticas'] and len(c['mispracticas']) > 0:
            for h in c['mispracticas']['horarios']:
                clase = h
                if int(clase['tipohorario']) == 1:
                    clases.append({'inicio_comienza': convertir_fecha_hora(f"{clase['inicio']} {clase['comienza']}"),
                                   'inicio': convertir_fecha(f"{clase['inicio']}"),
                                   'comienza': convertir_hora(f"{clase['comienza']}"),
                                   'fin_termina': convertir_fecha_hora(f"{clase['fin']} {clase['termina']}"),
                                   'fin': convertir_fecha(f"{clase['fin']}"),
                                   'termina': convertir_hora(f"{clase['termina']}"),
                                   'id': int(clase['id']),
                                   'tipohorario': int(clase['tipohorario']),
                                   'dia': int(clase['dia']),
                                   })
    msg = 'No se registra conflicto de horario'
    if clases:
        for c_1 in clases:
            for c_2 in clases:
                if int(c_1['id']) != int(c_2['id']):
                    if ((c_1['inicio'] >= c_2['inicio'] and c_1['fin'] <= c_2['fin']) or
                        (c_1['inicio'] <= c_2['inicio'] and c_1['fin'] >= c_2['fin']) or
                        (c_1['inicio'] <= c_2['fin'] and c_1['inicio'] >= c_2['inicio']) or
                        (c_1['fin'] >= c_2['inicio'] and c_1['fin'] <= c_2['fin'])):
                        if int(c_1['dia']) == int(c_2['dia']):
                            if (
                                    (c_1['comienza'] <= c_2['termina'] and c_1['termina'] >= c_2['termina'])
                                    or
                                    (c_1['comienza'] <= c_2['comienza'] and c_1['termina'] >= c_2['termina'])
                            ):
                                clase = Clase.objects.get(pk=int(c_1['id']))
                                conflicto = Clase.objects.get(pk=int(c_2['id']))
                                msg = "FCME: conflicto de horario " + to_unicode(clase.materia.asignatura.nombre) + "(" + to_unicode(clase.materia.identificacion) + ") y " + to_unicode(conflicto.materia.asignatura.nombre) + "(" + to_unicode(conflicto.materia.identificacion) + ") DIA: " + conflicto.dia_semana()
                                return True, msg
    return False, msg
