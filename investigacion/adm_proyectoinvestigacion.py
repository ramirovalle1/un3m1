# -*- coding: UTF-8 -*-
import json
import os
import io
import zipfile
import calendar
from datetime import time
import time as pausaparaemail
from decimal import Decimal
from math import ceil
from typing import Union
from bs4 import BeautifulSoup

import PyPDF2
import xlsxwriter
from django.core.files import File as DjangoFile
from fitz import fitz
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from xlwt import easyxf, XFStyle, Workbook
import random
from decorators import secure_module
from investigacion.forms import ConvocatoriaProyectoForm, ContenidoProyectoInvestigacionForm, \
    RubricaEvaluacionForm, EvaluadorProyectoInvestigacionForm, ResolucionAprobacionProyectoForm, EvaluadorExternoForm, \
    InformeProyectoForm, EvaluadorProyectoInvestigacionFinalizadoForm, RegistroPropuestaProyectoInvestigacionExternoForm, ExternoForm
from investigacion.funciones import coordinador_investigacion, tecnicos_investigacion, secuencia_codigo_proyecto, FORMATOS_CELDAS_EXCEL, periodo_vigente_distributivo_docente_investigacion, \
    actualizar_permiso_edicion_rubros_presupuesto, numero_criterio_evaluacion, getmonthname, guardar_historial_archivo_proyectos_investigacion, \
    elemento_repetido_lista
from investigacion.models import ProyectoInvestigacion, \
    ProyectoInvestigacionRecorrido, ProyectoInvestigacionIntegrante, ConvocatoriaMontoFinanciamiento, \
    ConvocatoriaProyecto, TIPO_PROYECTO, TIPO_PORCENTAJE_EQUIPOS, \
    ConvocatoriaProgramaInvestigacion, RubricaEvaluacion, RubricaEvaluacionItem, ProyectoInvestigacionEvaluador, \
    ESTADO_EVALUACION_INTERNA_EXTERNA, EvaluacionProyecto, EvaluacionProyectoDetalle, \
    ProyectoInvestigacionHistorialArchivo, ProyectoInvestigacionCronogramaActividad, \
    ProyectoInvestigacionRevisionActividad, ProyectoInvestigacionRevisionActividadDetalle, \
    ProyectoInvestigacionActividadEvidencia, ConvocatoriaResolucionAprobacionProyecto, TIPO_EVALUADOR_PROYECTO, \
    EvaluadorProyecto, ProyectoInvestigacionInforme, ProyectoInvestigacionCronogramaEntregable, ProyectoInvestigacionHistorialActividadEvidencia, ProyectoInvestigacionInformeActividad, ProyectoInvestigacionInformeAnexo, TIPO_INTEGRANTE, TipoResultadoCompromiso, TipoRecursoPresupuesto, \
    ConvocatoriaTipoRecurso, \
    Categoria, ZonaPlanificacion, ProyectoInvestigacionInstitucion, ProyectoInvestigacionObjetivo, ProyectoInvestigacionResultado, ProyectoInvestigacionReferenciaBibliografica, \
    ProyectoInvestigacionItemPresupuesto, ProyectoInvestigacionCronogramaResponsable, ProyectoInvestigacionHistorialMontoPresupuesto, TIPO_PERSONA_PERMISO_EDICION, ProyectoInvestigacionPermisoEdicion, \
    ProyectoInvestigacionHistorialPresupuesto, ProyectoInvestigacionItemPresupuestoHistorial, ProyectoInvestigacionMovimientoItemPresupuesto, \
    ProyectoInvestigacionHistorialCronograma, ProyectoInvestigacionCronogramaActividadHistorial, ProyectoInvestigacionCronogramaResponsableHistorial, ProyectoInvestigacionExclusionValidacion, \
    ProyectoInvestigacionAvanceActividad, TipoDocumento
from sagest.commonviews import obtener_estados_solicitud, obtener_estado_solicitud
from sagest.models import datetime, DistributivoPersona, ExperienciaLaboral, Producto
from settings import DEBUG, SITE_STORAGE
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible, generar_nombre, \
    cuenta_email_disponible_para_envio, validar_archivo, null_to_decimal, calculate_username, generar_usuario, remover_caracteres, elimina_tildes, remover_caracteres_especiales_unicode, resetear_clave
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, convert_html_to_pdf
from sga.models import Persona, miinstitucion, \
    CUENTAS_CORREOS, \
    ProgramasInvestigacion, Profesor, Externo, Titulo, InstitucionEducacionSuperior, Pais, Titulacion, \
    ArticuloPersonaExterna, PonenciaPersonaExterna, LibroPersonaExterna, ProyectoInvestigacionPersonaExterna, \
    NivelTitulacion, AreaConocimientoTitulacion, MESES_CHOICES, RedPersona, Inscripcion, Administrativo, Periodo, EvidenciaActividadDetalleDistributivo, \
    HistorialAprobacionEvidenciaActividad, AnexoEvidenciaActividad, EvidenciaActividadAudi, CriterioInvestigacion, DetalleDistributivo, TituloInstitucion, SubLineaInvestigacion, Provincia, \
    LineaInvestigacion

from postulaciondip.forms import FirmaElectronicaIndividualForm
from django.template import Context
from django.template.loader import get_template
from core.firmar_documentos import firmar, obtener_posicion_x_y_saltolinea
from core.firmar_documentos_ec import JavaFirmaEc
from django.core.files.base import ContentFile

import time as ET

from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    # data['periodo'] = periodo = request.session['periodo']
    periodo = request.session['periodo']

    # es_coordinacioninv = persona.grupo_coordinacion_investigacion()

    dominio_sistema = 'http://localhost:8000' if DEBUG else 'https://sga.unemi.edu.ec'
    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema

    # if not es_coordinacioninv:
    #     return HttpResponseRedirect("/?info=El Módulo está disponible para la Coordinación de Investigación.")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addconvocatoria':
            try:
                if 'archivoresolucion' in request.FILES:
                    archivo = request.FILES['archivoresolucion']
                    descripcionarchivo = 'Archivo resolución OCS'

                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivoconvocatoria' in request.FILES:
                    archivo = request.FILES['archivoconvocatoria']
                    descripcionarchivo = 'Archivo Bases Convocatoria'

                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                f = ConvocatoriaProyectoForm(request.POST, request.FILES)

                if f.is_valid():
                    if not ConvocatoriaProyecto.objects.filter(status=True, descripcion=f.cleaned_data['descripcion']).exists():
                        idstipo = request.POST.getlist('idtipo[]')
                        minimos = request.POST.getlist('minimo[]')
                        maximos = request.POST.getlist('maximo[]')
                        porcentajes = request.POST.getlist('porcentaje[]')
                        tiposporcentajes = request.POST.getlist('tipoporc[]')
                        programas = json.loads(request.POST['lista_items2'])

                        archivo = None
                        if 'archivoresolucion' in request.FILES:
                            archivo = request.FILES['archivoresolucion']
                            archivo._name = generar_nombre("resolucionocas", archivo._name)

                        archivoconvocatoria = None
                        if 'archivoconvocatoria' in request.FILES:
                            archivoconvocatoria = request.FILES['archivoconvocatoria']
                            archivoconvocatoria._name = generar_nombre("convocatoria", archivo._name)

                        # Guardo la convocatoria
                        convocatoria = ConvocatoriaProyecto(
                            descripcion=f.cleaned_data['descripcion'],
                            apertura=f.cleaned_data['apertura'],
                            cierre=f.cleaned_data['cierre'],
                            minimoaprobacion=f.cleaned_data['minimoaprobacion'],
                            inicioevalint=f.cleaned_data['inicioevalint'],
                            finevalint=f.cleaned_data['finevalint'],
                            inicioreevalint=f.cleaned_data['inicioreevalint'],
                            finreevalint=f.cleaned_data['finreevalint'],
                            inicioevalext=f.cleaned_data['inicioevalext'],
                            finevalext=f.cleaned_data['finevalext'],
                            inicioreevalext=f.cleaned_data['inicioreevalext'],
                            finreevalext=f.cleaned_data['finreevalext'],
                            inicioselapro=f.cleaned_data['inicioselapro'],
                            finselapro=f.cleaned_data['finselapro'],
                            periodocidad=f.cleaned_data['periodocidad'],
                            archivoresolucion=archivo,
                            archivoconvocatoria=archivoconvocatoria,
                            minintegranteu=f.cleaned_data['minintegranteu'],
                            maxintegranteu=f.cleaned_data['maxintegranteu'],
                            minintegrantee=f.cleaned_data['minintegrantee'],
                            maxintegrantee=f.cleaned_data['maxintegrantee']
                        )
                        convocatoria.save(request)

                        # Guardo los montos de financiamiento
                        for idtipo, minimo, maximo, porcentaje, tipoporcentaje in zip(idstipo, minimos, maximos, porcentajes, tiposporcentajes):
                            montoconvocatoria = ConvocatoriaMontoFinanciamiento(
                                convocatoria=convocatoria,
                                categoria_id=idtipo,
                                minimo=minimo,
                                maximo=maximo,
                                porcentajecompra=porcentaje,
                                tipoporcentaje=tipoporcentaje
                            )
                            montoconvocatoria.save(request)

                        # Guardo los programas de investigación
                        for programa in programas:
                            programaconvocatoria = ConvocatoriaProgramaInvestigacion(
                                convocatoria=convocatoria,
                                programainvestigacion_id=programa['idprog']
                            )
                            programaconvocatoria.save(request)

                        # Guardo los 3 compromisos de la convocatoria
                        descripcion = "Presentar la carta de aceptación o publicación de un artículo científico (mínimo en cuartil 3 en SJR/JCR), donde se evidencie la participación del director y/o co-director del proyecto, y al menos un investigador asociado."
                        compromisoconvocatoria = TipoResultadoCompromiso(
                            convocatoria=convocatoria,
                            descripcion=descripcion,
                            numero=1,
                            fijo=True,
                            obligatorio=True
                        )
                        compromisoconvocatoria.save(request)

                        descripcion = "Participar en al menos dos (2) eventos de divulgación científica de la Facultad de Investigación."
                        compromisoconvocatoria = TipoResultadoCompromiso(
                            convocatoria=convocatoria,
                            descripcion=descripcion,
                            numero=2,
                            fijo=True,
                            obligatorio=True
                        )
                        compromisoconvocatoria.save(request)

                        descripcion = "Evidenciar la transferencia de conocimientos mediante eventos o documentos que avalen la socialización de los resultados del proyecto a las comunidades, o profesionales en el área de interés del proyecto, que sirvan de línea base para la generación de proyectos, sean estos de vinculación o de otra naturaleza."
                        compromisoconvocatoria = TipoResultadoCompromiso(
                            convocatoria=convocatoria,
                            descripcion=descripcion,
                            numero=3,
                            fijo=True,
                            obligatorio=True
                        )
                        compromisoconvocatoria.save(request)

                        # Guardo los tipos de recursos para el presupuesto del proyecto
                        for tipo in TipoRecursoPresupuesto.objects.filter(status=True, vigente=True).order_by('orden'):
                            convocatoriarecurso = ConvocatoriaTipoRecurso(
                                convocatoria=convocatoria,
                                tiporecurso=tipo,
                                secuencia=tipo.orden
                            )
                            convocatoriarecurso.save(request)

                        log(u'%s agregó convocatoria a proyectos de investigación: %s' % (persona, convocatoria), request, "add")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La convocatoria para proyectos de investigación ya ha sido ingresada", "showSwal": "True", "swalType": "warning"})
                else:
                    x = f.errors
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editconvocatoria':
            try:
                if 'archivoresolucion' in request.FILES:
                    archivo = request.FILES['archivoresolucion']
                    descripcionarchivo = 'Archivo resolución Ocas'

                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivoformatopresupuesto' in request.FILES:
                    archivo = request.FILES['archivoformatopresupuesto']
                    descripcionarchivo = 'Archivo presupuesto final'

                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['xls', 'xlsx'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivoconvocatoria' in request.FILES:
                    archivo = request.FILES['archivoconvocatoria']
                    descripcionarchivo = 'Archivo Bases Convocatoria'

                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                f = ConvocatoriaProyectoForm(request.POST, request.FILES)

                if f.is_valid():
                    if not ConvocatoriaProyecto.objects.filter(status=True, descripcion=f.cleaned_data['descripcion']).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.POST['id'])))

                        idsdetalletipo = request.POST.getlist('iddetalletipo[]')
                        minimos = request.POST.getlist('minimo[]')
                        maximos = request.POST.getlist('maximo[]')
                        porcentajes = request.POST.getlist('porcentaje[]')
                        tiposporcentajes = request.POST.getlist('tipoporc[]')
                        programas = json.loads(request.POST['lista_items2'])

                        # Actualizo la convocatoria
                        convocatoria.descripcion = f.cleaned_data['descripcion']
                        convocatoria.apertura = f.cleaned_data['apertura']
                        convocatoria.cierre = f.cleaned_data['cierre']
                        convocatoria.minimoaprobacion = f.cleaned_data['minimoaprobacion']
                        convocatoria.periodocidad = f.cleaned_data['periodocidad']
                        convocatoria.inicioevalint = f.cleaned_data['inicioevalint']
                        convocatoria.finevalint = f.cleaned_data['finevalint']
                        convocatoria.inicioreevalint = f.cleaned_data['inicioreevalint']
                        convocatoria.finreevalint = f.cleaned_data['finreevalint']
                        convocatoria.inicioevalext = f.cleaned_data['inicioevalext']
                        convocatoria.finevalext = f.cleaned_data['finevalext']
                        convocatoria.inicioreevalext = f.cleaned_data['inicioreevalext']
                        convocatoria.finreevalext = f.cleaned_data['finreevalext']
                        convocatoria.inicioselapro = f.cleaned_data['inicioselapro']
                        convocatoria.finselapro = f.cleaned_data['finselapro']
                        convocatoria.minintegranteu = f.cleaned_data['minintegranteu']
                        convocatoria.maxintegranteu = f.cleaned_data['maxintegranteu']
                        convocatoria.minintegrantee = f.cleaned_data['minintegrantee']
                        convocatoria.maxintegrantee = f.cleaned_data['maxintegrantee']

                        if 'archivoresolucion' in request.FILES:
                            archivo = request.FILES['archivoresolucion']
                            archivo._name = generar_nombre("resolucionocas", archivo._name)
                            convocatoria.archivoresolucion = archivo

                        if 'archivoformatopresupuesto' in request.FILES:
                            archivo = request.FILES['archivoformatopresupuesto']
                            archivo._name = generar_nombre("formatopresupuestofinal", archivo._name)
                            convocatoria.archivoformatopresupuesto = archivo

                        if 'archivoconvocatoria' in request.FILES:
                            archivo = request.FILES['archivoconvocatoria']
                            archivo._name = generar_nombre("convocatoria", archivo._name)
                            convocatoria.archivoconvocatoria = archivo

                        convocatoria.save(request)

                        # Consulto los ids originales de programas
                        idsorigenprograma = convocatoria.lista_ids_programasinvestigacion()
                        idsprograma = [programa['idprog'] for programa in programas]
                        excluidosprograma = [p for p in idsorigenprograma if p not in idsprograma]

                        # Actualizo los montos de financiamiento
                        for iddetalle, minimo, maximo, porcentaje, tipoporcentaje in zip(idsdetalletipo, minimos, maximos, porcentajes, tiposporcentajes):
                            montoconvocatoria = ConvocatoriaMontoFinanciamiento.objects.get(pk=iddetalle)
                            montoconvocatoria.minimo = minimo
                            montoconvocatoria.maximo = maximo
                            montoconvocatoria.porcentajecompra = porcentaje
                            montoconvocatoria.tipoporcentaje = tipoporcentaje
                            montoconvocatoria.save(request)

                        # Guardo los programas de investigación
                        for programa in programas:
                            if programa['idreg'] == 0:
                                programaconvocatoria = ConvocatoriaProgramaInvestigacion(
                                    convocatoria=convocatoria,
                                    programainvestigacion_id=programa['idprog']
                                )
                                programaconvocatoria.save(request)

                        # Borro los programas excluidos
                        if excluidosprograma:
                            for excluido in excluidosprograma:
                                programaconvocatoria = ConvocatoriaProgramaInvestigacion.objects.get(convocatoria=convocatoria, programainvestigacion_id=excluido)
                                programaconvocatoria.status = False
                                programaconvocatoria.save(request)

                        log(u'%s editó convocatoria a proyectos de investigación: %s' % (persona, convocatoria), request, "edit")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La convocatoria para proyectos de investigación ya ha sido ingresada", "showSwal": "True", "swalType": "warning"})
                else:
                    x = f.errors
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        # elif action == 'addrubrica':
        #     try:
        #         f = RubricaEvaluacionForm(request.POST)
        #
        #         if f.is_valid():
        #             convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.POST['idc'])))
        #             if not RubricaEvaluacion.objects.filter(status=True, convocatoria=convocatoria, categoria=f.cleaned_data['categoria'], descripcion=f.cleaned_data['descripcion']).exists():
        #                 totalvaloracion = convocatoria.total_valoracion_rubricas()
        #
        #                 if (totalvaloracion + f.cleaned_data['valoracion']) > 100:
        #                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La sumatoria de valoración de las rúbricas no debe ser mayor a 100", "showSwal": "True", "swalType": "warning"})
        #
        #                 descripcionesitems = request.POST.getlist('descripcion_item[]')  # Descripciones de los items
        #                 puntajesitems = request.POST.getlist('puntaje_item[]')  # Puntajes de los items
        #                 sumapuntaje = sum(int(puntaje) for puntaje in puntajesitems)
        #
        #                 if f.cleaned_data['valoracion'] != sumapuntaje:
        #                     return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La valoración de la rúbrica y la sumatoria de puntajes de los items deben ser iguales", "showSwal": "True", "swalType": "warning"})
        #
        #                 # Guardo la rúbrica de evaluación
        #                 rubricaevaluacion = RubricaEvaluacion(
        #                     convocatoria=convocatoria,
        #                     categoria=f.cleaned_data['categoria'],
        #                     numero=f.cleaned_data['numero'],
        #                     descripcion=f.cleaned_data['descripcion'],
        #                     valoracion=f.cleaned_data['valoracion']
        #                 )
        #                 rubricaevaluacion.save(request)
        #
        #                 # Guardo los items de la rúbrica
        #                 for item, puntaje in zip(descripcionesitems, puntajesitems):
        #                     itemrubrica = RubricaEvaluacionItem(
        #                         rubrica=rubricaevaluacion,
        #                         item=item.strip(),
        #                         puntajemaximo=puntaje.strip()
        #                     )
        #                     itemrubrica.save(request)
        #
        #                 log(u'%s agregó rúbrica de evaluación a convocatoria a proyectos de investigación: %s' % (persona, rubricaevaluacion), request, "add")
        #                 return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
        #             else:
        #                 return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La rúbrica de evaluación ya ha sido ingresada", "showSwal": "True", "swalType": "warning"})
        #         else:
        #             x = f.errors
        #             raise NameError('Error')
        #     except Exception as ex:
        #         msg = ex.__str__()
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addcriterioevaluacion':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar la convocatoria
                convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.POST['id'])))

                # Obtener los valores del formulario
                criterio = request.POST['criterio'].strip()
                indicador = request.POST['indicador'].strip()
                evidencia = request.POST['evidencia'].strip()
                porcentaje = Decimal(request.POST['porcentaje']).quantize(Decimal('.01'))

                # Validar que el criterio no se repita
                if RubricaEvaluacion.objects.values("id").filter(status=True, convocatoria=convocatoria, categoria=criterio).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El criterio de evaluación ya ha sido ingresado", "showSwal": "True", "swalType": "warning"})

                # Validar que el total no exceda a 100
                totalvaloracion = convocatoria.total_valoracion_rubricas()
                if (totalvaloracion + porcentaje) > 100:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La sumatoria de porcentaje de los criterios no debe ser mayor a 100", "showSwal": "True", "swalType": "warning"})

                # Obtener el número del criterio
                numero = numero_criterio_evaluacion(convocatoria)

                # Guardo el criterio de evaluación
                criterioevaluacion = RubricaEvaluacion(
                    convocatoria=convocatoria,
                    categoria=criterio,
                    numero=numero,
                    descripcion='',
                    evidencia=evidencia,
                    valoracion=porcentaje
                )
                criterioevaluacion.save(request)

                # Guardo el item del criterio
                indicadorcriterio = RubricaEvaluacionItem(
                    rubrica=criterioevaluacion,
                    item=indicador,
                    puntajemaximo=porcentaje
                )
                indicadorcriterio.save(request)

                log(f'{persona} agregó criterio de evaluación de propuesta de proyecto {criterioevaluacion}', request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito.", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        # elif action == 'editrubrica':
        #     try:
        #         f = RubricaEvaluacionForm(request.POST)
        #
        #         if f.is_valid():
        #             rubricaevaluacion = RubricaEvaluacion.objects.get(pk=int(encrypt(request.POST['id'])))
        #             convocatoria = rubricaevaluacion.convocatoria
        #             if not RubricaEvaluacion.objects.filter(status=True, convocatoria=convocatoria, categoria=f.cleaned_data['categoria'], descripcion=f.cleaned_data['descripcion']).exclude(pk=int(encrypt(request.POST['id']))).exists():
        #                 totalvaloracion = convocatoria.total_valoracion_rubricas() - rubricaevaluacion.valoracion
        #
        #                 if (totalvaloracion + f.cleaned_data['valoracion']) > 100:
        #                     return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La sumatoria de valoración de las rúbricas no debe ser mayor a 100", "showSwal": "True", "swalType": "warning"})
        #
        #                 idsitems = request.POST.getlist('idregistro[]')  # IDs de los items
        #                 descripcionesitems = request.POST.getlist('descripcion_item[]')  # Descripciones de los items
        #                 puntajesitems = request.POST.getlist('puntaje_item[]')  # Puntajes de los items
        #                 sumapuntaje = sum(int(puntaje) for puntaje in puntajesitems)
        #                 itemseliminados = json.loads(request.POST['lista_items1']) if 'lista_items1' in request.POST else []
        #
        #                 if f.cleaned_data['valoracion'] != sumapuntaje:
        #                     return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La valoración de la rúbrica y la sumatoria de puntajes de los items deben ser iguales", "showSwal": "True", "swalType": "warning"})
        #
        #                 # Actualizo la rúbrica de evaluación
        #                 rubricaevaluacion.categoria = f.cleaned_data['categoria']
        #                 rubricaevaluacion.numero = f.cleaned_data['numero']
        #                 rubricaevaluacion.descripcion = f.cleaned_data['descripcion']
        #                 rubricaevaluacion.valoracion = f.cleaned_data['valoracion']
        #                 rubricaevaluacion.save(request)
        #
        #                 # Guardo los items de la rúbrica
        #                 for idreg, item, puntaje in zip(idsitems, descripcionesitems, puntajesitems):
        #                     # Nuevo item
        #                     if int(idreg) == 0:
        #                         itemrubrica = RubricaEvaluacionItem(
        #                             rubrica=rubricaevaluacion,
        #                             item=item.strip(),
        #                             puntajemaximo=puntaje.strip()
        #                         )
        #                     else:
        #                         itemrubrica = RubricaEvaluacionItem.objects.get(pk=int(idreg))
        #                         itemrubrica.item = item.strip()
        #                         itemrubrica.puntajemaximo = puntaje.strip()
        #
        #                     itemrubrica.save(request)
        #
        #                 # Elimino los que se borraron del detalle
        #                 if itemseliminados:
        #                     for item in itemseliminados:
        #                         itemrubrica = RubricaEvaluacionItem.objects.get(pk=int(item['idreg']))
        #                         itemrubrica.status = False
        #                         itemrubrica.save(request)
        #
        #                 log(u'%s editó rúbrica de evaluación a convocatoria a proyectos de investigación: %s' % (persona, rubricaevaluacion), request, "edit")
        #                 return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
        #             else:
        #                 return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La rúbrica de evaluación ya ha sido ingresada", "showSwal": "True", "swalType": "warning"})
        #         else:
        #             x = f.errors
        #             raise NameError('Error')
        #     except Exception as ex:
        #         msg = ex.__str__()
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
        #
        elif action == 'editcriterioevaluacion':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el criterio de evluaicón
                criterioevaluacion = RubricaEvaluacion.objects.get(pk=int(encrypt(request.POST['id'])))
                convocatoria = criterioevaluacion.convocatoria

                # Obtener los valores del formulario
                criterio = request.POST['criterioe'].strip()
                indicador = request.POST['indicadore'].strip()
                evidencia = request.POST['evidenciae'].strip()
                porcentaje = Decimal(request.POST['porcentajee']).quantize(Decimal('.01'))

                # Validar que el criterio no se repita
                if RubricaEvaluacion.objects.values("id").filter(status=True, convocatoria=convocatoria, categoria=criterio).exclude(pk=int(encrypt(request.POST['id']))).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El criterio de evaluación ya ha sido ingresado", "showSwal": "True", "swalType": "warning"})

                # Validar que el total no exceda a 100
                totalvaloracion = convocatoria.total_valoracion_rubricas() - criterioevaluacion.valoracion
                if (totalvaloracion + porcentaje) > 100:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La sumatoria de porcentaje de los criterios no debe ser mayor a 100", "showSwal": "True", "swalType": "warning"})

                # Actualizo el criterio de evaluación
                criterioevaluacion.categoria = criterio
                criterioevaluacion.evidencia = evidencia
                criterioevaluacion.valoracion = porcentaje
                criterioevaluacion.save(request)

                # Obtener y actualizar el item del criterio
                indicadorcriterio = criterioevaluacion.indicador_rubrica()
                indicadorcriterio.item = indicador
                indicadorcriterio.puntajemaximo = porcentaje
                indicadorcriterio.save(request)

                log(f'{persona} editó criterio de evaluación de propuesta de proyecto {criterioevaluacion}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'consultamontomaximo':
            try:
                idtipoproy = request.POST['idtp']
                idconvocatoria = request.POST['idc']

                convocatoriamonto = ConvocatoriaMontoFinanciamiento.objects.get(convocatoria_id=idconvocatoria, categoria_id=idtipoproy)
                montomaximo = convocatoriamonto.maximo
                textoporcentaje = "{} {}% DEL MONTO TOTAL {}".format(convocatoriamonto.get_tipoporcentaje_display(), convocatoriamonto.porcentajecompra, '(OPCIONAL)' if convocatoriamonto.categoria.compraequipo == 2 else '')

                return JsonResponse({'result': 'ok', 'montomaximo': montomaximo, 'textoporcentaje': textoporcentaje})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. [%s]" % msg})

        elif action == 'asignarevaluador':
            try:
                f = EvaluadorProyectoInvestigacionForm(request.POST)

                evalinternos = json.loads(request.POST['lista_items1'])
                evalinternoseliminados = json.loads(request.POST['lista_items3']) if 'lista_items3' in request.POST else []
                evalexternos = json.loads(request.POST['lista_items2'])
                evalexternoseliminados = json.loads(request.POST['lista_items4']) if 'lista_items4' in request.POST else []

                proyectoinvestigacion = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Si el estado el proyecto es EVALUACIÓN INTERNA o EXTERNA ADICIONAL
                reevaluacionint = proyectoinvestigacion.estado.valor in [9, 34]
                reevaluacionext = proyectoinvestigacion.estado.valor in [12, 35]

                codigos_profesores = [item['idpe'] for item in evalinternos]
                codigos_externos = [item['idpe'] for item in evalexternos]

                # Verificar que se hayan agregado mínimo 2 evaluadores
                if proyectoinvestigacion.convocatoria.apertura.year >= 2022:
                    if len(codigos_profesores) < 2:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"Debe agregar mínimo 2 evaluadores internos", "showSwal": "True", "swalType": "warning"})

                    if len(codigos_externos) < 2:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"Debe agregar mínimo 2 evaluadores externos", "showSwal": "True", "swalType": "warning"})

                # Verificar que no sean integrantes del proyecto
                if proyectoinvestigacion.proyectoinvestigacionintegrante_set.filter(status=True, profesor_id__in=codigos_profesores).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"Los evaluadores internos no deben ser integrantes del proyecto", "showSwal": "True", "swalType": "warning"})

                if proyectoinvestigacion.proyectoinvestigacionintegrante_set.filter(status=True, externo_id__in=codigos_externos).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"Los evaluadores externos no deben ser integrantes del proyecto", "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    registro_nuevo = False if proyectoinvestigacion.tiene_asignado_evaluadores_propuesta_proyecto() else True

                    lista_evaluadores = []

                    # Guardo los evaluadores internos
                    for evaluador in evalinternos:
                        # Nuevo evaluador interno
                        if int(evaluador['idreg']) == 0:
                            # Obtengo persona
                            personaevaluador = Profesor.objects.get(pk=int(evaluador['idpe'])).persona

                            # Guardo evaluador
                            evaluadorinterno = ProyectoInvestigacionEvaluador(
                                proyecto=proyectoinvestigacion,
                                tipo=1,
                                persona=personaevaluador,
                                tipoproyecto=1,
                                notificado=False,
                                reevaluacion=reevaluacionint
                            )
                            evaluadorinterno.save(request)

                            # Para enviar el e-mail al evaluador
                            evaluador = {
                                "nombre": personaevaluador.nombre_completo_inverso(),
                                "saludo": 'Estimada' if personaevaluador.sexo_id == 1 else 'Estimado',
                                "direccionemail": personaevaluador.lista_emails_envio(),
                                "inicioeval": proyectoinvestigacion.convocatoria.inicioevalint,
                                "fineval": proyectoinvestigacion.convocatoria.finevalint,
                                "tipo": "EVALUADOR INTERNO"
                            }
                            lista_evaluadores.append(evaluador)

                    # Elimino los que se borraron del detalle
                    if evalinternoseliminados:
                        for evaluador in evalinternoseliminados:
                            evaluadorinterno = ProyectoInvestigacionEvaluador.objects.get(pk=int(evaluador['idreg']))
                            evaluadorinterno.status = False
                            evaluadorinterno.save(request)

                    # Guardo los evaluadores externos
                    for evaluador in evalexternos:
                        # Nuevo evaluador externo
                        if int(evaluador['idreg']) == 0:
                            # Obtengo persona
                            personaevaluador = Externo.objects.get(pk=int(evaluador['idpe'])).persona
                            # Guardo evaluador
                            evaluadorexterno = ProyectoInvestigacionEvaluador(
                                proyecto=proyectoinvestigacion,
                                tipo=2,
                                persona=personaevaluador,
                                tipoproyecto=1,
                                notificado=False,
                                reevaluacion=reevaluacionext
                            )
                            evaluadorexterno.save(request)

                            # Para enviar el e-mail al evaluador
                            evaluador = {
                                "nombre": personaevaluador.nombre_completo_inverso(),
                                "saludo": 'Estimada' if personaevaluador.sexo_id == 1 else 'Estimado',
                                "direccionemail": personaevaluador.lista_emails_envio(),
                                "inicioeval": proyectoinvestigacion.convocatoria.inicioevalext,
                                "fineval": proyectoinvestigacion.convocatoria.finevalext,
                                "tipo": "EVALUADOR EXTERNO"
                            }
                            lista_evaluadores.append(evaluador)

                    # Elimino los que se borraron del detalle
                    if evalexternoseliminados:
                        for evaluador in evalexternoseliminados:
                            evaluadorexterno = ProyectoInvestigacionEvaluador.objects.get(pk=int(evaluador['idreg']))
                            evaluadorexterno.status = False
                            evaluadorexterno.save(request)

                    if registro_nuevo:
                        # Actualizo el estado del proyecto a EVALUADORES ASIGNADOS
                        mensaje = "Registro guardado con éxito"
                        estado = obtener_estado_solicitud(3, 6)
                        proyectoinvestigacion.estado = estado
                        proyectoinvestigacion.save(request)

                        # Creo el recorrido del proyecto
                        recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                                   fecha=datetime.now().date(),
                                                                   observacion='EVALUADORES ASIGNADOS',
                                                                   estado=estado
                                                                   )
                        recorrido.save(request)

                        log(u'% agregó evaluadores a proyectos de investigación: %s' % (persona, proyectoinvestigacion), request, "add")
                    else:
                        mensaje = "Registro actualizado con éxito"
                        log(u'%s editó evaluadores de proyectos de investigación: %s' % (persona, proyectoinvestigacion), request, "edit")

                    # Notificar por e-mail
                    # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                    listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                    fechaenvio = datetime.now().date()
                    horaenvio = datetime.now().time()
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                    for evaluador in lista_evaluadores:
                        lista_email_envio = evaluador['direccionemail']

                        tituloemail = "Designación Evaluador de Propuesta de Proyecto de Investigación"
                        tiponotificacion = "EVALPROPASIG"

                        lista_archivos_adjuntos = []
                        lista_email_cco = []
                        titulo = "Proyectos de Investigación"

                        send_html_mail(tituloemail,
                                       "emails/propuestaproyectoinvestigacion.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'titulo': titulo,
                                        'fecha': fechaenvio,
                                        'hora': horaenvio,
                                        'tiponotificacion': tiponotificacion,
                                        'saludo': evaluador['saludo'],
                                        'nombrepersona': evaluador['nombre'],
                                        'proyecto': proyectoinvestigacion,
                                        'tipoevaluador': evaluador['tipo'],
                                        'inicioeval': evaluador['inicioeval'],
                                        'fineval': evaluador['fineval']
                                        },
                                       lista_email_envio,  # Destinatarioa
                                       lista_email_cco,  # Copia oculta
                                       lista_archivos_adjuntos,  # Adjunto(s)
                                       cuenta=CUENTAS_CORREOS[cuenta][1]
                                       )

                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": mensaje, "showSwal": True})
                else:
                    x = f.errors
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addresolucion':
            try:
                archivo = request.FILES['archivo']
                descripcionarchivo = 'Archivo de la resolción'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                f = ResolucionAprobacionProyectoForm(request.POST, request.FILES)

                if f.is_valid():
                    convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.POST['idc'])))

                    archivo._name = generar_nombre("resolucionaprobacionocas", archivo._name)

                    # Guardo resolución de aprobación
                    resolucionaprobacion = ConvocatoriaResolucionAprobacionProyecto(
                        convocatoria=convocatoria,
                        fecha=f.cleaned_data['fecha'],
                        numero=f.cleaned_data['numero'],
                        archivo=archivo,
                        resuelve=f.cleaned_data['resuelve'],
                        fechanotificaaprobacion=f.cleaned_data['fechanotificaaprobacion']
                    )
                    resolucionaprobacion.save(request)

                    log(u'Agregó resolución de aprobación de proyectos de la convocatoria: %s' % convocatoria, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    x = f.errors
                    return JsonResponse({"result": "bad", "mensaje": u"Ingrese valor del campo resuelve"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'editresolucion':
            try:
                if 'archivo' in request.FILES:
                    archivo = request.FILES['archivo']
                    descripcionarchivo = 'Archivo de la resolción'

                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                f = ResolucionAprobacionProyectoForm(request.POST, request.FILES)

                if f.is_valid():
                    resolucionaprobacion = ConvocatoriaResolucionAprobacionProyecto.objects.get(pk=int(encrypt(request.POST['id'])))

                    # Actualizo resolución de aprobación
                    resolucionaprobacion.fecha = f.cleaned_data['fecha']
                    resolucionaprobacion.numero = f.cleaned_data['numero']
                    resolucionaprobacion.resuelve = f.cleaned_data['resuelve']
                    resolucionaprobacion.fechanotificaaprobacion = f.cleaned_data['fechanotificaaprobacion']

                    if 'archivo' in request.FILES:
                        archivo._name = generar_nombre("resolucionaprobacionocas", archivo._name)
                        resolucionaprobacion.archivo = archivo

                    resolucionaprobacion.save(request)
                    log(u'Editó resolución de aprobación de proyectos de la convocatoria: %s' % resolucionaprobacion.convocatoria, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    x = f.errors
                    # raise NameError('Error')
                    return JsonResponse({"result": "bad", "mensaje": u"Ingrese valor del campo resuelve"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'habilitaredicion':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto el proyecto
                proyectoinvestigacion = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Obtengo el registro del estado EN EDICIÓN
                estadopropuesta = obtener_estado_solicitud(3, 1)

                # Actualizo el proyecto
                proyectoinvestigacion.estado = estadopropuesta
                proyectoinvestigacion.documentogenerado = False
                proyectoinvestigacion.registrado = False
                proyectoinvestigacion.save(request)

                # Creo el recorrido del proyecto
                recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                           fecha=datetime.now().date(),
                                                           observacion='PROPUESTA DE PROYECTO EN EDICIÓN',
                                                           estado=estadopropuesta
                                                           )
                recorrido.save(request)

                log(u'%s habilitó edición de la propuesta de proyecto de investigación: %s' % (persona, proyectoinvestigacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addpropuestaproyectoexterno':
            try:
                if not 'idc' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivodocumento = request.FILES['archivodocumento']
                descripcionarchivo = 'Archivo Documento Proyecto'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivodocumento, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Verificar que el código no hay sido ingresado
                if ProyectoInvestigacion.objects.values("id").filter(codigo=request.POST['codigo'].strip(), convocatoria__tipo=2, status=True).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El código del proyecto ya ha sido ingresado", "showSwal": "True", "swalType": "warning"})

                # Verificar que el proyecto no exista
                if ProyectoInvestigacion.objects.filter(titulo=request.POST['titulo'].strip(), convocatoria__tipo=2, status=True).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La propuesta de proyecto de investigación ya ha sido ingresada", "showSwal": "True", "swalType": "warning"})

                # datetime.strptime(request.POST['fechaatencion'], '%Y-%m-%d').date()
                if null_to_decimal(request.POST['montounemi'], 2) > null_to_decimal(request.POST['montomaximounemi'], 2):
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El valor del campo Monto UNEMI debe ser menor o igual a Máximo a financiar", "showSwal": "True", "swalType": "warning"})

                archivodocumento._name = generar_nombre("documento", archivodocumento._name)

                if request.POST['existeinscoejecutora'] == '1':
                    # Obtiene los valores de los arreglos del detalle de instituciones
                    nombresi = request.POST.getlist('nombreinscoejec[]')
                    representantesi = request.POST.getlist('representanteinscoejec[]')
                    cedulasi = request.POST.getlist('cedulainscoejec[]')
                    emailsi = request.POST.getlist('emailinscoejec[]')
                    telefonosi = request.POST.getlist('telefonoinscoejec[]')
                    faxesi = request.POST.getlist('faxinscoejec[]')
                    direccionesi = request.POST.getlist('direccioninscoejec[]')
                    websi = request.POST.getlist('webinscoejec[]')

                # Consulto la convocatoria
                convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.POST['idc'])))

                # Consulto el estado que voy a asignar: REGISTRADO, VERIFICADO
                estado1 = obtener_estado_solicitud(3, 2)
                estado2 = obtener_estado_solicitud(3, 3)

                # Consulto al director de proyecto
                profesordirector = Profesor.objects.get(pk=request.POST['profesor']) if 'profesor' in request.POST else None

                # Guarda el proyecto
                proyectoinvestigacion = ProyectoInvestigacion(
                    convocatoria=convocatoria,
                    profesor=profesordirector,
                    categoria=None,
                    categoria2_id=request.POST['categoria'],
                    codigo=request.POST['codigo'],
                    titulo=request.POST['titulo'].strip(),
                    areaconocimiento_id=request.POST['areaconocimiento'],
                    subareaconocimiento_id=request.POST['subareaconocimiento'],
                    subareaespecificaconocimiento_id=request.POST['subareaespecificaconocimiento'],
                    lineainvestigacion_id=request.POST['lineainvestigacion'],
                    programainvestigacion_id=request.POST['programainvestigacion'],
                    industriapriorizada_id=request.POST['industriapriorizada'],
                    requiereconvenio='requiereconvenio' in request.POST,
                    especificaconvenio=request.POST['especificaconvenio'].strip(),
                    requierepermiso='requierepermiso' in request.POST,
                    especificapermiso=request.POST['especificapermiso'].strip(),
                    tiempomes=request.POST['tiempomes'],
                    montototal=request.POST['montototal'],
                    montounemi=request.POST['montounemi'],
                    montootrafuente=request.POST['montootrafuente'],
                    tipocobertura=request.POST['tipocobertura'],
                    grupoinvestigacion_id=request.POST['grupoinvestigacion'],
                    documentogenerado=True,
                    archivodocumento=archivodocumento,
                    registrado=True,
                    verificado=1,
                    estado=estado2
                )

                proyectoinvestigacion.save(request)

                # Guardo sublineas de investigacion
                for subli in request.POST.getlist('sublineainvestigacion'):
                    sublinea = SubLineaInvestigacion.objects.get(pk=subli)
                    proyectoinvestigacion.sublineainvestigacion.add(sublinea)

                proyectoinvestigacion.save(request)

                tipocobertura = int(request.POST['tipocobertura'])
                # Si tipo cobertura es zonal guardo las zonas
                if tipocobertura == 3:
                    for zona in request.POST.getlist('zonas'):
                        zonaplanificacion = ZonaPlanificacion.objects.get(pk=zona)
                        proyectoinvestigacion.zonas.add(zonaplanificacion)

                    proyectoinvestigacion.save(request)
                # Si es provincial guardo las provincias
                elif tipocobertura == 4:
                    for prov in request.POST.getlist('provincias'):
                        provincia = Provincia.objects.get(pk=prov)
                        proyectoinvestigacion.provincias.add(provincia)

                    proyectoinvestigacion.save(request)
                # Si es local guardo provincia y los cantones
                elif tipocobertura == 5:
                    proyectoinvestigacion.provincia_id = request.POST['provincia']
                    for cant in request.POST.getlist('canton'):
                        canton = Canton.objects.get(pk=cant)
                        proyectoinvestigacion.canton.add(canton)

                    proyectoinvestigacion.requiereparroquia = 'requiereparroquia' in request.POST
                    proyectoinvestigacion.parroquia = request.POST['parroquia'].strip()
                    proyectoinvestigacion.save(request)

                # Guardo institución participante ejecutora 1
                institucionproyecto = ProyectoInvestigacionInstitucion(
                    proyecto=proyectoinvestigacion,
                    tipo=1,
                    representante=request.POST['representanteinsejec'],
                    cedula=request.POST['cedulainsejec'],
                    telefono=request.POST['telefonoinsejec'],
                    fax=request.POST['faxinsejec'],
                    email=request.POST['emailinsejec'],
                    direccion=request.POST['direccioninsejec'],
                    paginaweb=request.POST['paginawebinsejec'],
                    nombre=request.POST['nombreinsejec'],
                    esunemi=True
                )
                institucionproyecto.save(request)

                # Guardo institución participante ejecutora 2
                institucionproyecto = ProyectoInvestigacionInstitucion(
                    proyecto=proyectoinvestigacion,
                    tipo=1,
                    representante=request.POST['representanteinsejec2'],
                    cedula=request.POST['cedulainsejec2'],
                    telefono=request.POST['telefonoinsejec2'],
                    fax=request.POST['faxinsejec2'],
                    email=request.POST['emailinsejec2'],
                    direccion=request.POST['direccioninsejec2'],
                    paginaweb=request.POST['paginawebinsejec2'],
                    nombre=request.POST['nombreinsejec2'],
                    esunemi=False
                )
                institucionproyecto.save(request)

                # Guardo institución participante co-ejecutora en caso de haber marcado la casilla
                if request.POST['existeinscoejecutora'] == '1':
                    for nombre, representante, cedula, email, telefono, fax, direccion, web in zip(nombresi, representantesi, cedulasi, emailsi, telefonosi, faxesi, direccionesi, websi):
                        institucionproyecto = ProyectoInvestigacionInstitucion(
                            proyecto=proyectoinvestigacion,
                            tipo=2,
                            representante=representante,
                            cedula=cedula,
                            telefono=telefono,
                            fax=fax,
                            email=email,
                            direccion=direccion,
                            paginaweb=web,
                            nombre=nombre
                        )
                        institucionproyecto.save(request)

                # Guardo un integrante del proyecto: Director del proyecto
                if profesordirector:
                    integranteproyecto = ProyectoInvestigacionIntegrante(
                        proyecto=proyectoinvestigacion,
                        funcion=1,
                        tipo=1,
                        persona=profesordirector.persona,
                        profesor=profesordirector,
                        estadoacreditado=2
                    )
                    integranteproyecto.save(request)

                # Creo el recorrido del proyecto
                recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                           fecha=datetime.now().date(),
                                                           observacion=estado1.observacion,
                                                           estado=estado1
                                                           )
                recorrido.save(request)

                recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                           fecha=datetime.now().date(),
                                                           observacion=estado2.observacion,
                                                           estado=estado2
                                                           )
                recorrido.save(request)

                log(u'%s agregó datos generales de propuesta de proyecto de investigación: %s' % (persona, proyectoinvestigacion), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editpropuestaproyectoexterno':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivodocumento = None
                if 'archivodocumento' in request.FILES:
                    archivodocumento = request.FILES['archivodocumento']
                    descripcionarchivo = 'Archivo Documento Proyecto'

                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivodocumento, ['PDF'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Verificar que el código no hay sido ingresado
                if ProyectoInvestigacion.objects.values("id").filter(codigo=request.POST['codigo'].strip(), convocatoria__tipo=2, status=True).exclude(pk=int(encrypt(request.POST['id']))).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El código del proyecto ya ha sido ingresado", "showSwal": "True", "swalType": "warning"})

                # Verificar que el proyecto no exista
                if ProyectoInvestigacion.objects.filter(titulo=request.POST['titulo'].strip(), convocatoria__tipo=2, status=True).exclude(pk=int(encrypt(request.POST['id']))).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La propuesta de proyecto de investigación ya ha sido ingresada", "showSwal": "True", "swalType": "warning"})

                if null_to_decimal(request.POST['montounemi'], 2) > null_to_decimal(request.POST['montomaximounemi'], 2):
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El valor del campo Monto UNEMI debe ser menor o igual a Máximo a financiar", "showSwal": "True", "swalType": "warning"})

                if request.POST['existeinscoejecutora'] == '1':
                    # Obtiene los valores de los arreglos del detalle de instituciones
                    idsi = request.POST.getlist('idinstitucion[]')
                    nombresi = request.POST.getlist('nombreinscoejec[]')
                    representantesi = request.POST.getlist('representanteinscoejec[]')
                    cedulasi = request.POST.getlist('cedulainscoejec[]')
                    emailsi = request.POST.getlist('emailinscoejec[]')
                    telefonosi = request.POST.getlist('telefonoinscoejec[]')
                    faxesi = request.POST.getlist('faxinscoejec[]')
                    direccionesi = request.POST.getlist('direccioninscoejec[]')
                    websi = request.POST.getlist('webinscoejec[]')

                institucioneseliminadas = json.loads(request.POST['lista_items1'])

                # Consulto el proyecto
                proyectoinvestigacion = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Consulto al director de proyecto
                profesordirector = Profesor.objects.get(pk=request.POST['profesor']) if 'profesor' in request.POST else None
                
                # Actualizar los datos generales
                proyectoinvestigacion.profesor = profesordirector
                proyectoinvestigacion.categoria2_id = request.POST['categoria']
                proyectoinvestigacion.codigo = request.POST['codigo'].strip()
                proyectoinvestigacion.titulo = request.POST['titulo'].strip()
                proyectoinvestigacion.areaconocimiento_id = request.POST['areaconocimiento']
                proyectoinvestigacion.subareaconocimiento_id = request.POST['subareaconocimiento']
                proyectoinvestigacion.subareaespecificaconocimiento_id = request.POST['subareaespecificaconocimiento']
                proyectoinvestigacion.lineainvestigacion_id = request.POST['lineainvestigacion']
                proyectoinvestigacion.programainvestigacion_id = request.POST['programainvestigacion']
                proyectoinvestigacion.industriapriorizada_id = request.POST['industriapriorizada']
                proyectoinvestigacion.requiereconvenio = 'requiereconvenio' in request.POST
                proyectoinvestigacion.especificaconvenio = request.POST['especificaconvenio'].strip()
                proyectoinvestigacion.requierepermiso = 'requierepermiso' in request.POST
                proyectoinvestigacion.especificapermiso = request.POST['especificapermiso'].strip()
                proyectoinvestigacion.tiempomes = request.POST['tiempomes']
                proyectoinvestigacion.montototal = request.POST['montototal']
                proyectoinvestigacion.montounemi = request.POST['montounemi']
                proyectoinvestigacion.montootrafuente = request.POST['montootrafuente']
                proyectoinvestigacion.tipocobertura = request.POST['tipocobertura']
                proyectoinvestigacion.grupoinvestigacion_id = request.POST['grupoinvestigacion']

                if archivodocumento:
                    archivodocumento._name = generar_nombre("documento", archivodocumento._name)
                    archivodocumento = archivodocumento

                # proyectoinvestigacion.save(request)

                # Guardo sublineas de investigacion
                proyectoinvestigacion.sublineainvestigacion.clear()
                for subli in request.POST.getlist('sublineainvestigacion'):
                    sublinea = SubLineaInvestigacion.objects.get(pk=subli)
                    proyectoinvestigacion.sublineainvestigacion.add(sublinea)

                # proyectoinvestigacion.save(request)

                tipocobertura = int(request.POST['tipocobertura'])
                # Si tipo cobertura es zonal guardo las zonas
                if tipocobertura == 3:
                    proyectoinvestigacion.zonas.clear()
                    for zona in request.POST.getlist('zonas'):
                        zonaplanificacion = ZonaPlanificacion.objects.get(pk=zona)
                        proyectoinvestigacion.zonas.add(zonaplanificacion)

                    # proyectoinvestigacion.save(request)
                # Si es provincial guardo las provincias
                elif tipocobertura == 4:
                    proyectoinvestigacion.provincias.clear()
                    for prov in request.POST.getlist('provincias'):
                        provincia = Provincia.objects.get(pk=prov)
                        proyectoinvestigacion.provincias.add(provincia)

                    # proyectoinvestigacion.save(request)
                # Si es local guardo provincia y los cantones
                elif tipocobertura == 5:
                    proyectoinvestigacion.provincia_id = request.POST['provincia']
                    proyectoinvestigacion.canton.clear()
                    for cant in request.POST.getlist('canton'):
                        canton = Canton.objects.get(pk=cant)
                        proyectoinvestigacion.canton.add(canton)

                    proyectoinvestigacion.requiereparroquia = 'requiereparroquia' in request.POST
                    proyectoinvestigacion.parroquia = request.POST['parroquia'].strip()
                    # proyectoinvestigacion.save(request)

                proyectoinvestigacion.save(request)

                # Elimino las instituciones co ejecutoras
                for institucioneli in institucioneseliminadas:
                    institucioneli = ProyectoInvestigacionInstitucion.objects.get(pk=int(institucioneli['idinstitucion']))
                    institucioneli.status = False
                    institucioneli.save(request)

                # Guardo institución participante co-ejecutora en caso de haber marcado la casilla
                if request.POST['existeinscoejecutora'] == '1':
                    for id, nombre, representante, cedula, email, telefono, fax, direccion, web in zip(idsi, nombresi, representantesi, cedulasi, emailsi, telefonosi, faxesi, direccionesi, websi):
                        # Nueva institución
                        if int(id) == 0:
                            institucionproyecto = ProyectoInvestigacionInstitucion(
                                proyecto=proyectoinvestigacion,
                                tipo=2,
                                representante=representante,
                                cedula=cedula,
                                telefono=telefono,
                                fax=fax,
                                email=email,
                                direccion=direccion,
                                paginaweb=web,
                                nombre=nombre
                            )
                        else:
                            institucionproyecto = ProyectoInvestigacionInstitucion.objects.get(pk=int(id))
                            institucionproyecto.representante = representante
                            institucionproyecto.cedula = cedula
                            institucionproyecto.telefono = telefono
                            institucionproyecto.fax = fax
                            institucionproyecto.email = email
                            institucionproyecto.direccion = direccion
                            institucionproyecto.paginaweb = web
                            institucionproyecto.nombre = nombre

                        institucionproyecto.save(request)

                # Actualizo un integrante del proyecto: Director del proyecto
                if profesordirector:
                    if not ProyectoInvestigacionIntegrante.objects.values("id").filter(proyecto=proyectoinvestigacion, funcion=1, tipo=1, status=True).exists():
                        integranteproyecto = ProyectoInvestigacionIntegrante(
                            proyecto=proyectoinvestigacion,
                            funcion=1,
                            tipo=1,
                            persona=profesordirector.persona,
                            profesor=profesordirector,
                            estadoacreditado=2
                        )
                        integranteproyecto.save(request)
                    else:
                        ProyectoInvestigacionIntegrante.objects.filter(proyecto=proyectoinvestigacion, funcion=1, tipo=1, status=True).update(persona=profesordirector.persona, profesor=profesordirector)
                else:
                    ProyectoInvestigacionIntegrante.objects.filter(proyecto=proyectoinvestigacion, funcion=1, tipo=1, status=True).update(status=False)

                log(u'%s editó datos generales de propuesta de proyecto de investigación: %s' % (persona, proyectoinvestigacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addintegranteproyecto':
            try:
                if not 'idproyecto' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                proyectoinvestigacion = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idproyecto'])))
                convocatoria = proyectoinvestigacion.convocatoria
                tipoconvocatoria = convocatoria.tipo

                tipopersona = int(request.POST['tipopersona'])
                personaintegrante = int(request.POST['persona_select2'])
                if 'funcionpersona' in request.POST:
                    funcionpersona = int(request.POST['funcionpersona'])
                else:
                    # Si es estudiante
                    if tipopersona == 2:
                        funcionpersona = 4 # AYUDANTE DE INVESTIGACION
                    elif tipopersona == 3: # Si es administrativo
                        funcionpersona = 3 # INVESTIGADOR ASOCIADO
                    else: # externo
                        funcionpersona = 5  # INVESTIGADOR COLABORADOR

                # Validar el límite de integrantes
                if tipoconvocatoria == 1:
                    if funcionpersona in [2, 3]:
                        if proyectoinvestigacion.cantidad_integrantes_unemi() >= convocatoria.maxintegranteu:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se pueden agregar más integrantes <b>UNEMI</b> al proyecto", "showSwal": "True", "swalType": "warning"})
                    elif funcionpersona == 5:
                        if proyectoinvestigacion.cantidad_integrantes_externos() >= convocatoria.maxintegrantee:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se pueden agregar más integrantes <b>EXTERNOS</b> al proyecto", "showSwal": "True", "swalType": "warning"})
                else:
                    if funcionpersona == 1:
                        if proyectoinvestigacion.cantidad_directores() == 2:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se pueden agregar más integrantes con el rol de DIRECTOR", "showSwal": "True", "swalType": "warning"})

                if tipopersona == 1:
                    persona_id = Profesor.objects.get(pk=personaintegrante).persona.id
                elif tipopersona == 2:
                    persona_id = Inscripcion.objects.get(pk=personaintegrante).persona.id
                elif tipopersona == 3:
                    persona_id = Administrativo.objects.get(pk=personaintegrante).persona.id
                else:
                    persona_id = Externo.objects.get(pk=personaintegrante).persona.id

                # Verificar que no haya sido registrado previamente
                if proyectoinvestigacion.proyectoinvestigacionintegrante_set.values("id").filter(status=True, persona_id=persona_id).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La persona ya consta como integrante del proyecto", "showSwal": "True", "swalType": "warning"})

                # Verifico que la persona no sea el director del proyecto
                if proyectoinvestigacion.proyectoinvestigacionintegrante_set.values("id").filter(status=True, persona_id=persona_id, funcion=1).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se puede agregar al integrante debido a que consta como <b>DIRECTOR</b>", "showSwal": "True", "swalType": "warning"})

                # Si el rol es co-director validar que otro integrante no cumpla ese mismo rol
                if proyectoinvestigacion.proyectoinvestigacionintegrante_set.values("id").filter(status=True, persona_id=persona_id, funcion=2, tiporegistro__in=[1, 3, 4]).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Ya existe otro integrante del proyecto con el rol de <b>CO-DIRECTOR</b>", "showSwal": "True", "swalType": "warning"})

                # Si es función de co-director validar que no esté participando en otro proyecto con esta función
                if funcionpersona == 2:
                    if ProyectoInvestigacionIntegrante.objects.values("id").filter(status=True, persona_id=persona_id, funcion=funcionpersona).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La persona ya consta como co-director en otro proyecto", "showSwal": "True", "swalType": "warning"})

                # # validar que no esté participando en mas de 1 proyecto
                # if ProyectoInvestigacionIntegrante.objects.values("id").filter(status=True, persona_id=persona_id).count() > 1:
                #     return JsonResponse({"result": "bad", "mensaje": u"La persona puede participar máximo en 1 proyecto"})

                # Guarda el integrante del proyecto
                integranteproyecto = ProyectoInvestigacionIntegrante(
                    proyecto=proyectoinvestigacion,
                    funcion=funcionpersona,
                    tipo=tipopersona,
                    persona_id=persona_id,
                    profesor_id=personaintegrante if tipopersona == 1 else None,
                    inscripcion_id=personaintegrante if tipopersona == 2 else None,
                    administrativo_id=personaintegrante if tipopersona == 3 else None,
                    externo_id=personaintegrante if tipopersona == 4 else None,
                    estadoacreditado=1 if funcionpersona in [1 ,2] else 4
                )
                integranteproyecto.save(request)

                log(u'% agregó integrante a proyecto de investigación: %s - %s' % (persona, proyectoinvestigacion, integranteproyecto), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addexterno':
            try:
                if not 'idp' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                f = ExternoForm(request.POST)

                if f.is_valid():
                    if not f.cleaned_data['cedula'] and not f.cleaned_data['pasaporte']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Ingrese número de cédula o pasaporte", "showSwal": "True", "swalType": "warning"})

                    # Verifica si existe la persona
                    if f.cleaned_data['cedula']:
                        if Persona.objects.values('id').filter(Q(cedula=f.cleaned_data['cedula'])|Q(pasaporte=f.cleaned_data['cedula']), status=True).exists():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La persona ya está registrada en la base de datos", "showSwal": "True", "swalType": "warning"})

                    if f.cleaned_data['pasaporte']:
                        if Persona.objects.values('id').filter(Q(cedula=f.cleaned_data['pasaporte'])|Q(pasaporte=f.cleaned_data['pasaporte']), status=True).exists():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La persona ya está registrada en la base de datos", "showSwal": "True", "swalType": "warning"})

                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idp'])))

                    # Si es de convocatoria externa
                    if proyecto.convocatoria.tipo == 2 and int(f.cleaned_data['funcionproyecto']) == 1:
                        if proyecto.cantidad_directores() == 2:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se pueden agregar más integrantes con el rol de DIRECTOR", "showSwal": "True", "swalType": "warning"})

                    # Validar el limite de integrantes externos para el proyecto
                    if proyecto.cantidad_integrantes_externos() >= proyecto.convocatoria.maxintegrantee:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se pueden agregar más integrantes EXTERNOS al proyecto", "showSwal": "True", "swalType": "warning"})

                    funcion = int(f.cleaned_data['funcionproyecto']) if f.cleaned_data['funcionproyecto'] else 5

                    # Guardo la persona
                    personaexterna = Persona(
                        nombres=f.cleaned_data['nombres'],
                        apellido1=f.cleaned_data['apellido1'],
                        apellido2=f.cleaned_data['apellido2'],
                        cedula=f.cleaned_data['cedula'],
                        pasaporte=f.cleaned_data['pasaporte'],
                        nacimiento=f.cleaned_data['nacimiento'],
                        sexo=f.cleaned_data['sexo'],
                        nacionalidad=f.cleaned_data['nacionalidad'],
                        email=f.cleaned_data['email'],
                        telefono=f.cleaned_data['telefono']
                    )
                    personaexterna.save(request)

                    # Guardo externo
                    externo = Externo(
                        persona=personaexterna,
                        nombrecomercial='',
                        institucionlabora=f.cleaned_data['institucionlabora'],
                        cargodesempena=f.cleaned_data['cargodesempena']
                    )
                    externo.save(request)

                    personaexterna.crear_perfil(externo=externo)
                    personaexterna.mi_perfil()
                    log(u'Agregó persona externa: %s' % (personaexterna), request, "add")

                    # Asigno la persona externa al proyecto con la función que cumple
                    integranteproyecto = ProyectoInvestigacionIntegrante(
                        proyecto=proyecto,
                        funcion=funcion,
                        tipo=4,
                        persona_id=personaexterna.id,
                        profesor_id=None,
                        inscripcion_id=None,
                        administrativo_id=None,
                        externo_id=externo.id,
                        estadoacreditado=2 if funcion in [1, 2] else  4
                    )
                    integranteproyecto.save(request)

                    log(u'%s agregó integrante al proyecto: %s - %s' % (persona, proyecto, personaexterna), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    x = f.errors
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editrolintegrante':
            try:
                if not 'idproyecto' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                integranteproyecto = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.POST['idi'])))
                proyectoinvestigacion = integranteproyecto.proyecto
                funcionpersona = int(request.POST['funcionpersona'])

                # Si es de convocatoria externa
                if proyectoinvestigacion.convocatoria.tipo == 2 and funcionpersona == 1:
                    if proyectoinvestigacion.cantidad_directores() == 2:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se pueden agregar más integrantes con el rol de DIRECTOR", "showSwal": "True", "swalType": "warning"})

                # Si es función de co-director validar que otro integrante no sea co-director y/o no esté participando en otro proyecto con esta función
                if funcionpersona == 2:
                    if proyectoinvestigacion.proyectoinvestigacionintegrante_set.values("id").filter(status=True, funcion=2, tiporegistro__in=[1, 3, 4]).exclude(persona_id=integranteproyecto.persona_id).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Ya existe otro integrante del proyecto con el rol de <b>CO-DIRECTOR</b>", "showSwal": "True", "swalType": "warning"})

                    if ProyectoInvestigacionIntegrante.objects.values("id").filter(status=True, persona_id=integranteproyecto.persona_id, funcion=funcionpersona).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La persona ya consta como <b>CO-DIRECTOR</b> en otro proyecto", "showSwal": "True", "swalType": "warning"})

                integranteproyecto.funcion = funcionpersona
                integranteproyecto.estadoacreditado = 2 if funcionpersona in [1, 2] else 4
                integranteproyecto.save(request)

                log(u'%s editó rol del integrante a proyecto de investigación: %s - %s' % (persona, integranteproyecto.proyecto, integranteproyecto), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'delintegranteproyecto':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                integrante = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.POST['id'])))
                integrante.status = False
                integrante.save(request)

                log(u'%s eliminó integrante de proyecto de investigación [ %s ]' % (persona, integrante), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al eliminar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editexterno':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                f = ExternoForm(request.POST)

                if f.is_valid():
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idp'])))

                    # Actualizo datos de la persona
                    personaexterna = Persona.objects.get(pk=int(encrypt(request.POST['idper'])))
                    personaexterna.nacimiento = f.cleaned_data['nacimiento']
                    personaexterna.sexo = f.cleaned_data['sexo']
                    personaexterna.nacionalidad = f.cleaned_data['nacionalidad'].strip().upper()
                    personaexterna.email = f.cleaned_data['email'].strip().lower()
                    personaexterna.telefono = f.cleaned_data['telefono'].strip()
                    personaexterna.save(request)


                    # Actualizo externo
                    integranteproyecto = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.POST['id'])))
                    externo = integranteproyecto.externo
                    externo.institucionlabora = f.cleaned_data['institucionlabora'].strip().upper()
                    externo.cargodesempena = f.cleaned_data['cargodesempena'].strip().upper()
                    externo.save(request)

                    log(u'%s editó persona externa: %s' % (persona, personaexterna), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    x = f.errors
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editcontenidoproyecto':
            try:
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                objetivoseliminados = json.loads(request.POST['lista_items1'])
                resultadoseliminados = json.loads(request.POST['lista_items2'])
                referenciaseliminadas = json.loads(request.POST['lista_items3'])

                # Validar las cantidades de palabras
                # LIMITE_PALABRAS = 500 # 500
                # totalpalabras = contar_palabras(request.POST['resumenpropuesta'])
                # if totalpalabras > LIMITE_PALABRAS:
                #     return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El valor del campo Resumen de la propuesta debe contener máximo " + str(LIMITE_PALABRAS) + " palabras. Usted ha ingresado un total de " + str(totalpalabras) + " palabras", "showSwal": "True", "swalType": "warning"})
                #
                # LIMITE_PALABRAS = 100 # 100
                # totalpalabras = contar_palabras(request.POST['formulacionproblema'])
                # if totalpalabras > LIMITE_PALABRAS:
                #     return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El valor del campo Formulación del problema debe contener máximo " + str(LIMITE_PALABRAS) + " palabras. Usted ha ingresado un total de " + str(totalpalabras) + " palabras", "showSwal": "True", "swalType": "warning"})
                #
                # LIMITE_PALABRAS = 300  # 300
                # totalpalabras = contar_palabras(request.POST['justificacion'])
                # if totalpalabras > LIMITE_PALABRAS:
                #     return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El valor del campo Justificación debe contener máximo " + str(LIMITE_PALABRAS) + " palabras. Usted ha ingresado un total de " + str(totalpalabras) + " palabras", "showSwal": "True", "swalType": "warning"})
                #
                # LIMITE_PALABRAS = 1000  # 1000
                # totalpalabras = contar_palabras(request.POST['estadoarte'])
                # if totalpalabras > LIMITE_PALABRAS:
                #     return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El valor del campo Estado del arte debe contener máximo " + str(LIMITE_PALABRAS) + " palabras. Usted ha ingresado un total de " + str(totalpalabras) + " palabras", "showSwal": "True", "swalType": "warning"})
                #
                # LIMITE_PALABRAS = 2500  # PASÓ DE 1000 A 2500 según e-mail 27-03-2023 de la coordinación de investigación
                # totalpalabras = contar_palabras(request.POST['metodologia'])
                # if totalpalabras > LIMITE_PALABRAS:
                #     return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El valor del campo Metodología debe contener máximo " + str(LIMITE_PALABRAS) + " palabras. Usted ha ingresado un total de " + str(totalpalabras) + " palabras", "showSwal": "True", "swalType": "warning"})

                if not request.POST['impactosocial'] and not request.POST['impactocientifico'] and not request.POST['impactoeconomico'] and not request.POST['impactopolitico'] and not request.POST['otroimpacto']:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Ingrese al menos uno de los impactos solicitados", "showSwal": "True", "swalType": "warning"})

                f = ContenidoProyectoInvestigacionForm(request.POST)
                if f.is_valid():
                    # Obtengo los valores de los arrays de objetivos específicos del formulario
                    idsobjetivosepecificos = request.POST.getlist('idobjetivoespecifico[]')
                    objetivosepecificos = request.POST.getlist('objetivoespecifico[]')
                    mediosverificacion = request.POST.getlist('medioverificacion[]')

                    # Obtengo los valores de los arrays de resultados/compromisos del formulario
                    tiposregistro = request.POST.getlist('tiporegistro[]')
                    idsresultadocompromiso = request.POST.getlist('idresultadocompromiso[]')
                    idstiporesultado = request.POST.getlist('idtiporesultado[]')
                    destiporesultado = request.POST.getlist('destiporesultado[]')
                    obligtiporesultado = request.POST.getlist('obligtiporesultado[]')
                    marcados = request.POST.getlist('marcados[]')

                    # Obtengo los valores de los arrays de referencias bibliográficas del formulario
                    idsreferencias = request.POST.getlist('idreferenciabib[]')
                    referenciasbib = request.POST.getlist('referenciabib[]')

                    # Verifico los items obligatorios de marcar
                    for idtr, destr, oblig in zip(idstiporesultado, destiporesultado, obligtiporesultado):
                        if oblig == 'True' and idtr not in marcados:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Debe marcar la casilla del item %s" % (destr), "showSwal": "True", "swalType": "warning"})

                    idstiporesultadonofijo = request.POST.getlist('idtiporesultadonofijo[]')
                    tipos = request.POST.getlist('tipo[]')
                    descripcionestiporesultado = request.POST.getlist('descripciontiporesultado[]')
                    detallestiporesultado = request.POST.getlist('detalletiporesultado[]')

                    # Actualizo los campos del proyecto
                    proyecto.resumenpropuesta = request.POST['resumenpropuesta'].strip()
                    proyecto.formulacionproblema = request.POST['formulacionproblema'].strip()
                    proyecto.objetivogeneral = request.POST['objetivogeneral'].strip()
                    proyecto.justificacion = request.POST['justificacion'].strip()
                    proyecto.estadoarte = request.POST['estadoarte'].strip()
                    proyecto.metodologia = request.POST['metodologia'].strip()
                    proyecto.impactosocial = request.POST['impactosocial'].strip()
                    proyecto.impactocientifico = request.POST['impactocientifico'].strip()
                    proyecto.impactoeconomico = request.POST['impactoeconomico'].strip()
                    proyecto.impactopolitico = request.POST['impactopolitico'].strip()
                    proyecto.otroimpacto = request.POST['otroimpacto'].strip()
                    proyecto.save(request)

                    # Elimino los detalles de objetivos que fueron borrados en el formulario
                    for objetivoe in objetivoseliminados:
                        objetivoe = ProyectoInvestigacionObjetivo.objects.get(pk=int(objetivoe['idobjetivo']))
                        objetivoe.status = False
                        objetivoe.save(request)

                    # Guardo los objetivos específicos
                    for idobjetivoespecifico, objetivoespecifico, medioverificacion in zip(idsobjetivosepecificos, objetivosepecificos, mediosverificacion):
                        # Nuevo detalle
                        if int(idobjetivoespecifico) == 0:
                            objetivoe = ProyectoInvestigacionObjetivo(
                                proyecto=proyecto,
                                descripcion=objetivoespecifico.strip(),
                                medioverificacion=medioverificacion.strip(),
                                estadocumplimiento=1
                            )
                        else:
                            objetivoe = ProyectoInvestigacionObjetivo.objects.get(pk=int(idobjetivoespecifico))
                            objetivoe.descripcion = objetivoespecifico.strip()
                            objetivoe.medioverificacion = medioverificacion.strip()

                        objetivoe.save(request)

                    # Elimino los detalles de resultados/compromisos que fueron borrados en el formulario
                    for resultadoe in resultadoseliminados:
                        resultadoe = ProyectoInvestigacionResultado.objects.get(pk=int(resultadoe['idresultado']))
                        resultadoe.status = False
                        resultadoe.save(request)

                    # Guardo los resultados de aquellos items tipo registro E: Existentes en tabla maestra de TipoResultadoCompromiso

                    # Actualizo los items marcados / desmarcados
                    for idresultado, tipo, tiporegistro, idtiporesultado, detalle in zip(idsresultadocompromiso, tipos, tiposregistro, idstiporesultado, detallestiporesultado):
                        if int(idresultado) == 0 and int(idtiporesultado) == 0:
                            break

                        marcado = idtiporesultado in marcados

                        # Nuevo
                        if int(idresultado) == 0:
                            resultadoproyecto = ProyectoInvestigacionResultado(
                                proyecto=proyecto,
                                tipo=tipo,
                                resultado_id=idtiporesultado,
                                detalle=detalle.strip(),
                                marcado=marcado
                            )
                        else:
                            resultadoproyecto = ProyectoInvestigacionResultado.objects.get(pk=int(idresultado))
                            resultadoproyecto.tipo = tipo
                            resultadoproyecto.marcado = marcado
                            resultadoproyecto.detalle = detalle.strip()

                        resultadoproyecto.save(request)

                    # Guardo los resultados de aquellos items tipo N: no existentes en tabla maestra de TipoResultadoCompromiso
                    for idtipo, tipo, descripcion, detalle in zip(idstiporesultadonofijo, tipos, descripcionestiporesultado, detallestiporesultado):
                        # Nuevo registro
                        if int(idtipo) == 0:
                            # Creo el registro de TipoResultadoCompromiso
                            tiporesultado = TipoResultadoCompromiso(
                                descripcion=descripcion.strip(),
                                numero=0,
                                fijo=False,
                                obligatorio=True
                            )
                            tiporesultado.save(request)

                            # Guardo el resultado del proyecto
                            resultadoproyecto = ProyectoInvestigacionResultado(
                                proyecto=proyecto,
                                tipo=tipo,
                                resultado=tiporesultado,
                                detalle=detalle.strip(),
                                marcado=True
                            )
                            resultadoproyecto.save(request)
                        else:
                            tiporesultado = TipoResultadoCompromiso.objects.get(pk=int(idtipo))
                            tiporesultado.descripcion = descripcion.strip()
                            tiporesultado.save(request)

                    # Elimino los detalles de referencias bibliográficas que fueron borrados en el formulario
                    for referenciae in referenciaseliminadas:
                        referenciabib = ProyectoInvestigacionReferenciaBibliografica.objects.get(pk=int(referenciae['idreferencia']))
                        referenciabib.status = False
                        referenciabib.save(request)

                    # Guardo las referencias bibliográficas
                    for idreferencia, referencia in zip(idsreferencias, referenciasbib):
                        # Nuevo detalle
                        if int(idreferencia) == 0:
                            referenciabib = ProyectoInvestigacionReferenciaBibliografica(
                                proyecto=proyecto,
                                descripcion=referencia.strip()
                            )
                        else:
                            referenciabib = ProyectoInvestigacionReferenciaBibliografica.objects.get(pk=int(idreferencia))
                            referenciabib.descripcion = referencia.strip()

                        referenciabib.save(request)

                    log(u'%s editó contenido de propuesta de proyecto de investigación: %s' % (persona, proyecto), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    x = f.errors
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'adddetallepresupuesto':
            try:
                if not 'idproyecto' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idproyecto'])))
                tiporecurso = TipoRecursoPresupuesto.objects.get(pk=int(encrypt(request.POST['idtiporecurso'])))

                # Validar que el total registrado del presupuesto + el nuevo valor no exceda el límite
                totaldetalles = proyecto.presupuesto + Decimal(request.POST['total']).quantize(Decimal('.01'))
                if totaldetalles > proyecto.montototal:
                    diferencia = totaldetalles - proyecto.montototal
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se puede guardar el registro debido a que está excediendo al monto total del proyecto que es <b>$ %s</b>.<br><br>Presupuesto registrado: <b>$ %s</b> + Nuevo Detalle: <b>$ %s</b> = <b>$ %s</b>. Excedente <b>$ %s</b>" % (proyecto.montototal, proyecto.presupuesto, request.POST['total'], totaldetalles, diferencia), "showSwal": "True", "swalType": "warning"})

                # Guardo el detalle de presupuesto
                itempresupuesto = ProyectoInvestigacionItemPresupuesto(
                    proyecto=proyecto,
                    tiporecurso=tiporecurso,
                    recurso=request.POST['recurso'].strip(),
                    descripcion=request.POST['descripcion'].strip(),
                    unidadmedida_id=1,
                    cantidad=request.POST['cantidad'],
                    valorunitario=request.POST['valorunitario'],
                    calculaiva=False,
                    valoriva=0,
                    valortotal=request.POST['total'],
                    cantidadorig=request.POST['cantidad'],
                    valorunitarioorig=request.POST['valorunitario'],
                    valortotalorig=request.POST['total'],
                    valorneto=request.POST['total'],
                    saldo=request.POST['total'],
                    observacion=request.POST['observacion'].strip()
                )
                itempresupuesto.save(request)

                # Actualizo el presupuesto en el proyecto
                proyecto.presupuesto = proyecto.total_general_detalle_presupuesto()
                proyecto.save(request)

                # Actualizo la solicitud de permiso en caso de estar vigente
                actualizar_permiso_edicion_rubros_presupuesto(proyecto, 1, 2, request)

                # Cargo la sección del detalle para el tipo de recurso
                data['tiporecurso'] = tiporecurso
                data['detalles'] = proyecto.presupuesto_detalle_tiporecurso(tiporecurso.id)
                totales = proyecto.totales_detalle_tiporecurso(tiporecurso.id)
                template = get_template("pro_proyectoinvestigacion/secciondetalletiporecurso.html")
                json_content = template.render(data)

                # regfin = ConvocatoriaMontoFinanciamiento.objects.get(convocatoria=proyecto.convocatoria, tipoequipamiento=proyecto.compraequipo)
                regfin = ConvocatoriaMontoFinanciamiento.objects.filter(status=True, convocatoria=proyecto.convocatoria, categoria=proyecto.categoria2)[0]
                montominimoequipos = Decimal(proyecto.montounemi * (regfin.porcentajecompra) / 100).quantize(Decimal('.01'))
                totalequipos = proyecto.totales_detalle_equipos()['totaldetalle']

                log(u'% agregó detalle al presupuesto de proyecto de investigación: %s - %s' % (persona, proyecto, itempresupuesto), request, "add")
                return JsonResponse({"result": "ok", "idtr": tiporecurso.id, "totalitems": totales["totalitems"], "totalrecurso": totales["totaldetalle"], "montototalproyecto": proyecto.montototal, "totalpresupuesto": proyecto.presupuesto, "totalequipos": totalequipos, "montominimoequipos": montominimoequipos, "tipoporcentaje": regfin.tipoporcentaje, 'data': json_content, "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editdetallepresupuesto':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                itempresupuesto = ProyectoInvestigacionItemPresupuesto.objects.get(pk=int(encrypt(request.POST['id'])))
                proyecto = itempresupuesto.proyecto
                tiporecurso = itempresupuesto.tiporecurso
                valorneto = itempresupuesto.valorneto
                saldoanterior = itempresupuesto.saldo

                # Validar que el total registrado del presupuesto + el nuevo valor no exceda el límite
                totaldetalles = (proyecto.presupuesto - itempresupuesto.valortotal) + Decimal(request.POST['totale']).quantize(Decimal('.01'))
                if totaldetalles > proyecto.montototal:
                    diferencia = totaldetalles - proyecto.montototal
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se puede actualizar el registro debido a que está excediendo al monto total del proyecto que es <b>$ %s</b>.<br><br>Presupuesto registrado: <b>$ %s</b> + Nuevo Detalle: <b>$ %s</b> = <b>$ %s</b>. Excedente <b>$ %s</b>" % (proyecto.montototal, proyecto.presupuesto, request.POST['totale'], totaldetalles, diferencia), "showSwal": "True", "swalType": "warning"})

                # Si no está en Ejecución, actualizo el registro por completo
                if proyecto.estado.valor != 20:
                    # Actualizo el detalle de presupuesto
                    itempresupuesto.recurso = request.POST['recursoe'].strip()
                    itempresupuesto.descripcion = request.POST['descripcione'].strip()
                    itempresupuesto.cantidad = request.POST['cantidade']
                    itempresupuesto.valorunitario = request.POST['valorunitarioe']
                    itempresupuesto.valortotal = request.POST['totale']
                    itempresupuesto.cantidadorig = request.POST['cantidade']
                    itempresupuesto.valorunitarioorig = request.POST['valorunitarioe']
                    itempresupuesto.valortotalorig = request.POST['totale']
                    itempresupuesto.valorneto = request.POST['totale']
                    itempresupuesto.saldo = request.POST['totale']
                    itempresupuesto.observacion = request.POST['observacione'].strip()
                    itempresupuesto.save(request)

                    # Actualizo el presupuesto en el proyecto
                    proyecto.presupuesto = proyecto.total_general_detalle_presupuesto()
                    proyecto.save(request)
                else:
                    # Se actualizan ciertos campos y se guardar el movimiento
                    itempresupuesto.cantidad = int(request.POST['cantidade'])
                    itempresupuesto.valorunitario = Decimal(request.POST['valorunitarioe']).quantize(Decimal('.01'))
                    itempresupuesto.valortotal = Decimal(request.POST['totale']).quantize(Decimal('.01'))
                    itempresupuesto.observacion = request.POST['observacione'].strip()
                    itempresupuesto.save(request)

                    # Actualizo el presupuesto en el proyecto
                    proyecto.presupuesto = proyecto.total_general_detalle_presupuesto()
                    proyecto.save(request)

                    valormodificado = itempresupuesto.valortotal - valorneto
                    if itempresupuesto.valortotal > valorneto:
                        valormovimiento = itempresupuesto.valortotal - valorneto
                        tipomovimiento = 3 # Aumento
                    else:
                        valormovimiento = valorneto - itempresupuesto.valortotal
                        tipomovimiento = 4  # Disminución

                    itempresupuesto.modificado = itempresupuesto.modificado + valormodificado
                    itempresupuesto.valorneto = itempresupuesto.valorneto + valormodificado
                    itempresupuesto.saldo = itempresupuesto.valorneto - itempresupuesto.devengado
                    itempresupuesto.save(request)

                    # Guardar el movimiento
                    movimientorubro = ProyectoInvestigacionMovimientoItemPresupuesto(
                        itempresupuesto=itempresupuesto,
                        tipo=tipomovimiento,
                        fecha=datetime.now(),
                        saldoant=saldoanterior,
                        ingreso=valormovimiento if tipomovimiento == 3 else 0,
                        salida=valormovimiento if tipomovimiento == 4 else 0,
                        saldo=itempresupuesto.saldo,
                        observacion='MODIFICACIÓN PRESPUESTARIA: AUMENTO' if tipomovimiento == 3 else 'MODIFICACIÓN PRESPUESTARIA: DISMINUCIÓN'
                    )
                    movimientorubro.save(request)

                    # Obtener permiso edición vigente
                    permiso = proyecto.permiso_edicion_vigente(1, 2)
                    new_file = ContentFile(permiso.archivo.file.read())
                    new_file.name = generar_nombre("actrubropresupuesto", "actrubropresupuesto.pdf")

                    # Actualizar movimiento
                    movimientorubro.fechadocmodipres = permiso.inicio
                    movimientorubro.archivodocmodipres = new_file
                    movimientorubro.save(request)

                # Actualizo la solicitud de permiso en caso de estar vigente
                actualizar_permiso_edicion_rubros_presupuesto(proyecto, 1, 2, request)

                # Cargo la sección del detalle para el tipo de recurso
                data['tiporecurso'] = tiporecurso
                data['detalles'] = proyecto.presupuesto_detalle_tiporecurso(tiporecurso.id)
                totales = proyecto.totales_detalle_tiporecurso(tiporecurso.id)
                template = get_template("pro_proyectoinvestigacion/secciondetalletiporecurso.html")
                json_content = template.render(data)

                # regfin = ConvocatoriaMontoFinanciamiento.objects.get(convocatoria=proyecto.convocatoria, tipoequipamiento=proyecto.compraequipo)
                regfin = ConvocatoriaMontoFinanciamiento.objects.filter(status=True, convocatoria=proyecto.convocatoria, categoria=proyecto.categoria2)[0]
                montominimoequipos = Decimal(proyecto.montounemi * (regfin.porcentajecompra) / 100).quantize(Decimal('.01'))
                totalequipos = proyecto.totales_detalle_equipos()['totaldetalle']

                log(u'%s editó detalle al presupuesto de proyecto de investigación: %s - %s' % (persona, proyecto, itempresupuesto), request, "edit")
                return JsonResponse({"result": "ok", "idtr": tiporecurso.id, "totalitems": totales["totalitems"], "totalrecurso": totales["totaldetalle"], "montototalproyecto": proyecto.montototal, "totalpresupuesto": proyecto.presupuesto, "totalequipos": totalequipos, "montominimoequipos": montominimoequipos, "tipoporcentaje": regfin.tipoporcentaje, 'data': json_content, "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'deldetallepresupuesto':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                itempresupuesto = ProyectoInvestigacionItemPresupuesto.objects.get(pk=int(encrypt(request.POST['id'])))
                proyecto = itempresupuesto.proyecto

                # Elimino el detalle de presupesto
                itempresupuesto.status = False
                itempresupuesto.save(request)

                # Actualizo el presupuesto en el proyecto
                proyecto.presupuesto = proyecto.total_general_detalle_presupuesto()
                proyecto.save(request)

                # Actualizo la solicitud de permiso en caso de estar vigente
                actualizar_permiso_edicion_rubros_presupuesto(proyecto, 1, 2, request)

                # Consulto los totales
                totales = proyecto.totales_detalle_tiporecurso(itempresupuesto.tiporecurso.id)
                # regfin = ConvocatoriaMontoFinanciamiento.objects.get(convocatoria=proyecto.convocatoria, tipoequipamiento=proyecto.compraequipo)
                regfin = ConvocatoriaMontoFinanciamiento.objects.filter(status=True, convocatoria=proyecto.convocatoria, categoria=proyecto.categoria2)[0]
                montominimoequipos = Decimal(proyecto.montounemi * (regfin.porcentajecompra) / 100).quantize(Decimal('.01'))
                totalequipos = proyecto.totales_detalle_equipos()['totaldetalle']

                log(u'%s eliminó detalle de presupuesto de proyecto de investigación [ %s ]' % (persona, itempresupuesto), request, "del")
                return JsonResponse({"result": "ok", "totalitems": totales["totalitems"], "totalrecurso": totales["totaldetalle"], "montototalproyecto": proyecto.montototal, "totalpresupuesto": proyecto.presupuesto, "totalequipos": totalequipos, "montominimoequipos": montominimoequipos, "tipoporcentaje": regfin.tipoporcentaje, "titulo": "Proceso exitoso!!!", "mensaje": u"Registro eliminado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al eliminar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addactividadcronograma':
            try:
                if not 'idproyecto' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idproyecto'])))
                objetivo = ProyectoInvestigacionObjetivo.objects.get(pk=int(encrypt(request.POST['idobjetivo'])))
                ponderaciongeneral = proyecto.total_ponderacion_actividades()

                # Validar que el total registrado de las ponderaciones no supere el 100 %
                totalponderacion = ponderaciongeneral + Decimal(request.POST['ponderacion']).quantize(Decimal('.01'))
                if totalponderacion > 100:
                    diferencia = totalponderacion - 100
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se puede guardar el registro debido a que está excediendo al <b>100 %</b>.<br><br>Ponderación  registrada: <b> {} %</b> + Nuevo Ponderación: <b>{} %</b> = <b>{} %</b>. Excedente <b>{} %</b>".format(ponderaciongeneral, request.POST['ponderacion'], totalponderacion, diferencia), "showSwal": "True", "swalType": "warning"})

                # Validar las fechas de la actividad
                fechainicio = datetime.strptime(request.POST['fechainicio'], '%Y-%m-%d').date()
                fechafin = datetime.strptime(request.POST['fechafin'], '%Y-%m-%d').date()

                if fechafin <= fechainicio:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin debe ser mayor a la fecha de inicio de la actividad", "showSwal": "True", "swalType": "warning"})

                # Guardo la actividad del cronograma
                actividadcronograma = ProyectoInvestigacionCronogramaActividad(
                    objetivo=objetivo,
                    actividad=request.POST['actividad'].strip(),
                    ponderacion=request.POST['ponderacion'],
                    fechainicio=fechainicio,
                    fechafin=fechafin,
                    entregable=request.POST['entregable'].strip()
                )
                actividadcronograma.save(request)

                # Guardo los responsables de la actividad
                responsables = request.POST.getlist('responsable')
                for responsable in responsables:
                    responsableactividad = ProyectoInvestigacionCronogramaResponsable(
                        actividad=actividadcronograma,
                        persona_id=responsable
                    )
                    responsableactividad.save(request)

                # Cargo la sección del detalle de actividades para el objetivo
                data['objetivo'] = objetivo
                data['numobj'] = request.POST['numobj']
                data['detalles'] = proyecto.cronograma_detallado_objetivo(objetivo.id)
                totales = proyecto.totales_detalle_objetivo(objetivo.id)
                template = get_template("pro_proyectoinvestigacion/secciondetalleobjetivo.html")
                json_content = template.render(data)

                ponderaciongeneral = proyecto.total_ponderacion_actividades()

                log(u'% agregó actividad al cronograma de proyecto de investigación: %s - %s' % (persona, proyecto, actividadcronograma), request, "add")
                return JsonResponse({"result": "ok", "idobj": objetivo.id, "totalactividades": totales["totalactividades"], "totalponderacion": totales["totalponderacion"], "ponderaciongeneral": ponderaciongeneral, 'data': json_content, "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editactividadcronograma':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                actividadcronograma = ProyectoInvestigacionCronogramaActividad.objects.get(pk=int(encrypt(request.POST['id'])))
                proyecto = actividadcronograma.objetivo.proyecto
                ponderaciongeneral = proyecto.total_ponderacion_actividades()

                # Validar que el total registrado de las ponderaciones no supere el 100 %
                totalponderacion = (ponderaciongeneral - actividadcronograma.ponderacion) + Decimal(request.POST['ponderacione']).quantize(Decimal('.01'))
                if totalponderacion > 100:
                    diferencia = totalponderacion - 100
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se puede guardar el registro debido a que está excediendo al <b>100 %</b>.<br><br>Ponderación  registrada: <b> {} %</b> + Nuevo Ponderación: <b>{} %</b> = <b>{} %</b>. Excedente <b>{} %</b>".format(ponderaciongeneral, request.POST['ponderacione'], totalponderacion, diferencia), "showSwal": "True", "swalType": "warning"})

                # Validar las fechas de la actividad
                fechainicio = datetime.strptime(request.POST['fechainicioe'], '%Y-%m-%d').date()
                fechafin = datetime.strptime(request.POST['fechafine'], '%Y-%m-%d').date()

                if fechafin <= fechainicio:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin debe ser mayor a la fecha de inicio de la actividad", "showSwal": "True", "swalType": "warning"})

                # Actualizo el cronograma
                actividadcronograma.actividad = request.POST['actividade'].strip()
                actividadcronograma.ponderacion = request.POST['ponderacione']
                actividadcronograma.fechainicio = fechainicio
                actividadcronograma.fechafin = fechafin
                actividadcronograma.entregable = request.POST['entregablee'].strip()
                actividadcronograma.save(request)

                # Obtengo los responsables de la actividad ingresados en el formulario
                responsables = request.POST.getlist('responsablee')

                # Consulto los ids originales de responsables de la actividad
                idsresponsables = actividadcronograma.lista_ids_responsables()

                excluidos = [c for c in idsresponsables if str(c) not in responsables]

                # Actualizo los responsables de la actividad
                for responsable in responsables:
                    # Si no existe lo creo
                    if not ProyectoInvestigacionCronogramaResponsable.objects.filter(actividad=actividadcronograma, persona_id=responsable, status=True).exists():
                        responsableactividad = ProyectoInvestigacionCronogramaResponsable(
                            actividad=actividadcronograma,
                            persona_id=responsable
                        )
                        responsableactividad.save(request)

                # Borro los responsables de la actividad
                for personaexcluida in excluidos:
                    responsableactividad = ProyectoInvestigacionCronogramaResponsable.objects.get(actividad=actividadcronograma, persona_id=personaexcluida, status=True)
                    responsableactividad.status = False
                    responsableactividad.save(request)

                # Cargo la sección del detalle de actividades para el objetivo
                data['objetivo'] = objetivo = actividadcronograma.objetivo
                data['numobj'] = request.POST['numobj']
                data['detalles'] = proyecto.cronograma_detallado_objetivo(objetivo.id)
                totales = proyecto.totales_detalle_objetivo(objetivo.id)
                template = get_template("pro_proyectoinvestigacion/secciondetalleobjetivo.html")
                json_content = template.render(data)

                ponderaciongeneral = proyecto.total_ponderacion_actividades()

                log(u'%s editó actividad del cronograma de proyecto de investigación: %s - %s' % (persona, proyecto, actividadcronograma), request, "edit")
                return JsonResponse({"result": "ok", "idobj": objetivo.id, "totalactividades": totales["totalactividades"], "totalponderacion": totales["totalponderacion"], "ponderaciongeneral": ponderaciongeneral, 'data': json_content, "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'delactividadcronograma':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                actividadcronograma = ProyectoInvestigacionCronogramaActividad.objects.get(pk=int(encrypt(request.POST['id'])))
                proyecto = actividadcronograma.objetivo.proyecto
                objetivo = actividadcronograma.objetivo
                responsables = actividadcronograma.lista_responsables()

                # Elimino la actividad
                actividadcronograma.status = False
                actividadcronograma.save(request)

                # Elimino los responsables de la actividad
                for responsable in responsables:
                    responsable.status = False
                    responsable.save(request)

                # Consulto los totales
                totales = proyecto.totales_detalle_objetivo(objetivo.id)
                ponderaciongeneral = proyecto.total_ponderacion_actividades()

                log(u'%s eliminó actividad del cronograma de proyecto de investigación [ %s ]' % (persona, actividadcronograma), request, "del")
                return JsonResponse({"result": "ok", "totalactividades": totales["totalactividades"], "totalponderacion": totales["totalponderacion"], "ponderaciongeneral": ponderaciongeneral, "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al eliminar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'verificarrequisitos':
            try:
                if not 'idproyecto' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                proyectoinvestigacion = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idproyecto'])))

                estado = int(request.POST['estado'])
                observaciongeneral = request.POST['observacion'].strip() if 'observacion' in request.POST else 'Propuesta de Proyecto Verificada'
                investigadores = json.loads(request.POST['lista_items1'])
                observacionesinv = request.POST.getlist('observacionint[]')
                documentos = json.loads(request.POST['lista_items2'])
                observacionesdoc = request.POST.getlist('observaciondoc[]')

                archivo = ''
                if 'archivo' in request.FILES:
                    archivo = request.FILES['archivo']
                    descripcionarchivo = 'Archivo de novedades'
                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    archivo._name = generar_nombre("novedades", archivo._name)

                # Obtengo el registro del estado
                estadopropuesta = obtener_estado_solicitud(3, estado)

                # Actualizo el proyecto
                proyectoinvestigacion.observacion = observaciongeneral
                proyectoinvestigacion.estado = estadopropuesta
                proyectoinvestigacion.fechaverirequi = datetime.now()

                # Actualizo los estados de revisión de las secciones y formulario inscripción
                generardocumento = False
                for documento, observacion in zip(documentos, observacionesdoc):
                    iddet = int(documento['id'])
                    if iddet == 1:
                        proyectoinvestigacion.estadodatogeneral = 2 if documento['valor'] is True else 4
                        proyectoinvestigacion.observaciondatogeneral = observacion.strip()
                        generardocumento = not documento['valor']
                    elif iddet == 2:
                        proyectoinvestigacion.estadointegrante = 2 if documento['valor'] is True else 4
                        proyectoinvestigacion.observacionintegrante = observacion.strip()
                        generardocumento = not documento['valor']
                    elif iddet == 3:
                        proyectoinvestigacion.estadocontenido = 2 if documento['valor'] is True else 4
                        proyectoinvestigacion.observacioncontenido = observacion.strip()
                        generardocumento = not documento['valor']
                    elif iddet == 4:
                        proyectoinvestigacion.estadopresupuesto = 2 if documento['valor'] is True else 4
                        proyectoinvestigacion.observacionpresupuesto = observacion.strip()
                        generardocumento = not documento['valor']
                    elif iddet == 5:
                        proyectoinvestigacion.estadocronogramarev = 2 if documento['valor'] is True else 4
                        proyectoinvestigacion.observacioncronograma = observacion.strip()
                        generardocumento = not documento['valor']
                    else:
                        proyectoinvestigacion.estadodocumentofirmado = 2 if documento['valor'] is True else 4
                        proyectoinvestigacion.observaciondocumentofirmado = observacion.strip()
                        generardocumento = not documento['valor']

                if archivo:
                    proyectoinvestigacion.archivonovedad = archivo

                proyectoinvestigacion.save(request)

                proyectoinvestigacion.verificado = 1 if proyectoinvestigacion.estado.valor == 3 else 2

                # Si asigna estado novedad, debe generar nuevamente el documento único
                if proyectoinvestigacion.estado.valor == 4 and generardocumento:
                    proyectoinvestigacion.documentogenerado = False
                    proyectoinvestigacion.documentogenerado = False

                proyectoinvestigacion.save(request)

                # Actualizo los estados acreditado de los investigadores
                for investigador, observacion in zip(investigadores, observacionesinv):
                    integranteproyecto = ProyectoInvestigacionIntegrante.objects.get(pk=investigador['id'])
                    integranteproyecto.estadoacreditado = 2 if investigador['valor'] is True else 3
                    integranteproyecto.observacion = observacion.strip()
                    integranteproyecto.save(request)

                # Creo el recorrido del proyecto
                recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                           fecha=datetime.now().date(),
                                                           observacion=observaciongeneral if observaciongeneral else 'Requisitos Verificados',
                                                           estado=estadopropuesta
                                                           )
                recorrido.save(request)

                # Si el estado es VERIFICADO, debo generar el documento del proyecto sin los nombres de los integrantes
                if estado == 3:
                    if not proyectoinvestigacion.codigo:
                        # Generar el código del proyecto
                        secuencia = str(secuencia_codigo_proyecto(proyectoinvestigacion.convocatoria, proyectoinvestigacion.lineainvestigacion))
                        codigo = "C" + str(proyectoinvestigacion.convocatoria.apertura.year)[2:] + "-" + proyectoinvestigacion.lineainvestigacion.abreviatura + "-" + secuencia.zfill(2)

                        # Actualizo el código del proyecto
                        proyectoinvestigacion.codigo = codigo
                        proyectoinvestigacion.secuencia = secuencia
                        proyectoinvestigacion.estadocronograma = 3
                        proyectoinvestigacion.save(request)

                    # Genero documento sin nombres de los integrantes
                    documentogenerado = generar_documento_proyecto_sin_nombreintegrantes(proyectoinvestigacion, data)

                    if documentogenerado['estado'] == 'ok':
                        # Actualizo el campo archivo documento sin integrantes
                        proyectoinvestigacion.archivodocumentosindatint = documentogenerado['archivo']
                        proyectoinvestigacion.save(request)

                        # Guardar historial de archivos
                        tipodocumento = TipoDocumento.objects.get(pk=4)
                        guardar_historial_archivo_proyectos_investigacion(proyectoinvestigacion, tipodocumento, proyectoinvestigacion.archivodocumentosindatint, request)

                # Si hay archivo debo crear el historial
                if archivo:
                    # Guardar historial de archivos
                    tipodocumento = TipoDocumento.objects.get(pk=3)
                    guardar_historial_archivo_proyectos_investigacion(proyectoinvestigacion, tipodocumento, proyectoinvestigacion.archivonovedad, request)

                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [29]  # investigacion@unemi.edu.ec

                lista_email_envio = []
                lista_email_cco = persona.lista_emails_envio()
                lista_email_cco.append('isaltosm@unemi.edu.ec')

                for integrante in proyectoinvestigacion.integrantes_proyecto():
                    lista_email_envio += integrante.persona.lista_emails_envio()

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                if estado == 3:
                    tituloemail = "Propuesta de Proyecto de Investigación - Verificada"
                    tiponotificacion = "REQVERI"
                elif estado == 4:
                    tituloemail = "Novedades en Propuesta de Proyecto de Investigación"
                    tiponotificacion = "ERRORREQ"
                else:
                    tituloemail = "Propuesta de Proyecto de Investigación - Rechazada"
                    tiponotificacion = "RECHAZADA"

                lista_archivos_adjuntos = []
                if proyectoinvestigacion.archivonovedad and estado != 3:
                    lista_archivos_adjuntos.append(proyectoinvestigacion.archivonovedad)

                titulo = "Proyectos de Investigación"
                send_html_mail(tituloemail,
                               "emails/propuestaproyectoinvestigacion.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimada' if proyectoinvestigacion.profesor.persona.sexo_id == 1 else 'Estimado',
                                'nombrepersona': proyectoinvestigacion.profesor.persona.nombre_completo_inverso(),
                                'observaciones': observaciongeneral,
                                'proyecto': proyectoinvestigacion
                                },
                               lista_email_envio,  # Destinatarioa
                               lista_email_cco,  # Copia oculta
                               lista_archivos_adjuntos, # Adjunto(s)
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                if estado == 3:
                    log(f'{persona} verificó requisitos de propuesta de proyecto de investigación: {proyectoinvestigacion}', request, "edit")
                elif estado == 4:
                    log(f'{persona} registró novedades durante verificación de requisitos de propuesta de proyecto de investigación: {proyectoinvestigacion}', request, "edit")
                else:
                    log(f'{persona} rechazó propuesta de proyecto de investigación: {proyectoinvestigacion}', request, "edit")

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addevaluacioninterna':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                # Consulto el proyecto de investigación
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                estadoactual = proyecto.estado.valor

                # Obtengo los valores de los campos del formulario
                fecha = request.POST['fechaevalua']
                evaluador = request.POST['evaluador']
                puntajetotal = request.POST['puntajetotal']
                estadoevaluacion = request.POST['estadoevaluacion']
                observacion= request.POST['observacion'].strip().upper()

                # Verifico que no exista evaluación interna con el evaluador para el proyecto
                if estadoactual != 9:
                    if EvaluacionProyecto.objects.filter(status=True, proyecto=proyecto, evaluador_id=evaluador, tipo=1).exists():
                        return JsonResponse({"result": "bad", "mensaje": "La evaluación ya ha sido guardada"})
                else:
                    if EvaluacionProyecto.objects.filter(status=True, proyecto=proyecto, evaluador_id=evaluador, tipo=1, adicional=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": "La evaluación ya ha sido guardada"})

                archivo = ''
                if 'archivo' in request.FILES:
                    archivo = request.FILES['archivo']
                    descripcionarchivo = 'Archivo de Evaluación'
                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    archivo._name = generar_nombre("evalinterna", archivo._name)

                # Obtengo los valores de los campos tipo arreglo del formulario
                idsrubricaitem = request.POST.getlist('idrubricaitem[]')
                puntajesasignados = request.POST.getlist('puntajeasignado[]')

                # Guardo la evaluación interna
                evaluacion = EvaluacionProyecto(
                    proyecto=proyecto,
                    fecha=fecha,
                    fechaconfirma=fecha,
                    tipo=1,
                    evaluador_id=evaluador,
                    puntajetotal=puntajetotal,
                    observacion=observacion,
                    estado=estadoevaluacion,
                    adicional=estadoactual == 9,
                    estadoregistro=5
                )
                evaluacion.save(request)

                if archivo:
                    evaluacion.archivoevaluacion = archivo
                    evaluacion.save(request)

                # Guardo el detalle de la evaluación interna
                numero = 1
                for idrubricaitem, puntajeasignado in zip(idsrubricaitem, puntajesasignados):
                    detalleevaluacion = EvaluacionProyectoDetalle(
                        evaluacion=evaluacion,
                        rubricaitem_id=idrubricaitem,
                        puntaje=puntajeasignado,
                        numero=numero
                    )
                    detalleevaluacion.save(request)
                    numero += 1

                # Verifico si todas las evaluaciones internas están realizadas
                if proyecto.evaluaciones_internas_completas() or estadoactual == 9:
                    # Ontengo los estados asignados en cada evaluación
                    # Si no requiere evaluación interna adicional
                    if estadoactual != 9:
                        estados = [evaluacion.estado for evaluacion in proyecto.evaluaciones_internas()]
                    else:
                        estados = [evaluacion.estado for evaluacion in proyecto.evaluacion_interna_adicional()]

                    # Verifico si hay un estado diferente: si los estados son iguales la longitud del conjunto debe ser 1
                    iguales = len(set(estados)) == 1

                    if iguales:
                        # Si es ACEPTADO Ó SERÁ ACEPTADO CON MODIFICACIONES MENORES
                        if estados[0] == 1 or estados[0] == 2:
                            # Se asigna al proyecto el estado EVALUACION INTERNA SUPERADA
                            estado = obtener_estado_solicitud(3, 8)
                            observacion = "ETAPA DE EVALUACIÓN INTERNA SUPERADA"
                        elif estados[0] == 3: # Será ACEPTADO CON MODIFICACIONES MAYORES
                            # Se asigna el estado EVALUACIÓN INTERNA ADICIONAL
                            estado = obtener_estado_solicitud(3, 9)
                            observacion = "REQUIERE EVALUACIÓN INTERNA ADICIONAL"
                        else:
                            # Se asigna el estado de RECHAZADO al proyecto
                            estado = obtener_estado_solicitud(3, 14)
                            observacion = "PROYECTO RECHAZADO"
                    else:
                        # Se asigna el estado EVALUACIÓN INTERNA ADICIONAL
                        estado = obtener_estado_solicitud(3, 9)
                        observacion = "REQUIERE EVALUACIÓN INTERNA ADICIONAL"

                    # Asignar el estado al proyecto
                    proyecto.estado = estado
                    proyecto.save(request)

                    # Creo el recorrido del proyecto
                    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                               fecha=datetime.now().date(),
                                                               observacion=observacion,
                                                               estado=estado
                                                               )
                    recorrido.save(request)

                    # Si estado es ACEPTADO o ACEPTADO LUEGO DE CAMBIOS MENORES, poner estado EVALUACION EXTERNA
                    if iguales:
                        if estados[0] == 1 or estados[0] == 2:
                            # Se asigna al proyecto el estado EVALUACIÓN EXTERNA
                            estado = obtener_estado_solicitud(3, 10)
                            observacion = "EVALUACIÓN EXTERNA EN CURSO"
                            proyecto.estado = estado
                            proyecto.save(request)

                            # Creo el recorrido del proyecto
                            recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                       fecha=datetime.now().date(),
                                                                       observacion=observacion,
                                                                       estado=estado
                                                                       )
                            recorrido.save(request)

                log(u'Agregó evaluación interna al proyecto de investigación: %s' % evaluacion, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'addevaluacionexterna':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                # Consulto el proyecto de investigación
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                estadoactual = proyecto.estado.valor

                # Obtengo los valores de los campos del formulario
                fecha = request.POST['fechaevalua']
                evaluador = request.POST['evaluador']
                puntajetotal = request.POST['puntajetotal']
                estadoevaluacion = request.POST['estadoevaluacion']
                observacion= request.POST['observacion'].strip().upper()

                # Verifico que no exista evaluación externa con el evaluador para el proyecto
                if estadoactual != 12:
                    if EvaluacionProyecto.objects.filter(status=True, proyecto=proyecto, evaluador_id=evaluador, tipo=2).exists():
                        return JsonResponse({"result": "bad", "mensaje": "La evaluación ya ha sido guardada"})
                else:
                    if EvaluacionProyecto.objects.filter(status=True, proyecto=proyecto, evaluador_id=evaluador, tipo=2, adicional=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": "La evaluación ya ha sido guardada"})

                archivo = ''
                if 'archivo' in request.FILES:
                    archivo = request.FILES['archivo']
                    descripcionarchivo = 'Archivo de Evaluación'
                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    archivo._name = generar_nombre("evalexterna", archivo._name)

                # Obtengo los valores de los campos tipo arreglo del formulario
                idsrubricaitem = request.POST.getlist('idrubricaitem[]')
                puntajesasignados = request.POST.getlist('puntajeasignado[]')

                # Guardo la evaluación externa
                evaluacion = EvaluacionProyecto(
                    proyecto=proyecto,
                    fecha=fecha,
                    fechaconfirma=fecha,
                    tipo=2,
                    evaluador_id=evaluador,
                    puntajetotal=puntajetotal,
                    observacion=observacion,
                    estado=estadoevaluacion,
                    adicional=estadoactual == 12,
                    estadoregistro=5
                )
                evaluacion.save(request)

                if archivo:
                    evaluacion.archivoevaluacion = archivo
                    evaluacion.save(request)

                # Guardo el detalle de la evaluación externa
                numero = 1
                for idrubricaitem, puntajeasignado in zip(idsrubricaitem, puntajesasignados):
                    detalleevaluacion = EvaluacionProyectoDetalle(
                        evaluacion=evaluacion,
                        rubricaitem_id=idrubricaitem,
                        puntaje=puntajeasignado,
                        numero=numero
                    )
                    detalleevaluacion.save(request)

                    numero += 1

                # Verifico si todas las evaluaciones externas están realizadas
                if proyecto.evaluaciones_externas_completas() or estadoactual == 12:
                    # Ontengo los estados asignados en cada evaluación
                    if estadoactual != 12:
                        estados = [evaluacion.estado for evaluacion in proyecto.evaluaciones_externas()]
                    else:
                        estados = [evaluacion.estado for evaluacion in proyecto.evaluacion_externa_adicional()]

                    # Verifico si hay un estado diferente: si los estados son iguales la longitud del conjunto debe ser 1
                    iguales = len(set(estados)) == 1

                    if iguales:
                        # Si es ACEPTADO o SERÁ ACEPTADO CON MODIFICACIONES MENORES
                        if estados[0] == 1 or estados[0] == 2:
                            # Se asigna al proyecto el estado EVALUACION EXTERNA SUPERADA
                            estado = obtener_estado_solicitud(3, 11)
                            observacion = "ETAPA DE EVALUACIÓN EXTERNA SUPERADA"
                        elif estados[0] == 3:
                            # Se asigna el estado EVALUACIÓN EXTERNA ADICIONAL
                            estado = obtener_estado_solicitud(3, 12)
                            observacion = "REQUIERE EVALUACIÓN EXTERNA ADICIONAL"
                        else: # Si es RECHAZADO
                            # Se asigna el estado de RECHAZADO al proyecto
                            estado = obtener_estado_solicitud(3, 14)
                            observacion = "PROYECTO RECHAZADO"
                    else:
                        # Se asigna el estado EVALUACIÓN EXTERNA ADICIONAL
                        estado = obtener_estado_solicitud(3, 12)
                        observacion = "REQUIERE EVALUACIÓN EXTERNA ADICIONAL"

                    # Asignar el estado al proyecto
                    proyecto.estado = estado
                    proyecto.save(request)

                    # Creo el recorrido del proyecto
                    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                               fecha=datetime.now().date(),
                                                               observacion=observacion,
                                                               estado=estado
                                                               )
                    recorrido.save(request)

                    # Si estado es ACEPTADO o SERÁ ACEPTADO CON MODIFICACIONES MENORES, poner estado ACEPTADO AL PROYECTO
                    if estados[0] == 1 or estados[0] == 2:
                        # Se asigna al proyecto el estado ACEPTADO
                        estado = obtener_estado_solicitud(3, 13)
                        observacion = "PROYECTO ACEPTADO PARA IR A CGA"
                        proyecto.estado = estado
                        proyecto.save(request)

                        # Creo el recorrido del proyecto
                        recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                   fecha=datetime.now().date(),
                                                                   observacion=observacion,
                                                                   estado=estado
                                                                   )
                        recorrido.save(request)

                        # Asignar el puntaje de evaluacion interna y externa al proyecto
                        puntajeinterna = proyecto.puntaje_final_evaluacion_interna()
                        puntajeexterna = proyecto.puntaje_final_evaluacion_externa()

                        proyecto.puntajeevalint = puntajeinterna
                        proyecto.puntajeevalext = puntajeexterna
                        proyecto.save(request)

                log(u'Agregó evaluación externa al proyecto de investigación: %s' % evaluacion, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'subirpresupuesto':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivo = request.FILES['archivopresupuesto']
                descripcionarchivo = 'Archivo del presupuesto actualizado'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto el proyecto de investigación
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Si proyecto no está en Ejecución, Finalizado y Cerrado
                if proyecto.estado.valor not in [20, 21, 26]:
                    archivo._name = generar_nombre("presupuestovs1", archivo._name)

                    proyecto.archivopresupuesto = archivo
                    proyecto.documentogenerado = False
                    proyecto.archivodocumentofirmado = None
                    proyecto.presupactualizado = True
                    proyecto.save(request)
                else:
                    # Si el total de archivos es 0, primero crear el historial del anterior
                    totalarchivos = proyecto.total_archivos_presupueso()
                    if totalarchivos == 0:
                        historialarchivo = ProyectoInvestigacionHistorialArchivo(
                            proyecto=proyecto,
                            descripcion='Presupuesto versión 1',
                            tipo=15,
                            archivo=proyecto.archivopresupuesto
                        )
                        historialarchivo.save(request)

                    # Guardo y creo el historial del nuevo archivo
                    version = totalarchivos + 1 if totalarchivos > 0 else 2
                    archivo._name = generar_nombre(f"presupuestovs{version}", archivo._name)
                    proyecto.archivopresupuesto = archivo
                    proyecto.save(request)

                    historialarchivo = ProyectoInvestigacionHistorialArchivo(
                        proyecto=proyecto,
                        descripcion=f'Presupuesto versión {version}',
                        tipo=15,
                        archivo=proyecto.archivopresupuesto
                    )
                    historialarchivo.save(request)

                log(u'%s actualizó archivo del presupuesto final del proyecto: %s' % (persona, proyecto), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True, "id": encrypt(proyecto.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'generardocumento':
            try:
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                data['proyecto'] = proyecto
                data['instituciones'] = proyecto.instituciones_proyecto()
                data['directorproyecto'] = proyecto.nombre_director_proyecto()
                data['resultados'] = proyecto.resultados_compromisos()
                data['referenciabib'] = proyecto.referencias_bibliograficas()

                # Datos del presupuesto
                listagrupos = []
                grupos_presupuesto = proyecto.presupuesto_grupo_totales()
                for grupo in grupos_presupuesto:
                    # ID GRUPO, DESCRIPCION, TOTAL X GRUPO
                    listagrupos.append([grupo['id'], grupo['descripcion'], grupo['totalgrupo']])

                datospresupuesto = []
                detalles_presupuesto = proyecto.presupuesto_detallado().filter(valortotal__gt=0)  # .order_by('tiporecurso__orden', 'tiporecurso__id', 'id')
                for detalle in detalles_presupuesto:
                    # ID GRUPO, RECURSO, DESCRIPCION, UNIDAD MEDIDA, CANTIDAD, PRECIO, IVA, TOTAL, OBSERVACION
                    datospresupuesto.append([
                        detalle.tiporecurso.id,
                        detalle.recurso,
                        detalle.descripcion,
                        detalle.unidadmedida.nombre,
                        detalle.cantidad,
                        detalle.valorunitario,
                        detalle.valoriva,
                        detalle.valortotal,
                        detalle.observacion
                    ])

                data['datospresupuesto'] = datospresupuesto
                data['listagrupos'] = listagrupos

                # Datos del cronograma de actividades
                listaobjetivos = []
                objetivos_cronograma = proyecto.cronograma_objetivo_totales()
                for objetivo in objetivos_cronograma:
                    # Id, descripcion, total actividades, total ponderacion
                    listaobjetivos.append([objetivo['id'], objetivo['descripcion'], objetivo['totalactividades'], objetivo['totalponderacion']])

                datoscronograma = []
                detalles_cronograma = proyecto.cronograma_detallado()
                auxid = 0
                secuencia = 0
                totalponderacion = 0
                for detalle in detalles_cronograma:
                    secuencia += 1
                    totalponderacion += detalle.ponderacion
                    if auxid != detalle.objetivo.id:
                        secuencia_grupo = 1
                        auxid = detalle.objetivo.id
                    else:
                        secuencia_grupo += 1

                    # id objetivo, secuencia, secuencia grupo, actividad, ponderacion, fecha inicio, fecha fin, entregables, responsables
                    datoscronograma.append([
                        detalle.objetivo.id,
                        secuencia,
                        secuencia_grupo,
                        detalle.actividad,
                        detalle.ponderacion,
                        detalle.fechainicio,
                        detalle.fechafin,
                        detalle.lista_html_entregables(),
                        detalle.lista_html_nombres_responsables()
                    ])

                data['datoscronograma'] = datoscronograma
                data['listaobjetivos'] = listaobjetivos
                data['totalponderacion'] = totalponderacion

                # Datos de los integrantes
                data['integrantes'] = integrantes = proyecto.integrantes_proyecto_informe()
                data['integrantesfirmas'] = integrantes.filter(tipo=1)
                data['totalintegrantes'] = integrantes.count()

                # Creacion de los archivos por separado
                directorio = SITE_STORAGE + '/media/proyectoinvestigacion/documentos'
                try:
                    os.stat(directorio)
                except:
                    os.mkdir(directorio)

                # Archivo de los datos generales del proyecto
                nombrearchivo1 = 'datosinformativos_' + str(proyecto.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                valida = convert_html_to_pdf(
                    'pro_proyectoinvestigacion/inscripcionproyectopdf.html',
                    {'pagesize': 'A4', 'data': data},
                    nombrearchivo1,
                    directorio
                )

                if not valida:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar documento de los datos principales.", "showSwal": "True", "swalType": "error"})

                # ACTIVAR PARA CONVOCATORIA 2024
                # Archivo con el presupuesto del proyecto
                nombrearchivo3 = 'presupuesto_' + str(proyecto.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                valida = convert_html_to_pdf(
                    'pro_proyectoinvestigacion/presupuestoproyectopdf.html',
                    {'pagesize': 'A4', 'data': data},
                    nombrearchivo3,
                    directorio
                )

                if not valida:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar documento del presupuesto.", "showSwal": "True", "swalType": "error"})

                #
                # Archivo con el cronograma de actividades del proyecto
                nombrearchivo4 = 'cronograma_' + str(proyecto.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                valida = convert_html_to_pdf(
                    'pro_proyectoinvestigacion/cronogramaproyectopdf.html',
                    {'pagesize': 'A4', 'data': data},
                    nombrearchivo4,
                    directorio
                )

                if not valida:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar documento del cronograma.", "showSwal": "True", "swalType": "error"})

                # # Archivo con las hojas de vida de los integrantes del proyecto
                # nombrearchivo5 = 'hojavidaintegrante_' + str(proyecto.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                # valida = convert_html_to_pdf(
                #     'pro_proyectoinvestigacion/hojavidaintegrantepdf.html',
                #     {'pagesize': 'A4', 'data': data},
                #     nombrearchivo5,
                #     directorio
                # )
                #
                # if not valida:
                #     return JsonResponse(
                #         {"result": "bad", "mensaje": u"Error al generar documento de las hojas de vida."})

                archivo1 = directorio + "/" + nombrearchivo1
                # archivo2 = SITE_STORAGE + proyecto.archivoproyecto.url  # Archivo pdf de proyecto cargado por el docente
                archivo3 = directorio + "/" + nombrearchivo3
                archivo4 = directorio + "/" + nombrearchivo4
                # archivo5 = directorio + "/" + nombrearchivo5
                # archivo6 = SITE_STORAGE + proyecto.archivopresupuesto.url  # Archivo pdf del presupuesto cargado por el docente

                # Leer los archivos
                pdf1Reader = PyPDF2.PdfFileReader(archivo1)
                # pdf2Reader = PyPDF2.PdfFileReader(archivo2)
                pdf3Reader = PyPDF2.PdfFileReader(archivo3)
                pdf4Reader = PyPDF2.PdfFileReader(archivo4)
                # pdf5Reader = PyPDF2.PdfFileReader(archivo5)
                # pdf6Reader = PyPDF2.PdfFileReader(archivo6)

                # Crea un nuevo objeto PdfFileWriter que representa un documento PDF en blanco
                pdfWriter = PyPDF2.PdfFileWriter()

                # Recorre todas las páginas del documento 1: Formulario de inscripcion del proyecto
                for pageNum in range(pdf1Reader.numPages):
                    pageObj = pdf1Reader.getPage(pageNum)
                    pdfWriter.addPage(pageObj)

                # # Recorre todas las páginas del documento 2
                # for pageNum in range(pdf2Reader.numPages):
                #     pageObj = pdf2Reader.getPage(pageNum)
                #     pdfWriter.addPage(pageObj)
                #

                # Recorre todas las páginas del documento 4: Cronograma de actividades
                for pageNum in range(pdf4Reader.numPages):
                    pageObj = pdf4Reader.getPage(pageNum)
                    pdfWriter.addPage(pageObj)

                # Recorre todas las páginas del documento 3: Presupuesto
                for pageNum in range(pdf3Reader.numPages):
                    pageObj = pdf3Reader.getPage(pageNum)
                    pdfWriter.addPage(pageObj)

                # # Recorre todas las páginas del documento 6: Presupuesto cargado por el docente
                # for pageNum in range(pdf6Reader.numPages):
                #     pageObj = pdf6Reader.getPage(pageNum)
                #     pdfWriter.addPage(pageObj)


                # # Recorre todas las páginas del documento 5
                # for pageNum in range(pdf5Reader.numPages):
                #     pageObj = pdf5Reader.getPage(pageNum)
                #     pdfWriter.addPage(pageObj)

                # Luego de haberse copiado todas las paginas de todos los documentos, se las escribe en el documento en blanco
                fecha = datetime.now().date()
                hora = datetime.now().time()
                nombrearchivoresultado = 'documento' + fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__() + '.pdf'
                pdfOutputFile = open(directorio + "/" + nombrearchivoresultado, "wb")
                pdfWriter.write(pdfOutputFile)

                # Borro los documento individuales creados a exepción del archcivo del proyecto cargado por el docente
                os.remove(archivo1)
                os.remove(archivo3)
                os.remove(archivo4)
                # os.remove(archivo5)

                pdfOutputFile.close()

                # Actualizo el nombre del documento del proyecto
                if 'tipo' not in request.POST:
                    proyecto.archivodocumento = 'proyectoinvestigacion/documentos/' + nombrearchivoresultado
                    proyecto.documentogenerado = True
                    proyecto.archivodocumentofirmado = None
                    # proyecto.archivodocumentosindatint = None
                    # proyecto.estadodocumentofirmado = 1
                else:
                    proyecto.archivodocumentoact = 'proyectoinvestigacion/documentos/' + nombrearchivoresultado
                proyecto.save(request)

                if 'tipo' not in request.POST:
                    # Crea el historial del archivo
                    historialarchivo = ProyectoInvestigacionHistorialArchivo(
                        proyecto=proyecto,
                        tipo=14,
                        archivo=proyecto.archivodocumento
                    )
                    historialarchivo.save(request)

                return JsonResponse({"result": "ok", "documento": proyecto.archivodocumento.url if 'tipo' not in request.POST else proyecto.archivodocumentoact.url})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar documento del proyecto. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'subirdocumento':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivo = request.FILES['archivodocumento']
                descripcionarchivo = 'Archivo del formato de inscripción firmado'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto el proyecto de investigación
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                archivo._name = generar_nombre("documentoinscripcionfirmado", archivo._name)

                proyecto.archivodocumentofirmado = archivo
                proyecto.save(request)

                # Crea el historial del archivo
                historialarchivo = ProyectoInvestigacionHistorialArchivo(
                    proyecto=proyecto,
                    tipo=11,
                    archivo=proyecto.archivodocumentofirmado
                )
                historialarchivo.save(request)

                log(u'%s subió documento inscripción de proyecto firmado: %s' % (persona, proyecto), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True, "id": encrypt(proyecto.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'aprobarproyecto':
            try:
                if not 'idproyecto' in request.POST and not 'idresolucion':
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                proyectoinvestigacion = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idproyecto'])))
                resolucionaprobacion = ConvocatoriaResolucionAprobacionProyecto.objects.get(pk=int(encrypt(request.POST['idresolucion'])))

                estado = int(request.POST['estado'])
                observacion = request.POST['observacion'].strip().upper() if 'observacion' in request.POST else 'APROBADO POR OCAS'

                # Actualizo el proyecto
                proyectoinvestigacion.estado_id = estado

                if estado == 35:
                    proyectoinvestigacion.fechainicio = request.POST['fechainicio']
                    proyectoinvestigacion.fechafinplaneado = request.POST['fechafin']
                    proyectoinvestigacion.fechaaprobacion = resolucionaprobacion.fecha
                    proyectoinvestigacion.aprobado = 1
                    proyectoinvestigacion.resolucionaprobacion = resolucionaprobacion
                else:
                    proyectoinvestigacion.fechainicio = None
                    proyectoinvestigacion.fechafinplaneado = None
                    proyectoinvestigacion.aprobado = 2
                    proyectoinvestigacion.resolucionaprobacion = None
                    proyectoinvestigacion.fechaaprobacion = datetime.now()

                proyectoinvestigacion.save(request)

                # Creo el recorrido del proyecto
                recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                           fecha=datetime.now().date(),
                                                           observacion=observacion,
                                                           estado_id=estado
                                                           )
                recorrido.save(request)

                # Envio de e-mail de notificacion al solicitante
                listacuentascorreo = [29]  # investigacion@unemi.edu.ec

                lista_email_envio = []
                lista_email_cco = []

                for integrante in proyectoinvestigacion.integrantes_proyecto():
                    lista_email_envio += integrante.persona.lista_emails_envio()
                    break

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                if estado == 35:
                    tituloemail = "Propuesta de Proyecto de Investigación - Aprobada"
                    tiponotificacion = "APROBADA"
                else:
                    tituloemail = "Propuesta de Proyecto de Investigación - Descartada"
                    tiponotificacion = "DESCARTADA"

                lista_archivos_adjuntos = []
                titulo = "Proyectos de Investigación"

                send_html_mail(tituloemail,
                               "emails/propuestaproyectoinvestigacion.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimada' if proyectoinvestigacion.profesor.persona.sexo_id == 1 else 'Estimado',
                                'nombrepersona': proyectoinvestigacion.profesor.persona.nombre_completo_inverso(),
                                'observaciones': observacion,
                                'proyecto': proyectoinvestigacion
                                },
                               lista_email_envio,  # Destinatarioa
                               lista_email_cco,  # Copia oculta
                               lista_archivos_adjuntos,  # Adjunto(s)
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                if estado == 35:
                    log(u'Aprobó propuesta de proyecto de investigación: %s' % (proyectoinvestigacion), request, "edit")
                else:
                    log(u'Descartó propuesta de proyecto de investigación: %s' % (proyectoinvestigacion), request, "edit")

                return JsonResponse({"result": "ok", "idp": request.POST['idproyecto']})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'validarcronograma':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                # Consulto el proyecto
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Obtengo los valores del formulario
                estadocronograma = int(request.POST['estadocronograma'])
                observacion = request.POST['observacion'].strip().upper()

                # Actualizo el proyecto
                proyecto.estadocronograma = estadocronograma
                proyecto.observacion = observacion
                proyecto.save(request)

                # Si el estado es validado, debo asignar estado EN EJECUCIÓN al proyecto
                if estadocronograma == 3:
                    # Si la fecha actual es mayor o igual a fecha de inicio del proyecto
                    if datetime.now().date() >= proyecto.fechainicio and proyecto.estado.valor != 20:
                        # Obtengo el estado EN EJECUCIÓN
                        estado = obtener_estado_solicitud(3, 20)

                        # Actualizo el proyecto
                        proyecto.estado = estado
                        proyecto.ejecucion = 1
                        proyecto.save(request)

                        # Creo el recorrido del proyecto
                        recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                   fecha=datetime.now().date(),
                                                                   observacion='PROYECTO EN EJECUCIÓN',
                                                                   estado=estado
                                                                   )
                        recorrido.save(request)

                # Notificar por e-mail al director
                listacuentascorreo = [29]  # investigacion@unemi.edu.ec

                lista_email_envio = []
                lista_email_cco = []

                for integrante in proyecto.integrantes_proyecto():
                    lista_email_envio += integrante.persona.lista_emails_envio()
                    break

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                if estadocronograma == 3:
                    tituloemail = "Cronograma de Actividades de Proyecto de Investigación - Validado"
                    tiponotificacion = "CRONVALIDA"
                else:
                    tituloemail = "Novedades Cronograma de Actividades de Proyecto de Investigación"
                    tiponotificacion = "CRONNOVEDAD"

                lista_archivos_adjuntos = []
                titulo = "Proyectos de Investigación"

                send_html_mail(tituloemail,
                               "emails/propuestaproyectoinvestigacion.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimada' if proyecto.profesor.persona.sexo_id == 1 else 'Estimado',
                                'nombrepersona': proyecto.profesor.persona.nombre_completo_inverso(),
                                'proyecto': proyecto,
                                'observaciones': observacion
                                },
                               lista_email_envio,  # Destinatarioa
                               lista_email_cco,  # Copia oculta
                               lista_archivos_adjuntos,  # Adjunto(s)
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                if estadocronograma == 3:
                    log(u'%s validó cronograma de actividades de proyecto de investigación [ %s ]' % (persona, proyecto), request, "edit")
                else:
                    log(u'%s registró novedades en cronograma de actividades de proyecto de investigación [ %s ]' % (persona, proyecto), request, "edit")

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al actualizar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'subirevidencia':
            try:
                if not 'entregable' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos", "tipomensaje": "danger"})

                entregable = ProyectoInvestigacionCronogramaEntregable.objects.get(pk=int(request.POST['entregable']))
                retraso = request.POST['retrasada']
                archivo = request.FILES['archivoevidencia']
                descripcionarchivo = 'Archivo de la evidencia'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['*'], '10MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "mensaje": resp["mensaje"], "tipomensaje": "warning"})

                archivo._name = generar_nombre("evidenciaproyecto", archivo._name)

                # Guardo la evidencia
                evidenciaactividad = ProyectoInvestigacionActividadEvidencia(
                    entregable=entregable,
                    fecha=datetime.now().date(),
                    archivo=archivo,
                    retraso=False if retraso == 'NO' else True,
                    descripcion=request.POST['descripcionevidencia'].strip()
                )

                evidenciaactividad.save(request)

                # Crea el historial del archivo
                historialevidencia = ProyectoInvestigacionHistorialActividadEvidencia(
                    entregable=entregable,
                    fecha=datetime.now().date(),
                    archivo=evidenciaactividad.archivo,
                    descripcion=evidenciaactividad.descripcion
                )
                historialevidencia.save(request)

                log(u'Agregó evidencia al entregable de la actividad: %s' % (entregable), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg, "tipomensaje": "danger"})

        elif action == 'editevidencia':
            try:
                if not 'idevidencia' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                evidenciaactividad = ProyectoInvestigacionActividadEvidencia.objects.get(pk=int(request.POST['idevidencia']))

                # En caso de haber ya sido revisada por coordinación de investigación
                if evidenciaactividad.estado != 1 and evidenciaactividad.estado != 4:
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede editar la evidencia porque ya fue revisada por Investigación"})

                if 'archivoevidenciaupdate' in request.FILES:
                    archivo = request.FILES['archivoevidenciaupdate']
                    descripcionarchivo = 'Archivo de la evidencia'

                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['*'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"], "tipomensaje": "warning"})

                    archivo._name = generar_nombre("evidenciaproyecto", archivo._name)

                # Actualizo la evidencia
                evidenciaactividad.fecha = datetime.now().date()
                evidenciaactividad.descripcion = request.POST['descripcionevidenciaupdate'].strip()
                evidenciaactividad.estado = 1
                evidenciaactividad.observacion = ""

                if 'archivoevidenciaupdate' in request.FILES:
                    evidenciaactividad.archivo = archivo

                evidenciaactividad.save(request)

                # Crea el historial del archivo
                historialevidencia = ProyectoInvestigacionHistorialActividadEvidencia(
                    entregable=evidenciaactividad.entregable,
                    fecha=datetime.now().date(),
                    archivo=evidenciaactividad.archivo,
                    descripcion=evidenciaactividad.descripcion
                )
                historialevidencia.save(request)

                # Actualizo la observación ingresada por investigación para la actividad
                actividad = evidenciaactividad.entregable.actividad
                actividad.observacioninv = ''
                actividad.save(request)

                log(u'Actualizó evidencia al entregable de la actividad: %s' % (evidenciaactividad), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg, "tipomensaje": "danger"})

        elif action == 'revisarevidencias':
            try:
                if not 'idactividad' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                actividad = ProyectoInvestigacionCronogramaActividad.objects.get(pk=int(encrypt(request.POST['idactividad'])))

                # Ontengo los valores del formulario
                porcentajeejecucion = request.POST['porcentajeejecucion']
                observacion = request.POST['observacion'].strip().upper()

                # Obtengo los valores de los campos tipo arreglo del formulario
                idevidencias = request.POST.getlist('idevidencia[]')
                estados = request.POST.getlist('estadoevidencia[]')
                observaciones = request.POST.getlist('observacionevidencia[]')

                # Verifico que las evidencias no hayan sido eliminadas
                for idevidencia in idevidencias:
                    if ProyectoInvestigacionActividadEvidencia.objects.values("id").filter(pk=idevidencia, status=False).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"No se puede guardar, uno o varias evidencias han sido eliminadas"})

                # Guardo registro de la revisión
                revisionactividad = ProyectoInvestigacionRevisionActividad(
                    actividad=actividad,
                    fecha=datetime.now().date(),
                    persona=persona,
                    porcentaje=porcentajeejecucion,
                    observacion=observacion,
                    confirmada=False
                )
                revisionactividad.save(request)
                
                # Guardo detalles de la revisión y actualizo estado de cada evidencia
                for idevidencia, estado, observacion in zip(idevidencias, estados, observaciones):
                    # Consulto evidencia
                    evidencia = ProyectoInvestigacionActividadEvidencia.objects.get(pk=idevidencia)

                    # Guardo detalle
                    detallerevision = ProyectoInvestigacionRevisionActividadDetalle(
                        revisionactividad=revisionactividad,
                        evidencia=evidencia,
                        estado=estado,
                        observacion=observacion.strip().upper()
                    )
                    detallerevision.save(request)

                    # Actualizo el estado de la evidencia a EN REVISIÓN
                    evidencia.estado = 5
                    evidencia.save(request)

                log(u'Agregó revisión de evidencias de actividad de proyecto de investigación: %s' % (actividad), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'confirmarrevisionevidencias':
            try:
                if not 'idrevision' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                revisionactividad = ProyectoInvestigacionRevisionActividad.objects.get(pk=int(encrypt(request.POST['idrevision'])))
                actividad = revisionactividad.actividad

                # Ontengo los valores del formulario
                porcentajeejecucion = request.POST['porcentajeejecucionedit']
                observacion = request.POST['observacionedit'].strip().upper()

                # Obtengo los valores de los campos tipo arreglo del formulario
                iddetalles = request.POST.getlist('iddetalleedit[]')
                idevidencias = request.POST.getlist('idevidenciaedit[]')
                estados = request.POST.getlist('estadoevidenciaedit[]')
                observaciones = request.POST.getlist('observacionevidenciaedit[]')

                # Actualizo registro de la revisión
                revisionactividad.porcentaje = porcentajeejecucion
                revisionactividad.observacion = observacion
                revisionactividad.confirmada = True
                revisionactividad.save(request)

                # Actualizo actividad: en caso de que porcentaje sea igual a la ponderación se asigna estado FINALIZADA
                actividad.porcentajeejecucion = porcentajeejecucion
                actividad.observacioninv = observacion

                if Decimal(porcentajeejecucion).quantize(Decimal('.01')) == actividad.ponderacion:
                    actividad.estado = 3

                actividad.save(request)

                # Actualizo detalles de la revisión y estado de cada evidencia
                for iddetalle, idevidencia, estado, observacion in zip(iddetalles, idevidencias, estados, observaciones):
                    # Consulto detalle de revisión
                    detallerevision = ProyectoInvestigacionRevisionActividadDetalle.objects.get(pk=iddetalle)
                    evidencia = detallerevision.evidencia

                    # Actualizo detalle de revision
                    detallerevision.estado = estado
                    detallerevision.observacion = observacion.strip().upper()
                    detallerevision.save(request)

                    # Actualizo la evidencia
                    evidencia.estado = estado
                    evidencia.observacion = observacion.strip().upper()
                    evidencia.save(request)


                # Envio de e-mail de notificacion al solicitante
                listacuentascorreo = [18]  # posgrado@unemi.edu.ec

                lista_email_envio = []
                # lista_email_envio.append('mreinosos@unemi.edu.ec')
                # lista_email_envio.append('olopezn@unemi.edu.ec')

                proyectoinvestigacion = actividad.objetivo.proyecto
                for integrante in proyectoinvestigacion.integrantes_proyecto():
                    lista_email_envio += integrante.persona.lista_emails_envio()

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                # cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
                #
                # tituloemail = "Revisión de Evidencias de Proyecto de Investigación"
                # tiponotificacion = "REVISIONEVIDENCIAS"
                #
                # send_html_mail(tituloemail,
                #                "emails/notificacion_propuesta_proyecto_investigacion.html",
                #                {'sistema': u'SGA - UNEMI',
                #                 'fecha': fechaenvio,
                #                 'hora': horaenvio,
                #                 'tiponotificacion': tiponotificacion,
                #                 'tituloproyecto': proyectoinvestigacion.titulo,
                #                 'actividad': actividad.actividad,
                #                 'detallesrevision': revisionactividad.detalle_revision(),
                #                 'porcentajeejecucion': revisionactividad.porcentaje,
                #                 'observaciones': revisionactividad.observacion,
                #                 't': miinstitucion()
                #                 },
                #                lista_email_envio,
                #                ['isaltosm@unemi.edu.ec'],
                #                [],
                #                cuenta=CUENTAS_CORREOS[cuenta][1]
                #                )

                log(u'Confirmó revisión de evidencias de actividad de proyecto de investigación: %s' % (actividad), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'asignarrevisorinformes':
            try:
                if not 'idproyecto' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                proyectoinvestigacion = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idproyecto'])))
                nuevo = False if proyectoinvestigacion.verificainforme else True
                verificainforme = int(request.POST['personaverifica'])
                apruebainforme = int(request.POST['personaaprueba'])

                # Actualiza los revisores
                proyectoinvestigacion.verificainforme_id = verificainforme
                proyectoinvestigacion.apruebainforme_id = apruebainforme
                proyectoinvestigacion.save(request)

                if nuevo:
                    log(u'Agregó revisores de informes de proyecto de investigación: %s' % (proyectoinvestigacion), request, "add")
                else:
                    log(u'Editó revisores de informes de proyecto de investigación: %s' % (proyectoinvestigacion), request, "edit")

                return JsonResponse({"result": "ok", "idp": request.POST['idproyecto']})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'verificarpropuestas':
            try:
                if ProyectoInvestigacion.objects.values('id').filter(status=True, convocatoria_id=int(encrypt(request.POST['idc']))).exists():
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "No existen registros de propuestas de proyectos de investigación"})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'listadogeneral':
            try:
                __author__ = 'Unemi'

                convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.POST['idc'])))

                fuentenormal = easyxtitulo = easyxf(
                    'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                titulo = easyxf(
                    'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                titulo2 = easyxf(
                    'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                fuentecabecera = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                fuentenormal = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentenormalwrap = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentenormalwrap.alignment.wrap = True
                fuentenormalcent = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                fuentemoneda = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str=' "$" #,##0.00')
                fuentefecha = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                    num_format_str='yyyy-mm-dd')
                fuentenumerodecimal = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str='#,##0.00')
                fuentenumeroentero = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('PropuestProyGeneral')
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=propuestas_proyectos_general_' + random.randint(1, 10000).__str__() + '.xls'

                ws.write_merge(0, 0, 0, 18, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                ws.write_merge(1, 1, 0, 18, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
                ws.write_merge(2, 2, 0, 18, 'COORDINACIÓN DE INVESTIGACIÓN', titulo2)
                ws.write_merge(3, 3, 0, 18, 'CONVOCATORIA ' + convocatoria.descripcion, titulo2)
                ws.write_merge(4, 4, 0, 18, 'LISTADO GENERAL DE PROPUESTAS DE PROYECTOS DE INVESTIGACIÓN', titulo2)

                row_num = 6
                columns = [
                    (u"#", 800),
                    (u"FECHA REGISTRO", 3500),
                    (u"CÓDIGO", 3500),
                    (u"CATEGORÍA", 6000),
                    (u"TÍTULO", 12000),
                    (u"LÍNEA DE INVESTIGACIÓN", 10000),
                    (u"COBERTURA", 3500),
                    (u"DIRECTOR", 8000),
                    (u"E-MAIL UNEMI", 5000),
                    (u"E-MAIL PERSONAL", 5000),
                    (u"TELÉFONO", 5000),
                    (u"CELULAR", 5000),
                    (u"TIEMPO EJECUCIÓN MESES", 3500),
                    (u"FECHA INICIO", 3500),
                    (u"FECHA FIN PLANEADA", 3500),
                    (u"FECHA FIN REAL", 3500),
                    (u"TIPO", 3000),
                    (u"TOTAL PRESUPUESTO", 5000),
                    (u"ESTADO", 5000)
                ]
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                    ws.col(col_num).width = columns[col_num][1]

                proyectos = ProyectoInvestigacion.objects.filter(status=True, convocatoria=convocatoria).order_by('-id')

                c = 0
                for proyecto in proyectos:
                    row_num += 1
                    c += 1

                    ws.write(row_num, 0, c, fuentenumeroentero)
                    ws.write(row_num, 1, proyecto.fecha_creacion, fuentefecha)
                    ws.write(row_num, 2, proyecto.codigo, fuentenormal)
                    ws.write(row_num, 3, proyecto.get_categoria_display(), fuentenormal)
                    ws.write(row_num, 4, proyecto.titulo, fuentenormal)
                    ws.write(row_num, 5, proyecto.lineainvestigacion.nombre, fuentenormal)
                    ws.write(row_num, 6, proyecto.get_tipocobertura_display(), fuentenormal)
                    ws.write(row_num, 7, proyecto.profesor.persona.nombre_completo_inverso(), fuentenormal)
                    ws.write(row_num, 8, proyecto.profesor.persona.email, fuentenormal)
                    ws.write(row_num, 9, proyecto.profesor.persona.emailinst, fuentenormal)
                    ws.write(row_num, 10, proyecto.profesor.persona.telefono_conv, fuentenormal)
                    ws.write(row_num, 11, proyecto.profesor.persona.telefono, fuentenormal)
                    ws.write(row_num, 12, proyecto.tiempomes, fuentenormalcent)
                    ws.write(row_num, 13, proyecto.fechainicio, fuentefecha)
                    ws.write(row_num, 14, proyecto.fechafinplaneado, fuentefecha)
                    ws.write(row_num, 15, proyecto.fechafinreal, fuentefecha)
                    ws.write(row_num, 16, proyecto.get_tipo_display(), fuentenormal)
                    ws.write(row_num, 17, proyecto.presupuesto, fuentemoneda)
                    ws.write(row_num, 18, proyecto.estado.descripcion, fuentenormalcent)

                wb.save(response)
                return response
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'addevaluador':
            try:
                tipopersona = int(request.POST['tipopersona'])
                personaintegrante = int(request.POST['persona_select2'])
                propuestaproyecto = 'perfpropuestaproyecto' in request.POST
                proyectofinalizado = 'perfproyectofinalizado' in request.POST
                obrarelevancia = 'perfobrarelevancia' in request.POST

                if tipopersona == 1:
                    persona_id = Profesor.objects.get(pk=personaintegrante).persona.id
                else:
                    persona_id = Externo.objects.get(pk=personaintegrante).persona.id
                    # propuestaproyecto = True

                # validar que no esté agregado como evaluador de proyectos
                if EvaluadorProyecto.objects.filter(status=True, persona_id=persona_id).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"La persona ya tiene registro de evaluador de proyectos"})

                evaluadorproyecto = EvaluadorProyecto(
                    tipo=1 if int(tipopersona) == 1 else 2,
                    tipopersona=tipopersona,
                    persona_id=persona_id,
                    profesor_id=personaintegrante if tipopersona == 1 else None,
                    inscripcion_id=personaintegrante if tipopersona == 2 else None,
                    administrativo_id=personaintegrante if tipopersona == 3 else None,
                    externo_id=personaintegrante if tipopersona == 4 else None,
                    propuestaproyecto=propuestaproyecto,
                    proyectofinalizado=proyectofinalizado,
                    obrarelevancia=obrarelevancia
                )
                evaluadorproyecto.save(request)

                log(u'Agregó evaluador de proyectos de investigación y obras de relevancia: %s' % (evaluadorproyecto), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'addevaluadorexterno':
            try:
                f = EvaluadorExternoForm(request.POST, request.FILES)

                if f.is_valid():
                    if not f.cleaned_data['cedula'] and not f.cleaned_data['pasaporte']:
                        return JsonResponse({"result": "bad", "mensaje": u"Ingrese número de cédula o pasaporte"})

                    # Verifica si existe la persona
                    if f.cleaned_data['cedula']:
                        if Persona.objects.values('id').filter(Q(cedula=f.cleaned_data['cedula'])|Q(pasaporte=f.cleaned_data['cedula']), status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"La persona ya está registrada en la base de datos"})

                    if f.cleaned_data['pasaporte']:
                        if Persona.objects.values('id').filter(Q(cedula=f.cleaned_data['pasaporte'])|Q(pasaporte=f.cleaned_data['pasaporte']), status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"La persona ya está registrada en la base de datos"})

                    if not f.cleaned_data['propuestaproyecto'] and not f.cleaned_data['obrarelevancia']:
                        return JsonResponse({"result": "bad", "mensaje": u"Seleccione un perfil de evaluación"})

                    # Obtiene los valores de los arreglos del detalle de formación académica
                    nfilas_ca_FA = json.loads(request.POST['lista_items1'])# Números de filas que tienen lleno el campo archivo
                    nfilas_FA = request.POST.getlist('nfila_FA[]')# Todos los número de filas

                    # Registros de formación académica es obligatorio
                    # if not nfilas_FA:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Ingrese los datos de la formación académica"})

                    titulos_FA = request.POST.getlist('tituloacademico_FA[]')
                    universidades_FA = request.POST.getlist('universidad_FA[]')
                    fechas_FA = request.POST.getlist('fechaobtencion_FA[]')
                    paises_FA = request.POST.getlist('pais_FA[]')
                    archivos_FA = request.FILES.getlist('archivo_FA[]')

                    # if not titulos_FA:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Ingrese los datos de la formación académica"})

                    tituloenblanco = [dato for dato in titulos_FA if int(dato.strip()) == 0]
                    universidadenblanco = [dato for dato in universidades_FA if int(dato.strip()) == 0]
                    fechaenblanco = [dato for dato in fechas_FA if dato.strip() == '']
                    paisenblanco = [dato for dato in paises_FA if int(dato.strip()) == 0]

                    # Si existen campos en blanco de formación académica
                    if tituloenblanco or universidadenblanco or fechaenblanco or paisenblanco:
                        return JsonResponse({"result": "bad", "mensaje": u"Los datos de los registros de formación académica son obligatorios excepto el archivo"})

                    # Valido los archivos cargados de formación académica
                    for nfila, archivo in zip(nfilas_ca_FA, archivos_FA):
                        descripcionarchivo = 'Formación académica'
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"] + " en la fila # "+str(nfila['cfila'])})

                    # Obtiene los valores de los arreglos del detalle de experiencia académica
                    nfilas_ca_EXP = json.loads(request.POST['lista_items2'])  # Números de filas que tienen lleno el campo archivo
                    nfilas_EXP = request.POST.getlist('nfila_EXP[]')  # Todos los número de filas

                    # Si agregó filas en tabla de experiencia
                    if nfilas_EXP:
                        cargos_EXP = request.POST.getlist('cargo_EXP[]')
                        instituciones_EXP = request.POST.getlist('institucion_EXP[]')
                        fechasinicio_EXP = request.POST.getlist('fechainicio_EXP[]')
                        fechasfin_EXP = request.POST.getlist('fechafin_EXP[]')
                        archivos_EXP = request.FILES.getlist('archivo_EXP[]')

                        if not cargos_EXP:
                            return JsonResponse({"result": "bad", "mensaje": u"Ingrese los datos de la experiencia académica"})

                        cargoenblanco = [dato for dato in cargos_EXP if dato.strip() == '']
                        institucionenblanco = [dato for dato in instituciones_EXP if dato.strip() == '']
                        fechainicioenblanco = [dato for dato in fechasinicio_EXP if dato.strip() == '']
                        fechafinenblanco = [dato for dato in fechasfin_EXP if dato.strip() == '']

                        # Si existen campos en blanco de la experiencia
                        if cargoenblanco or institucionenblanco or fechainicioenblanco or fechafinenblanco:
                            return JsonResponse({"result": "bad", "mensaje": u"Los datos de los registros de experiencia académica son obligatorios excepto el archivo"})

                        # Valido los archivos cargados de experiencia
                        for nfila, archivo in zip(nfilas_ca_EXP, archivos_EXP):
                            descripcionarchivo = 'Experiencia académica'
                            resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                            if resp['estado'] != "OK":
                                return JsonResponse({"result": "bad", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila'])})

                    # Obtiene los valores de los arreglos del detalle de artículos
                    nfilas_ca_ART = json.loads(request.POST['lista_items3'])  # Números de filas que tienen lleno el campo archivo
                    nfilas_ART = request.POST.getlist('nfila_ART[]')  # Todos los número de filas

                    # Si agregó filas en la tabla de artículos
                    if nfilas_ART:
                        titulos_ART = request.POST.getlist('titulo_ART[]')
                        revistas_ART = request.POST.getlist('revista_ART[]')
                        basesindexadas_ART = request.POST.getlist('baseindexada_ART[]')
                        fechaspublica_ART = request.POST.getlist('fechapublica_ART[]')
                        tiposautor_ART = request.POST.getlist('tipoautor_ART[]')
                        archivos_ART = request.FILES.getlist('archivo_ART[]')

                        if not titulos_ART:
                            return JsonResponse({"result": "bad", "mensaje": u"Ingrese los datos de artículos publicados"})

                        tituloenblanco = [dato for dato in titulos_ART if dato.strip() == '']
                        revistaenblanco = [dato for dato in revistas_ART if dato.strip() == '']
                        baseenblanco = [dato for dato in basesindexadas_ART if dato.strip() == '']
                        fechaenblanco = [dato for dato in fechaspublica_ART if dato.strip() == '']
                        tipoautorenblanco = [dato for dato in tiposautor_ART if int(dato.strip()) == 0]

                        # Si existen campos en blanco de articulos
                        if tituloenblanco or revistaenblanco or baseenblanco or fechaenblanco or tipoautorenblanco:
                            return JsonResponse({"result": "bad", "mensaje": u"Los datos de los registros de artículos son obligatorios excepto el archivo"})

                        # Valido los archivos cargados de articulos
                        for nfila, archivo in zip(nfilas_ca_ART, archivos_ART):
                            descripcionarchivo = 'Artículos'
                            resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                            if resp['estado'] != "OK":
                                return JsonResponse({"result": "bad", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila'])})

                    # Obtiene los valores de los arreglos del detalle de ponencias
                    nfilas_ca_PON = json.loads(request.POST['lista_items4'])  # Números de filas que tienen lleno el campo archivo
                    nfilas_PON = request.POST.getlist('nfila_PON[]')  # Todos los número de filas

                    # Si agregó filas en la tabla de ponencias
                    if nfilas_PON:
                        titulos_PON = request.POST.getlist('titulo_PON[]')
                        congresos_PON = request.POST.getlist('congreso_PON[]')
                        fechasinicio_PON = request.POST.getlist('fechainiciocongreso_PON[]')
                        fechasfin_PON = request.POST.getlist('fechafincongreso_PON[]')
                        paises_PON = request.POST.getlist('pais_PON[]')
                        ciudades_PON = request.POST.getlist('ciudad_PON[]')
                        tiposautor_PON = request.POST.getlist('tipoautor_PON[]')
                        archivos_PON = request.FILES.getlist('archivo_PON[]')

                        if not titulos_PON:
                            return JsonResponse({"result": "bad", "mensaje": u"Ingrese los datos de ponencias"})

                        tituloenblanco = [dato for dato in titulos_PON if dato.strip() == '']
                        congresoenblanco = [dato for dato in congresos_PON if dato.strip() == '']
                        fechainicioenblanco = [dato for dato in fechasinicio_PON if dato.strip() == '']
                        fechafinenblanco = [dato for dato in fechasfin_PON if dato.strip() == '']
                        paisenblanco = [dato for dato in paises_PON if int(dato.strip()) == 0]
                        ciudadenblanco = [dato for dato in ciudades_PON if dato.strip() == '']
                        tipoautorenblanco = [dato for dato in tiposautor_PON if int(dato.strip()) == 0]

                        # Si existen campos en blanco de ponencias
                        if tituloenblanco or congresoenblanco or fechainicioenblanco or fechafinenblanco or paisenblanco or ciudadenblanco or tipoautorenblanco:
                            return JsonResponse({"result": "bad", "mensaje": u"Los datos de los registros de ponencias son obligatorios excepto el archivo"})

                        # Valido los archivos cargados de ponencias
                        for nfila, archivo in zip(nfilas_ca_PON, archivos_PON):
                            descripcionarchivo = 'Ponencias'
                            resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                            if resp['estado'] != "OK":
                                return JsonResponse({"result": "bad", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila'])})


                    # Obtiene los valores de los arreglos del detalle de libros
                    nfilas_ca_LIB = json.loads(request.POST['lista_items5'])  # Números de filas que tienen lleno el campo archivo
                    nfilas_LIB = request.POST.getlist('nfila_LIB[]')  # Todos los número de filas

                    # Si agregó filas en tabla de libros
                    if nfilas_LIB:
                        titulos_LIB = request.POST.getlist('titulo_LIB[]')
                        codigosisbn_LIB = request.POST.getlist('codigoisbn_LIB[]')
                        editoriales_LIB = request.POST.getlist('editorial_LIB[]')
                        fechaspublicacion_LIB = request.POST.getlist('fechapublicacion_LIB[]')
                        tiposautor_LIB = request.POST.getlist('tipoautor_LIB[]')
                        archivos_LIB = request.FILES.getlist('archivo_LIB[]')

                        if not titulos_LIB:
                            return JsonResponse({"result": "bad", "mensaje": u"Ingrese los datos de libros"})

                        tituloenblanco = [dato for dato in titulos_LIB if dato.strip() == '']
                        codigoenblanco = [dato for dato in codigosisbn_LIB if dato.strip() == '']
                        editorialenblanco = [dato for dato in editoriales_LIB if dato.strip() == '']
                        fechapubfinenblanco = [dato for dato in fechaspublicacion_LIB if dato.strip() == '']
                        tipoautorenblanco = [dato for dato in tiposautor_LIB if int(dato.strip()) == 0]

                        # Si existen campos en blanco de libros
                        if tituloenblanco or codigoenblanco or editorialenblanco or fechapubfinenblanco or tipoautorenblanco:
                            return JsonResponse({"result": "bad", "mensaje": u"Los datos de los registros de libros son obligatorios excepto el archivo"})

                        # Valido los archivos cargados de libros
                        for nfila, archivo in zip(nfilas_ca_LIB, archivos_LIB):
                            descripcionarchivo = 'Libros'
                            resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                            if resp['estado'] != "OK":
                                return JsonResponse({"result": "bad", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila'])})

                    # Obtiene los valores de los arreglos del detalle de capítulos de libros
                    nfilas_ca_CAP = json.loads(request.POST['lista_items6'])  # Números de filas que tienen lleno el campo archivo
                    nfilas_CAP = request.POST.getlist('nfila_CAP[]')  # Todos los número de filas

                    # Si agregó filas en tabla de capítulos de libros
                    if nfilas_CAP:
                        tituloscapitulo_CAP = request.POST.getlist('titulocapitulo_CAP[]')
                        tituloslibro_CAP = request.POST.getlist('titulolibro_CAP[]')
                        codigosisbn_CAP = request.POST.getlist('codigoisbn_CAP[]')
                        editoriales_CAP = request.POST.getlist('editorial_CAP[]')
                        fechaspublicacion_CAP = request.POST.getlist('fechapublicacion_CAP[]')
                        tiposautor_CAP = request.POST.getlist('tipoautor_CAP[]')
                        archivos_CAP = request.FILES.getlist('archivo_CAP[]')

                        if not tituloscapitulo_CAP:
                            return JsonResponse({"result": "bad", "mensaje": u"Ingrese los datos de capítulos de libros"})

                        titulocapenblanco = [dato for dato in tituloscapitulo_CAP if dato.strip() == '']
                        titulolibenblanco = [dato for dato in tituloslibro_CAP if dato.strip() == '']
                        codigoenblanco = [dato for dato in codigosisbn_CAP if dato.strip() == '']
                        editorialenblanco = [dato for dato in editoriales_CAP if dato.strip() == '']
                        fechapubfinenblanco = [dato for dato in fechaspublicacion_CAP if dato.strip() == '']
                        tipoautorenblanco = [dato for dato in tiposautor_CAP if int(dato.strip()) == 0]

                        # Si existen campos en blanco de capitulos de libros
                        if titulocapenblanco or titulolibenblanco or codigoenblanco or editorialenblanco or fechapubfinenblanco or tipoautorenblanco:
                            return JsonResponse({"result": "bad", "mensaje": u"Los datos de los registros de capítulos de libros son obligatorios excepto el archivo"})

                        # Valido los archivos cargados de capítulos de libros
                        for nfila, archivo in zip(nfilas_ca_CAP, archivos_CAP):
                            descripcionarchivo = 'Caítulos de libros'
                            resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                            if resp['estado'] != "OK":
                                return JsonResponse({"result": "bad", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila'])})

                    # Obtiene los valores de los arreglos del detalle de proyectos de investigación
                    nfilas_ca_PROY = json.loads(request.POST['lista_items7'])  # Números de filas que tienen lleno el campo archivo
                    nfilas_PROY = request.POST.getlist('nfila_PROY[]')  # Todos los número de filas

                    # Si agregó filas en tabla de proyectos
                    if nfilas_PROY:
                        titulos_PROY = request.POST.getlist('titulo_PROY[]')
                        instituciones_PROY = request.POST.getlist('institucion_PROY[]')
                        funciones_PROY = request.POST.getlist('funcion_PROY[]')
                        fechasinicio_PROY = request.POST.getlist('fechainicio_PROY[]')
                        fechasfin_PROY = request.POST.getlist('fechafin_PROY[]')
                        archivos_PROY = request.FILES.getlist('archivo_PROY[]')

                        if not titulos_PROY:
                            return JsonResponse({"result": "bad", "mensaje": u"Ingrese los datos de los proyectos"})

                        tituloenblanco = [dato for dato in titulos_PROY if dato.strip() == '']
                        institucionenblanco = [dato for dato in instituciones_PROY if dato.strip() == '']
                        funcionenblanco = [dato for dato in funciones_PROY if int(dato.strip()) == 0]
                        fechainicioenblanco = [dato for dato in fechasinicio_PROY if dato.strip() == '']
                        fechafinenblanco = [dato for dato in fechasfin_PROY if dato.strip() == '']

                        # Si existen campos en blanco de capitulos de libros
                        if tituloenblanco or institucionenblanco or funcionenblanco or fechainicioenblanco or fechafinenblanco:
                            return JsonResponse({"result": "bad", "mensaje": u"Los datos de los registros de proyectos de investigación son obligatorios excepto el archivo"})

                        # Valido los archivos cargados de proyectos
                        for nfila, archivo in zip(nfilas_ca_PROY, archivos_PROY):
                            descripcionarchivo = 'Proyectos de investigación'
                            resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                            if resp['estado'] != "OK":
                                return JsonResponse({"result": "bad", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila'])})

                    # Guardo la persona
                    personaexterna = Persona(
                        nombres=f.cleaned_data['nombres'],
                        apellido1=f.cleaned_data['apellido1'],
                        apellido2=f.cleaned_data['apellido2'],
                        cedula=f.cleaned_data['cedula'],
                        pasaporte=f.cleaned_data['pasaporte'],
                        nacimiento=f.cleaned_data['nacimiento'],
                        sexo=f.cleaned_data['sexo'],
                        nacionalidad=f.cleaned_data['nacionalidad'],
                        email=f.cleaned_data['email'],
                        telefono=f.cleaned_data['telefono']
                    )
                    personaexterna.save(request)

                    # # Guardo el identificador ORCID en tabla red persona
                    # if f.cleaned_data['identificadororcid']:
                    #     redpersona = RedPersona(
                    #         tipo_id=1,
                    #         persona=personaexterna,
                    #         enlace=f.cleaned_data['identificadororcid']
                    #     )
                    #     redpersona.save(request)

                    # Guardo externo
                    externo = Externo(
                        persona=personaexterna,
                        nombrecomercial='',
                        institucionlabora=f.cleaned_data['institucionlabora'],
                        cargodesempena=f.cleaned_data['cargodesempena']
                    )
                    externo.save(request)

                    personaexterna.crear_perfil(externo=externo)
                    personaexterna.mi_perfil()
                    log(u'Agregó persona externa: %s' % (personaexterna), request, "add")

                    # Crear el usuario para el SGA/SAGEST, etc
                    nombreusuario = calculate_username(personaexterna)# Hay un error en esta funcion porque excluye persona
                    # personaexterna.emailinst = nombreusuario + '@unemi.edu.ec'
                    personaexterna.save(request)

                    #335 Grupo: INVESTIGACION EVALUADOR EXTERNO
                    generar_usuario(personaexterna, nombreusuario, 335)

                    # Guardar la formación académica
                    for nfila, titulo, universidad, fecha, pais in zip(nfilas_FA, titulos_FA, universidades_FA, fechas_FA, paises_FA):
                        # Guardo el titulo
                        tituloacademico = Titulacion(
                            persona=personaexterna,
                            titulo_id=titulo,
                            fechaobtencion=fecha,
                            pais_id=pais,
                            institucion_id=universidad
                        )
                        tituloacademico.save(request)

                        # Guardo el archivo del título
                        for nfilaarchi, archivo in zip(nfilas_ca_FA, archivos_FA):
                            # Si la fila del titulo es igual a la fila que contiene archivo
                            if int(nfilaarchi['nfila']) == int(nfila):
                                # actualizo campo archivo del registro creado
                                archivoreg = archivo
                                archivoreg._name = generar_nombre("titulacion_", archivoreg._name)
                                tituloacademico.archivo = archivoreg
                                tituloacademico.save(request)
                                break

                        log(u'Agregó título a la persona externa: %s - %s' % (personaexterna, tituloacademico), request, "add")

                    # Si agregó filas en tabla de experiencia
                    if nfilas_EXP:
                        for nfila, cargo, institucion, fechainicio, fechafin in zip(nfilas_EXP, cargos_EXP, instituciones_EXP, fechasinicio_EXP, fechasfin_EXP):
                            # Guardo la experiencia
                            experiencia = ExperienciaLaboral(
                                persona=personaexterna,
                                institucion=institucion,
                                cargo=cargo,
                                fechainicio=fechainicio,
                                fechafin=fechafin
                            )
                            experiencia.save(request)

                            # Guardo el archivo de la experiencia
                            for nfilaarchi, archivo in zip(nfilas_ca_EXP, archivos_EXP):
                                # Si la fila del titulo es igual a la fila que contiene archivo
                                if int(nfilaarchi['nfila']) == int(nfila):
                                    # actualizo campo archivo del registro creado
                                    archivoreg = archivo
                                    archivoreg._name = generar_nombre("experiencialaboral_", archivoreg._name)
                                    experiencia.archivo = archivoreg
                                    experiencia.save(request)
                                    break

                            log(u'Agregó experiencia a la persona externa: %s - %s' % (personaexterna, experiencia), request, "add")

                    # Si agregó filas en la tabla de artículos
                    if nfilas_ART:
                        for nfila, titulo, revista, bases, fechapublica, tipoautor in zip(nfilas_ART, titulos_ART, revistas_ART, basesindexadas_ART, fechaspublica_ART, tiposautor_ART):
                            # Guardo el artículo
                            articulo = ArticuloPersonaExterna(
                                externo=externo,
                                titulo=titulo,
                                revista=revista,
                                baseindexada=bases,
                                fechapublicacion=fechapublica,
                                tipoautor=tipoautor
                            )
                            articulo.save(request)

                            # Guardo el archivo del artículo
                            for nfilaarchi, archivo in zip(nfilas_ca_ART, archivos_ART):
                                # Si la fila del titulo es igual a la fila que contiene archivo
                                if int(nfilaarchi['nfila']) == int(nfila):
                                    # actualizo campo archivo del registro creado
                                    archivoreg = archivo
                                    archivoreg._name = generar_nombre("articulo_", archivoreg._name)
                                    articulo.archivo = archivoreg
                                    articulo.save(request)
                                    break

                            log(u'Agregó artículo a la persona externa: %s - %s' % (personaexterna, articulo), request, "add")

                    # Si agregó filas en la tabla de ponencias
                    if nfilas_PON:
                        for nfila, titulo, congreso, fechainicio, fechafin, pais, ciudad, tipoautor in zip(nfilas_PON, titulos_PON, congresos_PON, fechasinicio_PON, fechasfin_PON, paises_PON, ciudades_PON, tiposautor_PON):
                            # Guardo las ponencias
                            ponencia = PonenciaPersonaExterna(
                                externo=externo,
                                titulo=titulo,
                                congreso=congreso,
                                fechainicio=fechainicio,
                                fechafin=fechafin,
                                pais_id=pais,
                                ciudad=ciudad,
                                tipoautor=tipoautor
                            )
                            ponencia.save(request)

                            # Guardo el archivo de la ponencia
                            for nfilaarchi, archivo in zip(nfilas_ca_PON, archivos_PON):
                                # Si la fila del titulo es igual a la fila que contiene archivo
                                if int(nfilaarchi['nfila']) == int(nfila):
                                    # actualizo campo archivo del registro creado
                                    archivoreg = archivo
                                    archivoreg._name = generar_nombre("ponencia_", archivoreg._name)
                                    ponencia.archivo = archivoreg
                                    ponencia.save(request)
                                    break

                            log(u'Agregó ponencia a la persona externa: %s - %s' % (personaexterna, ponencia), request,"add")

                    # Si agregó filas en tabla de libros
                    if nfilas_LIB:
                        for nfila, titulo, codigoisbn, editorial, fechapublica, tipoautor in zip(nfilas_LIB, titulos_LIB, codigosisbn_LIB, editoriales_LIB, fechaspublicacion_LIB, tiposautor_LIB):
                            # Guardo el libro
                            libro = LibroPersonaExterna(
                                externo=externo,
                                tipo=1,
                                titulolibro=titulo,
                                titulocapitulo='',
                                codigoisbn=codigoisbn,
                                editorial=editorial,
                                fechapublicacion=fechapublica,
                                tipoautor=tipoautor
                            )
                            libro.save(request)

                            # Guardo el archivo del libro
                            for nfilaarchi, archivo in zip(nfilas_ca_LIB, archivos_LIB):
                                # Si la fila del titulo es igual a la fila que contiene archivo
                                if int(nfilaarchi['nfila']) == int(nfila):
                                    # actualizo campo archivo del registro creado
                                    archivoreg = archivo
                                    archivoreg._name = generar_nombre("libro_", archivoreg._name)
                                    libro.archivo = archivoreg
                                    libro.save(request)
                                    break

                            log(u'Agregó libro a la persona externa: %s - %s' % (personaexterna, libro), request,"add")

                    # Si agregó filas en tabla de capítulos de libros
                    if nfilas_CAP:
                        for nfila, titulocapitulo, titulolibro, codigoisbn, editorial, fechapublica, tipoautor in zip(nfilas_CAP, tituloscapitulo_CAP, tituloslibro_CAP, codigosisbn_CAP, editoriales_CAP, fechaspublicacion_CAP, tiposautor_CAP):
                            # Guardo el capítulo de libro
                            capitulolibro = LibroPersonaExterna(
                                externo=externo,
                                tipo=2,
                                titulolibro=titulolibro,
                                titulocapitulo=titulocapitulo,
                                codigoisbn=codigoisbn,
                                editorial=editorial,
                                fechapublicacion=fechapublica,
                                tipoautor=tipoautor
                            )
                            capitulolibro.save(request)

                            # Guardo el archivo del capítulo de libro
                            for nfilaarchi, archivo in zip(nfilas_ca_CAP, archivos_CAP):
                                # Si la fila del titulo es igual a la fila que contiene archivo
                                if int(nfilaarchi['nfila']) == int(nfila):
                                    # actualizo campo archivo del registro creado
                                    archivoreg = archivo
                                    archivoreg._name = generar_nombre("capitulolibro_", archivoreg._name)
                                    capitulolibro.archivo = archivoreg
                                    capitulolibro.save(request)
                                    break

                            log(u'Agregó capítulo de libro a la persona externa: %s - %s' % (personaexterna, capitulolibro), request, "add")

                    # Si agregó filas en tabla de proyectos
                    if nfilas_PROY:
                        for nfila, titulo, institucion, funcion, fechainicio, fechafin in zip(nfilas_PROY, titulos_PROY, instituciones_PROY, funciones_PROY, fechasinicio_PROY, fechasfin_PROY):
                            # Guardo el proyecto de investigación
                            proyectoinvestigacion = ProyectoInvestigacionPersonaExterna(
                                externo=externo,
                                titulo=titulo,
                                patrocinador=institucion,
                                funcion=funcion,
                                fechainicio=fechainicio,
                                fechafin=fechafin
                            )
                            proyectoinvestigacion.save(request)

                            # Guardo el archivo del proyecto externo
                            for nfilaarchi, archivo in zip(nfilas_ca_PROY, archivos_PROY):
                                # Si la fila del titulo es igual a la fila que contiene archivo
                                if int(nfilaarchi['nfila']) == int(nfila):
                                    # actualizo campo archivo del registro creado
                                    archivoreg = archivo
                                    archivoreg._name = generar_nombre("proyectoinvestigacion_", archivoreg._name)
                                    proyectoinvestigacion.archivo = archivoreg
                                    proyectoinvestigacion.save(request)
                                    break

                            log(u'Agregó proyecto de investigación a la persona externa: %s - %s' % (personaexterna, proyectoinvestigacion), request, "add")


                    # Guardo evaluador de proyecto
                    evaluadorproyecto = EvaluadorProyecto(
                        tipo=2,
                        tipopersona=4,
                        persona=personaexterna,
                        profesor=None,
                        inscripcion=None,
                        administrativo=None,
                        externo=externo,
                        propuestaproyecto=f.cleaned_data['propuestaproyecto'],
                        obrarelevancia=f.cleaned_data['obrarelevancia']
                    )
                    evaluadorproyecto.save(request)
                    log(u'Agregó evaluador de proyectos de investigación y obras de relevancia: %s' % (evaluadorproyecto), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    x = f.errors
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'editperfil':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                evaluadorproyecto = EvaluadorProyecto.objects.get(pk=int(encrypt(request.POST['id'])))

                propuestaproyecto = 'perfpropuestaproyecto' in request.POST
                proyectofinalizado = 'perfproyectofinalizado' in request.POST
                obrarelevancia = 'perfobrarelevancia' in request.POST

                evaluadorproyecto.propuestaproyecto = propuestaproyecto
                evaluadorproyecto.proyectofinalizado = proyectofinalizado
                evaluadorproyecto.obrarelevancia = obrarelevancia
                evaluadorproyecto.save(request)

                log(u'Editó perfil de evaluación del profesor: %s' % (evaluadorproyecto), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'editevaluadorexterno':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                f = EvaluadorExternoForm(request.POST, request.FILES)

                if f.is_valid():
                    if not f.cleaned_data['propuestaproyecto'] and not f.cleaned_data['obrarelevancia']:
                        return JsonResponse({"result": "bad", "mensaje": u"Seleccione un perfil de evaluación"})

                    # if not f.cleaned_data['cedula'] and not f.cleaned_data['pasaporte']:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Ingrese la cédula o pasaporte de la persona"})

                    # # Verifica si existe la persona
                    # if f.cleaned_data['cedula']:
                    #     if Persona.objects.values('id').filter(Q(cedula=f.cleaned_data['cedula']) | Q(pasaporte=f.cleaned_data['cedula']), status=True).exclude(pk=int(encrypt(request.POST['idper']))).exists():
                    #         return JsonResponse({"result": "bad", "mensaje": u"La persona ya está registrada en la base de datos"})
                    #
                    # if f.cleaned_data['pasaporte']:
                    #     if Persona.objects.values('id').filter(Q(cedula=f.cleaned_data['pasaporte']) | Q(pasaporte=f.cleaned_data['pasaporte']), status=True).exclude(pk=int(encrypt(request.POST['idper']))).exists():
                    #         return JsonResponse({"result": "bad", "mensaje": u"La persona ya está registrada en la base de datos"})

                    # Obtiene los valores de los arreglos del detalle de formación académica
                    nfilas_ca_FA = json.loads(request.POST['lista_items1'])# Números de filas que tienen lleno el campo archivo
                    nfilas_FA = request.POST.getlist('nfila_FA[]')# Todos los número de filas
                    idsregistro_FA = request.POST.getlist('idregistro_FA[]')# Todos los ids de los registros
                    idseliminados_FA = json.loads(request.POST['lista_items8'])  # Ids de los registros eliminados

                    # Registros de formación académica es obligatorio
                    # if not nfilas_FA:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Ingrese los datos de la formación académica"})

                    titulos_FA = request.POST.getlist('tituloacademico_FA[]')
                    universidades_FA = request.POST.getlist('universidad_FA[]')
                    fechas_FA = request.POST.getlist('fechaobtencion_FA[]')
                    paises_FA = request.POST.getlist('pais_FA[]')
                    archivos_FA = request.FILES.getlist('archivo_FA[]')

                    # if not titulos_FA:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Ingrese los datos de la formación académica"})

                    tituloenblanco = [dato for dato in titulos_FA if int(dato.strip()) == 0]
                    universidadenblanco = [dato for dato in universidades_FA if int(dato.strip()) == 0]
                    fechaenblanco = [dato for dato in fechas_FA if dato.strip() == '']
                    paisenblanco = [dato for dato in paises_FA if int(dato.strip()) == 0]

                    # Si existen campos en blanco de formación académica
                    if tituloenblanco or universidadenblanco or fechaenblanco or paisenblanco:
                        return JsonResponse({"result": "bad", "mensaje": u"Los datos de los registros de formación académica son obligatorios excepto el archivo"})

                    # Valido los archivos cargados de formación académica
                    for nfila, archivo in zip(nfilas_ca_FA, archivos_FA):
                        descripcionarchivo = 'Formación académica'
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"] + " en la fila # "+str(nfila['cfila'])})


                    # Obtiene los valores de los arreglos del detalle de experiencia académica
                    nfilas_ca_EXP = json.loads(request.POST['lista_items2'])  # Números de filas que tienen lleno el campo archivo
                    nfilas_EXP = request.POST.getlist('nfila_EXP[]')  # Todos los número de filas
                    idsregistro_EXP = request.POST.getlist('idregistro_EXP[]')  # Todos los ids de los registros
                    idseliminados_EXP = json.loads(request.POST['lista_items9'])  # Ids de los registros eliminados

                    # Si agregó filas en tabla de experiencia
                    if nfilas_EXP:
                        cargos_EXP = request.POST.getlist('cargo_EXP[]')
                        instituciones_EXP = request.POST.getlist('institucion_EXP[]')
                        fechasinicio_EXP = request.POST.getlist('fechainicio_EXP[]')
                        fechasfin_EXP = request.POST.getlist('fechafin_EXP[]')
                        archivos_EXP = request.FILES.getlist('archivo_EXP[]')

                        if not cargos_EXP:
                            return JsonResponse({"result": "bad", "mensaje": u"Ingrese los datos de la experiencia académica"})

                        cargoenblanco = [dato for dato in cargos_EXP if dato.strip() == '']
                        institucionenblanco = [dato for dato in instituciones_EXP if dato.strip() == '']
                        fechainicioenblanco = [dato for dato in fechasinicio_EXP if dato.strip() == '']
                        fechafinenblanco = [dato for dato in fechasfin_EXP if dato.strip() == '']

                        # Si existen campos en blanco de la experiencia
                        if cargoenblanco or institucionenblanco or fechainicioenblanco or fechafinenblanco:
                            return JsonResponse({"result": "bad", "mensaje": u"Los datos de los registros de experiencia académica son obligatorios excepto el archivo"})

                        # Valido los archivos cargados de experiencia
                        for nfila, archivo in zip(nfilas_ca_EXP, archivos_EXP):
                            descripcionarchivo = 'Experiencia académica'
                            resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                            if resp['estado'] != "OK":
                                return JsonResponse({"result": "bad", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila'])})

                    # Obtiene los valores de los arreglos del detalle de artículos
                    nfilas_ca_ART = json.loads(request.POST['lista_items3'])  # Números de filas que tienen lleno el campo archivo
                    nfilas_ART = request.POST.getlist('nfila_ART[]')  # Todos los número de filas
                    idsregistro_ART = request.POST.getlist('idregistro_ART[]')  # Todos los ids de los registros
                    idseliminados_ART = json.loads(request.POST['lista_items10'])  # Ids de los registros eliminados

                    # Si agregó filas en la tabla de artículos
                    if nfilas_ART:
                        titulos_ART = request.POST.getlist('titulo_ART[]')
                        revistas_ART = request.POST.getlist('revista_ART[]')
                        basesindexadas_ART = request.POST.getlist('baseindexada_ART[]')
                        fechaspublica_ART = request.POST.getlist('fechapublica_ART[]')
                        tiposautor_ART = request.POST.getlist('tipoautor_ART[]')
                        archivos_ART = request.FILES.getlist('archivo_ART[]')

                        if not titulos_ART:
                            return JsonResponse({"result": "bad", "mensaje": u"Ingrese los datos de artículos publicados"})

                        tituloenblanco = [dato for dato in titulos_ART if dato.strip() == '']
                        revistaenblanco = [dato for dato in revistas_ART if dato.strip() == '']
                        baseenblanco = [dato for dato in basesindexadas_ART if dato.strip() == '']
                        fechaenblanco = [dato for dato in fechaspublica_ART if dato.strip() == '']
                        tipoautorenblanco = [dato for dato in tiposautor_ART if int(dato.strip()) == 0]

                        # Si existen campos en blanco de articulos
                        if tituloenblanco or revistaenblanco or baseenblanco or fechaenblanco or tipoautorenblanco:
                            return JsonResponse({"result": "bad", "mensaje": u"Los datos de los registros de artículos son obligatorios excepto el archivo"})

                        # Valido los archivos cargados de articulos
                        for nfila, archivo in zip(nfilas_ca_ART, archivos_ART):
                            descripcionarchivo = 'Artículos'
                            resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                            if resp['estado'] != "OK":
                                return JsonResponse({"result": "bad", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila'])})

                    # Obtiene los valores de los arreglos del detalle de ponencias
                    nfilas_ca_PON = json.loads(request.POST['lista_items4'])  # Números de filas que tienen lleno el campo archivo
                    nfilas_PON = request.POST.getlist('nfila_PON[]')  # Todos los número de filas
                    idsregistro_PON = request.POST.getlist('idregistro_PON[]')  # Todos los ids de los registros
                    idseliminados_PON = json.loads(request.POST['lista_items11'])  # Ids de los registros eliminados

                    # Si agregó filas en la tabla de ponencias
                    if nfilas_PON:
                        titulos_PON = request.POST.getlist('titulo_PON[]')
                        congresos_PON = request.POST.getlist('congreso_PON[]')
                        fechasinicio_PON = request.POST.getlist('fechainiciocongreso_PON[]')
                        fechasfin_PON = request.POST.getlist('fechafincongreso_PON[]')
                        paises_PON = request.POST.getlist('pais_PON[]')
                        ciudades_PON = request.POST.getlist('ciudad_PON[]')
                        tiposautor_PON = request.POST.getlist('tipoautor_PON[]')
                        archivos_PON = request.FILES.getlist('archivo_PON[]')

                        if not titulos_PON:
                            return JsonResponse({"result": "bad", "mensaje": u"Ingrese los datos de ponencias"})

                        tituloenblanco = [dato for dato in titulos_PON if dato.strip() == '']
                        congresoenblanco = [dato for dato in congresos_PON if dato.strip() == '']
                        fechainicioenblanco = [dato for dato in fechasinicio_PON if dato.strip() == '']
                        fechafinenblanco = [dato for dato in fechasfin_PON if dato.strip() == '']
                        paisenblanco = [dato for dato in paises_PON if int(dato.strip()) == 0]
                        ciudadenblanco = [dato for dato in ciudades_PON if dato.strip() == '']
                        tipoautorenblanco = [dato for dato in tiposautor_PON if int(dato.strip()) == 0]

                        # Si existen campos en blanco de ponencias
                        if tituloenblanco or congresoenblanco or fechainicioenblanco or fechafinenblanco or paisenblanco or ciudadenblanco or tipoautorenblanco:
                            return JsonResponse({"result": "bad", "mensaje": u"Los datos de los registros de ponencias son obligatorios excepto el archivo"})

                        # Valido los archivos cargados de ponencias
                        for nfila, archivo in zip(nfilas_ca_PON, archivos_PON):
                            descripcionarchivo = 'Ponencias'
                            resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                            if resp['estado'] != "OK":
                                return JsonResponse({"result": "bad", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila'])})


                    # Obtiene los valores de los arreglos del detalle de libros
                    nfilas_ca_LIB = json.loads(request.POST['lista_items5'])  # Números de filas que tienen lleno el campo archivo
                    nfilas_LIB = request.POST.getlist('nfila_LIB[]')  # Todos los número de filas
                    idsregistro_LIB = request.POST.getlist('idregistro_LIB[]')  # Todos los ids de los registros
                    idseliminados_LIB = json.loads(request.POST['lista_items12'])  # Ids de los registros eliminados

                    # Si agregó filas en tabla de libros
                    if nfilas_LIB:
                        titulos_LIB = request.POST.getlist('titulo_LIB[]')
                        codigosisbn_LIB = request.POST.getlist('codigoisbn_LIB[]')
                        editoriales_LIB = request.POST.getlist('editorial_LIB[]')
                        fechaspublicacion_LIB = request.POST.getlist('fechapublicacion_LIB[]')
                        tiposautor_LIB = request.POST.getlist('tipoautor_LIB[]')
                        archivos_LIB = request.FILES.getlist('archivo_LIB[]')

                        if not titulos_LIB:
                            return JsonResponse({"result": "bad", "mensaje": u"Ingrese los datos de libros"})

                        tituloenblanco = [dato for dato in titulos_LIB if dato.strip() == '']
                        codigoenblanco = [dato for dato in codigosisbn_LIB if dato.strip() == '']
                        editorialenblanco = [dato for dato in editoriales_LIB if dato.strip() == '']
                        fechapubfinenblanco = [dato for dato in fechaspublicacion_LIB if dato.strip() == '']
                        tipoautorenblanco = [dato for dato in tiposautor_LIB if int(dato.strip()) == 0]

                        # Si existen campos en blanco de libros
                        if tituloenblanco or codigoenblanco or editorialenblanco or fechapubfinenblanco or tipoautorenblanco:
                            return JsonResponse({"result": "bad", "mensaje": u"Los datos de los registros de libros son obligatorios excepto el archivo"})

                        # Valido los archivos cargados de libros
                        for nfila, archivo in zip(nfilas_ca_LIB, archivos_LIB):
                            descripcionarchivo = 'Libros'
                            resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                            if resp['estado'] != "OK":
                                return JsonResponse({"result": "bad", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila'])})

                    # Obtiene los valores de los arreglos del detalle de capítulos de libros
                    nfilas_ca_CAP = json.loads(request.POST['lista_items6'])  # Números de filas que tienen lleno el campo archivo
                    nfilas_CAP = request.POST.getlist('nfila_CAP[]')  # Todos los número de filas
                    idsregistro_CAP = request.POST.getlist('idregistro_CAP[]')  # Todos los ids de los registros
                    idseliminados_CAP = json.loads(request.POST['lista_items13'])  # Ids de los registros eliminados

                    # Si agregó filas en tabla de capítulos de libros
                    if nfilas_CAP:
                        tituloscapitulo_CAP = request.POST.getlist('titulocapitulo_CAP[]')
                        tituloslibro_CAP = request.POST.getlist('titulolibro_CAP[]')
                        codigosisbn_CAP = request.POST.getlist('codigoisbn_CAP[]')
                        editoriales_CAP = request.POST.getlist('editorial_CAP[]')
                        fechaspublicacion_CAP = request.POST.getlist('fechapublicacion_CAP[]')
                        tiposautor_CAP = request.POST.getlist('tipoautor_CAP[]')
                        archivos_CAP = request.FILES.getlist('archivo_CAP[]')

                        if not tituloscapitulo_CAP:
                            return JsonResponse({"result": "bad", "mensaje": u"Ingrese los datos de capítulos de libros"})

                        titulocapenblanco = [dato for dato in tituloscapitulo_CAP if dato.strip() == '']
                        titulolibenblanco = [dato for dato in tituloslibro_CAP if dato.strip() == '']
                        codigoenblanco = [dato for dato in codigosisbn_CAP if dato.strip() == '']
                        editorialenblanco = [dato for dato in editoriales_CAP if dato.strip() == '']
                        fechapubfinenblanco = [dato for dato in fechaspublicacion_CAP if dato.strip() == '']
                        tipoautorenblanco = [dato for dato in tiposautor_CAP if int(dato.strip()) == 0]

                        # Si existen campos en blanco de capitulos de libros
                        if titulocapenblanco or titulolibenblanco or codigoenblanco or editorialenblanco or fechapubfinenblanco or tipoautorenblanco:
                            return JsonResponse({"result": "bad", "mensaje": u"Los datos de los registros de capítulos de libros son obligatorios excepto el archivo"})

                        # Valido los archivos cargados de capítulos de libros
                        for nfila, archivo in zip(nfilas_ca_CAP, archivos_CAP):
                            descripcionarchivo = 'Caítulos de libros'
                            resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                            if resp['estado'] != "OK":
                                return JsonResponse({"result": "bad", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila'])})

                    # Obtiene los valores de los arreglos del detalle de proyectos de investigación
                    nfilas_ca_PROY = json.loads(request.POST['lista_items7'])  # Números de filas que tienen lleno el campo archivo
                    nfilas_PROY = request.POST.getlist('nfila_PROY[]')  # Todos los número de filas
                    idsregistro_PROY = request.POST.getlist('idregistro_PROY[]')  # Todos los ids de los registros
                    idseliminados_PROY = json.loads(request.POST['lista_items14'])  # Ids de los registros eliminados

                    # Si agregó filas en tabla de proyectos
                    if nfilas_PROY:
                        titulos_PROY = request.POST.getlist('titulo_PROY[]')
                        instituciones_PROY = request.POST.getlist('institucion_PROY[]')
                        funciones_PROY = request.POST.getlist('funcion_PROY[]')
                        fechasinicio_PROY = request.POST.getlist('fechainicio_PROY[]')
                        fechasfin_PROY = request.POST.getlist('fechafin_PROY[]')
                        archivos_PROY = request.FILES.getlist('archivo_PROY[]')

                        if not titulos_PROY:
                            return JsonResponse({"result": "bad", "mensaje": u"Ingrese los datos de los proyectos"})

                        tituloenblanco = [dato for dato in titulos_PROY if dato.strip() == '']
                        institucionenblanco = [dato for dato in instituciones_PROY if dato.strip() == '']
                        funcionenblanco = [dato for dato in funciones_PROY if int(dato.strip()) == 0]
                        fechainicioenblanco = [dato for dato in fechasinicio_PROY if dato.strip() == '']
                        fechafinenblanco = [dato for dato in fechasfin_PROY if dato.strip() == '']

                        # Si existen campos en blanco de capitulos de libros
                        if tituloenblanco or institucionenblanco or funcionenblanco or fechainicioenblanco or fechafinenblanco:
                            return JsonResponse({"result": "bad", "mensaje": u"Los datos de los registros de proyectos de investigación son obligatorios excepto el archivo"})

                        # Valido los archivos cargados de proyectos
                        for nfila, archivo in zip(nfilas_ca_PROY, archivos_PROY):
                            descripcionarchivo = 'Proyectos de investigación'
                            resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                            if resp['estado'] != "OK":
                                return JsonResponse({"result": "bad", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila'])})

                    # Actualizo datos de la persona
                    personaexterna = Persona.objects.get(pk=int(encrypt(request.POST['idper'])))
                    personaexterna.cedula = f.cleaned_data['cedula']
                    personaexterna.pasaporte = f.cleaned_data['pasaporte']
                    personaexterna.nacimiento = f.cleaned_data['nacimiento']
                    personaexterna.sexo = f.cleaned_data['sexo']
                    personaexterna.nacionalidad = f.cleaned_data['nacionalidad']
                    personaexterna.email = f.cleaned_data['email']
                    personaexterna.telefono = f.cleaned_data['telefono']
                    personaexterna.save(request)

                    # Consulto red orcid de la persona
                    # redpersona = None
                    # if personaexterna.redpersona_set.filter(tipo_id=1, persona=personaexterna, status=True).exists():
                    #     redpersona = RedPersona.objects.get(tipo_id=1, persona=personaexterna, status=True)
                    #
                    # if f.cleaned_data['identificadororcid']:
                    #     if not redpersona:
                    #         redpersona = RedPersona(
                    #             tipo_id=1,
                    #             persona=personaexterna,
                    #             enlace=f.cleaned_data['identificadororcid'].strip()
                    #         )
                    #     else:
                    #         redpersona.enlace = f.cleaned_data['identificadororcid'].strip()
                    #
                    #     redpersona.save(request)
                    # else:
                    #     if redpersona:
                    #         redpersona.enlace = ''
                    #         redpersona.save(request)

                    # Actualizo perfil de evaluación
                    evaluadorproyecto = EvaluadorProyecto.objects.get(pk=int(encrypt(request.POST['id'])))
                    evaluadorproyecto.propuestaproyecto = f.cleaned_data['propuestaproyecto']
                    evaluadorproyecto.obrarelevancia = f.cleaned_data['obrarelevancia']
                    evaluadorproyecto.save(request)

                    # Actualizo externo
                    externo = evaluadorproyecto.externo
                    externo.institucionlabora = f.cleaned_data['institucionlabora']
                    externo.cargodesempena = f.cleaned_data['cargodesempena']
                    externo.save(request)

                    log(u'Editó persona externa: %s' % (personaexterna), request, "edit")

                    # Elimino los detalles de formación académica que fueron borrados en el formulario
                    for iteme in idseliminados_FA:
                        if not iteme:
                            break

                        iteme = Titulacion.objects.get(pk=int(iteme['idregistro']))
                        iteme.status = False
                        iteme.save(request)

                    # Guardar la formación académica
                    for idregistro, nfila, titulo, universidad, fecha, pais in zip(idsregistro_FA, nfilas_FA, titulos_FA, universidades_FA, fechas_FA, paises_FA):
                        # Si es nuevo
                        if int(idregistro) == 0:
                            # Guardo el titulo
                            tituloacademico = Titulacion(
                                persona=personaexterna,
                                titulo_id=titulo,
                                fechaobtencion=fecha,
                                pais_id=pais,
                                institucion_id=universidad
                            )
                            tituloacademico.save(request)

                            # Guardo el archivo del título
                            for nfilaarchi, archivo in zip(nfilas_ca_FA, archivos_FA):
                                # Si la fila del titulo es igual a la fila que contiene archivo
                                if int(nfilaarchi['nfila']) == int(nfila):
                                    # actualizo campo archivo del registro creado
                                    archivoreg = archivo
                                    archivoreg._name = generar_nombre("titulacion_", archivoreg._name)
                                    tituloacademico.archivo = archivoreg
                                    tituloacademico.save(request)
                                    break

                            log(u'Agregó título a la persona externa: %s - %s' % (personaexterna, tituloacademico), request, "add")
                        else:
                            # Actualizo
                            tituloacademico = Titulacion.objects.get(pk=idregistro)
                            tituloacademico.titulo_id = titulo
                            tituloacademico.fechaobtencion = fecha
                            tituloacademico.pais_id = pais
                            tituloacademico.institucion_id = universidad
                            tituloacademico.save(request)

                            # Guardo el archivo del título
                            for nfilaarchi, archivo in zip(nfilas_ca_FA, archivos_FA):
                                # Si la fila del titulo es igual a la fila que contiene archivo
                                if int(nfilaarchi['nfila']) == int(nfila):
                                    # actualizo campo archivo del registro creado
                                    archivoreg = archivo
                                    archivoreg._name = generar_nombre("titulacion_", archivoreg._name)
                                    tituloacademico.archivo = archivoreg
                                    tituloacademico.save(request)
                                    break


                            log(u'Editó título a la persona externa: %s - %s' % (personaexterna, tituloacademico), request, "edit")



                    # Elimino los detalles de experiencia que fueron borrados en el formulario
                    for iteme in idseliminados_EXP:
                        if not iteme:
                            break

                        iteme = ExperienciaLaboral.objects.get(pk=int(iteme['idregistro']))
                        iteme.status = False
                        iteme.save(request)

                    # Si agregó filas en tabla de experiencia
                    if nfilas_EXP:
                        for idregistro, nfila, cargo, institucion, fechainicio, fechafin in zip(idsregistro_EXP, nfilas_EXP, cargos_EXP, instituciones_EXP, fechasinicio_EXP, fechasfin_EXP):
                            # Si es nuevo
                            if int(idregistro) == 0:
                                # Guardo la experiencia
                                experiencia = ExperienciaLaboral(
                                    persona=personaexterna,
                                    institucion=institucion,
                                    cargo=cargo,
                                    fechainicio=fechainicio,
                                    fechafin=fechafin
                                )
                                experiencia.save(request)

                                # Guardo el archivo de la experiencia
                                for nfilaarchi, archivo in zip(nfilas_ca_EXP, archivos_EXP):
                                    # Si la fila del titulo es igual a la fila que contiene archivo
                                    if int(nfilaarchi['nfila']) == int(nfila):
                                        # actualizo campo archivo del registro creado
                                        archivoreg = archivo
                                        archivoreg._name = generar_nombre("experiencialaboral_", archivoreg._name)
                                        experiencia.archivo = archivoreg
                                        experiencia.save(request)
                                        break

                                log(u'Agregó experiencia a la persona externa: %s - %s' % (personaexterna, experiencia), request, "add")
                            else:
                                # Actualizo el registro
                                experiencia = ExperienciaLaboral.objects.get(pk=idregistro)
                                experiencia.institucion = institucion
                                experiencia.cargo = cargo
                                experiencia.fechainicio = fechainicio
                                experiencia.fechafin = fechafin
                                experiencia.save(request)

                                # Guardo el archivo de la experiencia
                                for nfilaarchi, archivo in zip(nfilas_ca_EXP, archivos_EXP):
                                    # Si la fila del titulo es igual a la fila que contiene archivo
                                    if int(nfilaarchi['nfila']) == int(nfila):
                                        # actualizo campo archivo del registro creado
                                        archivoreg = archivo
                                        archivoreg._name = generar_nombre("experiencialaboral_", archivoreg._name)
                                        experiencia.archivo = archivoreg
                                        experiencia.save(request)
                                        break

                                log(u'Editó experiencia a la persona externa: %s - %s' % (personaexterna, experiencia), request, "edit")



                    # Elimino los detalles de artículos que fueron borrados en el formulario
                    for iteme in idseliminados_ART:
                        if not iteme:
                            break

                        iteme = ArticuloPersonaExterna.objects.get(pk=int(iteme['idregistro']))
                        iteme.status = False
                        iteme.save(request)

                    # Si agregó filas en la tabla de artículos
                    if nfilas_ART:
                        for idregistro, nfila, titulo, revista, bases, fechapublica, tipoautor in zip(idsregistro_ART, nfilas_ART, titulos_ART, revistas_ART, basesindexadas_ART, fechaspublica_ART, tiposautor_ART):
                            # Si es nuevo
                            if int(idregistro) == 0:
                                # Guardo el artículo
                                articulo = ArticuloPersonaExterna(
                                    externo=externo,
                                    titulo=titulo,
                                    revista=revista,
                                    baseindexada=bases,
                                    fechapublicacion=fechapublica,
                                    tipoautor=tipoautor
                                )
                                articulo.save(request)

                                # Guardo el archivo del artículo
                                for nfilaarchi, archivo in zip(nfilas_ca_ART, archivos_ART):
                                    # Si la fila del titulo es igual a la fila que contiene archivo
                                    if int(nfilaarchi['nfila']) == int(nfila):
                                        # actualizo campo archivo del registro creado
                                        archivoreg = archivo
                                        archivoreg._name = generar_nombre("articulo_", archivoreg._name)
                                        articulo.archivo = archivoreg
                                        articulo.save(request)
                                        break

                                log(u'Agregó artículo a la persona externa: %s - %s' % (personaexterna, articulo), request, "add")
                            else:
                                # Actualizo el registro
                                articulo = ArticuloPersonaExterna.objects.get(pk=idregistro)
                                articulo.titulo = titulo
                                articulo.revista = revista
                                articulo.baseindexada = bases
                                articulo.fechapublicacion = fechapublica
                                articulo.tipoautor = tipoautor
                                articulo.save(request)

                                # Guardo el archivo del artículo
                                for nfilaarchi, archivo in zip(nfilas_ca_ART, archivos_ART):
                                    # Si la fila del titulo es igual a la fila que contiene archivo
                                    if int(nfilaarchi['nfila']) == int(nfila):
                                        # actualizo campo archivo del registro creado
                                        archivoreg = archivo
                                        archivoreg._name = generar_nombre("articulo_", archivoreg._name)
                                        articulo.archivo = archivoreg
                                        articulo.save(request)
                                        break

                                log(u'Editó artículo de la persona externa: %s - %s' % (personaexterna, articulo), request, "edit")


                    # Elimino los detalles de ponencias que fueron borrados en el formulario
                    for iteme in idseliminados_PON:
                        if not iteme:
                            break

                        iteme = PonenciaPersonaExterna.objects.get(pk=int(iteme['idregistro']))
                        iteme.status = False
                        iteme.save(request)

                    # Si agregó filas en la tabla de ponencias
                    if nfilas_PON:
                        for idregistro, nfila, titulo, congreso, fechainicio, fechafin, pais, ciudad, tipoautor in zip(idsregistro_PON, nfilas_PON, titulos_PON, congresos_PON, fechasinicio_PON, fechasfin_PON, paises_PON, ciudades_PON, tiposautor_PON):
                            # Si es nuevo
                            if int(idregistro) == 0:
                                # Guardo las ponencias
                                ponencia = PonenciaPersonaExterna(
                                    externo=externo,
                                    titulo=titulo,
                                    congreso=congreso,
                                    fechainicio=fechainicio,
                                    fechafin=fechafin,
                                    pais_id=pais,
                                    ciudad=ciudad,
                                    tipoautor=tipoautor
                                )
                                ponencia.save(request)

                                # Guardo el archivo de la ponencia
                                for nfilaarchi, archivo in zip(nfilas_ca_PON, archivos_PON):
                                    # Si la fila del titulo es igual a la fila que contiene archivo
                                    if int(nfilaarchi['nfila']) == int(nfila):
                                        # actualizo campo archivo del registro creado
                                        archivoreg = archivo
                                        archivoreg._name = generar_nombre("ponencia_", archivoreg._name)
                                        ponencia.archivo = archivoreg
                                        ponencia.save(request)
                                        break

                                log(u'Agregó ponencia a la persona externa: %s - %s' % (personaexterna, ponencia), request,"add")
                            else:
                                # Actualizo registro
                                ponencia = PonenciaPersonaExterna.objects.get(pk=idregistro)
                                ponencia.titulo = titulo
                                ponencia.congreso = congreso
                                ponencia.fechainicio = fechainicio
                                ponencia.fechafin = fechafin
                                ponencia.pais_id = pais
                                ponencia.ciudad = ciudad
                                ponencia.tipoautor = tipoautor
                                ponencia.save(request)

                                # Guardo el archivo de la ponencia
                                for nfilaarchi, archivo in zip(nfilas_ca_PON, archivos_PON):
                                    # Si la fila del titulo es igual a la fila que contiene archivo
                                    if int(nfilaarchi['nfila']) == int(nfila):
                                        # actualizo campo archivo del registro creado
                                        archivoreg = archivo
                                        archivoreg._name = generar_nombre("ponencia_", archivoreg._name)
                                        ponencia.archivo = archivoreg
                                        ponencia.save(request)
                                        break

                                log(u'Editó ponencia de la persona externa: %s - %s' % (personaexterna, ponencia), request, "edit")


                    # Elimino los detalles de libros que fueron borrados en el formulario
                    for iteme in idseliminados_LIB:
                        if not iteme:
                            break

                        iteme = LibroPersonaExterna.objects.get(pk=int(iteme['idregistro']))
                        iteme.status = False
                        iteme.save(request)

                    # Si agregó filas en tabla de libros
                    if nfilas_LIB:
                        for idregistro, nfila, titulo, codigoisbn, editorial, fechapublica, tipoautor in zip(idsregistro_LIB, nfilas_LIB, titulos_LIB, codigosisbn_LIB, editoriales_LIB, fechaspublicacion_LIB, tiposautor_LIB):
                            # Si es nuevo
                            if int(idregistro) == 0:
                                # Guardo el libro
                                libro = LibroPersonaExterna(
                                    externo=externo,
                                    tipo=1,
                                    titulolibro=titulo,
                                    titulocapitulo='',
                                    codigoisbn=codigoisbn,
                                    editorial=editorial,
                                    fechapublicacion=fechapublica,
                                    tipoautor=tipoautor
                                )
                                libro.save(request)

                                # Guardo el archivo del libro
                                for nfilaarchi, archivo in zip(nfilas_ca_LIB, archivos_LIB):
                                    # Si la fila del titulo es igual a la fila que contiene archivo
                                    if int(nfilaarchi['nfila']) == int(nfila):
                                        # actualizo campo archivo del registro creado
                                        archivoreg = archivo
                                        archivoreg._name = generar_nombre("libro_", archivoreg._name)
                                        libro.archivo = archivoreg
                                        libro.save(request)
                                        break

                                log(u'Agregó libro a la persona externa: %s - %s' % (personaexterna, libro), request,"add")
                            else:
                                # Actualizar el registro
                                libro = LibroPersonaExterna.objects.get(pk=idregistro)
                                libro.titulolibro = titulo
                                libro.codigoisbn = codigoisbn
                                libro.editorial = editorial
                                libro.fechapublicacion = fechapublica
                                libro.tipoautor = tipoautor
                                libro.save(request)

                                # Guardo el archivo del libro
                                for nfilaarchi, archivo in zip(nfilas_ca_LIB, archivos_LIB):
                                    # Si la fila del titulo es igual a la fila que contiene archivo
                                    if int(nfilaarchi['nfila']) == int(nfila):
                                        # actualizo campo archivo del registro creado
                                        archivoreg = archivo
                                        archivoreg._name = generar_nombre("libro_", archivoreg._name)
                                        libro.archivo = archivoreg
                                        libro.save(request)
                                        break

                                log(u'Editó libro de la persona externa: %s - %s' % (personaexterna, libro), request, "edit")


                    # Elimino los detalles de capítulos de libros que fueron borrados en el formulario
                    for iteme in idseliminados_CAP:
                        if not iteme:
                            break

                        iteme = LibroPersonaExterna.objects.get(pk=int(iteme['idregistro']))
                        iteme.status = False
                        iteme.save(request)

                    # Si agregó filas en tabla de capítulos de libros
                    if nfilas_CAP:
                        for idregistro, nfila, titulocapitulo, titulolibro, codigoisbn, editorial, fechapublica, tipoautor in zip(idsregistro_CAP, nfilas_CAP, tituloscapitulo_CAP, tituloslibro_CAP, codigosisbn_CAP, editoriales_CAP, fechaspublicacion_CAP, tiposautor_CAP):
                            # Si es nuevo
                            if int(idregistro) == 0:
                                # Guardo el capítulo de libro
                                capitulolibro = LibroPersonaExterna(
                                    externo=externo,
                                    tipo=2,
                                    titulolibro=titulolibro,
                                    titulocapitulo=titulocapitulo,
                                    codigoisbn=codigoisbn,
                                    editorial=editorial,
                                    fechapublicacion=fechapublica,
                                    tipoautor=tipoautor
                                )
                                capitulolibro.save(request)

                                # Guardo el archivo del capítulo de libro
                                for nfilaarchi, archivo in zip(nfilas_ca_CAP, archivos_CAP):
                                    # Si la fila del titulo es igual a la fila que contiene archivo
                                    if int(nfilaarchi['nfila']) == int(nfila):
                                        # actualizo campo archivo del registro creado
                                        archivoreg = archivo
                                        archivoreg._name = generar_nombre("capitulolibro_", archivoreg._name)
                                        capitulolibro.archivo = archivoreg
                                        capitulolibro.save(request)
                                        break

                                log(u'Agregó capítulo de libro a la persona externa: %s - %s' % (personaexterna, capitulolibro), request, "add")
                            else:
                                # Actualizo el registro
                                capitulolibro = LibroPersonaExterna.objects.get(pk=idregistro)
                                capitulolibro.titulolibro = titulolibro
                                capitulolibro.titulocapitulo = titulocapitulo
                                capitulolibro.codigoisbn = codigoisbn
                                capitulolibro.editorial = editorial
                                capitulolibro.fechapublicacion = fechapublica
                                capitulolibro.tipoautor = tipoautor
                                capitulolibro.save(request)

                                # Guardo el archivo del capítulo de libro
                                for nfilaarchi, archivo in zip(nfilas_ca_CAP, archivos_CAP):
                                    # Si la fila del titulo es igual a la fila que contiene archivo
                                    if int(nfilaarchi['nfila']) == int(nfila):
                                        # actualizo campo archivo del registro creado
                                        archivoreg = archivo
                                        archivoreg._name = generar_nombre("capitulolibro_", archivoreg._name)
                                        capitulolibro.archivo = archivoreg
                                        capitulolibro.save(request)
                                        break

                                log(u'Editó capítulo del libro a la persona externa: %s - %s' % (personaexterna, capitulolibro), request, "edit")

                    # Elimino los detalles de proyectos que fueron borrados en el formulario
                    for iteme in idseliminados_PROY:
                        if not iteme:
                            break

                        iteme = ProyectoInvestigacionPersonaExterna.objects.get(pk=int(iteme['idregistro']))
                        iteme.status = False
                        iteme.save(request)

                    # Si agregó filas en tabla de proyectos
                    if nfilas_PROY:
                        for idregistro, nfila, titulo, institucion, funcion, fechainicio, fechafin in zip(idsregistro_PROY, nfilas_PROY, titulos_PROY, instituciones_PROY, funciones_PROY, fechasinicio_PROY, fechasfin_PROY):
                            # Si es nuevo
                            if int(idregistro) == 0:
                                # Guardo el proyecto de investigación
                                proyectoinvestigacion = ProyectoInvestigacionPersonaExterna(
                                    externo=externo,
                                    titulo=titulo,
                                    patrocinador=institucion,
                                    funcion=funcion,
                                    fechainicio=fechainicio,
                                    fechafin=fechafin
                                )
                                proyectoinvestigacion.save(request)

                                # Guardo el archivo del proyecto externo
                                for nfilaarchi, archivo in zip(nfilas_ca_PROY, archivos_PROY):
                                    # Si la fila del titulo es igual a la fila que contiene archivo
                                    if int(nfilaarchi['nfila']) == int(nfila):
                                        # actualizo campo archivo del registro creado
                                        archivoreg = archivo
                                        archivoreg._name = generar_nombre("proyectoinvestigacion_", archivoreg._name)
                                        proyectoinvestigacion.archivo = archivoreg
                                        proyectoinvestigacion.save(request)
                                        break

                                log(u'Agregó proyecto de investigación a la persona externa: %s - %s' % (personaexterna, proyectoinvestigacion), request, "add")
                            else:
                                # Actualizo registro
                                proyectoinvestigacion = ProyectoInvestigacionPersonaExterna.objects.get(pk=idregistro)
                                proyectoinvestigacion.titulo = titulo
                                proyectoinvestigacion.patrocinador = institucion
                                proyectoinvestigacion.funcion = funcion
                                proyectoinvestigacion.fechainicio = fechainicio
                                proyectoinvestigacion.fechafin = fechafin
                                proyectoinvestigacion.save(request)

                                # Guardo el archivo del proyecto externo
                                for nfilaarchi, archivo in zip(nfilas_ca_PROY, archivos_PROY):
                                    # Si la fila del titulo es igual a la fila que contiene archivo
                                    if int(nfilaarchi['nfila']) == int(nfila):
                                        # actualizo campo archivo del registro creado
                                        archivoreg = archivo
                                        archivoreg._name = generar_nombre("proyectoinvestigacion_", archivoreg._name)
                                        proyectoinvestigacion.archivo = archivoreg
                                        proyectoinvestigacion.save(request)
                                        break

                                log(u'Actualió proyecto de investigación a la persona externa: %s - %s' % (personaexterna, proyectoinvestigacion), request, "edit")

                    log(u'Editó evaluador externo de proyectos: %s' % (personaexterna), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    x = f.errors
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'addtitulo':
            try:
                nombre = request.POST['nombre'].strip().upper()

                if Titulo.objects.filter(status=True, nombre=nombre).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"El título ya existe."})

                abreviatura = request.POST['abreviatura'].strip().upper()
                tiponivel = int(request.POST['tiponivel'])
                areaconocimiento = int(request.POST['areaconocimiento'])
                subareaconocimiento = int(request.POST['subareaconocimiento'])
                subareaconocimientoespecifica = int(request.POST['subareaconocimientoespecifica'])

                titulo = Titulo(
                    nombre=nombre,
                    abreviatura=abreviatura,
                    nivel_id=tiponivel,
                    areaconocimiento_id=areaconocimiento,
                    subareaconocimiento_id=subareaconocimiento,
                    subareaespecificaconocimiento_id=subareaconocimientoespecifica
                )
                titulo.save(request)

                log(u'Agregó título universitario: %s' % (titulo), request, "add")

                return JsonResponse({"result": "ok", "id": titulo.id, "nombre": titulo.nombre})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'adduniversidad':
            try:
                nombre = request.POST['nombreuniversidad'].strip().upper()

                if InstitucionEducacionSuperior.objects.filter(status=True, nombre=nombre).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"La Institución de educación superior ya existe."})

                pais = int(request.POST['paisuniversidad'])

                institucion = InstitucionEducacionSuperior(
                    nombre=nombre,
                    pais_id=pais
                )
                institucion.save(request)

                log(u'Agregó institución de educación superior: %s' % (institucion), request, "add")

                return JsonResponse({"result": "ok", "id": institucion.id, "nombre": institucion.nombre})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'revisarinforme':
            try:
                informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que no haya sido revisado por el coordinador de investigación
                # if informeproyecto.estado in [7, 8, 9]:
                if informeproyecto.estado == 7:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el registro debido a que fue revisado por el Coordinador de investigación", "showSwal": "True", "swalType": "warning"})

                f = InformeProyectoForm(request.POST)
                if f.is_valid():
                    estado = int(request.POST['estado'])
                    observacion = request.POST['observacion'].strip() if 'observacion' in request.POST else ''

                    # Actualizo el informe
                    informeproyecto.observacionverificacion = observacion
                    informeproyecto.fechaverificacion = datetime.now()
                    informeproyecto.estado = estado
                    informeproyecto.save(request)

                    # En caso de existir NOVEDAD se debe notificar
                    if estado == 6:
                        # Envio de e-mail de notificacion al solicitante
                        listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                        lista_email_envio = []
                        lista_email_cco = []

                        for integrante in informeproyecto.proyecto.integrantes_proyecto():
                            lista_email_envio += integrante.persona.lista_emails_envio()
                            break

                        fechaenvio = datetime.now().date()
                        horaenvio = datetime.now().time()
                        cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                        tituloemail = "Novedades Informe de Avance de Proyecto de Investigación" if informeproyecto.tipo == 1 else "Novedades Informe Final de Proyecto de Investigación"
                        tiponotificacion = "NOVEDADINFORME"
                        lista_archivos_adjuntos = []
                        titulo = "Proyectos de Investigación"

                        send_html_mail(tituloemail,
                                       "emails/propuestaproyectoinvestigacion.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'titulo': titulo,
                                        'fecha': fechaenvio,
                                        'hora': horaenvio,
                                        'tiponotificacion': tiponotificacion,
                                        'numeroinforme': informeproyecto.numero,
                                        'tipoinforme': 'de un informe de avance' if informeproyecto.tipo == 1 else 'del informe final',
                                        'tituloproyecto': informeproyecto.proyecto.titulo,
                                        'observaciones': observacion
                                        },
                                       lista_email_envio,  # Destinatarioa
                                       lista_email_cco,  # Copia oculta
                                       lista_archivos_adjuntos,  # Adjunto(s)
                                       cuenta=CUENTAS_CORREOS[cuenta][1]
                                       )

                    if estado == 5:
                        log(u'% revisó informe de proyecto de investigación: %s' % (persona, informeproyecto), request, "edit")
                    else:
                        log(u'% rechazó informe de proyecto de investigación: %s' % (persona, informeproyecto), request, "edit")

                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    x = f.errors
                    raise NameError('Error en el formulario')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'aprobarinforme':
            try:
                informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que el informe no haya sido cargado por el docente
                if informeproyecto.estado == 4:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el registro debido a que el informe ya fue impreso y cargado por el docente", "showSwal": "True", "swalType": "warning"})

                f = InformeProyectoForm(request.POST)
                if f.is_valid():
                    estado = int(request.POST['estado'])
                    observacion = request.POST['observacion'].strip() if 'observacion' in request.POST else ''

                    # Actualizo el informe
                    informeproyecto.observacionaprobacion = observacion
                    informeproyecto.fechaaprobacion = datetime.now()
                    informeproyecto.aprobado = (estado == 7)
                    informeproyecto.estado = estado
                    informeproyecto.save(request)

                    proyectofinalizado = False

                    # # Si se aprobó el informe final
                    # if informeproyecto.tipo == 2 and estado == 7:
                    #     proyectoinvestigacion = informeproyecto.proyecto
                    #
                    #     # Obtengo el estado FINALIZADO
                    #     estadoproyecto = obtener_estado_solicitud(3, 21)
                    #
                    #     # Actualizo el proyecto
                    #     proyectoinvestigacion.fechafinreal = request.POST['fechafinproyecto']
                    #     proyectoinvestigacion.ejecucion = 2
                    #     proyectoinvestigacion.estado = estadoproyecto
                    #     proyectoinvestigacion.save(request)
                    #
                    #     # Creo el recorrido del proyecto
                    #     recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                    #                                        fecha=datetime.now().date(),
                    #                                        observacion='PROYECTO FINALIZADO',
                    #                                        estado=estadoproyecto
                    #                                        )
                    #     recorrido.save(request)
                    #
                    #     log(u'%s finalizó proyecto de investigación: %s' % (persona, proyectoinvestigacion), request, "edit")
                    #     proyectofinalizado = True


                    # Envio de e-mail de notificacion al solicitante o al que revisó el informe
                    listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                    fechaenvio = datetime.now().date()
                    horaenvio = datetime.now().time()
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                    if estado == 7:
                        lista_email_envio = []
                        lista_email_cco = []
                        for integrante in informeproyecto.proyecto.integrantes_proyecto():
                            lista_email_envio += integrante.persona.lista_emails_envio()
                            break

                        tituloemail = "Informe de Avance de Proyecto de Investigación Aprobado" if informeproyecto.tipo == 1 else "Informe Final de Proyecto de Investigación Aprobado"
                        tiponotificacion = "APRUEBAINFORME"
                    else:
                        lista_email_envio = informeproyecto.personaverifica.lista_emails_envio()
                        lista_email_cco = []

                        tituloemail = "Novedades Informe de Avance de Proyecto de Investigación" if informeproyecto.tipo == 1 else "Novedades Informe Final de Proyecto de Investigación"
                        tiponotificacion = "NOVEDADINFORMEAPRO"

                    lista_archivos_adjuntos = []
                    titulo = "Proyectos de Investigación"

                    # Si es APROBADO se notifica a los integrantes del proyecto
                    if estado == 7:
                        send_html_mail(tituloemail,
                                       "emails/propuestaproyectoinvestigacion.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'titulo': titulo,
                                        'fecha': fechaenvio,
                                        'hora': horaenvio,
                                        'tiponotificacion': tiponotificacion,
                                        'numeroinforme': informeproyecto.numero,
                                        'tipoinforme': 'informe de avance' if informeproyecto.tipo == 1 else 'informe final',
                                        'tituloproyecto': informeproyecto.proyecto.titulo,
                                        'observaciones': observacion
                                        },
                                       lista_email_envio,  # Destinatarioa
                                       lista_email_cco,  # Copia oculta
                                       lista_archivos_adjuntos,  # Adjunto(s)
                                       cuenta=CUENTAS_CORREOS[cuenta][1]
                                       )
                    else:
                        # Si tiene novedades se notifica al usuario que revisó el informe
                        send_html_mail(tituloemail,
                                       "emails/propuestaproyectoinvestigacion.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'titulo': titulo,
                                        'fecha': fechaenvio,
                                        'hora': horaenvio,
                                        'tiponotificacion': tiponotificacion,
                                        'saludo': 'Estimada' if informeproyecto.personaverifica.sexo_id == 1 else 'Estimado',
                                        'nombrepersona': informeproyecto.personaverifica.nombre_completo_inverso(),
                                        'numeroinforme': informeproyecto.numero,
                                        'tipoinforme': 'del informe de avance' if informeproyecto.tipo == 1 else 'del informe final',
                                        'tituloproyecto': informeproyecto.proyecto.titulo,
                                        'observaciones': observacion
                                        },
                                       lista_email_envio,  # Destinatarioa
                                       lista_email_cco,  # Copia oculta
                                       lista_archivos_adjuntos,  # Adjunto(s)
                                       cuenta=CUENTAS_CORREOS[cuenta][1]
                                       )

                    # En caso de haber Finalizado el proyecto se debe notificar
                    if proyectofinalizado:
                        tiponotificacion = "FINALIZAPROYECTO"
                        send_html_mail(tituloemail,
                                       "emails/notificacion_propuesta_proyecto_investigacion.html",
                                       {'sistema': u'Coordinación de Investigación UNEMI',
                                        'fecha': fechaenvio,
                                        'hora': horaenvio,
                                        'tiponotificacion': tiponotificacion,
                                        'numeroinforme': informeproyecto.numero,
                                        'tituloproyecto': informeproyecto.proyecto.titulo,
                                        'observaciones': observacion,
                                        't': miinstitucion()
                                        },
                                       lista_email_envio,
                                       [],
                                       cuenta=CUENTAS_CORREOS[cuenta][1]
                                       )

                    if estado == 7:
                        log(u'%s aprobó informe de proyecto de investigación: %s' % (persona, informeproyecto), request, "edit")
                    else:
                        log(u'%s asignó novedades en informe de proyecto de investigación: %s' % (persona, informeproyecto), request, "edit")

                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    x = f.errors
                    raise NameError('Error en el formulario')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addinforme':
            try:
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                periodovigente = Periodo.objects.get(pk=int(encrypt(request.POST['idperiodovigente']))) if request.POST['idperiodovigente'] else None

                f = InformeProyectoForm(request.POST, request.FILES)
                if f.is_valid():
                    # Validar que no esté repetido el número del informe
                    if not ProyectoInvestigacionInforme.objects.filter(status=True, numero=request.POST['codigoinforme'].strip()).exists():
                        secuencia = proyecto.secuencia_informe_avance()
                        # Obtiene el detalle de actividades
                        actividades = json.loads(request.POST['lista_items1'])

                        # Obtiene los valores de los arreglos del detalle de formatos
                        # nfilas_ca_evi = json.loads(request.POST['lista_items2'])  # Números de filas que tienen lleno el campo archivo en detalle de evidencias
                        nfilas_ca_evi = json.loads(request.POST['lista_items2']) if 'lista_items2' in request.POST else [] # Números de filas que tienen lleno el campo archivo en detalle de evidencias
                        nfilas_evi = request.POST.getlist('nfila_evidencia[]')  # Todos los número de filas del detalle de evidencias
                        descripciones_evi = request.POST.getlist('descripcion_evidencia[]')  # Todas las descripciones
                        archivos_evi = request.FILES.getlist('archivo_evidencia[]')  # Todos los archivos
                        fechasgenera = request.POST.getlist('fecha_genera[]') # Todas las fechas de generación
                        numerospagina = request.POST.getlist('numero_pagina[]') # Todas los números de página

                        # Valido los archivos cargados de detalle de evidencias
                        for nfila, archivo in zip(nfilas_ca_evi, archivos_evi):
                            descripcionarchivo = 'Evidencia'
                            resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                            if resp['estado'] != "OK":
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                        # Guardar informe
                        informeproyecto = ProyectoInvestigacionInforme(
                            proyecto=proyecto,
                            periodo=periodovigente,
                            tipo=request.POST['tipoinforme'],
                            secuencia=secuencia,
                            generado=False,
                            fecha=request.POST['fechainforme'],
                            numero=request.POST['codigoinforme'].strip(),
                            conclusion=request.POST['conclusion'].strip(),
                            recomendacion=request.POST['recomendacion'].strip(),
                            personaverifica=proyecto.verificainforme,
                            personaaprueba=proyecto.apruebainforme,
                            aprobado=False,
                            estado=3
                        )
                        informeproyecto.save(request)

                        # Guardar detalle de actividades del informe
                        for actividad in actividades:
                            estado = 3 if actividad['estado'] == 'FINALIZADA' else 2

                            # Creo detalle de actividad del informe
                            actividadinforme = ProyectoInvestigacionInformeActividad(
                                informe=informeproyecto,
                                actividad_id=actividad['ida'],
                                entregable=actividad['entregable'],
                                fechainicio=actividad['fechainicio'],
                                fechafin=actividad['fechafin'],
                                cantidadhora=actividad['cantidadhora'],
                                porcentajeejecucion=actividad['avance'],
                                observacion=actividad['observacion'],
                                estado=estado
                            )
                            actividadinforme.save(request)

                            # Guardo los responsbles de la actividad
                            for responsable_id in actividad['responsables'].split(","):
                                actividadinforme.responsable.add(responsable_id)

                            actividadinforme.save(request)

                            # Consultar actividad para actualizar fechas y descripción de entregables
                            actividadcronograma = ProyectoInvestigacionCronogramaActividad.objects.get(pk=actividad['ida'])

                            # Actualizo los campos de lq actividad
                            actividadcronograma.fechainicio = actividad['fechainicio']
                            actividadcronograma.fechafin = actividad['fechafin']
                            actividadcronograma.entregable = actividad['entregable']
                            actividadcronograma.porcentajeejecucion = actividad['avance']
                            actividadcronograma.observacion = actividad['observacion']
                            actividadcronograma.estado = estado
                            actividadcronograma.save(request)

                        # Guardar evidencias de informe
                        for nfila, descripcion, fecha, numeropagina in zip(nfilas_evi, descripciones_evi, fechasgenera, numerospagina):
                            evidenciainforme = ProyectoInvestigacionInformeAnexo(
                                informe=informeproyecto,
                                descripcion=descripcion.strip(),
                                fecha=fecha,
                                numeropagina=numeropagina.strip()
                            )
                            evidenciainforme.save(request)

                            # Guardo el archivo del formato
                            for nfilaarchi, archivo in zip(nfilas_ca_evi, archivos_evi):
                                # Si la fila de la descripcion es igual a la fila que contiene archivo
                                if int(nfilaarchi['nfila']) == int(nfila):
                                    # actualizo campo archivo del registro creado
                                    archivoreg = archivo
                                    archivoreg._name = generar_nombre("evidenciainforme_", archivoreg._name)
                                    evidenciainforme.archivo = archivoreg
                                    evidenciainforme.save(request)
                                    break

                        # Actualizo el porcentaje esperado y ejecutado
                        informeproyecto.avanceesperado = proyecto.porcentaje_avance_esperado()
                        informeproyecto.porcentajeejecucion = proyecto.porcentaje_avance_ejecucion()
                        informeproyecto.save(request)

                        log(u'%s agregó informe al proyecto: %s' % (persona, informeproyecto.proyecto), request, "add")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El número de informe ya ha sido ingresado", "showSwal": "True", "swalType": "warning"})
                else:
                    x = f.errors
                    raise NameError('Error en el formulario')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editinforme':
            try:
                informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico si fue revisado o rechazado por el técnico de investigación
                if informeproyecto.estado in [5, 7]:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el informe debido a que fue revisado por Investigación", "showSwal": "True", "swalType": "warning"})

                notificar = informeproyecto.estado in [6, 8]

                f = InformeProyectoForm(request.POST, request.FILES)
                if f.is_valid():
                    # Obtiene el detalle de actividades
                    actividades = json.loads(request.POST['lista_items1'])
                    actividadeseliminadas = json.loads(request.POST['lista_items3']) if 'lista_items3' in request.POST else []

                    # Obtiene los valores de los arreglos del detalle de formatos
                    nfilas_ca_evi = json.loads(request.POST['lista_items2'])  # Números de filas que tienen lleno el campo archivo en detalle de evidencias
                    nfilas_evi = request.POST.getlist('nfila_evidencia[]')  # Todos los número de filas del detalle de evidencias
                    idsevidencias = request.POST.getlist('idregistro[]')  # Todos los ids de detalle de evidencias
                    descripciones_evi = request.POST.getlist('descripcion_evidencia[]')  # Todas las descripciones
                    archivos_evi = request.FILES.getlist('archivo_evidencia[]')  # Todos los archivos
                    fechasgenera = request.POST.getlist('fecha_genera[]')  # Todas las fechas de generación
                    numerospagina = request.POST.getlist('numero_pagina[]')  # Todas los números de página
                    evidenciasseliminadas = json.loads(request.POST['lista_items4']) if 'lista_items4' in request.POST else []

                    # Valido los archivos cargados de detalle de evidencias
                    for nfila, archivo in zip(nfilas_ca_evi, archivos_evi):
                        descripcionarchivo = 'Evidencia'
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                    # Actualizo el informe
                    informeproyecto.tipo = request.POST['tipoinforme']
                    informeproyecto.fecha = request.POST['fechainforme']
                    informeproyecto.conclusion = request.POST['conclusion'].strip()
                    informeproyecto.recomendacion = request.POST['recomendacion'].strip()
                    informeproyecto.observacionverificacion = ''
                    informeproyecto.fechaverificacion = None
                    informeproyecto.observacionaprobacion = ''
                    informeproyecto.fechaaprobacion = None
                    informeproyecto.estado = 3
                    informeproyecto.save(request)

                    # Guardar/actualizar detalle de actividades del informe
                    for actividad in actividades:
                        estado = 3 if actividad['estado'] == 'FINALIZADA' else 2

                        # Nuevo
                        if int(actividad['idreg']) == 0:
                            # Creo detalle de actividad del informe
                            actividadinforme = ProyectoInvestigacionInformeActividad(
                                informe=informeproyecto,
                                actividad_id=actividad['ida'],
                                entregable=actividad['entregable'],
                                fechainicio=actividad['fechainicio'],
                                fechafin=actividad['fechafin'],
                                cantidadhora=actividad['cantidadhora'],
                                porcentajeejecucion=actividad['avance'],
                                observacion=actividad['observacion'],
                                estado=estado
                            )
                        else:
                            # Consulto y actualizo el detalle de actividad
                            actividadinforme = ProyectoInvestigacionInformeActividad.objects.get(pk=actividad['idreg'])
                            actividadinforme.entregable = actividad['entregable']
                            actividadinforme.fechainicio = actividad['fechainicio']
                            actividadinforme.fechafin = actividad['fechafin']
                            actividadinforme.cantidadhora = actividad['cantidadhora']
                            actividadinforme.porcentajeejecucion = actividad['avance']
                            actividadinforme.observacion = actividad['observacion']
                            actividadinforme.estado = estado

                        actividadinforme.save(request)

                        # Guardo los responsbles de la actividad
                        actividadinforme.responsable.clear()
                        for responsable_id in actividad['responsables'].split(","):
                            actividadinforme.responsable.add(responsable_id)

                        actividadinforme.save(request)

                        # Consultar actividad para actualizar fechas y descripción de entregables
                        actividadcronograma = ProyectoInvestigacionCronogramaActividad.objects.get(pk=actividad['ida'])

                        # Actualizo los campos de lq actividad
                        actividadcronograma.fechainicio = actividad['fechainicio']
                        actividadcronograma.fechafin = actividad['fechafin']
                        actividadcronograma.entregable = actividad['entregable']
                        actividadcronograma.porcentajeejecucion = actividad['avance']
                        actividadcronograma.observacion = actividad['observacion']
                        actividadcronograma.estado = estado
                        actividadcronograma.save(request)

                    # Elimino las actividades que se borraron del detalle
                    if actividadeseliminadas:
                        for actividadeli in actividadeseliminadas:
                            actividadinforme = ProyectoInvestigacionInformeActividad.objects.get(pk=actividadeli['idreg'])
                            actividadinforme.status = False
                            actividadinforme.responsable.clear()
                            actividadinforme.save(request)

                    # Guardo el detalle de evidencias
                    for idevidencia, nfila, descripcion, fecha, numeropagina in zip(idsevidencias, nfilas_evi, descripciones_evi, fechasgenera, numerospagina):
                        # Si es registro nuevo
                        if int(idevidencia) == 0:
                            evidenciainforme = ProyectoInvestigacionInformeAnexo(
                                informe=informeproyecto,
                                descripcion=descripcion,
                                fecha=fecha,
                                numeropagina=numeropagina.strip()
                            )
                        else:
                            evidenciainforme = ProyectoInvestigacionInformeAnexo.objects.get(pk=idevidencia)
                            evidenciainforme.descripcion = descripcion
                            evidenciainforme.fecha = fecha
                            evidenciainforme.numeropagina = numeropagina

                        evidenciainforme.save(request)

                        # Guardo el archivo del formato
                        for nfilaarchi, archivo in zip(nfilas_ca_evi, archivos_evi):
                            # Si la fila de la descripcion es igual a la fila que contiene archivo
                            if int(nfilaarchi['nfila']) == int(nfila):
                                # actualizo campo archivo del registro creado
                                archivoreg = archivo
                                archivoreg._name = generar_nombre("evidenciainforme_", archivoreg._name)
                                evidenciainforme.archivo = archivoreg
                                evidenciainforme.save(request)
                                break

                    # Elimino las evidencias que se borraron del detalle
                    if evidenciasseliminadas:
                        for evidencia in evidenciasseliminadas:
                            evidenciainforme = ProyectoInvestigacionInformeAnexo.objects.get(pk=evidencia['idreg'])
                            evidenciainforme.status = False
                            evidenciainforme.save(request)

                    # Actualizo el porcentaje esperado y ejecutado
                    proyecto = informeproyecto.proyecto
                    informeproyecto.avanceesperado = proyecto.porcentaje_avance_esperado()
                    informeproyecto.porcentajeejecucion = proyecto.porcentaje_avance_ejecucion()
                    informeproyecto.save(request)

                    log(u'%s editó informe del proyecto: %s' % (persona, informeproyecto.proyecto), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    x = f.errors
                    raise NameError('Error en el formulario')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'informetecnicopdf':
            try:
                data = {}

                informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['id'])))

                if not informeproyecto.generado:
                    data['informeproyecto'] = informeproyecto
                    data['proyecto'] = proyecto = informeproyecto.proyecto

                    data['avanceesperado'] = informeproyecto.avanceesperado
                    data['avanceejecucion'] = informeproyecto.porcentajeejecucion

                    data['resolucionaprueba'] = resolucionaprueba = proyecto.convocatoria.resolucion_aprobacion()[0]
                    data['fecharesolucion'] = str(resolucionaprueba.fecha.day) + " de " + MESES_CHOICES[resolucionaprueba.fecha.month - 1][1].capitalize() + " del " + str(resolucionaprueba.fecha.year)
                    data['fechainicio'] = str(proyecto.fechainicio.day) + " de " + MESES_CHOICES[proyecto.fechainicio.month - 1][1].capitalize() + " del " + str(proyecto.fechainicio.year)
                    data['fechafinestimada'] = str(proyecto.fechafinplaneado.day) + " de " + MESES_CHOICES[proyecto.fechafinplaneado.month - 1][1].capitalize() + " del " + str(proyecto.fechafinplaneado.year)
                    data['mesinicio'] = MESES_CHOICES[proyecto.fechainicio.month - 1][1].capitalize() + " del " + str(proyecto.fechainicio.year)
                    data['integrantes'] = integrantes = proyecto.integrantes_proyecto_informe()
                    data['codirector'] = integrantes.filter(funcion=2)
                    data['investigadores'] = integrantes.filter(funcion=3)
                    data['asistentes'] = integrantes.filter(funcion=4)
                    data['objetivos'] = informeproyecto.objetivos_especificos_cronograma_informe()
                    data['evidencias'] = evidencias = informeproyecto.proyectoinvestigacioninformeanexo_set.filter(status=True).order_by('id')

                    # Creacion de los archivos por separado
                    directorio = SITE_STORAGE + '/media/proyectoinvestigacion/informes'
                    try:
                        os.stat(directorio)
                    except:
                        os.mkdir(directorio)

                    # Archivo de la parte 1 del informe
                    nombrearchivo = 'informeparte1_' + str(proyecto.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                    valida = convert_html_to_pdf(
                        'pro_proyectoinvestigacion/informeavancepdf.html',
                        {'pagesize': 'A4', 'data': data},
                        nombrearchivo,
                        directorio
                    )

                    if not valida:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento de la parte 1 del informe."})

                    archivo1 = directorio + "/" + nombrearchivo

                    # Leer los archivos
                    pdf1Reader = PyPDF2.PdfFileReader(archivo1)

                    # Crea un nuevo objeto PdfFileWriter que representa un documento PDF en blanco
                    pdfWriter = PyPDF2.PdfFileWriter()

                    # Recorre todas las páginas del documento 1
                    for pageNum in range(pdf1Reader.numPages):
                        pageObj = pdf1Reader.getPage(pageNum)
                        pdfWriter.addPage(pageObj)

                    # Recorro el detalle de evidencias
                    for evidencia in evidencias:
                        archivoevidencia = SITE_STORAGE + evidencia.archivo.url  # Archivo pdf de proyecto cargado como evidencia
                        pdf2ReaderEvi = PyPDF2.PdfFileReader(archivoevidencia)

                        # Recorre todas las páginas del documento de evidencia: pdf2ReaderEvi
                        for pageNum in range(pdf2ReaderEvi.numPages):
                            pageObj = pdf2ReaderEvi.getPage(pageNum)
                            pdfWriter.addPage(pageObj)

                    # Luego de haberse copiado todas las paginas de todos los documentos, se las escribe en el documento en blanco
                    fecha = datetime.now().date()
                    hora = datetime.now().time()
                    nombrearchivoresultado = 'informeavancepdf' + fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__() + '.pdf'
                    pdfOutputFile = open(directorio + "/" + nombrearchivoresultado, "wb")
                    pdfWriter.write(pdfOutputFile)

                    # Borro los documento individuales creados a exepción del archivo del proyecto cargado por el docente
                    os.remove(archivo1)

                    pdfOutputFile.close()

                    # Actualizo la ruta en el infome
                    informeproyecto.archivogenerado = 'proyectoinvestigacion/informes/' + nombrearchivoresultado
                    informeproyecto.generado = True
                    informeproyecto.save(request)

                    log(u'%s generó informe del proyecto: %s' % (persona, informeproyecto.proyecto), request, "edit")

                return JsonResponse({"result": "ok", "documento": informeproyecto.archivogenerado.url})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento del informe. [%s]" % msg})

        elif action == 'firmarinforme':
            try:
                nombre_mes = lambda x: MESES_CHOICES[int(x)] if x > 0 and x <= 12  else 'Por definir'
                txtFirmas = json.loads(request.POST['txtFirmas'])
                if not txtFirmas:
                    raise NameError("Debe seleccionar ubicación de la firma")

                coord = txtFirmas[-1]

                datas, PARSE_ESTADO = None, {7: 4, 9: 3}
                informe = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['id_objeto'])))
                a, m = informe.fecha.year, informe.fecha.month
                fechainicio, fechafin = datetime(a, m, 1), datetime(a, m, calendar.monthrange(a, m)[1])
                ci = CriterioInvestigacion.objects.get(pk=55)
                distributivolider = DetalleDistributivo.objects.filter(criterioinvestigacionperiodo__criterio=ci, distributivo__profesor=informe.proyecto.profesor, distributivo__periodo=periodo, status=True).first()

                file = informe.archivogenerado
                certificado = request.FILES["firma"]
                password = request.POST['palabraclave']
                razon = f"Legalizar informe del mes {nombre_mes(fechafin.month)} para proyecto de investigación {informe.proyecto.pk}."
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()

                words = "%s" % persona.nombre_completo_inverso().title()
                x, y, page =  coord["x"], coord["y"], coord["numPage"]  # obtener_posicion_x_y_saltolinea(file.url, words, False)

                if not x and not y: return JsonResponse({'result': 'bad', 'mensaje': "No se encontró la palabra %s en el archivo. Por favor verifique que este nombre se encuentre en el apartado de firmas." % words})

                # x, y = x + 30, y - 230

                try:
                    datau = JavaFirmaEc(archivo_a_firmar=file, archivo_certificado=bytes_certificado, extension_certificado=extension_certificado, password_certificado=password, page=page, reason="Validar informe de vinculación", lx=x, ly=y).sign_and_get_content_bytes()
                except Exception as ex:
                    datau, datas = firmar(request, password, certificado, file, page, x, y, 150, 45)

                if not datau:
                    return JsonResponse({'result': 'bad', 'mensaje': "Problemas con la firma electrónica. %s" % datas if datas else ''})

                documento_a_firmar = io.BytesIO()
                documento_a_firmar.write(datau)
                documento_a_firmar.seek(0)

                nombrefile_ = file.name.split('/')[-1].split('.')[0]
                _name = f'{nombrefile_}_signed_{request.user.username}_' + '.pdf'
                informe.archivogenerado.save(_name, ContentFile(documento_a_firmar.read()))

                if informe.proyecto.profesor.persona == persona:
                    from sga.pro_cronograma import migrar_evidencia_integrantes_proyecto_investigacion
                    if not distributivolider:
                        return JsonResponse({'result': 'bad', 'mensaje': f"Estimad{'a' if persona.es_mujer() else 'o'} {persona.nombres.__str__().split()[0].capitalize()}, al momento usted no cuenta con la actividad de {ci}. Por favor asegúrese de haber seleccionado el <b>periodo</b> correcto."})

                    evidencia = EvidenciaActividadDetalleDistributivo(criterio=distributivolider, desde=fechainicio, hasta=fechafin,
                                                                      actividad=f"Informe de evidencia correspondiente a: {nombre_mes(fechafin.month)} {fechafin.year}",
                                                                      estadoaprobacion=PARSE_ESTADO[informe.estado] if informe.estado in (7, 9) else 1)
                    if informe.estado == 7:
                        evidencia.archivofirmado = informe.archivo
                        evidencia.usuarioaprobado = informe.personaaprueba.usuario
                        evidencia.fechaaprobado = informe.fechaaprobacion
                        evidencia.save(request)
                        historial = HistorialAprobacionEvidenciaActividad(evidencia=evidencia, aprobacionpersona=informe.personaaprueba, fechaaprobacion=informe.fechaaprobacion, estadoaprobacion=2)
                        historial.save(request)
                    else:
                        evidencia.archivo = informe.archivo

                    evidencia.save(request)
                    historial = HistorialAprobacionEvidenciaActividad(evidencia=evidencia, aprobacionpersona=informe.personaaprueba, fechaaprobacion=informe.fechaaprobacion, estadoaprobacion=evidencia.estadoaprobacion)
                    historial.save(request)

                    eaa = EvidenciaActividadAudi(evidencia=evidencia, archivo=informe.archivo)
                    eaa.save(request)

                    for anexo in informe.proyectoinvestigacioninformeanexo_set.filter(status=True):
                        anexo = AnexoEvidenciaActividad(evidencia=evidencia, observacion=anexo.descripcion, fecha_creacion=anexo.fecha, archivo=anexo.archivo)
                        anexo.save(request)

                    migrar_evidencia_integrantes_proyecto_investigacion(evidencia=evidencia, request=request)

                    log(u'%s firmo documento: %s' % (persona, nombrefile_), request, "add")

                #return JsonResponse({"result": False, "mensaje": "Guardado con exito", }, safe=False)
                return redirect(f'/adm_proyectoinvestigacion?action=informesproyecto&id={encrypt(informe.proyecto.pk)}')
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': "Error de conexión. %s" % ex.__str__()})

        elif action == 'subirinforme':
            try:
                if not 'idinforme' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['idinforme'])))

                archivo = request.FILES['archivoinforme']
                descripcionarchivo = 'Archivo del informe firmado'
                tipoinforme = "avance" if informeproyecto.tipo == 1 else "final"

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                archivo._name = generar_nombre("informeproyecto" + tipoinforme, archivo._name)

                # Guardo el archivo del informe
                informeproyecto.archivo = archivo
                informeproyecto.estado = 4
                informeproyecto.save(request)

                log(u'Agregó archivo del informe firmado: %s' % (informeproyecto), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'subircontrato':
            try:
                if not 'idproyecto' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                proyectoinvestigacion = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idproyecto'])))

                archivo = request.FILES['archivocontrato']
                descripcionarchivo = 'Archivo del contrato de financiamiento'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                archivo._name = generar_nombre("contratofinanciamiento", archivo._name)

                if not proyectoinvestigacion.archivocontratoejecucion:
                    # Guardo el archivo del contrato
                    proyectoinvestigacion.estadocronograma = 1
                    proyectoinvestigacion.archivocontratoejecucion = archivo
                    proyectoinvestigacion.save(request)

                    # Crea el historial del archivo
                    historialarchivo = ProyectoInvestigacionHistorialArchivo(
                        proyecto=proyectoinvestigacion,
                        tipo=5,
                        archivo=proyectoinvestigacion.archivocontratoejecucion
                    )
                    historialarchivo.save(request)

                    # Notificar por e-mail a director para que edite el cronograma de actividades
                    listacuentascorreo = [29]  # investigacion@unemi.edu.ec

                    lista_email_envio = []
                    lista_email_cco = []

                    for integrante in proyectoinvestigacion.integrantes_proyecto():
                        lista_email_envio += integrante.persona.lista_emails_envio()
                        break

                    fechaenvio = datetime.now().date()
                    horaenvio = datetime.now().time()
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                    tituloemail = "Edición del Cronograma de Actividades de Proyecto de Investigación - Habilitada"
                    tiponotificacion = "HABEDICRON"

                    lista_archivos_adjuntos = []
                    titulo = "Proyectos de Investigación"

                    send_html_mail(tituloemail,
                                   "emails/propuestaproyectoinvestigacion.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'tiponotificacion': tiponotificacion,
                                    'saludo': 'Estimada' if proyectoinvestigacion.profesor.persona.sexo_id == 1 else 'Estimado',
                                    'nombrepersona': proyectoinvestigacion.profesor.persona.nombre_completo_inverso(),
                                    'proyecto': proyectoinvestigacion
                                    },
                                   lista_email_envio,  # Destinatarioa
                                   lista_email_cco,  # Copia oculta
                                   lista_archivos_adjuntos,  # Adjunto(s)
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                    log(u'%s agregó contrato de financiamiento al proyecto: %s' % (persona, proyectoinvestigacion), request, "add")
                else:
                    # Actualizo el archivo
                    proyectoinvestigacion.archivocontratoejecucion = archivo
                    proyectoinvestigacion.save(request)

                    # Crea el historial del archivo
                    historialarchivo = ProyectoInvestigacionHistorialArchivo(
                        proyecto=proyectoinvestigacion,
                        tipo=5,
                        archivo=proyectoinvestigacion.archivocontratoejecucion
                    )
                    historialarchivo.save(request)

                    log(u'%s editó contrato de financiamiento al proyecto: %s' % (persona, proyectoinvestigacion), request, "edit")

                return JsonResponse({"result": "ok", "idp": request.POST['idproyecto']})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'asignarevaluadorpfinalizado':
            try:
                f = EvaluadorProyectoInvestigacionFinalizadoForm(request.POST)

                evalinternos = json.loads(request.POST['lista_items1'])
                evalinternoseliminados = json.loads(request.POST['lista_items3']) if 'lista_items3' in request.POST else []

                if not evalinternos:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe agregar evaluadores al proyecto"})

                proyectoinvestigacion = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                codigos_profesores = [item['idpe'] for item in evalinternos]

                # Verificar que se hayan agregado mínimo 2 evaluadores
                if proyectoinvestigacion.convocatoria.apertura.year >= 2022:
                    if len(codigos_profesores) < 2:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe agregar mínimo 2 evaluadores"})

                # Verificar que no sean integrantes del proyecto
                if proyectoinvestigacion.proyectoinvestigacionintegrante_set.filter(status=True, profesor_id__in=codigos_profesores).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Los evaluadores no deben ser integrantes del proyecto"})

                if f.is_valid():
                    # Obtiene los valores de los arrays de input
                    codigosdetalles = request.POST.getlist('iddetalle[]')
                    codigosprofesores = request.POST.getlist('idevaluador[]')
                    nombresprofesores = request.POST.getlist('nombreevaluador[]')
                    fechasinicio = request.POST.getlist('fechainicio[]')
                    fechasfin = request.POST.getlist('fechafin[]')

                    # Obtiene fechas que estén en blanco
                    fechainicioenblanco = [dato for dato in fechasinicio if dato.strip() == '']
                    fechafinenblanco = [dato for dato in fechasfin if dato.strip() == '']

                    # Valida que no existan fechas en blanco
                    if fechainicioenblanco:
                        return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Fecha Inicio deben estar completos"})

                    if fechafinenblanco:
                        return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Fecha Fin deben estar completos"})

                    asignarestadoevaluacion = False

                    # Validar que las fechas de inicio sean menor o igual a fecha de fin
                    for nombreprofesor, inicio, fin in zip(nombresprofesores, fechasinicio, fechasfin):
                        if datetime.strptime(inicio, '%Y-%m-%d').date() > datetime.strptime(fin, '%Y-%m-%d').date():
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio debe ser menor o igual a la fecha de fin para el evaluador:  [ %s ]" % (nombreprofesor)})

                        # Si la fecha actual es mayor o igual a una de las fechas de inicio se debe poner estado EVALUACIÓN
                        if datetime.now().date() >= datetime.strptime(inicio, '%Y-%m-%d').date():
                            asignarestadoevaluacion = True

                    registro_nuevo = False if proyectoinvestigacion.tiene_asignado_evaluadores_proyecto_finalizado() else True

                    # Guardo los evaluadores
                    for idreg, idpe, fechainicio, fechafin in zip(codigosdetalles, codigosprofesores, fechasinicio, fechasfin):
                        # Nuevo evaluador
                        if int(idreg) == 0:
                            # Obtengo persona
                            personaevaluador = Profesor.objects.get(pk=int(idpe)).persona
                            # Guardo evaluador
                            evaluador = ProyectoInvestigacionEvaluador(
                                proyecto=proyectoinvestigacion,
                                tipo=1,
                                persona=personaevaluador,
                                tipoproyecto=2,
                                inicioevaluacion=fechainicio,
                                finevaluacion=fechafin
                            )
                            evaluador.save(request)
                        else:
                            evaluador = ProyectoInvestigacionEvaluador.objects.get(pk=int(idreg))
                            evaluador.inicioevaluacion = fechainicio
                            evaluador.finevaluacion = fechafin
                            evaluador.save(request)

                    # Elimino los que se borraron del detalle
                    if evalinternoseliminados:
                        for evaluador in evalinternoseliminados:
                            evaluador = ProyectoInvestigacionEvaluador.objects.get(pk=int(evaluador['idreg']))
                            evaluador.status = False
                            evaluador.save(request)

                    if registro_nuevo:
                        # Actualizo el estado del proyecto a EVALUADORES ASIGNADOS
                        estado = obtener_estado_solicitud(3, 22)
                        proyectoinvestigacion.estado = estado
                        proyectoinvestigacion.save(request)

                        # Creo el recorrido del proyecto
                        recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                                   fecha=datetime.now().date(),
                                                                   observacion='EVALUADORES ASIGNADOS',
                                                                   estado=estado
                                                                   )
                        recorrido.save(request)

                        # Si se debe asignar estado EVALUACION
                        if asignarestadoevaluacion:
                            # Actualizo el estado del proyecto a EVALUACION
                            estado = obtener_estado_solicitud(3, 23)
                            proyectoinvestigacion.estado = estado
                            proyectoinvestigacion.save(request)

                            # Creo el recorrido del proyecto
                            recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                                       fecha=datetime.now().date(),
                                                                       observacion='EVALUACIÓN EN CURSO',
                                                                       estado=estado
                                                                       )
                            recorrido.save(request)

                        log(u'Agregó evaluadores a proyecto de investigación finalizado: %s' % proyectoinvestigacion, request, "add")
                    else:
                        log(u'Editó evaluadores de proyecto de investigación finalizado: %s' % proyectoinvestigacion, request, "edit")

                    return JsonResponse({"result": "ok"})
                else:
                    x = f.errors
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'subirevaluacion':
            try:
                if not 'idevaluacion' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                evaluacion = EvaluacionProyecto.objects.get(pk=int(encrypt(request.POST['idevaluacion'])))

                archivo = request.FILES['archivoevaluacion']
                descripcionarchivo = 'Archivo evaluación de la propuesta'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if evaluacion.tipo == 1:
                    archivo._name = generar_nombre("evalinterna", archivo._name)
                else:
                    archivo._name = generar_nombre("evalexterna", archivo._name)

                evaluacion.archivoevaluacion = archivo
                evaluacion.save(request)

                log(u'Actualizó archivo de evaluación de propuesta de proyecto: %s' % (evaluacion), request, "edit")
                return JsonResponse({"result": "ok", "ide": evaluacion.id, "urlarchivo": evaluacion.archivoevaluacion.url})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'subirevaluacionfirmada':
            try:
                if not 'idevaluacion' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                evaluacion = EvaluacionProyecto.objects.get(pk=int(encrypt(request.POST['idevaluacion'])))

                archivo = request.FILES['archivoevaluacion']
                descripcionarchivo = 'Archivo evaluación de la propuesta firmada'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if evaluacion.tipo == 1:
                    archivo._name = generar_nombre("evalinternafirmada", archivo._name)
                else:
                    archivo._name = generar_nombre("evalexternafirmada", archivo._name)

                evaluacion.archivoevaluacionfirmada = archivo
                evaluacion.save(request)

                log(u'Actualizó archivo de evaluación firmada de propuesta de proyecto: %s' % (evaluacion), request, "edit")
                return JsonResponse({"result": "ok", "ide": evaluacion.id, "urlarchivo": evaluacion.archivoevaluacionfirmada.url})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'cerrarevaluacion':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                evaluacion = EvaluacionProyecto.objects.get(pk=int(encrypt(request.POST['id'])))
                proyecto = evaluacion.proyecto

                # Obtengo los valores del formulario
                estado = int(request.POST['estado'])
                observacion = request.POST['observacion'].strip().upper() if 'observacion' in request.POST else ''

                # Actualizo la evaluación
                evaluacion.persona = persona
                evaluacion.fecharevision = datetime.now()
                evaluacion.revisado = True
                evaluacion.observacionrevision = observacion
                evaluacion.estadoregistro = estado
                evaluacion.save(request)

                # Si la evaluación a cerrar es INTERNA
                if evaluacion.tipo == 1:
                    # Si el estado del proyecto es EVALUACIÓN INTERNA
                    if proyecto.estado.valor == 7:
                        # Verificar si están las evaluaciones completas para actualizar el estado del proyecto o si el estado es EVALUACION INTERNA ADICIONAL
                        notificardirector = False
                        if proyecto.evaluaciones_internas_completas_cerradas() or proyecto.estado.valor == 9:
                            notificardirector = True
                            # Obtengo los estados asignados en cada evaluación
                            estados = [evaluacion.estado for evaluacion in proyecto.evaluaciones_internas()]

                            # Verifico si hay un estado diferente: si los estados son iguales la longitud del conjunto debe ser 1
                            iguales = len(set(estados)) == 1

                            if iguales:
                                # Si es ACEPTADO
                                if estados[0] == 1:
                                    # Se asigna al proyecto el estado EVALUACION INTERNA SUPERADA
                                    estadoproyecto = obtener_estado_solicitud(3, 8)
                                    observacion = "ETAPA DE EVALUACIÓN INTERNA SUPERADA"
                                # SERÁ ACEPTADO CON MODIFICACIONES MENORES
                                elif estados[0] == 2:
                                    # Se asigna al proyecto el estado REALIZAR MODIFICACIONES MENORES
                                    estadoproyecto = obtener_estado_solicitud(3, 15)
                                    observacion = "REALIZAR MODIFICACIONES MENORES"
                                # DEBE SER PRESENTADO NUEVAMENTE LUEGO DE MODIFICACIONES MAYORES
                                elif estados[0] == 3:
                                    # Se asigna el estado EVALUACIÓN INTERNA ADICIONAL
                                    estadoproyecto = obtener_estado_solicitud(3, 9)
                                    observacion = "REQUIERE EVALUACIÓN INTERNA ADICIONAL"
                                else: # Si es RECHAZADO
                                    # Se asigna el estado de RECHAZADO al proyecto
                                    estadoproyecto = obtener_estado_solicitud(3, 14)
                                    observacion = "PROYECTO RECHAZADO"
                            else:
                                # Obtener las evaluaciones internas
                                evaluaciones = proyecto.evaluaciones_internas()
                                sumaevaluaciones = Decimal(null_to_decimal(evaluaciones.aggregate(valor=Sum('puntajetotal'))['valor'], 2)).quantize(Decimal('.01'))
                                totalevaluaciones = evaluaciones.count()
                                promedio = Decimal(null_to_decimal(sumaevaluaciones / totalevaluaciones, 2)).quantize(Decimal('.01'))

                                # Promedio >= 70
                                if promedio >= 70:
                                    # Consultar Aceptados
                                    if evaluaciones.values('id').filter(estado=1).exists():
                                        # Se asigna al proyecto el estado EVALUACIÓN INTERNA SUPERADA
                                        estadoproyecto = obtener_estado_solicitud(3, 8)
                                        observacion = "ETAPA DE EVALUACIÓN INTERNA SUPERADA"
                                    else:
                                        # Se asigna al proyecto el estado REALIZAR MODIFICACIONES MENORES
                                        estadoproyecto = obtener_estado_solicitud(3, 15)
                                        observacion = "REALIZAR MODIFICACIONES MENORES"
                                else:
                                    if promedio >= 40:
                                        # Se asigna el estado EVALUACIÓN INTERNA ADICIONAL
                                        estadoproyecto = obtener_estado_solicitud(3, 9)
                                        observacion = "REQUIERE EVALUACIÓN INTERNA ADICIONAL"
                                    else:
                                        # Se asigna el estado de RECHAZADO al proyecto
                                        estadoproyecto = obtener_estado_solicitud(3, 14)
                                        observacion = "PROYECTO RECHAZADO"

                            # Asignar el estado al proyecto
                            proyecto.estado = estadoproyecto

                            if estadoproyecto.valor == 15:
                                proyecto.cambiomenor = True
                            elif estadoproyecto.valor == 16:
                                proyecto.cambiomayor = True

                            proyecto.save(request)

                            # Si el estado es EVALUACION INTERNA SUPERADA o REQUIERE MODIFICACIONES MENORES
                            if proyecto.estado.valor == 8 or proyecto.estado.valor == 15:
                                proyecto.puntajeevalint = proyecto.puntaje_final_evaluacion_interna()
                                proyecto.save(request)

                            # Creo el recorrido del proyecto
                            recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                       fecha=datetime.now().date(),
                                                                       observacion=observacion,
                                                                       estado=estadoproyecto
                                                                       )
                            recorrido.save(request)
                    # estado REEVALUACIÓN INTERNA I
                    elif proyecto.estado.valor == 32:
                        # Verificar si están las evaluaciones completas para actualizar el estado del proyecto o si el estado es EVALUACION INTERNA ADICIONAL
                        notificardirector = False
                        if proyecto.reevaluaciones_internas_completas_cerradas() or proyecto.estado.valor == 9:
                            notificardirector = True
                            # Obtengo los estados asignados en cada evaluación
                            estados = [evaluacion.estado for evaluacion in proyecto.evaluacion_interna_adicional()]

                            # Verifico si hay un estado diferente: si los estados son iguales la longitud del conjunto debe ser 1
                            iguales = len(set(estados)) == 1

                            if iguales:
                                # Si es ACEPTADO
                                if estados[0] == 1:
                                    # Se asigna al proyecto el estado EVALUACION INTERNA SUPERADA
                                    estadoproyecto = obtener_estado_solicitud(3, 8)
                                    observacion = "ETAPA DE EVALUACIÓN INTERNA SUPERADA"
                                # SERÁ ACEPTADO CON MODIFICACIONES MENORES
                                elif estados[0] == 2:
                                    # Se asigna al proyecto el estado REALIZAR MODIFICACIONES MENORES
                                    estadoproyecto = obtener_estado_solicitud(3, 15)
                                    observacion = "REALIZAR MODIFICACIONES MENORES"
                                # DEBE SER PRESENTADO NUEVAMENTE LUEGO DE MODIFICACIONES MAYORES
                                elif estados[0] == 3:
                                    # Se asigna el estado de RECHAZADO al proyecto
                                    estadoproyecto = obtener_estado_solicitud(3, 14)
                                    observacion = "PROYECTO RECHAZADO"
                                else:  # Si es RECHAZADO
                                    # Se asigna el estado de RECHAZADO al proyecto
                                    estadoproyecto = obtener_estado_solicitud(3, 14)
                                    observacion = "PROYECTO RECHAZADO"
                            else:
                                # Obtener las evaluaciones internas
                                evaluaciones = proyecto.evaluacion_interna_adicional()
                                sumaevaluaciones = Decimal(null_to_decimal(evaluaciones.aggregate(valor=Sum('puntajetotal'))['valor'], 2)).quantize(Decimal('.01'))
                                totalevaluaciones = evaluaciones.count()
                                promedio = Decimal(null_to_decimal(sumaevaluaciones / totalevaluaciones, 2)).quantize(Decimal('.01'))

                                # Promedio >= 70
                                if promedio >= 70:
                                    # Consultar Aceptados
                                    if evaluaciones.values('id').filter(estado=1).exists():
                                        # Se asigna al proyecto el estado EVALUACIÓN INTERNA SUPERADA
                                        estadoproyecto = obtener_estado_solicitud(3, 8)
                                        observacion = "ETAPA DE EVALUACIÓN INTERNA SUPERADA"
                                    else:
                                        # Se asigna al proyecto el estado REALIZAR MODIFICACIONES MENORES
                                        estadoproyecto = obtener_estado_solicitud(3, 15)
                                        observacion = "REALIZAR MODIFICACIONES MENORES"
                                else:
                                    # Se asigna el estado de RECHAZADO al proyecto
                                    estadoproyecto = obtener_estado_solicitud(3, 14)
                                    observacion = "PROYECTO RECHAZADO"

                            # Asignar el estado al proyecto
                            proyecto.estado = estadoproyecto

                            if estadoproyecto.valor == 15:
                                proyecto.cambiomenor = True
                            elif estadoproyecto.valor == 16:
                                proyecto.cambiomayor = True

                            proyecto.save(request)

                            # Si el estado es EVALUACION INTERNA SUPERADA
                            if proyecto.estado.valor == 8:
                                proyecto.puntajeevalint = proyecto.puntaje_final_evaluacion_interna()
                                proyecto.save(request)

                            # Creo el recorrido del proyecto
                            recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                       fecha=datetime.now().date(),
                                                                       observacion=observacion,
                                                                       estado=estadoproyecto
                                                                       )
                            recorrido.save(request)
                    else:  # estado REEVALUACIÓN INTERNA II
                        notificardirector = True
                        # Consultar 2da Reevaluación interna
                        reevaluacion2 = proyecto.evaluacion_interna_adicional_2()
                        # Si es ACEPTADO
                        if reevaluacion2.estado == 1:
                            # Se asigna al proyecto el estado EVALUACION INTERNA SUPERADA
                            estadoproyecto = obtener_estado_solicitud(3, 8)
                            observacion = "ETAPA DE EVALUACIÓN INTERNA SUPERADA"
                        # SERÁ ACEPTADO CON MODIFICACIONES MENORES
                        elif reevaluacion2.estado == 2:
                            # Se asigna al proyecto el estado REALIZAR MODIFICACIONES MENORES
                            estadoproyecto = obtener_estado_solicitud(3, 15)
                            observacion = "REALIZAR MODIFICACIONES MENORES"
                        else:
                            # Se asigna el estado de RECHAZADO al proyecto
                            estadoproyecto = obtener_estado_solicitud(3, 14)
                            observacion = "PROYECTO RECHAZADO"

                        # Asignar el estado al proyecto
                        proyecto.estado = estadoproyecto

                        if estadoproyecto.valor == 15:
                            proyecto.cambiomenor = True
                        elif estadoproyecto.valor == 16:
                            proyecto.cambiomayor = True

                        proyecto.save(request)

                        # Si el estado es EVALUACION INTERNA SUPERADA
                        if proyecto.estado.valor == 8:
                            proyecto.puntajeevalint = reevaluacion2.puntajetotal
                            proyecto.save(request)

                        # Creo el recorrido del proyecto
                        recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                   fecha=datetime.now().date(),
                                                                   observacion=observacion,
                                                                   estado=estadoproyecto
                                                                   )
                        recorrido.save(request)

                else:  # Evaluación EXTERNA
                    # Si el estado del proyecto es EVALUACIÓN EXTERNA
                    if proyecto.estado.valor == 10:
                        notificardirector = False

                        if proyecto.evaluaciones_externas_completas_cerradas() or proyecto.estado.valor == 12:
                            notificardirector = True
                            # Obtengo los estados asignados en cada evaluación
                            estados = [evaluacion.estado for evaluacion in proyecto.evaluaciones_externas()]

                            # Verifico si hay un estado diferente: si los estados son iguales la longitud del conjunto debe ser 1
                            iguales = len(set(estados)) == 1

                            if iguales:
                                # Si es ACEPTADO
                                if estados[0] == 1:
                                    # Se asigna al proyecto el estado EVALUACION EXTERNA SUPERADA
                                    estadoproyecto = obtener_estado_solicitud(3, 11)
                                    observacion = "ETAPA DE EVALUACIÓN EXTERNA SUPERADA"
                                # SERÁ ACEPTADO CON MODIFICACIONES MENORES
                                elif estados[0] == 2:
                                    # Se asigna al proyecto el estado REALIZAR MODIFICACIONES MENORES E.E.
                                    estadoproyecto = obtener_estado_solicitud(3, 38)
                                    observacion = "REALIZAR MODIFICACIONES MENORES E.E."
                                # DEBE SER PRESENTADO NUEVAMENTE LUEGO DE MODIFICACIONES MAYORES
                                elif estados[0] == 3:
                                    # Se asigna el estado EVALUACIÓN EXTERNA ADICIONAL
                                    estadoproyecto = obtener_estado_solicitud(3, 12)
                                    observacion = "REQUIERE EVALUACIÓN EXTERNA ADICIONAL"
                                else:  # Si es RECHAZADO
                                    # Se asigna el estado de RECHAZADO al proyecto
                                    estadoproyecto = obtener_estado_solicitud(3, 27)
                                    observacion = "PROYECTO RECHAZADO"
                            else:
                                # Obtener las evaluaciones externas
                                evaluaciones = proyecto.evaluaciones_externas()
                                sumaevaluaciones = Decimal(null_to_decimal(evaluaciones.aggregate(valor=Sum('puntajetotal'))['valor'], 2)).quantize(Decimal('.01'))
                                totalevaluaciones = evaluaciones.count()
                                promedio = Decimal(null_to_decimal(sumaevaluaciones / totalevaluaciones, 2)).quantize(Decimal('.01'))

                                # Promedio >= 70
                                if promedio >= 70:
                                    # Consultar Aceptados
                                    if evaluaciones.values('id').filter(estado=1).exists():
                                        # Se asigna al proyecto el estado ETAPA DE EVALUACIÓN EXTERNA SUPERADA
                                        estadoproyecto = obtener_estado_solicitud(3, 11)
                                        observacion = "ETAPA DE EVALUACIÓN EXTERNA SUPERADA"
                                    else:
                                        # Se asigna al proyecto el estado REALIZAR MODIFICACIONES MENORES E.E.
                                        estadoproyecto = obtener_estado_solicitud(3, 38)
                                        observacion = "REALIZAR MODIFICACIONES MENORES E.E."
                                else:
                                    if promedio >= 40:
                                        # Se asigna el estado REQUIERE EVALUACIÓN EXTERNA ADICIONAL
                                        estadoproyecto = obtener_estado_solicitud(3, 12)
                                        observacion = "REQUIERE EVALUACIÓN EXTERNA ADICIONAL"
                                    else:
                                        # Se asigna el estado de RECHAZADO al proyecto
                                        estadoproyecto = obtener_estado_solicitud(3, 27)
                                        observacion = "PROYECTO RECHAZADO"

                            # Asignar el estado al proyecto
                            proyecto.estado = estadoproyecto
                            if estadoproyecto.valor == 38:
                                proyecto.cambiomenor = True
                            elif estadoproyecto.valor == 39:
                                proyecto.cambiomayor = True

                            proyecto.save(request)

                            # Si el estado es EVALUACION EXTERNA SUPERADA o REQUIERE MODIFICACIONES MENORES
                            if proyecto.estado.valor == 11 or proyecto.estado.valor == 38:
                                proyecto.puntajeevalext = proyecto.puntaje_final_evaluacion_externa()
                                proyecto.save(request)

                            # Creo el recorrido del proyecto
                            recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                       fecha=datetime.now().date(),
                                                                       observacion=observacion,
                                                                       estado=estadoproyecto
                                                                       )
                            recorrido.save(request)

                            # Si el estado es EVALUACION EXTERNA SUPERADA se debe asignar el estado ACEPTADO PARA IR A CGA
                            if proyecto.estado.valor == 11:
                                # Se asigna el estado ACEPTADO PARA IR A CGA
                                estadoproyecto = obtener_estado_solicitud(3, 13)
                                observacion = "PROYECTO ACEPTADO PARA IR A CGA"

                                proyecto.estado = estadoproyecto
                                proyecto.save(request)

                                # Creo el recorrido del proyecto
                                recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                           fecha=datetime.now().date(),
                                                                           observacion=observacion,
                                                                           estado=estadoproyecto
                                                                           )
                                recorrido.save(request)
                    # estado REEVALUACIÓN EXTERNA I
                    elif proyecto.estado.valor == 33:
                        # Verificar si están las evaluaciones completas para actualizar el estado del proyecto o si el estado es EVALUACION INTERNA ADICIONAL
                        notificardirector = False
                        if proyecto.reevaluaciones_externas_completas_cerradas() or proyecto.estado.valor == 11:
                            notificardirector = True
                            # Obtengo los estados asignados en cada evaluación
                            estados = [evaluacion.estado for evaluacion in proyecto.evaluacion_externa_adicional()]

                            # Verifico si hay un estado diferente: si los estados son iguales la longitud del conjunto debe ser 1
                            iguales = len(set(estados)) == 1

                            if iguales:
                                # Si es ACEPTADO
                                if estados[0] == 1:
                                    # Se asigna al proyecto el estado EVALUACION EXTERNA SUPERADA
                                    estadoproyecto = obtener_estado_solicitud(3, 11)
                                    observacion = "ETAPA DE EVALUACIÓN EXTERNA SUPERADA"
                                # SERÁ ACEPTADO CON MODIFICACIONES MENORES
                                elif estados[0] == 2:
                                    # Se asigna al proyecto el estado REALIZAR MODIFICACIONES MENORES E.E.
                                    estadoproyecto = obtener_estado_solicitud(3, 38)
                                    observacion = "REALIZAR MODIFICACIONES MENORES E.E."
                                # DEBE SER PRESENTADO NUEVAMENTE LUEGO DE MODIFICACIONES MAYORES
                                elif estados[0] == 3:
                                    # # Se asigna el estado REALIZAR MODIFICACIONES MAYORES
                                    # estadoproyecto = obtener_estado_solicitud(3, 16)
                                    # observacion = "REALIZAR MODIFICACIONES MAYORES"
                                    #

                                    # # Se asigna el estado EVALUACIÓN EXTERNA ADICIONAL II
                                    # estadoproyecto = obtener_estado_solicitud(3, 35)
                                    # observacion = "REQUIERE EVALUACIÓN EXTERNA ADICIONAL II"

                                    # Se asigna el estado de RECHAZADO al proyecto
                                    estadoproyecto = obtener_estado_solicitud(3, 27)
                                    observacion = "PROYECTO RECHAZADO"
                                else:  # Si es RECHAZADO
                                    # Se asigna el estado de RECHAZADO al proyecto
                                    estadoproyecto = obtener_estado_solicitud(3, 27)
                                    observacion = "PROYECTO RECHAZADO"
                            else:
                                # Obtener las reevaluaciones externas
                                evaluaciones = proyecto.evaluacion_externa_adicional()
                                sumaevaluaciones = Decimal(null_to_decimal(evaluaciones.aggregate(valor=Sum('puntajetotal'))['valor'], 2)).quantize(Decimal('.01'))
                                totalevaluaciones = evaluaciones.count()
                                promedio = Decimal(null_to_decimal(sumaevaluaciones / totalevaluaciones, 2)).quantize(Decimal('.01'))

                                # Promedio >= 70
                                if promedio >= 70:
                                    # Consultar Aceptados
                                    if evaluaciones.values('id').filter(estado=1).exists():
                                        # Se asigna al proyecto el estado EVALUACIÓN EXTERNA SUPERADA
                                        estadoproyecto = obtener_estado_solicitud(3, 11)
                                        observacion = "ETAPA DE EVALUACIÓN EXTERNA SUPERADA"
                                    else:
                                        # Se asigna al proyecto el estado REALIZAR MODIFICACIONES MENORES E.E.
                                        estadoproyecto = obtener_estado_solicitud(3, 38)
                                        observacion = "REALIZAR MODIFICACIONES MENORES E.E."
                                else:
                                    estadoproyecto = obtener_estado_solicitud(3, 27)
                                    observacion = "PROYECTO RECHAZADO"

                                # # Obtener las reevaluaciones externas
                                # evaluaciones = proyecto.evaluacion_externa_adicional()
                                #
                                # # Consultar Aceptados y Modificaciones menores
                                # if evaluaciones.values('id').filter(estado=1) and evaluaciones.values('id').filter(estado=2):
                                #     # Se asigna al proyecto el estado REALIZAR MODIFICACIONES MENORES E.E.
                                #     estadoproyecto = obtener_estado_solicitud(3, 38)
                                #     observacion = "REALIZAR MODIFICACIONES MENORES E.E."
                                # else:
                                #     # # Se asigna el estado EVALUACIÓN EXTERNA ADICIONAL II
                                #     # estadoproyecto = obtener_estado_solicitud(3, 35)
                                #     # observacion = "REQUIERE EVALUACIÓN EXTERNA ADICIONAL II"
                                #     # Se asigna el estado de RECHAZADO al proyecto
                                #     estadoproyecto = obtener_estado_solicitud(3, 27)
                                #     observacion = "PROYECTO RECHAZADO"

                            # Asignar el estado al proyecto
                            proyecto.estado = estadoproyecto

                            if estadoproyecto.valor == 38:
                                proyecto.cambiomenor = True
                            elif estadoproyecto.valor == 39:
                                proyecto.cambiomayor = True

                            proyecto.save(request)

                            # Si el estado es EVALUACION EXTERNA SUPERADA
                            if proyecto.estado.valor == 11:
                                proyecto.puntajeevalext = proyecto.puntaje_final_evaluacion_externa()
                                proyecto.save(request)

                            # Creo el recorrido del proyecto
                            recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                       fecha=datetime.now().date(),
                                                                       observacion=observacion,
                                                                       estado=estadoproyecto
                                                                       )
                            recorrido.save(request)

                            # Si el estado es EVALUACION EXTERNA SUPERADA se debe asignar el estado ACEPTADO PARA IR A CGA
                            if proyecto.estado.valor == 11:
                                # Se asigna el estado ACEPTADO PARA IR A CGA
                                estadoproyecto = obtener_estado_solicitud(3, 13)
                                observacion = "PROYECTO ACEPTADO PARA IR A CGA"

                                proyecto.estado = estadoproyecto
                                proyecto.save(request)

                                # Creo el recorrido del proyecto
                                recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                           fecha=datetime.now().date(),
                                                                           observacion=observacion,
                                                                           estado=estadoproyecto
                                                                           )
                                recorrido.save(request)
                    else:  # estado REEVALUACIÓN INTERNA II
                        notificardirector = True
                        # Consultar 2da Reevaluación externa
                        reevaluacion2 = proyecto.evaluacion_externa_adicional_2()
                        # Si es ACEPTADO
                        if reevaluacion2.estado == 1:
                            # Se asigna al proyecto el estado EVALUACION EXTERNA SUPERADA
                            estadoproyecto = obtener_estado_solicitud(3, 11)
                            observacion = "ETAPA DE EVALUACIÓN EXTERNA SUPERADA"
                        # SERÁ ACEPTADO CON MODIFICACIONES MENORES
                        elif reevaluacion2.estado == 2:
                            # Se asigna al proyecto el estado REALIZAR MODIFICACIONES MENORES E.E.
                            estadoproyecto = obtener_estado_solicitud(3, 38)
                            observacion = "REALIZAR MODIFICACIONES MENORES E.E."
                        else:
                            # Se asigna el estado de RECHAZADO al proyecto
                            estadoproyecto = obtener_estado_solicitud(3, 27)
                            observacion = "PROYECTO RECHAZADO"

                        # Asignar el estado al proyecto
                        proyecto.estado = estadoproyecto

                        if estadoproyecto.valor == 38:
                            proyecto.cambiomenor = True
                        elif estadoproyecto.valor == 39:
                            proyecto.cambiomayor = True

                        proyecto.save(request)

                        # Si el estado es EVALUACION EXTERNA SUPERADA
                        if proyecto.estado.valor == 11:
                            proyecto.puntajeevalext = reevaluacion2.puntajetotal
                            proyecto.save(request)

                        # Creo el recorrido del proyecto
                        recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                   fecha=datetime.now().date(),
                                                                   observacion=observacion,
                                                                   estado=estadoproyecto
                                                                   )
                        recorrido.save(request)

                        # Si el estado es EVALUACION EXTERNA SUPERADA se debe asignar el estado ACEPTADO PARA IR A CGA
                        if proyecto.estado.valor == 11:
                            # Se asigna el estado ACEPTADO PARA IR A CGA
                            estadoproyecto = obtener_estado_solicitud(3, 13)
                            observacion = "PROYECTO ACEPTADO PARA IR A CGA"

                            proyecto.estado = estadoproyecto
                            proyecto.save(request)

                            # Creo el recorrido del proyecto
                            recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                       fecha=datetime.now().date(),
                                                                       observacion=observacion,
                                                                       estado=estadoproyecto
                                                                       )
                            recorrido.save(request)


                # Notificar por e-mail al evaluador
                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                # Destinatarios
                personaevaluador = evaluacion.evaluador.persona
                lista_email_envio = personaevaluador.lista_emails_envio()
                lista_email_cco = []
                lista_archivos_adjuntos = []

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                # CERRADA
                if estado == 5:
                    if evaluacion.tipo == 1:
                        tiponotificacion = "EVALINTCERR"
                        tituloemail = "Evaluación Interna de Propuesta de Proyecto de Investigación Cerrada"
                    else:
                        tiponotificacion = "EVALEXTCERR"
                        tituloemail = "Evaluación Externa de Propuesta de Proyecto de Investigación Cerrada"
                else:
                    # NOVEDAD
                    if evaluacion.tipo == 1:
                        tiponotificacion = "EVALINTNOV"
                        tituloemail = "Novedades Evaluación Interna de Propuesta de Proyecto de Investigación"
                    else:
                        tiponotificacion = "EVALEXTNOV"
                        tituloemail = "Novedades Evaluación Externa de Propuesta de Proyecto de Investigación"


                titulo = "Proyectos de Investigación"
                send_html_mail(tituloemail,
                               "emails/propuestaproyectoinvestigacion.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'proyecto': proyecto,
                                'saludo': 'Estimada' if personaevaluador.sexo_id == 1 else 'Estimado',
                                'nombrepersona': personaevaluador.nombre_completo_inverso(),
                                'observaciones': observacion
                                },
                               lista_email_envio,  # Destinatarioa
                               lista_email_cco,  # Copia oculta, poner [] para que no me envíe jaja
                               lista_archivos_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                # Notificar al director del proyecto
                if notificardirector:
                    if proyecto.estado.valor == 8:
                        tiponotificacion = "EVALINTSUP"
                        tituloemail = "Evaluación Interna de Propuesta de Proyecto de Investigación Superada"
                    elif proyecto.estado.valor in [9, 34]:
                        tiponotificacion = "EVALINTADI"
                        tituloemail = "Propuesta de Proyecto de Investigación requiere Evaluación Interna Adicional"
                    elif proyecto.estado.valor == 15:
                        tiponotificacion = "EVALINTMODMENOR"
                        tituloemail = "Propuesta de Proyecto de Investigación requiere Modificaciones Menores"
                    elif proyecto.estado.valor == 16:
                        tiponotificacion = "EVALINTMODMAYOR"
                        tituloemail = "Propuesta de Proyecto de Investigación requiere Modificaciones Mayores"
                    elif proyecto.estado.valor == 14:
                        tiponotificacion = "EVALINTNOSUP"
                        tituloemail = "Evaluación Interna de Propuesta de Proyecto de Investigación No superada"
                    elif proyecto.estado.valor == 13:
                        tiponotificacion = "EVALEXTSUP"
                        tituloemail = "Evaluación Externa de Propuesta de Proyecto de Investigación Superada"
                    elif proyecto.estado.valor in [12, 35]:
                        tiponotificacion = "EVALEXTADI"
                        tituloemail = "Propuesta de Proyecto de Investigación requiere Evaluación Externa Adicional"
                    elif proyecto.estado.valor == 38:
                        tiponotificacion = "EVALEXTMODMENOR"
                        tituloemail = "Propuesta de Proyecto de Investigación requiere Modificaciones Menores"
                    elif proyecto.estado.valor == 27:
                        tiponotificacion = "EVALEXTNOSUP"
                        tituloemail = "Evaluación Externa de Propuesta de Proyecto de Investigación No superada"

                    lista_email_envio = proyecto.profesor.persona.lista_emails_envio()
                    lista_archivos_adjuntos = []

                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
                    titulo = "Proyectos de Investigación"
                    send_html_mail(tituloemail,
                                   "emails/propuestaproyectoinvestigacion.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'tiponotificacion': tiponotificacion,
                                    'saludo': 'Estimada' if proyecto.profesor.persona.sexo_id == 1 else 'Estimado',
                                    'nombrepersona': proyecto.profesor.persona.nombre_completo_inverso(),
                                    'observaciones': '',
                                    'proyecto': proyecto
                                    },
                                   lista_email_envio,  # Destinatarioa
                                   lista_email_cco,  # Copia oculta, poner [] para que no me envíe jaja
                                   lista_archivos_adjuntos,  # Adjunto(s)
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                if estado == 5:
                    log(u'%s cerró evaluación de propuesta de proyecto: %s' % (persona, evaluacion), request, "edit")
                else:
                    log(u'%s registró novedad en evaluación de propuesta de proyecto: %s' % (persona, evaluacion), request, "edit")

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True, "ide": evaluacion.id, "estado": evaluacion.estadoregistro})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addintegrante':
            try:
                if not 'idproyecto' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                proyectoinvestigacion = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idproyecto'])))
                convocatoria = proyectoinvestigacion.convocatoria

                tipopersona = int(request.POST['tipopersona'])
                personaintegrante = int(request.POST['persona_select2'])

                if 'funcionpersona' in request.POST:
                    funcionpersona = int(request.POST['funcionpersona'])
                else:
                    # Si es estudiante
                    if tipopersona == 2:
                        funcionpersona = 4 # AYUDANTE DE INVESTIGACION
                    elif tipopersona == 3: # Si es administrativo
                        funcionpersona = 3 # INVESTIGADOR ASOCIADO
                    else: # externo
                        funcionpersona = 5  # INVESTIGADOR COLABORADOR

                observacion = request.POST['observacion'].strip()
                archivo = None

                if 'archivosoporte' in request.FILES:
                    archivo = request.FILES['archivosoporte']
                    descripcionarchivo = 'Archivo de soporte'

                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    archivo._name = generar_nombre("soporteintegrante", archivo._name)

                # Validar el límite de integrantes
                if convocatoria.apertura.year > 2020:
                    if funcionpersona in [1, 2, 3]:
                        if proyectoinvestigacion.cantidad_integrantes_unemi() >= convocatoria.maxintegranteu:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se pueden agregar más integrantes <b>UNEMI</b> al proyecto", "showSwal": "True", "swalType": "warning"})
                    elif funcionpersona == 5:
                        if proyectoinvestigacion.cantidad_integrantes_externos() >= convocatoria.maxintegrantee:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se pueden agregar más integrantes <b>EXTERNOS</b> al proyecto", "showSwal": "True", "swalType": "warning"})

                if tipopersona == 1:
                    persona_id = Profesor.objects.get(pk=personaintegrante).persona.id
                elif tipopersona == 2:
                    persona_id = Inscripcion.objects.get(pk=personaintegrante).persona.id
                elif tipopersona == 3:
                    persona_id = Administrativo.objects.get(pk=personaintegrante).persona.id
                else:
                    persona_id = Externo.objects.get(pk=personaintegrante).persona.id

                # Verificar que no haya sido registrado previamente
                if proyectoinvestigacion.proyectoinvestigacionintegrante_set.values("id").filter(status=True, persona_id=persona_id).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La persona ya consta como integrante del proyecto", "showSwal": "True", "swalType": "warning"})

                # Verifico que la persona no sea el director del proyecto
                if proyectoinvestigacion.proyectoinvestigacionintegrante_set.values("id").filter(status=True, persona_id=persona_id, funcion=1).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se puede agregar al integrante debido a que consta como <b>DIRECTOR</b>", "showSwal": "True", "swalType": "warning"})

                # Si el rol es co-director validar que otro integrante no cumpla ese mismo rol
                if proyectoinvestigacion.proyectoinvestigacionintegrante_set.values("id").filter(status=True, persona_id=persona_id, funcion=2, tiporegistro__in=[1, 3, 4]).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Ya existe otro integrante del proyecto con el rol de <b>CO-DIRECTOR</b>", "showSwal": "True", "swalType": "warning"})

                # Si es función de co-director validar que no esté participando en otro proyecto con esta función
                if funcionpersona == 2 and convocatoria.apertura.year > 2020:
                    if ProyectoInvestigacionIntegrante.objects.values("id").filter(status=True, persona_id=persona_id, funcion=funcionpersona).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La persona ya consta como co-director en otro proyecto", "showSwal": "True", "swalType": "warning"})

                # Guardo el integrante
                integranteproyecto = ProyectoInvestigacionIntegrante(
                    proyecto=proyectoinvestigacion,
                    funcion=funcionpersona,
                    tipo=tipopersona,
                    persona_id=persona_id,
                    profesor_id=personaintegrante if tipopersona == 1 else None,
                    inscripcion_id=personaintegrante if tipopersona == 2 else None,
                    administrativo_id=personaintegrante if tipopersona == 3 else None,
                    externo_id=personaintegrante if tipopersona == 4 else None,
                    observacion=observacion,
                    archivo=archivo,
                    tiporegistro=4 if proyectoinvestigacion.estado.valor == 20 and convocatoria.apertura.year > 2020 else 1,
                    estadoacreditado=2 if funcionpersona in [1, 2] else 4
                )
                integranteproyecto.save(request)

                # Actualizo el proyecto
                if convocatoria.apertura.year > 2020 and proyectoinvestigacion.estado.valor == 13:
                    proyectoinvestigacion.documentogenerado = False
                    proyectoinvestigacion.archivodocumentofirmado = None

                # Si el rol es DIRECTOR se debe actualizar el profesor solicitante
                if funcionpersona == 1:
                    proyectoinvestigacion.profesor = integranteproyecto.profesor

                proyectoinvestigacion.save(request)

                log(u'%s agregó integrante a proyecto de investigación: %s - %s' % (persona, proyectoinvestigacion, integranteproyecto), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'editintegrante':
            try:
                if not 'idproyecto' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                integranteproyecto = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.POST['idi'])))
                funcionpersona = int(request.POST['funcionpersona'])
                observacion = request.POST['observacion'].strip()
                archivo = None

                if 'archivosoporte' in request.FILES:
                    archivo = request.FILES['archivosoporte']
                    descripcionarchivo = 'Archivo de soporte'
                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    archivo._name = generar_nombre("soporteintegrante", archivo._name)

                # Si es función de co-director validar que no esté participando en otro proyecto con esta función
                if funcionpersona == 2:
                    if ProyectoInvestigacionIntegrante.objects.values("id").filter(status=True, persona_id=integranteproyecto.persona_id, funcion=funcionpersona).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La persona ya consta como co-director en otro proyecto"})

                integranteproyecto.funcion = funcionpersona
                integranteproyecto.observacion = observacion

                if archivo:
                    integranteproyecto.archivo = archivo

                    # Consulto a quién reemplazó para actualizar el archivo
                    reemplazado = ProyectoInvestigacionIntegrante.objects.get(personareemplazo=integranteproyecto.persona)
                    reemplazado.archivo = archivo
                    reemplazado.save(request)

                integranteproyecto.save(request)

                log(u'%s editó integrante a proyecto de investigación: %s - %s' % (persona, integranteproyecto.proyecto, integranteproyecto), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'reemplazarintegrante':
            try:
                if not 'idproyecto' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                proyectoinvestigacion = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idproyecto'])))
                integranteproyecto = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.POST['idi'])))

                tipopersona = int(request.POST['tipopersonareemp'])
                personaintegrante = int(request.POST['personareemp_select2'])
                funcionpersona = integranteproyecto.funcion # La misma función que tiene el que va a ser reemplazad
                observacion = request.POST['observacionreemp'].strip()
                archivo = request.FILES['archivosoportereemp']
                descripcionarchivo = 'Archivo de soporte'

                if tipopersona == 1:
                    persona_id = Profesor.objects.get(pk=personaintegrante).persona.id
                elif tipopersona == 2:
                    persona_id = Inscripcion.objects.get(pk=personaintegrante).persona.id
                elif tipopersona == 3:
                    persona_id = Administrativo.objects.get(pk=personaintegrante).persona.id
                else:
                    persona_id = Externo.objects.get(pk=personaintegrante).persona.id

                # Validar que no sean las mismas personas
                if integranteproyecto.persona.id == persona_id:
                    return JsonResponse({"result": "bad", "mensaje": u"Las personas deben ser distintas"})

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                archivo._name = generar_nombre("soporteintegrante", archivo._name)

                # validar que no esté participando en mas de 1 proyecto
                if ProyectoInvestigacionIntegrante.objects.values("id").filter(status=True, persona_id=persona_id).count() > 1:
                    return JsonResponse({"result": "bad", "mensaje": u"La persona puede participar máximo en 2 proyectos"})

                # Si es función de co-director validar que no esté participando en otro proyecto con esta función
                if funcionpersona == 2:
                    if ProyectoInvestigacionIntegrante.objects.values("id").filter(status=True, persona_id=persona_id, funcion=funcionpersona).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La persona ya consta como co-director en otro proyecto"})

                # Actualizo al integrante reemplazado
                integranteproyecto.personareemplazo_id = persona_id
                integranteproyecto.tiporegistro = 2
                integranteproyecto.archivo = archivo
                integranteproyecto.save(request)

                # Agrego el integrante reemplazador
                integranteproyecto = ProyectoInvestigacionIntegrante(
                    proyecto=proyectoinvestigacion,
                    funcion=funcionpersona,
                    tipo=tipopersona,
                    persona_id=persona_id,
                    profesor_id=personaintegrante if tipopersona == 1 else None,
                    inscripcion_id=personaintegrante if tipopersona == 2 else None,
                    administrativo_id=personaintegrante if tipopersona == 3 else None,
                    externo_id=personaintegrante if tipopersona == 4 else None,
                    observacion=observacion,
                    archivo=archivo,
                    tiporegistro=3
                )
                integranteproyecto.save(request)

                log(u'%s reemplazó integrante a proyecto de investigación: %s - %s' % (persona, proyectoinvestigacion, integranteproyecto), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'editrol':
            try:
                if not 'idproyecto' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                proyectoinvestigacion = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idproyecto'])))
                convocatoria = proyectoinvestigacion.convocatoria
                integranteproyecto = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.POST['idi'])))

                funcionanterior = integranteproyecto.funcion
                funcionpersona = int(request.POST['rolpersona'])
                observacion = request.POST['observacioneditrol'].strip()
                archivo = None

                # Validar el archivo
                if 'archivosoporteeditrol' in request.FILES:
                    archivo = request.FILES['archivosoporteeditrol']
                    descripcionarchivo = 'Archivo de soporte'

                    resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    archivo._name = generar_nombre("soporteintegrante", archivo._name)

                # Si es función de director o co-director validar que no esté participando en otro proyecto con esta función
                if funcionpersona in [1, 2]:
                    # Valida que no esté participando en otro proyecto con esos roles
                    if convocatoria.apertura.year > 2020:
                        if ProyectoInvestigacionIntegrante.objects.values("id").filter(status=True, persona=integranteproyecto.persona, funcion=funcionpersona).exclude(proyecto=proyectoinvestigacion).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"La persona ya consta como %s en otro proyecto" % ("DIRECTOR" if funcionpersona == 1 else "CO-DIRECTOR")})

                    # Valida que otra persona no tenga el mismo rol en el proyecto actual
                    if proyectoinvestigacion.proyectoinvestigacionintegrante_set.filter(status=True, funcion=funcionpersona).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe otro integrante del proyecto con el rol de %s" % ("DIRECTOR" if funcionpersona == 1 else "CO-DIRECTOR")})

                # Actualizo los datos del integrante
                integranteproyecto.funcion = funcionpersona
                integranteproyecto.observacion = observacion
                integranteproyecto.archivo = archivo
                integranteproyecto.save(request)

                # Actualizo el proyecto
                if convocatoria.apertura.year > 2020 and proyectoinvestigacion.estado.valor not in [18, 20]:
                    proyectoinvestigacion.documentogenerado = False
                    proyectoinvestigacion.archivodocumentofirmado = None

                # Si el rol es DIRECTOR se debe actualizar el profesor solicitante
                if funcionpersona == 1:
                    proyectoinvestigacion.profesor = integranteproyecto.profesor
                elif funcionanterior == 1:
                    proyectoinvestigacion.profesor = None

                proyectoinvestigacion.save(request)
                log(u'%s editó rol del integrante a proyecto de investigación: %s - %s' % (persona, proyectoinvestigacion, integranteproyecto), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'delintegrante':
            try:
                if not 'idproyecto' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                proyectoinvestigacion = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idproyecto'])))
                convocatoria = proyectoinvestigacion.convocatoria
                integranteproyecto = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.POST['idi'])))

                observacion = request.POST['observaciondelint'].strip()
                archivo = None

                if 'archivosoportedelint' in request.FILES:
                    archivo = request.FILES['archivosoportedelint']
                    descripcionarchivo = 'Archivo de soporte'

                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    archivo._name = generar_nombre("soporteintegrante", archivo._name)

                # Elimino al integrante
                integranteproyecto.observacion = observacion
                integranteproyecto.archivo = archivo
                integranteproyecto.status = False
                integranteproyecto.save(request)

                # Elimino la actividad del crograma de actividades asociados al integrante
                for actividadasignada in integranteproyecto.persona.proyectoinvestigacioncronogramaresponsable_set.filter(status=True).order_by('id'):
                    actividadasignada.status = False
                    actividadasignada.save(request)

                # Actualizo el proyecto
                if convocatoria.apertura.year > 2020 and proyectoinvestigacion.estado.valor not in [18, 20]:
                    proyectoinvestigacion.documentogenerado = False
                    proyectoinvestigacion.archivodocumentofirmado = None

                proyectoinvestigacion.save(request)

                log(u'%s eliminó integrante de proyecto de investigación: %s - %s' % (persona, proyectoinvestigacion, integranteproyecto), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'descargarpresupuesto':
            try:
                import time as ET

                if 'idc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la convocatoria
                convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.POST['idc'])))

                # Aquí se almacenan los archivos de excel de los presupuestos
                directorio = SITE_STORAGE + '/media/proyectoinvestigacion/presupuesto'
                try:
                    os.stat(directorio)
                except:
                    os.mkdir(directorio)

                caracteres_a_quitar = "!\"\#$%&()=?¡'¿{}[],.-+*/|°^~:;"

                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'zipav'))

                response = HttpResponse(content_type='application/zip')
                response['Content-Disposition'] = 'attachment; filename=presupuestosproyecto_' + random.randint(1, 10000).__str__() + '.zip'

                nombre_archivo = "presupuestosproyectos" + str(convocatoria.apertura.year) + ".zip"
                filename = os.path.join(output_folder, nombre_archivo)
                fantasy_zip = zipfile.ZipFile(filename, 'w')

                # Consultar los proyectos que no tengan estado: EN EDICIÓN, RECHAZADO, PROPUESTA RECHAZADA
                proyectos = ProyectoInvestigacion.objects.filter(status=True, convocatoria=convocatoria).exclude(estado__valor__in=[1, 14, 27]).order_by('id')

                # Carpeta donde se crearán los archivos de excel
                output_folder_excel = os.path.join(os.path.join(SITE_STORAGE, 'media', 'proyectoinvestigacion', 'presupuesto'))

                for proyecto in proyectos:
                    # Creo el archivo de excel con el presupuesto
                    titulo = proyecto.titulo.upper()
                    palabras = titulo.split(" ")
                    titulo = "_".join(palabras[0:5])
                    titulo = remover_caracteres(titulo, caracteres_a_quitar)

                    titulo = elimina_tildes(remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(titulo)))
                    nombrearchivo = "PROYECTO_" + titulo + ".xlsx"

                    # Create un nuevo archivo de excel y le agrega una hoja
                    workbook = xlsxwriter.Workbook(output_folder_excel + '/' + nombrearchivo)
                    ws = workbook.add_worksheet("Presupuesto")

                    fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])
                    fceldageneral = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneral"])
                    ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
                    fceldafecha = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdafecha"])
                    fceldamoneda = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamoneda"])
                    ftextonegrita = workbook.add_format(FORMATOS_CELDAS_EXCEL["textonegrita"])
                    fmoneda = workbook.add_format(FORMATOS_CELDAS_EXCEL["formatomoneda"])
                    fceldanegritacent = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdanegritacent"])
                    fceldanegritaizq = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdanegritaizq"])
                    fceldamonedapie = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamonedapie"])

                    ws.merge_range(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
                    ws.merge_range(1, 0, 1, 7, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADO', ftitulo1)
                    ws.merge_range(2, 0, 2, 7, 'COORDINACIÓN DE INVESTIGACIÓN', ftitulo1)
                    ws.merge_range(3, 0, 3, 7, 'PRESUPUESTO DE PROYECTO DE INVESTIGACIÓN', ftitulo1)

                    ws.write(5, 0, "Título: " + proyecto.titulo, ftextonegrita)
                    ws.write(6, 0, "Director: " + proyecto.profesor.persona.nombre_completo_inverso(), ftextonegrita)
                    ws.write(6, 3, "Tiempo duración: " + str(proyecto.tiempomes) + " meses", ftextonegrita)
                    ws.write(6, 5, "Presupuesto Total: ", ftextonegrita)
                    ws.write(6, 6, proyecto.presupuesto, fmoneda)

                    columns = [
                        (u"N°", 4),
                        (u"RECURSO", 40),
                        (u"DESCRIPCIÓN", 40),
                        (u"UNIDAD MEDIDA", 16),
                        (u"CANTIDAD", 16),
                        (u"VALOR UNITARIO", 16),
                        (u"VALOR TOTAL", 16),
                        (u"OBSERVACIONES", 40)
                    ]

                    row_num = 8
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                        ws.set_column(col_num, col_num, columns[col_num][1])

                    # Datos del presupuesto
                    listagrupos = []
                    grupos_presupuesto = proyecto.presupuesto_grupo_totales()
                    for grupo in grupos_presupuesto:
                        # ID GRUPO, DESCRIPCION, TOTAL X GRUPO
                        listagrupos.append([grupo['id'], grupo['descripcion'], grupo['totalgrupo']])

                    datospresupuesto = []
                    detalles_presupuesto = proyecto.presupuesto_detallado().filter(valortotal__gt=0)  # .order_by('tiporecurso__orden', 'tiporecurso__id', 'id')
                    for detalle in detalles_presupuesto:
                        # ID GRUPO, RECURSO, DESCRIPCION, UNIDAD MEDIDA, CANTIDAD, PRECIO, IVA, TOTAL, OBSERVACION
                        datospresupuesto.append([
                            detalle.tiporecurso.id,
                            detalle.recurso,
                            detalle.descripcion,
                            detalle.unidadmedida.nombre,
                            detalle.cantidad,
                            detalle.valorunitario,
                            detalle.valoriva,
                            detalle.valortotal,
                            detalle.observacion
                        ])

                    # LLenar los detalles del presupuesto
                    cgrupo = 1
                    for grupo in listagrupos:
                        # Agrego la cabecera del grupo
                        row_num += 1
                        ws.write(row_num, 0, cgrupo, fceldanegritacent)
                        ws.merge_range(row_num, 1, row_num, 7, grupo[1], fceldanegritaizq)

                        # Agrego los detalles por cada grupo
                        for detalle in datospresupuesto:
                            if grupo[0] == detalle[0]:
                                row_num += 1
                                ws.write(row_num, 0, "", fceldageneral)
                                ws.write(row_num, 1, detalle[1], fceldageneral)
                                ws.write(row_num, 2, detalle[2] if detalle[2] else "", fceldageneral)
                                ws.write(row_num, 3, detalle[3], fceldageneral)
                                ws.write(row_num, 4, detalle[4], fceldageneral)
                                ws.write(row_num, 5, detalle[5], fceldamoneda)
                                ws.write(row_num, 6, detalle[7], fceldamoneda)
                                ws.write(row_num, 7, detalle[8], fceldageneral)

                        # Agrego el total por el grupo
                        row_num += 1
                        ws.merge_range(row_num, 0, row_num, 5, "TOTAL " + grupo[1], fceldanegritaizq)
                        ws.write(row_num, 6, grupo[2], fceldamonedapie)
                        ws.write(row_num, 7, "", fceldanegritaizq)
                        cgrupo += 1

                    # Agrego el total del presupuesto
                    row_num += 1
                    ws.merge_range(row_num, 0, row_num, 5, "PRESUPUESTO TOTAL DEL PROYECTO", fceldanegritaizq)
                    ws.write(row_num, 6, proyecto.presupuesto, fceldamonedapie)
                    ws.write(row_num, 7, "", fceldanegritaizq)

                    workbook.close()

                    # ruta_archivo_excel1 = "media/proyectoinvestigacion/presupuesto/" + nombrearchivo
                    ruta_archivo_excel = output_folder_excel + "/" + nombrearchivo

                    # Agrego el archivo a la carpeta comprimida
                    fantasy_zip.write(ruta_archivo_excel, nombrearchivo)

                    # Borro el archivo de excel creado
                    ET.sleep(3)
                    os.remove(ruta_archivo_excel)

                fantasy_zip.close()

                ruta_zip = "media/zipav/" + nombre_archivo

                return JsonResponse({'result': 'ok', 'archivo': ruta_zip})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al descargar evidencias. Detalle: [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'descargarpresupuestofinal':
            try:
                import time as ET

                if 'idc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la convocatoria
                convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.POST['idc'])))

                caracteres_a_quitar = "!\"\#$%&()=?¡'¿{}[],.-+*/|°^~:;"

                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'zipav'))

                response = HttpResponse(content_type='application/zip')
                response['Content-Disposition'] = 'attachment; filename=presupuestosproyecto_' + random.randint(1, 10000).__str__() + '.zip'

                nombre_archivo = "presupuestosproyectos" + str(convocatoria.apertura.year) + ".zip"
                filename = os.path.join(output_folder, nombre_archivo)
                fantasy_zip = zipfile.ZipFile(filename, 'w')

                # Consultar los proyectos que no tengan estado: EN EDICIÓN, RECHAZADO, PROPUESTA RECHAZADA
                proyectos = ProyectoInvestigacion.objects.filter(status=True, convocatoria=convocatoria).exclude(estado__valor__in=[1, 14, 27]).order_by('id')

                for proyecto in proyectos:
                    if proyecto.archivopresupuesto:
                        titulo = proyecto.titulo.upper()
                        palabras = titulo.split(" ")
                        titulo = "_".join(palabras[0:5])
                        titulo = remover_caracteres(titulo, caracteres_a_quitar)

                        titulo = elimina_tildes(remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(titulo)))
                        nombrearchivo = "PROYECTO_" + titulo

                        ext = proyecto.archivopresupuesto.__str__()[proyecto.archivopresupuesto.__str__().rfind("."):]

                        if os.path.exists(SITE_STORAGE + proyecto.archivopresupuesto.url):
                            fantasy_zip.write(SITE_STORAGE + proyecto.archivopresupuesto.url, nombrearchivo + ext.lower())

                fantasy_zip.close()

                ruta_zip = "media/zipav/" + nombre_archivo

                return JsonResponse({'result': 'ok', 'archivo': ruta_zip})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al descargar evidencias. Detalle: [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'descargarcronograma':
            try:
                import time as ET

                if 'idc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la convocatoria
                convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.POST['idc'])))

                # Aquí se almacenan los archivos de excel de los cronogramas
                directorio = SITE_STORAGE + '/media/proyectoinvestigacion/cronograma'
                try:
                    os.stat(directorio)
                except:
                    os.mkdir(directorio)

                caracteres_a_quitar = "!\"\#$%&()=?¡'¿{}[],.-+*/|°^~:;"

                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'zipav'))

                response = HttpResponse(content_type='application/zip')
                response['Content-Disposition'] = 'attachment; filename=cronogramasproyecto_' + random.randint(1, 10000).__str__() + '.zip'

                nombre_archivo = "cronogramasproyectos" + str(convocatoria.apertura.year) + ".zip"
                filename = os.path.join(output_folder, nombre_archivo)
                fantasy_zip = zipfile.ZipFile(filename, 'w')

                # Consultar los proyectos que no tengan estado: EN EDICIÓN, RECHAZADO, PROPUESTA RECHAZADA
                proyectos = ProyectoInvestigacion.objects.filter(status=True, convocatoria=convocatoria).exclude(estado__valor__in=[1, 14, 27]).order_by('id')

                # Carpeta donde se crearán los archivos de excel
                output_folder_excel = os.path.join(os.path.join(SITE_STORAGE, 'media', 'proyectoinvestigacion', 'cronograma'))

                for proyecto in proyectos:
                    # Creo el archivo de excel con el cronograma
                    titulo = proyecto.titulo.upper()
                    palabras = titulo.split(" ")
                    titulo = "_".join(palabras[0:5])
                    titulo = remover_caracteres(titulo, caracteres_a_quitar)

                    titulo = elimina_tildes(remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(titulo)))
                    nombrearchivo = "PROYECTO_" + titulo + ".xlsx"

                    # Create un nuevo archivo de excel y le agrega una hoja
                    workbook = xlsxwriter.Workbook(output_folder_excel + '/' + nombrearchivo)
                    ws = workbook.add_worksheet("Cronograma")

                    fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])
                    fceldageneral = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneral"])
                    ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
                    fceldafecha = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdafecha"])
                    fceldamoneda = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamoneda"])
                    ftextonegrita = workbook.add_format(FORMATOS_CELDAS_EXCEL["textonegrita"])
                    fmoneda = workbook.add_format(FORMATOS_CELDAS_EXCEL["formatomoneda"])
                    fceldanegritacent = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdanegritacent"])
                    fceldanegritaizq = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdanegritaizq"])
                    fceldamonedapie = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamonedapie"])
                    fceldaporcentaje = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdaporcentaje"])
                    fceldaporcentajepie = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdaporcentajepie"])

                    ws.merge_range(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
                    ws.merge_range(1, 0, 1, 6, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADO', ftitulo1)
                    ws.merge_range(2, 0, 2, 6, 'COORDINACIÓN DE INVESTIGACIÓN', ftitulo1)
                    ws.merge_range(3, 0, 3, 6, 'CRONOGRAMA DE PROYECTO DE INVESTIGACIÓN', ftitulo1)

                    ws.merge_range(5, 0, 5, 6, "Título: " + proyecto.titulo, ftextonegrita)
                    ws.merge_range(6, 0, 6, 1, "Director: " + proyecto.profesor.persona.nombre_completo_inverso(), ftextonegrita)
                    ws.write(6, 2, "Tiempo duración: " + str(proyecto.tiempomes) + " meses", ftextonegrita)
                    ws.write(6, 5, "Presupuesto Total: ", ftextonegrita)
                    ws.write(6, 6, proyecto.presupuesto, fmoneda)
                    ws.merge_range(7, 0, 7, 6, "Objetivo General: " + BeautifulSoup(proyecto.objetivogeneral, "lxml").text, ftextonegrita)

                    columns = [
                        (u"N°", 4),
                        (u"ACTIVIDAD", 74),
                        (u"PONDERACIÓN (%)", 16),
                        (u"FECHA INICIO", 14),
                        (u"FECHA FIN", 14),
                        (u"ENTREGABLE", 26),
                        (u"RESPONSABLES", 45)
                    ]

                    # Datos del cronograma de actividades
                    listaobjetivos = []
                    objetivos_cronograma = proyecto.cronograma_objetivo_totales()
                    for objetivo in objetivos_cronograma:
                        # Id, descripcion, total actividades, total ponderacion
                        listaobjetivos.append([objetivo['id'], objetivo['descripcion'], objetivo['totalactividades'], objetivo['totalponderacion']])

                    datoscronograma = []
                    detalles_cronograma = proyecto.cronograma_detallado()
                    auxid = 0
                    secuencia = 0
                    totalponderacion = 0
                    for detalle in detalles_cronograma:
                        secuencia += 1
                        totalponderacion += detalle.ponderacion
                        if auxid != detalle.objetivo.id:
                            secuencia_grupo = 1
                            auxid = detalle.objetivo.id
                        else:
                            secuencia_grupo += 1

                        # id objetivo, secuencia, secuencia grupo, actividad, ponderacion, fecha inicio, fecha fin, entregables, responsables
                        datoscronograma.append([
                            detalle.objetivo.id,
                            secuencia,
                            secuencia_grupo,
                            detalle.actividad,
                            detalle.ponderacion,
                            detalle.fechainicio,
                            detalle.fechafin,
                            detalle.entregables(),
                            detalle.responsables()
                        ])

                    row_num = 8
                    # Llenar los detalles del cronograma
                    for objetivo in listaobjetivos:
                        # Agrego el objetivo especifico
                        row_num += 1
                        ws.merge_range(row_num, 0, row_num, 6, "Objetivo Específico: " + objetivo[1], fceldanegritaizq)
                        row_num += 1

                        # Agrego las columnas
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                            ws.set_column(col_num, col_num, columns[col_num][1])

                        # Agrego los detalles de actividades por cada objetivo
                        for detalle in datoscronograma:
                            if objetivo[0] == detalle[0]:
                                row_num += 1
                                ws.write(row_num, 0, detalle[1], fceldageneral)
                                ws.write(row_num, 1, detalle[3], fceldageneral)
                                ws.write(row_num, 2, detalle[4] / 100, fceldaporcentaje)
                                ws.write(row_num, 3, detalle[5], fceldafecha)
                                ws.write(row_num, 4, detalle[6], fceldafecha)
                                ws.write(row_num, 5, detalle[7], fceldageneral)
                                ws.write(row_num, 6, detalle[8], fceldageneral)

                        # Agrego el total por el objetivo
                        row_num += 1
                        ws.merge_range(row_num, 0, row_num, 1, "TOTAL PONDERACIÓN OBJETIVO ESPECÍFICO", fceldanegritaizq)
                        ws.write(row_num, 2, objetivo[3] / 100, fceldaporcentajepie)
                        ws.merge_range(row_num, 3, row_num, 6, "", fceldanegritaizq)

                    # Agrego fila de ponderación total
                    row_num += 1
                    ws.merge_range(row_num, 0, row_num, 1, "PONDERACIÓN TOTAL", fceldanegritaizq)
                    ws.write(row_num, 2, 1, fceldaporcentajepie)
                    ws.merge_range(row_num, 3, row_num, 6, "", fceldanegritaizq)

                    workbook.close()

                    # ruta_archivo_excel11 = "media/proyectoinvestigacion/cronograma/" + nombrearchivo
                    ruta_archivo_excel = output_folder_excel + "/" + nombrearchivo

                    # Agrego el archivo a la carpeta comprimida
                    fantasy_zip.write(ruta_archivo_excel, nombrearchivo)

                    # Borro el archivo de excel creado
                    ET.sleep(3)
                    os.remove(ruta_archivo_excel)

                fantasy_zip.close()

                ruta_zip = "media/zipav/" + nombre_archivo

                return JsonResponse({'result': 'ok', 'archivo': ruta_zip})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al descargar evidencias. Detalle: [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'verificarcambiosmenores':
            try:
                if not 'idproyecto' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                proyectoinvestigacion = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idproyecto'])))

                estado = int(request.POST['estado'])
                observaciongeneral = request.POST['observacion'].strip().upper() if 'observacion' in request.POST else 'EVALUACIÓN INTERNA DE PROPUESTA SUPERADA'
                documentos = json.loads(request.POST['lista_items1'])
                observacionesdoc = request.POST.getlist('observaciondoc[]')

                archivo = ''
                if 'archivo' in request.FILES:
                    archivo = request.FILES['archivo']
                    descripcionarchivo = 'Archivo de novedades'
                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    archivo._name = generar_nombre("novedades", archivo._name)

                # Obtengo el registro del estado
                estadopropuesta = obtener_estado_solicitud(3, estado)

                # Actualizo el proyecto
                proyectoinvestigacion.estado = estadopropuesta
                proyectoinvestigacion.fechaverirequi = datetime.now()

                # Actualizo el estado del documento formulario de inscripción
                for documento, observacion in zip(documentos, observacionesdoc):
                    proyectoinvestigacion.estadodocumentofirmado = 2 if documento['valor'] is True else 4
                    proyectoinvestigacion.observaciondocumentofirmado = observacion.strip().upper()
                    break

                if archivo:
                    proyectoinvestigacion.archivonovedad = archivo

                proyectoinvestigacion.verificado = 1
                proyectoinvestigacion.save(request)

                # Creo el recorrido del proyecto
                recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                           fecha=datetime.now().date(),
                                                           observacion=observaciongeneral if observaciongeneral else estadopropuesta.observacion,
                                                           estado=estadopropuesta
                                                           )
                recorrido.save(request)

                # Si el estado es EVALUACION INTERNA/EXTERNA SUPERADA, debo generar el documento del proyecto sin los nombres de los integrantes
                if estado == 8 or estado == 11:
                    # Genero documento sin nombres de los integrantes
                    documentogenerado = generar_documento_proyecto_sin_nombreintegrantes(proyectoinvestigacion, data)

                    if documentogenerado['estado'] == 'ok':
                        # Actualizo el campo archivo documento sin integrantes
                        proyectoinvestigacion.archivodocumentosindatint = documentogenerado['archivo']
                        proyectoinvestigacion.save(request)

                # Si hay archivo debo crear el historial
                if archivo:
                    historialarchivo = ProyectoInvestigacionHistorialArchivo(
                        proyecto=proyectoinvestigacion,
                        tipo=3,
                        archivo=proyectoinvestigacion.archivonovedad
                    )
                    historialarchivo.save(request)

                # Si es EVALUACIÓN EXTERNA SUPERADA
                if estado == 11:
                    # Se asigna al proyecto el estado ACEPTADO
                    estado = obtener_estado_solicitud(3, 13)
                    observacion = "PROYECTO ACEPTADO PARA IR A CGA"
                    proyectoinvestigacion.estado = estado
                    proyectoinvestigacion.save(request)

                    # Creo el recorrido del proyecto
                    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                               fecha=datetime.now().date(),
                                                               observacion=observacion,
                                                               estado=estado
                                                               )
                    recorrido.save(request)

                if proyectoinvestigacion.estado.valor == 8:
                    tiponotificacion = "EVALINTSUP"
                    tituloemail = "Evaluación Interna de Propuesta de Proyecto de Investigación Superada"
                elif proyectoinvestigacion.estado.valor == 14:
                    tiponotificacion = "EVALINTNOSUP"
                    tituloemail = "Evaluación Interna de Propuesta de Proyecto de Investigación No superada"
                elif proyectoinvestigacion.estado.valor == 13:
                    tiponotificacion = "EVALEXTSUP"
                    tituloemail = "Evaluación Externa de Propuesta de Proyecto de Investigación Superada"
                else:
                    tiponotificacion = "EVALEXTNOSUP"
                    tituloemail = "Evaluación Externa de Propuesta de Proyecto de Investigación No superada"

                lista_email_envio = proyectoinvestigacion.profesor.persona.lista_emails_envio()
                lista_email_cco = []
                lista_archivos_adjuntos = []

                if proyectoinvestigacion.archivonovedad and estado != 8:
                    lista_archivos_adjuntos.append(proyectoinvestigacion.archivonovedad)

                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
                titulo = "Proyectos de Investigación"

                send_html_mail(tituloemail,
                               "emails/propuestaproyectoinvestigacion.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimada' if proyectoinvestigacion.profesor.persona.sexo_id == 1 else 'Estimado',
                                'nombrepersona': proyectoinvestigacion.profesor.persona.nombre_completo_inverso(),
                                'observaciones': '',
                                'proyecto': proyectoinvestigacion
                                },
                               lista_email_envio,  # Destinatarioa
                               lista_email_cco,  # Copia oculta, poner [] para que no me envíe jaja
                               lista_archivos_adjuntos,  # Adjunto(s)
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                if proyectoinvestigacion.estado.valor == 8:
                    log(u'%s verificó cambios menores en propuesta de proyecto de investigación, evaluación interna superada: %s' % (persona, proyectoinvestigacion), request, "edit")
                elif proyectoinvestigacion.estado.valor == 13:
                    log(u'%s verificó cambios menores en propuesta de proyecto de investigación, evaluación externa superada: %s' % (persona, proyectoinvestigacion), request, "edit")
                else:
                    log(u'%s rechazó propuesta de proyecto debido a novedades en cambios menores en propuesta de proyecto de investigación: %s' % (persona, proyectoinvestigacion), request, "edit")

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'resetearclave':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                evaluador = EvaluadorProyecto.objects.get(pk=int(encrypt(request.POST['id'])))
                externo = evaluador.externo
                resetear_clave(externo.persona)

                log(u'%s reseteó clave de evaluador externo de proyectos: %s' % (persona, externo), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'anularproyecto':
            try:
                if not 'idproyecto' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                archivo = request.FILES['archivorespaldoanul']
                descripcionarchivo = 'Archivo Respaldo Anulación'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                proyectoinvestigacion = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idproyecto'])))

                observacion = request.POST['observacionanulproy'].strip().upper()
                archivo._name = generar_nombre("anulacion", archivo._name)

                # Obtener el estado ANULADO
                estado = obtener_estado_solicitud(3, 44)

                # Actualizo el proyecto
                proyectoinvestigacion.observacion = observacion
                proyectoinvestigacion.archivoanulacion = archivo
                proyectoinvestigacion.estado = estado
                proyectoinvestigacion.save(request)

                # Creo el recorrido del proyecto
                recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                           fecha=datetime.now().date(),
                                                           observacion=observacion,
                                                           estado=estado
                                                           )
                recorrido.save(request)

                log(u'%s anuló proyecto de investigación: %s' % (persona, proyectoinvestigacion), request, "edit")

                return JsonResponse({"result": "ok", "idp": request.POST['idproyecto']})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'revisarinformefinal':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['id'])))

                if informeproyecto:
                    # Verifico que no haya sido revisado por el coordinador de investigación o actualizado por el docente
                    if informeproyecto.estado == 2:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el registro debido a que fue editado por el Director del proyecto", "showSwal": "True", "swalType": "warning"})
                    elif informeproyecto.estado == 7:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el registro debido a que fue revisado por el Coordinador de investigación", "showSwal": "True", "swalType": "warning"})

                    estado = int(request.POST['estado'])
                    observacion = request.POST['observacion'].strip() if 'observacion' in request.POST else ''

                    # Actualizo el informe
                    informeproyecto.observacionverificacion = observacion
                    informeproyecto.fechaverificacion = datetime.now()
                    informeproyecto.estado = estado
                    informeproyecto.save(request)

                    # En caso de existir NOVEDAD se debe notificar
                    if estado == 6:
                        # Envio de e-mail de notificacion al solicitante
                        listacuentascorreo = [29]  # investigacion@unemi.edu.ec

                        lista_email_envio = []
                        lista_email_cco = []
                        # lista_email_envio.append('olopezn@unemi.edu.ec')

                        for integrante in informeproyecto.proyecto.integrantes_proyecto():
                            lista_email_envio += integrante.persona.lista_emails_envio()
                            break

                        fechaenvio = datetime.now().date()
                        horaenvio = datetime.now().time()
                        cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                        tituloemail = "Novedades Informe Final de Proyecto de Investigación"
                        tiponotificacion = "NOVEDADINFORME"
                        lista_archivos_adjuntos = []
                        titulo = "Proyectos de Investigación"

                        send_html_mail(tituloemail,
                                       "emails/propuestaproyectoinvestigacion.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'titulo': titulo,
                                        'fecha': fechaenvio,
                                        'hora': horaenvio,
                                        'tiponotificacion': tiponotificacion,
                                        'numeroinforme': informeproyecto.numero,
                                        'tipoinforme': 'de un informe de avance' if informeproyecto.tipo == 1 else 'del informe final',
                                        'tituloproyecto': informeproyecto.proyecto.titulo,
                                        'observaciones': observacion
                                        },
                                       lista_email_envio,  # Destinatarioa
                                       lista_email_cco,  # Copia oculta
                                       lista_archivos_adjuntos,  # Adjunto(s)
                                       cuenta=CUENTAS_CORREOS[cuenta][1]
                                       )

                    if estado == 5:
                        log(u'% revisó informe final de proyecto de investigación: %s' % (persona, informeproyecto), request, "edit")
                    else:
                        log(u'% rechazó informe final de proyecto de investigación: %s' % (persona, informeproyecto), request, "edit")

                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El informe del proyecto de investigación no existe", "showSwal": "True", "swalType": "warning"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'aprobarinformefinal':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['id'])))

                if informeproyecto:
                    # Verifico que el informe no haya sido cargado por el docente o revisado por el técnico de investigación
                    if informeproyecto.estado == 4:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el registro debido a que el informe ya fue impreso y cargado por el docente", "showSwal": "True", "swalType": "warning"})
                    elif informeproyecto.estado == 6:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el registro debido a que fué revisado por el técnico de investigación", "showSwal": "True", "swalType": "warning"})

                    estado = int(request.POST['estado'])
                    observacion = request.POST['observacion'].strip() if 'observacion' in request.POST else ''

                    informeproyecto.observacionaprobacion = observacion
                    informeproyecto.fechaaprobacion = datetime.now()
                    informeproyecto.aprobado = (estado == 7)
                    informeproyecto.estado = estado
                    informeproyecto.save(request)

                    # Envio de e-mail de notificacion al solicitante o al que revisó el informe
                    listacuentascorreo = [29]  # investigacion@unemi.edu.ec

                    fechaenvio = datetime.now().date()
                    horaenvio = datetime.now().time()
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                    if estado == 7:
                        lista_email_envio = []
                        lista_email_cco = []
                        for integrante in informeproyecto.proyecto.integrantes_proyecto():
                            lista_email_envio += integrante.persona.lista_emails_envio()
                            break

                        tituloemail = "Informe Final de Proyecto de Investigación Aprobado"
                        tiponotificacion = "APRUEBAINFORME"
                    else:
                        lista_email_envio = informeproyecto.personaverifica.lista_emails_envio()
                        lista_email_cco = []

                        tituloemail = "Novedades Informe Final de Proyecto de Investigación"
                        tiponotificacion = "NOVEDADINFORMEAPRO"

                    lista_archivos_adjuntos = []
                    titulo = "Proyectos de Investigación"

                    # Si es APROBADO se notifica a los integrantes del proyecto
                    if estado == 7:
                        send_html_mail(tituloemail,
                                       "emails/propuestaproyectoinvestigacion.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'titulo': titulo,
                                        'fecha': fechaenvio,
                                        'hora': horaenvio,
                                        'tiponotificacion': tiponotificacion,
                                        'numeroinforme': informeproyecto.numero,
                                        'tipoinforme': 'informe de avance' if informeproyecto.tipo == 1 else 'informe final',
                                        'tituloproyecto': informeproyecto.proyecto.titulo,
                                        'observaciones': observacion
                                        },
                                       lista_email_envio,  # Destinatarioa
                                       lista_email_cco,  # Copia oculta
                                       lista_archivos_adjuntos,  # Adjunto(s)
                                       cuenta=CUENTAS_CORREOS[cuenta][1]
                                       )
                    else:
                        # Si tiene novedades se notifica al usuario que revisó el informe
                        send_html_mail(tituloemail,
                                       "emails/propuestaproyectoinvestigacion.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'titulo': titulo,
                                        'fecha': fechaenvio,
                                        'hora': horaenvio,
                                        'tiponotificacion': tiponotificacion,
                                        'saludo': 'Estimada' if informeproyecto.personaverifica.sexo_id == 1 else 'Estimado',
                                        'nombrepersona': informeproyecto.personaverifica.nombre_completo_inverso(),
                                        'numeroinforme': informeproyecto.numero,
                                        'tipoinforme': 'del informe de avance' if informeproyecto.tipo == 1 else 'del informe final',
                                        'tituloproyecto': informeproyecto.proyecto.titulo,
                                        'observaciones': observacion
                                        },
                                       lista_email_envio,  # Destinatarioa
                                       lista_email_cco,  # Copia oculta
                                       lista_archivos_adjuntos,  # Adjunto(s)
                                       cuenta=CUENTAS_CORREOS[cuenta][1]
                                       )

                    if estado == 7:
                        log(u'%s aprobó informe final de proyecto de investigación: %s' % (persona, informeproyecto), request, "edit")
                    else:
                        log(u'%s asignó novedades en informe final de proyecto de investigación: %s' % (persona, informeproyecto), request, "edit")

                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El informe del proyecto de investigación no existe", "showSwal": "True", "swalType": "warning"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'descargarpresupuestoindividual':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto el proyecto
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                caracteres_a_quitar = "!\"\#$%&()=?¡'¿{}[],.-+*/|°^~:;"

                # Aquí se almacenan los archivos de excel de los cronogramas
                directorio = SITE_STORAGE + '/media/proyectoinvestigacion/presupuesto'
                try:
                    os.stat(directorio)
                except:
                    os.mkdir(directorio)

                # Carpeta donde se crearán los archivos de excel
                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'proyectoinvestigacion', 'presupuesto'))

                # Creo el archivo de excel con el presupuesto
                titulo = proyecto.titulo.upper()
                palabras = titulo.split(" ")
                titulo = "_".join(palabras[0:5])
                titulo = remover_caracteres(titulo, caracteres_a_quitar)

                titulo = elimina_tildes(remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(titulo)))
                nombrearchivo = "PRESUPUESTO_PROYECTO_" + titulo + ".xlsx"

                # Create un nuevo archivo de excel y le agrega una hoja
                workbook = xlsxwriter.Workbook(output_folder + '/' + nombrearchivo)
                ws = workbook.add_worksheet("Presupuesto")

                fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])
                fceldageneral = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneral"])
                ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
                fceldafecha = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdafecha"])
                fceldamoneda = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamoneda"])
                ftextonegrita = workbook.add_format(FORMATOS_CELDAS_EXCEL["textonegrita"])
                fmoneda = workbook.add_format(FORMATOS_CELDAS_EXCEL["formatomoneda"])
                fceldanegritacent = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdanegritacent"])
                fceldanegritaizq = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdanegritaizq"])
                fceldamonedapie = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamonedapie"])

                ws.merge_range(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
                ws.merge_range(1, 0, 1, 7, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADO', ftitulo1)
                ws.merge_range(2, 0, 2, 7, 'FACULTAD DE INVESTIGACIÓN', ftitulo1)
                ws.merge_range(3, 0, 3, 7, 'PRESUPUESTO DE PROYECTO DE INVESTIGACIÓN', ftitulo1)
                ws.merge_range(5, 0, 5, 7, "Título: " + proyecto.titulo, ftextonegrita)
                ws.merge_range(6, 0, 6, 2, "Director: " + proyecto.profesor.persona.nombre_completo_inverso(), ftextonegrita)
                ws.merge_range(6, 3, 6, 4, f"Tiempo duración: {proyecto.tiempomes} meses", ftextonegrita)
                ws.merge_range(6, 6, 6, 7, f"Presupuesto Total $: {proyecto.presupuesto:.2f} ", ftextonegrita)

                columns = [
                    (u"N°", 4),
                    (u"RECURSO", 40),
                    (u"DESCRIPCIÓN", 40),
                    (u"UNIDAD MEDIDA", 16),
                    (u"CANTIDAD", 16),
                    (u"VALOR UNITARIO", 16),
                    (u"VALOR TOTAL", 16),
                    (u"OBSERVACIONES", 40)
                ]

                row_num = 8
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                    ws.set_column(col_num, col_num, columns[col_num][1])

                # Datos del presupuesto
                listagrupos = []
                grupos_presupuesto = proyecto.presupuesto_grupo_totales()
                for grupo in grupos_presupuesto:
                    # ID GRUPO, DESCRIPCION, TOTAL X GRUPO
                    listagrupos.append([grupo['id'], grupo['descripcion'], grupo['totalgrupo']])

                datospresupuesto = []
                detalles_presupuesto = proyecto.presupuesto_detallado().filter(valortotal__gt=0)  # .order_by('tiporecurso__orden', 'tiporecurso__id', 'id')
                for detalle in detalles_presupuesto:
                    # ID GRUPO, RECURSO, DESCRIPCION, UNIDAD MEDIDA, CANTIDAD, PRECIO, IVA, TOTAL, OBSERVACION
                    datospresupuesto.append([
                        detalle.tiporecurso.id,
                        detalle.recurso,
                        detalle.descripcion,
                        detalle.unidadmedida.nombre,
                        detalle.cantidad,
                        detalle.valorunitario,
                        detalle.valoriva,
                        detalle.valortotal,
                        detalle.observacion
                    ])

                # LLenar los detalles del presupuesto
                cgrupo = 1
                for grupo in listagrupos:
                    # Agrego la cabecera del grupo
                    row_num += 1
                    ws.write(row_num, 0, cgrupo, fceldanegritacent)
                    ws.merge_range(row_num, 1, row_num, 7, grupo[1], fceldanegritaizq)

                    # Agrego los detalles por cada grupo
                    for detalle in datospresupuesto:
                        if grupo[0] == detalle[0]:
                            row_num += 1
                            ws.write(row_num, 0, "", fceldageneral)
                            ws.write(row_num, 1, detalle[1], fceldageneral)
                            ws.write(row_num, 2, detalle[2] if detalle[2] else "", fceldageneral)
                            ws.write(row_num, 3, detalle[3], fceldageneral)
                            ws.write(row_num, 4, detalle[4], fceldageneral)
                            ws.write(row_num, 5, detalle[5], fceldamoneda)
                            ws.write(row_num, 6, detalle[7], fceldamoneda)
                            ws.write(row_num, 7, detalle[8], fceldageneral)

                    # Agrego el total por el grupo
                    row_num += 1
                    ws.merge_range(row_num, 0, row_num, 5, "TOTAL " + grupo[1], fceldanegritaizq)
                    ws.write(row_num, 6, grupo[2], fceldamonedapie)
                    ws.write(row_num, 7, "", fceldanegritaizq)
                    cgrupo += 1

                # Agrego el total del presupuesto
                row_num += 1
                ws.merge_range(row_num, 0, row_num, 5, "PRESUPUESTO TOTAL DEL PROYECTO", fceldanegritaizq)
                ws.write(row_num, 6, proyecto.presupuesto, fceldamonedapie)
                ws.write(row_num, 7, "", fceldanegritaizq)

                workbook.close()

                ruta = "media/proyectoinvestigacion/presupuesto/" + nombrearchivo

                return JsonResponse({'result': 'ok', 'archivo': ruta})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al descargar el presupuesto. Detalle: [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'descargarcronogramaindividual':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto el proyecto
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                caracteres_a_quitar = "!\"\#$%&()=?¡'¿{}[],.-+*/|°^~:;"

                # Aquí se almacenan los archivos de excel de los cronogramas
                directorio = SITE_STORAGE + '/media/proyectoinvestigacion/cronograma'
                try:
                    os.stat(directorio)
                except:
                    os.mkdir(directorio)

                # Carpeta donde se crearán los archivos de excel
                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'proyectoinvestigacion', 'cronograma'))

                # Creo el archivo de excel con el cronograma
                titulo = proyecto.titulo.upper()
                palabras = titulo.split(" ")
                titulo = "_".join(palabras[0:5])
                titulo = remover_caracteres(titulo, caracteres_a_quitar)

                titulo = elimina_tildes(remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(titulo)))
                nombrearchivo = "CRONOGRAMA_PROYECTO_" + titulo + ".xlsx"

                # Create un nuevo archivo de excel y le agrega una hoja
                workbook = xlsxwriter.Workbook(output_folder + '/' + nombrearchivo)
                ws = workbook.add_worksheet("Cronograma")

                fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])
                fceldageneral = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneral"])
                fceldageneralcent = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneralcent"])
                ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
                fceldafecha = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdafecha"])
                fceldamoneda = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamoneda"])
                ftextonegrita = workbook.add_format(FORMATOS_CELDAS_EXCEL["textonegrita"])
                fmoneda = workbook.add_format(FORMATOS_CELDAS_EXCEL["formatomoneda"])
                fceldanegritacent = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdanegritacent"])
                fceldanegritaizq = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdanegritaizq"])
                fceldamonedapie = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamonedapie"])
                fceldaporcentaje = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdaporcentaje"])
                fceldaporcentajepie = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdaporcentajepie"])

                ws.merge_range(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
                ws.merge_range(1, 0, 1, 10, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADO', ftitulo1)
                ws.merge_range(2, 0, 2, 10, 'FACULTAD DE INVESTIGACIÓN', ftitulo1)
                ws.merge_range(3, 0, 3, 10, 'CRONOGRAMA DE PROYECTO DE INVESTIGACIÓN', ftitulo1)
                ws.merge_range(5, 0, 5, 10, "Título: " + proyecto.titulo, ftextonegrita)
                ws.merge_range(6, 0, 6, 10, "Director: " + proyecto.profesor.persona.nombre_completo_inverso(), ftextonegrita)
                ws.merge_range(7, 0, 7, 1, f"Tiempo duración: {proyecto.tiempomes} meses", ftextonegrita)
                ws.merge_range(7, 3, 7, 4, f"Presupuesto Total: $ {proyecto.presupuesto:.2f}", ftextonegrita)

                ws.merge_range(8, 0, 8, 10, "Objetivo General: " + BeautifulSoup(proyecto.objetivogeneral, "lxml").text.strip(), ftextonegrita)
                ws.set_row_pixels(8, 30)

                columns = [
                    (u"N°", 4),
                    (u"ACTIVIDAD", 74),
                    (u"PONDERACIÓN (%)", 16),
                    (u"ESTADO AVANCE", 14),
                    (u"PORCENTAJE AVANCE", 14),
                    (u"FECHA INICIO", 14),
                    (u"FECHA FIN", 14),
                    (u"ENTREGABLE", 26),
                    (u"EVIDENCIA CONTROL INFORMES", 26),
                    (u"OBSERVACIONES", 26),
                    (u"RESPONSABLES ACTIVIDAD", 45)
                ]

                # Datos del cronograma de actividades
                listaobjetivos = []
                objetivos_cronograma = proyecto.cronograma_objetivo_totales()
                for objetivo in objetivos_cronograma:
                    # Id, descripcion, total actividades, total ponderacion
                    listaobjetivos.append([objetivo['id'], objetivo['descripcion'], objetivo['totalactividades'], objetivo['totalponderacion']])

                datoscronograma = []
                detalles_cronograma = proyecto.cronograma_detallado()
                auxid = 0
                secuencia = 0
                totalponderacion = 0
                for detalle in detalles_cronograma:
                    secuencia += 1
                    totalponderacion += detalle.ponderacion
                    if auxid != detalle.objetivo.id:
                        secuencia_grupo = 1
                        auxid = detalle.objetivo.id
                    else:
                        secuencia_grupo += 1

                    # id objetivo, secuencia, secuencia grupo, actividad, ponderacion, fecha inicio, fecha fin, entregables, responsables

                    # Consultar ultimo estado de avance
                    ultimo_avance_actividad = detalle.ultimo_avance_actividad()
                    if ultimo_avance_actividad:
                        estadoavance = ultimo_avance_actividad.get_estadoactual_display().title()
                        porcentajeavance = ultimo_avance_actividad.avanceactual
                    else:
                        estadoavance = "Por Iniciar"
                        porcentajeavance = 0

                    datoscronograma.append([
                        detalle.objetivo.id,
                        secuencia,
                        secuencia_grupo,
                        detalle.actividad,
                        detalle.ponderacion,
                        estadoavance,
                        porcentajeavance,
                        detalle.fechainicio,
                        detalle.fechafin,
                        detalle.entregable if detalle.entregable else detalle.entregables(),
                        detalle.evidenciacontrolinforme,
                        detalle.observaciongeneral,
                        detalle.responsables().title()
                    ])

                row_num = 9
                # Llenar los detalles del cronograma
                for objetivo in listaobjetivos:
                    # Agrego el objetivo especifico
                    row_num += 1
                    ws.merge_range(row_num, 0, row_num, 10, "Objetivo Específico: " + objetivo[1], fceldanegritaizq)
                    row_num += 1

                    # Agrego las columnas
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                        ws.set_column(col_num, col_num, columns[col_num][1])

                    # Agrego los detalles de actividades por cada objetivo
                    for detalle in datoscronograma:
                        if objetivo[0] == detalle[0]:
                            row_num += 1
                            ws.write(row_num, 0, detalle[1], fceldageneral)
                            ws.write(row_num, 1, detalle[3], fceldageneral)
                            ws.write(row_num, 2, detalle[4] / 100, fceldaporcentaje)
                            ws.write(row_num, 3, detalle[5], fceldageneralcent)
                            ws.write(row_num, 4, detalle[6] / 100, fceldaporcentaje)
                            ws.write(row_num, 5, detalle[7], fceldafecha)
                            ws.write(row_num, 6, detalle[8], fceldafecha)
                            ws.write(row_num, 7, detalle[9], fceldageneral)
                            ws.write(row_num, 8, detalle[10], fceldageneral)
                            ws.write(row_num, 9, detalle[11], fceldageneral)
                            ws.write(row_num, 10, detalle[12], fceldageneral)

                    # Agrego el total por el objetivo
                    row_num += 1
                    ws.merge_range(row_num, 0, row_num, 1, "TOTAL PONDERACIÓN OBJETIVO ESPECÍFICO", fceldanegritaizq)
                    ws.write(row_num, 2, objetivo[3] / 100, fceldaporcentajepie)
                    ws.merge_range(row_num, 3, row_num, 10, "", fceldanegritaizq)

                # Agrego fila de ponderación total
                row_num += 1
                ws.merge_range(row_num, 0, row_num, 1, "PONDERACIÓN TOTAL", fceldanegritaizq)
                ws.write(row_num, 2, 1, fceldaporcentajepie)
                ws.merge_range(row_num, 3, row_num, 10, "", fceldanegritaizq)

                workbook.close()

                ruta = "media/proyectoinvestigacion/cronograma/" + nombrearchivo

                return JsonResponse({'result': 'ok', 'archivo': ruta})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al descargar el cronograma. Detalle: [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'descargaravancecronogramaindividual':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto el registro de avance
                avanceactividad = ProyectoInvestigacionAvanceActividad.objects.get(pk=int(encrypt(request.POST['id'])))
                proyecto = avanceactividad.proyecto

                caracteres_a_quitar = "!\"\#$%&()=?¡'¿{}[],.-+*/|°^~:;"

                # Aquí se almacenan los archivos de excel de los cronogramas
                directorio = SITE_STORAGE + '/media/proyectoinvestigacion/cronograma'
                try:
                    os.stat(directorio)
                except:
                    os.mkdir(directorio)

                # Carpeta donde se crearán los archivos de excel
                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'proyectoinvestigacion', 'cronograma'))

                # Creo el archivo de excel con el cronograma
                titulo = proyecto.titulo.upper()
                palabras = titulo.split(" ")
                titulo = "_".join(palabras[0:5])
                titulo = remover_caracteres(titulo, caracteres_a_quitar)

                titulo = elimina_tildes(remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(titulo)))
                nombrearchivo = "AVANCE_CRONOGRAMA_PROYECTO_" + titulo + ".xlsx"

                # Create un nuevo archivo de excel y le agrega una hoja
                workbook = xlsxwriter.Workbook(output_folder + '/' + nombrearchivo)
                ws = workbook.add_worksheet("Cronograma")

                fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])
                fceldageneral = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneral"])
                fceldageneralcent = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneralcent"])
                ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
                fceldafecha = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdafecha"])
                fceldamoneda = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamoneda"])
                ftextonegrita = workbook.add_format(FORMATOS_CELDAS_EXCEL["textonegrita"])
                fmoneda = workbook.add_format(FORMATOS_CELDAS_EXCEL["formatomoneda"])
                fceldanegritacent = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdanegritacent"])
                fceldanegritaizq = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdanegritaizq"])
                fceldamonedapie = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamonedapie"])
                fceldaporcentaje = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdaporcentaje"])
                fceldaporcentajepie = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdaporcentajepie"])

                ws.merge_range(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
                ws.merge_range(1, 0, 1, 10, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADO', ftitulo1)
                ws.merge_range(2, 0, 2, 10, 'FACULTAD DE INVESTIGACIÓN', ftitulo1)
                ws.merge_range(3, 0, 3, 10, f'AVANCE DE CRONOGRAMA DE PROYECTO DE INVESTIGACIÓN', ftitulo1)
                ws.merge_range(4, 0, 4, 10, f'{getmonthname(avanceactividad.inicio).upper()} {avanceactividad.inicio.year}', ftitulo1)
                ws.merge_range(6, 0, 6, 10, "Título: " + proyecto.titulo, ftextonegrita)
                ws.merge_range(7, 0, 7, 10, "Director: " + proyecto.profesor.persona.nombre_completo_inverso(), ftextonegrita)
                ws.merge_range(8, 0, 8, 1, f"Tiempo duración: {proyecto.tiempomes} meses", ftextonegrita)
                ws.merge_range(8, 3, 8, 4, f"Presupuesto Total: $ {proyecto.presupuesto:.2f}", ftextonegrita)
                ws.merge_range(9, 0, 9, 10, "Objetivo General: " + BeautifulSoup(proyecto.objetivogeneral, "lxml").text.strip(), ftextonegrita)
                ws.set_row_pixels(9, 30)

                columns = [
                    (u"N°", 4),
                    (u"ACTIVIDAD", 74),
                    (u"PONDERACIÓN (%)", 16),
                    (u"ESTADO AVANCE", 14),
                    (u"PORCENTAJE AVANCE", 14),
                    (u"FECHA INICIO", 14),
                    (u"FECHA FIN", 14),
                    (u"ENTREGABLE", 26),
                    (u"EVIDENCIA CONTROL INFORMES", 26),
                    (u"OBSERVACIONES", 26),
                    (u"RESPONSABLES ACTIVIDAD", 45)
                ]

                # Datos del cronograma de actividades
                listaobjetivos = []
                objetivos_cronograma = proyecto.cronograma_objetivo_totales()
                for objetivo in objetivos_cronograma:
                    # Id, descripcion, total actividades, total ponderacion
                    listaobjetivos.append([objetivo['id'], objetivo['descripcion'], objetivo['totalactividades'], objetivo['totalponderacion']])

                datoscronograma = []
                detalles_cronograma = avanceactividad.detalle_avance()
                auxid = 0
                secuencia = 0
                totalponderacion = 0
                for detalle in detalles_cronograma:
                    secuencia += 1
                    totalponderacion += detalle.actividad.ponderacion
                    if auxid != detalle.actividad.objetivo.id:
                        secuencia_grupo = 1
                        auxid = detalle.actividad.objetivo.id
                    else:
                        secuencia_grupo += 1

                    datoscronograma.append([
                        detalle.actividad.objetivo.id,
                        secuencia,
                        secuencia_grupo,
                        detalle.actividad.actividad,
                        detalle.actividad.ponderacion,
                        detalle.get_estadoactual_display().title(),
                        detalle.avanceactual,
                        detalle.actividad.fechainicio,
                        detalle.actividad.fechafin,
                        detalle.actividad.entregables(),
                        detalle.actividad.evidenciacontrolinforme,
                        detalle.actividad.observaciongeneral,
                        detalle.actividad.responsables().title()
                    ])

                row_num = 10
                # Llenar los detalles del cronograma
                for objetivo in listaobjetivos:
                    # Agrego el objetivo especifico
                    row_num += 1
                    ws.merge_range(row_num, 0, row_num, 10, "Objetivo Específico: " + objetivo[1], fceldanegritaizq)
                    row_num += 1

                    # Agrego las columnas
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                        ws.set_column(col_num, col_num, columns[col_num][1])

                    # Agrego los detalles de actividades por cada objetivo
                    for detalle in datoscronograma:
                        if objetivo[0] == detalle[0]:
                            row_num += 1
                            ws.write(row_num, 0, detalle[1], fceldageneral)
                            ws.write(row_num, 1, detalle[3], fceldageneral)
                            ws.write(row_num, 2, detalle[4] / 100, fceldaporcentaje)
                            ws.write(row_num, 3, detalle[5], fceldageneralcent)
                            ws.write(row_num, 4, detalle[6] / 100, fceldaporcentaje)
                            ws.write(row_num, 5, detalle[7], fceldafecha)
                            ws.write(row_num, 6, detalle[8], fceldafecha)
                            ws.write(row_num, 7, detalle[9], fceldageneral)
                            ws.write(row_num, 8, detalle[10], fceldageneral)
                            ws.write(row_num, 9, detalle[11], fceldageneral)
                            ws.write(row_num, 10, detalle[12], fceldageneral)

                    # Agrego el total por el objetivo
                    row_num += 1
                    ws.merge_range(row_num, 0, row_num, 1, "TOTAL PONDERACIÓN OBJETIVO ESPECÍFICO", fceldanegritaizq)
                    ws.write(row_num, 2, objetivo[3] / 100, fceldaporcentajepie)
                    ws.merge_range(row_num, 3, row_num, 10, "", fceldanegritaizq)

                # Agrego fila de ponderación total
                row_num += 1
                ws.merge_range(row_num, 0, row_num, 1, "PONDERACIÓN TOTAL", fceldanegritaizq)
                ws.write(row_num, 2, 1, fceldaporcentajepie)
                ws.merge_range(row_num, 3, row_num, 10, "", fceldanegritaizq)

                workbook.close()

                ruta = "media/proyectoinvestigacion/cronograma/" + nombrearchivo

                return JsonResponse({'result': 'ok', 'archivo': ruta})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al descargar el cronograma. Detalle: [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editmontopresupuesto':
            try:
                if not 'idproyecto' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                archivo = request.FILES['archivorespaldonmp']
                descripcionarchivo = 'Archivo Soporte Actualización'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idproyecto'])))
                archivo._name = generar_nombre("actpresupuesto", archivo._name)

                # Guardo el historial
                historialmontopresupuesto = ProyectoInvestigacionHistorialMontoPresupuesto(
                    proyecto=proyecto,
                    fechaant=proyecto.fechainicio,
                    montounemiant=proyecto.montounemi,
                    montootrafuenteant=proyecto.montootrafuente,
                    montototalant=proyecto.montototal,
                    fecha=datetime.strptime(request.POST['fechanmp'], '%d-%m-%Y').date(),
                    montounemi=request.POST['montouneminmp'],
                    montootrafuente=request.POST['otrafuentenmp'],
                    montototal=request.POST['montototalnmp'],
                    observacion=request.POST['observacionnmp'].strip(),
                    archivo=archivo
                )
                historialmontopresupuesto.save(request)

                # Actualizo el proyecto
                proyecto.montounemi = request.POST['montouneminmp']
                proyecto.montootrafuente = request.POST['otrafuentenmp']
                proyecto.montototal = request.POST['montototalnmp']
                proyecto.save(request)

                log(u'%s actualizó monto del presupuesto total del proyecto de investigación: %s' % (persona, proyecto), request, "edit")

                return JsonResponse({"result": "ok", "idp": request.POST['idproyecto']})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'addpermisoedicion':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                tiporegistro = 1 if request.POST['tiporeg'] == 'PRE' else 2
                tipopersona = request.POST['tipopersonaperm']
                inicio = datetime.strptime(request.POST['inicioperm'], '%Y-%m-%d').date()
                fin = datetime.strptime(request.POST['finperm'], '%Y-%m-%d').date()
                observacion = request.POST['observacionperm'].strip()
                archivo = request.FILES['archivoperm']

                # Validaciones
                if proyecto.proyectoinvestigacionpermisoedicion_set.values("id").filter(status=True, tiporegistro=tiporegistro, tipopersona=tipopersona, inicio=inicio, fin=fin, estado__in=[1, 2]).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El tipo de persona ya tiene un permiso asignado para las fechas solicitadas", "showSwal": "True", "swalType": "warning"})

                descripcionarchivo = 'Archivo de soporte'
                resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if fin <= inicio:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin debe ser mayor a la fecha de inicio", "showSwal": "True", "swalType": "warning"})

                newfile = request.FILES['archivoperm']
                newfile._name = generar_nombre("actrubropresupuesto", newfile._name)

                # Guardar el registro
                permisoedicion = ProyectoInvestigacionPermisoEdicion(
                    proyecto=proyecto,
                    tiporegistro=tiporegistro,
                    tipopersona=tipopersona,
                    inicio=inicio,
                    fin=fin,
                    observacion=observacion,
                    archivo=newfile,
                    estado=1
                )
                permisoedicion.save(request)

                if tiporegistro == 1:
                    # Guardar el historial del presupuesto
                    historialpresupuesto = ProyectoInvestigacionHistorialPresupuesto(
                        permiso=permisoedicion,
                        fecha=datetime.now().date(),
                        total=proyecto.presupuesto
                    )
                    historialpresupuesto.save(request)

                    # Guardar el historial de los rubros del presupuesto
                    for rubro in proyecto.proyectoinvestigacionitempresupuesto_set.filter(status=True).order_by('id'):
                        historialrubro = ProyectoInvestigacionItemPresupuestoHistorial(
                            historial=historialpresupuesto,
                            tiporecurso=rubro.tiporecurso,
                            recurso=rubro.recurso,
                            descripcion=rubro.descripcion,
                            unidadmedida=rubro.unidadmedida,
                            cantidad=rubro.cantidad,
                            valorunitario=rubro.valorunitario,
                            calculaiva=rubro.calculaiva,
                            valoriva=rubro.valoriva,
                            valortotal=rubro.valortotal,
                            cantidadorig=rubro.cantidadorig,
                            valorunitarioorig=rubro.valorunitarioorig,
                            valortotalorig=rubro.valortotalorig,
                            modificado=rubro.modificado,
                            valorneto=rubro.valorneto,
                            devengado=rubro.devengado,
                            saldo=rubro.saldo,
                            observacion=rubro.observacion
                        )
                        historialrubro.save(request)
                else:
                    # Guardar el historial del cronograma
                    historialcronograma = ProyectoInvestigacionHistorialCronograma(
                        permiso=permisoedicion,
                        fecha=datetime.now().date()
                    )
                    historialcronograma.save(request)

                    # Guardar el historial de los actividades del cronograma
                    for objetivo in proyecto.objetivos_especificos():
                        for actividad in objetivo.proyectoinvestigacioncronogramaactividad_set.filter(status=True).order_by('id'):
                            historialactividad = ProyectoInvestigacionCronogramaActividadHistorial(
                                historial=historialcronograma,
                                objetivo=actividad.objetivo,
                                actividad=actividad.actividad,
                                ponderacion=actividad.ponderacion,
                                fechainicio=actividad.fechainicio,
                                fechafin=actividad.fechafin,
                                entregable=actividad.entregable,
                                subirevidenciaretraso=actividad.subirevidenciaretraso,
                                porcentajeejecucion=actividad.porcentajeejecucion,
                                observacion=actividad.observacion,
                                observacioninv=actividad.observacioninv,
                                estado=actividad.estado
                            )
                            historialactividad.save(request)

                            # Guardar el historial de los responsables de la actividad
                            for responsable in actividad.proyectoinvestigacioncronogramaresponsable_set.filter(status=True).order_by('id'):
                                historialresponsable = ProyectoInvestigacionCronogramaResponsableHistorial(
                                    actividad=historialactividad,
                                    persona=responsable.persona
                                )
                                historialresponsable.save(request)


                # Si el tipo de persona es DIRECTOR DE PROYECTO, notificar por e-mail
                if int(tipopersona) == 1:
                    # Notificar por e-mail a director para que edite los rubros del presupuesto
                    listacuentascorreo = [29]  # investigacion@unemi.edu.ec
                    lista_email_envio = []
                    lista_email_cco = []

                    for integrante in proyecto.integrantes_proyecto():
                        lista_email_envio += integrante.persona.lista_emails_envio()
                        break

                    fechaenvio = datetime.now().date()
                    horaenvio = datetime.now().time()
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                    if tiporegistro == 1:
                        tituloemail = "Permiso habilitado para Edición de los Rubros del presupuesto del Proyecto de Investigación"
                        tiponotificacion = "HABEDIPRE"
                    else:
                        tituloemail = "Permiso habilitado para Edición del Cronograma del Proyecto de Investigación"
                        tiponotificacion = "HABEDICROPRORR"

                    lista_archivos_adjuntos = []
                    titulo = "Proyectos de Investigación"

                    send_html_mail(tituloemail,
                                   "emails/propuestaproyectoinvestigacion.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'tiponotificacion': tiponotificacion,
                                    'saludo': 'Estimada' if proyecto.profesor.persona.sexo_id == 1 else 'Estimado',
                                    'nombrepersona': proyecto.profesor.persona.nombre_completo_inverso(),
                                    'proyecto': proyecto
                                    },
                                   lista_email_envio,  # Destinatarioa
                                   lista_email_cco,  # Copia oculta
                                   lista_archivos_adjuntos,  # Adjunto(s)
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                log(f'{persona} agregó permiso para edición {"de rubros del presupuesto" if tiporegistro == 1 else "del cronograma de actividades"} del proyecto: {permisoedicion}', request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'finalizaredicionpresupuesto':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                permisoedicion = proyecto.permiso_edicion_vigente(1, 2)

                # Actualizar el permiso
                permisoedicion.finedi = datetime.now().date()
                permisoedicion.estado = 3
                permisoedicion.save(request)

                log(u'%s finalizó edición de los rubros del presupuesto %s' % (persona, permisoedicion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al actualizar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'subircontratoexterno':
            try:
                if not 'idproyecto' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivo = None

                if 'archivocontratoproyext' in request.FILES:
                    archivo = request.FILES['archivocontratoproyext']
                    descripcionarchivo = 'Archivo Contrato de Financiamiento'

                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    archivo._name = generar_nombre("contratofinanciamiento", archivo._name)

                tiporeg = request.POST['tiporegconext']
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idproyecto'])))
                resolucionaprobacion = proyecto.convocatoria.resolucion_aprobacion()[0]

                numerocontratoejecucion = request.POST['numerocontratoproyext'].strip()
                fechacontratoejecucion = datetime.strptime(request.POST['fechacontratoproyext'], '%d-%m-%Y').date()
                fechainicio = datetime.strptime(request.POST['inicioproyectoext'], '%d-%m-%Y').date()
                fechafinplaneado = datetime.strptime(request.POST['finproyectoext'], '%d-%m-%Y').date()

                if fechafinplaneado <= fechainicio:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin debe ser mayor a la fecha de inicio", "showSwal": "True", "swalType": "warning"})

                # Obtengo el estado APROBADO
                estado = obtener_estado_solicitud(3, 18)

                # Actualizo el proyecto
                proyecto.fechaaprobacion = resolucionaprobacion.fecha
                proyecto.aprobado = 1
                proyecto.resolucionaprobacion = resolucionaprobacion
                proyecto.estado = estado if tiporeg == 'N' else proyecto.estado
                proyecto.save(request)

                # Creo el recorrido del proyecto
                if tiporeg == 'N':
                    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                               fecha=datetime.now().date(),
                                                               observacion='PROYECTO APROBADO POR OCS',
                                                               estado=estado
                                                               )
                    recorrido.save(request)

                # Obtengo el estado EJECUCIÓN
                estado = obtener_estado_solicitud(3, 20)

                # Actualizo el proyecto
                proyecto.fechainicio = fechainicio
                proyecto.fechafinplaneado = fechafinplaneado
                proyecto.fechacontratoejecucion = fechacontratoejecucion
                proyecto.numerocontratoejecucion = numerocontratoejecucion

                if archivo:
                    proyecto.archivocontratoejecucion = archivo

                proyecto.ejecucion = 1
                proyecto.estado = estado if tiporeg == 'N' else proyecto.estado
                proyecto.save(request)

                # Creo el recorrido del proyecto
                if tiporeg == 'N':
                    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                               fecha=datetime.now().date(),
                                                               observacion='PROYECTO EN EJECUCIÓN',
                                                               estado=estado
                                                               )
                    recorrido.save(request)

                # Crea el historial del archivo
                historialarchivo = ProyectoInvestigacionHistorialArchivo(
                    proyecto=proyecto,
                    tipo=5,
                    archivo=proyecto.archivocontratoejecucion
                )
                historialarchivo.save(request)

                if tiporeg == 'N':
                    log(u'%s agregó contrato de financiamiento del proyecto de investigación: %s' % (persona, proyecto), request, "add")
                else:
                    log(u'%s actualizó contrato de financiamiento del proyecto de investigación: %s' % (persona, proyecto), request, "edit")

                return JsonResponse({"result": "ok", "idp": request.POST['idproyecto']})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'adddevengadorubro':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el rubro y proyecto
                rubro = ProyectoInvestigacionItemPresupuesto.objects.get(pk=int(encrypt(request.POST['id'])))
                proyecto = rubro.proyecto

                # Obtener los valores del formulario
                saldoant = Decimal(request.POST['saldo']).quantize(Decimal('.01'))
                fechacomprobante = datetime.strptime(request.POST['fechacomp'], '%Y-%m-%d').date()
                archivocomprobante = request.FILES['archivocomprobante']
                fechaactaentrega = datetime.strptime(request.POST['fechaacta'], '%Y-%m-%d').date()
                archivoactaentrega = request.FILES['archivoacta']
                valordevengar = Decimal(request.POST['valordevengar']).quantize(Decimal('.01'))
                saldo = Decimal(request.POST['saldoact']).quantize(Decimal('.01'))

                # Validaciones
                if valordevengar > rubro.saldo:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"No existe saldo suficiente en el rubro para devengar. Saldo actual <b>{rubro.saldo:.2f}</b>, valor a devengar <b>{valordevengar:.2f}</b>", "showSwal": "True", "swalType": "warning"})

                descripcionarchivo = 'Archivo del comprobante de venta'
                resp = validar_archivo(descripcionarchivo, archivocomprobante, ['pdf'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                descripcionarchivo = 'Archivo de la acta entrega-recepción'
                resp = validar_archivo(descripcionarchivo, archivoactaentrega, ['pdf'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                archivocomprobante._name = generar_nombre("comprobanteventa", archivocomprobante._name)
                archivoactaentrega._name = generar_nombre("actaentregarecep", archivoactaentrega._name)

                # Actualizo los valores del proyecto
                proyecto.devengado = proyecto.devengado + valordevengar
                proyecto.saldo = proyecto.saldo - valordevengar
                proyecto.save(request)

                proyecto.porcentajepresupejec = Decimal((proyecto.devengado * 100) / proyecto.presupuesto).quantize(Decimal('.01'))
                proyecto.save(request)

                # Actualizo los valores del rubro
                rubro.devengado = rubro.devengado + valordevengar
                rubro.saldo = rubro.saldo - valordevengar
                rubro.save(request)

                # Guardo el movimiento del rubro
                movimientorubro = ProyectoInvestigacionMovimientoItemPresupuesto(
                    itempresupuesto=rubro,
                    tipo=2,
                    fecha=datetime.now(),
                    fechacomprobante=fechacomprobante,
                    archivocomprobante=archivocomprobante,
                    fechaactaentrega=fechaactaentrega,
                    archivoactaentrega=archivoactaentrega,
                    saldoant=saldoant,
                    ingreso=0,
                    salida=valordevengar,
                    saldo=saldo,
                    observacion='DEVENGADO DEL RUBRO'
                )
                movimientorubro.save(request)

                log(u'%s agregó devengado al rubro: %s' % (persona, rubro), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'firmarinformeavance':
            try:
                if 'iddoc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                tipofirma = request.POST['tipofirma']
                archivofirma = request.FILES['archivofirma']
                clavefirma = request.POST['cfirma']
                descripcionarchivo = 'Archivo de la firma electrónica'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivofirma, ['P12', 'PFX'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto el informe
                informe = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['iddoc'])))
                proyecto = informe.proyecto

                # Obtengo el archivo del informe firmado previamente
                archivoinforme = informe.archivo
                rutapdfarchivo = SITE_STORAGE + archivoinforme.url

                if tipofirma == 'VAL':
                    textoabuscar = informe.nombre_firma_valida()
                    textofirma = 'Verificado por:'
                    ocurrencia = 1
                else:
                    textoabuscar = informe.nombre_firma_aprueba()
                    textofirma = 'Aprobado por:'
                    ocurrencia = 1

                vecesencontrado = 0
                # ocurrencia = 5

                # Obtener coordenadas para ubicar al firma dependiendo de donde se encuentra ubicado el nombre de la persona
                documento = fitz.open(rutapdfarchivo)
                # numpaginafirma = int(documento.page_count) - 1

                # Busca la página donde se encuentran ubicados los textos: Elaboraro por, Verificado por y Aprobado por
                words_dict = {}
                encontrado = False
                for page_number, page in enumerate(documento):
                    words = page.get_text("blocks")
                    words_dict[0] = words

                    for cadena in words_dict[0]:
                        linea = cadena[4].replace("\n", " ")
                        if linea:
                            linea = linea.strip()

                        if textofirma in linea:
                            numpaginafirma = page_number
                            encontrado = True
                            break

                    if encontrado:
                        break

                # Obtener coordenadas para ubicar al firma dependiendo de donde se encuentra ubicado el nombre de la persona
                saltolinea = False
                words_dict = {}
                for page_number, page in enumerate(documento):
                    if page_number == numpaginafirma:
                        words = page.get_text("blocks")
                        words_dict[0] = words
                        break

                valor = None
                for cadena in words_dict[0]:
                    linea = cadena[4].replace("\n", " ")
                    if linea:
                        linea = linea.strip()

                    if textoabuscar in linea:
                        valor = cadena

                        vecesencontrado += 1
                        if vecesencontrado == ocurrencia:
                            break

                if valor:
                    y = 5000 - int(valor[3]) - 4120
                else:
                    y = 0

                # x = 87  # izq
                # x = 230  # cent
                x = 350  # der

                # Si no existe el nombre de la persona en el documento
                if y == 0:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"No se encuentra el nombre del firmante en el documento", "showSwal": "True", "swalType": "warning"})

                # Obtener extensión y leer archivo de la firma
                extfirma = os.path.splitext(archivofirma.name)[1][1:]
                bytesfirma = archivofirma.read()

                # Firma del documento
                datau = JavaFirmaEc(
                    archivo_a_firmar=archivoinforme,
                    archivo_certificado=bytesfirma,
                    extension_certificado=extfirma,
                    password_certificado=clavefirma,
                    page=numpaginafirma,
                    reason='',
                    lx=x,
                    ly=y
                ).sign_and_get_content_bytes()

                generar_archivo_firmado = io.BytesIO()
                generar_archivo_firmado.write(datau)
                generar_archivo_firmado.seek(0)

                nombre = "informeavancefirmado" if informe.tipo == 1 else "informefinalfirmado"

                nombrearchivofirmado = generar_nombre(nombre, nombre + '.pdf')
                objarchivo = DjangoFile(generar_archivo_firmado, nombrearchivofirmado)

                informe.archivo = objarchivo

                if tipofirma == 'VAL':
                    informe.firmaverifica = True
                else:
                    informe.firmaaprueba = True
                    informe.estado = 10

                informe.save(request)

                # Si es firma del aprobador, actualizar el porcenteje de ejecución técnica
                if tipofirma == 'APR':
                    proyecto.porcentajeproyejec = informe.porcentajeejecucion
                    proyecto.save(request)

                log(u'%s firmó informe de proyecto de investigación : %s' % (persona, informe), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Documento firmado con éxito", "showSwal": True, "idi": encrypt(informe.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'registrarreprogramacion':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el proyecto de investigacion
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda registra re-programación
                if not proyecto.puede_registrar_reprogramacion():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede registrar la prórroga", "showSwal": "True", "swalType": "warning"})

                # Obtener los valores del formulario
                tiempomesreprogramacion = request.POST['tiempomesreprogramacion'].strip()
                inicioreprogramacion = datetime.strptime(request.POST['inicioreprogramacion'], '%Y-%m-%d').date()
                finreprogramacion = datetime.strptime(request.POST['finreprogramacion'], '%Y-%m-%d').date()
                archivoocsreprogramacion = request.FILES['archivoocsreprogramacion'] if 'archivoocsreprogramacion' in request.FILES else None
                observacionreprogramacion = request.POST['observacionreprogramacion'].strip()

                # Validaciones
                if inicioreprogramacion <= proyecto.fechafinplaneado:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"La fecha de inicio de re-programación debe ser mayor a {proyecto.fechafinplaneado.strftime('%d-%m-%Y')}", "showSwal": "True", "swalType": "warning"})

                if finreprogramacion <= inicioreprogramacion:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de re-programación debe ser mayor a la fecha de inicio de re-programación", "showSwal": "True", "swalType": "warning"})

                if archivoocsreprogramacion:
                    descripcionarchivo = 'Archivo de Resolución OCS'
                    resp = validar_archivo(descripcionarchivo, archivoocsreprogramacion, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Actualizar el proyecto
                proyecto.fechafinreal = finreprogramacion
                proyecto.reprogramacion = True
                proyecto.tiempomesreprogramacion = tiempomesreprogramacion
                proyecto.inicioreprogramacion = inicioreprogramacion
                proyecto.finreprogramacion = finreprogramacion
                proyecto.observacionreprog = observacionreprogramacion

                if archivoocsreprogramacion:
                    newfile = archivoocsreprogramacion
                    newfile._name = generar_nombre("resolocsreprog", newfile._name)
                    proyecto.resolucionreprogramacionocs = newfile

                proyecto.save(request)

                log(f'{persona} registró re-programación a proyecto de investigación {proyecto}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True, "id": encrypt(proyecto.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'registrarprorroga':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el proyecto de investigacion
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda registra prorroga
                if not proyecto.puede_registrar_prorroga():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede registrar la prórroga", "showSwal": "True", "swalType": "warning"})

                # Obtener los valores del formulario
                tiempomesprorroga = request.POST['tiempomesprorroga'].strip()
                inicioprorroga = datetime.strptime(request.POST['inicioprorroga'], '%Y-%m-%d').date()
                finprorroga = datetime.strptime(request.POST['finprorroga'], '%Y-%m-%d').date()
                archivoocsprorroga = request.FILES['archivoocsprorroga'] if 'archivoocsprorroga' in request.FILES else None
                observacionprorroga = request.POST['observacionprorroga'].strip()
                iniciopermiso = datetime.strptime(request.POST['iniciopermiso'], '%Y-%m-%d').date() if 'iniciopermiso' in request.POST else None
                finpermiso = datetime.strptime(request.POST['finpermiso'], '%Y-%m-%d').date() if 'finpermiso' in request.POST else None

                # Validaciones
                if inicioprorroga <= proyecto.fechafinplaneado:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"La fecha de inicio de prórroga debe ser mayor a {proyecto.fechafinplaneado.strftime('%d-%m-%Y')}", "showSwal": "True", "swalType": "warning"})

                if finprorroga <= inicioprorroga:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de prórroga debe ser mayor a la fecha de inicio de prórroga", "showSwal": "True", "swalType": "warning"})

                if iniciopermiso:
                    if finpermiso < iniciopermiso:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de permiso debe ser mayor o igual a la fecha de inicio de permiso", "showSwal": "True", "swalType": "warning"})

                if archivoocsprorroga:
                    descripcionarchivo = 'Archivo de Resolución OCS'
                    resp = validar_archivo(descripcionarchivo, archivoocsprorroga, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Actualizar el proyecto
                proyecto.fechafinreal = finprorroga
                proyecto.prorroga = True
                proyecto.tiempomesprorroga = tiempomesprorroga
                proyecto.inicioprorroga = inicioprorroga
                proyecto.finprorroga = finprorroga
                proyecto.observacionprorr = observacionprorroga

                if archivoocsprorroga:
                    newfile = archivoocsprorroga
                    newfile._name = generar_nombre("resolocsprorroga", newfile._name)
                    proyecto.resolucionprorrogaocs = newfile

                proyecto.save(request)

                # Si es convocatoria mayor o igual a 2022 guardar permiso e historial
                if proyecto.convocatoria.apertura.year >= 2022:
                    if archivoocsprorroga:
                        newfile = archivoocsprorroga
                        newfile._name = generar_nombre("actcronograma", newfile._name)

                    permisovigente = proyecto.permiso_edicion_vigente(2, 1)
                    if not permisovigente:
                        # Guardar el registro permiso para edición del cronograma de actividades
                        permisoedicion = ProyectoInvestigacionPermisoEdicion(
                            proyecto=proyecto,
                            tiporegistro=2,
                            tipopersona=1,
                            inicio=iniciopermiso,
                            fin=finpermiso,
                            observacion=observacionprorroga,
                            archivo=newfile,
                            estado=1
                        )
                    else:
                        permisoedicion.inicio = iniciopermiso
                        permisoedicion.fin = finpermiso
                        permisoedicion.observacion = observacionprorroga
                        if archivoocsprorroga:
                            permisoedicion.archivo = newfile

                    permisoedicion.save(request)

                    # Si no existe permiso vigente entonces creo el historial del cronograma
                    if not permisovigente:
                        # Guardar el historial del cronograma
                        historialcronograma = ProyectoInvestigacionHistorialCronograma(
                            permiso=permisoedicion,
                            fecha=datetime.now().date()
                        )
                        historialcronograma.save(request)

                        # Guardar el historial de los actividades del cronograma
                        for objetivo in proyecto.objetivos_especificos():
                            for actividad in objetivo.proyectoinvestigacioncronogramaactividad_set.filter(status=True).order_by('id'):
                                historialactividad = ProyectoInvestigacionCronogramaActividadHistorial(
                                    historial=historialcronograma,
                                    objetivo=actividad.objetivo,
                                    actividad=actividad.actividad,
                                    ponderacion=actividad.ponderacion,
                                    fechainicio=actividad.fechainicio,
                                    fechafin=actividad.fechafin,
                                    entregable=actividad.entregable,
                                    subirevidenciaretraso=actividad.subirevidenciaretraso,
                                    porcentajeejecucion=actividad.porcentajeejecucion,
                                    observacion=actividad.observacion,
                                    observacioninv=actividad.observacioninv,
                                    estado=actividad.estado
                                )
                                historialactividad.save(request)

                                # Guardar el historial de los responsables de la actividad
                                for responsable in actividad.proyectoinvestigacioncronogramaresponsable_set.filter(status=True).order_by('id'):
                                    historialresponsable = ProyectoInvestigacionCronogramaResponsableHistorial(
                                        actividad=historialactividad,
                                        persona=responsable.persona
                                    )
                                    historialresponsable.save(request)

                        # Notificar por e-mail a director para que edite el cronograma de actividades
                        listacuentascorreo = [29]  # investigacion@unemi.edu.ec
                        lista_email_envio = []
                        lista_email_cco = []

                        for integrante in proyecto.integrantes_proyecto():
                            lista_email_envio += integrante.persona.lista_emails_envio()
                            break

                        fechaenvio = datetime.now().date()
                        horaenvio = datetime.now().time()
                        cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                        tituloemail = "Permiso habilitado para Edición del Cronograma del Proyecto de Investigación"
                        tiponotificacion = "HABEDICROPRORR"

                        lista_archivos_adjuntos = []
                        titulo = "Proyectos de Investigación"

                        send_html_mail(tituloemail,
                                       "emails/propuestaproyectoinvestigacion.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'titulo': titulo,
                                        'fecha': fechaenvio,
                                        'hora': horaenvio,
                                        'tiponotificacion': tiponotificacion,
                                        'saludo': 'Estimada' if proyecto.profesor.persona.sexo_id == 1 else 'Estimado',
                                        'nombrepersona': proyecto.profesor.persona.nombre_completo_inverso(),
                                        'proyecto': proyecto
                                        },
                                       lista_email_envio,  # Destinatarioa
                                       lista_email_cco,  # Copia oculta
                                       lista_archivos_adjuntos,  # Adjunto(s)
                                       cuenta=CUENTAS_CORREOS[cuenta][1]
                                       )

                log(f'{persona} registró prórroga a proyecto de investigación {proyecto}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True, "id": encrypt(proyecto.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'finalizarproyecto':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el proyecto de investigacion
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda finalizar
                if not proyecto.puede_finalizar():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede finalizar el proyecto", "showSwal": "True", "swalType": "warning"})

                # Obtener los valores del formulario
                ejecuciontecnica = Decimal(request.POST['ejecuciontecnica']).quantize(Decimal('.01'))
                numeroinforme = request.POST['numeroinforme']
                fechainforme = datetime.strptime(request.POST['fechainforme'], '%Y-%m-%d').date()
                montounemi = Decimal(request.POST['montounemi']).quantize(Decimal('.01'))
                otrafuente = Decimal(request.POST['otrafuente']).quantize(Decimal('.01'))
                totalfinanciamiento = Decimal(request.POST['totalfinanciamiento']).quantize(Decimal('.01'))
                montoejecutado = Decimal(request.POST['montoejecutado']).quantize(Decimal('.01'))
                ejecucionfinanciera = Decimal(request.POST['ejecucionfinanciera']).quantize(Decimal('.01'))
                fechafinalizacion = datetime.strptime(request.POST['fechafinalizacion'], '%Y-%m-%d').date()
                archivoinformefinal = request.FILES['archivoinformefinal'] if 'archivoinformefinal' in request.FILES else None

                # Validaciones
                if not proyecto.prorroga:
                    if fechafinalizacion < proyecto.fechafinplaneado:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"La fecha de finalización debe ser mayor o igual a {proyecto.fechafinplaneado.strftime('%d-%m-%Y')}", "showSwal": "True", "swalType": "warning"})
                else:
                    if fechafinalizacion < proyecto.fechafinreal:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"La fecha de finalización debe ser mayor o igual a {proyecto.fechafinreal.strftime('%d-%m-%Y')}", "showSwal": "True", "swalType": "warning"})

                if archivoinformefinal:
                    descripcionarchivo = 'Archivo del Informe Final'
                    resp = validar_archivo(descripcionarchivo, archivoinformefinal, ['pdf'], variable_valor("TAMANIO_INFORME_FINAL"))
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Obtener estado FINALIZADO
                estado = obtener_estado_solicitud(3, 21)

                # Actualizar el proyecto
                proyecto.montototal = totalfinanciamiento
                proyecto.montounemi = montounemi
                proyecto.montootrafuente = otrafuente
                proyecto.presupuesto = totalfinanciamiento
                proyecto.devengado = montoejecutado
                proyecto.saldo = totalfinanciamiento - montoejecutado
                proyecto.porcentajepresupejec = ejecucionfinanciera
                proyecto.porcentajeproyejec = ejecuciontecnica
                proyecto.fechafinreal = fechafinalizacion
                proyecto.ejecucion = 2
                proyecto.estado = estado

                if archivoinformefinal:
                    newfile = archivoinformefinal
                    newfile._name = generar_nombre("informefinal", newfile._name)
                    proyecto.archivoinformefinal = newfile

                proyecto.save(request)

                # Guardar el recorrido
                recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                           fecha=datetime.now().date(),
                                                           observacion=estado.observacion,
                                                           estado=estado
                                                           )
                recorrido.save(request)

                # Guardar o actualizar informe final
                if archivoinformefinal:
                    newfile = archivoinformefinal
                    newfile._name = generar_nombre("informefinalfirmado", newfile._name)

                informefinal = proyecto.informe_final()
                if not informefinal:
                    informefinal = ProyectoInvestigacionInforme(
                        proyecto=proyecto,
                        tipo=2,
                        fecha=fechainforme,
                        numero=numeroinforme,
                        fechafinproyecto=fechafinalizacion,
                        montoejecutado=montoejecutado,
                        porcentajepresup=ejecucionfinanciera,
                        archivo=newfile,
                        avanceesperado=100,
                        porcentajeejecucion=ejecuciontecnica,
                        firmaelabora=True,
                        observacionaprobacion='INFORME FINAL DE PROYECTO DE LA CONVOCATORIA 2020',
                        estado=10
                    )
                else:
                    informefinal.fecha = fechainforme
                    informefinal.numero = numeroinforme
                    informefinal.fechafinproyecto = fechafinalizacion
                    informefinal.montoejecutado = montoejecutado
                    informefinal.porcentajepresup = ejecucionfinanciera
                    informefinal.porcentajeejecucion = ejecuciontecnica

                    if archivoinformefinal:
                        informefinal.archivo = newfile

                informefinal.save(request)

                log(f'{persona} asignó estado finalizado a proyecto de investigación {proyecto}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True, "id": encrypt(proyecto.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'cerrarproyecto':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el proyecto de investigacion
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda finalizar
                if not proyecto.puede_cerrar():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede cerrar el proyecto", "showSwal": "True", "swalType": "warning"})

                # Obtener los valores del formulario
                fechacierre = datetime.strptime(request.POST['fechacierre'], '%Y-%m-%d').date()
                numeroresolucioncierreocs = request.POST['numeroresolucioncierreocs'].strip()
                archivoresolucioncga = request.FILES['archivoresolucioncga'] if 'archivoresolucioncga' in request.FILES else None
                archivoresolucionocs = request.FILES['archivoresolucionocs'] if 'archivoresolucionocs' in request.FILES else None

                # Validaciones
                if fechacierre <= proyecto.fechafinreal:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"La fecha de cierre debe ser mayor a {proyecto.fechafinreal.strftime('%d-%m-%Y')}", "showSwal": "True", "swalType": "warning"})

                if archivoresolucioncga:
                    descripcionarchivo = 'Archivo de Resolución CGA'
                    resp = validar_archivo(descripcionarchivo, archivoresolucioncga, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if archivoresolucionocs:
                    descripcionarchivo = 'Archivo de Resolución OCS'
                    resp = validar_archivo(descripcionarchivo, archivoresolucionocs, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Obtener estado CERRADO
                estado = obtener_estado_solicitud(3, 26)

                # Actualizar el proyecto
                proyecto.numeroresolucioncierreocs = numeroresolucioncierreocs
                proyecto.cerrado = 1
                proyecto.fechacierre = fechacierre
                proyecto.estado = estado

                if archivoresolucioncga:
                    newfile = archivoresolucioncga
                    newfile._name = generar_nombre("resolucioncierrecga", newfile._name)
                    proyecto.resolucioncierrecga = newfile

                if archivoresolucionocs:
                    newfile = archivoresolucionocs
                    newfile._name = generar_nombre("resolucioncierreocs", newfile._name)
                    proyecto.resolucioncierreocs = newfile

                proyecto.save(request)

                # Guardar el recorrido
                if not proyecto.estado.valor == 26:
                    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                               fecha=datetime.now().date(),
                                                               observacion=estado.observacion,
                                                               estado=estado
                                                               )
                    recorrido.save(request)

                log(f'{persona} asignó estado cerrado a proyecto de investigación {proyecto}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True, "id": encrypt(proyecto.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'validarinformefirmado':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['id'])))

                estado = int(request.POST['estado'])
                observacion = request.POST['observacion'].strip() if 'observacion' in request.POST else ''

                informeproyecto.observacionvalidacion = observacion
                informeproyecto.fechavalidacion = datetime.now()
                informeproyecto.estado = estado
                informeproyecto.save(request)

                # Si valida se debe cambiar el estado del proyecto a FINALIZADO
                if estado == 10:
                    proyectoinvestigacion = informeproyecto.proyecto

                    # Obtengo el estado FINALIZADO
                    estadoproyecto = obtener_estado_solicitud(3, 21)

                    # Actualizo el proyecto
                    proyectoinvestigacion.fechafinreal = informeproyecto.fechafinproyecto
                    proyectoinvestigacion.ejecucion = 2

                    # Si es convocatoria 2022 debo actualizar campos de presupuesto ejecutado
                    if proyectoinvestigacion.convocatoria.apertura.year == 2022:
                        proyectoinvestigacion.devengado = informeproyecto.montoejecutado
                        proyectoinvestigacion.saldo = proyectoinvestigacion.presupuesto - informeproyecto.montoejecutado
                        proyectoinvestigacion.porcentajepresupejec = informeproyecto.porcentajepresup

                    proyectoinvestigacion.estado = estadoproyecto
                    proyectoinvestigacion.save(request)

                    # Creo el recorrido del proyecto
                    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                               fecha=datetime.now().date(),
                                                               observacion='PROYECTO FINALIZADO',
                                                               estado=estadoproyecto
                                                               )
                    recorrido.save(request)

                    log(f'{persona} finalizó proyecto de investigación {proyectoinvestigacion}', request, "edit")

                # Envio de e-mail de notificacion al solicitante
                listacuentascorreo = [29]  # investigacion@unemi.edu.ec

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                lista_email_envio = []

                for integrante in informeproyecto.proyecto.integrantes_proyecto():
                    lista_email_envio += integrante.persona.lista_emails_envio()
                    break

                lista_email_cco = []

                if estado == 10:
                    tituloemail = "Informe Final de Proyecto de Investigación con Firmas Validado"
                    tiponotificacion = "VALIDAINFORME"
                else:
                    tituloemail = "Novedades Informe Final de Proyecto de Investigación con Firmas"
                    tiponotificacion = "NOVEDADINFORMEVAL"

                lista_archivos_adjuntos = []
                titulo = "Proyectos de Investigación"

                send_html_mail(tituloemail,
                               "emails/propuestaproyectoinvestigacion.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'numeroinforme': informeproyecto.numero,
                                'tipoinforme': 'informe final',
                                'tituloproyecto': informeproyecto.proyecto.titulo,
                                'observaciones': observacion
                                },
                               lista_email_envio,  # Destinatarioa
                               lista_email_cco,  # Copia oculta
                               lista_archivos_adjuntos,  # Adjunto(s)
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(f'{persona} {"validó el" if estado == 10 else "asignó novedades al"} informe final firmado de proyecto de investigación {informeproyecto}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'agregarexclusion':
            try:
                if not 'persona_select2' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                persona_id = request.POST['persona_select2']
                convocatoria_id = request.POST['convocatoria']
                observacion = request.POST['observacion'].strip()
                archivo = request.FILES['archivosoporte']

                # Validaciones
                if ProyectoInvestigacionExclusionValidacion.objects.values("id").filter(status=True, persona_id=persona_id, convocatoria_id=convocatoria_id).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La persona ya ha sido agregada anteriormente a la lista de exclusiones", "showSwal": "True", "swalType": "warning"})

                descripcionarchivo = 'Archivo de Soporte'
                resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                archivo._name = generar_nombre("soporteexclusion", archivo._name)

                # Guardar el registro
                exclusionvalidacion = ProyectoInvestigacionExclusionValidacion(
                    convocatoria_id=convocatoria_id,
                    persona_id=persona_id,
                    observacion=observacion,
                    archivo=archivo
                )
                exclusionvalidacion.save(request)

                log(f'{persona} agregó exclusión de validación para participación en proyectos de investigación {exclusionvalidacion}', request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'registrarevaluadorpropuesta':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el proyecto de investigacion
                proyectoinvestigacion = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Obtener los valores del formulario
                idregei1 = request.POST['idregei1']
                evaluadorinterno1 = request.POST['profesorei1_select2']
                notificarei1 = 'notificarei1' in request.POST
                idregei2 = request.POST['idregei2']
                evaluadorinterno2 = request.POST['profesorei2_select2']
                notificarei2 = 'notificarei2' in request.POST
                idregee1 = request.POST['idregee1']
                evaluadorexterno1 = request.POST['profesoree1_select2']
                notificaree1 = 'notificaree1' in request.POST
                idregee2 = request.POST['idregee2']
                evaluadorexterno2 = request.POST['profesoree2_select2']
                notificaree2 = 'notificaree2' in request.POST

                codigos_profesores = [evaluadorinterno1, evaluadorinterno2]
                codigos_externos = [evaluadorexterno1, evaluadorexterno2]

                # Validar que los evaluadores no estén repetidos
                repetido = elemento_repetido_lista(codigos_profesores)
                if repetido:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"Existen evaluadores repetidos en el detalle de Evaluadores Internos", "showSwal": "True", "swalType": "warning"})

                repetido = elemento_repetido_lista(codigos_externos)
                if repetido:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"Existen evaluadores repetidos en el detalle de Evaluadores Externos", "showSwal": "True", "swalType": "warning"})

                # Verificar que no sean integrantes del proyecto
                if proyectoinvestigacion.proyectoinvestigacionintegrante_set.filter(status=True, profesor_id__in=codigos_profesores).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"Los evaluadores internos no deben ser integrantes del proyecto", "showSwal": "True", "swalType": "warning"})

                if proyectoinvestigacion.proyectoinvestigacionintegrante_set.filter(status=True, externo_id__in=codigos_externos).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"Los evaluadores externos no deben ser integrantes del proyecto", "showSwal": "True", "swalType": "warning"})

                registro_nuevo = not proyectoinvestigacion.tiene_asignado_evaluadores_propuesta_proyecto()
                lista_evaluadores = []

                if registro_nuevo:
                    # Guardar evaluadores internos y extenos
                    personaevaluador = Profesor.objects.get(pk=int(evaluadorinterno1)).persona

                    # Guardo evaluador
                    evaluadorinterno = ProyectoInvestigacionEvaluador(
                        proyecto=proyectoinvestigacion,
                        tipo=1,
                        persona=personaevaluador,
                        tipoproyecto=1,
                        notificado=notificarei1,
                        reevaluacion=False
                    )
                    evaluadorinterno.save(request)

                    if notificarei1:
                        # Para enviar el e-mail al evaluador
                        evaluador = {
                            "nombre": personaevaluador.nombre_completo_inverso(),
                            "saludo": 'Estimada' if personaevaluador.sexo_id == 1 else 'Estimado',
                            "direccionemail": personaevaluador.lista_emails_envio(),
                            "inicioeval": proyectoinvestigacion.convocatoria.inicioevalint,
                            "fineval": proyectoinvestigacion.convocatoria.finevalint,
                            "tipo": "EVALUADOR INTERNO"
                        }
                        lista_evaluadores.append(evaluador)

                    personaevaluador = Profesor.objects.get(pk=int(evaluadorinterno2)).persona

                    # Guardo evaluador
                    evaluadorinterno = ProyectoInvestigacionEvaluador(
                        proyecto=proyectoinvestigacion,
                        tipo=1,
                        persona=personaevaluador,
                        tipoproyecto=1,
                        notificado=notificarei2,
                        reevaluacion=False
                    )
                    evaluadorinterno.save(request)

                    if notificarei2:
                        # Para enviar el e-mail al evaluador
                        evaluador = {
                            "nombre": personaevaluador.nombre_completo_inverso(),
                            "saludo": 'Estimada' if personaevaluador.sexo_id == 1 else 'Estimado',
                            "direccionemail": personaevaluador.lista_emails_envio(),
                            "inicioeval": proyectoinvestigacion.convocatoria.inicioevalint,
                            "fineval": proyectoinvestigacion.convocatoria.finevalint,
                            "tipo": "EVALUADOR INTERNO"
                        }
                        lista_evaluadores.append(evaluador)

                    personaevaluador = Externo.objects.get(pk=int(evaluadorexterno1)).persona

                    # Guardo evaluador
                    evaluadorexterno = ProyectoInvestigacionEvaluador(
                        proyecto=proyectoinvestigacion,
                        tipo=2,
                        persona=personaevaluador,
                        tipoproyecto=1,
                        notificado=notificaree1,
                        reevaluacion=False
                    )
                    evaluadorexterno.save(request)

                    if notificaree1:
                        # Para enviar el e-mail al evaluador
                        evaluador = {
                            "nombre": personaevaluador.nombre_completo_inverso(),
                            "saludo": 'Estimada' if personaevaluador.sexo_id == 1 else 'Estimado',
                            "direccionemail": personaevaluador.lista_emails_envio(),
                            "inicioeval": proyectoinvestigacion.convocatoria.inicioevalint,
                            "fineval": proyectoinvestigacion.convocatoria.finevalint,
                            "tipo": "EVALUADOR EXTERNO"
                        }
                        lista_evaluadores.append(evaluador)

                    personaevaluador = Externo.objects.get(pk=int(evaluadorexterno2)).persona

                    # Guardo evaluador
                    evaluadorexterno = ProyectoInvestigacionEvaluador(
                        proyecto=proyectoinvestigacion,
                        tipo=2,
                        persona=personaevaluador,
                        tipoproyecto=1,
                        notificado=notificaree2,
                        reevaluacion=False
                    )
                    evaluadorexterno.save(request)

                    if notificaree2:
                        # Para enviar el e-mail al evaluador
                        evaluador = {
                            "nombre": personaevaluador.nombre_completo_inverso(),
                            "saludo": 'Estimada' if personaevaluador.sexo_id == 1 else 'Estimado',
                            "direccionemail": personaevaluador.lista_emails_envio(),
                            "inicioeval": proyectoinvestigacion.convocatoria.inicioevalint,
                            "fineval": proyectoinvestigacion.convocatoria.finevalint,
                            "tipo": "EVALUADOR EXTERNO"
                        }
                        lista_evaluadores.append(evaluador)

                    # Actualizo el estado del proyecto a EVALUADORES ASIGNADOS
                    mensaje = "Registro guardado con éxito"
                    estado = obtener_estado_solicitud(3, 6)
                    proyectoinvestigacion.estado = estado
                    proyectoinvestigacion.save(request)

                    # Creo el recorrido del proyecto
                    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                               fecha=datetime.now().date(),
                                                               observacion=estado.observacion,
                                                               estado=estado
                                                               )
                    recorrido.save(request)

                    log(f'{persona} agregó evaluadores al proyecto de investigación: {proyectoinvestigacion}', request, "add")
                else:
                    # Actualizar evaluadores internos y extenos
                    personaevaluador = Profesor.objects.get(pk=int(evaluadorinterno1)).persona
                    evaluadorinterno = ProyectoInvestigacionEvaluador.objects.get(pk=idregei1)

                    # Actualizo evaluador
                    evaluadorinterno.persona = personaevaluador
                    evaluadorinterno.notificado = notificarei1
                    evaluadorinterno.save(request)

                    if notificarei1:
                        # Para enviar el e-mail al evaluador
                        evaluador = {
                            "nombre": personaevaluador.nombre_completo_inverso(),
                            "saludo": 'Estimada' if personaevaluador.sexo_id == 1 else 'Estimado',
                            "direccionemail": personaevaluador.lista_emails_envio(),
                            "inicioeval": proyectoinvestigacion.convocatoria.inicioevalint,
                            "fineval": proyectoinvestigacion.convocatoria.finevalint,
                            "tipo": "EVALUADOR INTERNO"
                        }
                        lista_evaluadores.append(evaluador)

                    personaevaluador = Profesor.objects.get(pk=int(evaluadorinterno2)).persona
                    evaluadorinterno = ProyectoInvestigacionEvaluador.objects.get(pk=idregei2)

                    # Actualizo evaluador
                    evaluadorinterno.persona = personaevaluador
                    evaluadorinterno.notificado = notificarei2
                    evaluadorinterno.save(request)

                    if notificarei2:
                        # Para enviar el e-mail al evaluador
                        evaluador = {
                            "nombre": personaevaluador.nombre_completo_inverso(),
                            "saludo": 'Estimada' if personaevaluador.sexo_id == 1 else 'Estimado',
                            "direccionemail": personaevaluador.lista_emails_envio(),
                            "inicioeval": proyectoinvestigacion.convocatoria.inicioevalint,
                            "fineval": proyectoinvestigacion.convocatoria.finevalint,
                            "tipo": "EVALUADOR INTERNO"
                        }
                        lista_evaluadores.append(evaluador)

                    personaevaluador = Externo.objects.get(pk=int(evaluadorexterno1)).persona
                    evaluadorexterno = ProyectoInvestigacionEvaluador.objects.get(pk=idregee1)

                    # Actualizo evaluador
                    evaluadorexterno.persona = personaevaluador
                    evaluadorexterno.notificado = notificaree1
                    evaluadorexterno.save(request)

                    if notificaree1:
                        # Para enviar el e-mail al evaluador
                        evaluador = {
                            "nombre": personaevaluador.nombre_completo_inverso(),
                            "saludo": 'Estimada' if personaevaluador.sexo_id == 1 else 'Estimado',
                            "direccionemail": personaevaluador.lista_emails_envio(),
                            "inicioeval": proyectoinvestigacion.convocatoria.inicioevalint,
                            "fineval": proyectoinvestigacion.convocatoria.finevalint,
                            "tipo": "EVALUADOR EXTERNO"
                        }
                        lista_evaluadores.append(evaluador)

                    personaevaluador = Externo.objects.get(pk=int(evaluadorexterno2)).persona
                    evaluadorexterno = ProyectoInvestigacionEvaluador.objects.get(pk=idregee2)

                    # Actualizo evaluador
                    evaluadorexterno.persona = personaevaluador
                    evaluadorexterno.notificado = notificaree2
                    evaluadorexterno.save(request)

                    if notificaree2:
                        # Para enviar el e-mail al evaluador
                        evaluador = {
                            "nombre": personaevaluador.nombre_completo_inverso(),
                            "saludo": 'Estimada' if personaevaluador.sexo_id == 1 else 'Estimado',
                            "direccionemail": personaevaluador.lista_emails_envio(),
                            "inicioeval": proyectoinvestigacion.convocatoria.inicioevalint,
                            "fineval": proyectoinvestigacion.convocatoria.finevalint,
                            "tipo": "EVALUADOR EXTERNO"
                        }
                        lista_evaluadores.append(evaluador)

                    mensaje = "Registro actualizado con éxito"
                    log(f'{persona} editó evaluadores del proyecto de investigación: {proyectoinvestigacion}', request, "edit")

                # Notificar por e-mail
                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                for evaluador in lista_evaluadores:
                    lista_email_envio = evaluador['direccionemail']

                    tituloemail = "Designación Evaluador de Propuesta de Proyecto de Investigación"
                    tiponotificacion = "EVALPROPASIG"

                    lista_archivos_adjuntos = []
                    lista_email_cco = []
                    titulo = "Proyectos de Investigación"

                    send_html_mail(tituloemail,
                                   "emails/propuestaproyectoinvestigacion.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'tiponotificacion': tiponotificacion,
                                    'saludo': evaluador['saludo'],
                                    'nombrepersona': evaluador['nombre'],
                                    'proyecto': proyectoinvestigacion,
                                    'tipoevaluador': evaluador['tipo'],
                                    'inicioeval': evaluador['inicioeval'],
                                    'fineval': evaluador['fineval']
                                    },
                                   lista_email_envio,  # Destinatarioa
                                   lista_email_cco,  # Copia oculta
                                   lista_archivos_adjuntos,  # Adjunto(s)
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": mensaje, "showSwal": True, "id": encrypt(proyectoinvestigacion.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'accionpost':
            try:
                pass
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                # return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        # return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Solicitud incorrecta.", "showSwal": "True", "swalType": "error"})
        # Fin POST
    else:
        # Inicio GET
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'firmarinforme':
                try:
                    # data['form2'] = FirmaElectronicaIndividualForm()
                    # # informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['id'])))
                    # data['id'] = request.GET.get('id')
                    # data['revision'] = request.GET.get('revision', None)
                    # data['modal'] = request.GET.get('modal', None)
                    # data['url'] = request.GET.get('url', None)
                    # template = get_template("proyectovinculaciondocente/modal/firmardocumentoauto.html")
                    # return JsonResponse({"result": "ok", 'data': template.render(data)})

                    informe = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.GET['id'])))
                    archivo = informe.archivogenerado.url
                    data['archivo'] = archivo
                    data['url_archivo'] = '{}{}'.format(dominio_sistema, archivo)
                    data['id_objeto'] = informe.id
                    data['action_firma'] = 'firmarinforme'
                    template = get_template("formfirmaelectronica.html")
                    return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'addconvocatoria':
                try:
                    data['title'] = u'Agregar Convocatoria a proyectos de investigación'
                    form = ConvocatoriaProyectoForm()
                    data['form'] = form
                    data['tiposproyecto'] = TIPO_PROYECTO
                    data['programasinvestigacion'] = ProgramasInvestigacion.objects.filter(status=True).order_by('nombre')
                    data['tiposrecursos'] = TipoRecursoPresupuesto.objects.filter(status=True, vigente=True).order_by('orden')
                    data['categorias'] = Categoria.objects.filter(status=True, vigente=True, tipo=1).order_by('numero')
                    data['tiposporcentaje'] = TIPO_PORCENTAJE_EQUIPOS
                    return render(request, "adm_proyectoinvestigacion/addconvocatoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'editconvocatoria':
                try:
                    data['title'] = u'Editar Convocatoria a proyectos de investigación'
                    convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.GET['idc'])))

                    form = ConvocatoriaProyectoForm(initial={'descripcion': convocatoria.descripcion,
                                                             'apertura': convocatoria.apertura,
                                                             'cierre': convocatoria.cierre,
                                                             'minimoaprobacion': convocatoria.minimoaprobacion,
                                                             'inicioevalint': convocatoria.inicioevalint,
                                                             'finevalint': convocatoria.finevalint,
                                                             'inicioreevalint': convocatoria.inicioreevalint,
                                                             'finreevalint': convocatoria.finreevalint,
                                                             'inicioevalext': convocatoria.inicioevalext,
                                                             'finevalext': convocatoria.finevalext,
                                                             'inicioreevalext': convocatoria.inicioreevalext,
                                                             'finreevalext': convocatoria.finreevalext,
                                                             'inicioselapro': convocatoria.inicioselapro,
                                                             'finselapro': convocatoria.finselapro,
                                                             'periodocidad': convocatoria.periodocidad,
                                                             'minintegranteu': convocatoria.minintegranteu,
                                                             'maxintegranteu': convocatoria.maxintegranteu,
                                                             'minintegrantee': convocatoria.minintegrantee,
                                                             'maxintegrantee': convocatoria.maxintegrantee})

                    data['form'] = form
                    data['id'] = request.GET['idc']
                    data['montosfinanciamiento'] = convocatoria.convocatoriamontofinanciamiento_set.filter(status=True).order_by('id')
                    data['programasconvocatoria'] = convocatoria.convocatoriaprogramainvestigacion_set.filter(status=True).order_by('id')
                    data['tiposrecursos'] = convocatoria.tipos_recursos_presupuesto()
                    data['totalproyectos'] = convocatoria.total_proyectos()
                    data['tiposproyecto'] = TIPO_PROYECTO
                    data['tiposporcentaje'] = TIPO_PORCENTAJE_EQUIPOS
                    data['programasinvestigacion'] = ProgramasInvestigacion.objects.filter(status=True).order_by('nombre')
                    return render(request, "adm_proyectoinvestigacion/editconvocatoria.html", data)
                except Exception as ex:
                    pass

            # elif action == 'addrubrica':
            #     try:
            #         convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.GET['idc'])))
            #         data['title'] = u'Agregar Rúbrica de Evaluación de Propuesta de Proyectos de Investigación'
            #         form = RubricaEvaluacionForm()
            #         data['form'] = form
            #         data['idc'] = request.GET['idc']
            #         return render(request, "adm_proyectoinvestigacion/addrubrica.html", data)
            #     except Exception as ex:
            #         pass

            elif action == 'addcriterioevaluacion':
                try:
                    data['title'] = u'Agregar Criterio de Evaluación'
                    data['convocatoria'] = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.GET['idc'])))
                    template = get_template("adm_proyectoinvestigacion/modal/addcriterioevaluacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            # elif action == 'editrubrica':
            #     try:
            #         rubricaevaluacion = RubricaEvaluacion.objects.get(pk=int(encrypt(request.GET['id'])))
            #         convocatoria = rubricaevaluacion.convocatoria
            #         data['title'] = u'Editar Rúbrica de Evaluación de Propuesta de Proyectos de Investigación'
            #
            #         form = RubricaEvaluacionForm(initial={
            #             'categoria': rubricaevaluacion.categoria,
            #             'numero': rubricaevaluacion.numero,
            #             'descripcion': rubricaevaluacion.descripcion,
            #             'valoracion': rubricaevaluacion.valoracion
            #         })
            #
            #         data['form'] = form
            #         data['id'] = request.GET['id']
            #         data['idc'] = request.GET['idc']
            #         data['itemsrubrica'] = items = rubricaevaluacion.items_rubrica()
            #         data['totalitems'] = items.count()
            #         data['enuso'] = rubricaevaluacion.en_uso()
            #         return render(request, "adm_proyectoinvestigacion/editrubrica.html", data)
            #     except Exception as ex:
            #         pass
            #
            elif action == 'editcriterioevaluacion':
                try:
                    data['title'] = u'Editar Criterio de Evaluación'
                    data['criterio'] = RubricaEvaluacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("adm_proyectoinvestigacion/modal/editcriterioevaluacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addresolucion':
                try:
                    data['convocatoria'] = convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.GET['idc'])))
                    data['title'] = u'Agregar Resolucíón de Aprobación de proyectos (Convocatoria: ' + convocatoria.descripcion + ')'
                    form = ResolucionAprobacionProyectoForm()
                    data['form'] = form
                    return render(request, "adm_proyectoinvestigacion/addresolucion.html", data)
                except Exception as ex:
                    pass

            elif action == 'editresolucion':
                try:
                    data['convocatoria'] = convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.GET['idc'])))
                    data['title'] = u'Editar Resolucíón de Aprobación de proyectos (Convocatoria: ' + convocatoria.descripcion + ')'
                    resolucion = ConvocatoriaResolucionAprobacionProyecto.objects.get(convocatoria=convocatoria, status=True)
                    data['resolucion'] = resolucion
                    form = ResolucionAprobacionProyectoForm(initial={
                        'fecha': resolucion.fecha,
                        'numero': resolucion.numero,
                        'resuelve': resolucion.resuelve,
                        'fechanotificaaprobacion': resolucion.fechanotificaaprobacion
                    })
                    data['form'] = form
                    return render(request, "adm_proyectoinvestigacion/editresolucion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpropuestaproyectoexterno':
                try:
                    convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.GET['idc'])))
                    data['title'] = f'Agregar Propuesta de Proyecto de Investigación {"En Conjunto" if convocatoria.tipo == 2 else "Externa"}'
                    institucionunemi = TituloInstitucion.objects.get(pk=1)
                    representante = DistributivoPersona.objects.get(denominacionpuesto_id=113, status=True)
                    institucionconvenio = convocatoria.institucion

                    form = RegistroPropuestaProyectoInvestigacionExternoForm(initial={
                        'convocatoria': convocatoria.descripcion,
                        'especificaconvenio': convocatoria.detalle,
                        'nombreinsejec': institucionunemi.nombre,
                        'representanteinsejec': representante.persona.nombre_completo(),
                        'cedulainsejec': representante.persona.cedula,
                        'telefonoinsejec': institucionunemi.telefono,
                        'faxinsejec': '',
                        'emailinsejec': representante.persona.emailinst,
                        'direccioninsejec': institucionunemi.direccion,
                        'paginawebinsejec': institucionunemi.web,
                        'nombreinsejec2': institucionconvenio.nombre,
                        'representanteinsejec2': institucionconvenio.representante,
                        'cedulainsejec2': institucionconvenio.cedula,
                        'telefonoinsejec2': institucionconvenio.telefono,
                        'faxinsejec2': institucionconvenio.fax,
                        'emailinsejec2': institucionconvenio.email,
                        'direccioninsejec2': institucionconvenio.direccion,
                        'paginawebinsejec2': institucionconvenio.paginaweb
                    })

                    data['convocatoria'] = convocatoria
                    form.cargarcategoria(convocatoria)
                    form.cargarprogramas(convocatoria)
                    data['form'] = form
                    return render(request, "adm_proyectoinvestigacion/addproyectoexterno.html", data)
                except Exception as ex:
                    pass

            elif action == 'editpropuestaproyectoexterno':
                try:
                    data['title'] = u'Editar Propuesta de Proyecto de Investigación Externa'

                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    institucionesejecutoras = ProyectoInvestigacionInstitucion.objects.filter(proyecto=proyecto, tipo=1, status=True).order_by('id')
                    iejecutora1 = institucionesejecutoras[0]
                    iejecutora2 = institucionesejecutoras[1]

                    existecoejecutora = 1 if ProyectoInvestigacionInstitucion.objects.filter(proyecto=proyecto, tipo=2).exists() else 2
                    form = RegistroPropuestaProyectoInvestigacionExternoForm(initial={
                        'categoria': proyecto.categoria2,
                        'codigo': proyecto.codigo,
                        'titulo': proyecto.titulo,
                        'convocatoria': proyecto.convocatoria.descripcion,
                        'areaconocimiento': proyecto.areaconocimiento,
                        'subareaconocimiento': proyecto.subareaconocimiento,
                        'subareaespecificaconocimiento': proyecto.subareaespecificaconocimiento,
                        'lineainvestigacion': proyecto.lineainvestigacion,
                        'sublineainvestigacion': proyecto.sublineainvestigacion.all(),
                        'programainvestigacion': proyecto.programainvestigacion,
                        'grupoinvestigacion': proyecto.grupoinvestigacion,
                        'industriapriorizada': proyecto.industriapriorizada,
                        'requiereconvenio': proyecto.requiereconvenio,
                        'especificaconvenio': proyecto.especificaconvenio,
                        'requierepermiso': proyecto.requierepermiso,
                        'especificapermiso': proyecto.especificapermiso,
                        'tiempomes': proyecto.tiempomes,
                        'montototal': proyecto.montototal,
                        'montounemi': proyecto.montounemi,
                        'montootrafuente': proyecto.montootrafuente,
                        'tipocobertura': proyecto.tipocobertura,
                        'zonas': proyecto.zonas.all(),
                        'provincia': proyecto.provincia,
                        'provincias': proyecto.provincias.all(),
                        'canton': proyecto.canton.all(),
                        'requiereparroquia': proyecto.requiereparroquia,
                        'parroquia': proyecto.parroquia,
                        'representanteinsejec': iejecutora1.representante,
                        'cedulainsejec': iejecutora1.cedula,
                        'telefonoinsejec': iejecutora1.telefono,
                        'faxinsejec': iejecutora1.fax,
                        'emailinsejec': iejecutora1.email,
                        'direccioninsejec': iejecutora1.direccion,
                        'paginawebinsejec': iejecutora1.paginaweb,
                        'nombreinsejec': iejecutora1.nombre,
                        'representanteinsejec2': iejecutora2.representante,
                        'cedulainsejec2': iejecutora2.cedula,
                        'telefonoinsejec2': iejecutora2.telefono,
                        'faxinsejec2': iejecutora2.fax,
                        'emailinsejec2': iejecutora2.email,
                        'direccioninsejec2': iejecutora2.direccion,
                        'paginawebinsejec2': iejecutora2.paginaweb,
                        'nombreinsejec2': iejecutora2.nombre,
                        'existeinscoejecutora': existecoejecutora
                    })

                    data['id'] = request.GET['id']
                    presupequip = False
                    # Si contempla compra de equipos
                    if proyecto.compraequipo != 3:
                        # Verificar si existen items de Equipos asignados en el presupuesto
                        presupequip = proyecto.presupuesto_asignado_equipos()

                    data['proyecto'] = proyecto
                    data['compraequipo'] = proyecto.compraequipo
                    data['inscoejecutoras'] = inscoejecutoras = proyecto.instituciones_proyecto().exclude(tipo=1)
                    data['totalinscoejec'] = len(inscoejecutoras)
                    data['convocatoria'] = proyecto.convocatoria
                    data['presupequip'] = presupequip
                    data['ocultarguardar'] = proyecto.estado.valor not in [1, 4, 15, 16, 28, 29, 38, 39, 40, 41]
                    data['parroquia'] = proyecto.parroquia
                    form.editar(proyecto)
                    data['form'] = form

                    return render(request, "adm_proyectoinvestigacion/editproyectoexterno.html", data)
                except Exception as ex:
                    pass

            elif action == 'integrantesproyecto':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Integrantes del Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    convocatoria = proyecto.convocatoria
                    integrantes = ProyectoInvestigacionIntegrante.objects.filter(status=True, proyecto=proyecto).order_by('funcion', 'persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    paging = MiPaginador(integrantes, 25)
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
                    data['tipoconvocatoria'] = convocatoria.tipo
                    data['integrantes'] = page.object_list
                    data['estadoproyecto'] = proyecto.estado.valor
                    data['puedeeditar'] = True # proyecto.estado.valor in [1, 4, 15, 16, 28, 29, 38, 39, 41, 41]
                    data['minimou'] = convocatoria.minintegranteu
                    data['maximou'] = maximou = convocatoria.maxintegranteu
                    data['minimoe'] = convocatoria.minintegrantee
                    data['maximoe'] = maximoe = convocatoria.maxintegrantee
                    data['registradosu'] = registradosu = integrantes.filter(funcion__in=[1, 2, 3], tipo__in=[1, 2, 3]).count()
                    data['registradose'] = registradose = integrantes.filter(funcion__in=[1, 2, 5], tipo=4).count()
                    data['mostrarboton'] = x = (registradosu + registradose) < (maximou + maximoe)
                    data['tituloconvocatoria'] = convocatoria.descripcion

                    return render(request, "adm_proyectoinvestigacion/integranteproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'addintegranteproyecto':
                try:
                    data['title'] = u'Agregar Integrante a Proyecto de Investigación'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    convocatoria = proyecto.convocatoria
                    data['proyecto'] = proyecto
                    data['tipopersona'] = TIPO_INTEGRANTE
                    data['tipoconvocatoria'] = convocatoria.tipo

                    if convocatoria.tipo == 1:
                        data['funcionpersona'] = ((2, u'CO-DIRECTOR'),
                                                 (3, u'INVESTIGADOR ASOCIADO'),
                                                 (4, u'AYUDANTE DE INVESTIGACIÓN'),
                                                 (5, u'INVESTIGADOR COLABORADOR'))
                    else:
                        data['funcionpersona'] = ((1, u'DIRECTOR'),
                                                  (2, u'CO-DIRECTOR'),
                                                  (3, u'INVESTIGADOR ASOCIADO'),
                                                  (4, u'AYUDANTE DE INVESTIGACIÓN'),
                                                  (5, u'INVESTIGADOR COLABORADOR'))

                    data['mostrarbotonagrexterno'] = proyecto.cantidad_integrantes_externos() < convocatoria.maxintegrantee

                    template = get_template("adm_proyectoinvestigacion/addintegranteproyecto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addexterno':
                try:
                    data['title'] = u'Agregar Integrante Externo'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))

                    form = ExternoForm()
                    data['proyecto'] = proyecto
                    data['form'] = form
                    return render(request, "adm_proyectoinvestigacion/addpersonaexterna.html", data)
                except Exception as ex:
                    pass

            elif action == 'editrolintegrante':
                try:
                    data['title'] = u'Editar Rol del Integrante'
                    integrante = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.GET['idi'])))
                    data['tipopersona'] = integrante.get_tipo_display()
                    data['tipoper'] = integrante.tipo
                    data['funcionper'] = integrante.funcion
                    data['integranteid'] = integrante.id
                    data['integrante'] = integrante.persona

                    if integrante.proyecto.convocatoria.tipo == 1:
                        data['funcionpersona'] = ((2, u'CO-DIRECTOR'),
                                                 (3, u'INVESTIGADOR ASOCIADO'),
                                                 (4, u'AYUDANTE DE INVESTIGACIÓN'))
                    else:
                        if integrante.tipo == 4:
                            data['funcionpersona'] = ((1, u'DIRECTOR'),
                                                      (2, u'CO-DIRECTOR'),
                                                      (3, u'INVESTIGADOR ASOCIADO'),
                                                      (4, u'AYUDANTE DE INVESTIGACIÓN'),
                                                      (5, u'INVESTIGADOR COLABORADOR'))
                        else:
                            data['funcionpersona'] = ((2, u'CO-DIRECTOR'),
                                                      (3, u'INVESTIGADOR ASOCIADO'),
                                                      (4, u'AYUDANTE DE INVESTIGACIÓN'))


                    template = get_template("adm_proyectoinvestigacion/editrolintegrante.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editexterno':
                try:
                    data['title'] = u'Editar Datos Integrante Externo'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    integrante = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.GET['idi'])))
                    personaexterna = integrante.persona

                    form = ExternoForm(initial={'nombres': personaexterna.nombres,
                                                'apellido1': personaexterna.apellido1,
                                                'apellido2': personaexterna.apellido2,
                                                'cedula': personaexterna.cedula,
                                                'pasaporte': personaexterna.pasaporte,
                                                'nacimiento': personaexterna.nacimiento,
                                                'sexo': personaexterna.sexo,
                                                'nacionalidad': personaexterna.nacionalidad,
                                                'email': personaexterna.email,
                                                'telefono': personaexterna.telefono,
                                                'funcionproyecto': integrante.funcion,
                                                'institucionlabora': integrante.externo.institucionlabora,
                                                'cargodesempena': integrante.externo.cargodesempena})

                    data['proyecto'] = proyecto
                    data['integrante'] = integrante
                    data['form'] = form

                    return render(request, "adm_proyectoinvestigacion/editpersonaexterna.html", data)
                except Exception as ex:
                    pass

            elif action == 'contenidoproyectoexterno':
                try:
                    data['title'] = u'Contenido de Proyecto de Investigación'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))

                    form = ContenidoProyectoInvestigacionForm(initial={
                        'titulo': proyecto.titulo
                    })

                    data['objetivos'] = objetivos = proyecto.objetivos_especificos()
                    data['totalobjetivos'] = len(objetivos)
                    resultados = proyecto.resultados_compromisos()

                    data['resultados'] = resultados
                    data['totalresultados'] = len(resultados)
                    data['form'] = form
                    data['id'] = request.GET['id']
                    data['existeresumen'] = True if proyecto.resumenpropuesta else False
                    data['puedeeditar'] = True # proyecto.estado.valor in [1, 4, 15, 16, 28, 29, 38, 39, 40, 41]

                    data['tiporesultado'] = [{"id": 2, "descripcion": "RESULTADO"},
                                             {"id": 3, "descripcion": "PRODUCTO"}]
                    data['resumenpropuesta'] = proyecto.resumenpropuesta
                    data['formulacionproblema'] = proyecto.formulacionproblema
                    data['objetivogeneral'] = proyecto.objetivogeneral
                    data['justificacion'] = proyecto.justificacion
                    data['estadoarte'] = proyecto.estadoarte
                    data['metodologia'] = proyecto.metodologia

                    data['impactosocial'] = proyecto.impactosocial
                    data['impactocientifico'] = proyecto.impactocientifico
                    data['impactoeconomico'] = proyecto.impactoeconomico
                    data['impactopolitico'] = proyecto.impactopolitico
                    data['otroimpacto'] = proyecto.otroimpacto
                    data['convocatoria'] = proyecto.convocatoria

                    data['referencias'] = referencias = proyecto.referencias_bibliograficas()
                    data['totalreferencias'] = len(referencias)
                    return render(request, "adm_proyectoinvestigacion/contenidoproyectoexterno.html", data)
                except Exception as ex:
                    pass

            elif action == 'presupuesto':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Presupuesto del Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    convocatoria = proyecto.convocatoria

                    data['tituloconvocatoria'] = convocatoria.descripcion
                    data['recursosconvocatoria'] = convocatoria.tipos_recursos_presupuesto()

                    if proyecto.compraequipo:
                        regfin = ConvocatoriaMontoFinanciamiento.objects.filter(status=True, tipoequipamiento=proyecto.compraequipo)[0]
                    else:
                        regfin = ConvocatoriaMontoFinanciamiento.objects.filter(status=True, categoria=proyecto.categoria2)[0]

                    data['montominimoequipos'] = Decimal(proyecto.montounemi * (regfin.porcentajecompra) / 100).quantize(Decimal('.01'))
                    data['totalequipos'] = proyecto.totales_detalle_equipos()['totaldetalle']

                    if proyecto.convocatoria.tipo == 1:
                        data['permisoedicion'] = proyecto.permiso_edicion_vigente(1, 2)
                        data['puedeagregarperm'] = not proyecto.puede_editar_rubros_presupuesto(2) and not proyecto.puede_editar_rubros_presupuesto(1)
                        data['puedeeditar'] = proyecto.puede_editar_rubros_presupuesto(2)
                    else:
                        if proyecto.estado.valor == 3:
                            data['puedeeditar'] = True
                        elif proyecto.estado.valor == 20:
                            data['permisoedicion'] = proyecto.permiso_edicion_vigente(1, 2)
                            data['puedeagregarperm'] = not proyecto.puede_editar_rubros_presupuesto(2) and not proyecto.puede_editar_rubros_presupuesto(1)
                            data['puedeeditar'] = proyecto.puede_editar_rubros_presupuesto(2)

                    data['textoequipos'] = 'Máximo Compra Equipos:' if regfin.tipoporcentaje == 2 else 'Mínimo Compra Equipos:'
                    data['tipoporcentaje'] = regfin.tipoporcentaje

                    return render(request, "adm_proyectoinvestigacion/presupuesto.html", data)
                except Exception as ex:
                    pass

            elif action == 'adddetallepresupuesto':
                try:
                    data['title'] = u'Agregar Detalle al Presupuesto'
                    data['proyecto'] = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    data['tiporecurso'] = tiporecurso = TipoRecursoPresupuesto.objects.get(pk=int(encrypt(request.GET['idt'])))

                    # Si el tipo de recurso es MATERIALES, se arma una lista de lo existente en bodega más lo que han ingresado en proyectos
                    if tiporecurso.abreviatura == 'MAT':
                        lista_bodega = [producto.descripcion for producto in Producto.objects.filter(status=True).distinct().order_by('descripcion')]
                        lista_recurso_proyecto = [recurso.recurso for recurso in ProyectoInvestigacionItemPresupuesto.objects.filter(status=True, tiporecurso__abreviatura='MAT').distinct().order_by('recurso')]
                        materiales = list(dict.fromkeys(lista_bodega + lista_recurso_proyecto))
                        materiales.sort()
                        data['materiales'] = materiales

                    template = get_template("adm_proyectoinvestigacion/adddetallepresupuesto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editdetallepresupuesto':
                try:
                    data['title'] = u'Editar Detalle del Presupuesto'
                    data['detalle'] = detalle = ProyectoInvestigacionItemPresupuesto.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['estadoproyecto'] = detalle.proyecto.estado.valor
                    # Si el tipo de recurso es MATERIALES, se arma una lista de lo existente en bodega más lo que han ingresado en proyectos
                    if detalle.tiporecurso.abreviatura == 'MAT':
                        lista_bodega = [producto.descripcion for producto in Producto.objects.filter(status=True).distinct().order_by('descripcion')]
                        lista_recurso_proyecto = [recurso.recurso for recurso in ProyectoInvestigacionItemPresupuesto.objects.filter(status=True, tiporecurso__abreviatura='MAT').distinct().order_by('recurso')]
                        materiales = list(dict.fromkeys(lista_bodega + lista_recurso_proyecto))
                        materiales.sort()
                        data['materiales'] = materiales

                    template = get_template("adm_proyectoinvestigacion/editdetallepresupuesto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cronograma':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Cronograma del Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    convocatoria = proyecto.convocatoria
                    data['tituloconvocatoria'] = convocatoria.descripcion
                    data['recursosconvocatoria'] = convocatoria.tipos_recursos_presupuesto()

                    data['objetivos'] = proyecto.objetivos_especificos()
                    data['ponderacion'] = proyecto.total_ponderacion_actividades()
                    data['cumplimiento'] = proyecto.porcentajeproyejec if proyecto.fase_aprobacion_superada() else 0
                    data['porcumplir'] = 100 - proyecto.porcentajeproyejec if proyecto.fase_aprobacion_superada() else 0

                    data['puedeeditar'] = not proyecto.fase_aprobacion_superada()
                    data['puedeagregarperm'] = not proyecto.puede_editar_cronograma_actividades(2) and not proyecto.puede_editar_cronograma_actividades(1)
                    data['fecha'] = datetime.now().date()

                    return render(request, "adm_proyectoinvestigacion/cronograma.html", data)
                except Exception as ex:
                    pass

            elif action == 'addactividadcronograma':
                try:
                    data['title'] = u'Agregar Actividad al Cronograma'
                    data['proyecto'] = proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    data['objetivo'] = objetivo = ProyectoInvestigacionObjetivo.objects.get(pk=int(encrypt(request.GET['idobj'])))
                    data['integrantes'] = proyecto.integrantes_proyecto_informe()
                    data['fecha'] = datetime.now().date()
                    data['numobj'] = request.GET['numobj']

                    template = get_template("adm_proyectoinvestigacion/addactividadcronograma.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editactividadcronograma':
                try:
                    data['title'] = u'Editar Actividad del Cronograma'
                    data['actividad'] = actividad = ProyectoInvestigacionCronogramaActividad.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['integrantes'] = actividad.objetivo.proyecto.integrantes_proyecto_informe()
                    data['responsables'] = [responsable.persona.id for responsable in actividad.lista_responsables()]
                    data['numobj'] = request.GET['numobj']
                    template = get_template("adm_proyectoinvestigacion/editactividadcronograma.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addpermisoedicion':
                try:
                    data['title'] = f'Agregar Permiso para Edición del {"Presupuesto del Proyecto" if request.GET["tiporeg"] == "PRE" else "Cronograma de actividades"}'
                    data['idp'] = request.GET['idp']
                    data['tipopersona'] = TIPO_PERSONA_PERMISO_EDICION
                    data['tiporeg'] = request.GET['tiporeg']
                    template = get_template("adm_proyectoinvestigacion/addpermisoedicion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'asignarevaluador':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    data['title'] = u'Asignar Evaluadores a Propuestas de Proyecto de Investigación'
                    form = EvaluadorProyectoInvestigacionForm(initial={
                        'titulo': proyecto.titulo,
                        'inicioevalint': proyecto.convocatoria.inicioevalint,
                        'finevalint': proyecto.convocatoria.finevalint,
                        'inicioevalext': proyecto.convocatoria.inicioevalext,
                        'finevalext': proyecto.convocatoria.finevalext
                    })
                    data['form'] = form
                    data['proyecto'] = proyecto
                    data['evaluadoresinternos'] = evaluadores = proyecto.evaluadores_internos()
                    data['totalinternos'] = evaluadores.count()
                    data['evaluadoresexternos'] = evaluadores = proyecto.evaluadores_externos()
                    data['totalexternos'] = evaluadores.count()
                    # data['enuso'] = proyecto.tiene_evaluaciones()
                    data['einternascompletas'] = einternascompletas = proyecto.evaluaciones_internas_completas()
                    data['requiereotraeinterna'] = proyecto.requiere_evaluacion_interna_adicional()
                    data['eexternascompletas'] = eexternascompletas = proyecto.evaluaciones_externas_completas()
                    data['requiereotraeexterna'] = requiereotraeexterna = proyecto.requiere_evaluacion_externa_adicional()
                    data['evaluacionescompletas'] = einternascompletas and eexternascompletas
                    data['bancoevaluadoresinternos'] = Profesor.objects.filter(evaluadorproyecto__status=True, evaluadorproyecto__activo=True, evaluadorproyecto__propuestaproyecto=True, status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    data['bancoevaluadoresexternos'] = Externo.objects.filter(evaluadorproyecto__status=True, evaluadorproyecto__activo=True, evaluadorproyecto__propuestaproyecto=True, status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    # Si el estado el proyecto es EVALUACIÓN INTERNA o EXTERNA ADICIONAL
                    data['reevaluacionint'] = proyecto.estado.valor in [9, 34]
                    data['reevaluacionext'] = proyecto.estado.valor in [12, 35]

                    return render(request, "adm_proyectoinvestigacion/asignarevaluador.html", data)
                except Exception as ex:
                    pass

            elif action == 'propuestas':
                try:
                    id = request.GET.get('id', '')
                    convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.GET['idc'])))
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, convocatoria=convocatoria), f'&action={action}&idc={request.GET["idc"]}'
                    categoriaid, lineainvestigacionid, estadoid = int(request.GET.get('categoriaid', '0')), int(request.GET.get('lineainvestigacionid', '0')), int(request.GET.get('estadoid', '0'))

                    if id:
                        data['id'] = id
                        filtro = filtro & (Q(pk=int(encrypt(id))))
                        url_vars += f'&id={id}'

                    if search:
                        data['s'] = search
                        ss = search.split(" ")
                        if len(ss) == 1:
                            filtro = filtro & (Q(profesor__persona__nombres__icontains=search) |
                                               Q(profesor__persona__apellido1__icontains=search) |
                                               Q(profesor__persona__apellido2__icontains=search) |
                                               Q(titulo__icontains=search))
                        else:
                            filtro = filtro & (Q(profesor__persona__apellido1__contains=ss[0]) &
                                               Q(profesor__persona__apellido2__contains=ss[1])
                                               |Q(titulo__icontains=search))

                        url_vars += f'&s={search}'

                    data['categoriaid'] = categoriaid
                    if categoriaid:
                        filtro = filtro & Q(categoria2_id=categoriaid)
                        url_vars += f'&categoriaid={categoriaid}'

                    data['lineainvestigacionid'] = lineainvestigacionid
                    if lineainvestigacionid:
                        filtro = filtro & Q(lineainvestigacion_id=lineainvestigacionid)
                        url_vars += f'&lineainvestigacionid={lineainvestigacionid}'

                    data['estadoid'] = estadoid
                    if estadoid:
                        filtro = filtro & Q(estado__valor=estadoid)
                        url_vars += f'&estadoid={estadoid}'

                    proyectos = ProyectoInvestigacion.objects.filter(filtro).order_by('-id')

                    paging = MiPaginador(proyectos, 25)
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
                    data['proyectos'] = page.object_list
                    data['categorias'] = Categoria.objects.filter(status=True, proyectoinvestigacion__convocatoria=convocatoria, proyectoinvestigacion__status=True).distinct().order_by('descripcion')
                    data['lineasinvestigacion'] = LineaInvestigacion.objects.filter(status=True, proyectoinvestigacion__convocatoria=convocatoria, proyectoinvestigacion__status=True).distinct().order_by('nombre')
                    data['estados'] = obtener_estados_solicitud(3, [1, 2, 3, 4, 6, 13, 18, 20, 21, 26])

                    data['total'] = proyectos.count()
                    data['registrado'] = registrados = proyectos.values("id").filter(registrado=True).count()
                    data['edicion'] = proyectos.count() - registrados
                    data['verificado'] = proyectos.values("id").filter(registrado=True, verificado=1).count()
                    data['novedad'] = proyectos.values("id").filter(registrado=True, verificado=2).count()
                    data['aprobado'] = proyectos.values("id").filter(registrado=True, verificado=1, aprobado=1).count()
                    data['ejecucion'] = proyectos.values("id").filter(registrado=True, verificado=1, aprobado=1, ejecucion=1).count()
                    data['prorroga'] = proyectos.values("id").filter(registrado=True, verificado=1, aprobado=1, prorroga=True).count()
                    data['finalizado'] = proyectos.values("id").filter(registrado=True, verificado=1, aprobado=1, ejecucion=2).count()
                    data['cerrado'] = proyectos.values("id").filter(registrado=True, verificado=1, aprobado=1, ejecucion=2, cerrado=1).count()

                    data['title'] = u'Gestión y Seguimiento de Proyectos de Investigación'
                    data['convocatoria'] = convocatoria

                    return render(request, "adm_proyectoinvestigacion/propuestas.html", data)
                except Exception as ex:
                    pass

            elif action == 'exclusiones':
                try:
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                    convocatoriaid = int(request.GET.get('convocatoriaid', '0'))

                    if search:
                        data['s'] = search
                        ss = search.split(" ")
                        if len(ss) == 1:
                            filtro = filtro & (Q(persona__nombres__icontains=search) |
                                               Q(persona__apellido1__icontains=search) |
                                               Q(persona__apellido2__icontains=search))
                        else:
                            filtro = filtro & (Q(persona__apellido1__contains=ss[0]) &
                                               Q(persona__apellido2__contains=ss[1]))

                        url_vars += f'&s={search}'

                    data['convocatoriaid'] = convocatoriaid
                    if convocatoriaid:
                        filtro = filtro & Q(convocatoria_id=convocatoriaid)
                        url_vars += f'&convocatoriaid={convocatoriaid}'

                    exclusiones = ProyectoInvestigacionExclusionValidacion.objects.filter(filtro).order_by('-id')

                    paging = MiPaginador(exclusiones, 25)
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
                    data['exclusiones'] = page.object_list
                    data['convocatorias'] = ConvocatoriaProyecto.objects.filter(status=True, proyectoinvestigacionexclusionvalidacion__status=True).distinct().order_by('-apertura')
                    data['title'] = u'Exclusiones de Validación para Participación en Proyectos de Investigación'

                    return render(request, "adm_proyectoinvestigacion/exclusion.html", data)
                except Exception as ex:
                    pass

            elif action == 'participantes':
                try:
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, proyectoinvestigacionintegrante__proyecto__estado__valor__in=[20, 21, 26]), f'&action={action}'

                    if search:
                        data['s'] = search
                        ss = search.split(" ")
                        if len(ss) == 1:
                            filtro = filtro & (Q(nombres__icontains=search) |
                                               Q(apellido1__icontains=search) |
                                               Q(apellido2__icontains=search))
                        else:
                            filtro = filtro & (Q(apellido1__contains=ss[0]) &
                                               Q(apellido2__contains=ss[1]))

                        url_vars += f'&s={search}'

                    participantes = Persona.objects.filter(filtro).distinct().order_by('apellido1', 'apellido2', 'nombres')

                    paging = MiPaginador(participantes, 25)
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
                    data['participantes'] = page.object_list
                    data['title'] = u'Participantes de los Proyectos de Investigación'

                    return render(request, "adm_proyectoinvestigacion/participante.html", data)
                except Exception as ex:
                    pass

            elif action == 'mostrarproyectos':
                try:
                    data['title'] = u'Proyectos de Investigación del Participante'
                    data['participante'] = participante = Persona.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['proyectos'] = ProyectoInvestigacionIntegrante.objects.filter(status=True, persona=participante, proyecto__estado__valor__in=[20, 21, 26]).distinct().order_by('proyecto__convocatoria__apertura')
                    template = get_template("adm_proyectoinvestigacion/modal/participanteproyecto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'proformadetallepresupuesto':
                try:
                    data['title'] = u'Proformas del Rubro del Presupuesto'
                    data['detalle'] = detalle = ProyectoInvestigacionItemPresupuesto.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("adm_proyectoinvestigacion/modal/proformadetallepresupuesto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            elif action == 'propuestasold':
                try:
                    search = None
                    ids = None
                    tipobus = 1

                    convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.GET['idc'])))
                    estadosproyecto = obtener_estados_solicitud(3, [1, 2, 3, 4, 5, 13, 18, 19, 20])

                    if 'tipobus' in request.GET:
                        tipobus = int(request.GET['tipobus'])

                    if 'id' in request.GET:
                        ids = request.GET['id']
                        proyectos = ProyectoInvestigacion.objects.filter(convocatoria=convocatoria, status=True, pk=int(encrypt(request.GET['id'])))
                    elif 's' in request.GET:
                        search = request.GET['s']
                        if tipobus == 1:
                            proyectos = ProyectoInvestigacion.objects.filter(convocatoria=convocatoria, status=True, titulo__icontains=search).order_by('-id')
                        elif tipobus == 2:
                            if ' ' not in search:
                                proyectos = ProyectoInvestigacion.objects.filter(
                                    Q(proyectoinvestigacionintegrante__persona__nombres__icontains=search) |
                                    Q(proyectoinvestigacionintegrante__persona__apellido1__icontains=search) |
                                    Q(proyectoinvestigacionintegrante__persona__apellido2__icontains=search),
                                    convocatoria=convocatoria, status=True).distinct().order_by('-id')
                            else:
                                ss = search.split(" ")
                                proyectos = ProyectoInvestigacion.objects.filter(
                                    proyectoinvestigacionintegrante__persona__apellido1__contains=ss[0],
                                    proyectoinvestigacionintegrante__persona__apellido2__contains=ss[1],
                                    convocatoria=convocatoria, status=True).distinct().order_by('-id')
                        else:
                            # Filtrar por año del proyecto..falta eso en el filter >>
                            proyectos = ProyectoInvestigacion.objects.filter(convocatoria=convocatoria, status=True).order_by('-id')
                    else:
                        proyectos = ProyectoInvestigacion.objects.filter(convocatoria=convocatoria, status=True).order_by('-id')

                    estadoproyecto = 0
                    # Filtro por estado
                    if tipobus == 4:
                        estadoproyecto = int(request.GET['estadoproyecto']) if 'estadoproyecto' in request.GET else 0
                        if estadoproyecto > 0:
                            proyectos = proyectos.filter(estado_id=estadoproyecto)


                    paging = MiPaginador(proyectos, 25)
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
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['proyectos'] = page.object_list
                    data['tipobus'] = tipobus
                    data['estadoproyecto'] = estadoproyecto
                    data['estadosproyecto'] = estadosproyecto

                    data['total'] = proyectos.count()
                    data['registrado'] = registrados = proyectos.values("id").filter(registrado=True).count()
                    data['edicion'] = proyectos.count() - registrados
                    data['verificado'] = verificados = proyectos.values("id").filter(registrado=True, verificado=1).count()
                    data['novedad'] = novedades = proyectos.values("id").filter(registrado=True, verificado=2).count()
                    data['porverificar'] = registrados - (verificados + novedades)
                    data['aprobado'] = aprobados = proyectos.values("id").filter(registrado=True, verificado=1, aprobado=1).count()
                    data['descartado'] = descartados = proyectos.values("id").filter(registrado=True, verificado=1, aprobado=2).count()
                    data['poraprobar'] = verificados - (aprobados + descartados)
                    data['enejecucion'] = ejecucion = proyectos.values("id").filter(registrado=True, verificado=1, aprobado=1, ejecucion=1).count()
                    data['finalizado'] = finalizado = proyectos.values("id").filter(registrado=True, verificado=1, aprobado=1, ejecucion=2).count()
                    data['porejecutar'] = aprobados - (ejecucion + finalizado)
                    data['convocatoriaid'] = convocatoria.id
                    data['tipoconvocatoria'] = convocatoria.tipo
                    data['anioconvocatoria'] = convocatoria.apertura.year

                    data['title'] = u'Administración y Seguimiento de Proyectos de Investigación (Convocatoria: ' + convocatoria.descripcion + ')'
                    return render(request, "adm_proyectoinvestigacion/propuestasold.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'evaluadores':
                try:
                    search = None
                    ids = None

                    tipoevaluador = int(request.GET['tipoevaluador']) if 'tipoevaluador' in request.GET else 0
                    perfilevaluacion = int(request.GET['perfilevaluacion']) if 'perfilevaluacion' in request.GET else 0


                    if 'id' in request.GET:
                        ids = request.GET['id']
                        evaluadores = EvaluadorProyecto.objects.filter(pk=int(encrypt(request.GET['id'])))
                    elif 's' in request.GET:
                        search = request.GET['s']
                        if ' ' not in search:
                            evaluadores = EvaluadorProyecto.objects.filter(Q(persona__nombres__icontains=search) |
                                                                Q(persona__apellido1__icontains=search) |
                                                                Q(persona__apellido2__icontains=search),
                                                                status=True, activo=True)
                        else:
                            ss = search.split(" ")
                            evaluadores = EvaluadorProyecto.objects.filter(persona__apellido1__contains=ss[0],
                                                                 persona__apellido2__contains=ss[1],
                                                                 status=True, activo=True
                                                                 )
                    else:
                        evaluadores = EvaluadorProyecto.objects.filter(status=True, activo=True)


                    if tipoevaluador > 0:
                        evaluadores = evaluadores.filter(tipo=tipoevaluador)

                    if perfilevaluacion > 0:
                        if perfilevaluacion == 1:
                            evaluadores = evaluadores.filter(propuestaproyecto=True)
                        elif perfilevaluacion == 2:
                            evaluadores = evaluadores.filter(proyectofinalizado=True)
                        else:
                            evaluadores = evaluadores.filter(obrarelevancia=True)

                    evaluadores = evaluadores.order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    paging = MiPaginador(evaluadores, 25)
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
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['evaluadores'] = page.object_list
                    data['tipoevaluador'] = tipoevaluador
                    data['perfilevaluacion'] = perfilevaluacion
                    data['title'] = u'Evaluadores de Proyectos de Investigación y Obras de Relevancia'
                    return render(request, "adm_proyectoinvestigacion/evaluadores.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addevaluador':
                try:
                    data['title'] = u'Agregar Evaluador de Proyectos y Obras de Relevancia'
                    data['tipopersona'] = TIPO_EVALUADOR_PROYECTO

                    template = get_template("adm_proyectoinvestigacion/addevaluador.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editperfil':
                try:
                    data['title'] = u'Editar Perfil de Evaluación'
                    data['evaluador'] = EvaluadorProyecto.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("adm_proyectoinvestigacion/editperfilevaluacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addevaluadorexterno':
                try:
                    data['title'] = u'Agregar Evaluador Externo de Propuestas de Proyectos de Investigación y Obras de Relevancia'

                    form = EvaluadorExternoForm()

                    data['form'] = form
                    # data['titulos'] = Titulo.objects.filter(status=True, nivel__rango__in=[5, 6]).order_by('nombre')
                    # data['universidades'] = InstitucionEducacionSuperior.objects.filter(status=True).order_by('nombre')
                    # data['paises'] = Pais.objects.filter(status=True).order_by('nombre')
                    data['tiposautor'] = [{'id': 1, 'descripcion': 'AUTOR'}, {'id': 2, 'descripcion': 'COAUTOR'}]
                    data['funciones'] = [{'id': 1, 'descripcion': 'DIRECTOR'},
                                         {'id': 2, 'descripcion': 'CO-DIRECTOR'},
                                         {'id': 3, 'descripcion': 'INVESTIGADOR ASOCIADO'},
                                         {'id': 4, 'descripcion': 'ASISTENTE DE INVESTIGACIÓN'}]

                    return render(request, "adm_proyectoinvestigacion/addevaluadorexterno.html", data)
                except Exception as ex:
                    pass

            elif action == 'editevaluadorexterno':
                try:
                    data['title'] = u'Editar Evaluador Externo de Propuestas de Proyectos de Investigación'
                    evaluador = EvaluadorProyecto.objects.get(pk=int(encrypt(request.GET['id'])))
                    personaexterna = evaluador.persona

                    form = EvaluadorExternoForm(initial={'nombres': personaexterna.nombres,
                                                'apellido1': personaexterna.apellido1,
                                                'apellido2': personaexterna.apellido2,
                                                'cedula': personaexterna.cedula,
                                                'pasaporte': personaexterna.pasaporte,
                                                'identificadororcid': personaexterna.identificador_orcid(),
                                                'nacimiento': personaexterna.nacimiento,
                                                'sexo': personaexterna.sexo,
                                                'nacionalidad': personaexterna.nacionalidad,
                                                'email': personaexterna.email,
                                                'telefono': personaexterna.telefono,
                                                'institucionlabora': evaluador.externo.institucionlabora,
                                                'cargodesempena': evaluador.externo.cargodesempena,
                                                'propuestaproyecto': evaluador.propuestaproyecto,
                                                'obrarelevancia': evaluador.obrarelevancia})

                    data['personaexterna'] = personaexterna
                    data['evaluador'] = evaluador
                    data['form'] = form
                    # data['titulos'] = Titulo.objects.filter(status=True, nivel__rango__in=[5, 6]).order_by('nombre')
                    # data['universidades'] = InstitucionEducacionSuperior.objects.filter(status=True).order_by('nombre')
                    # data['paises'] = Pais.objects.filter(status=True).order_by('nombre')
                    data['tiposautor'] = [{'id': 1, 'descripcion': 'AUTOR'}, {'id': 2, 'descripcion': 'COAUTOR'}]
                    data['funciones'] = [{'id': 1, 'descripcion': 'DIRECTOR'},
                                         {'id': 2, 'descripcion': 'CO-DIRECTOR'},
                                         {'id': 3, 'descripcion': 'INVESTIGADOR ASOCIADO'},
                                         {'id': 4, 'descripcion': 'ASISTENTE DE INVESTIGACIÓN'}]

                    # data['formacionacademica'] = evaluador.formacion_academica()
                    # data['experiencias'] = evaluador.experiencia_laboral()
                    # data['articulos'] = evaluador.articulos_publicados_persona_externa()
                    # data['ponencias'] = evaluador.ponencias_publicadas_persona_externa()
                    # data['libros'] = evaluador.libros_publicados_persona_externa()
                    # data['capitulos'] = evaluador.capitulos_libro_publicados_persona_externa()
                    # data['proyectos'] = evaluador.proyectos_investigacion_persona_externa()

                    return render(request, "adm_proyectoinvestigacion/editevaluadorexterno.html", data)
                except Exception as ex:
                    pass

            elif action == 'delevaluador':
                try:
                    evaluador = EvaluadorProyecto.objects.get(pk=int(encrypt(request.GET['id'])))

                    # Elimino al evaluador
                    evaluador.status = False
                    evaluador.save(request)

                    log(u'Eliminó evaluador de proyectos de investigación [ %s ]' % (evaluador), request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

            elif action == 'inactivarevaluador':
                try:
                    evaluador = EvaluadorProyecto.objects.get(pk=int(encrypt(request.GET['id'])))

                    # Elimino al evaluador
                    evaluador.activo = False
                    evaluador.save(request)

                    log(u'Inactivó evaluador de proyectos de investigación [ %s ]' % (evaluador), request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

            elif action == 'criteriosevaluacion':
                try:
                    id = request.GET.get('id', '')
                    convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.GET['idc'])))
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, convocatoria=convocatoria), f'&action={action}&idc={request.GET["idc"]}'

                    if id:
                        data['id'] = id
                        filtro = filtro & (Q(pk=int(encrypt(id))))
                        url_vars += f'&id={id}'

                    if search:
                        data['s'] = search
                        filtro = filtro & (Q(categoria__icontains=search))
                        url_vars += f'&s={search}'

                    criterios = RubricaEvaluacion.objects.filter(filtro).order_by('numero')

                    paging = MiPaginador(criterios, 25)
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
                    data['criterios'] = page.object_list
                    data['title'] = u'Criterios de Evaluación para Propuestas de Proyectos'
                    data['convocatoria'] = convocatoria
                    data['totalvaloracion'] = convocatoria.total_valoracion_rubricas()
                    data['minimoaprobar'] = convocatoria.minimoaprobacion

                    return render(request, "adm_proyectoinvestigacion/criterioevaluacion.html", data)
                except Exception as ex:
                    pass
                    # return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addtitulo':
                try:
                    data['title'] = u'Agregar Título Universitario'
                    data['niveltitulacion'] = NivelTitulacion.objects.filter(status=True, rango__in=[4, 5, 6]).order_by('rango')
                    data['areasconocimiento'] = AreaConocimientoTitulacion.objects.filter(status=True, tipo=1).order_by('nombre')

                    template = get_template("pro_proyectoinvestigacion/addtitulo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'adduniversidad':
                try:
                    data['title'] = u'Agregar Institución Educación Superior'
                    data['paises'] = Pais.objects.filter(status=True).order_by('nombre')

                    template = get_template("pro_proyectoinvestigacion/adduniversidad.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscarprofesor':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        personas = Profesor.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                        | Q(persona__apellido2__icontains=s[0])
                                                        | Q(persona__cedula__icontains=s[0])
                                                        | Q(persona__ruc__icontains=s[0])
                                                        | Q(persona__pasaporte__icontains=s[0]),
                                                        status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        personas = Profesor.objects.filter(persona__apellido1__icontains=s[0],
                                                           persona__apellido2__icontains=s[1],
                                                           status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    # data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso()), "identificacion": x.persona.identificacion(), "idpersona": x.persona.id, "usuario": x.persona.usuario.username, "emailinst": x.persona.emailinst, "email": x.persona.email, "celular": x.persona.telefono, "telefono": x.persona.telefono_conv} for x in personas]}
                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso()), "identificacion": x.persona.identificacion(), "idpersona": x.persona.id, "usuario": x.persona.usuario.username if x.persona.usuario else '', "emailinst": x.persona.emailinst, "email": x.persona.email, "celular": x.persona.telefono, "telefono": x.persona.telefono_conv} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscarexterno':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        personas = Externo.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                      | Q(persona__apellido2__icontains=s[0])
                                                      | Q(persona__cedula__icontains=s[0])
                                                      | Q(persona__pasaporte__icontains=s[0])
                                                      | Q(persona__ruc__icontains=s[0]),
                                                      status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        personas = Externo.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                        & Q(persona__apellido2__icontains=s[1]),
                                                           status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    # data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso())} for x in personas]}
                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso()), "identificacion": x.persona.identificacion(), "idpersona": x.persona.id, "usuario": x.persona.usuario.username if x.persona.usuario else '', "emailinst": x.persona.emailinst, "email": x.persona.email, "celular": x.persona.telefono, "telefono": x.persona.telefono_conv} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscaralumno':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        personas = Inscripcion.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                      | Q(persona__apellido2__icontains=s[0])
                                                      | Q(persona__cedula__icontains=s[0])
                                                      | Q(persona__pasaporte__icontains=s[0])
                                                      | Q(persona__ruc__icontains=s[0]),
                                                      status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        personas = Inscripcion.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                               & Q(persona__apellido2__icontains=s[1]),
                                                           status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    personas = personas.filter(persona__perfilusuario__visible=True, persona__perfilusuario__status=True).exclude(coordinacion_id=9).distinct()

                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso()) + ' - ' + x.carrera.nombre} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscaradministrativo':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        personas = Administrativo.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                      | Q(persona__apellido2__icontains=s[0])
                                                      | Q(persona__cedula__icontains=s[0])
                                                      | Q(persona__pasaporte__icontains=s[0])
                                                      | Q(persona__ruc__icontains=s[0]),
                                                      status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        personas = Administrativo.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                               & Q(persona__apellido2__icontains=s[1]),
                                                           status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso())} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscarprofesorevaluador':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    tipo = request.GET.get('tipo', '')
                    filtro = Q(evaluadorproyecto__status=True) & Q(evaluadorproyecto__activo=True) & Q(status=True)

                    if len(s) == 1:
                        filtro = filtro & (Q(persona__apellido1__icontains=s[0])
                                | Q(persona__apellido2__icontains=s[0])
                                | Q(persona__cedula__icontains=s[0])
                                | Q(persona__ruc__icontains=s[0])
                                | Q(persona__pasaporte__icontains=s[0])
                                )
                    else:
                        filtro = filtro & (Q(persona__apellido1__icontains=s[0])
                               & Q(persona__apellido2__icontains=s[1])
                               )

                    if tipo == 'obra':
                        filtro = filtro & Q(evaluadorproyecto__obrarelevancia=True)
                    else:
                        filtro = filtro & Q(evaluadorproyecto__propuestaproyecto=True)

                    personas = Profesor.objects.filter(filtro).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso()), "identificacion": x.persona.identificacion(), "idpersona": x.persona.id, "usuario": x.persona.usuario.username if x.persona.usuario else '', "emailinst": x.persona.emailinst, "email": x.persona.email, "celular": x.persona.telefono, "telefono": x.persona.telefono_conv} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscarexternoevaluador':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    tipo = request.GET.get('tipo', '')
                    filtro = Q(evaluadorproyecto__status=True) & Q(evaluadorproyecto__activo=True) & Q(status=True)

                    if len(s) == 1:
                        filtro = filtro & (Q(persona__apellido1__icontains=s[0])
                                | Q(persona__apellido2__icontains=s[0])
                                | Q(persona__cedula__icontains=s[0])
                                | Q(persona__ruc__icontains=s[0])
                                | Q(persona__pasaporte__icontains=s[0])
                                )
                    else:
                        filtro = filtro & (Q(persona__apellido1__icontains=s[0])
                               & Q(persona__apellido2__icontains=s[1])
                               )

                    if tipo == 'obra':
                        filtro = filtro & Q(evaluadorproyecto__obrarelevancia=True)
                    else:
                        filtro = filtro & Q(evaluadorproyecto__propuestaproyecto=True)

                    personas = Externo.objects.filter(filtro).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso()), "identificacion": x.persona.identificacion(), "idpersona": x.persona.id, "usuario": x.persona.usuario.username if x.persona.usuario else '', "emailinst": x.persona.emailinst, "email": x.persona.email, "celular": x.persona.telefono, "telefono": x.persona.telefono_conv} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscarpersona':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        personas = Persona.objects.filter(Q(apellido1__icontains=s[0])
                                                        | Q(apellido2__icontains=s[0])
                                                        | Q(cedula__icontains=s[0])
                                                        | Q(ruc__icontains=s[0])
                                                        | Q(pasaporte__icontains=s[0]),
                                                        status=True).order_by('apellido1', 'apellido2', 'nombres')
                    else:
                        personas = Persona.objects.filter(apellido1__icontains=s[0],
                                                          apellido2__icontains=s[1],
                                                          status=True).order_by('apellido1', 'apellido2', 'nombres')

                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.nombre_completo_inverso()), "identificacion": x.identificacion()} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscarpersonalinvestigacion':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        personas = Persona.objects.filter(Q(apellido1__icontains=s[0])
                                                        | Q(apellido2__icontains=s[0])
                                                        | Q(cedula__icontains=s[0])
                                                        | Q(ruc__icontains=s[0])
                                                        | Q(pasaporte__icontains=s[0]),
                                                        status=True, distributivopersona__denominacionpuesto_id=variable_valor('ID_CARGO_TECNICO_INV')).order_by('apellido1', 'apellido2', 'nombres')
                    else:
                        personas = Persona.objects.filter(apellido1__icontains=s[0],
                                                          apellido2__icontains=s[1],
                                                          status=True, distributivopersona__denominacionpuesto_id=variable_valor('ID_CARGO_TECNICO_INV')).order_by('apellido1', 'apellido2', 'nombres')

                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.nombre_completo_inverso()), "identificacion": x.identificacion()} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscarprofesorinvitado':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        profesores = Profesor.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                        | Q(persona__apellido2__icontains=s[0])
                                                        | Q(persona__cedula__icontains=s[0])
                                                        | Q(persona__ruc__icontains=s[0])
                                                        | Q(persona__pasaporte__icontains=s[0]),
                                                        status=True, categoria_id=2).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        profesores = Profesor.objects.filter(persona__apellido1__icontains=s[0],
                                                           persona__apellido2__icontains=s[1],
                                                           status=True, categoria_id=2).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    listado = [{"id": pro.id,
                                "name": str(pro.persona.nombre_completo_inverso()),
                                "identificacion": pro.persona.identificacion(),
                                "idpersona": pro.persona.id,
                                "usuario": pro.persona.usuario.username if pro.persona.usuario else '',
                                "emailinst": pro.persona.emailinst,
                                "email": pro.persona.email,
                                "celular": pro.persona.telefono,
                                "telefono": pro.persona.telefono_conv,
                                "coordinacion": pro.coordinacion.nombre,
                                "dedicacion": pro.dedicacion.nombre,
                                "horas": pro.dedicacion.horas} for pro in profesores]

                    data = {"result": "ok", "results": listado}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscarevaluador':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        profesores = Profesor.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                        | Q(persona__apellido2__icontains=s[0])
                                                        | Q(persona__cedula__icontains=s[0])
                                                        | Q(persona__ruc__icontains=s[0])
                                                        | Q(persona__pasaporte__icontains=s[0]),
                                                        status=True, categoria_id=2).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        profesores = Profesor.objects.filter(persona__apellido1__icontains=s[0],
                                                           persona__apellido2__icontains=s[1],
                                                           status=True, categoria_id=2).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    listado = [{"id": pro.id,
                                "name": str(pro.persona.nombre_completo_inverso()),
                                "identificacion": pro.persona.identificacion(),
                                "idpersona": pro.persona.id,
                                "usuario": pro.persona.usuario.username if pro.persona.usuario else '',
                                "emailinst": pro.persona.emailinst,
                                "email": pro.persona.email,
                                "celular": pro.persona.telefono,
                                "telefono": pro.persona.telefono_conv,
                                "coordinacion": pro.coordinacion.nombre,
                                "dedicacion": pro.dedicacion.nombre,
                                "horas": pro.dedicacion.horas} for pro in profesores]

                    data = {"result": "ok", "results": listado}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            elif action == 'datosactividad':
                try:
                    actividad = ProyectoInvestigacionCronogramaActividad.objects.get(pk=request.GET['id'])

                    data = {"result": "ok",
                            "fechainicio": actividad.fechainicio,
                            "fechafin": actividad.fechafin,
                            "ponderacion": actividad.ponderacion,
                            "avanceanterior": actividad.ultimo_porcentaje_ejecucion_asignado(),
                            "estado": actividad.get_estado_display(),
                            "entregables": actividad.entregables()}

                    return JsonResponse(data)
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos [%s]" % msg})

            elif action == 'mostrarrecorrido':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['proyecto'] = proyecto
                    data['recorrido'] = proyecto.proyectoinvestigacionrecorrido_set.filter(status=True).order_by('id')
                    template = get_template("pro_proyectoinvestigacion/recorridopropuesta.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'historialarchivo':
                try:
                    data['title'] = 'Historial de Archivos'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['proyecto'] = proyecto
                    data['archivos'] = proyecto.proyectoinvestigacionhistorialarchivo_set.filter(status=True).order_by('id')

                    template = get_template("adm_proyectoinvestigacion/historialarchivos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informacionproyecto':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Información del Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    convocatoria = proyecto.convocatoria
                    data['id'] = request.GET['id']

                    if proyecto.compraequipo:
                        convocatoriamonto = proyecto.convocatoria.convocatoriamontofinanciamiento_set.filter(status=True, tipoequipamiento=proyecto.compraequipo)[0]
                    else:
                        convocatoriamonto = proyecto.convocatoria.convocatoriamontofinanciamiento_set.filter(status=True, categoria=proyecto.categoria2)[0]

                    data['convocatoriamonto'] = convocatoriamonto
                    data['recursosconvocatoria'] = convocatoria.tipos_recursos_presupuesto()
                    regfin = convocatoriamonto
                    data['montominimoequipos'] = Decimal(proyecto.montounemi * (regfin.porcentajecompra) / 100).quantize(Decimal('.01'))
                    data['totalequipos'] = proyecto.totales_detalle_equipos()['totaldetalle']

                    data['objetivos'] = proyecto.objetivos_especificos()
                    data['ponderacion'] = proyecto.total_ponderacion_actividades()
                    data['cumplimiento'] = proyecto.porcentajeproyejec if proyecto.fase_aprobacion_superada() else 0
                    data['porcumplir'] = 100 - proyecto.porcentajeproyejec if proyecto.fase_aprobacion_superada() else 0

                    return render(request, "adm_proyectoinvestigacion/informacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'mostrarhojavida':
                try:
                    title = u'Hoja de Vida del Integrante'
                    integranteproyecto = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['integranteproyecto'] = integranteproyecto
                    data['integrante'] = integranteproyecto.persona
                    data['formacionacademica'] = integranteproyecto.formacion_academica()
                    data['experiencia'] = integranteproyecto.experiencia_laboral()
                    data['experienciaunemi'] = integranteproyecto.experiencia_laboral_unemi()
                    data['tipopersona'] = integranteproyecto.tipo

                    if integranteproyecto.tipo != 4:
                        data['articulos'] = integranteproyecto.articulos_publicados()
                        data['ponencias'] = integranteproyecto.ponencias_publicadas()
                        data['libros'] = integranteproyecto.libros_publicados()
                        data['capitulos'] = integranteproyecto.capitulos_libro_publicados()
                        data['proyectosunemi'] = integranteproyecto.proyectos_investigacion_unemi()
                        data['proyectosexternos'] = integranteproyecto.proyectos_investigacion_externo()
                    else:
                        data['articulos_externa'] = integranteproyecto.articulos_publicados_persona_externa()
                        data['ponencias_externa'] = integranteproyecto.ponencias_publicadas_persona_externa()
                        data['libros_externa'] = integranteproyecto.libros_publicados_persona_externa()
                        data['capitulos_externa'] = integranteproyecto.capitulos_libro_publicados_persona_externa()
                        data['proyectos_externa'] = integranteproyecto.proyectos_investigacion_persona_externa()

                    template = get_template("pro_proyectoinvestigacion/mostrarhojavida.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'personalproyecto':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Integrantes del Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    convocatoria = proyecto.convocatoria
                    integrantes = ProyectoInvestigacionIntegrante.objects.filter(status=True, proyecto=proyecto).order_by('funcion', 'persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    paging = MiPaginador(integrantes, 25)
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
                    data['integrantes'] = page.object_list
                    data['estadoproyecto'] = proyecto.estado.valor

                    data['minimou'] = convocatoria.minintegranteu
                    data['maximou'] = maximou = convocatoria.maxintegranteu
                    data['minimoe'] = convocatoria.minintegrantee
                    data['maximoe'] = maximoe = convocatoria.maxintegrantee
                    data['registradosu'] = registradosu = integrantes.filter(funcion__in=[1, 2, 3]).count()
                    data['registradose'] = registradose = integrantes.filter(funcion=5).count()
                    # data['mostrarboton'] = x = (registradosu + registradose) < (maximou + maximoe)

                    # if convocatoria.apertura.year <= 2020:
                    #     data['mostrarboton'] = True

                    data['mostrarboton'] = True
                    data['anio'] = convocatoria.apertura.year

                    return render(request, "adm_proyectoinvestigacion/personalproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'verificarrequisitos':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Verificación de Requisitos de la Propuesta de Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    convocatoria = proyecto.convocatoria
                    data['id'] = request.GET['id']

                    if proyecto.compraequipo:
                        convocatoriamonto = proyecto.convocatoria.convocatoriamontofinanciamiento_set.filter(status=True, tipoequipamiento=proyecto.compraequipo)[0]
                    else:
                        convocatoriamonto = proyecto.convocatoria.convocatoriamontofinanciamiento_set.filter(status=True, categoria=proyecto.categoria2)[0]

                    data['convocatoriamonto'] = convocatoriamonto
                    data['recursosconvocatoria'] = convocatoria.tipos_recursos_presupuesto()
                    regfin = convocatoriamonto
                    data['montominimoequipos'] = Decimal(proyecto.montounemi * (regfin.porcentajecompra) / 100).quantize(Decimal('.01'))
                    data['totalequipos'] = proyecto.totales_detalle_equipos()['totaldetalle']

                    data['objetivos'] = proyecto.objetivos_especificos()
                    data['ponderacion'] = proyecto.total_ponderacion_actividades()
                    data['cumplimiento'] = proyecto.porcentajeproyejec if proyecto.fase_aprobacion_superada() else 0
                    data['porcumplir'] = 100 - proyecto.porcentajeproyejec if proyecto.fase_aprobacion_superada() else 0

                    data['documentos'] = [
                        {"id": 1, "descripcion": "Datos Generales", "archivo": "", "estado": proyecto.estadodatogeneral, "observacion": proyecto.observaciondatogeneral},
                        {"id": 2, "descripcion": "Integrantes", "archivo": "", "estado": proyecto.estadointegrante, "observacion": proyecto.observacionintegrante},
                        {"id": 3, "descripcion": "Contenido", "archivo": "", "estado": proyecto.estadocontenido, "observacion": proyecto.observacioncontenido},
                        {"id": 4, "descripcion": "Presupuesto", "archivo": "", "estado": proyecto.estadopresupuesto, "observacion": proyecto.observacionpresupuesto},
                        {"id": 5, "descripcion": "Cronograma", "archivo": "", "estado": proyecto.estadocronogramarev, "observacion": proyecto.observacioncronograma},
                        {"id": 6, "descripcion": "Formulario Formato de inscripción de Proyecto firmado", "archivo": proyecto.archivodocumentofirmado.url, "estado": proyecto.estadodocumentofirmado, "observacion": proyecto.observaciondocumentofirmado}
                    ]

                    return render(request, "adm_proyectoinvestigacion/verificapropuesta.html", data)
                except Exception as ex:
                    pass

            elif action == 'verificarrequisitosold':
                try:
                    data['title'] = u'Verificación de Requisitos OLD'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['proyecto'] = proyecto
                    if proyecto.compraequipo:
                        convocatoriamonto = proyecto.convocatoria.convocatoriamontofinanciamiento_set.filter(status=True, tipoequipamiento=proyecto.compraequipo)[0]
                    else:
                        convocatoriamonto = proyecto.convocatoria.convocatoriamontofinanciamiento_set.filter(status=True, categoria=proyecto.categoria2)[0]
                    data['convocatoriamonto'] = convocatoriamonto

                    return render(request, "adm_proyectoinvestigacion/verificarequisitos.html", data)
                except Exception as ex:
                    pass

            elif action == 'verificarcambios':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['proyecto'] = proyecto
                    data['title'] = u'Verificación de Cambios Menores' if proyecto.estado.valor in [30, 42] else u'Verificación de Cambios Mayores'
                    data['estado'] = proyecto.estado.valor
                    return render(request, "adm_proyectoinvestigacion/verificarcambios.html", data)
                except Exception as ex:
                    pass

            elif action == 'evaluacioninterna':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    data['title'] = u'Evaluación Interna de la Propuesta de Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    data['estados'] = ESTADO_EVALUACION_INTERNA_EXTERNA
                    evaluadores1 = proyecto.evaluadores_internos_porevaluar()
                    evaluadores2 = None

                    # Si el estado del proyecto es E.I.ADICIONAL se debe mostrar los evaluadores que realizaron la evaluación :D
                    if proyecto.estado.valor == 9:
                        evaluadores2 = proyecto.evaluadores_internos_evaluaron()

                    if evaluadores1 and evaluadores2:
                        evaluadores = evaluadores1 | evaluadores2
                    elif evaluadores1:
                        evaluadores = evaluadores1
                    else:
                        evaluadores = evaluadores2

                    data['evaluadores'] = evaluadores
                    data['rubricas'] = proyecto.convocatoria.rubricas_evaluacion()
                    data['fecha'] = datetime.now().date()
                    return render(request, "adm_proyectoinvestigacion/evaluacioninterna.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'evaluacionexterna':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    data['title'] = u'Evaluación Externa de la Propuesta de Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    data['estados'] = ESTADO_EVALUACION_INTERNA_EXTERNA

                    evaluadores1 = proyecto.evaluadores_externos_porevaluar()
                    evaluadores2 = None

                    # Si el estado del proyecto es E.E.ADICIONAL se debe mostrar los evaluadores que realizaron la evaluación :D
                    if proyecto.estado.valor == 12:
                        evaluadores2 = proyecto.evaluadores_externos_evaluaron()

                    if evaluadores1 and evaluadores2:
                        evaluadores = evaluadores1 | evaluadores2
                    elif evaluadores1:
                        evaluadores = evaluadores1
                    else:
                        evaluadores = evaluadores2

                    data['evaluadores'] = evaluadores
                    data['rubricas'] = proyecto.convocatoria.rubricas_evaluacion()
                    data['fecha'] = datetime.now().date()
                    return render(request, "adm_proyectoinvestigacion/evaluacionexterna.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mostrarevaluaciones':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['proyecto'] = proyecto
                    data['evaluaciones'] = proyecto.evaluaciones()
                    data['rubricas'] = proyecto.convocatoria.rubricas_evaluacion()
                    if 'vcambios' in request.GET:
                        data['vcambios'] = request.GET['vcambios']

                    novedadesevaluaciones = proyecto.novedades_evaluaciones()
                    if novedadesevaluaciones["novedad"]:
                        data['mensajeresultadosdiferentes'] = novedadesevaluaciones["mensaje"]

                    template = get_template("adm_proyectoinvestigacion/evaluaciones.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'aprobarproyecto':
                try:
                    data['title'] = u'Aprobar Proyecto de Investigación'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    convocatoria = proyecto.convocatoria

                    if proyecto.tiene_conflicto_fechas_iniciofin_actividades():
                        return JsonResponse({"result": "bad", "mensaje": u"No se puede ejecutar la acción debido a que existen actividades con fecha de inicio mayor a la fecha de fin de la misma actividad. Revisar el cronograma de actividades"})

                    data['proyecto'] = proyecto
                    data['estados'] = obtener_estados_solicitud(3, [18, 19])
                    data['fecha'] = fechaactual = datetime.now().date()
                    data['mesesproyecto'] = mesesproyecto = proyecto.tiempomes
                    fechafin = fechaactual + relativedelta(months=mesesproyecto)
                    data['fechafin'] = fechafin
                    data['anioconvocatoria'] = convocatoria.apertura.year
                    data['resolucionaprobacion'] = convocatoria.resolucion_aprobacion()[0]


                    template = get_template("adm_proyectoinvestigacion/aprobarproyecto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'evidenciasproyecto':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Revisión de Evidencias del Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    data['objetivos'] = proyecto.cronograma_objetivo()

                    return render(request, "adm_proyectoinvestigacion/evidencias.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirevidencia':
                try:
                    data['title'] = u'Subir Evidencia de la Actividad' if request.GET['retraso'] == 'NO' else u'Subir Evidencia de la Actividad (Con Retraso)'
                    actividad = ProyectoInvestigacionCronogramaActividad.objects.get(pk=int(encrypt(request.GET['ida'])))

                    entregables = [{"id": entregable.id,
                                    "descripcion": entregable.entregable} for entregable in actividad.lista_entregables()]

                    return JsonResponse({"result": "ok", 'title': data['title'], 'descripcionactividad': actividad.actividad, 'entregables': entregables})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'delevidencia':
                try:
                    evidencia = ProyectoInvestigacionActividadEvidencia.objects.get(pk=request.GET['ide'])

                    # En caso de haber ya sido revisada por coordinación de investigación
                    if evidencia.estado != 1:
                        return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar la evidencia porque ya fue revisada por Investigación"})

                    actividad = evidencia.entregable.actividad
                    evidencia.status = False
                    evidencia.save(request)

                    totalevidencias = actividad.total_evidencias()

                    log(u'Eliminó evidencia de la actividad de proyecto de investigación [ %s ]' % (evidencia), request, "del")
                    return JsonResponse({"result": "ok", "totalevidencias": totalevidencias})
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

            elif action == 'mostrarevidencias':
                try:
                    data['title'] = u'Evidencias de la Actividad'
                    actividad = ProyectoInvestigacionCronogramaActividad.objects.get(pk=int(encrypt(request.GET['ida'])))

                    evidencias = [{"id": evidencia.id,
                                   "entregable": evidencia.entregable.entregable,
                                   "descripcion": evidencia.descripcion,
                                   "fecha": evidencia.fecha,
                                   "archivo": evidencia.archivo.url,
                                   "retraso": "SI" if evidencia.retraso else "NO",
                                   "estado": evidencia.get_estado_display(),
                                   "estadocod": evidencia.estado,
                                   "observacion": evidencia.observacion,
                                   "colorestado": evidencia.color_estado()} for evidencia in actividad.evidencias()]

                    return JsonResponse({"result": "ok", 'title': data['title'], 'descripcionactividad': actividad.actividad, 'evidencias': evidencias})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'revisarevidencias':
                try:
                    data['title'] = u'Revisar Actividad / Evidencias'
                    actividad = ProyectoInvestigacionCronogramaActividad.objects.get(pk=int(encrypt(request.GET['ida'])))

                    data['actividad'] = actividad
                    data['ponderacion'] = actividad.ponderacion
                    data['evidencias'] = actividad.evidencias_por_revisar()
                    data['estados'] = (
                                            (2, u"VALIDADO"),
                                            (4, u"NOVEDAD")
                                        )
                    data['ultimoporcentaje'] = actividad.ultimo_porcentaje_ejecucion_asignado()
                    template = get_template("adm_proyectoinvestigacion/revisarevidencia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'confirmarrevisionevidencias':
                try:
                    data['title'] = u'Confirmar Revisión Actividad / Evidencias'
                    actividad = ProyectoInvestigacionCronogramaActividad.objects.get(pk=int(encrypt(request.GET['ida'])))

                    data['actividad'] = actividad
                    data['ponderacion'] = actividad.ponderacion
                    data['ultimarevision'] = ultimarevision = actividad.ultima_revision()
                    data['detallesrevision'] = ultimarevision.detalle_revision()
                    data['evidenciasxrevisar'] = "SI" if actividad.evidencias_por_revisar() else "NO"

                    data['estados'] = (
                                            (2, u"VALIDADO"),
                                            (4, u"NOVEDAD")
                                        )
                    data['ultimoporcentaje'] = actividad.ultimo_porcentaje_ejecucion_asignado()
                    template = get_template("adm_proyectoinvestigacion/confirmarrevisionevidencia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'asignarrevisorinformes':
                try:
                    data['title'] = u'Asignar Revisores de Informes de Proyecto de Investigación'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    data['proyecto'] = proyecto
                    data['coordinador'] = coordinador_investigacion()
                    data['tecnicosinvestigacion'] = tecnicos_investigacion()
                    data['coordinadorasignado'] = proyecto.apruebainforme.id if proyecto.apruebainforme else None
                    data['tecnicoasignado'] = proyecto.verificainforme.id if proyecto.verificainforme else None

                    template = get_template("adm_proyectoinvestigacion/asignarrevisorinforme.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informesproyecto':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Revisión de Informes del Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    data['informes'] = proyecto.informes_tecnicos()

                    if 'idi' in request.GET:
                        informe = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.GET['idi'])))
                        data['informe'] = informe.archivo.url if informe.archivo else informe.archivogenerado.url
                        data['tipoinforme'] = f'Informe firmado {informe.numero}' if informe.archivo else f'Informe sin firma {informe.numero}'

                    return render(request, "adm_proyectoinvestigacion/informes.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinforme':
                try:
                    # data['informe'] = informe = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.GET['id'])))
                    # tipoinforme = informe.get_tipo_display() if informe.tipo == 2 else informe.get_tipo_display() + ' ' + str(informe.secuencia)
                    data['title'] = u'Agregar Informe de Proyecto de Investigación'
                    data['proyecto'] = proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    secuencia = proyecto.secuencia_informe_avance()
                    numero = str(secuencia).zfill(3) + "-PROY-" + proyecto.codigo

                    # data['avanceesperado'] = proyecto.porcentaje_avance_esperado()
                    # data['avanceejecucion'] = proyecto.porcentaje_avance_ejecucion()

                    data['resolucionaprueba'] = resolucionaprueba = proyecto.convocatoria.resolucion_aprobacion()[0]
                    data['fecharesolucion'] = str(resolucionaprueba.fecha.day) + " de " + MESES_CHOICES[resolucionaprueba.fecha.month - 1][1].capitalize() + " del " + str(resolucionaprueba.fecha.year)
                    data['fechainicio'] = str(proyecto.fechainicio.day) + " de " + MESES_CHOICES[proyecto.fechainicio.month - 1][1].capitalize() + " del " + str(proyecto.fechainicio.year)
                    data['fechafinestimada'] = str(proyecto.fechafinplaneado.day) + " de " + MESES_CHOICES[proyecto.fechafinplaneado.month - 1][1].capitalize() + " del " + str(proyecto.fechafinplaneado.year)
                    data['mesinicio'] = MESES_CHOICES[proyecto.fechainicio.month - 1][1].capitalize() + " del " + str(proyecto.fechainicio.year)
                    data['integrantes'] = integrantes = proyecto.integrantes_proyecto_informe()
                    data['codirector'] = integrantes.filter(funcion=2)
                    data['investigadores'] = integrantes.filter(funcion=3)
                    data['asistentes'] = integrantes.filter(funcion=4)

                    # data['objetivos'] = proyecto.objetivos_especificos()

                    data['numero'] = numero
                    data['fecha'] = datetime.now().date()
                    data['evidencias'] = proyecto.evidencias_subidas_validadas()
                    data['periodovigente'] = periodo_vigente_distributivo_docente_investigacion(proyecto.profesor)

                    form = InformeProyectoForm(initial={
                        'fecha': datetime.now().date(),
                        'numero': numero
                    })
                    data['form'] = form

                    return render(request, "adm_proyectoinvestigacion/addinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinforme':
                try:
                    data['informe'] = informe = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.GET['id'])))
                    tipoinforme = informe.get_tipo_display() if informe.tipo == 2 else informe.get_tipo_display() + ' ' + str(informe.secuencia)
                    data['title'] = u'Editar Informe de Proyecto de Investigación (INFORME ' + tipoinforme + ')'

                    data['proyecto'] = proyecto = informe.proyecto
                    data['avanceesperado'] = informe.avanceesperado
                    data['avanceejecucion'] = informe.porcentajeejecucion
                    data['resolucionaprueba'] = resolucionaprueba = proyecto.convocatoria.resolucion_aprobacion()[0]
                    data['fecharesolucion'] = str(resolucionaprueba.fecha.day) + " de " + MESES_CHOICES[resolucionaprueba.fecha.month - 1][1].capitalize() + " del " + str(resolucionaprueba.fecha.year)
                    data['fechainicio'] = str(proyecto.fechainicio.day) + " de " + MESES_CHOICES[proyecto.fechainicio.month - 1][1].capitalize() + " del " + str(proyecto.fechainicio.year)
                    data['fechafinestimada'] = str(proyecto.fechafinplaneado.day) + " de " + MESES_CHOICES[proyecto.fechafinplaneado.month - 1][1].capitalize() + " del " + str(proyecto.fechafinplaneado.year)
                    data['mesinicio'] = MESES_CHOICES[proyecto.fechainicio.month - 1][1].capitalize() + " del " + str(proyecto.fechainicio.year)
                    data['integrantes'] = integrantes = proyecto.integrantes_proyecto_informe()
                    data['codirector'] = integrantes.filter(funcion=2)
                    data['investigadores'] = integrantes.filter(funcion=3)
                    data['asistentes'] = integrantes.filter(funcion=4)
                    data['actividades'] = informe.actividades()
                    data['numero'] = numero = informe.numero
                    data['fechainforme'] = informe.fecha
                    data['fecha'] = fecha = datetime.now().date()
                    data['evidencias'] = informe.proyectoinvestigacioninformeanexo_set.filter(status=True).order_by('id')
                    data['periodovigente'] = informe.periodo

                    form = InformeProyectoForm(initial={
                        'fecha': fecha,
                        'numero': numero
                    })
                    data['form'] = form

                    return render(request, "adm_proyectoinvestigacion/editinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirinforme':
                try:
                    data['title'] = u'Subir Informe de Avance Firmado'
                    informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['informeproyecto'] = informeproyecto

                    template = get_template("adm_proyectoinvestigacion/subirinforme.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mostrardistributivo':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    periodovigente = Periodo.objects.get(pk=int(encrypt(request.GET['idper']))) if request.GET['idper'] else None

                    data['proyecto'] = proyecto
                    data['periodovigente'] = periodovigente

                    integrantes = proyecto.integrantes_proyecto_informe()
                    # Obtengo los integrantes tipo PROFESOR
                    data['integrantes'] = integrantes.filter(tipo=1)

                    template = get_template("pro_proyectoinvestigacion/distributivoinvestigacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'revisarinforme':
                try:
                    data['informe'] = informe = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.GET['id'])))
                    tipoinforme = informe.get_tipo_display() if informe.tipo == 2 else informe.get_tipo_display() + ' ' + str(informe.secuencia)
                    data['title'] = u'Revisar Informe de Proyecto de Investigación (INFORME ' + tipoinforme + ')'

                    data['proyecto'] = proyecto = informe.proyecto
                    data['avanceesperado'] = informe.avanceesperado
                    data['avanceejecucion'] = informe.porcentajeejecucion
                    data['resolucionaprueba'] = resolucionaprueba = proyecto.convocatoria.resolucion_aprobacion()[0]
                    data['fecharesolucion'] = str(resolucionaprueba.fecha.day) + " de " + MESES_CHOICES[resolucionaprueba.fecha.month - 1][1].capitalize() + " del " + str(resolucionaprueba.fecha.year)
                    data['fechanotificacion'] = str(resolucionaprueba.fechanotificaaprobacion.day) + " de " + MESES_CHOICES[resolucionaprueba.fechanotificaaprobacion.month - 1][1].capitalize() + " del " + str(resolucionaprueba.fechanotificaaprobacion.year)
                    data['fechainicio'] = str(proyecto.fechainicio.day) + " de " + MESES_CHOICES[proyecto.fechainicio.month - 1][1].capitalize() + " del " + str(proyecto.fechainicio.year)
                    data['fechafinestimada'] = str(proyecto.fechafinplaneado.day) + " de " + MESES_CHOICES[proyecto.fechafinplaneado.month - 1][1].capitalize() + " del " + str(proyecto.fechafinplaneado.year)
                    data['mesinicio'] = MESES_CHOICES[proyecto.fechainicio.month - 1][1].capitalize() + " del " + str(proyecto.fechainicio.year)
                    data['integrantes'] = integrantes = proyecto.integrantes_proyecto_informe()
                    data['codirector'] = integrantes.filter(funcion=2)
                    data['investigadores'] = integrantes.filter(funcion=3)
                    data['asistentes'] = integrantes.filter(funcion=4)
                    data['colaboradores'] = integrantes.filter(funcion=5)

                    # data['objetivos'] = informe.objetivos_especificos_cronograma_informe()
                    data['actividades'] = informe.actividades()

                    data['numero'] = numero = informe.numero
                    data['fecha'] = fecha = informe.fecha
                    data['evidencias'] = informe.evidencias()
                    data['periodovigente'] = informe.periodo

                    data['estados'] = (
                        (5, u"VERIFICADO"),
                        (6, u"PRESENTA NOVEDADES")
                    )

                    form = InformeProyectoForm(initial={
                        'fecha': fecha,
                        'numero': numero
                    })
                    data['form'] = form

                    return render(request, "adm_proyectoinvestigacion/revisarinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'revisarinformefinal':
                try:
                    data['informe'] = informe = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Revisar Informe Final de Proyecto de Investigación'
                    data['proyecto'] = proyecto = informe.proyecto
                    data['objetivos'] = proyecto.objetivos_especificos()
                    data['estados'] = (
                        (5, u"VERIFICADO"),
                        (6, u"PRESENTA NOVEDADES")
                    )
                    return render(request, "adm_proyectoinvestigacion/revisarinformefinal.html", data)
                except Exception as ex:
                    pass

            elif action == 'aprobarinforme':
                try:
                    data['informe'] = informe = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.GET['id'])))
                    tipoinforme = informe.get_tipo_display() if informe.tipo == 2 else informe.get_tipo_display() + ' ' + str(informe.secuencia)
                    data['title'] = u'Aprobar Informe de Proyecto de Investigación (INFORME ' + tipoinforme + ')'

                    data['proyecto'] = proyecto = informe.proyecto
                    data['avanceesperado'] = informe.avanceesperado
                    data['avanceejecucion'] = informe.porcentajeejecucion
                    data['resolucionaprueba'] = resolucionaprueba = proyecto.convocatoria.resolucion_aprobacion()[0]
                    data['fecharesolucion'] = str(resolucionaprueba.fecha.day) + " de " + MESES_CHOICES[resolucionaprueba.fecha.month - 1][1].capitalize() + " del " + str(resolucionaprueba.fecha.year)
                    data['fechanotificacion'] = str(resolucionaprueba.fechanotificaaprobacion.day) + " de " + MESES_CHOICES[resolucionaprueba.fechanotificaaprobacion.month - 1][1].capitalize() + " del " + str(resolucionaprueba.fechanotificaaprobacion.year)
                    data['fechainicio'] = str(proyecto.fechainicio.day) + " de " + MESES_CHOICES[proyecto.fechainicio.month - 1][1].capitalize() + " del " + str(proyecto.fechainicio.year)
                    data['fechafinestimada'] = str(proyecto.fechafinplaneado.day) + " de " + MESES_CHOICES[proyecto.fechafinplaneado.month - 1][1].capitalize() + " del " + str(proyecto.fechafinplaneado.year)
                    data['mesinicio'] = MESES_CHOICES[proyecto.fechainicio.month - 1][1].capitalize() + " del " + str(proyecto.fechainicio.year)
                    data['integrantes'] = integrantes = proyecto.integrantes_proyecto_informe()
                    data['codirector'] = integrantes.filter(funcion=2)
                    data['investigadores'] = integrantes.filter(funcion=3)
                    data['asistentes'] = integrantes.filter(funcion=4)
                    data['colaboradores'] = integrantes.filter(funcion=5)

                    # data['objetivos'] = informe.objetivos_especificos_cronograma_informe()
                    data['actividades'] = informe.actividades()

                    data['numero'] = numero = informe.numero
                    data['fecha'] = fecha = informe.fecha
                    data['evidencias'] = informe.proyectoinvestigacioninformeanexo_set.filter(status=True).order_by('id')
                    data['estados'] = (
                        (7, u"APROBADO"),
                        (8, u"PRESENTA NOVEDADES")
                    )

                    form = InformeProyectoForm(initial={
                        'fecha': fecha,
                        'numero': numero
                    })
                    data['form'] = form
                    data['fechaactual'] = datetime.now().date()

                    return render(request, "adm_proyectoinvestigacion/aprobarinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'aprobarinformefinal':
                try:
                    data['informe'] = informe = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Aprobar Informe Final de Proyecto de Investigación'
                    data['proyecto'] = proyecto = informe.proyecto
                    data['objetivos'] = proyecto.objetivos_especificos()
                    data['estados'] = (
                        (7, u"APROBADO"),
                        (8, u"P.NOVEDADES A")
                    )
                    return render(request, "adm_proyectoinvestigacion/aprobarinformefinal.html", data)
                except Exception as ex:
                    pass

            elif action == 'subircontrato':
                try:
                    # data['title'] = u'Subir Contrato de Financiamiento'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['title'] = u'Subir Contrato de Financiamiento' if not proyecto.archivocontratoejecucion else u'Actualizar Contrato de Financiamiento'

                    data['proyecto'] = proyecto

                    template = get_template("adm_proyectoinvestigacion/subircontratofinanciamiento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'asignarevaluadorpfinalizado':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    data['title'] = u'Asignar Evaluadores a Proyecto de Investigación Finalizado'
                    form = EvaluadorProyectoInvestigacionFinalizadoForm(initial={
                        'titulo': proyecto.titulo
                    })
                    data['form'] = form
                    data['proyecto'] = proyecto
                    data['evaluadores'] = evaluadores = proyecto.evaluadores_proyecto_finalizado()
                    data['total'] = evaluadores.count()
                    data['ecompletas'] = ecompletas = proyecto.evaluaciones_proyectofinalizado_completas()
                    data['evaluacionescompletas'] = ecompletas
                    data['bancoevaluadores'] = x = Profesor.objects.filter(evaluadorproyecto__status=True, evaluadorproyecto__activo=True, evaluadorproyecto__proyectofinalizado=True, status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    return render(request, "adm_proyectoinvestigacion/asignarevaluadorproyectofinalizado.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirevaluacion':
                try:
                    data['title'] = u'Subir Archivo de Evaluación'
                    evaluacion = EvaluacionProyecto.objects.get(pk=request.GET['id'])
                    data['evaluacion'] = evaluacion

                    template = get_template("adm_proyectoinvestigacion/subirevaluacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subirevaluacionfirmada':
                try:
                    data['title'] = u'Subir Archivo de Evaluación Firmada'
                    evaluacion = EvaluacionProyecto.objects.get(pk=request.GET['id'])
                    data['evaluacion'] = evaluacion

                    template = get_template("adm_proyectoinvestigacion/subirevaluacionfirmada.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cerrarevaluacion':
                try:
                    data['title'] = u'Cerrar Evaluación de la Propuesta'
                    evaluacion = EvaluacionProyecto.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['evaluacion'] = evaluacion
                    estados = [
                        {"id": "5", "descripcion": "CERRADA"},
                        {"id": "6", "descripcion": "NOVEDAD"}
                    ]
                    data['estados'] = estados
                    template = get_template("adm_proyectoinvestigacion/cerrarevaluacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'validarcronograma':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Validar Cronograma del Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    convocatoria = proyecto.convocatoria
                    data['tituloconvocatoria'] = convocatoria.descripcion
                    data['recursosconvocatoria'] = convocatoria.tipos_recursos_presupuesto()
                    data['objetivos'] = proyecto.objetivos_especificos()

                    return render(request, "adm_proyectoinvestigacion/validarcronograma.html", data)
                except Exception as ex:
                    pass

            elif action == 'agregaractividadinforme':
                try:
                    data['title'] = u'Agregar Actividad a Informe de Proyecto de Investigación'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))

                    data['proyecto'] = proyecto
                    data['periodovigente'] = periodo_vigente_distributivo_docente_investigacion(proyecto.profesor)
                    data['actividades'] = proyecto.cronograma_actividades_pendientes()
                    data['integrantes'] = proyecto.integrantes_proyecto_informe()

                    template = get_template("adm_proyectoinvestigacion/addactividadinforme.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addintegrante':
                try:
                    data['title'] = u'Agregar Integrante del proyecto'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    data['proyecto'] = proyecto

                    if not proyecto.integrantes_completos():
                        data['tipopersona'] = TIPO_INTEGRANTE
                        data['funcionpersona'] = ((1, u'DIRECTOR'),
                                                (2, u'CO-DIRECTOR'),
                                                (3, u'INVESTIGADOR ASOCIADO'),
                                                (4, u'AYUDANTE DE INVESTIGACIÓN'),
                                                (5, u'INVESTIGADOR COLABORADOR'))
                    else:
                        data['tipopersona'] = ((2, u'ESTUDIANTE'),)
                        data['funcionpersona'] = ((4, u'AYUDANTE DE INVESTIGACIÓN'),)

                    template = get_template("adm_proyectoinvestigacion/addintegrante.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editintegrante':
                try:
                    data['title'] = u'Editar Integrante del proyecto'
                    integrante = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.GET['idi'])))
                    data['tipopersona'] = integrante.get_tipo_display()
                    data['tipoper'] = integrante.tipo
                    data['funcionper'] = integrante.funcion
                    data['integranteid'] = integrante.id
                    data['integrante'] = integrante.persona
                    data['observacion'] = integrante.observacion
                    data['funcionpersona'] = ((2, u'CO-DIRECTOR'),
                                             (3, u'INVESTIGADOR ASOCIADO'),
                                             (4, u'ASISTENTE DE INVESTIGACIÓN'))

                    template = get_template("adm_proyectoinvestigacion/editintegrante.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'reemplazarintegrante':
                try:
                    data['title'] = u'Reemplazar Integrante del proyecto'
                    # proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))

                    integrante = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.GET['idi'])))

                    data['tipopersonai'] = integrante.get_tipo_display()
                    data['tipoper'] = integrante.tipo
                    data['funcionper'] = integrante.funcion
                    data['funcion'] = integrante.get_funcion_display()
                    data['integranteid'] = integrante.id
                    data['integrante'] = integrante.persona
                    data['proyecto'] = integrante.proyecto
                    data['tipopersona'] = TIPO_INTEGRANTE

                    template = get_template("adm_proyectoinvestigacion/reemplazarintegrante.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editrol':
                try:
                    data['title'] = u'Editar Rol del Integrante del proyecto'

                    integrante = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.GET['idi'])))

                    data['integrante'] = integrante
                    data['proyecto'] = integrante.proyecto

                    if integrante.funcion == 1:
                        roles = [
                            {"id": 2, "descripcion": "CO-DIRECTOR"},
                            {"id": 3, "descripcion": "INVESTIGADOR ASOCIADO"}
                        ]
                    elif integrante.funcion == 2:
                        roles = [
                            {"id": 1, "descripcion": "DIRECTOR"},
                            {"id": 3, "descripcion": "INVESTIGADOR ASOCIADO"}
                        ]
                    else:
                        roles = [
                            {"id": 1, "descripcion": "DIRECTOR"},
                            {"id": 2, "descripcion": "CO-DIRECTOR"}
                        ]

                    data['roles'] = roles
                    template = get_template("adm_proyectoinvestigacion/editrol.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'delintegrante':
                try:
                    data['title'] = u'Eliminar Integrante del proyecto'

                    integrante = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.GET['idi'])))

                    data['integrante'] = integrante
                    data['proyecto'] = integrante.proyecto

                    template = get_template("adm_proyectoinvestigacion/delintegrante.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mostrarevidenciasinforme':
                try:
                    informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['evidencias'] = evidencias = informeproyecto.evidencias() if informeproyecto.tipo == 1 else informeproyecto.evidencias_informe_final()
                    data['informe'] = informeproyecto
                    template = get_template("adm_proyectoinvestigacion/evidenciainformeadm.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subirpresupuesto':
                try:
                    data['title'] = u'Subir Presupuesto Actualizado'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['proyecto'] = proyecto

                    template = get_template("pro_proyectoinvestigacion/subirpresupuesto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subirdocumento':
                try:
                    data['title'] = u'Subir Documento Firmado'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['proyecto'] = proyecto
                    template = get_template("pro_proyectoinvestigacion/subirdocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'anularproyecto':
                try:
                    data['title'] = u'Anular Proyecto de Investigación'
                    data['proyecto'] = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("adm_proyectoinvestigacion/anularproyecto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editmontopresupuesto':
                try:
                    data['title'] = u'Actualizar Monto del Presupuesto de Proyecto de Investigación'
                    data['proyecto'] = proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['fecha'] = datetime.now().date()
                    convocatoriamonto = ConvocatoriaMontoFinanciamiento.objects.get(convocatoria=proyecto.convocatoria, categoria=proyecto.categoria2)
                    data['montomaximo'] = convocatoriamonto.maximo
                    template = get_template("adm_proyectoinvestigacion/editmontopresupuesto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subircontratoexterno':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['title'] = u'Subir Contrato de Financiamiento - Proyectos Externos (Convenio)' if not proyecto.archivocontratoejecucion else u'Actualizar Contrato de Financiamiento - Proyectos Externos (Convenio)'
                    data['proyecto'] = proyecto
                    data['fecha'] = datetime.now().date()
                    data['tiporeg'] = 'N' if not proyecto.archivocontratoejecucion else 'E'

                    template = get_template("adm_proyectoinvestigacion/subircontratofinanciamientoexterno.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'devengadopresupuesto':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Gestión de Presupuesto del Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    data['ejecutado'] = proyecto.porcentajepresupejec
                    data['porejecutar'] = 100 - proyecto.porcentajepresupejec
                    data['recursosconvocatoria'] = proyecto.convocatoria.tipos_recursos_presupuesto()
                    data['puedeagregar'] = not proyecto.permiso_edicion_vigente(1, 2) and not proyecto.permiso_edicion_vigente(1, 1)

                    return render(request, "adm_proyectoinvestigacion/devengadopresupuesto.html", data)
                except Exception as ex:
                    pass

            elif action == 'adddevengadorubro':
                try:
                    data['title'] = u'Agregar Devengado al Rubro del Presupuesto'
                    data['rubro']= ProyectoInvestigacionItemPresupuesto.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("adm_proyectoinvestigacion/adddevengadorubro.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'movimientorubro':
                try:
                    rubro = ProyectoInvestigacionItemPresupuesto.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Movimientos del Rubro de Presupuesto del Proyecto de Investigación'
                    data['rubro'] = rubro
                    data['proyecto'] = rubro.proyecto
                    data['movimientos'] = rubro.movimientos()
                    # data['ejecutado'] = proyecto.porcentajepresupejec
                    # data['porejecutar'] = 100 - proyecto.porcentajepresupejec
                    # data['recursosconvocatoria'] = proyecto.convocatoria.tipos_recursos_presupuesto()
                    # data['puedeagregar'] = not proyecto.permiso_edicion_vigente(2) and not proyecto.permiso_edicion_vigente(1)

                    return render(request, "adm_proyectoinvestigacion/movimientorubroproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'firmarinformeavance':
                try:
                    tipofirma = request.GET['tipofirma']

                    informe = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['iddoc'] = informe.id
                    data['tipofirma'] = tipofirma

                    if tipofirma == 'VAL':  # Persona que valida
                        data['title'] = u'Firma del Informe Técnico. Verificado por: {}'.format(informe.personaverifica.nombre_completo_inverso())
                        data['idper'] = informe.personaverifica.id
                    else:  # Persona que aprueba
                        data['title'] = u'Firma del Informe Técnico. Aprobado por: {}'.format(informe.personaaprueba.nombre_completo_inverso())
                        data['idper'] = informe.personaaprueba.id

                    data['mensaje'] = "Firma del Informe de Proyecto de Investigación N° <b>{}</b> del director de proyecto <b>{}</b>".format(informe.numero, informe.proyecto.profesor.persona.nombre_completo_inverso())
                    data['accionfirma'] = action

                    template = get_template("pro_becadocente/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'registrarreprogramacion':
                try:
                    data['title'] = u'Registrar Re-Programación al Proyecto de Investigación'
                    data['proyecto'] = proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("adm_proyectoinvestigacion/modal/registrarreprogramacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'registrarprorroga':
                try:
                    data['title'] = u'Registrar Prórroga al Proyecto de Investigación'
                    data['proyecto'] = proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))

                    # Si es convocatoria >= 2022 buscar permiso de edición del cronograma
                    if proyecto.convocatoria.apertura.year >= 2022:
                        permisovigente = proyecto.permiso_edicion_vigente(2, 1)
                        if permisovigente:
                            data['iniciopermiso'] = permisovigente.inicio
                            data['finpermiso'] = permisovigente.fin

                    template = get_template("adm_proyectoinvestigacion/modal/registrarprorroga.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'finalizarproyecto':
                try:
                    data['title'] = u'Finalizar Proyecto de Investigación'
                    data['proyecto'] = proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['informefinal'] = proyecto.informe_final()
                    data['tamanio'] = variable_valor("TAMANIO_INFORME_FINAL")
                    template = get_template("adm_proyectoinvestigacion/modal/finalizarproyecto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cerrarproyecto':
                try:
                    data['title'] = u'Cerrar Proyecto de Investigación'
                    data['proyecto'] = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['tamanio'] = "4MB"
                    template = get_template("adm_proyectoinvestigacion/modal/cerrarproyecto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'validarinformefirmado':
                try:
                    data['title'] = u'Validar Informe Final Firmado de Proyecto de Investigación'
                    data['informeproyecto'] = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("adm_proyectoinvestigacion/modal/validarinformefirmado.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'agregarexclusion':
                try:
                    data['title'] = u'Agregar Exclusion de Validación Participantes para Proyectos'
                    data['convocatorias'] = ConvocatoriaProyecto.objects.filter(status=True).order_by('-id')[:1]
                    template = get_template("adm_proyectoinvestigacion/modal/addexclusionvalidacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'avancesactividades':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    ida = request.GET.get('ida', '')
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, proyecto=proyecto), ''
                    desde, hasta, estadoid = request.GET.get('desde', ''), request.GET.get('hasta', ''), int(request.GET.get('estadoid', '0'))

                    if search:
                        data['s'] = search
                        ss = search.split(" ")
                        if len(ss) == 1:
                            filtro = filtro & (Q(solicita__nombres__icontains=search) |
                                               Q(solicita__apellido1__icontains=search) |
                                               Q(solicita__apellido2__icontains=search))
                        else:
                            filtro = filtro & (Q(solicita__apellido1__contains=ss[0]) &
                                               Q(solicita__apellido2__contains=ss[1]))

                        url_vars += f'&s={search}'

                    if desde:
                        data['desde'] = datetime.strptime(desde, '%Y-%m-%d').date()
                        filtro = filtro & Q(fecha__gte=desde)
                        url_vars += f'&desde={desde}'

                    if hasta:
                        data['hasta'] = datetime.strptime(hasta, '%Y-%m-%d').date()
                        filtro = filtro & Q(fecha__lte=hasta)
                        url_vars += f'&hasta={hasta}'

                    data['estadoid'] = estadoid
                    if estadoid:
                        filtro = filtro & Q(estado__valor=estadoid)
                        url_vars += f'&estadoid={estadoid}'

                    avances = ProyectoInvestigacionAvanceActividad.objects.filter(filtro).order_by('id')

                    paging = MiPaginador(avances, 25)
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
                    data['avances'] = page.object_list
                    # data['fechadesde'] = datetime.now().date()
                    # data['fechahasta'] = datetime.now().date()
                    data['title'] = u'Avances Mensuales de Actividades del Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    data['puedeagregar'] = not proyecto.avances_actividades()

                    return render(request, "adm_proyectoinvestigacion/avanceactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'mostraravanceactividad':
                try:
                    data['title'] = u'Detalle de Avances de Actividades del Proyecto de Investigación'
                    data['avanceactividad'] = avanceactividad = ProyectoInvestigacionAvanceActividad.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['proyecto'] = proyecto = avanceactividad.proyecto
                    data['objetivos'] = proyecto.objetivos_especificos()
                    return render(request, "adm_proyectoinvestigacion/mostraravanceactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'registrarevaluadorpropuesta':
                try:
                    data['title'] = u'Registro de Evaluadores de la Propuesta de Proyecto de Investigación'
                    data['proyecto'] = proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['convocatoria'] = proyecto.convocatoria

                    evaluadoresinternos = proyecto.evaluadores_internos()
                    evaluadoresexternos = proyecto.evaluadores_externos()

                    if evaluadoresinternos:
                        evaluador = evaluadoresinternos[0]
                        data['evaluadorinterno1'] = {
                            "id": evaluador.id,
                            "idp": evaluador.id_registro_profesor_o_externo(),
                            "identificacion": evaluador.persona.identificacion(),
                            "nombres": evaluador.persona.nombre_completo_inverso(),
                            "celular": evaluador.persona.telefono,
                            "email": evaluador.persona.emailinst,
                            "notificado" : evaluador.notificado,
                            "estado" : "Registrada" if evaluador.tiene_registro_evaluacion() else "Pendiente",
                            "clase" : "text-success" if evaluador.tiene_registro_evaluacion() else "text-warning",
                            "eregistrada" : "S" if evaluador.tiene_registro_evaluacion else "N"
                        }

                        evaluador = evaluadoresinternos[1]
                        data['evaluadorinterno2'] = {
                            "id": evaluador.id,
                            "idp": evaluador.id_registro_profesor_o_externo(),
                            "identificacion": evaluador.persona.identificacion(),
                            "nombres": evaluador.persona.nombre_completo_inverso(),
                            "celular": evaluador.persona.telefono,
                            "email": evaluador.persona.emailinst,
                            "notificado" : evaluador.notificado,
                            "estado" : "Registrada" if evaluador.tiene_registro_evaluacion() else "Pendiente",
                            "clase" : "text-success" if evaluador.tiene_registro_evaluacion() else "text-warning",
                            "eregistrada" : "S" if evaluador.tiene_registro_evaluacion else "N"
                        }

                    if evaluadoresexternos:
                        evaluador = evaluadoresexternos[0]
                        data['evaluadorexterno1'] = {
                            "id": evaluador.id,
                            "idp": evaluador.id_registro_profesor_o_externo(),
                            "identificacion": evaluador.persona.identificacion(),
                            "nombres": evaluador.persona.nombre_completo_inverso(),
                            "celular": evaluador.persona.telefono,
                            "email": evaluador.persona.emailinst,
                            "notificado" : evaluador.notificado,
                            "estado" : "Registrada" if evaluador.tiene_registro_evaluacion() else "Pendiente",
                            "clase" : "text-success" if evaluador.tiene_registro_evaluacion() else "text-warning",
                            "eregistrada" : "S" if evaluador.tiene_registro_evaluacion else "N"
                        }

                        evaluador = evaluadoresexternos[1]
                        data['evaluadorexterno2'] = {
                            "id": evaluador.id,
                            "idp": evaluador.id_registro_profesor_o_externo(),
                            "identificacion": evaluador.persona.identificacion(),
                            "nombres": evaluador.persona.nombre_completo_inverso(),
                            "celular": evaluador.persona.telefono,
                            "email": evaluador.persona.emailinst,
                            "notificado" : evaluador.notificado,
                            "estado" : "Registrada" if evaluador.tiene_registro_evaluacion() else "Pendiente",
                            "clase" : "text-success" if evaluador.tiene_registro_evaluacion() else "text-warning",
                            "eregistrada" : "S" if evaluador.tiene_registro_evaluacion else "N"
                        }

                    template = get_template("adm_proyectoinvestigacion/modal/evaluadorpropuesta.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "mensaje": f"Error al obtener los datos. {msg}"})

            elif action == 'convocatorias':
                try:
                    convocatorias = ConvocatoriaProyecto.objects.filter(status=True).order_by('-apertura', '-cierre')

                    paging = MiPaginador(convocatorias, 25)
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
                    data['convocatorias'] = page.object_list
                    data['title'] = u'Convocatorias a Proyectos de Investigación'
                    data['enlaceatras'] = "/ges_investigacion?action=convocatorias"

                    return render(request, "adm_proyectoinvestigacion/view.html", data)

                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
            # Fin GET
        else:
            try:
                url_vars = ''
                convocatorias = ConvocatoriaProyecto.objects.filter(status=True).order_by('-apertura', '-cierre')

                paging = MiPaginador(convocatorias, 25)
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
                data['convocatorias'] = page.object_list
                data['title'] = u'Convocatorias a Proyectos de Investigación'
                data['enlaceatras'] = "/ges_investigacion?action=convocatorias"

                return render(request, "adm_proyectoinvestigacion/view.html", data)

            except Exception as ex:
                msg = ex.__str__()
                return HttpResponseRedirect(f"/?info=Error al obtener los datos. {msg}")


def generar_documento_proyecto_sin_nombreintegrantes(proyecto, data):
    ponderacion = proyecto.total_ponderacion_actividades()
    dif = abs(proyecto.montototal - proyecto.presupuesto)
    mesesactividades = proyecto.total_meses_actividades()
    cantidadintegrantes = proyecto.cantidad_integrantes_unemi()

    data['proyecto'] = proyecto
    data['instituciones'] = proyecto.instituciones_proyecto()
    data['directorproyecto'] = proyecto.nombre_director_proyecto()
    data['resultados'] = proyecto.resultados_compromisos()
    data['referenciabib'] = proyecto.referencias_bibliograficas()
    data['ocultarintegrantes'] = True

    # Datos del presupuesto
    listagrupos = []
    grupos_presupuesto = proyecto.presupuesto_grupo_totales()
    for grupo in grupos_presupuesto:
        # ID GRUPO, DESCRIPCION, TOTAL X GRUPO
        listagrupos.append([grupo['id'], grupo['descripcion'], grupo['totalgrupo']])

    datospresupuesto = []
    detalles_presupuesto = proyecto.presupuesto_detallado().filter(valortotal__gt=0)  # .order_by('tiporecurso__orden', 'tiporecurso__id', 'id')
    for detalle in detalles_presupuesto:
        # ID GRUPO, RECURSO, DESCRIPCION, UNIDAD MEDIDA, CANTIDAD, PRECIO, IVA, TOTAL, OBSERVACION

        if 'PASAJES' in detalle.recurso or 'VIÁTICOS' in detalle.recurso:
            if 'PASAJES' in detalle.recurso:
                recurso = 'PASAJES XXXX XXXX XXXX XXXX'
            else:
                recurso = 'VIÁTICOS XXXX XXXX XXXX XXXX'
        else:
            recurso = detalle.recurso

        datospresupuesto.append([
            detalle.tiporecurso.id,
            recurso,
            detalle.descripcion,
            detalle.unidadmedida.nombre,
            detalle.cantidad,
            detalle.valorunitario,
            detalle.valoriva,
            detalle.valortotal,
            detalle.observacion
        ])

    data['datospresupuesto'] = datospresupuesto
    data['listagrupos'] = listagrupos

    # Datos del cronograma de actividades
    listaobjetivos = []
    objetivos_cronograma = proyecto.cronograma_objetivo_totales()
    for objetivo in objetivos_cronograma:
        # Id, descripcion, total actividades, total ponderacion
        listaobjetivos.append([objetivo['id'], objetivo['descripcion'], objetivo['totalactividades'], objetivo['totalponderacion']])

    datoscronograma = []
    detalles_cronograma = proyecto.cronograma_detallado()
    auxid = 0
    secuencia = 0
    totalponderacion = 0
    for detalle in detalles_cronograma:
        secuencia += 1
        totalponderacion += detalle.ponderacion
        if auxid != detalle.objetivo.id:
            secuencia_grupo = 1
            auxid = detalle.objetivo.id
        else:
            secuencia_grupo += 1

        # id objetivo, secuencia, secuencia grupo, actividad, ponderacion, fecha inicio, fecha fin, entregables, responsables
        datoscronograma.append([
            detalle.objetivo.id,
            secuencia,
            secuencia_grupo,
            detalle.actividad,
            detalle.ponderacion,
            detalle.fechainicio,
            detalle.fechafin,
            detalle.entregable if detalle.entregable else detalle.lista_html_entregables(),
            detalle.lista_html_nombres_responsables()
        ])

    data['datoscronograma'] = datoscronograma
    data['listaobjetivos'] = listaobjetivos
    data['totalponderacion'] = totalponderacion

    # Datos de los integrantes
    data['integrantes'] = integrantes = proyecto.integrantes_proyecto_informe()
    data['totalintegrantes'] = integrantes.count()

    # Creacion de los archivos por separado
    directorio = SITE_STORAGE + '/media/proyectoinvestigacion/documentos'
    try:
        os.stat(directorio)
    except:
        os.mkdir(directorio)

    # Archivo de los datos generales del proyecto
    nombrearchivo1 = 'datosinformativos_' + str(proyecto.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
    valida = convert_html_to_pdf(
        'pro_proyectoinvestigacion/inscripcionproyectopdf.html',
        {'pagesize': 'A4', 'data': data},
        nombrearchivo1,
        directorio
    )

    if not valida:
        return "Error al generar documento de los datos principales."

    # Archivo con el presupuesto del proyecto
    nombrearchivo3 = 'presupuesto_' + str(proyecto.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
    valida = convert_html_to_pdf(
        'pro_proyectoinvestigacion/presupuestoproyectopdf.html',
        {'pagesize': 'A4', 'data': data},
        nombrearchivo3,
        directorio
    )

    if not valida:
        return "Error al generar documento del presupuesto."

    # Archivo con el cronograma de actividades del proyecto
    nombrearchivo4 = 'cronograma_' + str(proyecto.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
    valida = convert_html_to_pdf(
        'pro_proyectoinvestigacion/cronogramaproyectopdf.html',
        {'pagesize': 'A4', 'data': data},
        nombrearchivo4,
        directorio
    )

    if not valida:
        return "Error al generar documento del cronograma."

    # # # Archivo con las hojas de vida de los integrantes del proyecto
    # # nombrearchivo5 = 'hojavidaintegrante_' + str(proyecto.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
    # # valida = convert_html_to_pdf(
    # #     'pro_proyectoinvestigacion/hojavidaintegrantepdf.html',
    # #     {'pagesize': 'A4', 'data': data},
    # #     nombrearchivo5,
    # #     directorio
    # # )
    # #
    # # if not valida:
    # #     return JsonResponse(
    # #         {"result": "bad", "mensaje": u"Error al generar documento de las hojas de vida."})

    archivo1 = directorio + "/" + nombrearchivo1

    # # archivo2 = SITE_STORAGE + proyecto.archivoproyecto.url  # Archivo pdf de proyecto cargado por el docente
    archivo3 = directorio + "/" + nombrearchivo3
    archivo4 = directorio + "/" + nombrearchivo4
    # # archivo5 = directorio + "/" + nombrearchivo5
    # archivo6 = SITE_STORAGE + proyecto.archivopresupuesto.url  # Archivo pdf del presupuesto cargado por el docente

    # Leer los archivos
    pdf1Reader = PyPDF2.PdfFileReader(archivo1)
    # # pdf2Reader = PyPDF2.PdfFileReader(archivo2)

    pdf3Reader = PyPDF2.PdfFileReader(archivo3)
    pdf4Reader = PyPDF2.PdfFileReader(archivo4)
    # # pdf5Reader = PyPDF2.PdfFileReader(archivo5)
    # pdf6Reader = PyPDF2.PdfFileReader(archivo6)

    # Crea un nuevo objeto PdfFileWriter que representa un documento PDF en blanco
    pdfWriter = PyPDF2.PdfFileWriter()

    # Recorre todas las páginas del documento 1: Formulario de inscripcion del proyecto
    for pageNum in range(pdf1Reader.numPages):
        pageObj = pdf1Reader.getPage(pageNum)
        pdfWriter.addPage(pageObj)

    # # Recorre todas las páginas del documento 2
    # for pageNum in range(pdf2Reader.numPages):
    #     pageObj = pdf2Reader.getPage(pageNum)
    #     pdfWriter.addPage(pageObj)
    #

    # Recorre todas las páginas del documento 4: Cronograma de actividades
    for pageNum in range(pdf4Reader.numPages):
        pageObj = pdf4Reader.getPage(pageNum)
        pdfWriter.addPage(pageObj)

    # Recorre todas las páginas del documento 3: Presupuesto
    for pageNum in range(pdf3Reader.numPages):
        pageObj = pdf3Reader.getPage(pageNum)
        pdfWriter.addPage(pageObj)

    # # Recorre todas las páginas del documento 6: Presupuesto cargado por el docente
    # for pageNum in range(pdf6Reader.numPages):
    #     pageObj = pdf6Reader.getPage(pageNum)
    #     pdfWriter.addPage(pageObj)

    # # Recorre todas las páginas del documento 5
    # for pageNum in range(pdf5Reader.numPages):
    #     pageObj = pdf5Reader.getPage(pageNum)
    #     pdfWriter.addPage(pageObj)

    # Luego de haberse copiado todas las paginas de todos los documentos, se las escribe en el documento en blanco
    fecha = datetime.now().date()
    hora = datetime.now().time()
    nombrearchivoresultado = 'documentoev' + fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__() + '.pdf'
    pdfOutputFile = open(directorio + "/" + nombrearchivoresultado, "wb")
    pdfWriter.write(pdfOutputFile)

    # Borro los documento individuales creados a exepción del archcivo del proyecto cargado por el docente

    os.remove(archivo1)
    os.remove(archivo3)
    os.remove(archivo4)
    # os.remove(archivo5)

    pdfOutputFile.close()

    # # Actualizo el nombre del documento del proyecto
    # proyecto.archivodocumento = 'proyectoinvestigacion/documentos/' + nombrearchivoresultado
    # proyecto.documentogenerado = True
    # proyecto.archivodocumentofirmado = None
    # proyecto.save(request)
    #
    # # Crea el historial del archivo
    # historialarchivo = ProyectoInvestigacionHistorialArchivo(
    #     proyecto=proyecto,
    #     tipo=8,
    #     archivo=proyecto.archivodocumento
    # )
    # historialarchivo.save(request)
    #
    # return JsonResponse({"result": "ok", "documento": proyecto.archivodocumento.url})
    return {"estado": "ok", "archivo": 'proyectoinvestigacion/documentos/' + nombrearchivoresultado}
