# -*- coding: UTF-8 -*-
import json
import os
from math import ceil

import collections
import PyPDF2
from datetime import time
from decimal import Decimal

import requests
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import time as pausaparaemail
from xlwt import easyxf, XFStyle, Workbook
import random
from decorators import secure_module
from investigacion.forms import SolicitudGrupoInvestigacionForm, GrupoInvestigacionForm
from investigacion.funciones import periodo_vigente_distributivo_docente, coordinacion_carrera_distributivo_docente, secuencia_solicitud_grupo_investigacion, responsable_coordinacion, vicerrector_investigacion_posgrado, notificar_grupo_investigacion, identificacion_valida
from investigacion.models import GrupoInvestigacion, FUNCION_INTEGRANTE_GRUPO_INVESTIGACION, GrupoInvestigacionIntegrante, TIPO_PERSONA_GRUPO_INVESTIGACION_F, TIPO_FILIACION_PUBLICACION_F, GrupoInvestigacionRequisitoIntegrante, GrupoInvestigacionObjetivo, GrupoInvestigacionIntegranteRequisito, \
    GrupoInvestigacionTecnologia, GrupoInvestigacionRecorrido, GrupoInvestigacionResolucion
from sagest.commonviews import obtener_estado_solicitud, obtener_estados_solicitud
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible, generar_nombre, email_valido, \
    validar_archivo, null_to_decimal, cuenta_email_disponible_para_envio, fechaletra_corta
from sga.models import CUENTAS_CORREOS, Persona, LineaInvestigacion, Profesor, Inscripcion, Externo, Sexo
from django.template import Context
from django.template.loader import get_template
from sagest.models import datetime

import time as ET

from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt

from django.core.cache import cache


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    es_profesor = perfilprincipal.es_profesor()

    if not es_profesor:
        return HttpResponseRedirect("/?info=El Módulo está disponible para docentes.")

    data['profesor'] = profesor = persona.profesor()
    periodo = request.session['periodo']
    periodovigentedist = periodo_vigente_distributivo_docente(profesor)
    es_decano = False
    mis_coordinaciones = None
    if periodovigentedist:
        mcoord = profesor.mis_coordinaciones_a_cargo(periodovigentedist)
        es_decano = mcoord["resp"]
        mis_coordinaciones = mcoord["coordinaciones"]

    if request.method == 'POST':
        # Inicio POST
        action = request.POST['action']

        if action == 'addsolicitudgrupo':
            try:
                f = SolicitudGrupoInvestigacionForm(request.POST, request.FILES)

                if 'logotipo' in request.FILES:
                    archivo = request.FILES['logotipo']
                    descripcionarchivo = 'Logotipo'
                    resp = validar_archivo(descripcionarchivo, archivo, ['jpg', 'jpeg', 'png'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    # Verifico que no exista un grupo de investigación con el mismo nombre
                    if GrupoInvestigacion.objects.filter(status=True, nombre__iexact=f.cleaned_data['nombre']).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El nombre del grupo de investigación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    # Verifico que no exista un grupo de investigación con el mismo acrónimo
                    if GrupoInvestigacion.objects.filter(status=True, acronimo__iexact=f.cleaned_data['acronimo']).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El acrónimo del grupo de investigación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    archivologotipo = None
                    if 'logotipo' in request.FILES:
                        archivologotipo = request.FILES['logotipo']
                        archivologotipo._name = generar_nombre("logotipo", archivologotipo._name)

                    # Obtengo los valores de los detalles
                    integrantes = json.loads(request.POST['lista_items1'])
                    requisitos = json.loads(request.POST['lista_items2'])
                    objetivos = request.POST.getlist('objetivo_especifico[]')
                    tecnologias = request.POST.getlist('tecnologia[]')

                    # Validar que los objetivos no estén repetidos
                    listado = [objetivo.strip().upper() for objetivo in objetivos]
                    repetido = [x for x, y in collections.Counter(listado).items() if y > 1]
                    if repetido:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El item <b>%s</b> del detalle de objetivos específicos está repetido" % (repetido[0]), "showSwal": "True", "swalType": "warning"})

                    # Validar que se vayan a guardar mínimo 3 y máximo 15 profesores unemi
                    total = len([item for item in integrantes if item.get('idtipopersona') == '1' and item.get('idtipo') != '4'])
                    if total < 3 or total > 15:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El grupo de investigación debe estar conformado con mínimo tres (3) y máximo quince (15) profesores", "showSwal": "True", "swalType": "warning"})

                    # Validar que las tecnologías no estén repetidas
                    listado = [tecnologia.strip().upper() for tecnologia in tecnologias]
                    repetido = [x for x, y in collections.Counter(listado).items() if y > 1]
                    if repetido:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El item <b>%s</b> del detalle de tecnologías que domina está repetido" % (repetido[0]), "showSwal": "True", "swalType": "warning"})

                    # Obtengo estado EN EDICIÓN
                    estado = obtener_estado_solicitud(19, 1)

                    # Guardo los datos de la solicitud
                    solicitudgrupo = GrupoInvestigacion(
                        solicitudvigente=True,
                        periodo=periodovigentedist,
                        coordinacion=profesor.coordinacion,
                        profesor=profesor,
                        nombre=f.cleaned_data['nombre'].strip(),
                        acronimo=f.cleaned_data['acronimo'].strip(),
                        descripcion=f.cleaned_data['descripcion'].strip(),
                        objetivogeneral=f.cleaned_data['objetivogeneral'].strip(),
                        colaboracion=request.POST['colaboracion'].strip(),
                        logotipo=archivologotipo,
                        aprobadocoord=False,
                        aprobadoocs=False,
                        vigente=False,
                        estado=estado
                    )
                    solicitudgrupo.save(request)

                    # Guardar las líneas de investigación
                    for linea in request.POST.getlist('id_lineainvestigacion'):
                        solicitudgrupo.lineainvestigacion.add(linea)

                    solicitudgrupo.save(request)

                    # Guardar los objetivos específicos
                    for objetivo in objetivos:
                        objetivoespecifico = GrupoInvestigacionObjetivo(
                            grupo=solicitudgrupo,
                            descripcion=objetivo.strip()
                        )
                        objetivoespecifico.save(request)

                    # Guardar los integrantes o participantes
                    integrantedirector = None
                    for integrante in integrantes:
                        integrantegrupo = GrupoInvestigacionIntegrante(
                            grupo=solicitudgrupo,
                            tipo=integrante['idtipopersona'],
                            persona_id=integrante['idpersona'],
                            coordinacion_id=integrante['idcoordinacion'] if int(integrante['idcoordinacion']) != 0 else None,
                            carrera_id=integrante['idcarrera'] if int(integrante['idcarrera']) != 0 else None,
                            tipodocente_id=integrante['idtipo'] if int(integrante['idtipo']) != 0 else None,
                            dedicacion_id=integrante['iddedicacion'] if int(integrante['iddedicacion']) != 0 else None,
                            filiacion=integrante['idfiliacion'],
                            funcion=integrante['idfuncion'],
                            cantidadhora=integrante['horas'],
                            trayectoriaprevia=integrante['trayectoria'].strip(),
                            justificacion=integrante['justificacion'].strip()
                        )
                        integrantegrupo.save(request)

                        if int(integrante['idfuncion']) == 1:
                            integrantedirector = integrantegrupo

                    # Guardar las tecnologías que domina
                    for tecnologia in tecnologias:
                        tecnologiagrupo = GrupoInvestigacionTecnologia(
                            grupo=solicitudgrupo,
                            descripcion=tecnologia.strip()
                        )
                        tecnologiagrupo.save(request)

                    # Guardar los requisitos que debe cumplir el director de grupo
                    for requisito in requisitos:
                        integranterequisito = GrupoInvestigacionIntegranteRequisito(
                            integrante=integrantedirector,
                            requisito_id=requisito['id'],
                            cumpledir=requisito['valor']
                        )
                        integranterequisito.save(request)

                    # Creo el recorrido de la solicitud
                    recorrido = GrupoInvestigacionRecorrido(
                        grupo=solicitudgrupo,
                        fecha=datetime.now().date(),
                        observacion=estado.observacion,
                        estado=estado
                    )
                    recorrido.save(request)

                    log(u'%s adicionó solicitud de propuesta de creación de grupo de investigación: %s' % (persona, solicitudgrupo), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    for k, v in f.errors.items():
                        raise NameError( k + ', ' + v[0])

            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editsolicitudgrupo':
            try:
                # Consulto la solcitud
                solicitudgrupo = GrupoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda editar
                if not solicitudgrupo.puede_editar_solicitud():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el Registro porque ya ha sido revisado por otra instancia", "showSwal": "True", "swalType": "warning"})

                f = SolicitudGrupoInvestigacionForm(request.POST, request.FILES)

                if 'logotipo' in request.FILES:
                    archivo = request.FILES['logotipo']
                    descripcionarchivo = 'Logotipo'
                    resp = validar_archivo(descripcionarchivo, archivo, ['jpg', 'jpeg', 'png'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    # Verifico que no exista un grupo de investigación con el mismo nombre
                    if GrupoInvestigacion.objects.filter(status=True, nombre__iexact=f.cleaned_data['nombre']).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El nombre del grupo de investigación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    # Verifico que no exista un grupo de investigación con el mismo acrónimo
                    if GrupoInvestigacion.objects.filter(status=True, acronimo__iexact=f.cleaned_data['acronimo']).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El acrónimo del grupo de investigación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    archivologotipo = None
                    if 'logotipo' in request.FILES:
                        archivologotipo = request.FILES['logotipo']
                        archivologotipo._name = generar_nombre("logotipo", archivologotipo._name)

                    # Obtengo los valores de los detalles
                    integrantes = json.loads(request.POST['lista_items1'])
                    requisitos = json.loads(request.POST['lista_items2'])
                    idsobjetivos = request.POST.getlist('id_objetivo[]')
                    objetivos = request.POST.getlist('objetivo_especifico[]')
                    idtecnologias = request.POST.getlist('id_tecnologia[]')
                    tecnologias = request.POST.getlist('tecnologia[]')
                    objetivos_e = json.loads(request.POST['lista_items3']) # Objetivos eliminados
                    integrantes_e = json.loads(request.POST['lista_items4']) # Integrantes eliminados
                    tecnologias_e = json.loads(request.POST['lista_items5']) # Tecnologías eliminadas

                    # Validar que los objetivos no estén repetidos
                    listado = [objetivo.strip().upper() for objetivo in objetivos]
                    repetido = [x for x, y in collections.Counter(listado).items() if y > 1]
                    if repetido:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El item <b>%s</b> del detalle de objetivos específicos está repetido" % (repetido[0]), "showSwal": "True", "swalType": "warning"})

                    # Validar que se vayan a guardar mínimo 3 y máximo 15 profesores unemi
                    total = len([item for item in integrantes if item.get('idtipopersona') == '1' and item.get('idtipo') != '4'])
                    if total < 3 or total > 15:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El grupo de investigación debe estar conformado con mínimo tres (3) y máximo quince (15) profesores", "showSwal": "True", "swalType": "warning"})

                    # Validar que las tecnologías no estén repetidas
                    listado = [tecnologia.strip().upper() for tecnologia in tecnologias]
                    repetido = [x for x, y in collections.Counter(listado).items() if y > 1]
                    if repetido:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El item <b>%s</b> del detalle de tecnologías que domina está repetido" % (repetido[0]), "showSwal": "True", "swalType": "warning"})

                    # Actualizo los datos de la solicitud
                    solicitudgrupo.nombre = f.cleaned_data['nombre'].strip()
                    solicitudgrupo.acronimo = f.cleaned_data['acronimo'].strip()
                    solicitudgrupo.descripcion = f.cleaned_data['descripcion'].strip()
                    solicitudgrupo.objetivogeneral = f.cleaned_data['objetivogeneral'].strip()
                    solicitudgrupo.colaboracion = request.POST['colaboracion'].strip()
                    solicitudgrupo.observacion = ""
                    if archivologotipo:
                        solicitudgrupo.logotipo = archivologotipo

                    solicitudgrupo.save(request)

                    solicitudgrupo.lineainvestigacion.clear()
                    # Guardar las líneas de investigación
                    for linea in request.POST.getlist('id_lineainvestigacion'):
                        solicitudgrupo.lineainvestigacion.add(linea)

                    # Guardar los objetivos específicos
                    for idobj, objetivo in zip(idsobjetivos, objetivos):
                        # Nuevo
                        if int(idobj) == 0:
                            objetivoespecifico = GrupoInvestigacionObjetivo(
                                grupo=solicitudgrupo,
                                descripcion=objetivo.strip()
                            )
                        else:
                            objetivoespecifico = GrupoInvestigacionObjetivo.objects.get(pk=idobj)
                            objetivoespecifico.descripcion = objetivo.strip()

                        objetivoespecifico.save(request)

                    # Elimino los objetivos que se borraron del detalle
                    if objetivos_e:
                        for objetivo in objetivos_e:
                            objetivoespecifico = GrupoInvestigacionObjetivo.objects.get(pk=int(objetivo['idreg']))
                            objetivoespecifico.status = False
                            objetivoespecifico.save(request)

                    # Guardar los integrantes o participantes
                    for integrante in integrantes:
                        # Si es nuevo
                        if int(integrante['idreg']) == 0:
                            integrantegrupo = GrupoInvestigacionIntegrante(
                                grupo=solicitudgrupo,
                                tipo=integrante['idtipopersona'],
                                persona_id=integrante['idpersona'],
                                coordinacion_id=integrante['idcoordinacion'] if int(integrante['idcoordinacion']) != 0 else None,
                                carrera_id=integrante['idcarrera'] if int(integrante['idcarrera']) != 0 else None,
                                tipodocente_id=integrante['idtipo'] if int(integrante['idtipo']) != 0 else None,
                                dedicacion_id=integrante['iddedicacion'] if int(integrante['iddedicacion']) != 0 else None,
                                filiacion=integrante['idfiliacion'],
                                funcion=integrante['idfuncion'],
                                cantidadhora=integrante['horas'],
                                trayectoriaprevia=integrante['trayectoria'].strip(),
                                justificacion=integrante['justificacion'].strip()
                            )
                        else:
                            integrantegrupo = GrupoInvestigacionIntegrante.objects.get(pk=integrante['idreg'])
                            integrantegrupo.filiacion = integrante['idfiliacion']
                            integrantegrupo.trayectoriaprevia = integrante['trayectoria'].strip()
                            integrantegrupo.justificacion = integrante['justificacion'].strip()

                        integrantegrupo.save(request)

                    # Elimino los integrantes que se borraron del detalle
                    if integrantes_e:
                        for integrante in integrantes_e:
                            integrantegrupo = GrupoInvestigacionIntegrante.objects.get(pk=int(integrante['idreg']))
                            integrantegrupo.status = False
                            integrantegrupo.save(request)

                    # Guardar las tecnologías que domina
                    for idtecn, tecnologia in zip(idtecnologias, tecnologias):
                        # Nuevo
                        if int(idtecn) == 0:
                            tecnologiagrupo = GrupoInvestigacionTecnologia(
                                grupo=solicitudgrupo,
                                descripcion=tecnologia.strip()
                            )
                        else:
                            tecnologiagrupo = GrupoInvestigacionTecnologia.objects.get(pk=idtecn)
                            tecnologiagrupo.descripcion = tecnologia.strip()

                        tecnologiagrupo.save(request)

                    # Elimino las tecnologías que se borraron del detalle
                    if tecnologias_e:
                        for tecnologia in tecnologias_e:
                            tecnologiagrupo = GrupoInvestigacionTecnologia.objects.get(pk=int(tecnologia['idreg']))
                            tecnologiagrupo.status = False
                            tecnologiagrupo.save(request)

                    # Actualizar los requisitos que debe cumplir el director de grupo
                    for requisito in requisitos:
                        integranterequisito = GrupoInvestigacionIntegranteRequisito.objects.get(pk=int(requisito['idreg']))
                        integranterequisito.cumpledir = requisito['valor']
                        integranterequisito.cumpledec = False
                        integranterequisito.cumpleanl = False
                        integranterequisito.save(request)

                    # En caso de que estado actual sea NOVEDADES o DEVUELTO S se vuelve asignar EN EDICIÓN
                    if solicitudgrupo.estado.valor in [6, 12]:
                        # Obtengo estado SOLICITADO
                        estado = obtener_estado_solicitud(19, 1)

                        # Actualizo el estado de la solicitud
                        solicitudgrupo.solicitado = False
                        solicitudgrupo.estado = estado
                        solicitudgrupo.save(request)

                        # Creo el recorrido de la solicitud
                        recorrido = GrupoInvestigacionRecorrido(
                            grupo=solicitudgrupo,
                            fecha=datetime.now().date(),
                            observacion=estado.observacion,
                            estado=estado
                        )
                        recorrido.save(request)

                    log(u'%s editó solicitud de propuesta de creación de grupo de investigación: %s' % (persona, solicitudgrupo), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    for k, v in f.errors.items():
                        raise NameError( k + ', ' + v[0])

            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'delsolicitudgrupo':
            try:
                # Consulto la solicitud
                grupoinvestigacion = GrupoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda eliminar
                if not grupoinvestigacion.puede_eliminar_solicitud():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede eliminar el Registro porque no tiene estado EN EDICIÓN o NOVEDADES", "showSwal": "True", "swalType": "warning"})

                # Obtengo estado ANULADO
                estado = obtener_estado_solicitud(19, 3)

                # Elimino la solicitud
                grupoinvestigacion.estado = estado
                grupoinvestigacion.observacion = "ELIMINADA POR EL SOLICITANTE"
                grupoinvestigacion.status = False
                grupoinvestigacion.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = GrupoInvestigacionRecorrido(
                    grupo=grupoinvestigacion,
                    fecha=datetime.now().date(),
                    observacion='SOLICITUD ELIMINADA',
                    estado=estado
                )
                recorrido.save(request)

                log(u'%s eliminó solicitud de propuesta de creación de grupo de investigación: %s' % (persona, grupoinvestigacion), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al eliminar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'confirmarsolicitudgrupo':
            try:
                # Consulto la solicitud
                grupoinvestigacion = GrupoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que tenga estado EN EDICIÓN
                if not grupoinvestigacion.estado.valor == 1:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el Registro porque no tiene estado EN EDICIÓN", "showSwal": "True", "swalType": "warning"})

                # Obtengo la persona responsable de la coordinación
                decano = responsable_coordinacion(grupoinvestigacion.periodo, grupoinvestigacion.coordinacion)
                if not decano:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el Registro porque la facultad a la que pertenece no tiene asignado un decano", "showSwal": "True", "swalType": "warning"})

                # Obtengo estado SOLICITADO
                estado = obtener_estado_solicitud(19, 2)

                # En caso de no tener número de solicitud
                if not grupoinvestigacion.numero:
                    # Obtener secuencia de la solicitud
                    secuencia = secuencia_solicitud_grupo_investigacion()

                    # Actualizo la postulación
                    grupoinvestigacion.numero = secuencia
                    grupoinvestigacion.fechasolicitud = datetime.now()

                # Actualizo los demás campos de postulación
                grupoinvestigacion.solicitudvigente = True
                grupoinvestigacion.solicitado = True
                grupoinvestigacion.estado = estado
                grupoinvestigacion.save(request)

                # Guardo el recorrido
                recorrido = GrupoInvestigacionRecorrido(
                    grupo=grupoinvestigacion,
                    fecha=datetime.now().date(),
                    observacion=estado.observacion,
                    estado=estado
                )
                recorrido.save(request)

                # Notificar al solicitante
                notificar_grupo_investigacion(grupoinvestigacion, "REGSOL")

                # Notificar al decano
                notificar_grupo_investigacion(grupoinvestigacion, "REGDEC")

                log(u'%s confirmó solicitud de propuesta para creación de grupo de investigación: %s' % (persona, grupoinvestigacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro de solicitud confirmado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'revisarsolicitud':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la solicitud de Grupo de Investigación
                grupoinvestigacion = GrupoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                estadoinicial = grupoinvestigacion.estado

                # Verifico si puede revisar la solicitud
                if not grupoinvestigacion.puede_revisar_solicitud():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el Registro porque ya ha sido revisado por otra instancia", "showSwal": "True", "swalType": "warning"})

                # Obtengo los valores del formulario
                requisitos = json.loads(request.POST['lista_items1'])
                valorestado = int(request.POST['estadosolicitud'])
                estado = obtener_estado_solicitud(19, valorestado)
                observacion = request.POST['observacion'].strip()

                # Actualizo la solicitud
                grupoinvestigacion.observacion = observacion
                grupoinvestigacion.estado = estado
                grupoinvestigacion.save(request)

                # Actualizar los requisitos que debe cumplir el director de grupo
                for requisito in requisitos:
                    integranterequisito = GrupoInvestigacionIntegranteRequisito.objects.get(pk=int(requisito['idreg']))
                    integranterequisito.cumpledec = requisito['valor']
                    integranterequisito.save(request)

                # Si los estados son distintos
                if estadoinicial.valor != estado.valor:
                    # Guardar el recorrido
                    recorrido = GrupoInvestigacionRecorrido(
                        grupo=grupoinvestigacion,
                        fecha=datetime.now().date(),
                        observacion=observacion if observacion else estado.observacion,
                        estado=estado
                    )
                else:
                    recorrido = GrupoInvestigacionRecorrido.objects.filter(status=True, grupo=grupoinvestigacion, estado=estado).order_by('-id')[0]
                    recorrido.observacion = observacion

                recorrido.save(request)

                # Notificar al solicitante
                notificar_grupo_investigacion(grupoinvestigacion, "REVSOL" if valorestado == 4 else "NOVSOL")

                log(u'%s revisó solicitud de propuesta para creación de grupo de investigación: %s' % (persona, grupoinvestigacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'aprobacionconsejo':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la solicitud de Grupo de Investigación
                grupoinvestigacion = GrupoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                estadoinicial = grupoinvestigacion.estado
                archivoresolucion = None

                # Verifico que se pueda editar
                if not grupoinvestigacion.puede_subir_resolucion_facultad():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el Registro porque ya ha sido revisado por otra instancia", "showSwal": "True", "swalType": "warning"})

                if 'archivoresolucion' in request.FILES:
                    archivoresolucion = request.FILES['archivoresolucion']
                    descripcionarchivo = 'Archivo Resolución Consejo'

                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivoresolucion, ['PDF'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    archivoresolucion = request.FILES['archivoresolucion']
                    archivoresolucion._name = generar_nombre("resolucionconsejofacultad", archivoresolucion._name)

                # Obtengo los valores del formulario
                valorestado = int(request.POST['estadosolicitud'])
                estado = obtener_estado_solicitud(19, valorestado)
                numeroresolucion = request.POST['numeroresolucion'].strip().upper()
                fecharesolucion = datetime.strptime(request.POST['fecharesolucion'], '%Y-%m-%d').date()
                resuelve = request.POST['resuelve'].strip()

                # Fecha de resolución debe ser mayor o igual a fecha solicitud
                if fecharesolucion < grupoinvestigacion.fechasolicitud.date():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de resolución debe ser mayor o igual a la fecha de solicitud", "showSwal": "True", "swalType": "warning"})

                # Actualizo la solicitud
                grupoinvestigacion.aprobadocoord = True
                grupoinvestigacion.estado = estado
                grupoinvestigacion.save(request)

                # Consulto la resolución de facultad
                resolucion = grupoinvestigacion.resolucion_facultad()
                if not resolucion:
                    pdf2ReaderEvi = PyPDF2.PdfFileReader(archivoresolucion)
                    resolucion = GrupoInvestigacionResolucion(
                        grupo=grupoinvestigacion,
                        tipo=1,
                        numero=numeroresolucion,
                        fecha=fecharesolucion,
                        resuelve=resuelve,
                        archivo=archivoresolucion,
                        numeropagina=pdf2ReaderEvi.numPages,
                        vigente=True
                    )
                else:
                    resolucion.numero = numeroresolucion
                    resolucion.fecha = fecharesolucion
                    resolucion.resuelve = resuelve
                    if archivoresolucion:
                        pdf2ReaderEvi = PyPDF2.PdfFileReader(archivoresolucion)
                        resolucion.archivo = archivoresolucion
                        resolucion.numeropagina = pdf2ReaderEvi.numPages

                resolucion.save(request)

                # Si el estado original es REVISADO y notificar por email
                if estadoinicial.valor == 4:
                    # Guardar el recorrido
                    recorrido = GrupoInvestigacionRecorrido(
                        grupo=grupoinvestigacion,
                        fecha=datetime.now().date(),
                        observacion=estado.observacion,
                        estado=estado
                    )
                    recorrido.save(request)

                    # Notificar al solicitante
                    notificar_grupo_investigacion(grupoinvestigacion, "APRFAC")

                    # Notificar al vicerrector de investigación
                    notificar_grupo_investigacion(grupoinvestigacion, "NOTVICE")

                log(u'%s registró aprobación de consejo de facultad para la solicitud de propuesta para creación de grupo de investigación: %s' % (persona, grupoinvestigacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addpersonaexterna':
            try:
                # Verifico que haya ingresado cédula o pasaporte
                if not request.POST['cedulapex'] and not request.POST['pasaportepex']:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"Ingrese número de cédula o pasaporte", "showSwal": "True", "swalType": "warning"})

                resp = identificacion_valida(request.POST['cedulapex'].strip(), request.POST['pasaportepex'].strip().upper())

                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Guardo la persona
                personaexterna = Persona(
                    nombres=request.POST['nombrepex'].strip().upper(),
                    apellido1=request.POST['apellido1pex'].strip().upper(),
                    apellido2=request.POST['apellido2pex'].strip().upper(),
                    cedula=request.POST['cedulapex'].strip(),
                    pasaporte=request.POST['pasaportepex'].strip().upper(),
                    sexo_id=request.POST['generopex'],
                    nacimiento=datetime.now().date()
                )
                personaexterna.save(request)

                # Guardo externo
                externo = Externo(
                    persona=personaexterna,
                    nombrecomercial=request.POST['apellido1pex'].strip().upper() + ' ' + request.POST['apellido2pex'].strip().upper() + ' ' + request.POST['nombrepex'].strip().upper()
                )
                externo.save(request)

                personaexterna.crear_perfil(externo=externo)
                personaexterna.mi_perfil()

                log(u'%s agregó persona externa: %s' % (persona, personaexterna), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Persona externa guardada con éxito", "showSwal": True, "idpersona": personaexterna.id, "nombres": personaexterna.nombre_completo_inverso()})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})


        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Solicitud incorrecta.", "showSwal": "True", "swalType": "error"})
        # Fin POST
    else:
        if 'action' in request.GET:
            # Inicio GET (action)
            action = request.GET['action']

            if action == 'solicitudesgrupo':
                try:
                    search, tipo, url_vars = request.GET.get('s', ''), request.GET.get('tipo', ''), '&action=' + action

                    if tipo == 'ms':
                        filtro = Q(status=True, profesor=profesor, grupoinvestigacionrecorrido__estado__valor=1)
                    else:
                        filtro = Q(status=True, periodo=periodovigentedist, coordinacion_id__in=mis_coordinaciones, solicitado=True)

                    if search:
                        data['s'] = search
                        filtro = filtro & (Q(nombre__unaccent__icontains=search))
                        url_vars += '&s=' + search

                    gruposinvestigacion = GrupoInvestigacion.objects.filter(filtro).distinct().order_by('-numero')

                    paging = MiPaginador(gruposinvestigacion, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['url_vars'] = url_vars
                    data['gruposinvestigacion'] = page.object_list
                    data['title'] = u'Solicitudes de Propuestas de Creación de Grupos de Investigación'
                    puedeagregar = profesor.puede_agregar_solicitud_grupo_investigacion()
                    data['solicitar'] = puedeagregar["resp"]
                    data['mensaje'] = puedeagregar["msg"]
                    data['tipo'] = tipo
                    data['es_decano'] = es_decano
                    data['enlaceatras'] = "/pro_fgrupoinvestigacion"

                    return render(request, "pro_grupoinvestigacion/solicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'addsolicitudgrupo':
                try:
                    data['title'] = u'Agregar Solicitud de Propuesta de Creación de Grupo de Investigación'
                    reg = coordinacion_carrera_distributivo_docente(profesor)
                    form = SolicitudGrupoInvestigacionForm(
                        initial={
                            "coordinacion": reg["coordinacion"],
                            "carrera": reg["carrera"]
                        }
                    )
                    data['form'] = form
                    data['coordcarr'] = reg
                    data['lineasinvestigacion'] = LineaInvestigacion.objects.filter(vigente=True, status=True).order_by('nombre')
                    data['filiaciones'] = TIPO_FILIACION_PUBLICACION_F
                    data['requisitos'] = GrupoInvestigacionRequisitoIntegrante.objects.filter(status=True, vigente=True).order_by('numero')
                    return render(request, "pro_grupoinvestigacion/addsolicitudgrupo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editsolicitudgrupo':
                try:
                    data['title'] = u'Editar Solicitud de Propuesta de Creación de Grupo de Investigación'

                    data['grupoinvestigacion'] = grupoinvestigacion = GrupoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))

                    form = SolicitudGrupoInvestigacionForm(
                        initial={
                            "coordinacion": grupoinvestigacion.coordinacion.nombre,
                            "carrera": grupoinvestigacion.carrera_grupo(),
                            "nombre": grupoinvestigacion.nombre,
                            "acronimo" : grupoinvestigacion.acronimo,
                            "descripcion": grupoinvestigacion.descripcion,
                            "objetivogeneral": grupoinvestigacion.objetivogeneral
                        }
                    )

                    data['form'] = form
                    data['lineasgrupo'] = ",".join([str(lineagrupo.id) for lineagrupo in grupoinvestigacion.lineas_grupo()])
                    data['lineasinvestigacion'] = LineaInvestigacion.objects.filter(vigente=True, status=True).order_by('nombre')
                    data['objetivos'] = grupoinvestigacion.objetivos_especificos()
                    data['integrantes'] = grupoinvestigacion.integrantes()
                    data['tecnologias'] = grupoinvestigacion.tecnologias()
                    data['requisitos'] = grupoinvestigacion.requisitos_director()
                    data['filiaciones'] = TIPO_FILIACION_PUBLICACION_F

                    return render(request, "pro_grupoinvestigacion/editsolicitudgrupo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addintegrante':
                try:
                    data['title'] = u'Agregar Integrante al Grupo de Investigación'
                    data['tipospersona'] = TIPO_PERSONA_GRUPO_INVESTIGACION_F
                    data['funcion'] = 'INVESTIGADOR'
                    data['idfuncion'] = 3
                    data['filiaciones'] = TIPO_FILIACION_PUBLICACION_F

                    template = get_template("pro_grupoinvestigacion/addintegrante.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'datosprofesor':
                try:
                    profesor = Profesor.objects.get(pk=request.GET['id'])

                    idtipo = profesor.nivelcategoria.id
                    tipo = profesor.nivelcategoria.nombre
                    iddedicacion = profesor.dedicacion.id
                    dedicacion = profesor.dedicacion.nombre
                    nombre = profesor.persona.nombre_completo_inverso()
                    horasgrupoinv = 0
                    cantgruposvigentes = profesor.persona.cantidad_grupos_investigacion_vigente()
                    dist = coordinacion_carrera_distributivo_docente(profesor)
                    idcoordinacion = dist["idcoordinacion"]
                    coordinacion = dist["coordinacion"]
                    aliascoordinacion = dist["aliascoordinacion"]
                    idcarrera = dist["idcarrera"]
                    carrera = dist["carrera"]
                    aliascarrera = dist["aliascarrera"]

                    data = {"result": "ok", "idtipo" : idtipo, "tipo": tipo, "iddedicacion": iddedicacion, "dedicacion": dedicacion, "nombre": nombre, "horasgrupoinv": horasgrupoinv, "cantgruposvigentes": cantgruposvigentes, "idcoordinacion": idcoordinacion, "coordinacion": coordinacion, "aliascoordinacion": aliascoordinacion, "idcarrera": idcarrera, "carrera": carrera, "aliascarrera": aliascarrera}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'datosalumno':
                try:
                    inscripcion = Inscripcion.objects.get(pk=request.GET['id'])

                    idtipo = 0
                    tipo = ""
                    iddedicacion = 0
                    dedicacion = ""
                    nombre = inscripcion.persona.nombre_completo_inverso()
                    horasgrupoinv = 0
                    cantgruposvigentes = inscripcion.persona.cantidad_grupos_investigacion_vigente()
                    idcoordinacion = inscripcion.coordinacion.id
                    coordinacion = inscripcion.coordinacion.nombre
                    aliascoordinacion = inscripcion.coordinacion.alias
                    idcarrera = inscripcion.carrera.id
                    carrera = inscripcion.carrera.nombre
                    aliascarrera = inscripcion.carrera.alias
                    data = {"result": "ok", "idtipo" : idtipo, "tipo": tipo, "iddedicacion": iddedicacion, "dedicacion": dedicacion, "nombre": nombre, "horasgrupoinv": horasgrupoinv, "cantgruposvigentes": cantgruposvigentes, "idcoordinacion": idcoordinacion, "coordinacion": coordinacion, "aliascoordinacion": aliascoordinacion, "idcarrera": idcarrera, "carrera": carrera, "aliascarrera": aliascarrera}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'datosexterno':
                try:
                    externo = Externo.objects.get(pk=request.GET['id'])

                    idtipo = 0
                    tipo = ""
                    iddedicacion = 0
                    dedicacion = ""
                    nombre = externo.persona.nombre_completo_inverso()
                    horasgrupoinv = 0
                    cantgruposvigentes = externo.persona.cantidad_grupos_investigacion_vigente()
                    idcoordinacion = 0
                    coordinacion = ""
                    aliascoordinacion = ""
                    idcarrera = 0
                    carrera = ""
                    aliascarrera = ""
                    data = {"result": "ok", "idtipo" : idtipo, "tipo": tipo, "iddedicacion": iddedicacion, "dedicacion": dedicacion, "nombre": nombre, "horasgrupoinv": horasgrupoinv, "cantgruposvigentes": cantgruposvigentes, "idcoordinacion": idcoordinacion, "coordinacion": coordinacion, "aliascoordinacion": aliascoordinacion, "idcarrera": idcarrera, "carrera": carrera, "aliascarrera": aliascarrera}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addpersonaexterna':
                try:
                    data['title'] = u'Agregar Persona Externa'
                    data['funcion'] = 'INVESTIGADOR'
                    data['idfuncion'] = 3
                    data['filiaciones'] = TIPO_FILIACION_PUBLICACION_F
                    data['generos'] = Sexo.objects.filter(status=True)

                    template = get_template("pro_grupoinvestigacion/addpersonaexterna.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mostrarrecorrido':
                try:
                    title = u'Recorrido de la Solicitud de Propuesta de Creación de Grupo de Investigación'
                    grupoinvestigacion = GrupoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['grupoinvestigacion'] = grupoinvestigacion
                    data['recorrido'] = grupoinvestigacion.recorrido()
                    template = get_template("pro_grupoinvestigacion/recorrido.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informacion':
                try:
                    data['title'] = u'Información Solicitud de Propuesta de Creación de Grupo de Investigación'
                    data['grupo'] = grupoinvestigacion = GrupoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['objetivos'] = grupoinvestigacion.objetivos_especificos()
                    data['lineasinvestigacion'] = grupoinvestigacion.lineas_grupo()
                    data['integrantes'] = grupoinvestigacion.integrantes()
                    data['tecnologias'] = grupoinvestigacion.tecnologias()
                    data['requisitos'] = grupoinvestigacion.requisitos_director()
                    data['resolucion'] = grupoinvestigacion.resolucion_facultad()
                    data['resolucionocs'] = grupoinvestigacion.resolucion_ocs()
                    data['tipo'] = request.GET['tipo']
                    return render(request, "pro_grupoinvestigacion/informacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'revisarsolicitud':
                try:
                    data['title'] = u'Revisar Solicitud de Propuesta de Creación de Grupo de Investigación'
                    data['grupo'] = grupoinvestigacion = GrupoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['objetivos'] = grupoinvestigacion.objetivos_especificos()
                    data['lineasinvestigacion'] = grupoinvestigacion.lineas_grupo()
                    data['integrantes'] = grupoinvestigacion.integrantes()
                    data['tecnologias'] = grupoinvestigacion.tecnologias()
                    data['requisitos'] = grupoinvestigacion.requisitos_director()
                    data['estados'] = obtener_estados_solicitud(19, [4, 6])
                    return render(request, "pro_grupoinvestigacion/revisarsolicitudgrupo.html", data)
                except Exception as ex:
                    pass

            elif action == 'aprobacionconsejo':
                try:
                    data['title'] = u'Aprobación Consejo Directivo de Facultad'
                    data['grupo'] = grupo = GrupoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['fecha'] = datetime.now().date()
                    data['estado'] = obtener_estado_solicitud(19, 5)
                    data['resolucion'] = grupo.resolucion_facultad()
                    template = get_template("pro_grupoinvestigacion/aprobacionfacultad.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al obtener los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})


            return HttpResponseRedirect(request.path)
            # Fin GET (action)
        else:
            try:
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, vigente=True, grupoinvestigacionintegrante__persona=persona, grupoinvestigacionintegrante__status=True, grupoinvestigacionrecorrido__estado__valor=21), ''

                if search:
                    data['s'] = search
                    filtro = filtro & (Q(nombre__unaccent__icontains=search))
                    url_vars += '&s=' + search

                gruposinvestigacion = GrupoInvestigacion.objects.filter(filtro).order_by('nombre')

                paging = MiPaginador(gruposinvestigacion, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
                    else:
                        p = paginasesion
                    try:
                        page = paging.page(p)
                    except:
                        p = 1
                    page = paging.page(p)
                except:
                    page = paging.page(p)
                request.session['paginador'] = p
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['url_vars'] = url_vars
                data['gruposinvestigacion'] = page.object_list
                data['es_decano'] = es_decano
                data['title'] = u'Mis Grupos de Investigación'
                data['enlaceatras'] = "/pro_investigacion"

                return render(request, "pro_grupoinvestigacion/view.html", data)
            except Exception as ex:
                pass
