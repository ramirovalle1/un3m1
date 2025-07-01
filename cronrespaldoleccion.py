#!/usr/bin/env python

import os
import sys

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from django.db import transaction
from sga.models import Periodo
from sga.models import Leccion, LeccionGrupo, RegistraLeccion, Incidencia, \
    EvaluacionLeccion, AsistenciaLeccion, JustificacionAusenciaAsistenciaLeccion, \
    PracticaPreProfesional, ParticipantePracticaPreProfesional, TemaAsistencia, SubTemaAsistencia
from sga.models import Leccion_Historico, LeccionGrupo_Historico, RegistraLeccion_Historico, Incidencia_Historico, \
    EvaluacionLeccion_Historico, AsistenciaLeccion_Historico, JustificacionAusenciaAsistenciaLeccion_Historico, \
    PracticaPreProfesional_Historico, ParticipantePracticaPreProfesional_Historico, TemaAsistencia_Historico, SubTemaAsistencia_Historico


def enviar_mensaje_bot_telegram(mensaje):
    import requests
    json_arr = []
    try:
        api = '1954045154:AAFK8CJo2Wr3nWpS-acBRgchZzcz2qxUKSU'
        cgomez, clocke, rviteri = '', '838621184', ''
        chats = [rviteri]
        for x in chats:
            data = {'chat_id': x, 'text': mensaje, 'parse_mode': 'HTML'}
            url = "https://api.telegram.org/bot{}/sendMessage".format(api)
            json_arr.append(requests.post(url, data).json())
    except Exception as ex:
        print("TELEGRAM ERROR" + str(ex))
    return json_arr


def respaldarlecciongrupos():
    try:
        periodolist_ = Periodo.objects.filter(status=True, leccion_dismigrar=True, leccion_migracion=False)
        for periodo_ in periodolist_:
            print('---------------------------------------------------------------------------------------------------------------------------------')
            print('PERIODO: {}'.format(periodo_.__str__()))

            eLeccionGrupos = LeccionGrupo.objects.db_manager('sga_select').filter(lecciones__clase__materia__nivel__periodo_id=periodo_.id).distinct()
            totalLeccionGrupo = len(eLeccionGrupos)
            print(f"Lecciones Grupos: {totalLeccionGrupo}")
            tt = 0
            for l in eLeccionGrupos:
                tt += 1
                print(f"({tt}/{totalLeccionGrupo}) LeccionGrupo: {l.__str__()}")
                lecciongrupo_ = LeccionGrupo_Historico(usuario_creacion=l.usuario_creacion, fecha_creacion=l.fecha_creacion, usuario_modificacion=l.usuario_modificacion, fecha_modificacion=l.fecha_modificacion)
                lecciongrupo_.profesor = l.profesor
                lecciongrupo_.turno = l.turno
                lecciongrupo_.aula = l.aula
                lecciongrupo_.dia = l.dia
                lecciongrupo_.fecha = l.fecha
                lecciongrupo_.horaentrada = l.horaentrada
                lecciongrupo_.horasalida = l.horasalida
                lecciongrupo_.abierta = l.abierta
                lecciongrupo_.contenido = l.contenido
                lecciongrupo_.estrategiasmetodologicas = l.estrategiasmetodologicas
                lecciongrupo_.observaciones = l.observaciones
                lecciongrupo_.motivoapertura = l.motivoapertura
                lecciongrupo_.origen_movil = l.origen_movil
                lecciongrupo_.origen_coordinador = l.origen_coordinador
                lecciongrupo_.automatica = l.automatica
                lecciongrupo_.solicitada = l.solicitada
                lecciongrupo_.ipingreso = l.ipingreso
                lecciongrupo_.ipexterna = l.ipexterna
                lecciongrupo_.save()
                # eLeccion = Leccion.objects.db_manager('sga_select').filter(status=True, clase__materia__nivel__periodo_id=periodo_.id)
                eLeccion = l.mis_leciones()
                total_leccion = len(eLeccion)
                print(f"Lecciones: {total_leccion}...")
                tt2 = 0
                for l in eLeccion:
                    print(f'({tt2}/{total_leccion}) {l.__str__()}')
                    _leccion_ = l
                    tt2 += 1
                    leccion_ = Leccion_Historico(usuario_creacion=l.usuario_creacion, fecha_creacion=l.fecha_creacion, usuario_modificacion=l.usuario_modificacion, fecha_modificacion=l.fecha_modificacion)
                    leccion_.clase = l.clase
                    leccion_.fecha = l.fecha
                    leccion_.horaentrada = l.horaentrada
                    leccion_.horasalida = l.horasalida
                    leccion_.abierta = l.abierta
                    leccion_.contenido = l.contenido
                    leccion_.estrategiasmetodologicas = l.estrategiasmetodologicas
                    leccion_.observaciones = l.observaciones
                    leccion_.ipingreso = l.ipingreso
                    leccion_.ipexterna = l.ipexterna
                    leccion_.motivoapertura = l.motivoapertura
                    leccion_.origen_movil = l.origen_movil
                    leccion_.origen_coordinador = l.origen_coordinador
                    leccion_.automatica = l.automatica
                    leccion_.solicitada = l.solicitada
                    leccion_.aperturaleccion = l.aperturaleccion
                    leccion_.save()
                    # GUARDAR LECCION EN GRUPO
                    lecciongrupo_.lecciones.add(leccion_)
                    # GUARDAR LECCION EN GRUPO

                    ePracticas = PracticaPreProfesional.objects.db_manager('sga_select').filter(status=True, leccion=_leccion_)
                    total_practicas = len(ePracticas)
                    print(f"-Practicas Pre Profesionales: {total_practicas}...")
                    tt3 = 0
                    for l in ePracticas:
                        tt3 += 1
                        practica_ = PracticaPreProfesional_Historico(usuario_creacion=l.usuario_creacion, fecha_creacion=l.fecha_creacion, usuario_modificacion=l.usuario_modificacion, fecha_modificacion=l.fecha_modificacion)
                        practica_.materia = l.materia
                        practica_.profesor = l.profesor
                        practica_.lugar = l.lugar
                        practica_.horas = l.horas
                        practica_.fecha = l.fecha
                        practica_.objetivo = l.objetivo
                        practica_.cerrado = l.cerrado
                        practica_.calificar = l.calificar
                        practica_.calfmaxima = l.calfmaxima
                        practica_.calfminima = l.calfminima
                        practica_.grupopractica = l.grupopractica
                        practica_.leccion = leccion_
                        practica_.save()

                        eParticipantePracticas = ParticipantePracticaPreProfesional.objects.db_manager('sga_select').filter(status=True, practica=l)
                        total_participante_practicas = len(eParticipantePracticas)
                        print(f"--Participante Practicas Pre Profesionales: {total_participante_practicas}...")
                        tt4 = 0
                        for l in eParticipantePracticas:
                            tt4 += 1
                            participante_ = ParticipantePracticaPreProfesional_Historico(usuario_creacion=l.usuario_creacion, fecha_creacion=l.fecha_creacion, usuario_modificacion=l.usuario_modificacion, fecha_modificacion=l.fecha_modificacion)
                            participante_.practica = practica_
                            participante_.materiaasignada = l.materiaasignada
                            participante_.nota = l.nota
                            participante_.asistencia = l.asistencia
                            participante_.observacion = l.observacion
                            participante_.estado = l.estado
                            participante_.asistencialeccion = l.asistencialeccion
                            participante_.save()

                    eEvaluacion = EvaluacionLeccion.objects.db_manager('sga_select').filter(status=True, leccion=_leccion_)
                    total_evaluacion = len(eEvaluacion)
                    print(f"-Evaluación Lección: {total_evaluacion}...")
                    tt5 = 0
                    for l in eEvaluacion:
                        tt5 += 1
                        eva_ = EvaluacionLeccion_Historico(usuario_creacion=l.usuario_creacion, fecha_creacion=l.fecha_creacion, usuario_modificacion=l.usuario_modificacion, fecha_modificacion=l.fecha_modificacion)
                        eva_.evaluacion = l.evaluacion
                        eva_.materiaasignada = l.materiaasignada
                        eva_.leccion = leccion_
                        eva_.save()

                    eAsistenciaLeccion = AsistenciaLeccion.objects.db_manager('sga_select').filter(status=True, leccion=_leccion_)
                    total_asistencia = len(eAsistenciaLeccion)
                    print(f"-Asistencia Lección: {total_asistencia}...")
                    tt6 = 0
                    for l in eAsistenciaLeccion:
                        tt6 += 1
                        asistencia_ = AsistenciaLeccion_Historico(usuario_creacion=l.usuario_creacion, fecha_creacion=l.fecha_creacion, usuario_modificacion=l.usuario_modificacion, fecha_modificacion=l.fecha_modificacion)
                        asistencia_.materiaasignada = l.materiaasignada
                        asistencia_.asistenciajustificada = l.asistenciajustificada
                        asistencia_.asistio = l.asistio
                        asistencia_.leccion = leccion_
                        asistencia_.save()

                        eJustiAsistencia = JustificacionAusenciaAsistenciaLeccion.objects.db_manager('sga_select').filter(status=True, asistencialeccion=l)
                        total_justificacion = len(eJustiAsistencia)
                        print(f"--Justificación Asistencia Lección: {total_justificacion}...")
                        tt7 = 0
                        for l in eJustiAsistencia:
                            tt7 += 1
                            justi_ = JustificacionAusenciaAsistenciaLeccion_Historico(usuario_creacion=l.usuario_creacion, fecha_creacion=l.fecha_creacion, usuario_modificacion=l.usuario_modificacion, fecha_modificacion=l.fecha_modificacion)
                            justi_.porcientojustificado = l.porcientojustificado
                            justi_.motivo = l.motivo
                            justi_.fecha = l.fecha
                            justi_.persona = l.persona
                            justi_.asistencialeccion = asistencia_
                            justi_.save()

                    eTemaAsistenciaLeccion = TemaAsistencia.objects.db_manager('sga_select').filter(status=True, leccion=_leccion_)
                    total_temaasistencia = len(eTemaAsistenciaLeccion)
                    print(f"-Tema Asistencia Lección: {total_temaasistencia}...")
                    tt8 = 0
                    for l in eTemaAsistenciaLeccion:
                        tt += 1
                        temaasistencia_ = TemaAsistencia_Historico(usuario_creacion=l.usuario_creacion, fecha_creacion=l.fecha_creacion, usuario_modificacion=l.usuario_modificacion, fecha_modificacion=l.fecha_modificacion)
                        temaasistencia_.tema = l.tema
                        temaasistencia_.fecha = l.fecha
                        temaasistencia_.leccion = leccion_
                        temaasistencia_.save()

                        eSubTemaAsistencia = SubTemaAsistencia.objects.db_manager('sga_select').filter(status=True, asistencialeccion=l)
                        total_subtema = len(eSubTemaAsistencia)
                        print(f"--SubTema Asistencia Lección: {total_subtema}...")
                        tt8 = 0
                        for l in eSubTemaAsistencia:
                            tt += 1
                            justi_ = SubTemaAsistencia_Historico(usuario_creacion=l.usuario_creacion, fecha_creacion=l.fecha_creacion, usuario_modificacion=l.usuario_modificacion, fecha_modificacion=l.fecha_modificacion)
                            justi_.subtema = l.subtema
                            justi_.fecha = l.fecha
                            justi_.tema = temaasistencia_
                            justi_.save()
                    print('------------------------------------------------------------')

    except Exception as ex:
        textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
        print(textoerror)


respaldarlecciongrupos()