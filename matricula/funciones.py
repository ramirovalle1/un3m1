# coding=latin-1
import json
import os
import random
from hashlib import md5
from secrets import token_hex
from cgitb import html
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen, Request

import pyqrcode
from django.db import connection, transaction, connections
from django.db.models import F, Sum
from django.db.models import Q
from django.db.models.aggregates import Count, Max
from django.http import JsonResponse
from decimal import Decimal

from api.serializers.alumno.matriculacion import MatriMateriaSerializer
from bd.funciones import generate_code
from bd.models import UserToken
from core.cache import CacheRedisProxy
from inno.models import PeriodoMalla, DetallePeriodoMalla, RequisitoIngresoUnidadIntegracionCurricular, ExtraPreInscripcionPracticasPP, ExtraDetallePreInscripcionPracticasPP
from matricula.models import PeriodoMatricula, MateriaAsignadaToken, MatriculaToken, SolicitudMatriculaEspecial
from settings import MATRICULACION_LIBRE, MATRICULACION_POR_NIVEL, HOMITIRCAPACIDADHORARIO, NOTA_ESTADO_EN_CURSO, \
    RUBRO_ARANCEL, RUBRO_MATRICULA, PORCENTAJE_MULTA, DEBUG, TIPO_DOCENTE_PRACTICA, EMAIL_DOMAIN, NIVEL_MALLA_CERO, \
    NIVEL_MALLA_UNO, SITE_STORAGE
from sga.funciones import variable_valor, null_to_numeric, convertir_fecha_invertida_hora, convertir_fecha_hora, \
    convertir_fecha_invertida, convertir_hora, convertir_fecha, fechatope, log, null_to_decimal, generar_codigo, generar_nombre
from sga.funcionesxhtml2pdf import conviert_html_to_pdf_save_file_model
from sga.models import Nivel, TipoProfesor, Clase, Inscripcion, Materia, GruposProfesorMateria, Matricula, \
    MateriaAsignada, ProfesorMateria, AlumnosPracticaMateria, AsignaturaMalla, PerdidaGratuidad, \
    ConfirmaCapacidadTecnologica, miinstitucion, CUENTAS_CORREOS, LogReporteDescarga, Sesion, PreInscripcionPracticasPP, \
    DetallePreInscripcionPracticasPP, DetalleRecoridoPreInscripcionPracticasPP
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt

unicode = str
TIPO_PROFESOR_PRACTICA = 2
TIPO_PROFESOR_PRACTICA_SALUD = 13


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


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def valid_intro_module_estudiante(request, level=None):
    try:
        perfilprincipal = request.session['perfilprincipal']

        if not perfilprincipal.es_estudiante():
            raise NameError(u"Solo los perfiles de aspirante pueden ingresar al modulo.")
        if not level or not level in ['admision', 'pregrado', 'posgrado']:
            raise NameError(u"Solicitud no identificada")

        inscripcion = perfilprincipal.inscripcion

        if level == 'admision':
            if not inscripcion.mi_coordinacion().id in [9]:
                raise NameError(u"Estimado/a aspirante, este módulo solo se encuentra activo para estudiantes de admisión")
        elif level == 'pregrado':
            if not inscripcion.mi_coordinacion().id in [1, 2, 3, 4, 5]:
                raise NameError(u"Estimado/a estudiante, este módulo solo se encuentra activo para estudiantes de pregrado")
        elif level == 'posgrado':
            if not inscripcion.mi_coordinacion().id in [7, 10]:
                raise NameError(u"Estimado/a estudiante, este módulo solo se encuentra activo para estudiantes de posgrado")

        if inscripcion.bloqueomatricula:
            raise NameError(u"Estimado/a, su matrícula se encuentra bloqueada, por favor contactarse con secretaria de la coordinación")
        if inscripcion.graduado() or inscripcion.egresado() or inscripcion.estainactivo() or inscripcion.retiro_carrera():
            raise NameError(u"Estimado/a, solo se permiten aspirantes activos")
        return True, None
    except Exception as ex:
        return False, ex.__str__()


def get_nivel_matriculacion(inscripcion, periodo):
    nivel = None
    if not MATRICULACION_LIBRE:
        # MATERIAS POR NIVEL
        if MATRICULACION_POR_NIVEL:
            minivelmalla = inscripcion.mi_nivel().nivel
            # MATRICULACION SEGUN NIVEL MALLA O GRUPO
            materias_ingles = Materia.objects.filter(status=True, asignaturamalla__malla_id__in=[353], nivel__periodo=periodo).values_list('nivel_id', flat=True)
            if Nivel.objects.values('id').filter(periodo=periodo, nivelgrado=False, nivelmalla__gte=minivelmalla, modalidad=inscripcion.modalidad, sesion=inscripcion.sesion, sede=inscripcion.sede, carrera=inscripcion.carrera, cerrado=False, fin__gt=datetime.now().date()).exclude(id__in=materias_ingles).exists():
                for nivelseleccion in Nivel.objects.filter(periodo=periodo, nivelgrado=False, nivelmalla__gte=minivelmalla, modalidad=inscripcion.modalidad, sesion=inscripcion.sesion, sede=inscripcion.sede, carrera=inscripcion.carrera, cerrado=False, fin__gt=datetime.now().date()).exclude(id__in=materias_ingles).order_by('nivelmalla', 'id'):
                    if nivelseleccion.capacidadmatricula > nivelseleccion.matricula_set.count() and nivelseleccion.pagonivel_set.exists():
                        nivel = nivelseleccion
                        break
                if not nivel:
                    return -3
            else:
                return -4
        else:
            grupo = inscripcion.grupo()
            for nivelseleccion in Nivel.objects.annotate(periodo=periodo, matriculados=Count('matricula')).filter(capacidadmatricula__gt=F("matriculados")).filter(grupo=grupo, nivelgrado=False, cerrado=False, fin__gt=datetime.now().date()).order_by('id'):
                if nivelseleccion.capacidadmatricula > nivelseleccion.matricula_set.count() and nivelseleccion.pagonivel_set.exists():
                    nivel = nivelseleccion
                    break
            if not nivel:
                return -2
    else:
        # MATERIAS X LIBRES X COORDINACIONES
        # HABILITAR PARA EL PROXIMO PERIODO
        materias_ingles = Materia.objects.filter(status=True, asignaturamalla__malla_id__in=[353], nivel__periodo=periodo).values_list('nivel_id', flat=True)
        if Nivel.objects.values('id').filter(periodo=periodo, nivellibrecoordinacion__coordinacion__carrera=inscripcion.carrera, nivellibrecoordinacion__coordinacion__sede=inscripcion.sede, sesion=inscripcion.sesion, cerrado=False, fin__gte=datetime.now().date()).exclude(id__in=materias_ingles).exists():
            nivel = Nivel.objects.filter(periodo=periodo, nivellibrecoordinacion__coordinacion__carrera=inscripcion.carrera, nivellibrecoordinacion__coordinacion__sede=inscripcion.sede, sesion=inscripcion.sesion, cerrado=False, fin__gte=datetime.now().date()).exclude(id__in=materias_ingles).order_by('-fin')[0]
        else:
            return -1
    return nivel.id


def puede_matricularse_seguncronograma_carrera(inscripcion, periodo):
    minivel = inscripcion.mi_nivel().nivel
    hoy = datetime.now().date()
    cronograma = None
    if periodo.periodomatriculacion_set.filter(status=True, carrera=inscripcion.carrera, nivelmalla=minivel, modalidad=inscripcion.modalidad).exists():
        cronograma = periodo.periodomatriculacion_set.filter(status=True, carrera=inscripcion.carrera, nivelmalla=minivel, modalidad=inscripcion.modalidad)[0]
    elif periodo.periodomatriculacion_set.filter(status=True, carrera=inscripcion.carrera, nivelmalla=minivel, modalidad=None).exists():
        cronograma = periodo.periodomatriculacion_set.filter(status=True, carrera=inscripcion.carrera, nivelmalla=minivel, modalidad=None)[0]
    elif periodo.periodomatriculacion_set.filter(status=True, carrera=inscripcion.carrera, nivelmalla=None, modalidad=inscripcion.modalidad).exists():
        cronograma = periodo.periodomatriculacion_set.filter(status=True, carrera=inscripcion.carrera, nivelmalla=None, modalidad=inscripcion.modalidad)[0]
    elif periodo.periodomatriculacion_set.filter(status=True, carrera=inscripcion.carrera, nivelmalla=None, modalidad=None).exists():
        cronograma = periodo.periodomatriculacion_set.filter(status=True, carrera=inscripcion.carrera, nivelmalla=None, modalidad=None)[0]
    if cronograma:
        if cronograma.prematricula:
            prematricula = inscripcion.mi_prematricula(periodo)
            if cronograma.fecha_inicio <= hoy <= cronograma.fecha_fin:
                if prematricula:
                    if cronograma.fecha_inicio <= hoy <= cronograma.fecha_fin:
                        return [1]
                    else:
                        return [2, cronograma]
                else:
                    fechapermite = (datetime(cronograma.fecha_inicio.year, cronograma.fecha_inicio.month, cronograma.fecha_inicio.day, 0, 0, 0) + timedelta(days=cronograma.dias)).date()
                    if hoy >= fechapermite and cronograma.fecha_inicio <= hoy <= cronograma.fecha_fin:
                        return [1]
                    else:
                        return [3, cronograma]
            else:
                if hoy <= cronograma.fecha_fin:
                    return [2, cronograma]
                else:
                    return [4, cronograma]
        else:
            if cronograma.fecha_inicio <= hoy <= cronograma.fecha_fin:
                return [1]
            else:
                if hoy <= cronograma.fecha_fin:
                    return [2, cronograma]
                else:
                    return [4, cronograma]
    return [1]


def puede_matricularse_seguncronograma_coordinacion(inscripcion, periodo):
    # hoy_date = datetime.now().date()
    # hoy_time = datetime.now().time()
    coordinacion = inscripcion.coordinacion
    carrera = inscripcion.carrera
    nivelmalla = inscripcion.mi_nivel()
    if coordinacion.id == 1 and nivelmalla.nivel_id >= 7:
        return True
    # cronograma = None
    # periodomatricula = None
    if not periodo.periodomatricula_set.values('id').filter(status=True, activo=True).exists():
        return False
    periodomatricula = periodo.periodomatricula_set.filter(status=True, activo=True)
    if not periodomatricula.values('id').filter(valida_cronograma=True).exists():
        return True
    periodomatricula = periodomatricula[0]
    if not periodomatricula.tiene_coordincaciones():
        return True
    if not coordinacion.id in periodomatricula.coordinaciones().values_list("id", flat=True):
        return True
    if not periodomatricula.tiene_cronograma_coordinaciones():
        return True
    cronogramacoordinacion = periodomatricula.cronograma_coordinaciones()
    if not coordinacion.id in list(cronogramacoordinacion.values_list('coordinacion_id', flat=True)):
        return False
    cronogramacoordinacion = cronogramacoordinacion.filter(coordinacion=coordinacion)[0]
    if not cronogramacoordinacion.activo:
        return False
    fhInicioCoordinacion = datetime.combine(cronogramacoordinacion.fechainicio, cronogramacoordinacion.horainicio)
    fhFinCoordinacion = datetime.combine(cronogramacoordinacion.fechafin, cronogramacoordinacion.horafin)
    if not (fhInicioCoordinacion <= datetime.now() <= fhFinCoordinacion):
        return False
    if not cronogramacoordinacion.tiene_cronogramacarreras():
        return True
    cronogramacarrera = cronogramacoordinacion.cronogramacarreras()
    if not carrera.id in list(cronogramacarrera.values_list('carrera_id', flat=True)):
        return True

    if (cronograma := cronogramacarrera.filter(nivel__isnull=True, sesion__isnull=True, carrera=carrera).first()) is not None:
        if not cronograma.activo:
            return False
        fhInicioCarrera = datetime.combine(cronograma.fechainicio, cronograma.horainicio)
        fhFinCarrera = datetime.combine(cronograma.fechafin, cronograma.horafin)
        if not (fhInicioCarrera <= datetime.now() <= fhFinCarrera):
            return False
    elif (cronograma := cronogramacarrera.filter(carrera=carrera, nivel__id=nivelmalla.nivel_id, sesion__id=inscripcion.sesion_id).first()) is not None:
        if not cronograma.activo:
            return False
        fhInicioCarrera = datetime.combine(cronograma.fechainicio, cronograma.horainicio)
        fhFinCarrera = datetime.combine(cronograma.fechafin, cronograma.horafin)
        if not (fhInicioCarrera <= datetime.now() <= fhFinCarrera):
            return False
    elif (cronograma := cronogramacarrera.filter(carrera=carrera, nivel__isnull=True, sesion__id=inscripcion.sesion_id).first()) is not None:
        if not cronograma.activo:
            return False
        fhInicioCarrera = datetime.combine(cronograma.fechainicio, cronograma.horainicio)
        fhFinCarrera = datetime.combine(cronograma.fechafin, cronograma.horafin)
        if not (fhInicioCarrera <= datetime.now() <= fhFinCarrera):
            return False
    elif (cronograma := cronogramacarrera.filter(carrera=carrera, nivel__id=nivelmalla.nivel_id, sesion__isnull=True).first()) is not None:
        if not cronograma.activo:
            return False
        fhInicioCarrera = datetime.combine(cronograma.fechainicio, cronograma.horainicio)
        fhFinCarrera = datetime.combine(cronograma.fechafin, cronograma.horafin)
        if not (fhInicioCarrera <= datetime.now() <= fhFinCarrera):
            return False

    # cronogramacarrera = cronogramacarrera.filter(carrera=carrera)[0]
    # if not cronogramacarrera.activo:
    #     return False
    # fhInicioCarrera = datetime.combine(cronogramacarrera.fechainicio, cronogramacarrera.horainicio)
    # fhFinCarrera = datetime.combine(cronogramacarrera.fechafin, cronogramacarrera.horafin)
    #
    # if cronogramacarrera.tiene_niveles():
    #     if not nivelmalla.nivel_id in list(cronogramacarrera.niveles().values_list('id', flat=True)):
    #         return False
    # else:
    #     if not (fhInicioCarrera <= datetime.now() <= fhFinCarrera):
    #         return False

    return True


def ubicar_nivel_matricula(materias):
    try:
        mismaterias_aux = ""
        cantidad = len(materias)
        i = 1
        for x in materias:
            if i != cantidad:
                mismaterias_aux = mismaterias_aux + str(int(x)) + ","
            else:
                mismaterias_aux = mismaterias_aux + str(int(x))
            i += 1
        nivel = 0
        if mismaterias_aux != "":
            cursor = connection.cursor()
            sql = f"select nm.id from sga_materia mate, sga_asignaturamalla am, sga_nivelmalla nm where mate.id in ({mismaterias_aux}) and mate.status = true and mate.asignaturamalla_id=am.id and am.status=true and nm.id=am.nivelmalla_id and nm.status=true GROUP by nm.id order by count(nm.id) desc, nm.id desc limit 1"
            cursor.execute(sql)
            results = cursor.fetchall()
            nivel = 0
            for per in results:
                nivel = per[0]
        return nivel
    except Exception as ex:
        return ex

def contar_nivel_matricula(materias):
    try:
        bandera = False
        mismaterias_aux = ""
        cantidad = len(materias)
        i = 1
        for x in materias:
            if i != cantidad:
                mismaterias_aux = mismaterias_aux + str(int(x)) + ","
            else:
                mismaterias_aux = mismaterias_aux + str(int(x))
            i += 1
        nivel = 0
        if mismaterias_aux != "":
            cursor = connection.cursor()
            sql = f"SELECT nm.id FROM sga_materia mate, sga_asignaturamalla am, sga_nivelmalla nm WHERE mate.id in ({mismaterias_aux}) AND mate.status = TRUE AND mate.asignaturamalla_id=am.id AND am.status= TRUE AND nm.id=am.nivelmalla_id AND nm.status= TRUE GROUP BY nm.id ORDER BY COUNT(nm.id) DESC, nm.id DESC"
            cursor.execute(sql)
            results = cursor.fetchall()
            cant = len(results)
            if cant > 1:
                bandera = True
        return bandera
    except Exception as ex:
        return ex

def get_horarios_clases_informacion(materia):
    key = f"matricula_horarios_clases_informacion_materia_id_{encrypt(materia.id)}"
    eCache = CacheRedisProxy()
    if eCache.has_key_cache(key=key):
        data = eCache.get_cache(key=key)
    else:
        data = ["%s - %s a %s - (%s al %s) - %s" % (x.dia_semana(), x.turno.comienza.strftime('%H:%M %p'), x.turno.termina.strftime('%H:%M %p'), x.inicio.strftime('%d-%m-%Y'), x.fin.strftime('%d-%m-%Y'), x.aula.nombre) for x in materia.clase_set.filter(activo=True, status=True).exclude(tipoprofesor=TIPO_PROFESOR_PRACTICA).order_by('dia', 'turno__comienza')]
        eCache.set_cache(key=key, value=data)
    return data


def get_horarios_clases_data(materia):
    key = f"matricula_horarios_clases_data_materia_id_{encrypt(materia.id)}"
    eCache = CacheRedisProxy()
    if eCache.has_key_cache(key=key):
        data = eCache.get_cache(key=key)
    else:
        data = []
        for x in materia.clase_set.filter(activo=True, status=True).exclude(tipoprofesor=TIPO_PROFESOR_PRACTICA).order_by('dia', 'turno__comienza'):
            data.append({"id": x.id,
                         "dia_verbose": x.dia_semana(),
                         "dia": x.dia,
                         "inicio": x.inicio.strftime('%d-%m-%Y'),
                         "comienza": x.turno.comienza.strftime('%H:%M:%S'),
                         "fin": x.fin.strftime('%d-%m-%Y'),
                         "termina": x.turno.termina.strftime('%H:%M:%S'),
                         "aula": x.aula.nombre,
                         "tipohorario": x.tipohorario,
                         })
        eCache.set_cache(key=key, value=data)
    return data


def get_horarios_practicas_informacion(grupoprofesor):
    key = f"matricula_horarios_practicas_informacion_grupoprofesormateria_id_{encrypt(grupoprofesor.id)}"
    eCache = CacheRedisProxy()
    if eCache.has_key_cache(key=key):
        data = eCache.get_cache(key=key)
    else:
        data = ["%s - %s a %s - (%s al %s) - %s" % (x.dia_semana(), x.turno.comienza.strftime('%H:%M %p'), x.turno.termina.strftime('%H:%M %p'), x.inicio.strftime('%d-%m-%Y'), x.fin.strftime('%d-%m-%Y'), x.aula.nombre) for x in grupoprofesor.clase_set.filter(activo=True, status=True, tipoprofesor=TIPO_PROFESOR_PRACTICA).order_by('dia', 'turno__comienza')]
        eCache.set_cache(key=key, value=data)
    return data


def get_horarios_practicas_data(grupoprofesor):
    key = f"matricula_horarios_practicas_data_grupoprofesormateria_id_{encrypt(grupoprofesor.id)}"
    eCache = CacheRedisProxy()
    if eCache.has_key_cache(key=key):
        data = eCache.get_cache(key=key)
    else:
        data = []
        for x in grupoprofesor.clase_set.filter(activo=True, status=True, tipoprofesor=TIPO_PROFESOR_PRACTICA).order_by('dia', 'turno__comienza'):
            data.append({"id": x.id,
                         "dia_verbose": x.dia_semana(),
                         "dia": x.dia,
                         "inicio": x.inicio.strftime('%d-%m-%Y'),
                         "comienza": x.turno.comienza.strftime('%H:%M:%S'),
                         "fin": x.fin.strftime('%d-%m-%Y'),
                         "termina": x.turno.termina.strftime('%H:%M:%S'),
                         "aula": x.aula.nombre,
                         "tipohorario": x.tipohorario,
                         })
        eCache.set_cache(key=key, value=data)
    return data


def get_practicas_data(materia):
    periodomatricula = materia.nivel.periodo.periodomatricula_set.filter().first()
    materiaespractica = materia.asignaturamalla.practicas
    horario_practicas = []
    if materiaespractica:
        tipoprofesorpracticas = TipoProfesor.objects.filter(pk__in=[TIPO_PROFESOR_PRACTICA, TIPO_PROFESOR_PRACTICA_SALUD])
        profesoresmateria = materia.profesores_materia_segun_tipoprofesor_pm(tipoprofesorpracticas, multiple=True)
        for profesormateria in profesoresmateria:
            grupoprofesor = profesormateria.grupoprofesormateria()
            if grupoprofesor:
                for grupo in grupoprofesor:
                    eProfesor = '-- SIN DEFINIR --'
                    if periodomatricula.ver_profesor_materia:
                        if grupo.profesormateria:
                            eProfesor = grupo.profesormateria.profesor.persona.nombre_completo_inverso().__str__()
                    horario_practicas.append({"id": grupo.id,
                                              "horarios_verbose": get_horarios_practicas_informacion(grupo) if periodomatricula and periodomatricula.ver_horario_materia else '',
                                              "horarios": get_horarios_practicas_data(grupo) if periodomatricula and periodomatricula.valida_conflicto_horario else [],
                                              "cupos": grupo.cupo if periodomatricula and periodomatricula.valida_cupo_materia else 0,
                                              "disponibles": grupo.cuposdisponiblesgrupoprofesor() if periodomatricula and periodomatricula.valida_cupo_materia else 0,
                                              "paralelo": grupo.get_paralelopractica_display(),
                                              "profesor": eProfesor,
                                              })
    return horario_practicas


def get_deuda_persona(persona, periodomatricula=None):
    from sagest.models import Pago, Rubro
    tiene_valores_pendientes = False
    msg = ""
    rubros = Rubro.objects.filter(persona=persona, cancelado=False, status=True).distinct()
    if periodomatricula:
        if periodomatricula.tiene_tiposrubros():
            rubros = rubros.filter(tipo__in=periodomatricula.tiposrubros())
    if rubros.exists():
        tiene_valores_pendientes = True
        rubros_vencidos = rubros.filter(fechavence__lt=datetime.now().date()).distinct()
        if rubros_vencidos.exists():
            valor_rubros = null_to_numeric(rubros_vencidos.aggregate(valor=Sum('valortotal'))['valor'])
            valor_pagos = null_to_numeric(Pago.objects.filter(rubro__in=rubros_vencidos, status=True).distinct().aggregate(valor=Sum('valortotal'))['valor'])
            valores_vencidos = valor_rubros - valor_pagos
            msg = f"""<div class="alert alert-danger" style="margin-top: 10px;">
                                        <!--<h4 class="alert-heading">ALERTA</h4>-->
                                        Estimad{'a' if persona.es_mujer() else 'o'} {persona.__str__()}, aún posee <b>VALORES PENDIENTES POR PAGAR</b>. Total de deuda: <b>${valores_vencidos}</b>{"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href='javascript:;' class='btn btn-info btn-sm action-view-pending-values'>Detalle</a>" if periodomatricula.ver_deduda else ""}
                                    </div>"""
        else:
            valor_rubros = null_to_numeric(rubros.aggregate(valor=Sum('valortotal'))['valor'])
            valor_pagos = null_to_numeric(Pago.objects.filter(rubro__in=rubros, status=True).distinct().aggregate(valor=Sum('valortotal'))['valor'])
            valores_pendientes = valor_rubros - valor_pagos
            msg = f"""<div class="alert alert-warning" style="margin-top: 10px;">
                                        <!--<h4 class="alert-heading">ALERTA</h4>-->
                                        Estimad{'a' if persona.es_mujer() else 'o'} {persona.__str__()}, posee <b>VALORES PENDIENTES POR PAGAR</b>.  Total de deuda: <b>${valores_pendientes}</b>{"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href='javascript:;' class='btn btn-info btn-sm action-view-pending-values'>Detalle</a>" if periodomatricula.ver_deduda else ""}
                                    </div>"""
    return tiene_valores_pendientes, msg


def get_deuda_persona_posgrado(persona, periodomatricula=None):
    from sagest.models import Pago, Rubro
    tiene_valores_pendientes = False
    msg = ""
    rubros = Rubro.objects.filter(persona=persona, cancelado=False, status=True).distinct()
    if periodomatricula:
        if periodomatricula.tiene_tiposrubros():
            rubros = rubros.filter(tipo__in=periodomatricula.tiposrubros())
    if rubros.exists():
        tiene_valores_pendientes = True
        rubros_vencidos = rubros.filter(fechavence__lt=datetime.now().date()).distinct()
        if rubros_vencidos.exists():
            valor_rubros = null_to_numeric(rubros_vencidos.aggregate(valor=Sum('valortotal'))['valor'])
            valor_pagos = null_to_numeric(Pago.objects.filter(rubro__in=rubros_vencidos, status=True).distinct().aggregate(valor=Sum('valortotal'))['valor'])
            valores_vencidos = valor_rubros - valor_pagos
            msg = f"""<div class="alert alert-danger" style="margin-top: 10px;">
                                        <!--<h4 class="alert-heading">ALERTA</h4>-->
                                        Estimad{'a' if persona.es_mujer() else 'o'} {persona.__str__()}, aún posee <b>VALORES PENDIENTES POR PAGAR</b>. Total de deuda: <b>${valores_vencidos}</b> {"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href='javascript:;' class='btn btn-info btn-sm action-view-pending-values'>Detalle</a>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href='javascript:;' class='btn btn-warning btn-sm action-pay-pending-values'>Pagar con tarjeta</a>" if periodomatricula.ver_deduda else ""}
                                    </div>"""
            # Estimad{'a' if persona.es_mujer() else 'o'} {persona.__str__()}, aún posee <b>VALORES PENDIENTES POR PAGAR</b>. Total de deuda: <b>${valores_vencidos}</b> {"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href='javascript:;' class='btn btn-info btn-sm action-view-pending-values'>Detalle</a>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;" if periodomatricula.ver_deduda else ""}
            # Estimad{'a' if persona.es_mujer() else 'o'} {persona.__str__()}, aún posee <b>VALORES PENDIENTES POR PAGAR</b>. Total de deuda: <b>${valores_vencidos}</b> {"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href='javascript:;' class='btn btn-info btn-sm action-view-pending-values'>Detalle</a>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href='javascript:;' class='btn btn-warning btn-sm action-pay-pending-values'>Pagar con tarjeta</a>" if periodomatricula.ver_deduda else ""}
        else:
            valor_rubros = null_to_numeric(rubros.aggregate(valor=Sum('valortotal'))['valor'])
            valor_pagos = null_to_numeric(Pago.objects.filter(rubro__in=rubros, status=True).distinct().aggregate(valor=Sum('valortotal'))['valor'])
            valores_pendientes = valor_rubros - valor_pagos
            msg = f"""<div class="alert alert-info" style="margin-top: 10px;">
                                        <!--<h4 class="alert-heading">ALERTA</h4>-->
                                        Estimad{'a' if persona.es_mujer() else 'o'} {persona.__str__()}, posee <b>rubros generados</b> por valor de maestría. Total: <b>${valores_pendientes}</b> {"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href='javascript:;' class='btn btn-info btn-sm action-view-pending-values'>Detalle rubros</a>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href='javascript:;' class='btn btn-warning btn-sm action-pay-pending-values'>Pagar con tarjeta</a>" if periodomatricula.ver_deduda else ""}
                                    </div>"""
            # Estimad{'a' if persona.es_mujer() else 'o'} {persona.__str__()}, posee <b>rubros generados</b> por valor de maestría. Total: <b>${valores_pendientes}</b>{"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href='javascript:;' class='btn btn-info btn-sm action-view-pending-values'>Detalle rubros</a>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;" if periodomatricula.ver_deduda else ""}
            # Estimad{'a' if persona.es_mujer() else 'o'} {persona.__str__()}, posee <b>rubros generados</b> por valor de maestría. Total: <b>${valores_pendientes}</b>{"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href='javascript:;' class='btn btn-info btn-sm action-view-pending-values'>Detalle rubros</a>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href='javascript:;' class='btn btn-warning btn-sm action-pay-pending-values'>Pagar con tarjeta</a>" if periodomatricula.ver_deduda else ""}
    return tiene_valores_pendientes, msg


def get_bloqueo_matricula_posgrado(persona, inscohorte, periodomatricula=None):
    from sagest.models import Pago, Rubro
    rubros = Rubro.objects.filter(persona=persona, cancelado=False, status=True).distinct()
    if periodomatricula:
        if periodomatricula.tiene_tiposrubros():
            rubros = rubros.filter(tipo__in=periodomatricula.tiposrubros())
    if rubros.exists():
        rubros_vencidos = rubros.filter(fechavence__lt=datetime.now().date()).distinct()
        if inscohorte.formapagopac:
            if inscohorte.formapagopac.id == 1:
                if rubros_vencidos.count() >= 1:
                    return True
                else:
                    return False
            else:
                if rubros_vencidos.count() >= 2:
                    return True
                else:
                    return False
        else:
            if rubros_vencidos.count() >= 2:
                return True
            else:
                return False
    else:
        return False


def tiene_deudas_vencidas_persona(persona, periodomatricula=None):
    from sagest.models import Pago, Rubro
    tiene_valores_vencidos = False
    filtros = Q(persona=persona) & Q(cancelado=False) & Q(status=True) & Q(fechavence__lt=datetime.now().date())
    # rubros = Rubro.objects.filter(persona=persona, cancelado=False, status=True).distinct()
    if periodomatricula:
        if periodomatricula.tiene_tiposrubros():
            # rubros = rubros.filter(tipo__in=periodomatricula.tiposrubros())
            filtros = filtros & Q(tipo__in=periodomatricula.tiposrubros())
    tiene_valores_vencidos = Rubro.objects.values("id").filter(filtros).exists()
    # if eRubros.values("id").exists():
    #     rubros_vencidos = rubros.filter(fechavence__lt=datetime.now().date()).distinct()
    #     return rubros_vencidos.exists()

    return tiene_valores_vencidos


def valida_conflicto_materias_estudiante(mis_clases, mi_clase):
    clases = []
    for clase in mis_clases:
        for c in clase:
            # if int(c['tipohorario']) == 1:
            clases.append({'inicio_comienza': convertir_fecha_hora(f"{c['inicio']} {c['comienza']}"),
                           'inicio': convertir_fecha(f"{c['inicio']}"),
                           'comienza': convertir_hora(f"{c['comienza']}"),
                           'fin_termina': convertir_fecha_hora(f"{c['fin']} {c['termina']}"),
                           'fin': convertir_fecha(f"{c['fin']}"),
                           'termina': convertir_hora(f"{c['termina']}"),
                           'id': int(c['id']),
                           'tipohorario': int(c['tipohorario']),
                           'dia': int(c['dia']),
                           })
    clase_aux = []
    for clase in mi_clase:
        for c in clase:
            # if int(c['tipohorario']) == 1:
            clase_aux.append({'inicio_comienza': convertir_fecha_hora(f"{c['inicio']} {c['comienza']}"),
                              'inicio': convertir_fecha(f"{c['inicio']}"),
                              'comienza': convertir_hora(f"{c['comienza']}"),
                              'fin_termina': convertir_fecha_hora(f"{c['fin']} {c['termina']}"),
                              'fin': convertir_fecha(f"{c['fin']}"),
                              'termina': convertir_hora(f"{c['termina']}"),
                              'id': int(c['id']),
                              'tipohorario': int(c['tipohorario']),
                              'dia': int(c['dia']),
                              })

    msg = 'No se registra conflicto de horario'
    if clases and clase_aux:
        for c_selec in clases:
            for c_escog in clase_aux:
                if ((c_selec['inicio'] >= c_escog['inicio'] and c_selec['fin'] <= c_escog['fin']) or
                    (c_selec['inicio'] <= c_escog['inicio'] and c_selec['fin'] >= c_escog['fin']) or
                    (c_selec['inicio'] <= c_escog['fin'] and c_selec['inicio'] >= c_escog['inicio']) or
                    (c_selec['fin'] >= c_escog['inicio'] and c_selec['fin'] <= c_escog['fin'])):
                    if int(c_selec['dia']) == int(c_escog['dia']):
                        if (
                                (c_selec['comienza'] <= c_escog['termina'] and c_selec['termina'] >= c_escog['termina'])
                                or
                                (c_selec['comienza'] <= c_escog['comienza'] and c_selec['termina'] >= c_escog['termina'])
                        ):
                            clase = Clase.objects.get(pk=int(c_selec['id']))
                            conflicto = Clase.objects.get(pk=int(c_escog['id']))
                            msg = "FCME: conflicto de horario " + to_unicode(clase.materia.asignatura.nombre) + "(" + to_unicode(clase.materia.identificacion) + ") y " + to_unicode(conflicto.materia.asignatura.nombre) + "(" + to_unicode(conflicto.materia.identificacion) + ") DIA: " + conflicto.dia_semana()
                            return True, msg
    return False, msg


def valida_conflicto_materias_estudiante_enroll(mis_clases):
    clases = []
    for c in mis_clases:
        if c['horarios'] and c['validarequisitograduacion']:
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
        if c['practica'] and len(c['practica']) > 0 and c['validarequisitograduacion']:
            for h in c['practica']['horarios']:
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


def calcula_nivel(matricula):
    cursor = connection.cursor()

    sql = """select am.nivelmalla_id, count(am.nivelmalla_id) as cantidad_materias_seleccionadas 
             from sga_materiaasignada ma, sga_materia m, sga_asignaturamalla am 
             where ma.status=true and ma.matricula_id=%s and m.status=true and m.id=ma.materia_id and am.status=true
             and am.id=m.asignaturamalla_id GROUP by am.nivelmalla_id, am.malla_id order by count(am.nivelmalla_id) desc, am.nivelmalla_id desc limit 1""" % matricula.id

    cursor.execute(sql)
    results = cursor.fetchall()
    nivel = 1
    for per in results:
        nivel = per[0]
    matricula.nivelmalla_id = nivel
    matricula.save()


def calculos_finanzas_adicional_aux_pregrado(request, matricula, cobro):
    from sagest.models import TipoOtroRubro, Rubro
    persona = matricula.inscripcion.persona
    periodo = matricula.nivel.periodo
    if not matricula.inscripcion.persona.fichasocioeconomicainec_set.all().exists():
        raise NameError(u"No puede matricularse, debe llenar la ficha socioeconomica")

    matriculagruposocioeconomico = matricula.matriculagruposocioeconomico_set.filter(status=True)
    if matriculagruposocioeconomico.values("id").exists():
        gruposocioeconomico = matriculagruposocioeconomico[0].gruposocioeconomico
    else:
        gruposocioeconomico = matricula.inscripcion.persona.grupoeconomico()

    valorgrupoeconomico = 0
    if periodo.tipocalculo == 1:
        periodogruposocioeconomico = gruposocioeconomico.periodogruposocioeconomico_set.filter(periodo=periodo, status=True)
        if not periodogruposocioeconomico.values("id").exists():
            raise NameError(u"Grupo socioeconomico no tiene configurado valores de créditos")
        valorgrupoeconomico = periodogruposocioeconomico[0].valor
    else:
        malla = matricula.inscripcion.mi_malla()
        if malla is None:
            raise NameError(u"Malla sin configurar")
        periodomalla = PeriodoMalla.objects.filter(periodo=periodo, malla=malla, status=True)
        if not periodomalla.values("id").exists():
            raise NameError(u"Malla no tiene configurado valores de cobro")
        periodomalla = periodomalla[0]
        detalleperiodomalla = DetallePeriodoMalla.objects.filter(periodomalla=periodomalla, gruposocioeconomico=gruposocioeconomico, status=True)
        if not detalleperiodomalla.values("id").exists():
            raise NameError(u"Malla en grupo socioeconomico no tiene configurado valores de cobro")
        valorgrupoeconomico = detalleperiodomalla[0].valor

    porcentaje_gratuidad = periodo.porcentaje_gratuidad
    valor_maximo = periodo.valor_maximo
    rubro_anterior_matricula = None
    if Rubro.objects.values('id').filter(matricula=matricula, relacionados__isnull=True, status=True).exists():
        rubro_anterior_matricula = Rubro.objects.filter(matricula=matricula, relacionados__isnull=True, status=True)[0]

    costo_materia_total = 0
    tiporubroarancel = TipoOtroRubro.objects.filter(pk=RUBRO_ARANCEL)[0]
    tiporubromatricula = TipoOtroRubro.objects.filter(pk=RUBRO_MATRICULA)[0]

    if cobro > 0:
        for materiaasignada in matricula.materiaasignada_set.filter(status=True, retiramateria=False):
            costo_materia = 0
            if cobro == 1:
                costo_materia = Decimal(Decimal(materiaasignada.materia.creditos).quantize(Decimal('.01')) * valorgrupoeconomico).quantize(Decimal('.01'))
            else:
                if cobro == 2:
                    if materiaasignada.matriculas > 1:
                        costo_materia = Decimal(Decimal(materiaasignada.materia.creditos).quantize(Decimal('.01')) * valorgrupoeconomico).quantize(Decimal('.01'))
                else:
                    costo_materia = Decimal(Decimal(materiaasignada.materia.creditos).quantize(Decimal('.01')) * valorgrupoeconomico).quantize(Decimal('.01'))
            costo_materia_total += costo_materia

    valor_pagado_arancel = 0
    if Rubro.objects.values('id').filter(matricula=matricula, status=True, tipo=tiporubroarancel, cancelado=True).exists():
        valor_pagado_arancel = Rubro.objects.filter(matricula=matricula, status=True, tipo=tiporubroarancel, cancelado=True).aggregate(suma=Sum('valor'))['suma']
        costo_materia_total = costo_materia_total - valor_pagado_arancel

    if costo_materia_total > 0:
        matricula.estado_matricula = 1
        matricula.save(request)
        # valor_porcentaje = Decimal((costo_materia_total * porcentaje_gratuidad) / 100).quantize(Decimal('.01'))
        rubro = Rubro(tipo=tiporubroarancel,
                      persona=persona,
                      relacionados=rubro_anterior_matricula,
                      matricula=matricula,
                      # contratorecaudacion = None,
                      nombre=tiporubroarancel.nombre + ' - ' + periodo.nombre,
                      cuota=1,
                      fecha=datetime.now().date(),
                      fechavence=datetime.now().date() + timedelta(days=1),
                      valor=costo_materia_total,
                      iva_id=1,
                      valoriva=0,
                      valortotal=costo_materia_total,
                      saldo=costo_materia_total,
                      cancelado=False)
        rubro.save(request)
        # valor_porcentaje = Decimal(((Rubro.objects.filter(matricula=matricula, status=True, tipo=tiporubroarancel).aggregate(suma=Sum('valor'))['suma']) * porcentaje_gratuidad) / 100).quantize(Decimal('.01'))
        # valor = valor_porcentaje
        valor = valor_maximo
        valor_pagado_matricula = 0
        if Rubro.objects.values('id').filter(matricula=matricula, status=True, tipo=tiporubromatricula).exists():
            # valormulta = Decimal((valor_maximo * PORCENTAJE_MULTA) / 100).quantize(Decimal('.01'))
            valormulta = Decimal(valor_maximo).quantize(Decimal('.01'))
            valor_pagado_matricula = 0
            if Rubro.objects.values('id').filter(matricula=matricula, status=True, tipo=tiporubromatricula).exclude(valor=valormulta).exists():
                valor_pagado_matricula = Rubro.objects.filter(matricula=matricula, status=True, tipo=tiporubromatricula).exclude(valor=valormulta)[0].valor

        if valor_pagado_matricula < valor:
            valor = valor - valor_pagado_matricula
            if (valor + valor_pagado_matricula) > valor_maximo:
                valor = valor_maximo - valor_pagado_matricula
        else:
            valor = 0

        if valor > 0:
            rubro1 = Rubro(tipo=tiporubromatricula,
                           persona=persona,
                           relacionados=rubro_anterior_matricula,
                           matricula=matricula,
                           # contratorecaudacion = None,
                           nombre=tiporubromatricula.nombre + ' - ' + periodo.nombre,
                           cuota=1,
                           fecha=datetime.now().date(),
                           fechavence=datetime.now().date() + timedelta(days=1),
                           valor=valor,
                           iva_id=1,
                           valoriva=0,
                           valortotal=valor,
                           saldo=valor,
                           cancelado=False)
            rubro1.save(request)

        # valor multa por no se ordinaria
        if matricula.tipomatricula_id != 1:
            # valor = Decimal((valor_maximo * PORCENTAJE_MULTA) / 100).quantize(Decimal('.01'))
            valor = valor_maximo
            if not Rubro.objects.values('id').filter(matricula=matricula, status=True, tipo=tiporubromatricula, valor=valor).exists():
                rubro1 = Rubro(tipo=tiporubromatricula,
                               persona=persona,
                               relacionados=None,
                               matricula=matricula,
                               # contratorecaudacion = None,
                               nombre=tiporubromatricula.nombre + ' - ' + periodo.nombre,
                               cuota=1,
                               fecha=datetime.now().date(),
                               fechavence=datetime.now().date() + timedelta(days=1),
                               valor=valor,
                               iva_id=1,
                               valoriva=0,
                               valortotal=valor,
                               saldo=valor,
                               cancelado=False)
                rubro1.save(request)
    else:
        if matricula.tipomatricula_id == 1:
            matricula.estado_matricula = 2
            matricula.save(request)
            # else:
            #     valor = Decimal((valor_maximo * PORCENTAJE_MULTA) / 100).quantize(Decimal('.01'))
            #     rubro1 = Rubro(tipo=tiporubromatricula,
            #                    persona=persona,
            #                    relacionados=None,
            #                    matricula=self,
            #                    # contratorecaudacion = None,
            #                    nombre=tiporubromatricula.nombre + ' - ' + periodo.nombre,
            #                    cuota=1,
            #                    fecha=datetime.now().date(),
            #                    fechavence=datetime.now().date() + timedelta(days=1),
            #                    valor=valor,
            #                    iva_id=1,
            #                    valoriva=0,
            #                    valortotal=valor,
            #                    saldo=valor,
            #                    cancelado=False)
            #     rubro1.save(request)
            #     # costo de matricula carlos loyola 03-03-2017


def calculos_finanzas_pregrado(request, matricula, cobro):
    from sagest.models import TipoOtroRubro, Rubro
    persona = matricula.inscripcion.persona
    periodo = matricula.nivel.periodo
    if not matricula.inscripcion.persona.fichasocioeconomicainec_set.all().exists():
        raise NameError(u"No puede matricularse, debe llenar la ficha socioeconomica")

    matriculagruposocioeconomico = matricula.matriculagruposocioeconomico_set.filter(status=True)

    if matriculagruposocioeconomico.values("id").exists():
        gruposocioeconomico = matriculagruposocioeconomico[0].gruposocioeconomico
    else:
        gruposocioeconomico = matricula.inscripcion.persona.grupoeconomico()

    valorgrupoeconomico = 0
    if periodo.tipocalculo == 1:
        periodogruposocioeconomico = gruposocioeconomico.periodogruposocioeconomico_set.filter(periodo=periodo, status=True)
        if not periodogruposocioeconomico.values("id").exists():
            raise NameError(u"Grupo socioeconomico no tiene configurado valores de créditos")
        valorgrupoeconomico = periodogruposocioeconomico[0].valor
    else:
        malla = matricula.inscripcion.mi_malla()
        if malla is None:
            raise NameError(u"Malla sin configurar")
        periodomalla = PeriodoMalla.objects.filter(periodo=periodo, malla=malla, status=True)
        if not periodomalla.values("id").exists():
            raise NameError(u"Malla no tiene configurado valores de cobro")
        periodomalla = periodomalla[0]
        detalleperiodomalla = DetallePeriodoMalla.objects.filter(periodomalla=periodomalla, gruposocioeconomico=gruposocioeconomico, status=True)
        if not detalleperiodomalla.values("id").exists():
            raise NameError(u"Malla en grupo socioeconomico no tiene configurado valores de cobro")
        valorgrupoeconomico = detalleperiodomalla[0].valor

    valorgrupoeconomico = matricula.inscripcion.persona.fichasocioeconomicainec_set.all()[0].grupoeconomico.periodogruposocioeconomico_set.filter(periodo=periodo, status=True)[0].valor
    porcentaje_gratuidad = periodo.porcentaje_gratuidad
    valor_maximo = periodo.valor_maximo
    costo_materia_total = 0
    tiporubroarancel = TipoOtroRubro.objects.filter(pk=RUBRO_ARANCEL)[0]
    tiporubromatricula = TipoOtroRubro.objects.filter(pk=RUBRO_MATRICULA)[0]
    if cobro > 0:
        for materiaasignada in matricula.materiaasignada_set.filter(status=True, retiramateria=False):
            costo_materia = 0
            if cobro == 1:
                costo_materia = Decimal(Decimal(materiaasignada.materia.creditos).quantize(Decimal('.01')) * valorgrupoeconomico).quantize(Decimal('.01'))
            else:
                if cobro == 2:
                    if materiaasignada.matriculas > 1:
                        costo_materia = Decimal(Decimal(materiaasignada.materia.creditos).quantize(Decimal('.01')) * valorgrupoeconomico).quantize(Decimal('.01'))
                else:
                    costo_materia = Decimal(Decimal(materiaasignada.materia.creditos).quantize(Decimal('.01')) * valorgrupoeconomico).quantize(Decimal('.01'))
            costo_materia_total += costo_materia

    if costo_materia_total > 0:
        # self.estado_matricula = 2
        # self.save(request)
        # valor_porcentaje = Decimal((costo_materia_total * porcentaje_gratuidad) / 100).quantize(Decimal('.01'))
        rubro = Rubro(tipo=tiporubroarancel,
                      persona=persona,
                      relacionados=None,
                      matricula=matricula,
                      # contratorecaudacion = None,
                      nombre=tiporubroarancel.nombre + ' - ' + periodo.nombre,
                      cuota=1,
                      fecha=datetime.now().date(),
                      fechavence=datetime.now().date() + timedelta(days=1),
                      valor=costo_materia_total,
                      iva_id=1,
                      valoriva=0,
                      valortotal=costo_materia_total,
                      saldo=costo_materia_total,
                      cancelado=False)
        rubro.save(request)

        valor = valor_maximo
        # if valor_porcentaje > valor_maximo:
        #     valor = valor_maximo
        rubro1 = Rubro(tipo=tiporubromatricula,
                       persona=persona,
                       relacionados=rubro,
                       matricula=matricula,
                       # contratorecaudacion = None,
                       nombre=tiporubromatricula.nombre + ' - ' + periodo.nombre,
                       cuota=1,
                       fecha=datetime.now().date(),
                       fechavence=datetime.now().date() + timedelta(days=1),
                       valor=valor,
                       iva_id=1,
                       valoriva=0,
                       valortotal=valor,
                       saldo=valor,
                       cancelado=False)
        rubro1.save(request)

        # valor multa por no se ordinaria
        if matricula.tipomatricula_id != 1:
            # valor = Decimal((valor_maximo * PORCENTAJE_MULTA) / 100).quantize(Decimal('.01'))
            valor = valor_maximo
            rubro1 = Rubro(tipo=tiporubromatricula,
                           persona=persona,
                           relacionados=None,
                           matricula=matricula,
                           # contratorecaudacion = None,
                           nombre=tiporubromatricula.nombre + ' - ' + periodo.nombre,
                           cuota=1,
                           fecha=datetime.now().date(),
                           fechavence=datetime.now().date() + timedelta(days=1),
                           valor=valor,
                           iva_id=1,
                           valoriva=0,
                           valortotal=valor,
                           saldo=valor,
                           cancelado=False)
            rubro1.save(request)

    else:
        if matricula.tipomatricula_id == 1:
            matricula.estado_matricula = 2
            matricula.save(request)
        else:
            # valor = Decimal((valor_maximo * PORCENTAJE_MULTA) / 100).quantize(Decimal('.01'))
            valor = valor_maximo
            rubro1 = Rubro(tipo=tiporubromatricula,
                           persona=persona,
                           relacionados=None,
                           matricula=matricula,
                           # contratorecaudacion = None,
                           nombre=tiporubromatricula.nombre + ' - ' + periodo.nombre,
                           cuota=1,
                           fecha=datetime.now().date(),
                           fechavence=datetime.now().date() + timedelta(days=1),
                           valor=valor,
                           iva_id=1,
                           valoriva=0,
                           valortotal=valor,
                           saldo=valor,
                           cancelado=False)
            rubro1.save(request)
            # costo de matricula carlos loyola 03-03-2017


# PERMITE DEFINIR QUE TIPO DE MATRICULA SI ES REGULAR O IRREGULAR
def get_tipo_matricula(request, matricula):
    try:
        periodomatricula = None
        if PeriodoMatricula.objects.values('id').filter(status=True, periodo=matricula.nivel.periodo, activo=True).exists():
            periodomatricula = PeriodoMatricula.objects.filter(status=True, periodo=matricula.nivel.periodo, activo=True)[0]
        if not periodomatricula:
            raise NameError(u"No se ha identificado el periodo de matricula")
        cantidad_seleccionadas = 0
        cursor = connection.cursor()
        # cursor = connections['default'].cursor()
        itinerario = 0
        if not matricula.inscripcion.itinerario is None and matricula.inscripcion.itinerario > 0:
            itinerario = matricula.inscripcion.itinerario
        sql = f"select am.nivelmalla_id, count(am.nivelmalla_id) as cantidad_materias_seleccionadas from sga_materiaasignada ma, sga_materia m, sga_asignaturamalla am where ma.status=true and ma.matricula_id={str(matricula.id)} and m.status=true and m.id=ma.materia_id and am.status=true and am.id=m.asignaturamalla_id GROUP by am.nivelmalla_id, am.malla_id order by count(am.nivelmalla_id) desc, am.nivelmalla_id desc limit 1;"
        if itinerario > 0:
            sql = f"select am.nivelmalla_id, count(am.nivelmalla_id) as cantidad_materias_seleccionadas from sga_materiaasignada ma, sga_materia m, sga_asignaturamalla am where ma.status=true and ma.matricula_id={str(matricula.id)} and m.status=true and m.id=ma.materia_id and am.status=true and am.id=m.asignaturamalla_id and (am.itinerario=0 or am.itinerario=" + str(itinerario) + ") GROUP by am.nivelmalla_id, am.malla_id order by count(am.nivelmalla_id) desc, am.nivelmalla_id desc limit 1;"

        # sql = "select am.nivelmalla_id, count(am.nivelmalla_id) as cantidad_materias_seleccionadas from sga_materiaasignada ma, sga_materia m, sga_asignaturamalla am where ma.status=true and ma.matricula_id=" + str(matricula.id) + " and m.status=true and m.id=ma.materia_id and am.status=true and am.id=m.asignaturamalla_id GROUP by am.nivelmalla_id, am.malla_id order by count(am.nivelmalla_id) desc, am.nivelmalla_id desc limit 1;"
        cursor.execute(sql)
        results = cursor.fetchall()
        nivel = 0
        for per in results:
            nivel = per[0]
            cantidad_seleccionadas = per[1]
        cantidad_nivel = 0

        for asignaturamalla in AsignaturaMalla.objects.filter(nivelmalla__id=nivel, status=True, malla=matricula.inscripcion.mi_malla()):
            if Materia.objects.values("id").filter(nivel__periodo=matricula.nivel.periodo, asignaturamalla=asignaturamalla).exists():
                if matricula.inscripcion.estado_asignatura(asignaturamalla.asignatura) != 1:
                    cantidad_nivel += 1
        aData = {"cantidad_nivel": cantidad_nivel,
                 "porcentaje_perdidad_parcial_gratuidad": periodomatricula.porcentaje_perdidad_parcial_gratuidad,
                 "cantidad_seleccionadas": cantidad_seleccionadas}
        return True, "ok", aData
    except Exception as ex:
        return False, ex.__str__(), {}


def agregacion_aux_pregrado(request, matricula):
    try:
        valid, msg, aData = get_tipo_matricula(request, matricula)
        if not valid:
            raise NameError(msg)
        cantidad_nivel = aData['cantidad_nivel']
        porcentaje_perdidad_parcial_gratuidad = aData['porcentaje_perdidad_parcial_gratuidad']
        cantidad_seleccionadas = aData['cantidad_seleccionadas']

        porcentaje_seleccionadas = int(round(Decimal((float(cantidad_nivel) * float(porcentaje_perdidad_parcial_gratuidad)) / 100).quantize(Decimal('.00')), 0))
        cobro = 0
        if matricula.inscripcion.estado_gratuidad == 1 or matricula.inscripcion.estado_gratuidad == 2:
            if (cantidad_seleccionadas < porcentaje_seleccionadas):
                cobro = 1
            else:
                # if self.inscripcion.estado_gratuidad == 2:
                cobro = 2
        else:
            if matricula.inscripcion.estado_gratuidad == 2:
                cobro = 2
            else:
                cobro = 3

        if matricula.inscripcion.persona.tiene_otro_titulo(inscripcion=matricula.inscripcion):
            cobro = 3

        # cobro = 3 # BORRAR SOLO ES PARA PROBAR TITULO - SOLO SE HABILITA PARA PRUEBAS OJOOOO

        if matricula.tiene_pagos_matricula():
            # cuando tiene pagos de los rubros de la matricula, se le generara un rubro aparta por el valor de la matricula, y el valor adicional de los 10$ pero que no se pase de los 10$
            matricula.elimina_rubro_matricula_adicional()
            calculos_finanzas_adicional_aux_pregrado(request, matricula, cobro)
        else:
            matricula.elimina_rubro_matricula()
            calculos_finanzas_pregrado(request, matricula, cobro)
        matricula.actualiza_matricula()
        return True, None
    except Exception as ex:
        return False, ex


def action_enroll_pregrado(request, inscripcion, periodomatricula, nivel, mis_clases, cobro):
    try:
        hoy = datetime.now().date()
        persona = inscripcion.persona
        periodo = periodomatricula.periodo
        # PERDIDA DE CARRERA POR 4TA MATRICULA
        if inscripcion.tiene_perdida_carrera(periodomatricula.num_matriculas):
            raise NameError(u"Tiene limite de matriculas.")
        # regular o irregular
        tipo_matricula_ri = int(request.POST['tipo_matricula'])
        # MATERIAS PRACTICAS
        mis_practicas = []
        mis_materias_congrupo = []
        for m in mis_clases:
            if m['practica']:
                for k, v in m['practica'].items():
                    if k == 'id':
                        mis_practicas.append(v)
                        mis_materias_congrupo.append(int(m['id']))
        mis_materias = []
        for m in mis_clases:
            mis_materias.append(int(m['id']))
        materias = Materia.objects.filter(id__in=mis_materias)
        mis_materias_singrupo = []
        for m in materias:
            if m.asignaturamalla.tipomateria_id == TIPO_PROFESOR_PRACTICA:
                if not m.id in mis_materias_congrupo:
                    mis_materias_singrupo.append(m.id)
        # MATERIAS PRACTICAS
        grupoprofesormaterias = GruposProfesorMateria.objects.filter(id__in=mis_practicas)
        # profesoresmateriassingrupo = ProfesorMateria.objects.filter(id__in=materias.values('profesormateria__id').filter(profesormateria__gruposprofesormateria__isnull=True)).exclude(materia__in=grupoprofesormaterias.values('profesormateria__materia'))
        profesoresmateriassingrupo = ProfesorMateria.objects.filter(materia_id__in=mis_materias_singrupo, tipoprofesor_id=TIPO_PROFESOR_PRACTICA)

        if periodomatricula.valida_horario_materia:
            # VALIDACION MATERIAS TIENE PRACTICAS PARA LA CARRERA DE ENFERMERIA Y NUTRICION
            if inscripcion.carrera.id in [1, 3]:
                totalpracticas = materias.values('id').filter(asignaturamalla__practicas=True, id__in=grupoprofesormaterias.values('materia__id')).count() + materias.values('id').filter(asignaturamalla__practicas=True, id__in=grupoprofesormaterias.values('profesormateria__materia__id')).count()
                if not materias.values('id').filter(asignaturamalla__practicas=True).count() == totalpracticas:
                    raise NameError(u"Falta de seleccionar horario de practicas")

        if periodomatricula.valida_conflicto_horario and inscripcion.carrera.modalidad != 3:
            conflicto, msg = valida_conflicto_materias_estudiante_enroll(mis_clases)
            if conflicto:
                raise NameError(msg)

        if periodomatricula.valida_cupo_materia:
            # VERIFICANDO CUPO MATERIAS PRACTICAS EN PROFESOR MATERIA CON PÁRALELO
            for gpm in grupoprofesormaterias:
                validar = True
                if gpm.profesormateria.materia.tipomateria == TIPO_PROFESOR_PRACTICA:
                    validar = variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL')
                if validar:
                    if not HOMITIRCAPACIDADHORARIO and gpm.cuposdisponiblesgrupoprofesor() <= 0:
                        raise NameError(u"Capacidad limite de la materia en la práctica:  " + unicode(gpm.profesormateria.materia) + ", seleccione otro.")

            # LIMITE DE MATRICULAS EN EL PARALELO
            if not MATRICULACION_LIBRE and nivel.capacidadmatricula <= nivel.matricula_set.values('id').count():
                raise NameError(u"Capacidad matricula limite del paralelo: " + unicode(nivel.paralelo) + ", seleccione otro.")
            # habilitar cuando sea matriculacion
            # if estudiante and 'matriculamodulos' not in request.POST:
            #     if nivel.fechatopematriculaex and hoy > nivel.fechatopematriculaex:
            #         return JsonResponse({"result": "bad", "reload": False, "mensaje": u"Fuera del periodo de matriculacion."})
            # habilitar cuando sea matriculacion


        # MATRICULA
        costo_materia_total = 0
        if inscripcion.matricula_set.values('id').filter(nivel__periodo=periodo).exists():
            raise NameError(u"Ya se encuentra matriculado.")

        for materia in materias:
            if periodomatricula.valida_cupo_materia:
                if not materia.tiene_cupo_materia():
                    if materia.cupoadicional > 0:
                        if not materia.existen_cupos_con_adicional():
                            raise NameError(u"Capacidad limite de la materia: " + unicode(materia.asignatura) + ", seleccione otro.")
                    else:
                        raise NameError(u"Capacidad limite de la materia: " + unicode(materia.asignatura) + ", seleccione otro.")

        with transaction.atomic():
            matricula = Matricula(inscripcion=inscripcion,
                                  nivel=nivel,
                                  pago=False,
                                  iece=False,
                                  becado=False,
                                  porcientobeca=0,
                                  fecha=datetime.now().date(),
                                  hora=datetime.now().time(),
                                  fechatope=fechatope(datetime.now().date()),
                                  termino=True,
                                  fechatermino=datetime.now())
            matricula.save(request)
            # matricula.grupo_socio_economico()
            # matriculagruposocioeconomico = matricula.matriculagruposocioeconomico_set.all()[0]
            # matriculagruposocioeconomico.tipomatricula=tipo_matricula
            # matriculagruposocioeconomico.save()
            matricula.confirmar_matricula()
            codigoitinerario = 0
            for materia in materias:
                matriculacupoadicional = False
                if not inscripcion.itinerario or inscripcion.itinerario < 1:
                    if materia.asignaturamalla.itinerario > 0:
                        codigoitinerario = int(materia.asignaturamalla.itinerario)
                if periodomatricula.valida_cupo_materia:
                    if not materia.tiene_cupo_materia():
                        if materia.cupoadicional > 0:
                            if not materia.existen_cupos_con_adicional():
                                transaction.set_rollback(True)
                                raise NameError(u"Capacidad limite de la materia: " + unicode(materia.asignatura) + ", seleccione otro.")
                            else:
                                matriculacupoadicional = True
                        else:
                            transaction.set_rollback(True)
                            raise NameError(u"Capacidad limite de la materia: " + unicode(materia.asignatura) + ", seleccione otro.")

                matriculas = matricula.inscripcion.historicorecordacademico_set.values('id').filter(asignatura=materia.asignatura, fecha__lt=materia.nivel.fin).count() + 1
                materiaasignada = MateriaAsignada(matricula=matricula,
                                                  materia=materia,
                                                  notafinal=0,
                                                  asistenciafinal=0,
                                                  cerrado=False,
                                                  matriculas=matriculas,
                                                  observaciones='',
                                                  estado_id=NOTA_ESTADO_EN_CURSO)
                materiaasignada.save(request)
                if matriculacupoadicional:
                    materia.totalmatriculadocupoadicional += 1
                    materia.cupo += 1
                    materia.save(request)
                    log(u'Estudiante matriculado en cupo adicional materia: %s - estudiante: %s y se aumento un cupo en materia' % (materia, matricula), request, "add")
                materiaasignada.asistencias()
                materiaasignada.evaluacion()
                materiaasignada.mis_planificaciones()
                materiaasignada.save(request)
                # MATRICULA EN LA PRACTICA QUE NO TENGAN GRUPO
                if profesoresmateriassingrupo.values('id').filter(materia=materia).exists():
                    profemate = profesoresmateriassingrupo.filter(materia=materia)[0]
                    alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada,
                                                            profesormateria=profemate)
                    alumnopractica.save(request)
                    log(u'Materia (%s) con profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profemate, materiaasignada, alumnopractica.id), request, "add")
                # MATRICULA EN LA PRACTICA QUE SI TENGAN GRUPOS
                elif grupoprofesormaterias.values('id').filter(profesormateria__materia=materia).exists():
                    profemate_congrupo = grupoprofesormaterias.filter(profesormateria__materia=materia)[0]
                    if periodomatricula.valida_cupo_materia:
                        validar = True
                        if profemate_congrupo.profesormateria.materia.tipomateria == 2:
                            validar = variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL')
                        if validar:
                            if not HOMITIRCAPACIDADHORARIO and profemate_congrupo.cuposdisponiblesgrupoprofesor() <= 0:
                                raise NameError(u"Capacidad limite de la materia en la práctica:  " + unicode(profemate_congrupo.profesormateria.materia) + ", seleccione otro.")

                    alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada,
                                                            profesormateria=profemate_congrupo.profesormateria,
                                                            grupoprofesor=profemate_congrupo)
                    alumnopractica.save(request)
                    log(u'Materia (%s) con grupo profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profemate_congrupo, materiaasignada, alumnopractica.id), request, "add")
                log(u'Materia seleccionada matricula: %s' % materiaasignada, request, "add")
            matricula.actualizar_horas_creditos()
            if not inscripcion.itinerario or inscripcion.itinerario < 1:
                inscripcion.itinerario = codigoitinerario
                inscripcion.save(request)
        # with transaction.atomic():
        #     # if int(cobro) > 0:
        #     #     agregacion_aux_pregrado(request, matricula)
        #     matricula.actualiza_matricula()
        #     matricula.inscripcion.actualiza_estado_matricula()
        #     matricula.grupo_socio_economico(tipo_matricula_ri)
        #     calcula_nivel(matricula)

        matricula.agregacion_aux(request)
        matricula.calcula_nivel()

        if periodomatricula.valida_envio_mail:
            send_html_mail("Automatricula", "emails/matricula.html",
                           {
                               'sistema': request.session['nombresistema'],
                               'matricula': matricula,
                               't': miinstitucion(),
                               'ip': get_client_ip(request),
                           }, inscripcion.persona.lista_emails_envio(), [],
                           cuenta=CUENTAS_CORREOS[0][1])
        log(u'Automatricula estudiante: %s' % matricula, request, "add")

        valorpagar = str(null_to_decimal(matricula.rubro_set.filter(status=True).aggregate(valor=Sum('valortotal'))['valor']))

        descripcionarancel = ''
        valorarancel = ''
        if matricula.rubro_set.filter(status=True, tipo_id=RUBRO_ARANCEL).exists():
            ra = matricula.rubro_set.get(tipo_id=RUBRO_ARANCEL)
            descripcionarancel = ra.nombre
            valorarancel = str(ra.valortotal)

            matricula.aranceldiferido = 2
            matricula.save(request)

        ConfirmaCapacidadTecnologica.objects.filter(persona=matricula.inscripcion.persona).update(confirmado=True)
        request.session['periodo'] = matricula.nivel.periodo
        return True, None, {"valorpagar": valorpagar, "descripcionarancel": descripcionarancel, "valorarancel": valorarancel, "phase": matricula.id}
    except Exception as ex:
        transaction.set_rollback(True)
        return False, ex, {}


def generateCodeRemoveMateria(request, materiaasignada):
    with transaction.atomic():
        try:
            fecha = datetime.now().date()
            hora = datetime.now().time()
            fecha_hora = fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__()
            if not materiaasignada:
                raise NameError(u"Materia no encontrada")
            materia = materiaasignada.materia
            matricula = materiaasignada.matricula
            inscripcion = matricula.inscripcion
            persona = inscripcion.persona
            usuario = persona.usuario
            if not usuario:
                raise NameError(u"Usuario no encontrado")
            code = generate_code(6)
            token = md5(str(encrypt(usuario.id) + fecha_hora).encode("utf-8")).hexdigest()
            if materiaasignada.materiaasignadatoken_set.values("id").filter(status=True, isActive=True, user_token__user=usuario, user_token__isActive=True, user_token__action_type=2, user_token__date_expires__gte=datetime.now()).exists():
                raise NameError(u"Mantiene un código activo.")
            else:
                mis_materias = matricula.mismaterias()
                mis_materias = mis_materias.exclude(pk=materiaasignada.id)
                UserToken.objects.filter(user=usuario, isActive=True, action_type=2).exclude(pk__in=MateriaAsignadaToken.objects.values("user_token__id").filter(status=True, materia_asignada__in=mis_materias, isActive=True).distinct()).update(isActive=False)
                eUserToken = UserToken(user=usuario,
                                       token=token,
                                       action_type=2,
                                       date_expires=datetime.now() + timedelta(days=1),
                                       app=1,
                                       isActive=True)
                eUserToken.save(request)
                eMateriaAsignadaToken = MateriaAsignadaToken(materia_asignada=materiaasignada,
                                                             user_token=eUserToken,
                                                             codigo=code,
                                                             isActive=True,
                                                             num_email=1)
                eMateriaAsignadaToken.save(request)
                log(u'Genera codigo y token de retiro de materia: %s de la matricula: %s' % (materia, matricula), request, "add")
                app_label = 'sga'
                sistema = u'Sistema de Gestión Académica'
                send_html_mail("Código de confirmación - Retiro de materia",
                               "emails/solicitud_retiro_materia.html",
                               {'sistema': sistema,
                                'fecha': datetime.now().date,
                                'fecha_g': fecha,
                                'hora_g': hora,
                                'persona': persona,
                                'materia': materia,
                                'matricula': matricula,
                                'token': token,
                                'codigo': code,
                                'app_label': app_label,
                                't': miinstitucion(),
                                'dominio': EMAIL_DOMAIN,
                                'ip': get_client_ip(request),
                                },
                               persona.lista_emails(), [],
                               cuenta=CUENTAS_CORREOS[7][1])
            return JsonResponse({"result": "ok", "mensaje": "Se genero un correo con un código o link para retirar la materia."})
        except Exception as ex:
            transaction.set_rollback(True)
            return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})


def reenvioCodeRemoveMateria(request, materiaasignada):
    with transaction.atomic():
        try:
            materia = materiaasignada.materia
            matricula = materiaasignada.matricula
            inscripcion = matricula.inscripcion
            persona = inscripcion.persona
            usuario = persona.usuario
            if not materiaasignada.materiaasignadatoken_set.values("id").filter(status=True, isActive=True, user_token__user=usuario, user_token__isActive=True, user_token__action_type=2, user_token__date_expires__gte=datetime.now()).exists():
                raise NameError(u"No mantiene código activo.")
            eMateriaAsignadaToken = materiaasignada.materiaasignadatoken_set.filter(status=True, isActive=True, user_token__user=usuario, user_token__isActive=True, user_token__action_type=2, user_token__date_expires__gte=datetime.now())[0]
            eUserToken = eMateriaAsignadaToken.user_token
            eMateriaAsignadaToken.num_email = eMateriaAsignadaToken.num_email + 1
            eMateriaAsignadaToken.save(request)
            log(u'Reenvio de codigo y token de retiro de materia: %s de la matricula: %s' % (materia, matricula), request, "add")
            app_label = 'sga'
            sistema = u'Sistema de Gestión Académica'
            send_html_mail("Código de confirmación - Retiro de materia",
                           "emails/solicitud_retiro_materia.html",
                           {'sistema': sistema,
                            'fecha': datetime.now().date,
                            'fecha_g': eMateriaAsignadaToken.fecha_creacion.date(),
                            'hora_g': eMateriaAsignadaToken.fecha_creacion.time(),
                            'persona': persona,
                            'materia': materia,
                            'matricula': matricula,
                            'token': eUserToken.token,
                            'codigo': eMateriaAsignadaToken.codigo,
                            'app_label': app_label,
                            't': miinstitucion(),
                            'dominio': EMAIL_DOMAIN,
                            'ip': get_client_ip(request),
                            },
                           persona.lista_emails(), [],
                           cuenta=CUENTAS_CORREOS[7][1])
            contador = materiaasignada.contador_reenviar_email_token()
            return JsonResponse({"result": "ok", "mensaje": "Se reenvio correo con un código o link para retirar la materia.", "contador": contador})
        except Exception as ex:
            transaction.set_rollback(True)
            return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})


def generateCodeDeleteMatricula(request, matricula):
    with transaction.atomic():
        try:
            fecha = datetime.now().date()
            hora = datetime.now().time()
            fecha_hora = fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__()
            if not matricula:
                raise NameError(u"Matricula no encontrada")
            inscripcion = matricula.inscripcion
            persona = inscripcion.persona
            usuario = persona.usuario
            if not usuario:
                raise NameError(u"Usuario no encontrado")
            code = generate_code(6)
            token = md5(str(encrypt(usuario.id) + fecha_hora).encode("utf-8")).hexdigest()
            if matricula.matriculatoken_set.values("id").filter(status=True, isActive=True, user_token__user=usuario, user_token__isActive=True, user_token__action_type=3, user_token__date_expires__gte=datetime.now()).exists():
                raise NameError(u"Mantiene una recuperación de contraseña activa.")
            else:
                # BUSCAR TODAS LAS MATERIAS ASIGNADAS QUE TENGAN TOKEN ACTIVOS PARA INACTIVAR
                mis_materias = matricula.mismaterias()
                aMateriaAsignadaTokens = MateriaAsignadaToken.objects.filter(status=True, materia_asignada__in=mis_materias, isActive=True).update(isActive=False)
                UserToken.objects.filter(user=usuario, isActive=True, action_type=2).update(isActive=False)
                aMatriculaTokens = MatriculaToken.objects.filter(matricula=matricula, status=True, isActive=True).update(isActive=False)
                UserToken.objects.filter(user=usuario, isActive=True, action_type=3).update(isActive=False)
                eUserToken = UserToken(user=usuario,
                                       token=token,
                                       action_type=3,
                                       date_expires=datetime.now() + timedelta(days=1),
                                       app=1,
                                       isActive=True)
                eUserToken.save(request)
                eMatriculaToken = MatriculaToken(matricula=matricula,
                                                 user_token=eUserToken,
                                                 codigo=code,
                                                 isActive=True,
                                                 num_email=1)
                eMatriculaToken.save(request)
                log(u'Genera codigo y token de eliminar la matricula: %s' % matricula, request, "add")
                app_label = 'sga'
                sistema = u'Sistema de Gestión Académica'
                send_html_mail("Código de confirmación - Eliminar matrícula",
                               "emails/solicitud_eliminar_matricula.html",
                               {'sistema': sistema,
                                'fecha': datetime.now().date,
                                'persona': persona,
                                'matricula': matricula,
                                'fecha_g': eMatriculaToken.fecha_creacion.date(),
                                'hora_g': eMatriculaToken.fecha_creacion.time(),
                                'token': token,
                                'codigo': code,
                                'app_label': app_label,
                                't': miinstitucion(),
                                'ip': get_client_ip(request),
                                'dominio': EMAIL_DOMAIN
                                },
                               persona.lista_emails(), [],
                               cuenta=CUENTAS_CORREOS[7][1])
            return JsonResponse({"result": "ok", "mensaje": "Se genero un correo con un código o link para eliminar matrícula."})
        except Exception as ex:
            transaction.set_rollback(True)
            return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})


def reenvioCodeDeleteMatricula(request, matricula):
    with transaction.atomic():
        try:
            inscripcion = matricula.inscripcion
            persona = inscripcion.persona
            usuario = persona.usuario
            if not matricula.matriculatoken_set.values("id").filter(status=True, isActive=True, user_token__user=usuario, user_token__isActive=True, user_token__action_type=3, user_token__date_expires__gte=datetime.now()).exists():
                raise NameError(u"No mantiene código activo.")
            eMatriculaToken = matricula.matriculatoken_set.filter(status=True, isActive=True, user_token__user=usuario, user_token__isActive=True, user_token__action_type=3, user_token__date_expires__gte=datetime.now())[0]
            eUserToken = eMatriculaToken.user_token
            eMatriculaToken.num_email = eMatriculaToken.num_email + 1
            eMatriculaToken.save(request)
            log(u'Reenvio de codigo y token de eliminar matricula: %s' % matricula, request, "add")
            app_label = 'sga'
            sistema = u'Sistema de Gestión Académica'
            send_html_mail("Código de confirmación - Retiro de materia",
                           "emails/solicitud_eliminar_matricula.html",
                           {'sistema': sistema,
                            'fecha': datetime.now().date,
                            'fecha_g': eMatriculaToken.fecha_creacion.date(),
                            'hora_g': eMatriculaToken.fecha_creacion.time(),
                            'persona': persona,
                            'matricula': matricula,
                            'token': eUserToken.token,
                            'codigo': eMatriculaToken.codigo,
                            'app_label': app_label,
                            't': miinstitucion(),
                            'dominio': EMAIL_DOMAIN,
                            'ip': get_client_ip(request),
                            },
                           persona.lista_emails(), [],
                           cuenta=CUENTAS_CORREOS[7][1])
            contador = matricula.contador_reenviar_email_token()
            return JsonResponse({"result": "ok", "mensaje": "Se reenvio correo con un código o link para eliminar la matrícula.", "contador": contador})
        except Exception as ex:
            transaction.set_rollback(True)
            return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})


def generar_codigo_matricula_especial(sufijo):
    if not sufijo:
        raise NameError(u"Proceso de código no configurado")
    SUFFIX = sufijo.strip()
    secuencia = 1
    try:
        if datetime.now().month == 1 and datetime.now().day == 1 and not SolicitudMatriculaEspecial.objects.filter(fecha__gte=datetime.now().date(), secuencia__gt=0).exists():
            secuencia = 1
        else:
            if SolicitudMatriculaEspecial.objects.filter(secuencia__gt=0).order_by("-secuencia").exists():
                sec = SolicitudMatriculaEspecial.objects.filter(secuencia__gt=0).order_by("-secuencia")[0].secuencia
                if sec:
                    secuencia = int(sec) + 1
    except:
        pass
    return generar_codigo(secuencia, 'UNEMI', SUFFIX, 7), secuencia


def puede_matricularse_seguncronograma_coordinacion_prematricula(inscripcion, periodo):
    coordinacion = inscripcion.coordinacion
    carrera = inscripcion.carrera
    nivelmalla = inscripcion.mi_nivel()
    if not periodo.periodomatricula_set.values('id').filter(status=True, activo=True).exists():
        return False
    periodomatricula = periodo.periodomatricula_set.filter(status=True, activo=True)
    if not periodomatricula.values('id').filter(valida_cronogramaprematricula=True).exists():
        return True
    periodomatricula = periodomatricula[0]
    # if not periodomatricula.tiene_coordincaciones():
    #     return True
    # if not coordinacion.id in periodomatricula.coordinaciones().values_list("id", flat=True):
    #     return True
    if not periodomatricula.tiene_cronograma_coordinacionesprematricula():
        return True
    cronogramacoordinacion = periodomatricula.cronograma_coordinacionesprematricula()
    if not coordinacion.id in list(cronogramacoordinacion.values_list('coordinacion_id', flat=True)):
        return False
    cronogramacoordinacion = cronogramacoordinacion.filter(coordinacion=coordinacion)[0]
    if not cronogramacoordinacion.activo:
        return False
    fhInicioCoordinacion = datetime.combine(cronogramacoordinacion.fechainicio, cronogramacoordinacion.horainicio)
    fhFinCoordinacion = datetime.combine(cronogramacoordinacion.fechafin, cronogramacoordinacion.horafin)
    if not (fhInicioCoordinacion <= datetime.now() <= fhFinCoordinacion):
        return False

    if not cronogramacoordinacion.tiene_cronogramacarrerasprematricula():
        return True
    cronogramacarrera = cronogramacoordinacion.cronogramacarrerasprematricula()
    if not carrera.id in list(cronogramacarrera.values_list('carrera_id', flat=True)):
        return False
    cronogramacarrera = cronogramacarrera.filter(carrera=carrera)[0]
    if not cronogramacarrera.activo:
        return False
    fhInicioCarrera = datetime.combine(cronogramacarrera.fechainicio, cronogramacarrera.horainicio)
    fhFinCarrera = datetime.combine(cronogramacarrera.fechafin, cronogramacarrera.horafin)

    # SI TIENE NIVELES SE VERIFICA EL NIVEL DEL ESTUDIANTE VS EL NIVEL PLANIFICADO
    if cronogramacarrera.tiene_niveles():
        # SI EXISTE NIVEL PLANIFICADO SE VERIFICA SI ESTA EN LA FECHA
        if not nivelmalla.nivel_id in list(cronogramacarrera.niveles().values_list('id', flat=True)):
            return False
    if not (fhInicioCarrera <= datetime.now() <= fhFinCarrera):
        return False
    return True


def get_materias_x_inscripcion_x_asignatura(eNivel, eInscripcion, eAsignaturaMalla, eParalelo=None):
    hoy = datetime.now()
    ePeriodoMatricula = eNivel.periodo.periodomatricula_set.filter(status=True).first()
    if not ePeriodoMatricula:
        raise NameError(u"Periodo académico no existe")
    eMalla = eInscripcion.mi_malla()
    materias = []
    estado = eInscripcion.estado_asignatura(eAsignaturaMalla.asignatura)
    if not estado in [1, 2]:
        if eInscripcion.itinerario:
            if eAsignaturaMalla.itinerario:
                if eInscripcion.itinerario == eAsignaturaMalla.itinerario:
                    estado = 3
                else:
                    estado = 0
            else:
                estado = 3
        else:
            estado = 3
    eMateriasAbiertas = Materia.objects.filter(Q(asignatura=eAsignaturaMalla.asignatura, inicio__gte=hoy, nivel__cerrado=False, nivel__periodo=eNivel.periodo), status=True)
    if ePeriodoMatricula and ePeriodoMatricula.valida_materia_carrera:
        eMateriasAbiertas = eMateriasAbiertas.filter(asignaturamalla__malla=eMalla)
    eSesiones = Sesion.objects.filter(status=True, clasificacion=1, tipo=1)
    PRESENCIALES = [1, 4, 5]
    SEMIPRESENCIALES = [7]
    EN_LINEA = [13]
    if eInscripcion.sesion_id in PRESENCIALES:
        eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.filter(pk__in=PRESENCIALES))
    elif eInscripcion.sesion_id in EN_LINEA:
        eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.filter(pk__in=EN_LINEA))
    elif eInscripcion.sesion_id in SEMIPRESENCIALES:
        eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.filter(pk__in=SEMIPRESENCIALES))
    else:
        eModalidad = eInscripcion.modalidad
        if eModalidad:
            if eModalidad.es_presencial():
                eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.filter(pk__in=PRESENCIALES))
            elif eModalidad.es_semipresencial():
                eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.filter(pk__in=SEMIPRESENCIALES))
            elif eModalidad.es_enlinea():
                eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.filter(pk__in=EN_LINEA))
            else:
                eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.none())
        else:
            eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.none())
    eMateriasAbiertas_aux = eMateriasAbiertas
    if estado != 2:
        if ePeriodoMatricula and ePeriodoMatricula.valida_seccion:
            eMateriasAbiertas_s = eMateriasAbiertas.filter(nivel__sesion=eInscripcion.sesion)
            capacidad = null_to_numeric(eMateriasAbiertas_s.aggregate(capacidad=Sum('cupo'))['capacidad'])
            asignados = MateriaAsignada.objects.values("id").filter(status=True, materia__in=eMateriasAbiertas_s).count()
            if eMateriasAbiertas_s.values("id").exists() and asignados < capacidad:
                eMateriasAbiertas_aux = eMateriasAbiertas_s
        eMateriasAbiertas = eMateriasAbiertas_aux
        if eParalelo and eAsignaturaMalla.itinerario == 0:
            if eInscripcion.estado_asignatura(eAsignaturaMalla.asignatura) in [1, 0]:
                eMateriasAbiertas_p = eMateriasAbiertas_aux.filter(paralelomateria=eParalelo)
                capacidad = null_to_numeric(eMateriasAbiertas_p.aggregate(capacidad=Sum('cupo'))['capacidad'])
                asignados = MateriaAsignada.objects.values("id").filter(status=True, materia__in=eMateriasAbiertas_p).count()
                if eMateriasAbiertas_p.values("id").exists() and asignados < capacidad:
                    eMateriasAbiertas = eMateriasAbiertas_p
    eMateriasAbiertas = eMateriasAbiertas.distinct().order_by('paralelomateria__nombre')
    for _eMateria in eMateriasAbiertas:
        puede_agregar = False
        coordinacion = _eMateria.coordinacion()
        horarios_verbose = []
        horarios = []
        horarios_verbose_aux = []
        _horarios = get_horarios_clases_data(_eMateria)
        if ePeriodoMatricula.ver_horario_materia:
            horarios_verbose = get_horarios_clases_informacion(_eMateria)
            horarios_verbose_aux = _horarios
        if ePeriodoMatricula.valida_conflicto_horario:
            horarios = _horarios
        mispracticas = get_practicas_data(_eMateria)
        if _eMateria.nivel.puede_agregar_materia_matricula():
            puede_agregar = True
        materias.append({"id": _eMateria.id,
                         "asignatura": _eMateria.asignatura.nombre,
                         "nivelmalla": to_unicode(_eMateria.asignaturamalla.nivelmalla.nombre) if _eMateria.asignaturamalla.nivelmalla else "",
                         "nivelmalla_id": _eMateria.asignaturamalla.nivelmalla.id if _eMateria.asignaturamalla.nivelmalla else 0,
                         'sede': to_unicode(_eMateria.nivel.sede.nombre) if _eMateria.nivel.sede else "",
                         "carrera": to_unicode(_eMateria.asignaturamalla.malla.carrera.nombre_completo()) if _eMateria.asignaturamalla.malla.carrera else "",
                         "coordinacion": coordinacion.nombre if coordinacion else None,
                         "coordinacion_alias": coordinacion.alias if coordinacion else None,
                         "paralelo": _eMateria.paralelomateria.nombre,
                         "paralelo_id": _eMateria.paralelomateria.id,
                         "profesor": (_eMateria.profesor_principal().persona.nombre_completo()) if _eMateria.profesor_principal() else 'SIN DEFINIR',
                         'inicio': _eMateria.inicio.strftime("%d-%m-%Y"),
                         'fin': _eMateria.fin.strftime("%d-%m-%Y"),
                         'session': to_unicode(_eMateria.nivel.sesion.nombre),
                         'identificacion': _eMateria.identificacion,
                         "tipomateria": _eMateria.tipomateria,
                         "tipomateria_display": _eMateria.get_tipomateria_display(),
                         "teoriapractica": 1 if _eMateria.asignaturamalla.practicas else 0,
                         "cupos": _eMateria.cupo if ePeriodoMatricula and ePeriodoMatricula.valida_cupo_materia else 0,
                         "disponibles": _eMateria.capacidad_disponible() if ePeriodoMatricula and ePeriodoMatricula.valida_cupo_materia else 0,
                         "horarios_verbose": horarios_verbose,
                         "horarios_verbose_aux": horarios_verbose_aux,
                         "horarios": horarios,
                         "mispracticas": mispracticas,
                         "puede_agregar": puede_agregar,
                         "validaconflictohorarioalu": _eMateria.validaconflictohorarioalu,
                         })
    return materias


def get_materias_x_inscripcion_x_asignatura_aux(eNivel, eInscripcion, eAsignaturaMalla, eParalelo=None):
    hoy = datetime.now()
    ePeriodoMatricula = None
    ePeriodoMatriculas = eNivel.periodo.periodomatricula_set.filter(status=True)
    if ePeriodoMatriculas.values('id').exists():
        ePeriodoMatricula = ePeriodoMatriculas[0]
    if not ePeriodoMatricula:
        raise NameError(u"Periodo académico no existe")
    eMalla = eInscripcion.mi_malla()
    aMaterias = []
    estado = eInscripcion.estado_asignatura(eAsignaturaMalla.asignatura)
    if not estado in [1, 2]:
        if eInscripcion.itinerario:
            if eAsignaturaMalla.itinerario:
                if eInscripcion.itinerario == eAsignaturaMalla.itinerario:
                    estado = 3
                else:
                    estado = 0
            else:
                estado = 3
        else:
            estado = 3
    eMateriasAbiertas = Materia.objects.filter(Q(asignatura=eAsignaturaMalla.asignatura, inicio__gte=hoy, nivel__cerrado=False, nivel__periodo=eNivel.periodo), status=True)
    if ePeriodoMatricula and ePeriodoMatricula.valida_materia_carrera:
        eMateriasAbiertas = eMateriasAbiertas.filter(asignaturamalla__malla=eMalla)
    eSesiones = Sesion.objects.filter(status=True, clasificacion=1, tipo=1)
    PRESENCIALES = [1, 4, 5]
    SEMIPRESENCIALES = [7]
    EN_LINEA = [13]
    if eInscripcion.sesion_id in PRESENCIALES:
        eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.filter(pk__in=PRESENCIALES))
    elif eInscripcion.sesion_id in EN_LINEA:
        eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.filter(pk__in=EN_LINEA))
    elif eInscripcion.sesion_id in SEMIPRESENCIALES:
        eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.filter(pk__in=SEMIPRESENCIALES))
    else:
        eModalidad = eInscripcion.modalidad
        if eModalidad:
            if eModalidad.es_presencial():
                eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.filter(pk__in=PRESENCIALES))
            elif eModalidad.es_semipresencial():
                eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.filter(pk__in=SEMIPRESENCIALES))
            elif eModalidad.es_enlinea():
                eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.filter(pk__in=EN_LINEA))
            else:
                eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.none())
        else:
            eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.none())
    eMateriasAbiertas_aux = eMateriasAbiertas
    if estado != 2:
        if ePeriodoMatricula and ePeriodoMatricula.valida_seccion:
            eMateriasAbiertas_s = eMateriasAbiertas.filter(nivel__sesion=eInscripcion.sesion)
            capacidad = null_to_numeric(eMateriasAbiertas_s.aggregate(capacidad=Sum('cupo'))['capacidad'])
            asignados = MateriaAsignada.objects.values("id").filter(status=True, materia__in=eMateriasAbiertas_s).count()
            if eMateriasAbiertas_s.values("id").exists() and asignados < capacidad:
                eMateriasAbiertas_aux = eMateriasAbiertas_s
        eMateriasAbiertas = eMateriasAbiertas_aux
        if eParalelo and eAsignaturaMalla.itinerario == 0:
            if eInscripcion.estado_asignatura(eAsignaturaMalla.asignatura) in [1, 0]:
                eMateriasAbiertas_p = eMateriasAbiertas_aux.filter(paralelomateria=eParalelo)
                capacidad = null_to_numeric(eMateriasAbiertas_p.aggregate(capacidad=Sum('cupo'))['capacidad'])
                asignados = MateriaAsignada.objects.values("id").filter(status=True, materia__in=eMateriasAbiertas_p).count()
                if eMateriasAbiertas_p.values("id").exists() and asignados < capacidad:
                    eMateriasAbiertas = eMateriasAbiertas_p
    eMateriasAbiertas = eMateriasAbiertas.distinct().order_by('paralelomateria__nombre')
    for eMateria in eMateriasAbiertas:
        eMateria_data = MatriMateriaSerializer(eMateria).data
        eMateria_data.__setitem__('horarios', get_horarios_clases_data(eMateria) if ePeriodoMatricula.valida_conflicto_horario or ePeriodoMatricula.ver_horario_materia else [])
        eMateria_data.__setitem__('mispracticas', get_practicas_data(eMateria))
        eMateria_data.__setitem__('disponibles', eMateria.capacidad_disponible() if ePeriodoMatricula.valida_cupo_materia else 0)
        # eMateria.__setitem__('carrera', to_unicode(eM.asignaturamalla.malla.carrera.nombre_completo()) if eM.asignaturamalla.malla.carrera.nombre else "")
        eMateria_data.__setitem__('profesor', (eMateria.profesor_principal().persona.nombre_completo()) if eMateria.profesor_principal() else 'SIN DEFINIR')
        eMateria_data.__setitem__('session', to_unicode(eMateria.nivel.sesion.nombre))
        eMateria_data.__setitem__('tipomateria_display', eMateria.get_tipomateria_display())
        aMaterias.append(eMateria_data)
    return aMaterias

def generar_acta_compromiso(materiaasignada):
    url_path = 'http://127.0.0.1:8000'
    if not DEBUG:
        url_path = 'https://sga.unemi.edu.ec'
    hoy = datetime.now()
    data={}
    data['fecha'] = hoy.date
    data['hora'] = hoy.time()
    data['materiaasignada'] = materiaasignada
    nombre_archivo = generar_nombre(f'acta_compromiso_{materiaasignada.id}_', 'generado') + '.pdf'
    data['persona']=persona=materiaasignada.matricula.inscripcion.persona
    formato_acta = 'matriculacion/acta_compromiso_asignaturapracticas_enlinea.html'
    url_acta = 'actas_practicas'
    if materiaasignada.materia.asignaturamalla.asignaturapracticas and materiaasignada.materia.asignaturamalla.asignaturavinculacion:
        formato_acta = 'matriculacion/acta_compromiso_vinculacionpracticas_enlinea.html'
    elif materiaasignada.materia.asignaturamalla.asignaturapracticas:
        formato_acta = 'matriculacion/acta_compromiso_asignaturapracticas_enlinea.html'
    elif materiaasignada.materia.asignaturamalla.asignaturavinculacion:
        url_acta = 'actas_vinculacion'
        formato_acta = 'matriculacion/acta_compromiso_vinculacion_enlinea.html'
    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'matriculacion', 'actas_practicas', ''))
    filename = generar_nombre(f'acta_compromiso_asignaturaprac_{persona.usuario.username}_{materiaasignada.id}_','')
    os.makedirs(folder, exist_ok=True)
    os.makedirs(f'{folder}/qrcode/', exist_ok=True)
    data['url_pdf'] = url_pdf = f'{url_path}/media/matriculacion/{url_acta}/{nombre_archivo}'
    url = pyqrcode.create(url_pdf)
    imageqr = url.png(f'{folder}/qrcode/{filename}.png', 16, '#000000')
    data['url_qr'] = f'{folder}/qrcode/{filename}.png'
    pdf, response = conviert_html_to_pdf_save_file_model(
        formato_acta,
        {'pagesize': 'a4 landscape',
         'data': data, }, nombre_archivo)
    return pdf, response

def pre_inscripcion_practicas_pre_profesionales(request, eMateriaAsignada, matricula, pdf, action):
    try:
        habilita_preinscripcion_ppp = variable_valor('HABILITA_PREINSCRIPCION_PPP_MATRICULA')
        if habilita_preinscripcion_ppp:
            inscripcion = matricula.inscripcion
            periodo = matricula.nivel.periodo
            coordinacion = matricula.inscripcion.carrera.coordinacion_carrera()
            eMateria = eMateriaAsignada.materia
            carrera = eMateria.asignaturamalla.malla.carrera
            enlinea = carrera.modalidad == 3
            if enlinea:
                nivelmalla = eMateria.asignaturamalla.nivelmalla
                asignatura_itinerariomalla = eMateria.asignaturamalla.itinerarioasignaturamalla_set.filter(status=True).last()
                itinerariomalla = asignatura_itinerariomalla.itinerariomalla if asignatura_itinerariomalla else None

                pre_inscripcion = ExtraPreInscripcionPracticasPP.objects.filter(status=True, enlinea=enlinea, preinscripcion__status=True,
                                                                                preinscripcion__periodo=periodo, preinscripcion__coordinacion__in=[coordinacion],
                                                                                preinscripcion__carrera__in=[carrera]).distinct().first()
                preinscripcion = pre_inscripcion.preinscripcion if pre_inscripcion else None

                if preinscripcion and action == 'add':

                    if itinerariomalla:
                        detallepreinscripcion = DetallePreInscripcionPracticasPP(inscripcion=inscripcion,
                                                                                 nivelmalla=nivelmalla,
                                                                                 preinscripcion=preinscripcion,
                                                                                 fecha=datetime.now(),
                                                                                 itinerariomalla=itinerariomalla,
                                                                                 estado=1
                                                                                 )
                        detallepreinscripcion.save(request)

                        extradetalle = ExtraDetallePreInscripcionPracticasPP(detallepreins=detallepreinscripcion, migradomatricula=True)
                        extradetalle.save(request)
                        if pdf:
                            extradetalle.actacompromisopracticas = pdf
                            extradetalle.save(request)
                        log(u'Adicionó detalle de preinscripción prácticas PP (matricula): %s' % (detallepreinscripcion), request, "add")

                elif preinscripcion and action == 'del':
                    if itinerariomalla:
                        if detpre := DetallePreInscripcionPracticasPP.objects.filter(inscripcion=inscripcion, preinscripcion=preinscripcion, itinerariomalla=itinerariomalla, estado=1, status=True).first():
                            log(u'Eliminó detalle de preinscripción prácticas PP (matricula): %s' % (detpre), request, "add")
                            detpre.delete()

                elif preinscripcion and action == 'deladm':
                    if itinerariomalla:
                        detpre = DetallePreInscripcionPracticasPP.objects.filter(inscripcion=inscripcion, preinscripcion=preinscripcion, itinerariomalla=itinerariomalla, status=True)
                        if detpreinscripcion := detpre.filter(estado=2).first():
                            detpreinscripcion.estado = 3
                            detpreinscripcion.save(request)
                            if pra := detpreinscripcion.practicaspreprofesionalesinscripcion_set.filter(status=True).first():
                                pra.estadosolicitud = 3 #5 es RETIRADO
                                pra.save(request)
                            log(u'Administrativo rechazó la pre-inscripción por retiro de materia práctica: %s' % detpreinscripcion, request, "rech")
                            recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=detpreinscripcion,
                                                                                 fecha=datetime.now().date(),
                                                                                 observacion=f'Estudiante fué RETIRADO de la materia práctica: {eMateria}',
                                                                                 estado=detpreinscripcion.estado)
                            recorrido.save(request)
                            log(u'Rechazo la pre-inscripción: %s' % detpreinscripcion, request, "rech")

                        elif detpreinscripcion := detpre.filter(estado=1).first():
                            log(u'Administrativo eliminó detalle de preinscripción prácticas PP (matricula) por retiro de materia práctica: %s' % (detpre), request, "add")
                            detpreinscripcion.delete()

    except Exception as ex:
        pass