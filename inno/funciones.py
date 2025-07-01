# coding=utf-8
from __future__ import division

import uuid
import random
import string
import threading
from hashlib import md5
from decimal import Decimal
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType
from bd.models import UserToken
from secrets import token_hex
import json
from decorators import get_client_ip
from inno.models import HorarioTutoriaAcademica
from settings import EMAIL_DOMAIN, NOTA_ESTADO_APROBADO, DEBUG, HOMITIRCAPACIDADHORARIO, NOTA_ESTADO_EN_CURSO, RUBRO_ARANCEL
from sga.funciones import log, null_to_decimal, to_unicode, variable_valor, notificacion, fechatope, convertir_fecha
from sga.commonviews import conflicto_materias_estudiante
from sga.models import miinstitucion, CUENTAS_CORREOS, Persona, Notificacion, Materia, PerfilUsuario, Modulo, \
    LeccionGrupo, Clase, ProfesorMateria, DetalleDistributivo, ComplexivoClase, Sesion, ComplexivoLeccion, ModuloMalla, \
    Inscripcion, AsignaturaMalla, RecordAcademico, ParticipantesMatrices, PracticasPreprofesionalesInscripcion, \
    CertificadoIdioma, HistorialCertificacionPersona, IpPermitidas, TestSilaboSemanal, TareaSilaboSemanal, \
    ForoSilaboSemanal, TareaPracticaSilaboSemanal, Asignatura, Nivel, DetallePreInscripcionPracticasPP, DetalleRecoridoPreInscripcionPracticasPP, \
    Profesor, MateriaAsignada, GruposProfesorMateria, MATRICULACION_LIBRE, Matricula, AlumnosPracticaMateria, ConfirmaCapacidadTecnologica, CriterioDocenciaPeriodo, ProfesorDistributivoHoras
from inno.models import CalendarioRecursoActividad, CalendarioRecursoActividadAlumno , SecuenciaEvidenciaSalud, \
    ConfiguracionInscripcionPracticasPP, PracticasPreprofesionalesInscripcionExtensionSalud, HistorialInscricionOferta
from matricula.funciones import get_tipo_matricula, TIPO_PROFESOR_PRACTICA, calcula_nivel
from django.forms import model_to_dict
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from datetime import datetime, timedelta

unicode = str


def generar_clave_aleatoria(limit=50, mini=False):
    clave = ''
    base_string = '0123456789#ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz*'
    if mini:
        base_string = '0123456789abcdefghijklmnopqrstuvwxyz'
    for i in range(limit):
        clave += random.choice(base_string)
    return clave


def enviar_notificacion_solicitud_registro_asistencia_pro(profesor, solicitudes):
    coordinadores = []
    for solicitud in solicitudes:
        if solicitud.materia.asignaturamalla.malla.carrera.tiene_coordinaciones():
            periodo = solicitud.materia.nivel.periodo
            if solicitud.materia.asignaturamalla.malla.carrera.coordinadores(periodo).filter(tipo=3).values("id").exists():
                coordinacion = solicitud.materia.asignaturamalla.malla.carrera.coordinadores(periodo).filter(tipo=3)[0]
                if not coordinacion.persona.id in coordinadores:
                    coordinadores.append(coordinacion.persona.id)

    for coordinador in Persona.objects.filter(pk__in=coordinadores).distinct():
        materias = []
        for solicitud in solicitudes:
            if solicitud.materia.asignaturamalla.malla.carrera.tiene_coordinaciones():
                periodo = solicitud.materia.nivel.periodo
                if solicitud.materia.asignaturamalla.malla.carrera.coordinadores(periodo).filter(tipo=3).values("id").exists():
                    coordinacion = solicitud.materia.asignaturamalla.malla.carrera.coordinadores(periodo).filter(tipo=3)[0]
                    if coordinacion.persona.id == coordinador.id:
                        if not solicitud.materia.id in materias:
                            materias.append(solicitud.materia.id)

        if Materia.objects.values("id").filter(pk__in=materias).exists():
            eMaterias = Materia.objects.filter(pk__in=materias).distinct()
            notificacion = Notificacion(titulo=f"Tiene {'solicitudes' if eMaterias.count() > 1 else 'solicitud'} de apertura de clase {'del profesor' if profesor.persona.sexo.id == 1 else 'de la profesora'} {profesor.__str__()}",
                                        cuerpo=f"{'solicitudes de las materias' if eMaterias.count() > 1 else 'Solicitud de la materia'} {', '.join([x.nombre_mostrar_solo() for x in eMaterias])}",
                                        destinatario=coordinador,
                                        url="/adm_aperturaclase",
                                        content_type=None,
                                        object_id=None,
                                        prioridad=1,
                                        app_label='sga',
                                        fecha_hora_visible=datetime.now() + timedelta(days=3)
                                        )
            notificacion.save()


def enviar_notificacion_aceptar_rechazar_solicitud_asistencia_pro(solicitud):
    titulo = ''
    if solicitud.estado == 1:
        titulo = 'Director/a aprobó solicitud de registro de clase'
    elif solicitud.estado == 2:
        titulo = 'Director/a rechazo solicitud de registro de clase'
    else:
        titulo = 'Cambio de estado de la solicitud de registro de clase'
    ePerfilDocente = None
    eModulo = None
    for ePerfil in PerfilUsuario.objects.filter(persona=solicitud.profesor.persona):
        if ePerfil.es_profesor():
            ePerfilDocente = ePerfil
            break
    if ePerfilDocente:
        eModulos = Modulo.objects.filter(Q(url='pro_aperturaclase') | Q(url='/pro_aperturaclase'))
        if eModulos.values("id").exists():
            eModulo = eModulos[0]
    notificacion = Notificacion(titulo=titulo,
                                cuerpo=f"Hubo un cambio de estado en la solicitud { solicitud.mi_clase() if solicitud.mi_clase() else solicitud.__str__()}",
                                destinatario=solicitud.profesor.persona,
                                url="/pro_aperturaclase",
                                content_type=ContentType.objects.get_for_model(solicitud),
                                object_id=solicitud.id,
                                prioridad=1,
                                app_label='sga',
                                fecha_hora_visible=datetime.now() + timedelta(days=3),
                                perfil=ePerfilDocente,
                                modulo=eModulo
                                )
    notificacion.save()


def estar_matriculado_todas_asignaturas_ultimo_periodo_academico(id_inscripcion):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    return eInscripcion.esta_matriculado_ultimo_nivel()


def asignaturas_aprobadas_primero_penultimo_nivel(id_inscripcion):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    return eInscripcion.aprobo_asta_penultimo_malla()

def detalle_aprobadas_primero_penultimo_nivel(id_inscripcion):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    totalrecord = eInscripcion.cantidad_asig_aprobada_penultimo_malla()
    totalmalla = eInscripcion.cantidad_asig_aprobar_penultimo_malla()
    color = 'danger'
    if totalrecord >= totalmalla:
        color = 'success'
    texto = "<span class='badge rounded-pill bg-" + color + "'>MALLA " + str(totalmalla) + "</span> <span class='badge rounded-pill bg-" + color + "'> RECORD " + str(totalrecord) + "</span>"
    return texto

def asignaturas_aprobadas_primero_ultimo_nivel(id_inscripcion):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    malla = eInscripcion.inscripcionmalla_set.filter(status=True)[0].malla
    # total_materias_malla = malla.cantidad_materiasaprobadas()
    cantidadmalla = eInscripcion.cantidad_asig_aprobar_ultimo_malla()
    cantidad_materias_aprobadas_record = len(eInscripcion.recordacademico_set.filter(aprobada=True, status=True, asignatura__in=[x.asignatura for x in malla.asignaturamalla_set.filter(status=True)]))
    # poraprobacion = round(cantidad_materias_aprobadas_record * 100 / total_materias_malla, 0)
    poraprobacion = round(cantidad_materias_aprobadas_record * 100 / cantidadmalla, 0)
    if poraprobacion >= 100:
        return True
    else:
        return False

def asignaturas_aprobadas_primero_septimo_nivel(id_inscripcion):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    return eInscripcion.aprobo_hasta_septimo_malla()


def ficha_estudiantil_actualizada_completa(id_inscripcion):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))

    def tiene_pais_residencia():
        if not eInscripcion.persona.pais:
            return False
        if not eInscripcion.persona.pais_id == 1:
            return eInscripcion.persona.direccion and eInscripcion.persona.direccion2 and eInscripcion.persona.num_direccion and eInscripcion.persona.telefono_conv or eInscripcion.persona.telefono
        return eInscripcion.persona.provincia and eInscripcion.persona.canton and eInscripcion.persona.parroquia and eInscripcion.persona.direccion and eInscripcion.persona.direccion2 and eInscripcion.persona.num_direccion and eInscripcion.persona.telefono_conv or eInscripcion.persona.telefono

    def tiene_pais_nacimiento():
        if not eInscripcion.persona.paisnacimiento:
            return False
        if not eInscripcion.persona.paisnacimiento_id == 1:
            return True
        return eInscripcion.persona.provincianacimiento and eInscripcion.persona.cantonnacimiento and eInscripcion.persona.parroquianacimiento


    perfil = eInscripcion.persona.mi_perfil()
    ficha = 0
    if eInscripcion.persona.nombres and eInscripcion.persona.apellido1 and eInscripcion.persona.apellido2 and eInscripcion.persona.nacimiento and eInscripcion.persona.cedula and eInscripcion.persona.nacionalidad and eInscripcion.persona.email and eInscripcion.persona.estado_civil and eInscripcion.persona.sexo:
        ficha += 1
    if tiene_pais_nacimiento():
        ficha += 1
    examenfisico = eInscripcion.persona.datos_examen_fisico()
    if eInscripcion.persona.sangre and examenfisico.peso and examenfisico.talla:
        ficha += 1
    if tiene_pais_residencia():
        ficha += 1
    if perfil.raza:
        ficha += 1
    return ficha == 5


def detalle_ficha_estudiantil_actualizada_completa(id_inscripcion):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    perfil = eInscripcion.persona.mi_perfil()
    texto = ''
    if not eInscripcion.persona.nombres: texto += "<span class='badge rounded-pill bg-danger'>NOMBRES</span>"
    if not eInscripcion.persona.apellido1: texto += "<span class='badge rounded-pill bg-danger'>APELLIDOS</span>"
    if not eInscripcion.persona.apellido2: texto += "<span class='badge rounded-pill bg-danger'>APELLIDOS</span>"
    if not eInscripcion.persona.nacimiento: texto += "<span class='badge rounded-pill bg-danger'>FECHA NACIMIENTO</span>"
    if not eInscripcion.persona.cedula: texto += "<span class='badge rounded-pill bg-danger'>CEDULA</span>"
    if not eInscripcion.persona.nacionalidad: texto += "<span class='badge rounded-pill bg-danger'>NACIONALIDAD</span>"
    if not eInscripcion.persona.email: texto += "<span class='badge rounded-pill bg-danger'>EMAIL</span>"
    if not eInscripcion.persona.estado_civil: texto += "<span class='badge rounded-pill bg-danger'>ESTADO CIVIL</span>"
    if not eInscripcion.persona.sexo: texto += "<span class='badge rounded-pill bg-danger'>GENERO</span>"
    if not eInscripcion.persona.paisnacimiento: texto += "<span class='badge rounded-pill bg-danger'>PAIS NACIMIENTO</span>"
    if not eInscripcion.persona.provincianacimiento: texto += "<span class='badge rounded-pill bg-danger'>PROVINCIA NACIMIENTO</span>"
    if not eInscripcion.persona.cantonnacimiento: texto += "<span class='badge rounded-pill bg-danger'>CANTON NACIMIENTO</span>"
    if not eInscripcion.persona.parroquianacimiento: texto += "<span class='badge rounded-pill bg-danger'>PARROQUIA NACIMIENTO</span>"
    examenfisico = eInscripcion.persona.datos_examen_fisico()
    if not eInscripcion.persona.sangre: texto += "<span class='badge rounded-pill bg-danger'>TIPO SANGRE</span>"
    if not examenfisico.peso: texto += "<span class='badge rounded-pill bg-danger'>PESO</span>"
    if not examenfisico.talla: texto += "<span class='badge rounded-pill bg-danger'>TALLA</span>"
    if not eInscripcion.persona.pais: texto += "<span class='badge rounded-pill bg-danger'>PAIS</span>"
    if eInscripcion.persona.pais_id == 1:
        if not eInscripcion.persona.provincia: texto += "<span class='badge rounded-pill bg-danger'>PROVINCIA</span>"
        if not eInscripcion.persona.canton: texto += "<span class='badge rounded-pill bg-danger'>CANTON</span>"
        if not eInscripcion.persona.parroquia: texto += "<span class='badge rounded-pill bg-danger'>PARROQUIA</span>"
    if not eInscripcion.persona.direccion: texto += "<span class='badge rounded-pill bg-danger'>DIRECCION DOMICILIARIA</span>"
    if not eInscripcion.persona.direccion2: texto += "<span class='badge rounded-pill bg-danger'>DIRECCION DOMICILIARIA</span>"
    if not eInscripcion.persona.num_direccion: texto += "<span class='badge rounded-pill bg-danger'>NUMERO DIRECCION</span>"
    if not eInscripcion.persona.telefono_conv: texto += "<span class='badge rounded-pill bg-danger'>TELEFONO CONVENCIONAL</span>"
    if not eInscripcion.persona.telefono: texto += "<span class='badge rounded-pill bg-danger'>TELEFONO CELULAR</span>"
    if not perfil.raza: texto += "<span class='badge rounded-pill bg-danger'>ETNIA</span>"
    if texto == '':
        return "<span class='badge rounded-pill bg-success'>FICHA COMPLETA</span>"
    return texto


def haber_aprobado_modulos_ingles(id_inscripcion):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    eMalla = eInscripcion.mi_malla()
    if not eMalla:
        return False
    if id_inscripcion in variable_valor('EXCLUIR_REQUISITO_INGLES'):
        return True
    ingles = ModuloMalla.objects.filter(malla=eMalla, status=True).exclude(asignatura_id=782)
    records = eInscripcion.recordacademico_set.filter(asignatura_id__in=ingles.values('asignatura_id'), aprobada=True)
    if not records.values("id").exists():
        return False
    if variable_valor('VALIDA_NIVEL_REQUISITO_INGLES_MATRICULACION'):
        if eMalla.modalidad.id == 3:
            nivel_maximo = variable_valor('NIVEL_MAXIMO_REQUISITO_INGLES_MATRICULACION') if variable_valor('NIVEL_MAXIMO_REQUISITO_INGLES_MATRICULACION') else 5
            ingles = ingles.filter(orden__lte=nivel_maximo).values('asignatura_id')
            records = eInscripcion.recordacademico_set.filter(asignatura_id__in=ingles, aprobada=True)
    return len(ingles) == len(records)


def detalle_aprobado_modulos_ingles(id_inscripcion):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    eMalla = eInscripcion.mi_malla()
    if not eMalla:
        return "<span class='badge rounded-pill bg-danger'>INSCRIPCION SIN MALLA</span>"
    totalmalla = ModuloMalla.objects.filter(malla=eMalla, status=True).exclude(asignatura_id=782)
    records = eInscripcion.recordacademico_set.filter(asignatura_id__in=totalmalla.values('asignatura_id'), aprobada=True)
    if totalmalla.count() < 1 :
        return "<span class='badge rounded-pill bg-danger'>MALLA NO TIENE CONFIGURADO CREDITOS DE INGLES</span>"
    if not records.values("id").exists():
        return "<span class='badge rounded-pill bg-danger'>NO TIENE MODULOS DE INGLES EN RECORD ACADEMICO</span>"
    color = 'danger'
    if records.count() >= totalmalla.count():
        color = 'success'
    texto = "<span class='badge rounded-pill bg-" + color + "'>MALLA " + str(totalmalla.count()) + "</span> <span class='badge rounded-pill bg-" + color + "'> RECORD " + str(records.count()) + "</span>"
    return texto


def haber_aprobado_modulos_computacion(id_inscripcion):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    eMalla = eInscripcion.mi_malla()
    if not eMalla:
        return False
    eAsignaturas = eInscripcion.recordacademico_set.filter(asignatura_id__in=AsignaturaMalla.objects.values('asignatura_id').filter(malla_id=32), aprobada=True)
    if not eAsignaturas.values("id").exists():
        return False
    if eMalla.creditos_computacion < 1:
        return False
    total = Decimal(null_to_decimal(eAsignaturas.aggregate(total=Sum('creditos'))['total'])).quantize(Decimal('.01'))
    return total >= Decimal(null_to_decimal(eMalla.creditos_computacion)).quantize(Decimal('.01'))


def detalle_aprobado_modulos_computacion(id_inscripcion):
    listado = []
    texto = ''
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    eMalla = eInscripcion.mi_malla()
    if not eMalla:
        return "<span class='badge rounded-pill bg-danger'>INSCRIPCION SIN MALLA</span>"
    eAsignaturas = eInscripcion.recordacademico_set.filter(asignatura_id__in=AsignaturaMalla.objects.values('asignatura_id').filter(malla_id=32), aprobada=True)
    if not eAsignaturas.values("id").exists():
        return "<span class='badge rounded-pill bg-danger'>NO TIENE MODULOS DE COMPUTACION EN RECORD ACADEMICO</span>"
    total = Decimal(null_to_decimal(eAsignaturas.aggregate(total=Sum('creditos'))['total'])).quantize(Decimal('.01'))
    totalmalla = Decimal(null_to_decimal(eMalla.creditos_computacion)).quantize(Decimal('.01'))
    if totalmalla < 1 :
        return "<span class='badge rounded-pill bg-danger'>MALLA NO TIENE CONFIGURADO CREDITOS DE COMPUTACION</span>"
    color = 'danger'
    if total >= totalmalla:
        color = 'success'
    texto = "<span class='badge rounded-pill bg-"+color+"'>MALLA " + str(totalmalla) + "</span> <span class='badge rounded-pill bg-"+color+"'> RECORD " + str(total) + "</span>"
    return texto


def haber_cumplido_horas_creditos_practicas_preprofesionales(id_inscripcion, nivel=0):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    eMalla = eInscripcion.mi_malla()
    if not eMalla:
        return False
    fechainicioprimernivel = eInscripcion.fechainicioprimernivel if eInscripcion.fechainicioprimernivel else datetime.now().date()
    if fechainicioprimernivel <= datetime(2009, 1, 21, 23, 59, 59).date():
        return True
    horaspracticas = eMalla.horas_practicas
    if nivel > 0:
        # if eMalla.ultimo_nivel_malla().id == nivel:
        #     return eInscripcion.numero_horas_practicas_pre_profesionales() >= horaspracticas
        # else:
        if eMalla.itinerariosmalla_set.filter(status=True, nivel_id__lte=nivel-1):
            horasnivel = eMalla.itinerariosmalla_set.filter(status=True, nivel_id__lte=nivel-1).aggregate(totalhoras=Sum('horas_practicas')).get('totalhoras')
            if horasnivel > 0:
                return eInscripcion.numero_horas_practicas_pre_profesionales() >= horasnivel
    return eInscripcion.numero_horas_practicas_pre_profesionales() >= horaspracticas


def detalle_cumplido_horas_creditos_practicas_preprofesionales(id_inscripcion):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    eMalla = eInscripcion.mi_malla()
    if not eMalla:
        return "<span class='badge rounded-pill bg-danger'>INSCRIPCION SIN MALLA</span>"
    fechainicioprimernivel = eInscripcion.fechainicioprimernivel if eInscripcion.fechainicioprimernivel else datetime.now().date()
    if fechainicioprimernivel <= datetime(2009, 1, 21, 23, 59, 59).date():
        return "<span class='badge rounded-pill bg-success'>APROBADO</span>"
    totalrecord = eInscripcion.numero_horas_practicas_pre_profesionales()
    totalmalla = eMalla.horas_practicas
    if totalmalla < 1:
        return "<span class='badge rounded-pill bg-danger'>MALLA NO TIENE CONFIGURADO CREDITOS DE PRACTICAS</span>"
    color = 'danger'
    if totalrecord >= totalmalla:
        color = 'success'
    texto = "<span class='badge rounded-pill bg-" + color + "'>MALLA " + str(totalmalla) + "</span> <span class='badge rounded-pill bg-" + color + "'> RECORD " + str(totalrecord) + "</span>"
    return texto


def haber_cumplido_horas_creditos_vinculacion(id_inscripcion, nivel=0):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    eMalla = eInscripcion.mi_malla()
    if not eMalla:
        return False
    fechainicioprimernivel = eInscripcion.fechainicioprimernivel if eInscripcion.fechainicioprimernivel else datetime.now().date()
    if fechainicioprimernivel <= datetime(2009, 1, 21, 23, 59, 59).date():
        return True
    horasvinculacion = eMalla.horas_vinculacion
    if nivel > 0:
        # if eMalla.ultimo_nivel_malla().id == nivel:
        #     return eInscripcion.numero_horas_proyectos_vinculacion() >= horasvinculacion
        # else:
        if eMalla.itinerariosvinculacionmalla_set.filter(status=True, nivel_id__lte=nivel-1):
            horasnivel = eMalla.itinerariosvinculacionmalla_set.filter(status=True, nivel_id__lte=nivel-1).aggregate(totalhoras=Sum('horas_vinculacion')).get('totalhoras')
            if horasnivel > 0:
                return eInscripcion.numero_horas_proyectos_vinculacion() >= horasnivel
    return eInscripcion.numero_horas_proyectos_vinculacion() >= horasvinculacion


def detalle_cumplido_horas_creditos_vinculacion(id_inscripcion):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    eMalla = eInscripcion.mi_malla()
    if not eMalla:
        return "<span class='badge rounded-pill bg-danger'>INSCRIPCION SIN MALLA</span>"
    fechainicioprimernivel = eInscripcion.fechainicioprimernivel if eInscripcion.fechainicioprimernivel else datetime.now().date()
    if fechainicioprimernivel <= datetime(2009, 1, 21, 23, 59, 59).date():
        return "<span class='badge rounded-pill bg-success'>APROBADO</span>"
    totalrecord = eInscripcion.numero_horas_proyectos_vinculacion()
    totalmalla = eMalla.horas_vinculacion
    if totalmalla < 1 :
        return "<span class='badge rounded-pill bg-danger'>MALLA NO TIENE CONFIGURADO CREDITOS DE VINCULACION</span>"
    color = 'danger'
    if totalrecord >= totalmalla:
        color = 'success'
    texto = "<span class='badge rounded-pill bg-"+color+"'>MALLA " + str(totalmalla) + "</span> <span class='badge rounded-pill bg-"+color+"'> RECORD " + str(totalrecord) + "</span>"
    return texto

def detalle_aprobadas_primero_ultimo_nivel(id_inscripcion):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    inscripcionmalla = eInscripcion.malla_inscripcion()
    malla = inscripcionmalla.malla
    cantidadmalla = eInscripcion.cantidad_asig_aprobar_ultimo_malla()
    cantidad_materias_aprobadas_record = eInscripcion.recordacademico_set.filter(aprobada=True, status=True, asignatura__in=[x.asignatura for x in malla.asignaturamalla_set.filter(status=True)]).count()
    poraprobacion = round(cantidad_materias_aprobadas_record * 100 / cantidadmalla, 0)
    color = 'danger'
    if poraprobacion >= 100:
        color = 'success'
    texto = "<span class='badge rounded-pill bg-"+color+"'>MALLA " + str(cantidadmalla) + "</span> <span class='badge rounded-pill bg-"+color+"'> RECORD " + str(cantidad_materias_aprobadas_record) + "</span>"
    return texto

def no_adeudar_institucion(id_inscripcion):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    return not eInscripcion.persona.tiene_deuda()

def secuencia_evidencia(periodoppp, inscripcion, campo=None):
    if not SecuenciaEvidenciaSalud.objects.filter(periodoppp=periodoppp, inscripcion=inscripcion).exists():
        qsbasesecuencial = SecuenciaEvidenciaSalud.objects.create(periodoppp=periodoppp, inscripcion=inscripcion)
    else:
        qsbasesecuencial = SecuenciaEvidenciaSalud.objects.filter(periodoppp=periodoppp, inscripcion=inscripcion).first()
    secuencial_ = model_to_dict(qsbasesecuencial)[campo]
    if secuencial_ > 0:
        secuencial_ += 1
    else:
        secuencial_ = 1
    if campo == 'secuenciainforme':
        SecuenciaEvidenciaSalud.objects.filter(periodoppp=periodoppp, inscripcion=inscripcion).update(secuenciainforme=secuencial_)
    elif campo == 'secuenciaejemplo':
        SecuenciaEvidenciaSalud.objects.filter(periodoppp=periodoppp, inscripcion=inscripcion).update(secuenciaejemplo=secuencial_)
    return secuencial_

def tiene_certificacion_segunda_lengua_sin_aprobar_director_carrera(id_inscripcion):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    IDIOMAS = [2, 5] # INGLES, FRANCES
    if id_inscripcion in variable_valor('EXCLUIR_REQUISITO_INGLES'):
        return True
    return CertificadoIdioma.objects.values("id").filter(status=True, persona=eInscripcion.persona, idioma_id__in=IDIOMAS).exists()


def tiene_certificacion_segunda_lengua_aprobado_director_carrera(id_inscripcion):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    IDIOMAS = [1, 5, 8]  # INGLES, FRANCES, QUICHUA
    if id_inscripcion in variable_valor('EXCLUIR_REQUISITO_INGLES'):
        return True
    eCertificadoIdioma = CertificadoIdioma.objects.filter(status=True, persona=eInscripcion.persona, idioma_id__in=IDIOMAS)
    if not eCertificadoIdioma.values("id").exists():
        return False
    eHistorialCertificacionPersona = HistorialCertificacionPersona.objects.filter(certificado_id__in=eCertificadoIdioma, status=True, perfilusuario__inscripcion=eInscripcion)
    if not eHistorialCertificacionPersona.values("id").exists():
        return False
    eHistorialCertificacionPersona = eHistorialCertificacionPersona.order_by('pk').last()
    return eHistorialCertificacionPersona.estado == 1

def tener_certificado_inglesb2(id_inscripcion):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    IDIOMAS = [1, 5, 8]  # INGLES, FRANCES, QUICHUA
    if id_inscripcion in variable_valor('EXCLUIR_REQUISITO_INGLES'):
        return True
    eCertificadoIdioma = CertificadoIdioma.objects.filter(status=True, persona=eInscripcion.persona, idioma_id__in=IDIOMAS)
    if not eCertificadoIdioma.values("id").exists():
        return False
    eHistorialCertificacionPersona = HistorialCertificacionPersona.objects.filter(certificado_id__in=eCertificadoIdioma, status=True, perfilusuario__inscripcion=eInscripcion)
    if not eHistorialCertificacionPersona.values("id").exists():
        return False
    eHistorialCertificacionPersona = eHistorialCertificacionPersona.order_by('pk').last()
    return eHistorialCertificacionPersona.estado == 1


def crear_editar_calendario_actividades_pregrado(eMateria):
    # print(u"****************************************************************************************************")
    # print(f"Inicia proceso de crear calendario de actividades de estudiantes a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} de la materia: {eMateria}")
    urlMoodleBase = f"https://aulagrado.unemi.edu.ec"
    if DEBUG:
        urlMoodleBase = f"http://127.0.0.1"
    eProfesor = eMateria.profesor_principal()
    eAsignados = eMateria.materiaasignada_set.select_related().filter(status=True)
    for eSilabo in eMateria.silabo_set.filter(profesor=eProfesor, status=True):
        # print(f"#SILABO: {eSilabo}")
        eAprobarSilabo = eMateria.tiene_silabo_aprobado(eProfesor.id)
        tieneAprobadoSilabo = True if eSilabo.codigoqr else True if eAprobarSilabo else False
        if tieneAprobadoSilabo:
            # TEST
            eTestSilaboSemanales = TestSilaboSemanal.objects.filter(Q(estado_id=4) | Q(estado__migramoodle=True))
            for eCalendario in CalendarioRecursoActividad.objects.filter(materia=eMateria, tipo=1):
                if not eCalendario.content_object.pk in eTestSilaboSemanales.values_list("id", flat=True):
                    eCalendario.delete()
            for eCalendarioAsignado in CalendarioRecursoActividadAlumno.objects.filter(recurso__materia=eMateria, recurso__tipo=1):
                if not eCalendarioAsignado.materiaasignada.id in eAsignados.values_list("id", flat=True):
                    eCalendarioAsignado.delete()

            ########################################################################################################
            # EXPOSICIÓN
            eExposicionSilaboSemanales = TareaSilaboSemanal.objects.filter(Q(estado_id=4) | Q(estado__migramoodle=True), actividad_id=2)
            for eCalendario in CalendarioRecursoActividad.objects.filter(materia=eMateria, tipo=2):
                if not eCalendario.content_object.pk in eExposicionSilaboSemanales.values_list("id", flat=True):
                    eCalendario.delete()
            for eCalendarioAsignado in CalendarioRecursoActividadAlumno.objects.filter(recurso__materia=eMateria, recurso__tipo=2):
                if not eCalendarioAsignado.materiaasignada.id in eAsignados.values_list("id", flat=True):
                    eCalendarioAsignado.delete()

            ########################################################################################################
            # TALLER
            eTalleresSilaboSemanales = TareaSilaboSemanal.objects.filter(Q(estado_id=4) | Q(estado__migramoodle=True), actividad_id=3)
            for eCalendario in CalendarioRecursoActividad.objects.filter(materia=eMateria, tipo=3):
                if not eCalendario.content_object.pk in eTalleresSilaboSemanales.values_list("id", flat=True):
                    eCalendario.delete()
            for eCalendarioAsignado in CalendarioRecursoActividadAlumno.objects.filter(recurso__materia=eMateria, recurso__tipo=3):
                if not eCalendarioAsignado.materiaasignada.id in eAsignados.values_list("id", flat=True):
                    eCalendarioAsignado.delete()

            ########################################################################################################
            # TAREAS
            eTareaSilaboSemanales = TareaSilaboSemanal.objects.filter(Q(estado_id=4) | Q(estado__migramoodle=True), actividad_id=5)
            for eCalendario in CalendarioRecursoActividad.objects.filter(materia=eMateria, tipo=4):
                if not eCalendario.content_object.pk in eTareaSilaboSemanales.values_list("id", flat=True):
                    eCalendario.delete()
            for eCalendarioAsignado in CalendarioRecursoActividadAlumno.objects.filter(recurso__materia=eMateria, recurso__tipo=4):
                if not eCalendarioAsignado.materiaasignada.id in eAsignados.values_list("id", flat=True):
                    eCalendarioAsignado.delete()

            ########################################################################################################
            # TRABAJO DE INVESTIGACIÓN
            eTrabajosSilaboSemanales = TareaSilaboSemanal.objects.filter(Q(estado_id=4) | Q(estado__migramoodle=True), actividad_id=7)
            for eCalendario in CalendarioRecursoActividad.objects.filter(materia=eMateria, tipo=5):
                if not eCalendario.content_object.pk in eTrabajosSilaboSemanales.values_list("id", flat=True):
                    eCalendario.delete()
            for eCalendarioAsignado in CalendarioRecursoActividadAlumno.objects.filter(recurso__materia=eMateria, recurso__tipo=5):
                if not eCalendarioAsignado.materiaasignada.id in eAsignados.values_list("id", flat=True):
                    eCalendarioAsignado.delete()

            ########################################################################################################
            # ANÁLISIS DE CASOS
            eAnalisisSilaboSemanales = TareaSilaboSemanal.objects.filter(Q(estado_id=4) | Q(estado__migramoodle=True), actividad_id=8)
            for eCalendario in CalendarioRecursoActividad.objects.filter(materia=eMateria, tipo=6):
                if not eCalendario.content_object.pk in eAnalisisSilaboSemanales.values_list("id", flat=True):
                    eCalendario.delete()
            for eCalendarioAsignado in CalendarioRecursoActividadAlumno.objects.filter(recurso__materia=eMateria, recurso__tipo=6):
                if not eCalendarioAsignado.materiaasignada.id in eAsignados.values_list("id", flat=True):
                    eCalendarioAsignado.delete()

            ########################################################################################################
            # FOROS
            eForosSilaboSemanales = ForoSilaboSemanal.objects.filter(Q(estado_id=4) | Q(estado__migramoodle=True))
            for eCalendario in CalendarioRecursoActividad.objects.filter(materia=eMateria, tipo=7):
                if not eCalendario.content_object.pk in eForosSilaboSemanales.values_list("id", flat=True):
                    eCalendario.delete()
            for eCalendarioAsignado in CalendarioRecursoActividadAlumno.objects.filter(recurso__materia=eMateria, recurso__tipo=7):
                if not eCalendarioAsignado.materiaasignada.id in eAsignados.values_list("id", flat=True):
                    eCalendarioAsignado.delete()

            ########################################################################################################
            # TRABAJOS PRACTICOS EXPERIMENTAL
            ePracticasSilaboSemanales = TareaPracticaSilaboSemanal.objects.filter(Q(estado_id=4) | Q(estado__migramoodle=True))
            for eCalendario in CalendarioRecursoActividad.objects.filter(materia=eMateria, tipo=8):
                if not eCalendario.content_object.pk in ePracticasSilaboSemanales.values_list("id", flat=True):
                    eCalendario.delete()
            for eCalendarioAsignado in CalendarioRecursoActividadAlumno.objects.filter(recurso__materia=eMateria, recurso__tipo=8):
                if not eCalendarioAsignado.materiaasignada.id in eAsignados.values_list("id", flat=True):
                    eCalendarioAsignado.delete()

            eSilaboSemanales = eSilabo.silabosemanal_set.filter(status=True)
            for eSilaboSemanal in eSilaboSemanales.order_by('semana'):
                # print(f"#Semana: {eSilaboSemanal.numsemana}")
                # TEST
                for eTestSilaboSemanal in eTestSilaboSemanales.filter(silabosemanal=eSilaboSemanal):
                    # print(f"{eTestSilaboSemanal.nombre_actividad()}")
                    urlMoodle = f"{urlMoodleBase}/mod/quiz/view.php?id={eTestSilaboSemanal.idtestmoodle}"
                    fechadesde = eTestSilaboSemanal.fechadesde
                    horadesde = eTestSilaboSemanal.horadesde
                    fechahasta = eTestSilaboSemanal.fechahasta
                    horahasta = eTestSilaboSemanal.horahasta

                    if horadesde is None:
                        fechahoradesde = datetime(fechadesde.year, fechadesde.month, fechadesde.day, 0, 0, 0)
                    else:
                        fechahoradesde = datetime(fechadesde.year, fechadesde.month, fechadesde.day, horadesde.hour, horadesde.minute)
                    if horahasta is None:
                        fechahorahasta = datetime(fechahasta.year, fechahasta.month, fechahasta.day, 23, 59, 59)
                    else:
                        fechahorahasta = datetime(fechahasta.year, fechahasta.month, fechahasta.day, horahasta.hour, horahasta.minute)
                    if CalendarioRecursoActividad.objects.filter(materia=eMateria, content_type=ContentType.objects.get_for_model(eTestSilaboSemanal), object_id=eTestSilaboSemanal.id, tipo=1).exists():
                        eCalendarioRecursoActividad = CalendarioRecursoActividad.objects.filter(materia=eMateria, content_type=ContentType.objects.get_for_model(eTestSilaboSemanal), object_id=eTestSilaboSemanal.id, tipo=1)[0]
                        if (eCalendarioRecursoActividad.fechahoradesde != fechahoradesde) or (eCalendarioRecursoActividad.fechahorahasta != fechahorahasta):
                            eCalendarioRecursoActividad.fechahoradesde = fechahoradesde
                            eCalendarioRecursoActividad.fechahorahasta = fechahorahasta
                            eCalendarioRecursoActividad.cambio = True
                            eCalendarioRecursoActividad.save()
                    else:
                        eCalendarioRecursoActividad = CalendarioRecursoActividad(materia=eMateria,
                                                                                 content_type=ContentType.objects.get_for_model(eTestSilaboSemanal),
                                                                                 object_id=eTestSilaboSemanal.id,
                                                                                 tipo=1,
                                                                                 url=urlMoodle,
                                                                                 fechahoradesde=fechahoradesde,
                                                                                 fechahorahasta=fechahorahasta)
                        eCalendarioRecursoActividad.save()
                    for eMateriaAsignada in eAsignados:
                        if not CalendarioRecursoActividadAlumno.objects.filter(recurso=eCalendarioRecursoActividad, materiaasignada=eMateriaAsignada).exists():
                            eCalendarioRecursoActividadAlumno = CalendarioRecursoActividadAlumno(recurso=eCalendarioRecursoActividad,
                                                                                                 materiaasignada=eMateriaAsignada)
                            eCalendarioRecursoActividadAlumno.save()

                # EXPOSICIÓN
                for eTareaSilaboSemanal in eExposicionSilaboSemanales.filter(silabosemanal=eSilaboSemanal):
                    # print(f"{eTareaSilaboSemanal.nombre_actividad()}")
                    urlMoodle = f"{urlMoodleBase}/mod/assign/view.php?id={eTareaSilaboSemanal.idtareamoodle}"
                    if CalendarioRecursoActividad.objects.filter(materia=eMateria, content_type=ContentType.objects.get_for_model(eTareaSilaboSemanal), object_id=eTareaSilaboSemanal.id, tipo=2).exists():
                        eCalendarioRecursoActividad = CalendarioRecursoActividad.objects.filter(materia=eMateria, content_type=ContentType.objects.get_for_model(eTareaSilaboSemanal), object_id=eTareaSilaboSemanal.id, tipo=2)[0]
                        if (eCalendarioRecursoActividad.fechahoradesde != eTareaSilaboSemanal.fechadesde) or (eCalendarioRecursoActividad.fechahorahasta != eTareaSilaboSemanal.fechahasta):
                            eCalendarioRecursoActividad.fechahoradesde = eTareaSilaboSemanal.fechadesde
                            eCalendarioRecursoActividad.fechahorahasta = eTareaSilaboSemanal.fechahasta
                            eCalendarioRecursoActividad.cambio = True
                            eCalendarioRecursoActividad.save()
                    else:
                        eCalendarioRecursoActividad = CalendarioRecursoActividad(materia=eMateria,
                                                                                 content_type=ContentType.objects.get_for_model(eTareaSilaboSemanal),
                                                                                 object_id=eTareaSilaboSemanal.id,
                                                                                 tipo=2,
                                                                                 url=urlMoodle,
                                                                                 fechahoradesde=eTareaSilaboSemanal.fechadesde,
                                                                                 fechahorahasta=eTareaSilaboSemanal.fechahasta)
                        eCalendarioRecursoActividad.save()
                    for eMateriaAsignada in eAsignados:
                        if not CalendarioRecursoActividadAlumno.objects.filter(recurso=eCalendarioRecursoActividad, materiaasignada=eMateriaAsignada).exists():
                            eCalendarioRecursoActividadAlumno = CalendarioRecursoActividadAlumno(recurso=eCalendarioRecursoActividad,
                                                                                                 materiaasignada=eMateriaAsignada)
                            eCalendarioRecursoActividadAlumno.save()

                # TALLER
                for eTareaSilaboSemanal in eTalleresSilaboSemanales.filter(silabosemanal=eSilaboSemanal):
                    # print(f"{eTareaSilaboSemanal.nombre_actividad()}")
                    urlMoodle = f"{urlMoodleBase}/mod/assign/view.php?id={eTareaSilaboSemanal.idtareamoodle}"
                    if CalendarioRecursoActividad.objects.filter(materia=eMateria, content_type=ContentType.objects.get_for_model(eTareaSilaboSemanal), object_id=eTareaSilaboSemanal.id, tipo=3).exists():
                        eCalendarioRecursoActividad = CalendarioRecursoActividad.objects.filter(materia=eMateria, content_type=ContentType.objects.get_for_model(eTareaSilaboSemanal), object_id=eTareaSilaboSemanal.id, tipo=3)[0]
                        if (eCalendarioRecursoActividad.fechahoradesde != eTareaSilaboSemanal.fechadesde) or (eCalendarioRecursoActividad.fechahorahasta != eTareaSilaboSemanal.fechahasta):
                            eCalendarioRecursoActividad.fechahoradesde = eTareaSilaboSemanal.fechadesde
                            eCalendarioRecursoActividad.fechahorahasta = eTareaSilaboSemanal.fechahasta
                            eCalendarioRecursoActividad.cambio = True
                            eCalendarioRecursoActividad.save()
                    else:
                        eCalendarioRecursoActividad = CalendarioRecursoActividad(materia=eMateria,
                                                                                 content_type=ContentType.objects.get_for_model(eTareaSilaboSemanal),
                                                                                 object_id=eTareaSilaboSemanal.id,
                                                                                 tipo=3,
                                                                                 url=urlMoodle,
                                                                                 fechahoradesde=eTareaSilaboSemanal.fechadesde,
                                                                                 fechahorahasta=eTareaSilaboSemanal.fechahasta)
                        eCalendarioRecursoActividad.save()
                    for eMateriaAsignada in eAsignados:
                        if not CalendarioRecursoActividadAlumno.objects.filter(recurso=eCalendarioRecursoActividad, materiaasignada=eMateriaAsignada).exists():
                            eCalendarioRecursoActividadAlumno = CalendarioRecursoActividadAlumno(recurso=eCalendarioRecursoActividad,
                                                                                                 materiaasignada=eMateriaAsignada)
                            eCalendarioRecursoActividadAlumno.save()

                # TAREAS
                for eTareaSilaboSemanal in eTareaSilaboSemanales.filter(silabosemanal=eSilaboSemanal):
                    # print(f"{eTareaSilaboSemanal.nombre_actividad()}")
                    urlMoodle = f"{urlMoodleBase}/mod/assign/view.php?id={eTareaSilaboSemanal.idtareamoodle}"
                    if CalendarioRecursoActividad.objects.filter(materia=eMateria, content_type=ContentType.objects.get_for_model(eTareaSilaboSemanal), object_id=eTareaSilaboSemanal.id, tipo=4).exists():
                        eCalendarioRecursoActividad = CalendarioRecursoActividad.objects.filter(materia=eMateria, content_type=ContentType.objects.get_for_model(eTareaSilaboSemanal), object_id=eTareaSilaboSemanal.id, tipo=4)[0]
                        if (eCalendarioRecursoActividad.fechahoradesde != eTareaSilaboSemanal.fechadesde) or (eCalendarioRecursoActividad.fechahorahasta != eTareaSilaboSemanal.fechahasta):
                            eCalendarioRecursoActividad.fechahoradesde = eTareaSilaboSemanal.fechadesde
                            eCalendarioRecursoActividad.fechahorahasta = eTareaSilaboSemanal.fechahasta
                            eCalendarioRecursoActividad.cambio = True
                            eCalendarioRecursoActividad.save()
                    else:
                        eCalendarioRecursoActividad = CalendarioRecursoActividad(materia=eMateria,
                                                                                 content_type=ContentType.objects.get_for_model(eTareaSilaboSemanal),
                                                                                 object_id=eTareaSilaboSemanal.id,
                                                                                 tipo=4,
                                                                                 url=urlMoodle,
                                                                                 fechahoradesde=eTareaSilaboSemanal.fechadesde,
                                                                                 fechahorahasta=eTareaSilaboSemanal.fechahasta)
                        eCalendarioRecursoActividad.save()
                    for eMateriaAsignada in eAsignados:
                        if not CalendarioRecursoActividadAlumno.objects.filter(recurso=eCalendarioRecursoActividad, materiaasignada=eMateriaAsignada).exists():
                            eCalendarioRecursoActividadAlumno = CalendarioRecursoActividadAlumno(recurso=eCalendarioRecursoActividad,
                                                                                                 materiaasignada=eMateriaAsignada)
                            eCalendarioRecursoActividadAlumno.save()

                # TRABAJO DE INVESTIGACIÓN
                for eTareaSilaboSemanal in eTrabajosSilaboSemanales.filter(silabosemanal=eSilaboSemanal):
                    # print(f"{eTareaSilaboSemanal.nombre_actividad()}")
                    urlMoodle = f"{urlMoodleBase}/mod/assign/view.php?id={eTareaSilaboSemanal.idtareamoodle}"
                    if CalendarioRecursoActividad.objects.filter(materia=eMateria, content_type=ContentType.objects.get_for_model(eTareaSilaboSemanal), object_id=eTareaSilaboSemanal.id, tipo=5).exists():
                        eCalendarioRecursoActividad = CalendarioRecursoActividad.objects.filter(materia=eMateria, content_type=ContentType.objects.get_for_model(eTareaSilaboSemanal), object_id=eTareaSilaboSemanal.id, tipo=5)[0]
                        if (eCalendarioRecursoActividad.fechahoradesde != eTareaSilaboSemanal.fechadesde) or (eCalendarioRecursoActividad.fechahorahasta != eTareaSilaboSemanal.fechahasta):
                            eCalendarioRecursoActividad.fechahoradesde = eTareaSilaboSemanal.fechadesde
                            eCalendarioRecursoActividad.fechahorahasta = eTareaSilaboSemanal.fechahasta
                            eCalendarioRecursoActividad.cambio = True
                            eCalendarioRecursoActividad.save()
                    else:
                        eCalendarioRecursoActividad = CalendarioRecursoActividad(materia=eMateria,
                                                                                 content_type=ContentType.objects.get_for_model(eTareaSilaboSemanal),
                                                                                 object_id=eTareaSilaboSemanal.id,
                                                                                 tipo=5,
                                                                                 url=urlMoodle,
                                                                                 fechahoradesde=eTareaSilaboSemanal.fechadesde,
                                                                                 fechahorahasta=eTareaSilaboSemanal.fechahasta)
                        eCalendarioRecursoActividad.save()
                    for eMateriaAsignada in eAsignados:
                        if not CalendarioRecursoActividadAlumno.objects.filter(recurso=eCalendarioRecursoActividad, materiaasignada=eMateriaAsignada).exists():
                            eCalendarioRecursoActividadAlumno = CalendarioRecursoActividadAlumno(recurso=eCalendarioRecursoActividad,
                                                                                                 materiaasignada=eMateriaAsignada)
                            eCalendarioRecursoActividadAlumno.save()

                # ANALISIS DE CASOS
                for eTareaSilaboSemanal in eAnalisisSilaboSemanales.filter(silabosemanal=eSilaboSemanal):
                    # print(f"{eTareaSilaboSemanal.nombre_actividad()}")
                    urlMoodle = f"{urlMoodleBase}/mod/assign/view.php?id={eTareaSilaboSemanal.idtareamoodle}"
                    if CalendarioRecursoActividad.objects.filter(materia=eMateria, content_type=ContentType.objects.get_for_model(eTareaSilaboSemanal), object_id=eTareaSilaboSemanal.id, tipo=6).exists():
                        eCalendarioRecursoActividad = CalendarioRecursoActividad.objects.filter(materia=eMateria, content_type=ContentType.objects.get_for_model(eTareaSilaboSemanal), object_id=eTareaSilaboSemanal.id, tipo=6)[0]
                        if (eCalendarioRecursoActividad.fechahoradesde != eTareaSilaboSemanal.fechadesde) or (eCalendarioRecursoActividad.fechahorahasta != eTareaSilaboSemanal.fechahasta):
                            eCalendarioRecursoActividad.fechahoradesde = eTareaSilaboSemanal.fechadesde
                            eCalendarioRecursoActividad.fechahorahasta = eTareaSilaboSemanal.fechahasta
                            eCalendarioRecursoActividad.cambio = True
                            eCalendarioRecursoActividad.save()
                    else:
                        eCalendarioRecursoActividad = CalendarioRecursoActividad(materia=eMateria,
                                                                                 content_type=ContentType.objects.get_for_model(eTareaSilaboSemanal),
                                                                                 object_id=eTareaSilaboSemanal.id,
                                                                                 tipo=6,
                                                                                 url=urlMoodle,
                                                                                 fechahoradesde=eTareaSilaboSemanal.fechadesde,
                                                                                 fechahorahasta=eTareaSilaboSemanal.fechahasta)
                        eCalendarioRecursoActividad.save()
                    for eMateriaAsignada in eAsignados:
                        if not CalendarioRecursoActividadAlumno.objects.filter(recurso=eCalendarioRecursoActividad, materiaasignada=eMateriaAsignada).exists():
                            eCalendarioRecursoActividadAlumno = CalendarioRecursoActividadAlumno(recurso=eCalendarioRecursoActividad,
                                                                                                 materiaasignada=eMateriaAsignada)
                            eCalendarioRecursoActividadAlumno.save()

                # FOROS
                for eForoSilaboSemanal in eForosSilaboSemanales.filter(silabosemanal=eSilaboSemanal):
                    # print(f"{eForoSilaboSemanal.nombre_actividad()}")
                    urlMoodle = f"{urlMoodleBase}/mod/url/view.php?id={eForoSilaboSemanal.idforomoodle}"
                    if CalendarioRecursoActividad.objects.filter(materia=eMateria, content_type=ContentType.objects.get_for_model(eForoSilaboSemanal), object_id=eForoSilaboSemanal.id, tipo=7).exists():
                        eCalendarioRecursoActividad = CalendarioRecursoActividad.objects.filter(materia=eMateria, content_type=ContentType.objects.get_for_model(eForoSilaboSemanal), object_id=eForoSilaboSemanal.id, tipo=7)[0]
                        if (eCalendarioRecursoActividad.fechahoradesde != eForoSilaboSemanal.fechadesde) or (eCalendarioRecursoActividad.fechahorahasta != eForoSilaboSemanal.fechahasta):
                            eCalendarioRecursoActividad.fechahoradesde = eForoSilaboSemanal.fechadesde
                            eCalendarioRecursoActividad.fechahorahasta = eForoSilaboSemanal.fechahasta
                            eCalendarioRecursoActividad.cambio = True
                            eCalendarioRecursoActividad.save()
                    else:
                        eCalendarioRecursoActividad = CalendarioRecursoActividad(materia=eMateria,
                                                                                 content_type=ContentType.objects.get_for_model(eForoSilaboSemanal),
                                                                                 object_id=eForoSilaboSemanal.id,
                                                                                 tipo=7,
                                                                                 url=urlMoodle,
                                                                                 fechahoradesde=eForoSilaboSemanal.fechadesde,
                                                                                 fechahorahasta=eForoSilaboSemanal.fechahasta)
                        eCalendarioRecursoActividad.save()
                    for eMateriaAsignada in eAsignados:
                        if not CalendarioRecursoActividadAlumno.objects.filter(recurso=eCalendarioRecursoActividad, materiaasignada=eMateriaAsignada).exists():
                            eCalendarioRecursoActividadAlumno = CalendarioRecursoActividadAlumno(recurso=eCalendarioRecursoActividad,
                                                                                                 materiaasignada=eMateriaAsignada)
                            eCalendarioRecursoActividadAlumno.save()

                # TRABAJO PRÁCTICO EXPERIMENTAL
                for eTareaPracticaSilaboSemanal in ePracticasSilaboSemanales.filter(silabosemanal=eSilaboSemanal):
                    # print(f"{eTareaPracticaSilaboSemanal.nombre_actividad()}")
                    urlMoodle = f"{urlMoodleBase}/mod/assign/view.php?id={eTareaPracticaSilaboSemanal.idtareapracticamoodle}"
                    if CalendarioRecursoActividad.objects.filter(materia=eMateria, content_type=ContentType.objects.get_for_model(eTareaPracticaSilaboSemanal), object_id=eTareaPracticaSilaboSemanal.id, tipo=8).exists():
                        eCalendarioRecursoActividad = CalendarioRecursoActividad.objects.filter(materia=eMateria, content_type=ContentType.objects.get_for_model(eTareaPracticaSilaboSemanal), object_id=eTareaPracticaSilaboSemanal.id, tipo=8)[0]
                        if (eCalendarioRecursoActividad.fechahoradesde != eTareaPracticaSilaboSemanal.fechadesde) or (eCalendarioRecursoActividad.fechahorahasta != eTareaPracticaSilaboSemanal.fechahasta):
                            eCalendarioRecursoActividad.fechahoradesde = eTareaPracticaSilaboSemanal.fechadesde
                            eCalendarioRecursoActividad.fechahorahasta = eTareaPracticaSilaboSemanal.fechahasta
                            eCalendarioRecursoActividad.cambio = True
                            eCalendarioRecursoActividad.save()
                    else:
                        eCalendarioRecursoActividad = CalendarioRecursoActividad(materia=eMateria,
                                                                                 content_type=ContentType.objects.get_for_model(eTareaPracticaSilaboSemanal),
                                                                                 object_id=eTareaPracticaSilaboSemanal.id,
                                                                                 tipo=8,
                                                                                 url=urlMoodle,
                                                                                 fechahoradesde=eTareaPracticaSilaboSemanal.fechadesde,
                                                                                 fechahorahasta=eTareaPracticaSilaboSemanal.fechahasta)
                        eCalendarioRecursoActividad.save()
                    for eMateriaAsignada in eAsignados:
                        if not CalendarioRecursoActividadAlumno.objects.filter(recurso=eCalendarioRecursoActividad, materiaasignada=eMateriaAsignada).exists():
                            eCalendarioRecursoActividadAlumno = CalendarioRecursoActividadAlumno(recurso=eCalendarioRecursoActividad,
                                                                                                 materiaasignada=eMateriaAsignada)
                            eCalendarioRecursoActividadAlumno.save()

        #
        # print(u"****************************************************************************************************")
        # print(u"****************************************************************************************************")
        # print(f"** Finaliza proceso de crear actividades de estudiantes del materia: {eMateria}")


class ProcesoBackGroundCrearEditarCalendarioActividadesPregradoEstudiante(threading.Thread):

    def __init__(self, eMateria):
        self.eMateria = eMateria
        threading.Thread.__init__(self)

    def run(self):
        eMateria = self.eMateria
        crear_editar_calendario_actividades_pregrado(eMateria)


class MasivoProcesoBackGroundCrearEditarCalendarioActividadesPregradoEstudiante(threading.Thread):

    def __init__(self, eMaterias):
        self.eMaterias = eMaterias
        threading.Thread.__init__(self)

    def run(self):
        eMaterias = self.eMaterias
        for eMateria in eMaterias:
            crear_editar_calendario_actividades_pregrado(eMateria)

def materias_abiertas_salud(id, ida, idam, nivel, paralelo=None, alumno=False, secretaria=False):
    try:
        validarcupos = False # IMSM
        asignatura = Asignatura.objects.get(pk=ida)
        asigmalla = None
        if idam:
            asigmalla = AsignaturaMalla.objects.get(pk=idam)
        inscripcion = Inscripcion.objects.get(pk=id)
        # IMSM
        puede_seleccionar = True
        nivelmallaaux = AsignaturaMalla.objects.filter(asignatura=asignatura, malla=inscripcion.mi_malla(), status=True)
        nivelmalla = None
        if nivelmallaaux:
            nivelmalla = nivelmallaaux[0].nivelmalla
        estado = inscripcion.estado_asignatura(asignatura)

        hoy = datetime.now().date()
        minivelmalla = inscripcion.mi_nivel().nivel
        nivel = Nivel.objects.get(pk=nivel)
        if alumno:
            materiasabiertas = Materia.objects.filter(Q(asignatura=asignatura, inicio__gte=hoy, nivel__cerrado=False, nivel__periodo=nivel.periodo), status=True).order_by('id')
            if nivelmallaaux:
                materiasabiertas = materiasabiertas.filter(asignaturamalla__malla=inscripcion.mi_malla()).distinct().order_by('id')
        else:
            materiasabiertas = Materia.objects.filter(Q(asignatura=asignatura,  nivel__cerrado=False, nivel__periodo=nivel.periodo, carrerascomunes__id__in=[inscripcion.carrera.id]) | Q(asignatura=asignatura, nivel__cerrado=False, nivel__periodo=nivel.periodo, carrerascomunes__isnull=True), paralelo=paralelo, status=True).distinct().order_by('id')
        if paralelo:
            materiasabiertas = materiasabiertas.filter(paralelo=paralelo)
        materias = {}
        # VALIDA SI NO TIENE HORARIO SOLO PARA PRESENTAR EL MENSAJE Q DEBE TENER HORARIO
        mensajenotienehorario = True
        tipo_materia = 2
        for materia in materiasabiertas:
            if materia.nivel.nivellibrecoordinacion_set.exists():
                origen = materia.nivel.nivellibrecoordinacion_set.all()[0].coordinacion.alias
            else:
                origen = materia.nivel.carrera.nombre
            mat = {}
            paralelo = materia.paralelo
            novalidar_horario_cupo_materiavirtual = True
            # if materia.tipomateria == 2:
            #     novalidar_horario_cupo_materiavirtual = True
            #SECRETARIA PUEDE MATRICULAR CON CUPOS ADICIONAL

            if validarcupos:# IMSM
                tiene_cupos_adicional = False
                if not materia.capacidad_disponible() > 0 and materia.cupos_restante_adicional() > 0 and secretaria:
                    tiene_cupos_adicional = True
            else:# IMSM
                tiene_cupos_adicional = True # IMSM

            # HABILITAR LA LINEA SIGUIENTE PARA EL PROXIMO PERIODO: IMSM
            if materia.capacidad_disponible() > 0 or HOMITIRCAPACIDADHORARIO or tiene_cupos_adicional:
                horariosmateria= materia.clases_informacion_teoria_practica()
                matricular_facs = True
                #SI TIENE HORARIO Y TIPO MATERIA ES 1(PRESENCIAL) PRESENTA PARA LA MATRICULACION, CASO CONTRARIO ES TIPO MATERIA 2 PRESENTA SI NO TIENE HORARIO
                if horariosmateria or matricular_facs:
                    mensajenotienehorario = False
                    mat[materia.id] = {'nivel': to_unicode(materia.nivel.nivelmalla.nombre) if materia.nivel.nivelmalla else "",
                                       # 'idnivel': to_unicode(materia.asignaturamalla.nivelmalla.id) if materia.asignaturamalla.nivelmalla else "",
                                       'sede': to_unicode(materia.nivel.sede.nombre) if materia.nivel.sede else "",
                                       'profesor': (materia.profesor_principal().persona.nombre_completo()) if materia.profesor_principal() else 'SIN DEFINIR',
                                       'horario': "<br>".join(x for x in horariosmateria),
                                       'id': materia.id,
                                       'tipomateria': materia.tipomateria,
                                       'teopract': 2 if materia.asignaturamalla.practicas else 1,
                                       'inicio': materia.inicio.strftime("%d-%m-%Y"),
                                       'session': to_unicode(materia.nivel.sesion.nombre),
                                       'fin': materia.fin.strftime("%d-%m-%Y"), 'identificacion': materia.identificacion,
                                       'coordcarrera': origen,
                                       'paralelo': paralelo,
                                       'cupo': materia.cupo if novalidar_horario_cupo_materiavirtual else materia.capacidad_disponible(),
                                       'matriculados': materia.cantidad_matriculas_materia(),
                                       'novalhorcup': not variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL'),
                                       'carrera': to_unicode(materia.asignaturamalla.malla.carrera.nombre) if materia.asignaturamalla.malla.carrera.nombre else "",
                                       'cupoadicional': materia.cupos_restante_adicional()}
                    materias.update(mat)
                else:
                    mensajenotienehorario = True
            tipo_materia=materia.tipomateria
        mensaje = 'NO EXISTEN CUPOS DISPONIBLES O MATERIAS PROGRAMADAS'

        estaabierta = True if materiasabiertas else False

        # IMSM
        if puede_seleccionar is False:
            materias = {}
        # IMSM

        if nivelmallaaux:
            return {"result": "ok", "idd": asignatura.id, "asignatura": unicode(asignatura.nombre)+" "+unicode(nivelmalla), "abiertas": materiasabiertas.__len__(), "disponibles": materias.__len__(), "materias": materias, "notienehorario":mensajenotienehorario, "mensaje":mensaje, "estaabierta" : estaabierta, "puede_seleccionar": puede_seleccionar}
        else:
            return {"result": "ok", "idd": asignatura.id, "asignatura": unicode(asignatura.nombre), "abiertas": materiasabiertas.__len__(), "disponibles": materias.__len__(), "materias": materias, "notienehorario":mensajenotienehorario, "mensaje":mensaje, "estaabierta" : estaabierta, "puede_seleccionar": puede_seleccionar}
    except Exception as ex:
        return {"result": "bad", 'error': unicode(ex)}

def inscripcion_practicas_salud(request, preins, configuracionoferta, turno):
    try:
        # configuracionoferta = ConfiguracionInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['idconfig']))
        # preins = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.POST['idpreins']))
        preins.tipo = 4
        preins.fechadesde = configuracionoferta.fechainicio
        preins.nivelmalla = preins.inscripcion.mi_nivel().nivel
        preins.itinerariomalla = preins.itinerariomalla
        preins.fechahasta = configuracionoferta.fechafin
        # preins.empresaempleadora = configuracionoferta.empresaempleadora
        # preins.otraempresaempleadora = configuracionoferta.otraempresaempleadora
        preins.tutorunemi = configuracionoferta.tutorunemi
        preins.supervisor = configuracionoferta.supervisor
        preins.numerohora = configuracionoferta.numerohora
        preins.tipoinstitucion = configuracionoferta.tipoinstitucion
        preins.sectoreconomico = 5  # servicios
        preins.departamento_id = 41  # FACULTAD CIENCIAS DE LA SALUD (FACS)
        preins.periodoppp = configuracionoferta.periodoppp
        preins.convenio = configuracionoferta.convenio
        preins.lugarpractica = configuracionoferta.lugarpractica
        # preins.acuerdo = configuracionoferta.acuerdo
        preins.save(request)
        observaciondefault = 'Estudiante ha seleccionado lugar de prácticas.'
        if preins.recorrido():
            if not preins.recorrido().estado == 2:
                recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                     fecha=datetime.now().date(),
                                                                     observacion=observaciondefault,
                                                                     estado=2)
            else:
                recorrido = preins.recorrido()
                recorrido.observacion = 'Estudiante ha seleccionado lugar de prácticas.'
            recorrido.save(request)
        else:
            recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                 fecha=datetime.now().date(),
                                                                 observacion=observaciondefault,
                                                                 estado=2)
            recorrido.save(request)
        emailestudiante = preins.inscripcion.persona.lista_emails_envio()
        estudiante = preins.inscripcion.persona.nombre_completo_inverso()

        ################ APROBAR LA PRACTICA ################################################
        practa = PracticasPreprofesionalesInscripcion(preinscripcion=preins,
                                                      inscripcion=preins.inscripcion,
                                                      nivelmalla=preins.nivelmalla,
                                                      itinerariomalla=preins.itinerariomalla if preins.itinerariomalla else None,
                                                      tipo=preins.tipo,
                                                      fechadesde=preins.fechadesde,
                                                      fechahasta=preins.fechahasta,
                                                      tutorunemi=preins.tutorunemi if preins.tutorunemi else None,
                                                      supervisor=preins.supervisor if preins.supervisor else None,
                                                      numerohora=preins.numerohora,
                                                      tiposolicitud=1,
                                                      # acuerdo=preins.acuerdo,
                                                      convenio=preins.convenio,
                                                      lugarpractica=preins.lugarpractica,
                                                      asignacionempresapractica=configuracionoferta.asignacionempresapractica,
                                                      empresaempleadora=preins.empresaempleadora if preins.empresaempleadora else None,
                                                      otraempresaempleadora=preins.otraempresaempleadora,
                                                      tipoinstitucion=preins.tipoinstitucion if preins.tipoinstitucion else None,
                                                      sectoreconomico=preins.sectoreconomico if preins.sectoreconomico else None,
                                                      departamento=preins.departamento if preins.departamento else None,
                                                      periodoppp=preins.periodoppp if preins.periodoppp else None,
                                                      fechaasigtutor=datetime.now().date(),
                                                      observacion=observaciondefault, estadosolicitud=2,
                                                      fechaasigsupervisor=datetime.now().date())
        practa.save(request)
        log(u'El estudiante %s acepto la asignacion de práctica preprofesionales a la empresa: %s' % (
            preins.inscripcion,
            practa.asignacionempresapractica if practa.asignacionempresapractica else practa.otraempresaempleadora),
            request,
            "add")

        # Relaciona datos adicionales para la tabla PracticasPreprofesionalesInscripcion
        practaexten = PracticasPreprofesionalesInscripcionExtensionSalud(practicasppinscripcion=practa, dia=configuracionoferta.dia, configinscppp=configuracionoferta, responsable=configuracionoferta.responsable)
        practaexten.save(request)
        # Almacena historial de inscritos en la oferta
        historialinscripcionoferta = HistorialInscricionOferta(configinscppp=configuracionoferta, practicasppinscripcion=practa, fecha=datetime.now().date())
        historialinscripcionoferta.save(request)
        idturno = turno
        # idturno = int(request.POST.get('idturno', '0'))
        if idturno > 0:
            historialinscripcionoferta.ordenprioridad_id = idturno
        historialinscripcionoferta.save(request)

        if preins.estado == 2:
            if not preins.detallerecoridopreinscripcionpracticaspp_set.filter(status=True).exists():
                recorridoa = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                      fecha=preins.fecha,
                                                                      observacion=u'Asignado',
                                                                      estado=2)
                recorridoa.save(request)
        recorridoa = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                              fecha=datetime.now().date(),
                                                              observacion=u'Acepto la asignacion de práctica preprofesionales',
                                                              estado=5,
                                                              esestudiante=True)
        recorridoa.save(request)
        preins.estado = 2
        preins.save(request)

        # Envío de correo y notificaiones
        if configuracionoferta.tutorunemi:
            idprof = configuracionoferta.tutorunemi.id
            profesor1 = Profesor.objects.get(pk=idprof)
            asunto = u"ASIGNACIÓN TUTOR ACADÉMICO PRÁCTICAS PREPROFESIONALES "
            para = profesor1.persona
            observacion = 'Se le comunica que ha sido designado como tutor académico a (el/la) estudiante: {} de la carrera: {}'.format(
                estudiante, preins.inscripcion.carrera)
            notificacion(asunto, observacion, para, None, '/pro_cronograma?action=listatutorias', preins.pk, 1, 'sga', DetallePreInscripcionPracticasPP, request)
        if configuracionoferta.supervisor:
            idprof = configuracionoferta.supervisor.id
            profesor1 = Profesor.objects.get(pk=idprof)
            asunto = u"ASIGNACIÓN SUPERVISOR ACADÉMICO PRÁCTICAS PREPROFESIONALES "
            para = profesor1.persona
            observacion = 'Se le comunica que ha sido designado como supervisor académico a (el/la) estudiante: {} de la carrera: {}'.format(
                estudiante, preins.inscripcion.carrera)
            notificacion(asunto, observacion, para, None, '/pro_cronograma?action=listasupervision', preins.pk, 1, 'sga', DetallePreInscripcionPracticasPP, request)

        asunto = u"Asignación de cupo para Prácticas Preprofesionales"
        send_html_mail(asunto, "emails/asignacion_cupo_practica.html",
                       {'sistema': request.session['nombresistema'],
                        'estudiante': estudiante}, emailestudiante, [],
                       cuenta=CUENTAS_CORREOS[4][1])
        log(u'Asignó la pre inscripción: %s a la práctica pre profesional: %s' % (preins, preins), request, "asig")

        return True, ''
    except Exception as ex:
        transaction.set_rollback(True)
        return False, f"{str(ex)} Error al guardar los datos."

def matricularSaludCero(request, validartodo, estudiante=False):
    try:
        inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
        persona = inscripcion.persona
        mismaterias = json.loads(request.POST['materias'])
        mispracticas = []
        if not inscripcion.carrera.coordinaciones().values('id').filter(id=9).exists():
            mispracticas = json.loads(request.POST['practicas'])
        periodo = request.session['periodo']
        cobro = request.POST['cobro']
        # regular o irregular
        tipo_matricula_ri = request.POST['tipo_matricula']
        seleccion = []
        for m in mismaterias:
            seleccion.append(int(m))
        materias = Materia.objects.filter(id__in=seleccion, status=True)
        #MATERIAS PRACTICAS
        listaprofemateriaid_singrupo = []
        listaprofemateriaid_congrupo = []
        listagrupoprofesorid = []
        for x in mispracticas:
            if not int(x[1]) > 0:
                listaprofemateriaid_singrupo.append(int(x[0]))
            else:
                listaprofemateriaid_congrupo.append([int(x[0]), int(x[1])])
                listagrupoprofesorid.append(int(x[1]))
        profesoresmateriassingrupo = ProfesorMateria.objects.filter(id__in=listaprofemateriaid_singrupo)
        grupoprofesormateria = GruposProfesorMateria.objects.filter(id__in=listagrupoprofesorid)

        if validartodo:
            # VALIDACION MATERIAS TIENE PRACTICAS PARA LA CARRERA DE ENFERMERIA Y NUTRICION
            if inscripcion.carrera.id in [1, 3]:
                totalpracticas = materias.values('id').filter(asignaturamalla__practicas=True, id__in=profesoresmateriassingrupo.values('materia__id')).count() + materias.values('id').filter(asignaturamalla__practicas=True, id__in=grupoprofesormateria.values('profesormateria__materia__id')).count()
                if not materias.values('id').filter(asignaturamalla__practicas=True).count() == totalpracticas:
                    raise NameError("Falta de seleccionar horario de practicas")

        if validartodo:
            # CONFLICTO DE HORARIO PARA EL ESTUDIANTE
            materiasasistir = []
            for m in materias:
                if not inscripcion.sin_asistencia(m.asignatura):
                    materiasasistir.append(m)
            # conflicto = ""
            # if materiasasistir:
            if not inscripcion.carrera.modalidad == 3 and not inscripcion.carrera.id in [1, 110, 3, 111]:
                conflicto = conflicto_materias_estudiante(materiasasistir, profesoresmateriassingrupo, listaprofemateriaid_congrupo)
                if conflicto:
                    raise NameError(conflicto)

        nivel = Nivel.objects.get(pk=request.POST['nivel'])
        if validartodo:
            # VERIFICANDO CUPO MATERIAS PRACTICAS EN PROFESOR MATERIA CON PÁRALELO
            for grupoprofemat in grupoprofesormateria:
                grupoprofemat.verificar_capacidad_limite_grupoprofesor()
            hoy = datetime.now().date()
            nivel = Nivel.objects.get(pk=request.POST['nivel'])
            # LIMITE DE MATRICULAS EN EL PARALELO
            if not MATRICULACION_LIBRE and nivel.capacidadmatricula <= nivel.matricula_set.values('id').count():
                raise NameError(u"Capacidad matricula limite del paralelo: " + unicode(nivel.paralelo) + ", seleccione otro.")
                # return JsonResponse({"result": "bad", "reload": True, "mensaje": u"Capacidad matricula limite del paralelo: " + unicode(nivel.paralelo) + ", seleccione otro."})
            # habilitar cuando sea matriculacion
            # if estudiante and 'matriculamodulos' not in request.POST:
            #     if nivel.fechatopematriculaex and hoy > nivel.fechatopematriculaex:
            #         return JsonResponse({"result": "bad", "reload": False, "mensaje": u"Fuera del periodo de matriculacion."})
            # habilitar cuando sea matriculacion
            # PERDIDA DE CARRERA POR 4TA MATRICULA
            if inscripcion.tiene_perdida_carrera():
                raise NameError(u"Tiene limite de matriculas.")
            # MATRICULA
            costo_materia_total = 0

        if not inscripcion.matriculado_periodo(nivel.periodo):
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
                if 'fecha_matricula' in request.POST:
                    fecha_matricula=convertir_fecha(request.POST['fecha_matricula'])
                    if datetime.now().date() != fecha_matricula:
                        matricula.fecha=fecha_matricula
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
                        # if inscripcion.itinerario < 1:
                        if materia.asignaturamalla.itinerario > 0:
                            codigoitinerario = int(materia.asignaturamalla.itinerario)
                    if validartodo:
                        if not materia.tiene_cupo_materia():
                            if materia.cupoadicional > 0:
                                if not materia.existen_cupos_con_adicional():
                                    transaction.set_rollback(True)
                                    raise NameError(u"Capacidad limite de la materia: " + unicode(materia.asignatura) + ", seleccione otro.")
                                else:
                                    matriculacupoadicional = True
                            else:
                                transaction.set_rollback(True)
                                raise NameError(u"Capacidad limite de la materia: " + unicode( materia.asignatura) + ", seleccione otro.")

                    matriculas = matricula.inscripcion.historicorecordacademico_set.values('id').filter(asignatura=materia.asignatura, fecha__lt=materia.nivel.fin).count() + 1
                    if inscripcion.carrera.modalidad == 3:
                        materiaasignada = MateriaAsignada(matricula=matricula,
                                                          materia=materia,
                                                          notafinal=0,
                                                          sinasistencia=True,
                                                          asistenciafinal=100,
                                                          cerrado=False,
                                                          matriculas=matriculas,
                                                          observaciones='',
                                                          estado_id=NOTA_ESTADO_EN_CURSO)
                    else:
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
                    #MATRICULA EN LA PRACTICA QUE NO TENGAN GRUPO
                    if profesoresmateriassingrupo.values('id').filter(materia=materia).exists():
                        profemate = profesoresmateriassingrupo.filter(materia=materia)[0]
                        alumnopractica = AlumnosPracticaMateria(materiaasignada= materiaasignada,
                                                                profesormateria= profemate)
                        alumnopractica.save(request)
                        log(u'Materia (%s) con profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profemate, materiaasignada, alumnopractica.id), request, "add")
                    # MATRICULA EN LA PRACTICA QUE SI TENGAN GRUPOS
                    elif grupoprofesormateria.values('id').filter(profesormateria__materia=materia).exists():
                        profemate_congrupo = grupoprofesormateria.filter(profesormateria__materia=materia)[0]

                        if validartodo:
                            profemate_congrupo.verificar_capacidad_limite_grupoprofesor()

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
            with transaction.atomic():
                if int(cobro) > 0:
                    if matricula.inscripcion.mi_coordinacion().id != 9:
                        # matricula.calcular_rubros_matricula(request,int(cobro))
                        matricula.agregacion_aux(request)
                matricula.actualiza_matricula()
                matricula.inscripcion.actualiza_estado_matricula()
                matricula.grupo_socio_economico(tipo_matricula_ri)
                matricula.calcula_nivel()

            if estudiante:
                send_html_mail("Automatricula", "emails/matricula.html", {'sistema': request.session['nombresistema'], 'matricula': matricula, 't': miinstitucion()}, inscripcion.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[5][1])
                log(u'Automatricula estudiante: %s' % matricula, request, "add")
            else:
                send_html_mail("Matricula por secretaria", "emails/matricula.html", {'sistema': request.session['nombresistema'], 'matricula': matricula, 't': miinstitucion()}, inscripcion.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[5][1])
                log(u'Matricula secretaria: %s' % matricula, request, "add")
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
            return JsonResponse({"result": "ok", "valorpagar":valorpagar, "descripcionarancel": descripcionarancel, "valorarancel": valorarancel, "phase": matricula.id})
        else:
            transaction.set_rollback(True)
            raise NameError(u"Ya se encuentra matriculado.")
    except Exception as ex:
        transaction.set_rollback(True)
        import sys
        return JsonResponse({"result": "bad", "reload": False, "mensaje": u"Problemas en la matriculación %s - %s" % (ex, sys.exc_info()[-1].tb_lineno)})

def matricularSalud(request, eMatricula, estudiante=False):
    try:
        from api.views.alumno.addremove_matricula.functions import valida_conflicto_materias_estudiante_enroll
        from sga.models import AgregacionEliminacionMaterias
        eInscripcion = eMatricula.inscripcion
        eMalla = eInscripcion.mi_malla()
        ePersona = eInscripcion.persona
        mis_clases = json.loads(request.POST['materias'])
        lista_materias = []
        eListadoMaterias = Materia.objects.filter(id__in=mis_clases, status=True)
        for eMateria in eListadoMaterias:
            mi_practica = 0
            mi_materia_singrupo = 0
            if eMateria.asignaturamalla.tipomateria_id == TIPO_PROFESOR_PRACTICA:
                if mi_materia_singrupo != mi_practica:
                    mi_materia_singrupo = eMateria.id

            if not eInscripcion.itinerario or eInscripcion.itinerario < 1:
                if eMateria.asignaturamalla.itinerario > 0:
                    eInscripcion.itinerario = int(eMateria.asignaturamalla.itinerario)
                    eInscripcion.save(request)

            if eMateria.asignaturamalla.practicas:
                if mi_practica == 0:
                    raise NameError(u"Materia es TP, seleccione un horario de prácticas.")
            # MATERIAS PRACTICAS
            grupoprofesormaterias = GruposProfesorMateria.objects.filter(pk=mi_practica)
            profesoresmateriassingrupo = ProfesorMateria.objects.filter(materia_id=mi_materia_singrupo, tipoprofesor_id=TIPO_PROFESOR_PRACTICA)

            if eMatricula.inscripcion.existe_en_malla(eMateria.asignatura) and not eMatricula.inscripcion.puede_tomar_materia(eMateria.asignatura):
                raise NameError(u"No puede tomar esta materia por tener precedencias")
            if eMatricula.inscripcion.existe_en_modulos(eMateria.asignatura) and not eMatricula.inscripcion.puede_tomar_materia_modulo(eMateria.asignatura):
                raise NameError(u"No puede tomar esta materia por tener precedencias")
            ePeriodoMatricula = None
            if eMatricula.nivel.periodo.periodomatricula_set.values('id').filter(status=True, tipo=2).exists():
                ePeriodoMatricula = eMatricula.nivel.periodo.periodomatricula_set.filter(status=True, tipo=2)[0]
            # if not ePeriodoMatricula:
            #     raise NameError(u"Periodo académico no existe")
            # if not ePeriodoMatricula.puede_agregar_materia:
            #     raise NameError(u"No se permite agregar materia a la matricula")

            if ePeriodoMatricula and ePeriodoMatricula.valida_conflicto_horario and eInscripcion.carrera.modalidad != 3 and not eInscripcion.carrera.id in [1, 110, 3, 111]:
                conflicto, msg = valida_conflicto_materias_estudiante_enroll(mis_clases)
                if conflicto:
                    raise NameError(msg)
            if ePeriodoMatricula and ePeriodoMatricula.valida_cupo_materia:
                if not eMateria.tiene_capacidad():
                    raise NameError(u"No existe cupo para esta materia.")
                    # VERIFICANDO CUPO MATERIAS PRACTICAS EN PROFESOR MATERIA CON PÁRALELO
                for gpm in grupoprofesormaterias:
                    validar = True
                    if gpm.profesormateria.materia.tipomateria == TIPO_PROFESOR_PRACTICA:
                        validar = variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL')
                    if validar:
                        if not HOMITIRCAPACIDADHORARIO and gpm.cuposdisponiblesgrupoprofesor() <= 0:
                            raise NameError(u"Capacidad limite de la materia en la práctica:  " + str(gpm.profesormateria.materia) + ", seleccione otro.")

            if eMatricula.materiaasignada_set.values('id').filter(materia=eMateria).exists():
                raise NameError(u"Ya se encuentra matriculado en esta materia")

            eMateriaAsignada = MateriaAsignada(matricula=eMatricula,
                                               materia=eMateria,
                                               notafinal=0,
                                               asistenciafinal=0,
                                               cerrado=False,
                                               observaciones='',
                                               estado_id=NOTA_ESTADO_EN_CURSO,
                                               sinasistencia=False,
                                               casoultimamatricula=eMatricula.mi_casoultimamatricula())
            if ePeriodoMatricula:
                if ePeriodoMatricula.periodo.valida_asistencia:
                    if eMalla.modalidad.es_enlinea():
                        eMateriaAsignada.sinasistencia = True
                else:
                    eMateriaAsignada.sinasistencia = True
            eMateriaAsignada.save(request)

            # MATRICULA EN LA PRACTICA QUE NO TENGAN GRUPO
            if profesoresmateriassingrupo.values('id').filter(materia=eMateria).exists():
                profemate = profesoresmateriassingrupo.filter(materia=eMateria)[0]
                alumnopractica = AlumnosPracticaMateria(materiaasignada=eMateriaAsignada,
                                                        profesormateria=profemate)
                alumnopractica.save(request)
                log(u'Materia (%s) con profesor practica (%s) seleccionada matrícula: %s en tabla alumnopractica (%s)' % (eMateria, profemate, eMateriaAsignada, alumnopractica.id), request, "add")
            # MATRICULA EN LA PRACTICA QUE SI TENGAN GRUPOS
            elif grupoprofesormaterias.values('id').filter(profesormateria__materia=eMateria).exists():
                profemate_congrupo = grupoprofesormaterias.filter(profesormateria__materia=eMateria)[0]
                if ePeriodoMatricula and ePeriodoMatricula.valida_cupo_materia:
                    validar = True
                    if profemate_congrupo.profesormateria.materia.tipomateria == 2:
                        validar = variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL')
                    if validar:
                        if not HOMITIRCAPACIDADHORARIO and profemate_congrupo.cuposdisponiblesgrupoprofesor() <= 0:
                            raise NameError(u"Capacidad limite de la materia en la práctica:  " + str(profemate_congrupo.profesormateria.materia) + ", seleccione otro.")

                alumnopractica = AlumnosPracticaMateria(materiaasignada=eMateriaAsignada,
                                                        profesormateria=profemate_congrupo.profesormateria,
                                                        grupoprofesor=profemate_congrupo)
                alumnopractica.save(request)
                log(u'Materia (%s) con grupo profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (eMateria, profemate_congrupo, eMateriaAsignada, alumnopractica.id), request, "add")
            eMateriaAsignada.matriculas = eMateriaAsignada.cantidad_matriculas()
            eMateriaAsignada.asistencias()
            eMateriaAsignada.evaluacion()
            eMateriaAsignada.mis_planificaciones()
            eMateriaAsignada.save(request)
            if eMatricula.nivel.nivelgrado:
                log(u'Adiciono materia: %s' % eMateriaAsignada, request, "add")
            else:
                if datetime.now().date() < eMateria.nivel.fechainicioagregacion:
                    # AGREGACION DE MATERIAS EN MATRICULACION REGULAR SIN REALIZAR PAGOS
                    eMateriaAsignada.save(request)
                    log(u'Adiciono materia: %s' % eMateriaAsignada, request, "add")
                elif eMatricula.nivel.puede_agregar_materia_matricula():
                    # AGREGACION DE MATERIAS EN FECHAS DE AGREGACIONES
                    registro = AgregacionEliminacionMaterias(matricula=eMatricula,
                                                             agregacion=True,
                                                             asignatura=eMateriaAsignada.materia.asignatura,
                                                             responsable=ePersona,
                                                             fecha=datetime.now().date(),
                                                             creditos=eMateriaAsignada.materia.creditos,
                                                             nivelmalla=eMateriaAsignada.materia.nivel.nivelmalla if eMateriaAsignada.materia.nivel.nivelmalla else None,
                                                             matriculas=eMateriaAsignada.matriculas)
                    registro.save(request)
                    log(u'Adiciono materia: %s' % eMateriaAsignada, request, "add")
                else:
                    if not eMateria.asignatura.modulo:
                        raise NameError(u"Materia no permitida")
                    registro = AgregacionEliminacionMaterias(matricula=eMatricula,
                                                             agregacion=True,
                                                             asignatura=eMateriaAsignada.materia.asignatura,
                                                             responsable=ePersona,
                                                             fecha=datetime.now().date(),
                                                             creditos=eMateriaAsignada.materia.creditos,
                                                             nivelmalla=eMateriaAsignada.materia.nivel.nivelmalla if eMateriaAsignada.materia.nivel.nivelmalla else None,
                                                             matriculas=eMateriaAsignada.matriculas)
                    registro.save(request)
                    log(u'Adiciono materia: %s' % eMateriaAsignada, request, "add")
            eMatricula.actualizar_horas_creditos()
            eMatricula.actualiza_matricula()
            eMatricula.inscripcion.actualiza_estado_matricula()
            valid, msg, aData = get_tipo_matricula(request, eMatricula)
            if not valid:
                raise NameError(msg)
            cantidad_nivel = aData['cantidad_nivel']
            porcentaje_perdidad_parcial_gratuidad = aData['porcentaje_perdidad_parcial_gratuidad']
            cantidad_seleccionadas = aData['cantidad_seleccionadas']
            porcentaje_seleccionadas = int(round(Decimal((float(cantidad_nivel) * float(porcentaje_perdidad_parcial_gratuidad)) / 100).quantize(Decimal('.00')), 0))
            if (cantidad_seleccionadas < porcentaje_seleccionadas):
                eMatricula.grupo_socio_economico(2)
            else:
                eMatricula.grupo_socio_economico(1)
            calcula_nivel(eMatricula)
            eMatricula.agregacion_aux(request)
            eMatricula.calcula_nivel()
            eMatricula.aranceldiferido = 2
            eMatricula.save(request)
            lista_materias.append(eMateria)
        if estudiante:
            send_html_mail("Automatricula", 'emails/notificacion_matriculacion_salud.html',
                           {'sistema': request.session['nombresistema'], 'ePersona': ePersona, 'fecha': datetime.now(),
                            'eMaterias': lista_materias, 't': miinstitucion()}, ePersona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[5][1])
            log(u'Automatricula estudiante: %s' % eMatricula, request, "add")
        return JsonResponse({"result": "ok"})
    except Exception as ex:
        transaction.set_rollback(True)
        return JsonResponse({"result": "bad", "mensaje": u"Error al matricular en las materias. %s" % ex})

def actualiza_criterios_actividades_tecnico_transversal(request, eProfesor, ePeriodo):
    try:
        listado_materias = ProfesorMateria.objects.filter(status=True, profesor=eProfesor, tipoprofesor_id=22, materia__nivel__periodo=ePeriodo)
        distributivo = ProfesorDistributivoHoras.objects.filter(status=True, periodo=ePeriodo, profesor=eProfesor).first()
        if not distributivo.bloqueardistributivo:
            totalhoras_materias_docente = sum(materia.hora for materia in listado_materias)
            # ACTUALIZA CRITERIO Y ACTIVIDAD DE TECNICO TRANSVERSAL
            criterio_tecnico_transversal = CriterioDocenciaPeriodo.objects.filter(criterio_id=185, periodo=ePeriodo).last()
            if criterio_tecnico_transversal:
                eDetalle = DetalleDistributivo.objects.filter(distributivo=distributivo, criteriodocenciaperiodo=criterio_tecnico_transversal).first()
                if totalhoras_materias_docente > 0:
                    if not eDetalle:
                        eDetalle = DetalleDistributivo(distributivo=distributivo,
                                                       criteriodocenciaperiodo=criterio_tecnico_transversal,
                                                       criterioinvestigacionperiodo=None,
                                                       criteriogestionperiodo=None,
                                                       criteriovinculacionperiodo=None,
                                                       horas=totalhoras_materias_docente)
                        eDetalle.save(request)
                        log(u'Adiciono criterio docencia a docente: %s - periodo: %s' % (eDetalle, eDetalle.distributivo.periodo), request, "add")
                    else:
                        eDetalle.horas = totalhoras_materias_docente
                        eDetalle.save(request)
                        log(u'Actualizó horas criterio docencia a docente: %s - periodo: %s' % (eDetalle, eDetalle.distributivo.periodo), request, "edit")
                    eDetalle.verifica_actividades(horas=eDetalle.horas)

                # ACTUALIZA CRITERIO  IMPARTIR CLASE
                criterio_impartir_clase = CriterioDocenciaPeriodo.objects.filter(criterio_id=118, periodo=ePeriodo).last()
                if criterio_impartir_clase:
                    eDetalle2 = DetalleDistributivo.objects.filter(distributivo=distributivo, criteriodocenciaperiodo=criterio_impartir_clase).first()
                    if eDetalle2:
                        horas_restantes = eDetalle2.horas - totalhoras_materias_docente
                        if horas_restantes > 0:
                            eDetalle2.horas = horas_restantes
                            eDetalle2.save(request)
                            log(u'Actualizó horas criterio docencia a docente: %s - periodo: %s' % (eDetalle2, eDetalle2.distributivo.periodo), request, "edit")
                            eDetalle2.verifica_actividades(horas=eDetalle2.horas)
                        else:
                            log(u'Elimino detalle docencia: %s - periodo: %s' % (eDetalle2, eDetalle2.distributivo.periodo), request, "del")
                            eDetalle2.delete()
                            distributivo.actualiza_hijos()

            distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
    except Exception as ex:
        transaction.set_rollback(True)
        return JsonResponse({"result": "bad", "mensaje": u"Problemas al actualizar el distributivo del docente. %s" % ex})


def asignaturas_aprobadas_primero_nivel_especifico(id_inscripcion, nivel):
    eInscripcion = Inscripcion.objects.get(pk=int(id_inscripcion))
    idasignatura = AsignaturaMalla.objects.values_list('asignatura_id', flat=False).filter(status=True,
                                                                                           opcional=False,
                                                                                           itinerario=0,
                                                                                           malla__inscripcionmalla__inscripcion=eInscripcion,
                                                                                           malla__inscripcionmalla__status=True,
                                                                                           nivelmalla__orden__lte=nivel-1)
    if eInscripcion.itinerario:
        if eInscripcion.itinerario > 0:
            otrosidasignatura = AsignaturaMalla.objects.values_list('asignatura_id', flat=False).filter(status=True,
                                                                                                        itinerario=eInscripcion.itinerario,
                                                                                                        malla__inscripcionmalla__inscripcion=eInscripcion,
                                                                                                        malla__inscripcionmalla__status=True,
                                                                                                        nivelmalla__orden__lte=nivel-1)
            idasignatura = idasignatura | otrosidasignatura
    for asignatura in idasignatura:
        materiarecord = eInscripcion.recordacademico_set.filter(status=True, asignatura=asignatura).first()
        ids_asignaturas_excluir_por_cambio_nivel_malla = variable_valor('ASIGNATURAS_CAMBIO_NIVEL_MALLA_PRACTICAS') if variable_valor('ASIGNATURAS_CAMBIO_NIVEL_MALLA_PRACTICAS') else []
        if asignatura and str(asignatura[0]) in ids_asignaturas_excluir_por_cambio_nivel_malla:
            continue
        if not materiarecord:
            return False
        if not materiarecord.aprobada:
            return False
    return True

def obtener_acta_compromiso_por_nivel(idmatricula):
    if _matricula := Matricula.objects.get(pk=idmatricula):
        _nivel = _matricula.nivelmalla
        eInscripcion = _matricula.inscripcion
        materias_asignada_vinculacion = _matricula.materiaasignada_set.filter(status=True, retiromanual=False, retiramateria=False, materia__status=True, materia__asignaturamalla__status=True,
                                                                              materia__asignaturamalla__asignaturavinculacion=True, materia__asignaturamalla__nivelmalla=_nivel).distinct().first()
        if materias_asignada_vinculacion and materias_asignada_vinculacion.actacompromisovinculacion:
            return materias_asignada_vinculacion.actacompromisovinculacion
    return None

def obtener_materia_asignada_vinculacion_por_nivel_v2(idmatricula):
    if _matricula := Matricula.objects.get(pk=idmatricula):
        _nivel = _matricula.nivelmalla
        materias_asignada_vinculacion = _matricula.materiaasignada_set.filter(status=True, retiromanual=False, retiramateria=False, materia__status=True, materia__asignaturamalla__status=True,
                                                                              materia__asignaturamalla__asignaturavinculacion=True, materia__asignaturamalla__nivelmalla__lte=_nivel).distinct().first()
        return materias_asignada_vinculacion
    return None

def actualiza_vigencia_criterios_docente(distributivo):
    try:
        if variable_valor('ACTUALIZAR_VIGENCIA_CRITERIOS_DOCENTE'):
            bandera = False
            if criterios_docencia := distributivo.detalle_horas_docencia():
                for docencia in criterios_docencia:
                    if actividades_docencia := docencia.actividades():
                        if actividad_vigente_docencia := actividades_docencia.filter(desde__lte=datetime.now().date(), hasta__gte=datetime.now().date(), vigente=False):
                            _actividad_vigente_docencia = actividad_vigente_docencia.first()
                            if not _actividad_vigente_docencia.nombre.endswith('.'):
                                _actividad_vigente_docencia.nombre += '.'
                                _actividad_vigente_docencia.save()
                            no_vigentes = actividades_docencia.exclude(pk=_actividad_vigente_docencia.id)
                            for nv in no_vigentes:
                                nv.criterio.claseactividad_set.filter(status=True, actividaddetallehorario=nv).delete()
                                if nv.nombre.endswith('.'):
                                    nv.nombre = nv.nombre[:-1]
                                    nv.save()
                            no_vigentes.update(vigente=False)
                            actividad_vigente_docencia.update(vigente=True)
                            if distributivo.bloqueardistributivo == True:
                                bandera = True
                                distributivo.bloqueardistributivo = False
                                distributivo.save()
                            _actividad_vigente_docencia.actualiza_padre()

            if criterios_investigacion := distributivo.detalle_horas_investigacion():
                for investigacion in criterios_investigacion:
                    if actividades_investigacion := investigacion.actividades():
                        if actividad_vigente_investigacion := actividades_investigacion.filter(desde__lte=datetime.now().date(), hasta__gte=datetime.now().date(), vigente=False):
                            _actividad_vigente_investigacion = actividad_vigente_investigacion.first()
                            if not _actividad_vigente_investigacion.nombre.endswith('.'):
                                _actividad_vigente_investigacion.nombre += '.'
                                _actividad_vigente_investigacion.save()
                            no_vigentes = actividades_investigacion.exclude(pk=_actividad_vigente_investigacion.id)
                            for nv in no_vigentes:
                                nv.criterio.claseactividad_set.filter(status=True, actividaddetallehorario=nv).delete()
                                if nv.nombre.endswith('.'):
                                    nv.nombre = nv.nombre[:-1]
                                    nv.save()
                            no_vigentes.update(vigente=False)
                            actividad_vigente_investigacion.update(vigente=True)
                            if distributivo.bloqueardistributivo == True:
                                bandera = True
                                distributivo.bloqueardistributivo = False
                                distributivo.save()
                            _actividad_vigente_investigacion.actualiza_padre()

            if criterios_gestion := distributivo.detalle_horas_gestion():
                for gestion in criterios_gestion:
                    if actividades_gestion := gestion.actividades():
                        if actividad_vigente_gestion := actividades_gestion.filter(desde__lte=datetime.now().date(), hasta__gte=datetime.now().date(), vigente=False):
                            _actividad_vigente_gestion = actividad_vigente_gestion.first()
                            if not _actividad_vigente_gestion.nombre.endswith('.'):
                                _actividad_vigente_gestion.nombre += '.'
                                _actividad_vigente_gestion.save()
                            no_vigentes = actividades_gestion.exclude(pk=_actividad_vigente_gestion.id)
                            for nv in no_vigentes:
                                nv.criterio.claseactividad_set.filter(status=True, actividaddetallehorario=nv).delete()
                                if nv.nombre.endswith('.'):
                                    nv.nombre = nv.nombre[:-1]
                                    nv.save()
                            no_vigentes.update(vigente=False)
                            actividad_vigente_gestion.update(vigente=True)
                            if distributivo.bloqueardistributivo == True:
                                bandera = True
                                distributivo.bloqueardistributivo = False
                                distributivo.save()
                            _actividad_vigente_gestion.actualiza_padre()

            if criterios_vinculacion := distributivo.detalle_horas_vinculacion():
                for vinculacion in criterios_vinculacion:
                    if actividades_vinculacion := vinculacion.actividades():
                        if actividad_vigente_vinculacion := actividades_vinculacion.filter(desde__lte=datetime.now().date(), hasta__gte=datetime.now().date(), vigente=False):
                            _actividad_vigente_vinculacion = actividad_vigente_vinculacion.first()
                            if not _actividad_vigente_vinculacion.nombre.endswith('.'):
                                _actividad_vigente_vinculacion.nombre += '.'
                                _actividad_vigente_vinculacion.save()
                            no_vigentes = actividades_vinculacion.exclude(pk=_actividad_vigente_vinculacion.id)
                            for nv in no_vigentes:
                                nv.criterio.claseactividad_set.filter(status=True, actividaddetallehorario=nv).delete()
                                if nv.nombre.endswith('.'):
                                    nv.nombre = nv.nombre[:-1]
                                    nv.save()
                            no_vigentes.update(vigente=False)
                            actividad_vigente_vinculacion.update(vigente=True)
                            if distributivo.bloqueardistributivo == True:
                                bandera = True
                                distributivo.bloqueardistributivo = False
                                distributivo.save()
                            _actividad_vigente_vinculacion.actualiza_padre()
            if bandera:
                distributivo.bloqueardistributivo = True
                distributivo.save()

    except Exception as ex:
        pass

def actualiza_registro_horario_docente(actividad, _action):
    try:
        if variable_valor('ACTUALIZAR_HORARIO_DOCENTE') and actividad.horas > 0:
            detalledistributivo = actividad.criterio
            if actividades := detalledistributivo.actividades():
                actividades_vigentes = actividades.filter(vigente=True)
                actividad_horas_vigente = detalledistributivo.detalleactividadcriterio()
                if not detalledistributivo.claseactividad_set.filter(status=True, actividaddetallehorario=actividad_horas_vigente).values('id').exists():
                    actividad_horas_vigente = actividad

                if _action == 'add' and actividad_horas_vigente:
                    registros_sin_relacion = detalledistributivo.claseactividad_set.filter(status=True).exclude(actividaddetallehorario=actividad_horas_vigente)[:actividad.horas]
                    detalledistributivo.claseactividad_set.filter(pk__in=registros_sin_relacion.values_list('id', flat=True)).update(actividaddetallehorario=actividad_horas_vigente, inicio=actividad_horas_vigente.desde, fin=actividad_horas_vigente.hasta, estadosolicitud=1)
                    detalledistributivo.claseactividad_set.filter(status=True).exclude(actividaddetallehorario=actividad_horas_vigente).delete()

                elif _action == 'edit' and actividad_horas_vigente:
                    registros = detalledistributivo.claseactividad_set.filter(status=True, actividaddetallehorario=actividad_horas_vigente)
                    if actividad.vigente and registros.count() != actividad.horas:
                        diferencia = registros[actividad.horas:]
                        registros.filter(pk__in=diferencia.values_list('id', flat=True)).delete()

                elif _action == 'check':
                    if not actividad.vigente:
                        if actividades_vigentes:
                            horas_vigentes = actividades_vigentes.aggregate(Sum('horas'))['horas__sum']
                            registros_del = detalledistributivo.claseactividad_set.filter(status=True, actividaddetallehorario=actividad_horas_vigente).order_by('fecha_creacion')[horas_vigentes:horas_vigentes + actividad.horas]
                            detalledistributivo.claseactividad_set.filter(pk__in=registros_del.values_list('id', flat=True)).delete()
                        else:
                            detalledistributivo.claseactividad_set.filter(status=True, actividaddetallehorario=actividad).delete()
    except Exception as ex:
        pass