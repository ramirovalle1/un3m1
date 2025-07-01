# -*- coding: UTF-8 -*-
import io
import json
import os
from math import ceil

from bs4 import BeautifulSoup
import xlsxwriter
import PyPDF2
from datetime import time, datetime, timedelta, date
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

from core.firmar_documentos_ec import JavaFirmaEc
from django.core.files import File as DjangoFile
from django.core.files.base import ContentFile
from fitz import fitz

from decorators import secure_module
from investigacion.forms import RegistroPropuestaProyectoInvestigacionForm, ContenidoProyectoInvestigacionForm, \
    PresupuestoProyectoInvestigacionForm, CronogramaActividadProyectoInvestigacionForm, ExternoForm, \
    FinalizaEdicionForm, InformeProyectoForm
from investigacion.funciones import diff_month, periodo_vigente_distributivo_docente_investigacion, FORMATOS_CELDAS_EXCEL, \
    actualizar_permiso_edicion_rubros_presupuesto, aplica_para_director_proyecto, aplica_para_codirector_proyecto, aplica_para_ayudante_investigacion_proyecto, \
    aplica_para_investigador_asociado_investigacion_proyecto, aplica_para_investigador_colaborador_proyecto, mensaje_consideraciones_integrantes, \
    reemplazar_fuente_para_formato_inscripcion, reemplazar_fuente_para_informe, getlastdayofmonth, guardar_historial_archivo_proyectos_investigacion
from investigacion.models import ProyectoInvestigacion, TipoRecursoPresupuesto, ProyectoInvestigacionInstitucion, \
    ProyectoInvestigacionIntegrante, ProyectoInvestigacionRecorrido, ProyectoInvestigacionItemPresupuesto, \
    TIPO_INTEGRANTE, ProyectoInvestigacionObjetivo, TipoResultadoCompromiso, ProyectoInvestigacionResultado, \
    ConvocatoriaProyecto, ConvocatoriaMontoFinanciamiento, ProyectoInvestigacionCronogramaActividad, \
    ProyectoInvestigacionCronogramaResponsable, ProyectoInvestigacionPasajeIntegrante, \
    ProyectoInvestigacionViaticoIntegrante, ProyectoInvestigacionActividadEvidencia, \
    ProyectoInvestigacionCronogramaEntregable, ProyectoInvestigacionHistorialArchivo, \
    ProyectoInvestigacionHistorialActividadEvidencia, ProyectoInvestigacionInforme, \
    ProyectoInvestigacionHistorialInforme, ProyectoInvestigacionInformeActividad, ProyectoInvestigacionInformeAnexo, ProyectoInvestigacionReferenciaBibliografica, ProyectoInvestigacionMovilizacionIntegrante, FUNCION_INTEGRANTE, ProyectoInvestigacionInformeEvideciaPresupuesto, \
    ProyectoInvestigacionInformeEjecucionObjetivo, ProyectoInvestigacionInformeObjetivoResultado, ProyectoInvestigacionInformeCapacitacion, ProyectoInvestigacionInformePublicacion, ProyectoInvestigacionInformeEvento, ProyectoInvestigacionInformeOtroProducto, ProyectoInvestigacionInformeParticipante, \
    ProyectoInvestigacionInformeCambioProblema, ProyectoInvestigacionInformeEquipamiento, ProyectoInvestigacionInformeIndicador, ProyectoInvestigacionInformeInstitucion, ProyectoInvestigacionMovimientoItemPresupuesto, \
    ProyectoInvestigacionProformaItemPresupuesto, ProyectoInvestigacionAvanceActividad, ProyectoInvestigacionDetalleAvanceActividad, TipoDocumento
from sagest.commonviews import obtener_estado_solicitud
from sagest.models import datetime, Banco, DistributivoPersona, UnidadMedida, ExperienciaLaboral, Producto
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible, generar_nombre, email_valido, \
    validar_archivo, null_to_decimal, cuenta_email_disponible_para_envio, fechaletra_corta, contar_palabras, elimina_tildes, remover_caracteres, remover_caracteres_especiales_unicode
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqrcertificado, convert_html_to_pdf, conviert_html_to_pdf
from sga.models import CUENTAS_CORREOS, ActividadConvalidacionPPV, Profesor, Administrativo, Inscripcion, \
    TituloInstitucion, Externo, miinstitucion, Titulo, InstitucionEducacionSuperior, Pais, NivelTitulacion, \
    AreaConocimientoTitulacion, Persona, Titulacion, ArticuloPersonaExterna, PonenciaPersonaExterna, \
    LibroPersonaExterna, ProyectoInvestigacionPersonaExterna, Coordinacion, MESES_CHOICES, RedPersona, Periodo
from django.template import Context
from django.template.loader import get_template

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

    es_docente = persona.es_profesor()
    es_integrante_externo = persona.es_integrante_externo_proyecto_investigacion()

    if not es_docente and not es_integrante_externo:
        return HttpResponseRedirect("/?info=El Módulo está disponible para Docentes y/o Integrantes externos de proyectos.")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addpropuestaproyecto':
            try:
                f = RegistroPropuestaProyectoInvestigacionForm(request.POST)

                if f.is_valid():
                    if not ProyectoInvestigacion.objects.filter(titulo=f.cleaned_data['titulo'], status=True).exclude(estado__valor=44).exists():
                        if f.cleaned_data['montounemi'] > f.cleaned_data['montomaximounemi']:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El valor del campo Monto UNEMI debe ser menor o igual a Máximo a financiar", "showSwal": "True", "swalType": "warning"})

                        if f.cleaned_data['existeinscoejecutora'] == '1':
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

                        # Consulto el estado que voy a asignar
                        estado = obtener_estado_solicitud(3, 1)

                        # Guarda el proyecto
                        proyectoinvestigacion = ProyectoInvestigacion(
                            convocatoria=convocatoria,
                            profesor=persona.profesor(),
                            categoria=None,
                            categoria2=f.cleaned_data['categoria'],
                            titulo=f.cleaned_data['titulo'],
                            areaconocimiento=f.cleaned_data['areaconocimiento'],
                            subareaconocimiento=f.cleaned_data['subareaconocimiento'],
                            subareaespecificaconocimiento=f.cleaned_data['subareaespecificaconocimiento'],
                            lineainvestigacion=f.cleaned_data['lineainvestigacion'],
                            programainvestigacion=f.cleaned_data['programainvestigacion'],
                            industriapriorizada=f.cleaned_data['industriapriorizada'],
                            requiereconvenio=f.cleaned_data['requiereconvenio'],
                            especificaconvenio=f.cleaned_data['especificaconvenio'],
                            requierepermiso=f.cleaned_data['requierepermiso'],
                            especificapermiso=f.cleaned_data['especificapermiso'],
                            tiempomes=f.cleaned_data['tiempomes'],
                            montototal=f.cleaned_data['montototal'],
                            montounemi=f.cleaned_data['montounemi'],
                            montootrafuente=f.cleaned_data['montootrafuente'],
                            tipocobertura=f.cleaned_data['tipocobertura'],
                            grupoinvestigacion=f.cleaned_data['grupoinvestigacion'],
                            estado=estado
                        )

                        proyectoinvestigacion.save(request)

                        # Guardo sublineas de investigacion
                        for sublinea in f.cleaned_data['sublineainvestigacion']:
                            proyectoinvestigacion.sublineainvestigacion.add(sublinea)

                        proyectoinvestigacion.save(request)

                        tipocobertura = int(f.cleaned_data['tipocobertura'])
                        # Si tipo cobertura es zonal guardo las zonas
                        if tipocobertura == 3:
                            for zona in f.cleaned_data['zonas']:
                                proyectoinvestigacion.zonas.add(zona)

                            proyectoinvestigacion.save(request)
                        # Si es provincial guardo las provincias
                        elif tipocobertura == 4:
                            for provincia in f.cleaned_data['provincias']:
                                proyectoinvestigacion.provincias.add(provincia)

                            proyectoinvestigacion.save(request)
                        # Si es local guardo provincia y los cantones
                        elif tipocobertura == 5:
                            proyectoinvestigacion.provincia = f.cleaned_data['provincia']
                            for canton in f.cleaned_data['canton']:
                                proyectoinvestigacion.canton.add(canton)

                            proyectoinvestigacion.requiereparroquia = f.cleaned_data['requiereparroquia']
                            proyectoinvestigacion.parroquia = f.cleaned_data['parroquia']
                            proyectoinvestigacion.save(request)

                        # Guardo institución participante ejecutora
                        institucionproyecto = ProyectoInvestigacionInstitucion(
                            proyecto=proyectoinvestigacion,
                            tipo=1,
                            representante=f.cleaned_data['representanteinsejec'],
                            cedula=f.cleaned_data['cedulainsejec'],
                            telefono=f.cleaned_data['telefonoinsejec'],
                            fax=f.cleaned_data['faxinsejec'],
                            email=f.cleaned_data['emailinsejec'],
                            direccion=f.cleaned_data['direccioninsejec'],
                            paginaweb=f.cleaned_data['paginawebinsejec'],
                            nombre=f.cleaned_data['nombreinsejec']
                        )
                        institucionproyecto.save(request)

                        # Guardo institución participante co-ejecutora en caso de haber marcado la casilla
                        if f.cleaned_data['existeinscoejecutora'] == '1':
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
                        integranteproyecto = ProyectoInvestigacionIntegrante(
                            proyecto=proyectoinvestigacion,
                            funcion=1,
                            tipo=1,
                            persona=persona,
                            profesor=persona.profesor(),
                        )
                        integranteproyecto.save(request)

                        # Creo el recorrido del proyecto
                        recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                                   fecha=datetime.now().date(),
                                                                   observacion='Propuesta de Proyecto en Edición',
                                                                   estado=estado
                                                                   )
                        recorrido.save(request)

                        log(f'{persona} agregó datos generales de propuesta de proyecto de investigación {proyectoinvestigacion}', request, "add")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La propuesta de proyecto de investigación ya ha sido ingresada", "showSwal": "True", "swalType": "warning"})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
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

        elif action == 'editpropuestaproyecto':
            try:
                f = RegistroPropuestaProyectoInvestigacionForm(request.POST)

                if f.is_valid():
                    if not ProyectoInvestigacion.objects.filter(titulo=f.cleaned_data['titulo'], status=True).exclude(estado__valor=44).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        proyectoinvestigacion = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                        if f.cleaned_data['existeinscoejecutora'] == '1':
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

                        # Si tiene estado ERROR en requisitos, o REQUIERE MODIFICACIONES MENORES/MAYORES se debe poner estado EN EDICIÓN
                        if proyectoinvestigacion.estado.valor in [4, 15, 16, 38, 39]:
                            # Consulto el estado que voy a asignar

                            if proyectoinvestigacion.estado.valor == 4:
                                estado = obtener_estado_solicitud(3, 1)
                            elif proyectoinvestigacion.estado.valor == 15:
                                estado = obtener_estado_solicitud(3, 28)
                            elif proyectoinvestigacion.estado.valor == 16:
                                estado = obtener_estado_solicitud(3, 29)
                            elif proyectoinvestigacion.estado.valor == 38:
                                estado = obtener_estado_solicitud(3, 40)
                            else:
                                estado = obtener_estado_solicitud(3, 41)

                            # Actualizo estado
                            proyectoinvestigacion.estado = estado
                            proyectoinvestigacion.save(request)

                            # Creo el recorrido del proyecto
                            recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                                       fecha=datetime.now().date(),
                                                                       observacion=estado.observacion,
                                                                       estado=estado
                                                                       )
                            recorrido.save(request)

                        # Actualizo los datos generales
                        proyectoinvestigacion.categoria2 = f.cleaned_data['categoria']
                        proyectoinvestigacion.titulo = f.cleaned_data['titulo']
                        proyectoinvestigacion.areaconocimiento = f.cleaned_data['areaconocimiento']
                        proyectoinvestigacion.subareaconocimiento = f.cleaned_data['subareaconocimiento']
                        proyectoinvestigacion.subareaespecificaconocimiento = f.cleaned_data['subareaespecificaconocimiento']
                        proyectoinvestigacion.lineainvestigacion = f.cleaned_data['lineainvestigacion']
                        proyectoinvestigacion.programainvestigacion = f.cleaned_data['programainvestigacion']
                        proyectoinvestigacion.industriapriorizada = f.cleaned_data['industriapriorizada']
                        proyectoinvestigacion.requiereconvenio = f.cleaned_data['requiereconvenio']
                        proyectoinvestigacion.especificaconvenio = f.cleaned_data['especificaconvenio']
                        proyectoinvestigacion.requierepermiso = f.cleaned_data['requierepermiso']
                        proyectoinvestigacion.especificapermiso = f.cleaned_data['especificapermiso']
                        proyectoinvestigacion.requiereparroquia = f.cleaned_data['requiereparroquia']
                        proyectoinvestigacion.parroquia = f.cleaned_data['parroquia']
                        proyectoinvestigacion.tiempomes = f.cleaned_data['tiempomes']
                        proyectoinvestigacion.grupoinvestigacion = f.cleaned_data['grupoinvestigacion']
                        proyectoinvestigacion.montototal = f.cleaned_data['montototal']
                        proyectoinvestigacion.montounemi = f.cleaned_data['montounemi']
                        proyectoinvestigacion.montootrafuente = f.cleaned_data['montootrafuente']
                        proyectoinvestigacion.tipocobertura = f.cleaned_data['tipocobertura']
                        proyectoinvestigacion.registrado = False
                        proyectoinvestigacion.verificado = None
                        proyectoinvestigacion.documentogenerado = False
                        proyectoinvestigacion.archivodocumentofirmado = None
                        proyectoinvestigacion.archivodocumentosindatint = None
                        proyectoinvestigacion.estadodocumentofirmado = 1
                        proyectoinvestigacion.estadodatogeneral = 1
                        proyectoinvestigacion.observaciondatogeneral = ""

                        proyectoinvestigacion.save(request)

                        # Actualizo sublineas de investigacion y coordinaciones
                        proyectoinvestigacion.sublineainvestigacion.clear()
                        for sublinea in f.cleaned_data['sublineainvestigacion']:
                            proyectoinvestigacion.sublineainvestigacion.add(sublinea)

                        proyectoinvestigacion.save(request)

                        tipocobertura = int(f.cleaned_data['tipocobertura'])
                        # Si tipo cobertura es nacional guardo las zonas
                        if tipocobertura == 3:
                            proyectoinvestigacion.zonas.clear()
                            for zona in f.cleaned_data['zonas']:
                                proyectoinvestigacion.zonas.add(zona)

                            proyectoinvestigacion.save(request)
                        # Si es provincial guardo las provincias
                        elif tipocobertura == 4:
                            proyectoinvestigacion.provincias.clear()
                            for provincia in f.cleaned_data['provincias']:
                                proyectoinvestigacion.provincias.add(provincia)

                            proyectoinvestigacion.save(request)
                        # Si es local guardo provincia y los cantones
                        elif tipocobertura == 5:
                            proyectoinvestigacion.provincia = f.cleaned_data['provincia']
                            proyectoinvestigacion.canton.clear()
                            for canton in f.cleaned_data['canton']:
                                proyectoinvestigacion.canton.add(canton)

                            proyectoinvestigacion.save(request)

                        # Elimino las instituciones co ejecutoras
                        for institucioneli in institucioneseliminadas:
                            institucioneli = ProyectoInvestigacionInstitucion.objects.get(pk=int(institucioneli['idinstitucion']))
                            institucioneli.status = False
                            institucioneli.save(request)

                        # Guardo institución participante co-ejecutora en caso de haber marcado la casilla
                        if f.cleaned_data['existeinscoejecutora'] == '1':
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

                        log(f'{persona} editó datos generales de propuesta de proyecto de investigación {proyectoinvestigacion}', request, "edit")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La propuesta de proyecto de investigación ya ha sido ingresada", "showSwal": "True", "swalType": "warning"})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'delpropuestaproyecto':
            try:
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Elimino el proyecto
                proyecto.status = False
                proyecto.save(request)

                # Elimino el recorrido
                for recorrido in proyecto.proyectoinvestigacionrecorrido_set.filter(status=True):
                    recorrido.status = False
                    recorrido.save(request)

                # Elimino historial de archivos
                for historial in proyecto.proyectoinvestigacionhistorialarchivo_set.filter(status=True):
                    historial.status = False
                    historial.save(request)

                # Elimino las instituciones participantes
                for institucion in proyecto.proyectoinvestigacioninstitucion_set.filter(status=True):
                    institucion.status = False
                    institucion.save(request)

                # Elimino los objetivos
                for objetivo in proyecto.proyectoinvestigacionobjetivo_set.filter(status=True):
                    objetivo.status = False
                    objetivo.save(request)

                # Elimino los resultados
                for resultado in proyecto.proyectoinvestigacionresultado_set.filter(status=True):
                    resultado.status = False
                    resultado.save(request)

                # Elimino los integrantes
                integrantes = proyecto.integrantes_proyecto()
                for integrante in integrantes:
                    integrante.status = False
                    integrante.save(request)

                # Elimino el cronograma
                for actividad in proyecto.cronograma_actividades():
                    actividad.status = False
                    actividad.save(request)

                    # Elimino responsables de actividad
                    for responsable in actividad.lista_responsables():
                        responsable.status = False
                        responsable.save(request)

                    # Elimino los entregables de la actividad
                    for entregable in actividad.lista_entregables():
                        entregable.status = False
                        entregable.save(request)

                # Elimino el presupuesto
                for itempresupuesto in proyecto.presupuesto_detallado():
                    itempresupuesto.status = False
                    itempresupuesto.save(request)

                # Elimino pasajes
                for pasaje in proyecto.proyectoinvestigacionpasajeintegrante_set.filter(status=True):
                    pasaje.status = False
                    pasaje.save(request)

                # Elimino viáticos
                for viatico in proyecto.proyectoinvestigacionviaticointegrante_set.filter(status=True):
                    viatico.status = False
                    viatico.save(request)

                log(u'%s eliminó propuesta de proyecto de investigación [ %s ]' % (persona, proyecto), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al eliminar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'habilitaredicion':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto el proyecto
                proyectoinvestigacion = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que no hayan realizado la revisión en Coordinación de Investigación
                if proyectoinvestigacion.estado.valor not in [2, 5]:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede habilitar la edición debido a que la propuesta ya ha sido revisada", "showSwal": "True", "swalType": "warning"})

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
                                                           observacion='Propuesta de Proyecto en Edición',
                                                           estado=estadopropuesta
                                                           )
                recorrido.save(request)

                log(u'%s habilitó edición de la propuesta de proyecto de investigación: %s' % (persona, proyectoinvestigacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addintegrante':
            try:
                if not 'idproyecto' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

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

                # Validar el límite de integrantes
                if funcionpersona != 5:
                    if proyectoinvestigacion.cantidad_integrantes_unemi() >= convocatoria.maxintegranteu:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se pueden agregar más integrantes <b>UNEMI</b> al proyecto", "showSwal": "True", "swalType": "warning"})
                else:
                    if proyectoinvestigacion.cantidad_integrantes_externos() >= convocatoria.maxintegrantee:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se pueden agregar más integrantes <b>EXTERNOS</b> al proyecto", "showSwal": "True", "swalType": "warning"})

                profesori = inscripcioni = administrativoi = externoi = None
                if tipopersona == 1:
                    profesori = Profesor.objects.get(pk=personaintegrante)
                    persona_id = profesori.persona.id
                elif tipopersona == 2:
                    inscripcioni = Inscripcion.objects.get(pk=personaintegrante)
                    persona_id = inscripcioni.persona.id
                elif tipopersona == 3:
                    administrativoi = Administrativo.objects.get(pk=personaintegrante)
                    persona_id = administrativoi.persona.id
                else:
                    externoi = Externo.objects.get(pk=personaintegrante)
                    persona_id = externoi.persona.id

                # Verificar que no haya sido registrado previamente
                if proyectoinvestigacion.proyectoinvestigacionintegrante_set.values("id").filter(status=True, persona_id=persona_id).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La persona ya consta como integrante del proyecto", "showSwal": "True", "swalType": "warning"})

                # Verifico que la persona no sea el director del proyecto
                if proyectoinvestigacion.proyectoinvestigacionintegrante_set.values("id").filter(status=True, persona_id=persona_id, funcion=1).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se puede agregar al integrante debido a que consta como <b>DIRECTOR</b>", "showSwal": "True", "swalType": "warning"})

                # Si es funcion co-director validar que pueda aplicar
                if funcionpersona == 2:
                    if proyectoinvestigacion.proyectoinvestigacionintegrante_set.values("id").filter(status=True, funcion=2, tiporegistro__in=[1, 3, 4]).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Ya existe otro integrante del proyecto con el rol de <b>CO-DIRECTOR</b>", "showSwal": "True", "swalType": "warning"})

                    aplica = aplica_para_codirector_proyecto(profesori, convocatoria)
                    if not aplica['puedeaplicar']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": aplica['mensaje'], "showSwal": "True", "swalType": "warning"})
                elif funcionpersona == 4: # Si la función es ayudante de investigación validar que aplique
                    aplica = aplica_para_ayudante_investigacion_proyecto(inscripcioni, convocatoria)
                    if not aplica['puedeaplicar']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": aplica['mensaje'], "showSwal": "True", "swalType": "warning"})
                elif funcionpersona == 3: # Si la función es investigador asociado validar que aplique
                    aplica = aplica_para_investigador_asociado_investigacion_proyecto(profesori.persona if profesori else administrativoi.persona, convocatoria)
                    if not aplica['puedeaplicar']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": aplica['mensaje'], "showSwal": "True", "swalType": "warning"})
                elif funcionpersona == 5: # Si la funcion es investigador colaborador
                    aplica = aplica_para_investigador_colaborador_proyecto(externoi.persona, convocatoria)
                    if not aplica['puedeaplicar']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": aplica['mensaje'], "showSwal": "True", "swalType": "warning"})

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

                if proyectoinvestigacion.estadointegrante == 4:
                    proyectoinvestigacion.estadointegrante = 1
                    proyectoinvestigacion.observacionintegrante = ''
                    proyectoinvestigacion.save(request)

                # Si tiene estado ERROR en requisitos, o REQUIERE MODIFICACIONES MENORES/MAYORES se debe poner estado EN EDICIÓN
                if proyectoinvestigacion.estado.valor in [4, 15, 16, 38, 39]:
                    # Consulto el estado que voy a asignar
                    if proyectoinvestigacion.estado.valor == 4:
                        estado = obtener_estado_solicitud(3, 1)
                    elif proyectoinvestigacion.estado.valor == 15:
                        estado = obtener_estado_solicitud(3, 28)
                    elif proyectoinvestigacion.estado.valor == 16:
                        estado = obtener_estado_solicitud(3, 29)
                    elif proyectoinvestigacion.estado.valor == 38:
                        estado = obtener_estado_solicitud(3, 40)
                    else:
                        estado = obtener_estado_solicitud(3, 41)

                    # Actualizo estado
                    proyectoinvestigacion.estado = estado
                    proyectoinvestigacion.registrado = False
                    proyectoinvestigacion.verificado = None
                    proyectoinvestigacion.documentogenerado = False
                    proyectoinvestigacion.archivodocumentofirmado = None
                    proyectoinvestigacion.archivodocumentosindatint = None
                    proyectoinvestigacion.estadodocumentofirmado = 1
                    proyectoinvestigacion.save(request)

                    # Creo el recorrido del proyecto
                    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                               fecha=datetime.now().date(),
                                                               observacion=estado.observacion,
                                                               estado=estado
                                                               )
                    recorrido.save(request)

                log(f'{persona} agregó integrante {integranteproyecto} a proyecto de investigación {proyectoinvestigacion}', request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editintegrante':
            try:
                if not 'idproyecto' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                integranteproyecto = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.POST['idi'])))
                proyectoinvestigacion = integranteproyecto.proyecto
                funcionpersona = int(request.POST['funcionpersona'])

                # Si es función de co-director validar que otro integrante no sea co-director y/o no esté participando en otro proyecto con esta función
                if funcionpersona == 2:
                    if proyectoinvestigacion.proyectoinvestigacionintegrante_set.values("id").filter(status=True, funcion=2, tiporegistro__in=[1, 3, 4]).exclude(persona_id=integranteproyecto.persona_id).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Ya existe otro integrante del proyecto con el rol de <b>CO-DIRECTOR</b>", "showSwal": "True", "swalType": "warning"})

                    aplica = aplica_para_codirector_proyecto(integranteproyecto.profesor, proyectoinvestigacion.convocatoria)
                    if not aplica['puedeaplicar']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": aplica['mensaje'], "showSwal": "True", "swalType": "warning"})

                integranteproyecto.funcion = funcionpersona
                integranteproyecto.observacion = ''
                integranteproyecto.estadoacreditado = 1 if funcionpersona in [1, 2] else 4
                integranteproyecto.save(request)

                if proyectoinvestigacion.estadointegrante == 4:
                    proyectoinvestigacion.estadointegrante = 1
                    proyectoinvestigacion.observacionintegrante = ''
                    proyectoinvestigacion.save(request)

                # Si tiene estado ERROR en requisitos, o REQUIERE MODIFICACIONES MENORES/MAYORES se debe poner estado EN EDICIÓN
                if proyectoinvestigacion.estado.valor in [4, 15, 16, 38, 39]:
                    # Consulto el estado que voy a asignar
                    if proyectoinvestigacion.estado.valor == 4:
                        estado = obtener_estado_solicitud(3, 1)
                    elif proyectoinvestigacion.estado.valor == 15:
                        estado = obtener_estado_solicitud(3, 28)
                    elif proyectoinvestigacion.estado.valor == 16:
                        estado = obtener_estado_solicitud(3, 29)
                    elif proyectoinvestigacion.estado.valor == 38:
                        estado = obtener_estado_solicitud(3, 40)
                    else:
                        estado = obtener_estado_solicitud(3, 41)

                    # Actualizo estado
                    proyectoinvestigacion.estado = estado
                    proyectoinvestigacion.registrado = False
                    proyectoinvestigacion.verificado = None
                    proyectoinvestigacion.documentogenerado = False
                    proyectoinvestigacion.archivodocumentofirmado = None
                    proyectoinvestigacion.archivodocumentosindatint = None
                    proyectoinvestigacion.estadodocumentofirmado = 1
                    proyectoinvestigacion.save(request)

                    # Creo el recorrido del proyecto
                    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                               fecha=datetime.now().date(),
                                                               observacion=estado.observacion,
                                                               estado=estado
                                                               )
                    recorrido.save(request)

                log(u'%s editó integrante a proyecto de investigación: %s - %s' % (persona, integranteproyecto.proyecto, integranteproyecto), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'delintegrante':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                integrante = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.POST['id'])))
                integrante.status = False
                integrante.save(request)

                proyectoinvestigacion = integrante.proyecto

                if proyectoinvestigacion.estadointegrante == 4:
                    proyectoinvestigacion.estadointegrante = 1
                    proyectoinvestigacion.observacionintegrante = ''
                    proyectoinvestigacion.save(request)

                # Si tiene estado ERROR en requisitos, o REQUIERE MODIFICACIONES MENORES/MAYORES se debe poner estado EN EDICIÓN

                if proyectoinvestigacion.estado.valor in [4, 15, 16, 38, 39]:
                    # Consulto el estado que voy a asignar

                    if proyectoinvestigacion.estado.valor == 4:
                        estado = obtener_estado_solicitud(3, 1)
                    elif proyectoinvestigacion.estado.valor == 15:
                        estado = obtener_estado_solicitud(3, 28)
                    elif proyectoinvestigacion.estado.valor == 16:
                        estado = obtener_estado_solicitud(3, 29)
                    elif proyectoinvestigacion.estado.valor == 38:
                        estado = obtener_estado_solicitud(3, 40)
                    else:
                        estado = obtener_estado_solicitud(3, 41)

                    # Actualizo estado
                    proyectoinvestigacion.estado = estado
                    proyectoinvestigacion.registrado = False
                    proyectoinvestigacion.verificado = None
                    proyectoinvestigacion.documentogenerado = False
                    proyectoinvestigacion.archivodocumentofirmado = None
                    proyectoinvestigacion.archivodocumentosindatint = None
                    proyectoinvestigacion.estadodocumentofirmado = 1
                    proyectoinvestigacion.save(request)

                    # Creo el recorrido del proyecto
                    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                               fecha=datetime.now().date(),
                                                               observacion=estado.observacion,
                                                               estado=estado
                                                               )
                    recorrido.save(request)

                log(f'{persona} eliminó integrante {integrante} de proyecto de investigación', request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al eliminar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addexterno':
            try:
                from sga.models import PerfilUsuario
                if not 'idp' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                f = ExternoForm(request.POST)

                if f.is_valid():
                    if not f.cleaned_data['cedula'] and not f.cleaned_data['pasaporte']:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Ingrese número de cédula o pasaporte", "showSwal": "True", "swalType": "warning"})

                    # Verifica si existe la persona
                    nuevo = True
                    if f.cleaned_data['cedula']:
                        personas = Persona.objects.filter(Q(cedula=f.cleaned_data['cedula'])|Q(pasaporte=f.cleaned_data['cedula']), status=True)
                        if personas:
                            nuevo = False
                            if personas.count() > 1:
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La persona tiene más de un registro en la base de datos", "showSwal": "True", "swalType": "warning"})
                            else:
                                personaexterna = personas[0]

                    if f.cleaned_data['pasaporte']:
                        personas = Persona.objects.filter(Q(cedula=f.cleaned_data['pasaporte'])|Q(pasaporte=f.cleaned_data['pasaporte']), status=True)
                        if personas:
                            nuevo = False
                            if personas.count() > 1:
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La persona tiene más de un registro en la base de datos", "showSwal": "True", "swalType": "warning"})
                            else:
                                personaexterna = personas[0]

                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idp'])))

                    # Validar el limite de integrantes externos para el proyecto
                    if proyecto.cantidad_integrantes_externos() >= proyecto.convocatoria.maxintegrantee:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se pueden agregar más integrantes EXTERNOS al proyecto", "showSwal": "True", "swalType": "warning"})

                    if nuevo:
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
                        log(f'{persona} agregó persona externa: {personaexterna}', request, "add")
                    else:
                        # Actualizo la persona
                        personaexterna.nacimiento = f.cleaned_data['nacimiento']
                        personaexterna.sexo = f.cleaned_data['sexo']
                        personaexterna.nacionalidad = f.cleaned_data['nacionalidad'].strip().upper()
                        personaexterna.email = f.cleaned_data['email'].strip().lower()
                        personaexterna.telefono = f.cleaned_data['telefono'].strip()
                        personaexterna.save(request)

                        # Si no hay externo lo creo sino actualizo
                        if not Externo.objects.filter(persona=personaexterna, status=True).exists():
                            # Guardo externo
                            externo = Externo(
                                persona=personaexterna,
                                nombrecomercial='',
                                institucionlabora=f.cleaned_data['institucionlabora'],
                                cargodesempena=f.cleaned_data['cargodesempena']
                            )
                        else:
                            externo = Externo.objects.get(persona=personaexterna, status=True)
                            externo.institucionlabora = f.cleaned_data['institucionlabora'].strip().upper()
                            externo.cargodesempena = f.cleaned_data['cargodesempena'].strip().upper()

                        externo.save(request)

                        if not PerfilUsuario.objects.values("id").filter(persona=externo.persona, externo=externo).exists():
                            personaexterna.crear_perfil(externo=externo)
                            personaexterna.mi_perfil()

                        log(f'{persona} editó persona externa: {personaexterna}', request, "edit")

                    # Asigno la persona externa al proyecto con la función que cumple
                    integranteproyecto = ProyectoInvestigacionIntegrante(
                        proyecto=proyecto,
                        funcion=5,
                        tipo=4,
                        persona_id=personaexterna.id,
                        profesor_id=None,
                        inscripcion_id=None,
                        administrativo_id=None,
                        externo_id=externo.id,
                        estadoacreditado=4
                    )
                    integranteproyecto.save(request)

                    log(f'{persona} agregó integrante al proyecto: {proyecto} - {personaexterna}', request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    x = f.errors
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

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

                    log(f'{persona} editó persona externa {personaexterna}', request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

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

        elif action == 'editcontenidoproyecto':
            try:
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                objetivoseliminados = json.loads(request.POST['lista_items1'])
                resultadoseliminados = json.loads(request.POST['lista_items2'])
                referenciaseliminadas = json.loads(request.POST['lista_items3'])

                # Validar las cantidades de palabras
                if '<img' in request.POST['resumenpropuesta'].strip():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"El Resumen de la propuesta no debe contener imágenes en el contenido", "showSwal": "True", "swalType": "warning"})

                LIMITE_PALABRAS = 500 # 500
                totalpalabras = contar_palabras(request.POST['resumenpropuesta'])
                if totalpalabras > LIMITE_PALABRAS:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El valor del campo Resumen de la propuesta debe contener máximo " + str(LIMITE_PALABRAS) + " palabras. Usted ha ingresado un total de " + str(totalpalabras) + " palabras", "showSwal": "True", "swalType": "warning"})

                if '<img' in request.POST['formulacionproblema'].strip():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"La formulación del problema no debe contener imágenes en el contenido", "showSwal": "True", "swalType": "warning"})

                LIMITE_PALABRAS = 100 # 100
                totalpalabras = contar_palabras(request.POST['formulacionproblema'])
                if totalpalabras > LIMITE_PALABRAS:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El valor del campo Formulación del problema debe contener máximo " + str(LIMITE_PALABRAS) + " palabras. Usted ha ingresado un total de " + str(totalpalabras) + " palabras", "showSwal": "True", "swalType": "warning"})

                if '<img' in request.POST['objetivogeneral'].strip():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"El objetivo general no debe contener imágenes en el contenido", "showSwal": "True", "swalType": "warning"})

                if '<img' in request.POST['justificacion'].strip():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"La justificación no debe contener imágenes en el contenido", "showSwal": "True", "swalType": "warning"})

                LIMITE_PALABRAS = 300  # 300
                totalpalabras = contar_palabras(request.POST['justificacion'])
                if totalpalabras > LIMITE_PALABRAS:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El valor del campo Justificación debe contener máximo " + str(LIMITE_PALABRAS) + " palabras. Usted ha ingresado un total de " + str(totalpalabras) + " palabras", "showSwal": "True", "swalType": "warning"})

                if '<img' in request.POST['estadoarte'].strip():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"El estado del arte no debe contener imágenes en el contenido", "showSwal": "True", "swalType": "warning"})

                LIMITE_PALABRAS = 1000  # 1000
                totalpalabras = contar_palabras(request.POST['estadoarte'])
                if totalpalabras > LIMITE_PALABRAS:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El valor del campo Estado del arte debe contener máximo " + str(LIMITE_PALABRAS) + " palabras. Usted ha ingresado un total de " + str(totalpalabras) + " palabras", "showSwal": "True", "swalType": "warning"})

                if '<img' in request.POST['metodologia'].strip():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"La metodología no debe contener imágenes en el contenido", "showSwal": "True", "swalType": "warning"})

                LIMITE_PALABRAS = 2500  # PASÓ DE 1000 A 2500 según e-mail 27-03-2023 de la coordinación de investigación
                totalpalabras = contar_palabras(request.POST['metodologia'])
                if totalpalabras > LIMITE_PALABRAS:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El valor del campo Metodología debe contener máximo " + str(LIMITE_PALABRAS) + " palabras. Usted ha ingresado un total de " + str(totalpalabras) + " palabras", "showSwal": "True", "swalType": "warning"})

                if not request.POST['impactosocial'] and not request.POST['impactocientifico'] and not request.POST['impactoeconomico'] and not request.POST['impactopolitico'] and not request.POST['otroimpacto']:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Ingrese al menos uno de los impactos solicitados", "showSwal": "True", "swalType": "warning"})

                f = ContenidoProyectoInvestigacionForm(request.POST)
                if f.is_valid():
                    # Obtengo los valores de los arrays de objetivos específicos del formulario
                    idsobjetivosepecificos = request.POST.getlist('idobjetivoespecifico[]')
                    objetivosepecificos = request.POST.getlist('objetivoespecifico[]')

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
                    descripcionestiporesultado = request.POST.getlist('descripciontiporesultado[]')

                    # Actualizo los campos del proyecto
                    fuente = "Berlin Sans FB Demi"
                    tamanio = "14"
                    proyecto.resumenpropuesta = reemplazar_fuente_para_formato_inscripcion(request.POST['resumenpropuesta'].strip(), fuente, tamanio)
                    proyecto.formulacionproblema = reemplazar_fuente_para_formato_inscripcion(request.POST['formulacionproblema'].strip(), fuente, tamanio)
                    proyecto.objetivogeneral = reemplazar_fuente_para_formato_inscripcion(request.POST['objetivogeneral'].strip(), fuente, tamanio)
                    proyecto.justificacion = reemplazar_fuente_para_formato_inscripcion(request.POST['justificacion'].strip(), fuente, tamanio)
                    proyecto.estadoarte = reemplazar_fuente_para_formato_inscripcion(request.POST['estadoarte'].strip(), fuente, tamanio)
                    proyecto.metodologia = reemplazar_fuente_para_formato_inscripcion(request.POST['metodologia'].strip(), fuente, tamanio)
                    proyecto.impactosocial = request.POST['impactosocial']
                    proyecto.impactocientifico = request.POST['impactocientifico']
                    proyecto.impactoeconomico = request.POST['impactoeconomico']
                    proyecto.impactopolitico = request.POST['impactopolitico']
                    proyecto.otroimpacto = request.POST['otroimpacto']
                    proyecto.registrado = False
                    proyecto.verificado = None
                    proyecto.documentogenerado = False
                    proyecto.archivodocumentofirmado = None
                    proyecto.archivodocumentosindatint = None
                    proyecto.estadodocumentofirmado = 1
                    proyecto.estadocontenido = 1
                    proyecto.observacioncontenido = ''
                    proyecto.save(request)

                    # Elimino los detalles de objetivos que fueron borrados en el formulario
                    for objetivoe in objetivoseliminados:
                        objetivoe = ProyectoInvestigacionObjetivo.objects.get(pk=int(objetivoe['idobjetivo']))
                        objetivoe.status = False
                        objetivoe.save(request)

                    # Guardo los objetivos específicos
                    for idobjetivoespecifico, objetivoespecifico in zip(idsobjetivosepecificos, objetivosepecificos):
                        # Nuevo detalle
                        if int(idobjetivoespecifico) == 0:
                            objetivoe = ProyectoInvestigacionObjetivo(
                                proyecto=proyecto,
                                descripcion=objetivoespecifico,
                                estadocumplimiento=1
                            )
                        else:
                            objetivoe = ProyectoInvestigacionObjetivo.objects.get(pk=int(idobjetivoespecifico))
                            objetivoe.descripcion = objetivoespecifico

                        objetivoe.save(request)

                    # Elimino los detalles de resultados/compromisos que fueron borrados en el formulario
                    for resultadoe in resultadoseliminados:
                        resultadoe = ProyectoInvestigacionResultado.objects.get(pk=int(resultadoe['idresultado']))
                        resultadoe.status = False
                        resultadoe.save(request)

                    # Guardo los resultados de aquellos items tipo registro E: Existentes en tabla maestra de TipoResultadoCompromiso

                    # Actualizo los items marcados / desmarcados
                    for idresultado, tiporegistro, idtiporesultado in zip(idsresultadocompromiso, tiposregistro, idstiporesultado):
                        if int(idresultado) == 0 and int(idtiporesultado) == 0:
                            break

                        marcado = idtiporesultado in marcados

                        # Nuevo
                        if int(idresultado) == 0:
                            resultadoproyecto = ProyectoInvestigacionResultado(
                                proyecto=proyecto,
                                resultado_id=idtiporesultado,
                                marcado=marcado
                            )
                        else:
                            resultadoproyecto = ProyectoInvestigacionResultado.objects.get(pk=int(idresultado))
                            resultadoproyecto.marcado = marcado

                        resultadoproyecto.save(request)

                    # Guardo los resultados de aquellos items tipo N: no existentes en tabla maestra de TipoResultadoCompromiso
                    for idtipo, descripcion in zip(idstiporesultadonofijo, descripcionestiporesultado):
                        # Nuevo registro
                        if int(idtipo) == 0:
                            # Creo el registro de TipoResultadoCompromiso
                            tiporesultado = TipoResultadoCompromiso(
                                descripcion=descripcion,
                                numero=0,
                                fijo=False,
                                obligatorio=True
                            )
                            tiporesultado.save(request)

                            # Guardo el resultado del proyecto
                            resultadoproyecto = ProyectoInvestigacionResultado(
                                proyecto=proyecto,
                                resultado=tiporesultado,
                                marcado=True
                            )
                            resultadoproyecto.save(request)
                        else:
                            tiporesultado = TipoResultadoCompromiso.objects.get(pk=int(idtipo))
                            tiporesultado.descripcion = descripcion
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
                                descripcion=referencia
                            )
                        else:
                            referenciabib = ProyectoInvestigacionReferenciaBibliografica.objects.get(pk=int(idreferencia))
                            referenciabib.descripcion = referencia

                        referenciabib.save(request)

                    # Si tiene estado ERROR en requisitos, o REQUIERE MODIFICACIONES MENORES/MAYORES se debe poner estado EN EDICIÓN
                    if proyecto.estado.valor in [4, 15, 16, 38, 39]:
                        # Consulto el estado que voy a asignar

                        if proyecto.estado.valor == 4:
                            estado = obtener_estado_solicitud(3, 1)
                        elif proyecto.estado.valor == 15:
                            estado = obtener_estado_solicitud(3, 28)
                        elif proyecto.estado.valor == 16:
                            estado = obtener_estado_solicitud(3, 29)
                        elif proyecto.estado.valor == 38:
                            estado = obtener_estado_solicitud(3, 40)
                        else:
                            estado = obtener_estado_solicitud(3, 41)

                        # Actualizo estado

                        proyecto.estado = estado
                        proyecto.save(request)

                        # Creo el recorrido del proyecto
                        recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                   fecha=datetime.now().date(),
                                                                   observacion=estado.observacion,
                                                                   estado=estado
                                                                   )
                        recorrido.save(request)

                    log(f'{persona} editó contenido de propuesta de proyecto de investigación {proyecto}', request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
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
                aplicaproforma = tiporecurso.aplica_proforma()

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

                # Actualizo el presupuesto en el proyecto y otros campos
                proyecto.presupuesto = proyecto.total_general_detalle_presupuesto()
                proyecto.estadopresupuesto = 1
                proyecto.observacionpresupuesto = ''
                proyecto.save(request)

                # Actualizo la solicitud de permiso en caso de estar vigente
                actualizar_permiso_edicion_rubros_presupuesto(proyecto, 1, 1, request)

                # Cargo la sección del detalle para el tipo de recurso
                data['tiporecurso'] = tiporecurso
                data['aplicaproforma'] = aplicaproforma
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
                aplicaproforma = tiporecurso.aplica_proforma()

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

                    # Actualizo el presupuesto en el proyecto y otros campos
                    proyecto.presupuesto = proyecto.total_general_detalle_presupuesto()
                    proyecto.estadopresupuesto = 1
                    proyecto.observacionpresupuesto = ''
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
                        tipomovimiento = 3  # Aumento
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
                    permiso = proyecto.permiso_edicion_vigente(1, 1)
                    new_file = ContentFile(permiso.archivo.file.read())
                    new_file.name = generar_nombre("actrubropresupuesto", "actrubropresupuesto.pdf")

                    # Actualizar movimiento
                    movimientorubro.fechadocmodipres = permiso.inicio
                    movimientorubro.archivodocmodipres = new_file
                    movimientorubro.save(request)

                # Si no está EN EJECUCIÓN
                if proyecto.estado.valor != 20:
                    # Si el estado del proyecto NO ES ACEPTADO
                    if proyecto.estado.valor != 13:
                        proyecto.registrado = False
                        proyecto.verificado = None
                        proyecto.documentogenerado = False
                        proyecto.archivodocumentofirmado = None
                        proyecto.archivodocumentosindatint = None
                        proyecto.estadodocumentofirmado = 1

                proyecto.save(request)

                # Si tiene estado ERROR en requisitos, o REQUIERE MODIFICACIONES MENORES/MAYORES se debe poner estado EN EDICIÓN
                if proyecto.estado.valor in [4, 15, 16, 38, 39]:
                    # Consulto el estado que voy a asignar

                    if proyecto.estado.valor == 4:
                        estado = obtener_estado_solicitud(3, 1)
                    elif proyecto.estado.valor == 15:
                        estado = obtener_estado_solicitud(3, 28)
                    elif proyecto.estado.valor == 16:
                        estado = obtener_estado_solicitud(3, 29)
                    elif proyecto.estado.valor == 38:
                        estado = obtener_estado_solicitud(3, 40)
                    else:
                        estado = obtener_estado_solicitud(3, 41)

                    # Actualizo estado
                    proyecto.estado = estado
                    proyecto.save(request)

                    # Creo el recorrido del proyecto
                    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                               fecha=datetime.now().date(),
                                                               observacion=estado.observacion,
                                                               estado=estado
                                                               )
                    recorrido.save(request)

                # Actualizo la solicitud de permiso en caso de estar vigente
                actualizar_permiso_edicion_rubros_presupuesto(proyecto, 1, 1, request)

                # Cargo la sección del detalle para el tipo de recurso
                data['tiporecurso'] = tiporecurso
                data['aplicaproforma'] = aplicaproforma
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

        elif action == 'subirproformadetalle':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                itempresupuesto = ProyectoInvestigacionItemPresupuesto.objects.get(pk=int(encrypt(request.POST['id'])))
                proyecto = itempresupuesto.proyecto

                if itempresupuesto:
                    # Obtener los valores de los detalles del formulario
                    nfilas_ca_anexo = json.loads(request.POST['lista_items1']) if 'lista_items1' in request.POST else []  # Números de filas que tienen lleno el campo archivo en detalle de anexos
                    nfilas_anexo = request.POST.getlist('nfila_anexo[]')  # Todos los número de filas del detalle de evidencias de anexo
                    idsreganexos = request.POST.getlist('idreganexo[]')  # Todos los ids de detalle de anexos
                    descripciones_anexos = request.POST.getlist('descripcion_anexo[]')  # Todas las descripciones detalle anexos
                    archivos_anexos = request.FILES.getlist('archivo_anexo[]')  # Todos los archivos detalle anexos
                    anexos_elim = json.loads(request.POST['lista_items2']) if 'lista_items2' in request.POST else [] # Ids registros de anexos borrados

                    # Valido los archivos cargados de detalle de anexos
                    for nfila, archivo in zip(nfilas_ca_anexo, archivos_anexos):
                        descripcionarchivo = 'Anexos'
                        resp = validar_archivo(descripcionarchivo, archivo, variable_valor("TIPOS_PROFORMAS_PROYECTOS_INV"), variable_valor("TAMANIO_PROFORMAS_PROYECTOS_INV"))
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "{} en la fila # {}".format(resp["mensaje"], nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                    # Guarda las proformas del rubro
                    for idreg, nfila, descripcion in zip(idsreganexos, nfilas_anexo, descripciones_anexos):
                        # Si es registro nuevo
                        if int(idreg) == 0:
                            proformarubro = ProyectoInvestigacionProformaItemPresupuesto(
                                itempresupuesto=itempresupuesto,
                                descripcion=descripcion.strip(),
                            )
                        else:
                            proformarubro = ProyectoInvestigacionProformaItemPresupuesto.objects.get(pk=idreg)
                            proformarubro.descripcion = descripcion.strip()

                        proformarubro.save(request)

                        # Guardo el archivo del detalle
                        for nfilaarchi, archivo in zip(nfilas_ca_anexo, archivos_anexos):
                            # Si la fila de la descripcion es igual a la fila que contiene archivo
                            if int(nfilaarchi['nfila']) == int(nfila):
                                # actualizo campo archivo del registro creado
                                archivoreg = archivo
                                archivoreg._name = generar_nombre("proforma", archivoreg._name)
                                proformarubro.archivo = archivoreg
                                proformarubro.save(request)
                                break

                    # Elimino detalles de anexos
                    if anexos_elim:
                        for registro in anexos_elim:
                            proformarubro = ProyectoInvestigacionProformaItemPresupuesto.objects.get(pk=registro['idreg'])
                            proformarubro.status = False
                            proformarubro.save(request)

                    # Actualizar el proyecto
                    proyecto.registrado = False
                    proyecto.verificado = None
                    proyecto.documentogenerado = False
                    proyecto.archivodocumentofirmado = None
                    proyecto.archivodocumentosindatint = None
                    proyecto.estadodocumentofirmado = 1
                    proyecto.save(request)

                    log(f'{persona} actualizó proformas del rubro del presupuesto {itempresupuesto}', request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El rubro del presupuesto no existe", "showSwal": "True", "swalType": "warning"})
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

                # Actualizo el presupuesto en el proyecto y otros campos
                proyecto.presupuesto = proyecto.total_general_detalle_presupuesto()
                proyecto.estadopresupuesto = 1
                proyecto.observacionpresupuesto = ''
                proyecto.save(request)

                # Actualizo la solicitud de permiso en caso de estar vigente
                actualizar_permiso_edicion_rubros_presupuesto(proyecto, 1, 1, request)

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

                # Guardo la actividad del cronorama
                actividadcronograma = ProyectoInvestigacionCronogramaActividad(
                    objetivo=objetivo,
                    actividad=request.POST['actividad'].strip(),
                    ponderacion=request.POST['ponderacion'],
                    fechainicio=fechainicio,
                    fechafin=fechafin,
                    entregable=request.POST['entregable'].strip(),
                    evidenciacontrolinforme=request.POST['evidenciacontrolinforme'].strip(),
                    observaciongeneral=request.POST['observaciongeneral'].strip()
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

                # Actualizo estado de revisión del cronograma
                if not proyecto.fase_aprobacion_superada():
                    proyecto.estadocronogramarev = 1
                    proyecto.observacioncronograma = ''
                    proyecto.save(request)

                # Actualizo el proyecto si el estado del cronograma es NOVEDAD
                if proyecto.estadocronograma == 4:
                    proyecto.observacion = ""
                    proyecto.estadocronograma = 1
                    proyecto.save(request)

                # Actualizo la solicitud de permiso en caso de estar vigente
                actualizar_permiso_edicion_rubros_presupuesto(proyecto, 2, 1, request)

                # Cargo la sección del detalle de actividades para el objetivo
                data['objetivo'] = objetivo
                data['numobj'] = request.POST['numobj']
                data['detalles'] = proyecto.cronograma_detallado_objetivo(objetivo.id)
                totales = proyecto.totales_detalle_objetivo(objetivo.id)
                template = get_template("pro_proyectoinvestigacion/secciondetalleobjetivo.html")
                json_content = template.render(data)

                ponderaciongeneral = proyecto.total_ponderacion_actividades()

                log(f'{persona} agregó actividad al cronograma de proyecto de investigación {actividadcronograma}', request, "add")
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
                if 'ponderacione' in request.POST:
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
                if 'ponderacione' in request.POST:
                    actividadcronograma.ponderacion = request.POST['ponderacione']

                actividadcronograma.fechainicio = fechainicio
                actividadcronograma.fechafin = fechafin
                actividadcronograma.entregable = request.POST['entregablee'].strip()
                actividadcronograma.evidenciacontrolinforme = request.POST['evidenciacontrolinformee'].strip()
                actividadcronograma.observaciongeneral = request.POST['observaciongenerale'].strip()
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

                # Actualizo estado de revisión del cronograma
                if not proyecto.fase_aprobacion_superada():
                    proyecto.estadocronogramarev = 1
                    proyecto.observacioncronograma = ''
                    proyecto.save(request)

                # Actualizo el proyecto si el estado del cronograma es NOVEDAD
                if proyecto.estadocronograma == 4:
                    proyecto.observacion = ""
                    proyecto.estadocronograma = 1
                    proyecto.save(request)

                # Si el estado del proyecto NO ES APROBADO, NI EN EJECUCIÓN
                if proyecto.estado.valor not in [18, 20]:
                    proyecto.registrado = False
                    proyecto.verificado = None
                    proyecto.documentogenerado = False
                    proyecto.archivodocumentofirmado = None
                    proyecto.archivodocumentosindatint = None
                    proyecto.estadodocumentofirmado = 1

                proyecto.save(request)

                # Si tiene estado ERROR en requisitos, o REQUIERE MODIFICACIONES MENORES/MAYORES se debe poner estado EN EDICIÓN
                if proyecto.estado.valor in [4, 15, 16, 38, 39]:
                    # Consulto el estado que voy a asignar

                    if proyecto.estado.valor == 4:
                        estado = obtener_estado_solicitud(3, 1)
                    elif proyecto.estado.valor == 15:
                        estado = obtener_estado_solicitud(3, 28)
                    elif proyecto.estado.valor == 16:
                        estado = obtener_estado_solicitud(3, 29)
                    elif proyecto.estado.valor == 38:
                        estado = obtener_estado_solicitud(3, 40)
                    else:
                        estado = obtener_estado_solicitud(3, 41)

                    # Actualizo estado
                    proyecto.estado = estado
                    proyecto.save(request)

                    # Creo el recorrido del proyecto
                    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                               fecha=datetime.now().date(),
                                                               observacion=estado.observacion,
                                                               estado=estado
                                                               )
                    recorrido.save(request)

                # Actualizo la solicitud de permiso en caso de estar vigente
                actualizar_permiso_edicion_rubros_presupuesto(proyecto, 2, 1, request)

                # Cargo la sección del detalle de actividades para el objetivo
                data['objetivo'] = objetivo = actividadcronograma.objetivo
                data['numobj'] = request.POST['numobj']
                data['detalles'] = proyecto.cronograma_detallado_objetivo(objetivo.id)
                totales = proyecto.totales_detalle_objetivo(objetivo.id)
                template = get_template("pro_proyectoinvestigacion/secciondetalleobjetivo.html")
                json_content = template.render(data)

                ponderaciongeneral = proyecto.total_ponderacion_actividades()

                log(f'{persona} editó actividad del cronograma de proyecto de investigación {actividadcronograma}', request, "edit")
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

                # Actualizo estado de revisión del cronograma
                if not proyecto.fase_aprobacion_superada():
                    proyecto.estadocronogramarev = 1
                    proyecto.observacioncronograma = ''
                    proyecto.save(request)

                # Actualizo el proyecto si el estado del cronograma es NOVEDAD
                if proyecto.estadocronograma == 4:
                    proyecto.observacion = ""
                    proyecto.estadocronograma = 1
                    proyecto.save(request)

                # Actualizo la solicitud de permiso en caso de estar vigente
                actualizar_permiso_edicion_rubros_presupuesto(proyecto, 2, 1, request)

                # Consulto los totales
                totales = proyecto.totales_detalle_objetivo(objetivo.id)
                ponderaciongeneral = proyecto.total_ponderacion_actividades()

                log(f'{persona} eliminó actividad del cronograma de proyecto de investigación {actividadcronograma}', request, "del")
                return JsonResponse({"result": "ok", "totalactividades": totales["totalactividades"], "totalponderacion": totales["totalponderacion"], "ponderaciongeneral": ponderaciongeneral, "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al eliminar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'confirmarcronograma':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Validar que el cronograma tenga el total de las ponderaciones de las actividades en 100%
                totalponderacion = proyecto.total_ponderacion_actividades()
                if totalponderacion != 100:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La ponderación registrada de las actividades del cronograma del proyecto debe ser del 100%. Usted ha registrado un {}%".format(totalponderacion), "showSwal": "True", "swalType": "warning"})

                # Validar que todas las actividades tengan entregables
                if not proyecto.entregables_actividades_completos():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Todas las actividades del cronograma del proyecto deben tener entregables", "showSwal": "True", "swalType": "warning"})

                # Actualizar el estado de cronograma
                proyecto.estadocronograma = 2
                proyecto.save(request)

                # Notificar por e-mail a la coordinación de investigación
                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, . . .sga7@unemi.edu.ec

                # Destinatarios
                lista_email_envio = ['investigacion@unemi.edu.ec']
                lista_email_cco = []
                lista_adjuntos = []

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
                tituloemail = "Cronograma de Actividades de Proyecto de Investigación Editado"
                titulo = "Proyectos de Investigación"

                send_html_mail(tituloemail,
                               "emails/propuestaproyectoinvestigacion.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': 'CRONEDIT',
                                'proyecto': proyecto
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'%s confirmó cronograma de actividades de proyecto de investigación [ %s ]' % (persona, proyecto), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al actualizar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addpresupuestoproyecto':
            try:
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                f = PresupuestoProyectoInvestigacionForm(request.POST)
                if f.is_valid():
                    # Validar que el total presupuestado no exceda al total de financiamiento del proyecto en 0.05
                    diferencia = 0 if f.cleaned_data['montototal'] >= f.cleaned_data['totalpresupuesto'] else f.cleaned_data['totalpresupuesto'] - f.cleaned_data['montototal']
                    # diferencia = abs(f.cleaned_data['montototal'] - f.cleaned_data['totalpresupuesto'])
                    if diferencia > 0.00:
                        # return JsonResponse({"result": "bad", "mensaje": u"El valor de Total de Presupuesto no debe ser mayor a %s" % (f.cleaned_data['montototal'] + 0.05)})
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El valor de Total de Presupuesto no debe ser mayor a %s" % (f.cleaned_data['montototal']), "showSwal": "True", "swalType": "warning"})

                    cumpleporcentajeequipo = 1

                    # Si proyecto incluye compra de equipos validar que no sea inferior al porcentaje para convocatorias 2022 en adelante
                    # if proyecto.compraequipo != 3:
                    #     if proyecto.convocatoria.apertura.year >= 2022:
                    #         if Decimal(request.POST['totalpresupuestoequipo']).quantize(Decimal('.01')) < Decimal(request.POST['minimocompraequipo']).quantize(Decimal('.01')):
                    #             # return JsonResponse({"result": "bad", "mensaje": u"El valor de Total de Presupuesto de EQUIPOS no debe ser inferior a %s" % (request.POST['minimocompraequipo'])})
                    #             return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El valor de Total de Presupuesto de EQUIPOS no debe ser inferior a %s" % (request.POST['minimocompraequipo']), "showSwal": "True", "swalType": "warning"})
                    #     else:
                    #         cumpleporcentajeequipo = 2 if Decimal(request.POST['totalpresupuestoequipo']).quantize(Decimal('.01')) >= Decimal(request.POST['minimocompraequipo']).quantize(Decimal('.01')) else 3

                    tiposrecurso = TipoRecursoPresupuesto.objects.filter(status=True, vigente=True).order_by('orden', 'descripcion')

                    for tiporecurso in tiposrecurso:
                        # Obtengo los items por tipo de recurso del formulario
                        if tiporecurso.abreviatura != 'VTI' and tiporecurso.abreviatura != 'VTN':
                            recursos = request.POST.getlist('recurso_'+tiporecurso.abreviatura+'[]')
                            descripciones = request.POST.getlist('descripcion_'+tiporecurso.abreviatura+'[]')
                            unidadesmedida = request.POST.getlist('unidadmedida_'+tiporecurso.abreviatura+'[]', [])
                            cantidades = request.POST.getlist('cantidad_'+tiporecurso.abreviatura+'[]')
                            valoresunitarios = request.POST.getlist('valorunitario_' + tiporecurso.abreviatura + '[]')

                            if recursos:
                                recursoenblanco = [dato for dato in recursos if dato.strip() == '']
                                descripcionenblanco = [dato for dato in descripciones if dato.strip() == '']
                                unidadencero = [dato for dato in unidadesmedida if int(dato.strip()) == 0]
                                cantidadencero = [dato for dato in cantidades if int(dato.strip()) == 0]
                                valorencero = [dato for dato in valoresunitarios if Decimal(dato.strip()) == 0]

                                if recursoenblanco:
                                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Recurso deben estar completos [ %s ]" % (tiporecurso.descripcion), "showSwal": "True", "swalType": "warning"})

                                if descripcionenblanco:
                                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Descripción deben estar completos [ %s ]" % (tiporecurso.descripcion), "showSwal": "True", "swalType": "warning"})

                                if unidadencero:
                                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Unidad de medida deben estar completos [ %s ]" % (tiporecurso.descripcion), "showSwal": "True", "swalType": "warning"})

                                if cantidadencero:
                                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Cantidad deben ser mayores a 0 [ %s ]" % (tiporecurso.descripcion), "showSwal": "True", "swalType": "warning"})

                                if valorencero:
                                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Valor Unitario deben ser mayores a 0 [ %s ]" % (tiporecurso.descripcion), "showSwal": "True", "swalType": "warning"})
                        else:
                            if tiporecurso.abreviatura == 'VTI':
                                integrantes = request.POST.getlist('integrante_pasaje_VTI[]')
                                itinerarios = request.POST.getlist('itinerario_pasaje_VTI[]')
                                fechassalida = request.POST.getlist('fechasalida_pasaje_VTI[]')
                                fechasretorno = request.POST.getlist('fecharetorno_pasaje_VTI[]')
                                actividades = request.POST.getlist('actividad_pasaje_VTI[]')
                                valorespasajes = request.POST.getlist('valorunitario_pasaje_VTI[]')
                                nochesestancia = request.POST.getlist('nocheestancia_viatico_VTI[]')
                                valoresviaticos = request.POST.getlist('valorunitario_viatico_VTI[]')

                                ciudadesmovilizacion = request.POST.getlist('ciudades_movilizacion_VTI[]')
                                diasmovilizacion = request.POST.getlist('dias_movilizacion_VTI[]')


                                if integrantes:
                                    integranteencero = [dato for dato in integrantes if int(dato.strip()) == 0]
                                    itinerarioenblanco = [dato for dato in itinerarios if dato.strip() == '']
                                    fechasalidaenblanco = [dato for dato in fechassalida if dato.strip() == '']
                                    fecharetornoenblanco = [dato for dato in fechasretorno if dato.strip() == '']
                                    actividadenblanco = [dato for dato in actividades if dato.strip() == '']
                                    valorencero = [dato for dato in valorespasajes if Decimal(dato.strip()) == 0]

                                    nocheencero = [dato for dato in nochesestancia if int(dato.strip()) == 0]
                                    valorviaticoencero = [dato for dato in valoresviaticos if Decimal(dato.strip()) == 0]

                                    ciudadenblanco = [dato for dato in ciudadesmovilizacion if dato.strip() == '']
                                    diaencero = [dato for dato in diasmovilizacion if int(dato.strip()) == 0]

                                    if integranteencero:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Integrante deben estar completos", "showSwal": "True", "swalType": "warning"})

                                    if itinerarioenblanco:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Itinerario deben estar completos", "showSwal": "True", "swalType": "warning"})

                                    if fechasalidaenblanco:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo fecha de salida deben estar completos", "showSwal": "True", "swalType": "warning"})

                                    if fecharetornoenblanco:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo fecha de retorno deben estar completos", "showSwal": "True", "swalType": "warning"})

                                    if actividadenblanco:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo actividad a desarrollar deben estar completos", "showSwal": "True", "swalType": "warning"})

                                    if valorencero:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Costo de pasaje deben ser mayores a 0", "showSwal": "True", "swalType": "warning"})

                                    if nocheencero:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo noches de estancia deben estar completos", "showSwal": "True", "swalType": "warning"})

                                    if valorviaticoencero:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Valor de viático deben ser mayores a 0", "showSwal": "True", "swalType": "warning"})

                                    if ciudadenblanco:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Ciudades dónde se moviliza deben estar completos", "showSwal": "True", "swalType": "warning"})

                                    if diaencero:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Cantidad de días deben ser mayores a 0", "showSwal": "True", "swalType": "warning"})

                            else:
                                integrantes = request.POST.getlist('integrante_pasaje_VTN[]')
                                itinerarios = request.POST.getlist('itinerario_pasaje_VTN[]')
                                fechassalida = request.POST.getlist('fechasalida_pasaje_VTN[]')
                                fechasretorno = request.POST.getlist('fecharetorno_pasaje_VTN[]')
                                actividades = request.POST.getlist('actividad_pasaje_VTN[]')
                                valorespasajes = request.POST.getlist('valorunitario_pasaje_VTN[]')
                                nochesestancia = request.POST.getlist('nocheestancia_viatico_VTN[]')
                                valoresviaticos = request.POST.getlist('valorunitario_viatico_VTN[]')

                                if integrantes:
                                    integranteencero = [dato for dato in integrantes if int(dato.strip()) == 0]
                                    itinerarioenblanco = [dato for dato in itinerarios if dato.strip() == '']
                                    fechasalidaenblanco = [dato for dato in fechassalida if dato.strip() == '']
                                    fecharetornoenblanco = [dato for dato in fechasretorno if dato.strip() == '']
                                    actividadenblanco = [dato for dato in actividades if dato.strip() == '']
                                    valorencero = [dato for dato in valorespasajes if Decimal(dato.strip()) == 0]
                                    valorviaticoencero = []

                                    for noche, valorviatico in zip(nochesestancia, valoresviaticos):
                                        if int(noche) > 0 and Decimal(valorviatico) == 0:
                                            valorviaticoencero.append(valorviatico)

                                    if integranteencero:
                                        return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Integrante deben estar completos"})

                                    if itinerarioenblanco:
                                        return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Itinerario deben estar completos"})

                                    if fechasalidaenblanco:
                                        return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo fecha de salida deben estar completos"})

                                    if fecharetornoenblanco:
                                        return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo fecha de retorno deben estar completos"})

                                    if actividadenblanco:
                                        return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo actividad a desarrollar deben estar completos"})

                                    if valorencero:
                                        return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Costo de pasaje deben ser mayores a 0"})

                                    if valorviaticoencero:
                                        return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Valor de viático deben ser mayores a 0 cuando las noches de estancia sean mayor a 0"})

                    # Actualizo el total del presupuesto del proyecto
                    proyecto.presupuesto = f.cleaned_data['totalpresupuesto']
                    proyecto.cumpleporcentajeequipo = cumpleporcentajeequipo
                    proyecto.save(request)

                    for tiporecurso in tiposrecurso:
                        if tiporecurso.abreviatura != 'VTI' and tiporecurso.abreviatura != 'VTN':
                            # Obtengo los items por tipo de recurso del formulario
                            recursos = request.POST.getlist('recurso_'+tiporecurso.abreviatura+'[]')
                            descripciones = request.POST.getlist('descripcion_'+tiporecurso.abreviatura+'[]')
                            unidadesmedida = request.POST.getlist('unidadmedida_'+tiporecurso.abreviatura+'[]')
                            cantidades = request.POST.getlist('cantidad_'+tiporecurso.abreviatura+'[]')
                            valoresunitarios = request.POST.getlist('valorunitario_'+tiporecurso.abreviatura+'[]')
                            valoresiva = request.POST.getlist('valoriva_'+tiporecurso.abreviatura+'[]')
                            valorestotales = request.POST.getlist('valortotal_'+tiporecurso.abreviatura+'[]')
                            observaciones = request.POST.getlist('observacion_'+tiporecurso.abreviatura+'[]')

                            # Si hay datos en el grupo
                            if recursos:
                                # Guardo el detalle de presupuesto del tipo de recurso
                                for recurso, descripcion, unidadmedida, cantidad, valorunitario, valoriva, valortotal, observacion in zip(recursos, descripciones, unidadesmedida, cantidades, valoresunitarios, valoresiva, valorestotales, observaciones):
                                    itempresupuesto = ProyectoInvestigacionItemPresupuesto(
                                        proyecto=proyecto,
                                        tiporecurso=tiporecurso,
                                        recurso=recurso,
                                        descripcion=descripcion,
                                        unidadmedida_id=unidadmedida,
                                        cantidad=cantidad,
                                        valorunitario=valorunitario,
                                        calculaiva=Decimal(valoriva) > 0,
                                        valoriva=valoriva,
                                        valortotal=valortotal,
                                        observacion=observacion
                                    )
                                    itempresupuesto.save(request)
                        else:
                            if tiporecurso.abreviatura == 'VTI':
                                # Obtengo los items por tipo de recurso del formulario
                                integrantes = request.POST.getlist('integrante_pasaje_VTI[]')

                                # Si hay datos en el grupo
                                if integrantes:
                                    itinerarios = request.POST.getlist('itinerario_pasaje_VTI[]')
                                    fechassalida = request.POST.getlist('fechasalida_pasaje_VTI[]')
                                    fechasretorno = request.POST.getlist('fecharetorno_pasaje_VTI[]')
                                    actividades = request.POST.getlist('actividad_pasaje_VTI[]')
                                    valorespasajes = request.POST.getlist('valorunitario_pasaje_VTI[]')
                                    valoresiva = request.POST.getlist('valoriva_pasaje_VTI[]')
                                    valorestotales = request.POST.getlist('valortotal_pasaje_VTI[]')
                                    observaciones = request.POST.getlist('observacion_pasaje_VTI[]')

                                    integrantes_viatico = request.POST.getlist('idpersonaviatico[]')
                                    nochesviatico = request.POST.getlist('nocheestancia_viatico_VTI[]')
                                    valoresviaticos = request.POST.getlist('valorunitario_viatico_VTI[]')
                                    valoresivaviatico = request.POST.getlist('valoriva_viatico_VTI[]')
                                    valorestotalesviatico = request.POST.getlist('valortotal_viatico_VTI[]')
                                    observacionesviatico = request.POST.getlist('observacion_viatico_VTI[]')

                                    integrantes_movilizacion = request.POST.getlist('idpersonamovilizacion[]')
                                    ciudadesmovilizacion = request.POST.getlist('ciudades_movilizacion_VTI[]')
                                    diasmovilizacion = request.POST.getlist('dias_movilizacion_VTI[]')
                                    observacionesmovilizacion = request.POST.getlist('observacion_movilizacion_VTI[]')

                                    lista_id_pasaje = []

                                    # Guardo el detalle de presupuesto de pasajes
                                    for integrante, itinerario, fechasalida, fecharetorno, actividad, valorpasaje, valoriva, valortotal, observacion in zip(integrantes, itinerarios, fechassalida, fechasretorno, actividades, valorespasajes, valoresiva, valorestotales, observaciones):
                                        # Consulto persona
                                        personai = Persona.objects.get(pk=integrante)
                                        nombrepersona = personai.nombre_completo_inverso()

                                        # Guardo detalle presupuesto
                                        itempresupuesto = ProyectoInvestigacionItemPresupuesto(
                                            proyecto=proyecto,
                                            tiporecurso=tiporecurso,
                                            # recurso='PASAJES AÉREOS INTERNACIONALES - ' + nombrepersona,
                                            recurso='PASAJES - ' + nombrepersona,
                                            descripcion=itinerario,
                                            unidadmedida_id=1,
                                            cantidad=1,
                                            valorunitario=valorpasaje,
                                            calculaiva=Decimal(valoriva) > 0,
                                            valoriva=valoriva,
                                            valortotal=valortotal,
                                            observacion=observacion
                                        )
                                        itempresupuesto.save(request)

                                        # Guardo detalle de pasaje
                                        pasajeintegrante = ProyectoInvestigacionPasajeIntegrante(
                                            proyecto=proyecto,
                                            itempresupuesto=itempresupuesto,
                                            persona_id=integrante,
                                            itinerario=itinerario,
                                            fechasalida=fechasalida,
                                            fecharetorno=fecharetorno,
                                            actividad=actividad,
                                            cantidad=1,
                                            valorunitario=valorpasaje,
                                            calculaiva=Decimal(valoriva) > 0,
                                            valoriva=valoriva,
                                            valortotal=valortotal,
                                            observacion=observacion,
                                            tipopasaje=3
                                        )
                                        pasajeintegrante.save(request)
                                        lista_id_pasaje.append(pasajeintegrante.id)

                                    # Recorrer los datos de integrantes de viáticos
                                    for integrante, noches, valorunitario, valoriva, valortotal, observacion, idpasaje in zip(integrantes_viatico, nochesviatico, valoresviaticos, valoresivaviatico, valorestotalesviatico, observacionesviatico, lista_id_pasaje):
                                        # Consulto persona
                                        personai = Persona.objects.get(pk=integrante)
                                        nombrepersona = personai.nombre_completo_inverso()

                                        # Guardo detalle presupuesto
                                        itempresupuesto = ProyectoInvestigacionItemPresupuesto(
                                            proyecto=proyecto,
                                            tiporecurso=tiporecurso,
                                            # recurso='VIÁTICOS INTERNACIONALES - ' + nombrepersona,
                                            recurso='VIÁTICOS - ' + nombrepersona,
                                            descripcion=observacion,
                                            unidadmedida_id=1,
                                            cantidad=noches,
                                            valorunitario=valorunitario,
                                            calculaiva=Decimal(valoriva) > 0,
                                            valoriva=valoriva,
                                            valortotal=valortotal,
                                            observacion=observacion
                                        )
                                        itempresupuesto.save(request)

                                        # Guardo detalle de viático
                                        viaticointegrante = ProyectoInvestigacionViaticoIntegrante(
                                            proyecto=proyecto,
                                            itempresupuesto=itempresupuesto,
                                            pasajeintegrante_id=idpasaje,
                                            persona_id=integrante,
                                            nocheestancia=noches,
                                            valor=valorunitario,
                                            calculaiva=Decimal(valoriva) > 0,
                                            valoriva=valoriva,
                                            valortotal=valortotal,
                                            observacion=observacion,
                                            tipoviatico=3
                                        )
                                        viaticointegrante.save(request)

                                    # Recorrer los datos de integrantes de movilizaciones
                                    valorunitario = 0
                                    valoriva = 0
                                    valortotal = 0

                                    for integrante, ciudad, dias, observacion, idpasaje in zip(integrantes_movilizacion, ciudadesmovilizacion, diasmovilizacion, observacionesmovilizacion, lista_id_pasaje):
                                        # Consulto persona
                                        personai = Persona.objects.get(pk=integrante)
                                        nombrepersona = personai.nombre_completo_inverso()

                                        # Guardo detalle presupuesto
                                        itempresupuesto = ProyectoInvestigacionItemPresupuesto(
                                            proyecto=proyecto,
                                            tiporecurso=tiporecurso,
                                            # recurso='VIÁTICOS INTERNACIONALES - ' + nombrepersona,
                                            recurso='MOVILIZACIÓN - ' + nombrepersona,
                                            descripcion=observacion,
                                            unidadmedida_id=1,
                                            cantidad=dias,
                                            valorunitario=valorunitario,
                                            calculaiva=Decimal(valoriva) > 0,
                                            valoriva=valoriva,
                                            valortotal=valortotal,
                                            observacion=observacion
                                        )
                                        itempresupuesto.save(request)

                                        # Guardo detalle de movilización
                                        movilizacionintegrante = ProyectoInvestigacionMovilizacionIntegrante(
                                            proyecto=proyecto,
                                            itempresupuesto=itempresupuesto,
                                            pasajeintegrante_id=idpasaje,
                                            persona_id=integrante,
                                            ciudad=ciudad,
                                            cantidaddia=dias,
                                            valor=valorunitario,
                                            calculaiva=Decimal(valoriva) > 0,
                                            valoriva=valoriva,
                                            valortotal=valortotal,
                                            observacion=observacion,
                                            tipomovilizacion=3
                                        )
                                        movilizacionintegrante.save(request)

                            else:
                                # Obtengo los items por tipo de recurso del formulario
                                integrantes = request.POST.getlist('integrante_pasaje_VTN[]')

                                # Si hay datos en el grupo
                                if integrantes:
                                    itinerarios = request.POST.getlist('itinerario_pasaje_VTN[]')
                                    fechassalida = request.POST.getlist('fechasalida_pasaje_VTN[]')
                                    fechasretorno = request.POST.getlist('fecharetorno_pasaje_VTN[]')
                                    actividades = request.POST.getlist('actividad_pasaje_VTN[]')
                                    valorespasajes = request.POST.getlist('valorunitario_pasaje_VTN[]')
                                    valoresiva = request.POST.getlist('valoriva_pasaje_VTN[]')
                                    valorestotales = request.POST.getlist('valortotal_pasaje_VTN[]')
                                    observaciones = request.POST.getlist('observacion_pasaje_VTN[]')

                                    integrantes_viatico = request.POST.getlist('idpersonaviaticonac[]')
                                    nochesviatico = request.POST.getlist('nocheestancia_viatico_VTN[]')
                                    valoresviaticos = request.POST.getlist('valorunitario_viatico_VTN[]')
                                    valoresivaviatico = request.POST.getlist('valoriva_viatico_VTN[]')
                                    valorestotalesviatico = request.POST.getlist('valortotal_viatico_VTN[]')
                                    observacionesviatico = request.POST.getlist('observacion_viatico_VTN[]')

                                    lista_id_pasaje = []

                                    # Guardo el detalle de presupuesto de pasajes
                                    for integrante, itinerario, fechasalida, fecharetorno, actividad, valorpasaje, valoriva, valortotal, observacion in zip(integrantes, itinerarios, fechassalida, fechasretorno, actividades, valorespasajes, valoresiva, valorestotales, observaciones):
                                        # Consulto persona
                                        personai = Persona.objects.get(pk=integrante)
                                        nombrepersona = personai.nombre_completo_inverso()

                                        # Guardo detalle presupuesto
                                        itempresupuesto = ProyectoInvestigacionItemPresupuesto(
                                            proyecto=proyecto,
                                            tiporecurso=tiporecurso,
                                            recurso='PASAJES AÉREOS NACIONALES - ' + nombrepersona,
                                            descripcion=itinerario,
                                            unidadmedida_id=1,
                                            cantidad=1,
                                            valorunitario=valorpasaje,
                                            calculaiva=Decimal(valoriva) > 0,
                                            valoriva=valoriva,
                                            valortotal=valortotal,
                                            observacion=observacion
                                        )
                                        itempresupuesto.save(request)

                                        # Guardo detalle de pasaje
                                        pasajeintegrante = ProyectoInvestigacionPasajeIntegrante(
                                            proyecto=proyecto,
                                            itempresupuesto=itempresupuesto,
                                            persona_id=integrante,
                                            itinerario=itinerario,
                                            fechasalida=fechasalida,
                                            fecharetorno=fecharetorno,
                                            actividad=actividad,
                                            cantidad=1,
                                            valorunitario=valorpasaje,
                                            calculaiva=Decimal(valoriva) > 0,
                                            valoriva=valoriva,
                                            valortotal=valortotal,
                                            observacion=observacion,
                                            tipopasaje=2
                                        )
                                        pasajeintegrante.save(request)
                                        lista_id_pasaje.append(pasajeintegrante.id)

                                    # Recorrer los datos de integrantes de viáticos
                                    for integrante, noches, valorunitario, valoriva, valortotal, observacion, idpasaje in zip(integrantes_viatico, nochesviatico, valoresviaticos, valoresivaviatico, valorestotalesviatico, observacionesviatico, lista_id_pasaje):
                                        # Consulto persona
                                        personai = Persona.objects.get(pk=integrante)
                                        nombrepersona = personai.nombre_completo_inverso()

                                        # Guardo detalle presupuesto
                                        itempresupuesto = ProyectoInvestigacionItemPresupuesto(
                                            proyecto=proyecto,
                                            tiporecurso=tiporecurso,
                                            recurso='VIÁTICOS NACIONALES - ' + nombrepersona,
                                            descripcion=observacion,
                                            unidadmedida_id=1,
                                            cantidad=noches,
                                            valorunitario=valorunitario,
                                            calculaiva=Decimal(valoriva) > 0,
                                            valoriva=valoriva,
                                            valortotal=valortotal,
                                            observacion=observacion
                                        )
                                        itempresupuesto.save(request)

                                        # Guardo detalle de viático
                                        viaticointegrante = ProyectoInvestigacionViaticoIntegrante(
                                            proyecto=proyecto,
                                            itempresupuesto=itempresupuesto,
                                            pasajeintegrante_id=idpasaje,
                                            persona_id=integrante,
                                            nocheestancia=noches,
                                            valor=valorunitario,
                                            calculaiva=Decimal(valoriva) > 0,
                                            valoriva=valoriva,
                                            valortotal=valortotal,
                                            observacion=observacion,
                                            tipoviatico=2
                                        )
                                        viaticointegrante.save(request)

                    log(u'%s agregó presupuesto de propuesta de proyecto de investigación: %s' % (persona, proyecto), request, "add")
                    # return JsonResponse({"result": "ok"})
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    x = f.errors
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editpresupuestoproyecto':
            try:
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                itemseliminados = json.loads(request.POST['lista_items1'])

                f = PresupuestoProyectoInvestigacionForm(request.POST)
                if f.is_valid():
                    # Validar que el total presupuestado no exceda al total de financiamiento del proyecto
                    diferencia = 0 if f.cleaned_data['montototal'] >= f.cleaned_data['totalpresupuesto'] else f.cleaned_data['totalpresupuesto'] - f.cleaned_data['montototal']
                    diferencia = Decimal(diferencia).quantize(Decimal('.01'))
                    # diferencia = abs(f.cleaned_data['montototal'] - f.cleaned_data['totalpresupuesto'])
                    if diferencia > 0.00:
                        # return JsonResponse({"result": "bad", "mensaje": u"El valor de Total de Presupuesto no debe ser mayor a %s" % (f.cleaned_data['montototal'] + 0.05)})
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El valor de Total de Presupuesto no debe ser mayor a %s" % (f.cleaned_data['montototal']), "showSwal": "True", "swalType": "warning"})

                    # if f.cleaned_data['totalpresupuesto'] > f.cleaned_data['montototal']:
                    #     return JsonResponse({"result": "bad", "mensaje": u"El valor de Total de Presupuesto no debe ser mayor a %s" % (f.cleaned_data['montototal'])})

                    cumpleporcentajeequipo = 1

                    # # Si proyecto incluye compra de equipos validar que no sea inferior al porcentaje para convocatorias 2022 en adelante
                    # if proyecto.compraequipo != 3:
                    #     if proyecto.convocatoria.apertura.year >= 2022:
                    #         if Decimal(request.POST['totalpresupuestoequipo']).quantize(Decimal('.01')) < Decimal(request.POST['minimocompraequipo']).quantize(Decimal('.01')):
                    #             return JsonResponse({"result": "bad", "mensaje": u"El valor de Total de Presupuesto de EQUIPOS no debe ser inferior a %s" % (request.POST['minimocompraequipo'])})
                    #     else:
                    #         cumpleporcentajeequipo = 2 if Decimal(request.POST['totalpresupuestoequipo']).quantize(Decimal('.01')) >= Decimal(request.POST['minimocompraequipo']).quantize(Decimal('.01')) else 3

                    tiposrecurso = TipoRecursoPresupuesto.objects.filter(status=True, vigente=True).order_by('orden', 'descripcion')

                    for tiporecurso in tiposrecurso:
                        # Obtengo los items por tipo de recurso del formulario
                        if tiporecurso.abreviatura != 'VTI' and tiporecurso.abreviatura != 'VTN':
                            recursos = request.POST.getlist('recurso_'+tiporecurso.abreviatura+'[]')
                            descripciones = request.POST.getlist('descripcion_'+tiporecurso.abreviatura+'[]')
                            unidadesmedida = request.POST.getlist('unidadmedida_'+tiporecurso.abreviatura+'[]')
                            cantidades = request.POST.getlist('cantidad_'+tiporecurso.abreviatura+'[]')
                            valoresunitarios = request.POST.getlist('valorunitario_' + tiporecurso.abreviatura + '[]')


                            if recursos:
                                recursoenblanco = [dato for dato in recursos if dato.strip() == '']
                                descripcionenblanco = [dato for dato in descripciones if dato.strip() == '']
                                unidadencero = [dato for dato in unidadesmedida if int(dato.strip()) == 0]
                                cantidadencero = [dato for dato in cantidades if int(dato.strip()) == 0]
                                valorencero = [dato for dato in valoresunitarios if Decimal(dato.strip()) == 0]

                                if recursoenblanco:
                                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Recurso deben estar completos [ %s ]" % (tiporecurso.descripcion), "showSwal": "True", "swalType": "warning"})

                                if descripcionenblanco:
                                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Descripción deben estar completos [ %s ]" % (tiporecurso.descripcion), "showSwal": "True", "swalType": "warning"})

                                if unidadencero:
                                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Unidad de medida deben estar completos [ %s ]" % (tiporecurso.descripcion), "showSwal": "True", "swalType": "warning"})

                                if cantidadencero:
                                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Cantidad deben ser mayores a 0 [ %s ]" % (tiporecurso.descripcion), "showSwal": "True", "swalType": "warning"})

                                if valorencero:
                                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Valor Unitario deben ser mayores a 0 [ %s ]" % (tiporecurso.descripcion), "showSwal": "True", "swalType": "warning"})

                        else:
                            if tiporecurso.abreviatura == 'VTI':
                                integrantes = request.POST.getlist('integrante_pasaje_VTI[]')
                                itinerarios = request.POST.getlist('itinerario_pasaje_VTI[]')
                                fechassalida = request.POST.getlist('fechasalida_pasaje_VTI[]')
                                fechasretorno = request.POST.getlist('fecharetorno_pasaje_VTI[]')
                                actividades = request.POST.getlist('actividad_pasaje_VTI[]')
                                valorespasajes = request.POST.getlist('valorunitario_pasaje_VTI[]')
                                nochesestancia = request.POST.getlist('nocheestancia_viatico_VTI[]')
                                valoresviaticos = request.POST.getlist('valorunitario_viatico_VTI[]')

                                ciudadesmovilizacion = request.POST.getlist('ciudades_movilizacion_VTI[]')
                                diasmovilizacion = request.POST.getlist('dias_movilizacion_VTI[]')

                                if integrantes:
                                    integranteencero = [dato for dato in integrantes if int(dato.strip()) == 0]
                                    itinerarioenblanco = [dato for dato in itinerarios if dato.strip() == '']
                                    fechasalidaenblanco = [dato for dato in fechassalida if dato.strip() == '']
                                    fecharetornoenblanco = [dato for dato in fechasretorno if dato.strip() == '']
                                    actividadenblanco = [dato for dato in actividades if dato.strip() == '']
                                    valorencero = [dato for dato in valorespasajes if Decimal(dato.strip()) == 0]

                                    nocheencero = [dato for dato in nochesestancia if int(dato.strip()) == 0]
                                    valorviaticoencero = [dato for dato in valoresviaticos if Decimal(dato.strip()) == 0]

                                    ciudadenblanco = [dato for dato in ciudadesmovilizacion if dato.strip() == '']
                                    diaencero = [dato for dato in diasmovilizacion if int(dato.strip()) == 0]

                                    if integranteencero:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Integrante deben estar completos", "showSwal": "True", "swalType": "warning"})

                                    if itinerarioenblanco:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Itinerario deben estar completos", "showSwal": "True", "swalType": "warning"})

                                    if fechasalidaenblanco:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo fecha de salida deben estar completos", "showSwal": "True", "swalType": "warning"})

                                    if fecharetornoenblanco:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo fecha de retorno deben estar completos", "showSwal": "True", "swalType": "warning"})

                                    if actividadenblanco:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo actividad a desarrollar deben estar completos", "showSwal": "True", "swalType": "warning"})

                                    if valorencero:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Costo de pasaje deben ser mayores a 0", "showSwal": "True", "swalType": "warning"})

                                    if nocheencero:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo noches de estancia deben estar completos", "showSwal": "True", "swalType": "warning"})

                                    if valorviaticoencero:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Valor de viático deben ser mayores a 0", "showSwal": "True", "swalType": "warning"})

                                    if ciudadenblanco:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Ciudades dónde se moviliza deben estar completos", "showSwal": "True", "swalType": "warning"})

                                    if diaencero:
                                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Cantidad de días deben ser mayores a 0", "showSwal": "True", "swalType": "warning"})
                            else:
                                integrantes = request.POST.getlist('integrante_pasaje_VTN[]')
                                itinerarios = request.POST.getlist('itinerario_pasaje_VTN[]')
                                fechassalida = request.POST.getlist('fechasalida_pasaje_VTN[]')
                                fechasretorno = request.POST.getlist('fecharetorno_pasaje_VTN[]')
                                actividades = request.POST.getlist('actividad_pasaje_VTN[]')
                                valorespasajes = request.POST.getlist('valorunitario_pasaje_VTN[]')
                                nochesestancia = request.POST.getlist('nocheestancia_viatico_VTN[]')
                                valoresviaticos = request.POST.getlist('valorunitario_viatico_VTN[]')

                                if integrantes:
                                    integranteencero = [dato for dato in integrantes if int(dato.strip()) == 0]
                                    itinerarioenblanco = [dato for dato in itinerarios if dato.strip() == '']
                                    fechasalidaenblanco = [dato for dato in fechassalida if dato.strip() == '']
                                    fecharetornoenblanco = [dato for dato in fechasretorno if dato.strip() == '']
                                    actividadenblanco = [dato for dato in actividades if dato.strip() == '']
                                    valorencero = [dato for dato in valorespasajes if Decimal(dato.strip()) == 0]
                                    valorviaticoencero = []

                                    for noche, valorviatico in zip(nochesestancia, valoresviaticos):
                                        if int(noche) > 0 and Decimal(valorviatico) == 0:
                                            valorviaticoencero.append(valorviatico)

                                    if integranteencero:
                                        return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Integrante deben estar completos"})

                                    if itinerarioenblanco:
                                        return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Itinerario deben estar completos"})

                                    if fechasalidaenblanco:
                                        return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo fecha de salida deben estar completos"})

                                    if fecharetornoenblanco:
                                        return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo fecha de retorno deben estar completos"})

                                    if actividadenblanco:
                                        return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo actividad a desarrollar deben estar completos"})

                                    if valorencero:
                                        return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Costo de pasaje deben ser mayores a 0"})

                                    if valorviaticoencero:
                                        return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Valor de viático deben ser mayores a 0 cuando las noches de estancia sean mayor a 0"})


                    # Actualizo el total del presupuesto del proyecto
                    proyecto.presupuesto = f.cleaned_data['totalpresupuesto']
                    proyecto.cumpleporcentajeequipo = cumpleporcentajeequipo
                    proyecto.registrado = False
                    proyecto.verificado = None
                    proyecto.documentogenerado = False
                    proyecto.archivodocumentofirmado = None
                    proyecto.archivodocumentosindatint = None
                    proyecto.estadodocumentofirmado = 1
                    proyecto.save(request)

                    # Elimino los detalles que fueron borrados en el formulario
                    for iteme in itemseliminados:
                        if not iteme:
                            break

                        # Borro item presupuesto PASAJES
                        iteme = ProyectoInvestigacionItemPresupuesto.objects.get(pk=int(iteme['iddetalle']))
                        iteme.status = False
                        iteme.save(request)

                        itempasaje = None

                        # Verifico si existe detalle de pasaje del item
                        if ProyectoInvestigacionPasajeIntegrante.objects.filter(itempresupuesto=iteme).exists():
                            itempasaje = ProyectoInvestigacionPasajeIntegrante.objects.get(itempresupuesto=iteme)
                            itempasaje.status = False
                            itempasaje.save(request)

                        # Verifico si existe detalle de viatico y de movilizacion del item
                        if itempasaje:
                            if ProyectoInvestigacionViaticoIntegrante.objects.filter(pasajeintegrante=itempasaje).exists():
                                itemviatico = ProyectoInvestigacionViaticoIntegrante.objects.get(pasajeintegrante=itempasaje)
                                itempresupuestoviatico = itemviatico.itempresupuesto
                                itemviatico.status = False
                                itemviatico.save(request)

                                # Borro item presupuesto VIATICO
                                itempresupuestoviatico.status = False
                                itempresupuestoviatico.save(request)

                            if ProyectoInvestigacionMovilizacionIntegrante.objects.filter(pasajeintegrante=itempasaje).exists():
                                itemmovilizacion = ProyectoInvestigacionMovilizacionIntegrante.objects.get(pasajeintegrante=itempasaje)
                                itempresupuestomovilizacion = itemviatico.itempresupuesto
                                itemmovilizacion.status = False
                                itemmovilizacion.save(request)

                                # Borro item presupuesto MOVILIZACION
                                itempresupuestomovilizacion.status = False
                                itempresupuestomovilizacion.save(request)

                    for tiporecurso in tiposrecurso:
                        if tiporecurso.abreviatura != 'VTI' and tiporecurso.abreviatura != 'VTN':
                            # Obtengo los items por tipo de recurso del formulario
                            idsdetalles = request.POST.getlist('iddetalle_' + tiporecurso.abreviatura + '[]')
                            recursos = request.POST.getlist('recurso_' + tiporecurso.abreviatura + '[]')
                            descripciones = request.POST.getlist('descripcion_' + tiporecurso.abreviatura + '[]')
                            unidadesmedida = request.POST.getlist('unidadmedida_' + tiporecurso.abreviatura + '[]')
                            cantidades = request.POST.getlist('cantidad_' + tiporecurso.abreviatura + '[]')
                            valoresunitarios = request.POST.getlist('valorunitario_' + tiporecurso.abreviatura + '[]')
                            valoresiva = request.POST.getlist('valoriva_' + tiporecurso.abreviatura + '[]')
                            valorestotales = request.POST.getlist('valortotal_' + tiporecurso.abreviatura + '[]')
                            observaciones = request.POST.getlist('observacion_' + tiporecurso.abreviatura + '[]')

                            # Si hay datos en el grupo
                            if recursos:
                                # Guardo el detalle de presupuesto del tipo de recurso
                                for iddetalle, recurso, descripcion, unidadmedida, cantidad, valorunitario, valoriva, valortotal, observacion in zip(idsdetalles, recursos, descripciones, unidadesmedida, cantidades, valoresunitarios, valoresiva, valorestotales, observaciones):
                                    # Nuevo detalle
                                    if int(iddetalle) == 0:
                                        itempresupuesto = ProyectoInvestigacionItemPresupuesto(
                                            proyecto=proyecto,
                                            tiporecurso=tiporecurso,
                                            recurso=recurso,
                                            descripcion=descripcion,
                                            unidadmedida_id=unidadmedida,
                                            cantidad=cantidad,
                                            valorunitario=valorunitario,
                                            calculaiva=Decimal(valoriva) > 0,
                                            valoriva=valoriva,
                                            valortotal=valortotal,
                                            observacion=observacion
                                        )
                                    else:
                                        itempresupuesto = ProyectoInvestigacionItemPresupuesto.objects.get(pk=int(iddetalle))
                                        itempresupuesto.recurso = recurso
                                        itempresupuesto.descripcion = descripcion
                                        itempresupuesto.unidadmedida_id = unidadmedida
                                        itempresupuesto.cantidad = cantidad
                                        itempresupuesto.valorunitario = valorunitario
                                        itempresupuesto.calculaiva = Decimal(valoriva) > 0
                                        itempresupuesto.valoriva = valoriva
                                        itempresupuesto.valortotal = valortotal
                                        itempresupuesto.observacion = observacion

                                    itempresupuesto.save(request)
                        else:
                            if tiporecurso.abreviatura == 'VTI':
                                # Obtengo los items por tipo de recurso del formulario
                                integrantes = request.POST.getlist('integrante_pasaje_VTI[]')
                                if integrantes:
                                    idsdetalles = request.POST.getlist('iddetalle_VTI[]')
                                    idsdetallespasajes = request.POST.getlist('iddetallepasaje_VTI[]')
                                    itinerarios = request.POST.getlist('itinerario_pasaje_VTI[]')
                                    fechassalida = request.POST.getlist('fechasalida_pasaje_VTI[]')
                                    fechasretorno = request.POST.getlist('fecharetorno_pasaje_VTI[]')
                                    actividades = request.POST.getlist('actividad_pasaje_VTI[]')
                                    valorespasajes = request.POST.getlist('valorunitario_pasaje_VTI[]')
                                    valoresiva = request.POST.getlist('valoriva_pasaje_VTI[]')
                                    valorestotales = request.POST.getlist('valortotal_pasaje_VTI[]')
                                    observaciones = request.POST.getlist('observacion_pasaje_VTI[]')

                                    idsdetalles2 = request.POST.getlist('iddetalle_VTI2[]')
                                    idsdetallesviaticos = request.POST.getlist('iddetalleviatico_VTI[]')
                                    integrantes_viatico = request.POST.getlist('idpersonaviatico[]')
                                    nochesviatico = request.POST.getlist('nocheestancia_viatico_VTI[]')
                                    valoresviaticos = request.POST.getlist('valorunitario_viatico_VTI[]')
                                    valoresivaviatico = request.POST.getlist('valoriva_viatico_VTI[]')
                                    valorestotalesviatico = request.POST.getlist('valortotal_viatico_VTI[]')
                                    observacionesviatico = request.POST.getlist('observacion_viatico_VTI[]')

                                    idsdetallesmov2 = request.POST.getlist('iddetallemovilizacion_VTI2[]')
                                    idsdetallesmovilizacion = request.POST.getlist('iddetallemovilizacion_VTI[]')
                                    integrantes_movilizacion = request.POST.getlist('idpersonamovilizacion[]')
                                    ciudadesmovilizacion = request.POST.getlist('ciudades_movilizacion_VTI[]')
                                    diasmovilizacion = request.POST.getlist('dias_movilizacion_VTI[]')
                                    observacionesmovilizacion = request.POST.getlist('observacion_movilizacion_VTI[]')

                                    lista_id_pasaje = []

                                    # Guardo el detalle de presupuesto de pasajes
                                    for iddetalle, iddetallepasaje, integrante, itinerario, fechasalida, fecharetorno, actividad, valorpasaje, valoriva, valortotal, observacion in zip(idsdetalles, idsdetallespasajes, integrantes, itinerarios, fechassalida, fechasretorno, actividades, valorespasajes, valoresiva, valorestotales, observaciones):
                                        # Consulto persona
                                        personai = Persona.objects.get(pk=integrante)
                                        nombrepersona = personai.nombre_completo_inverso()

                                        # Nuevo detalle
                                        if int(iddetalle) == 0:
                                            # Guardo detalle presupuesto
                                            itempresupuesto = ProyectoInvestigacionItemPresupuesto(
                                                proyecto=proyecto,
                                                tiporecurso=tiporecurso,
                                                # recurso='PASAJES AÉREOS INTERNACIONALES - ' + nombrepersona,
                                                recurso='PASAJES - ' + nombrepersona,
                                                descripcion=itinerario,
                                                unidadmedida_id=1,
                                                cantidad=1,
                                                valorunitario=valorpasaje,
                                                calculaiva=Decimal(valoriva) > 0,
                                                valoriva=valoriva,
                                                valortotal=valortotal,
                                                observacion=observacion
                                            )
                                            itempresupuesto.save(request)

                                            # Guardo detalle de pasaje
                                            pasajeintegrante = ProyectoInvestigacionPasajeIntegrante(
                                                proyecto=proyecto,
                                                itempresupuesto=itempresupuesto,
                                                persona_id=integrante,
                                                itinerario=itinerario,
                                                fechasalida=fechasalida,
                                                fecharetorno=fecharetorno,
                                                actividad=actividad,
                                                cantidad=1,
                                                valorunitario=valorpasaje,
                                                calculaiva=Decimal(valoriva) > 0,
                                                valoriva=valoriva,
                                                valortotal=valortotal,
                                                observacion=observacion,
                                                tipopasaje=1
                                            )
                                            pasajeintegrante.save(request)
                                            lista_id_pasaje.append(pasajeintegrante.id)
                                        else:
                                            # Actualizo detalle de presupuesto
                                            itempresupuesto = ProyectoInvestigacionItemPresupuesto.objects.get(pk=int(iddetalle))
                                            # itempresupuesto.recurso = 'PASAJES AÉREOS INTERNACIONALES - ' + nombrepersona
                                            itempresupuesto.recurso = 'PASAJES - ' + nombrepersona
                                            itempresupuesto.descripcion = itinerario
                                            itempresupuesto.unidadmedida_id = 1
                                            itempresupuesto.cantidad = 1
                                            itempresupuesto.valorunitario = valorpasaje
                                            itempresupuesto.calculaiva = Decimal(valoriva) > 0
                                            itempresupuesto.valoriva = valoriva
                                            itempresupuesto.valortotal = valortotal
                                            itempresupuesto.observacion = observacion
                                            itempresupuesto.save(request)

                                            # Actualizo detalle de pasaje
                                            pasajeintegrante = ProyectoInvestigacionPasajeIntegrante.objects.get(pk=int(iddetallepasaje))
                                            pasajeintegrante.persona_id = integrante
                                            pasajeintegrante.itinerario = itinerario
                                            pasajeintegrante.fechasalida = fechasalida
                                            pasajeintegrante.fecharetorno = fecharetorno
                                            pasajeintegrante.actividad = actividad
                                            pasajeintegrante.valorunitario = valorpasaje
                                            pasajeintegrante.calculaiva = Decimal(valoriva) > 0
                                            pasajeintegrante.valoriva = valoriva
                                            pasajeintegrante.valortotal = valortotal
                                            pasajeintegrante.observacion = observacion
                                            pasajeintegrante.save(request)

                                            lista_id_pasaje.append(pasajeintegrante.id)

                                    # Guardo el detalle de presupuesto de viáticos
                                    for iddetalle, iddetalleviatico, integrante, noches, valorunitario, valoriva, valortotal, observacion, idpasaje in zip(idsdetalles2, idsdetallesviaticos, integrantes_viatico, nochesviatico, valoresviaticos, valoresivaviatico, valorestotalesviatico, observacionesviatico, lista_id_pasaje):
                                        # Consulto persona
                                        personai = Persona.objects.get(pk=integrante)
                                        nombrepersona = personai.nombre_completo_inverso()

                                        # Nuevo detalle
                                        if int(iddetalle) == 0:
                                            # Guardo detalle presupuesto
                                            itempresupuesto = ProyectoInvestigacionItemPresupuesto(
                                                proyecto=proyecto,
                                                tiporecurso=tiporecurso,
                                                # recurso='VIÁTICOS INTERNACIONALES - ' + nombrepersona,
                                                recurso='VIÁTICOS - ' + nombrepersona,
                                                descripcion=observacion,
                                                unidadmedida_id=1,
                                                cantidad=noches,
                                                valorunitario=valorunitario,
                                                calculaiva=Decimal(valoriva) > 0,
                                                valoriva=valoriva,
                                                valortotal=valortotal,
                                                observacion=observacion
                                            )
                                            itempresupuesto.save(request)

                                            # Guardo detalle de viático
                                            viaticointegrante = ProyectoInvestigacionViaticoIntegrante(
                                                proyecto=proyecto,
                                                itempresupuesto=itempresupuesto,
                                                pasajeintegrante_id=idpasaje,
                                                persona_id=integrante,
                                                nocheestancia=noches,
                                                valor=valorunitario,
                                                calculaiva=Decimal(valoriva) > 0,
                                                valoriva=valoriva,
                                                valortotal=valortotal,
                                                observacion=observacion,
                                                tipoviatico=1
                                            )
                                            viaticointegrante.save(request)
                                        else:
                                            # Actualizo detalle de presupuesto
                                            itempresupuesto = ProyectoInvestigacionItemPresupuesto.objects.get(pk=int(iddetalle))
                                            # itempresupuesto.recurso = 'VIÁTICOS INTERNACIONALES - ' + nombrepersona
                                            itempresupuesto.recurso = 'VIÁTICOS - ' + nombrepersona
                                            itempresupuesto.descripcion = observacion
                                            itempresupuesto.unidadmedida_id = 1
                                            itempresupuesto.cantidad = noches
                                            itempresupuesto.valorunitario = valorunitario
                                            itempresupuesto.calculaiva = Decimal(valoriva) > 0
                                            itempresupuesto.valoriva = valoriva
                                            itempresupuesto.valortotal = valortotal
                                            itempresupuesto.observacion = observacion
                                            itempresupuesto.save(request)

                                            # Actualizo detalle de viático
                                            viaticointegrante = ProyectoInvestigacionViaticoIntegrante.objects.get(pk=int(iddetalleviatico))
                                            viaticointegrante.persona_id = integrante
                                            viaticointegrante.nocheestancia = noches
                                            viaticointegrante.valor = valorunitario
                                            viaticointegrante.calculaiva = Decimal(valoriva) > 0
                                            viaticointegrante.valoriva = valoriva
                                            viaticointegrante.valortotal = valortotal
                                            viaticointegrante.observacion = observacion
                                            viaticointegrante.save(request)

                                    # Recorrer los datos de integrantes de movilizaciones
                                    valorunitario = 0
                                    valoriva = 0
                                    valortotal = 0

                                    for iddetalle, iddetallemovilizacion, integrante, ciudad, dias, observacion, idpasaje in zip(idsdetallesmov2, idsdetallesmovilizacion, integrantes_movilizacion, ciudadesmovilizacion, diasmovilizacion, observacionesmovilizacion, lista_id_pasaje):
                                        # Consulto persona
                                        personai = Persona.objects.get(pk=integrante)
                                        nombrepersona = personai.nombre_completo_inverso()

                                        # Nuevo detalle
                                        if int(iddetalle) == 0:
                                            # Guardo detalle presupuesto
                                            itempresupuesto = ProyectoInvestigacionItemPresupuesto(
                                                proyecto=proyecto,
                                                tiporecurso=tiporecurso,
                                                # recurso='VIÁTICOS INTERNACIONALES - ' + nombrepersona,
                                                recurso='MOVILIZACIÓN - ' + nombrepersona,
                                                descripcion=observacion,
                                                unidadmedida_id=1,
                                                cantidad=dias,
                                                valorunitario=valorunitario,
                                                calculaiva=Decimal(valoriva) > 0,
                                                valoriva=valoriva,
                                                valortotal=valortotal,
                                                observacion=observacion
                                            )
                                            itempresupuesto.save(request)

                                            # Guardo detalle de movilización
                                            movilizacionintegrante = ProyectoInvestigacionMovilizacionIntegrante(
                                                proyecto=proyecto,
                                                itempresupuesto=itempresupuesto,
                                                pasajeintegrante_id=idpasaje,
                                                persona_id=integrante,
                                                ciudad=ciudad,
                                                cantidaddia=dias,
                                                valor=valorunitario,
                                                calculaiva=Decimal(valoriva) > 0,
                                                valoriva=valoriva,
                                                valortotal=valortotal,
                                                observacion=observacion,
                                                tipomovilizacion=3
                                            )
                                            movilizacionintegrante.save(request)
                                        else:
                                            # Actualizo detalle de presupuesto
                                            itempresupuesto = ProyectoInvestigacionItemPresupuesto.objects.get(pk=int(iddetalle))
                                            # itempresupuesto.recurso = 'VIÁTICOS INTERNACIONALES - ' + nombrepersona
                                            itempresupuesto.recurso = 'MOVILIZACIÓN - ' + nombrepersona
                                            itempresupuesto.descripcion = observacion
                                            itempresupuesto.unidadmedida_id = 1
                                            itempresupuesto.cantidad = dias
                                            itempresupuesto.valorunitario = valorunitario
                                            itempresupuesto.calculaiva = Decimal(valoriva) > 0
                                            itempresupuesto.valoriva = valoriva
                                            itempresupuesto.valortotal = valortotal
                                            itempresupuesto.observacion = observacion
                                            itempresupuesto.save(request)

                                            # Actualizo detalle de movilización
                                            movilizacionintegrante = ProyectoInvestigacionMovilizacionIntegrante.objects.get(pk=int(iddetallemovilizacion))
                                            movilizacionintegrante.persona_id = integrante
                                            movilizacionintegrante.ciudad = ciudad
                                            movilizacionintegrante.cantidaddia = dias
                                            movilizacionintegrante.valor = valorunitario
                                            movilizacionintegrante.calculaiva = Decimal(valoriva) > 0
                                            movilizacionintegrante.valoriva = valoriva
                                            movilizacionintegrante.valortotal = valortotal
                                            movilizacionintegrante.observacion = observacion
                                            movilizacionintegrante.save(request)

                            else:
                                # Obtengo los items por tipo de recurso del formulario
                                integrantes = request.POST.getlist('integrante_pasaje_VTN[]')
                                if integrantes:
                                    idsdetalles = request.POST.getlist('iddetalle_VTN[]')
                                    idsdetallespasajes = request.POST.getlist('iddetallepasaje_VTN[]')
                                    itinerarios = request.POST.getlist('itinerario_pasaje_VTN[]')
                                    fechassalida = request.POST.getlist('fechasalida_pasaje_VTN[]')
                                    fechasretorno = request.POST.getlist('fecharetorno_pasaje_VTN[]')
                                    actividades = request.POST.getlist('actividad_pasaje_VTN[]')
                                    valorespasajes = request.POST.getlist('valorunitario_pasaje_VTN[]')
                                    valoresiva = request.POST.getlist('valoriva_pasaje_VTN[]')
                                    valorestotales = request.POST.getlist('valortotal_pasaje_VTN[]')
                                    observaciones = request.POST.getlist('observacion_pasaje_VTN[]')

                                    idsdetalles2 = request.POST.getlist('iddetalle_VTN2[]')
                                    idsdetallesviaticos = request.POST.getlist('iddetalleviatico_VTN[]')
                                    integrantes_viatico = request.POST.getlist('idpersonaviaticonac[]')
                                    nochesviatico = request.POST.getlist('nocheestancia_viatico_VTN[]')
                                    valoresviaticos = request.POST.getlist('valorunitario_viatico_VTN[]')
                                    valoresivaviatico = request.POST.getlist('valoriva_viatico_VTN[]')
                                    valorestotalesviatico = request.POST.getlist('valortotal_viatico_VTN[]')
                                    observacionesviatico = request.POST.getlist('observacion_viatico_VTN[]')
                                    lista_id_pasaje = []

                                    # Guardo el detalle de presupuesto de pasajes
                                    for iddetalle, iddetallepasaje, integrante, itinerario, fechasalida, fecharetorno, actividad, valorpasaje, valoriva, valortotal, observacion in zip(idsdetalles, idsdetallespasajes, integrantes, itinerarios, fechassalida, fechasretorno, actividades, valorespasajes, valoresiva, valorestotales, observaciones):
                                        # Consulto persona
                                        personai = Persona.objects.get(pk=integrante)
                                        nombrepersona = personai.nombre_completo_inverso()

                                        # Nuevo detalle
                                        if int(iddetalle) == 0:
                                            # Guardo detalle presupuesto
                                            itempresupuesto = ProyectoInvestigacionItemPresupuesto(
                                                proyecto=proyecto,
                                                tiporecurso=tiporecurso,
                                                recurso='PASAJES AÉREOS NACIONALES - ' + nombrepersona,
                                                descripcion=itinerario,
                                                unidadmedida_id=1,
                                                cantidad=1,
                                                valorunitario=valorpasaje,
                                                calculaiva=Decimal(valoriva) > 0,
                                                valoriva=valoriva,
                                                valortotal=valortotal,
                                                observacion=observacion
                                            )
                                            itempresupuesto.save(request)

                                            # Guardo detalle de pasaje
                                            pasajeintegrante = ProyectoInvestigacionPasajeIntegrante(
                                                proyecto=proyecto,
                                                itempresupuesto=itempresupuesto,
                                                persona_id=integrante,
                                                itinerario=itinerario,
                                                fechasalida=fechasalida,
                                                fecharetorno=fecharetorno,
                                                actividad=actividad,
                                                cantidad=1,
                                                valorunitario=valorpasaje,
                                                calculaiva=Decimal(valoriva) > 0,
                                                valoriva=valoriva,
                                                valortotal=valortotal,
                                                observacion=observacion,
                                                tipopasaje=2
                                            )
                                            pasajeintegrante.save(request)
                                            lista_id_pasaje.append(pasajeintegrante.id)
                                        else:
                                            # Actualizo detalle de presupuesto
                                            itempresupuesto = ProyectoInvestigacionItemPresupuesto.objects.get(pk=int(iddetalle))
                                            itempresupuesto.recurso = 'PASAJES AÉREOS NACIONALES - ' + nombrepersona
                                            itempresupuesto.descripcion = itinerario
                                            itempresupuesto.unidadmedida_id = 1
                                            itempresupuesto.cantidad = 1
                                            itempresupuesto.valorunitario = valorpasaje
                                            itempresupuesto.calculaiva = Decimal(valoriva) > 0
                                            itempresupuesto.valoriva = valoriva
                                            itempresupuesto.valortotal = valortotal
                                            itempresupuesto.observacion = observacion
                                            itempresupuesto.save(request)

                                            # Actualizo detalle de pasaje
                                            pasajeintegrante = ProyectoInvestigacionPasajeIntegrante.objects.get(pk=int(iddetallepasaje))
                                            pasajeintegrante.persona_id = integrante
                                            pasajeintegrante.itinerario = itinerario
                                            pasajeintegrante.fechasalida = fechasalida
                                            pasajeintegrante.fecharetorno = fecharetorno
                                            pasajeintegrante.actividad = actividad
                                            pasajeintegrante.valorunitario = valorpasaje
                                            pasajeintegrante.calculaiva = Decimal(valoriva) > 0
                                            pasajeintegrante.valoriva = valoriva
                                            pasajeintegrante.valortotal = valortotal
                                            pasajeintegrante.observacion = observacion
                                            pasajeintegrante.save(request)
                                            lista_id_pasaje.append(pasajeintegrante.id)

                                    # Guardo el detalle de presupuesto de viáticos
                                    for iddetalle, iddetalleviatico, integrante, noches, valorunitario, valoriva, valortotal, observacion, idpasaje in zip(idsdetalles2, idsdetallesviaticos, integrantes_viatico, nochesviatico, valoresviaticos, valoresivaviatico, valorestotalesviatico, observacionesviatico, lista_id_pasaje):
                                        # Consulto persona
                                        personai = Persona.objects.get(pk=integrante)
                                        nombrepersona = personai.nombre_completo_inverso()

                                        # Nuevo detalle
                                        if int(iddetalle) == 0:
                                            # Guardo detalle presupuesto
                                            itempresupuesto = ProyectoInvestigacionItemPresupuesto(
                                                proyecto=proyecto,
                                                tiporecurso=tiporecurso,
                                                recurso='VIÁTICOS NACIONALES - ' + nombrepersona,
                                                descripcion=observacion,
                                                unidadmedida_id=1,
                                                cantidad=noches,
                                                valorunitario=valorunitario,
                                                calculaiva=Decimal(valoriva) > 0,
                                                valoriva=valoriva,
                                                valortotal=valortotal,
                                                observacion=observacion
                                            )
                                            itempresupuesto.save(request)

                                            # Guardo detalle de viático
                                            viaticointegrante = ProyectoInvestigacionViaticoIntegrante(
                                                proyecto=proyecto,
                                                itempresupuesto=itempresupuesto,
                                                pasajeintegrante_id=idpasaje,
                                                persona_id=integrante,
                                                nocheestancia=noches,
                                                valor=valorunitario,
                                                calculaiva=Decimal(valoriva) > 0,
                                                valoriva=valoriva,
                                                valortotal=valortotal,
                                                observacion=observacion,
                                                tipoviatico=2
                                            )
                                            viaticointegrante.save(request)
                                        else:
                                            # Actualizo detalle de presupuesto
                                            itempresupuesto = ProyectoInvestigacionItemPresupuesto.objects.get(pk=int(iddetalle))
                                            itempresupuesto.recurso = 'VIÁTICOS NACIONALES - ' + nombrepersona
                                            itempresupuesto.descripcion = observacion
                                            itempresupuesto.unidadmedida_id = 1
                                            itempresupuesto.cantidad = noches
                                            itempresupuesto.valorunitario = valorunitario
                                            itempresupuesto.calculaiva = Decimal(valoriva) > 0
                                            itempresupuesto.valoriva = valoriva
                                            itempresupuesto.valortotal = valortotal
                                            itempresupuesto.observacion = observacion
                                            itempresupuesto.save(request)

                                            # Actualizo detalle de viático
                                            viaticointegrante = ProyectoInvestigacionViaticoIntegrante.objects.get(pk=int(iddetalleviatico))
                                            viaticointegrante.persona_id = integrante
                                            viaticointegrante.nocheestancia = noches
                                            viaticointegrante.valor = valorunitario
                                            viaticointegrante.calculaiva = Decimal(valoriva) > 0
                                            viaticointegrante.valoriva = valoriva
                                            viaticointegrante.valortotal = valortotal
                                            viaticointegrante.observacion = observacion
                                            viaticointegrante.save(request)

                    # Si tiene estado ERROR en requisitos, o REQUIERE MODIFICACIONES MENORES/MAYORES se debe poner estado EN EDICIÓN
                    if proyecto.estado.valor in [4, 15, 16, 38, 39]:
                        # Consulto el estado que voy a asignar

                        if proyecto.estado.valor == 4:
                            estado = obtener_estado_solicitud(3, 1)
                        elif proyecto.estado.valor == 15:
                            estado = obtener_estado_solicitud(3, 28)
                        elif proyecto.estado.valor == 16:
                            estado = obtener_estado_solicitud(3, 29)
                        elif proyecto.estado.valor == 38:
                            estado = obtener_estado_solicitud(3, 40)
                        else:
                            estado = obtener_estado_solicitud(3, 41)

                        # Actualizo estado
                        proyecto.estado = estado
                        proyecto.save(request)

                        # Creo el recorrido del proyecto
                        recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                   fecha=datetime.now().date(),
                                                                   observacion=estado.observacion,
                                                                   estado=estado
                                                                   )
                        recorrido.save(request)

                    log(u'%s editó presupuesto de propuesta de proyecto de investigación: %s' % (persona, proyecto), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    x = f.errors
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                # return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addcronograma':
            try:
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                f = CronogramaActividadProyectoInvestigacionForm(request.POST)
                if f.is_valid():
                    objetivos = proyecto.objetivos_especificos()
                    maximomeses = 0
                    fechainiciomin = None
                    fechafinmax = None
                    for objetivo in objetivos:
                        # Obtengo los items por objetivo del formulario
                        actividades = request.POST.getlist('actividad_' + str(objetivo.id) + '[]')
                        ponderaciones = request.POST.getlist('valorponderacion_' + str(objetivo.id) + '[]')
                        fechasinicio = request.POST.getlist('fechainicio_' + str(objetivo.id) + '[]')
                        fechasfin = request.POST.getlist('fechafin_' + str(objetivo.id) + '[]')
                        # entregables = request.POST.getlist('entregable_' + str(objetivo.id) + '[]')
                        # responsablesactividad = request.POST.getlist('codigosresponsables_' + str(objetivo.id) + '[]')
                        responsablesactividad = request.POST.getlist('codigosresponsables_' + str(objetivo.id) + '[]')

                        if actividades:
                            actividadenblanco = [dato for dato in actividades if dato.strip() == '']
                            ponderacionencero = [dato for dato in ponderaciones if Decimal(dato.strip()) == 0]
                            fechainicioenblanco = [dato for dato in fechasinicio if dato.strip() == '']
                            fechafinenblanco = [dato for dato in fechasfin if dato.strip() == '']
                            responsablesenblanco = [dato for dato in responsablesactividad if dato.strip() == '']

                            if actividadenblanco:
                                # return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Actividad deben estar completos [ %s ]" % (objetivo.descripcion)})
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Actividad deben estar completos [ %s ]" % (objetivo.descripcion), "showSwal": "True", "swalType": "warning"})

                            if ponderacionencero:
                                # return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Ponderación deben ser mayores a 0 [ %s ]" % (objetivo.descripcion)})
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Ponderación deben ser mayores a 0 [ %s ]" % (objetivo.descripcion), "showSwal": "True", "swalType": "warning"})

                            if fechainicioenblanco:
                                # return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Fecha inicio deben estar completos [ %s ]" % (objetivo.descripcion)})
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Fecha inicio deben estar completos [ %s ]" % (objetivo.descripcion), "showSwal": "True", "swalType": "warning"})

                            if fechafinenblanco:
                                # return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Fecha inicio deben estar completos [ %s ]" % (objetivo.descripcion)})
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Fecha fin deben estar completos [ %s ]" % (objetivo.descripcion), "showSwal": "True", "swalType": "warning"})
                            
                            if responsablesenblanco:
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Responsables deben estar completos [ %s ]" % (objetivo.descripcion), "showSwal": "True", "swalType": "warning"})
                            
                            for actividad, inicio, fin in zip(actividades, fechasinicio, fechasfin):
                                finicio = datetime.strptime(inicio, '%Y-%m-%d').date()
                                ffin = datetime.strptime(fin, '%Y-%m-%d').date()

                                if finicio > ffin:
                                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La fecha de inicio debe ser menor a la fecha de fin en la actividad:  [ %s ]" % (actividad), "showSwal": "True", "swalType": "warning"})
                                else:
                                    if fechainiciomin is None:
                                        fechainiciomin = finicio

                                    if fechafinmax is None:
                                        fechafinmax = ffin

                                    if finicio < fechainiciomin:
                                        fechainiciomin = finicio

                                    if ffin > fechafinmax:
                                        fechafinmax = ffin

                    mesesactividad = diff_month(fechainiciomin, fechafinmax)
                    # if mesesactividad > maximomeses:
                    #     maximomeses = mesesactividad

                    # Validar que el cronograma cumpla con la cantidad de meses de duración del proyecto
                    # if mesesactividad < proyecto.tiempomes:
                    #     return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La duración en meses de las actividades es inferior a la cantidad de meses de duracion del proyecto. Actividades: %s meses, Proyecto: %s meses" % (mesesactividad, proyecto.tiempomes), "showSwal": "True", "swalType": "warning"})

                    for objetivo in objetivos:
                        # Obtengo los items por tipo de recurso del formulario
                        actividades = request.POST.getlist('actividad_' + str(objetivo.id) + '[]')
                        ponderaciones = request.POST.getlist('valorponderacion_' + str(objetivo.id) + '[]')
                        fechasinicio = request.POST.getlist('fechainicio_' + str(objetivo.id) + '[]')
                        fechasfin = request.POST.getlist('fechafin_' + str(objetivo.id) + '[]')
                        # entregables = request.POST.getlist('entregable_' + str(objetivo.id) + '[]')
                        entregablesactividad = request.POST.getlist('descripcionesentregables_' + str(objetivo.id) + '[]')
                        responsablesactividad = request.POST.getlist('codigosresponsables_' + str(objetivo.id) + '[]')

                        # Si hay datos de actividades en el objetivo
                        if actividades:
                            # Guardo el detalle de actividades del objetivo

                            for actividad, ponderacion, fechainicio, fechafin, entregables, responsables in zip(actividades, ponderaciones, fechasinicio, fechasfin, entregablesactividad, responsablesactividad):
                                cronogramaactividad = ProyectoInvestigacionCronogramaActividad(
                                    objetivo=objetivo,
                                    actividad=actividad,
                                    ponderacion=ponderacion,
                                    fechainicio=fechainicio,
                                    fechafin=fechafin,
                                    entregable=''
                                )
                                cronogramaactividad.save(request)

                                # Guardo los entregables de la actividad
                                if entregables:
                                    for entregable in entregables.split("|"):
                                        if entregable != '':
                                            entregableactividad = ProyectoInvestigacionCronogramaEntregable(
                                                actividad=cronogramaactividad,
                                                entregable=entregable
                                            )
                                            entregableactividad.save(request)

                                # Guardo los responsables de la activividad
                                if responsables:
                                    for responsable in responsables.split(","):
                                        if responsable != '':
                                            responsableactividad = ProyectoInvestigacionCronogramaResponsable(
                                                actividad=cronogramaactividad,
                                                persona_id=responsable
                                            )
                                            responsableactividad.save(request)

                    log(u'%s agregó cronograma de propuesta de proyecto de investigación: %s' % (persona, proyecto), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    x = f.errors
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editcronograma':
            try:
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                itemseliminados = json.loads(request.POST['lista_items1'])

                f = CronogramaActividadProyectoInvestigacionForm(request.POST)
                if f.is_valid():
                    objetivos = proyecto.objetivos_especificos()
                    maximomeses = 0
                    fechainiciomin = None
                    fechafinmax = None
                    for objetivo in objetivos:
                        # Obtengo los items por objetivo del formulario
                        actividades = request.POST.getlist('actividad_' + str(objetivo.id) + '[]')
                        ponderaciones = request.POST.getlist('valorponderacion_' + str(objetivo.id) + '[]')
                        fechasinicio = request.POST.getlist('fechainicio_' + str(objetivo.id) + '[]')
                        fechasfin = request.POST.getlist('fechafin_' + str(objetivo.id) + '[]')
                        # entregables = request.POST.getlist('entregable_' + str(objetivo.id) + '[]')
                        # responsablesactividad = request.POST.getlist('codigosresponsables_' + str(objetivo.id) + '[]')
                        responsablesactividad = request.POST.getlist('codigosresponsables_' + str(objetivo.id) + '[]')

                        if actividades:
                            actividadenblanco = [dato for dato in actividades if dato.strip() == '']
                            ponderacionencero = [dato for dato in ponderaciones if Decimal(dato.strip()) == 0]
                            fechainicioenblanco = [dato for dato in fechasinicio if dato.strip() == '']
                            fechafinenblanco = [dato for dato in fechasfin if dato.strip() == '']
                            responsablesenblanco = [dato for dato in responsablesactividad if dato.strip() == '']

                            # if actividadenblanco:
                            #     return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Actividad deben estar completos [ %s ]" % (objetivo.descripcion)})
                            #
                            #
                            # if ponderacionencero:
                            #     return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Ponderación deben ser mayores a 0 [ %s ]" % (objetivo.descripcion)})
                            #
                            # if fechainicioenblanco:
                            #     return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Fecha inicio deben estar completos [ %s ]" % (objetivo.descripcion)})
                            #
                            # if fechafinenblanco:
                            #     return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Fecha inicio deben estar completos [ %s ]" % (objetivo.descripcion)})

                            if actividadenblanco:
                                # return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Actividad deben estar completos [ %s ]" % (objetivo.descripcion)})
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Actividad deben estar completos [ %s ]" % (objetivo.descripcion), "showSwal": "True", "swalType": "warning"})

                            if ponderacionencero:
                                # return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Ponderación deben ser mayores a 0 [ %s ]" % (objetivo.descripcion)})
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Ponderación deben ser mayores a 0 [ %s ]" % (objetivo.descripcion), "showSwal": "True", "swalType": "warning"})

                            if fechainicioenblanco:
                                # return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Fecha inicio deben estar completos [ %s ]" % (objetivo.descripcion)})
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Fecha inicio deben estar completos [ %s ]" % (objetivo.descripcion), "showSwal": "True", "swalType": "warning"})

                            if fechafinenblanco:
                                # return JsonResponse({"result": "bad", "mensaje": u"Los valores del campo Fecha inicio deben estar completos [ %s ]" % (objetivo.descripcion)})
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Fecha fin deben estar completos [ %s ]" % (objetivo.descripcion), "showSwal": "True", "swalType": "warning"})

                            if responsablesenblanco:
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Los valores del campo Responsables deben estar completos [ %s ]" % (objetivo.descripcion), "showSwal": "True", "swalType": "warning"})

                            # for actividad, inicio, fin in zip(actividades, fechasinicio, fechasfin):
                            #     if datetime.strptime(inicio, '%Y-%m-%d').date() > datetime.strptime(fin, '%Y-%m-%d').date():
                            #         return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio debe ser menor a la fecha de fin en la actividad:  [ %s ]" % (actividad)})

                            for actividad, inicio, fin in zip(actividades, fechasinicio, fechasfin):
                                finicio = datetime.strptime(inicio, '%Y-%m-%d').date()
                                ffin = datetime.strptime(fin, '%Y-%m-%d').date()

                                if finicio > ffin:
                                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La fecha de inicio debe ser menor a la fecha de fin en la actividad:  [ %s ]" % (actividad), "showSwal": "True", "swalType": "warning"})
                                else:
                                    if fechainiciomin is None:
                                        fechainiciomin = finicio

                                    if fechafinmax is None:
                                        fechafinmax = ffin

                                    if finicio < fechainiciomin:
                                        fechainiciomin = finicio

                                    if ffin > fechafinmax:
                                        fechafinmax = ffin


                    mesesactividad = diff_month(fechainiciomin, fechafinmax)
                    # if mesesactividad > maximomeses:
                    #     maximomeses = mesesactividad

                    # Validar que el cronograma cumpla con la cantidad de meses de duración del proyecto
                    if mesesactividad < proyecto.tiempomes:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La duración en meses de las actividades es inferior a la cantidad de meses de duracion del proyecto. Actividades: %s meses, Proyecto: %s meses" % (mesesactividad, proyecto.tiempomes), "showSwal": "True", "swalType": "warning"})

                    # Elimino los detalles que fueron borrados en el formulario
                    for iteme in itemseliminados:
                        # Consulto actividad del cronograma
                        actividad = ProyectoInvestigacionCronogramaActividad.objects.get(pk=int(iteme['iddetalle']))

                        # Consulto y elimino los entregables
                        for entregable in actividad.lista_entregables():
                            entregable.status = False
                            entregable.save(request)

                        # Consulto y elimino los responsables
                        for responsable in actividad.lista_responsables():
                            responsable.status = False
                            responsable.save(request)

                        # Elimino la actividad
                        actividad.status = False
                        actividad.save(request)

                    # Crear y actualizar actividades
                    for objetivo in objetivos:
                        # Obtengo los items por tipo de recurso del formulario
                        idactividades = request.POST.getlist('idactividad_' + str(objetivo.id) + '[]')
                        actividades = request.POST.getlist('actividad_' + str(objetivo.id) + '[]')
                        ponderaciones = request.POST.getlist('valorponderacion_' + str(objetivo.id) + '[]')
                        fechasinicio = request.POST.getlist('fechainicio_' + str(objetivo.id) + '[]')
                        fechasfin = request.POST.getlist('fechafin_' + str(objetivo.id) + '[]')

                        idsentregablesactividad = request.POST.getlist('codigosentregables_' + str(objetivo.id) + '[]')
                        entregablesactividad = request.POST.getlist('descripcionesentregables_' + str(objetivo.id) + '[]')

                        # entregables = request.POST.getlist('entregable_' + str(objetivo.id) + '[]')


                        responsablesactividad = request.POST.getlist('codigosresponsables_' + str(objetivo.id) + '[]')

                        # Si hay datos de actividades en el objetivo
                        if actividades:
                            # Guardo el detalle de actividades del objetivo

                            for idactividad, actividad, ponderacion, fechainicio, fechafin, identregables, entregables, responsables in zip(idactividades, actividades, ponderaciones, fechasinicio, fechasfin, idsentregablesactividad, entregablesactividad, responsablesactividad):
                                # Actividad nueva
                                if int(idactividad) == 0:
                                    cronogramaactividad = ProyectoInvestigacionCronogramaActividad(
                                        objetivo=objetivo,
                                        actividad=actividad,
                                        ponderacion=ponderacion,
                                        fechainicio=fechainicio,
                                        fechafin=fechafin,
                                        entregable=''
                                    )
                                    cronogramaactividad.save(request)

                                    # Guardo los entregables de la activividad
                                    if entregables:
                                        for entregable in entregables.split("|"):
                                            if entregable != '':
                                                entregableactividad = ProyectoInvestigacionCronogramaEntregable(
                                                    actividad=cronogramaactividad,
                                                    entregable=entregable
                                                )
                                                entregableactividad.save(request)

                                    # Guardo los responsables de la activividad
                                    if responsables:
                                        for responsable in responsables.split(","):
                                            if responsable != '':
                                                responsableactividad = ProyectoInvestigacionCronogramaResponsable(
                                                    actividad=cronogramaactividad,
                                                    persona_id=responsable
                                                )
                                                responsableactividad.save(request)
                                else:
                                    cronogramaactividad = ProyectoInvestigacionCronogramaActividad.objects.get(pk=int(idactividad))
                                    cronogramaactividad.actividad = actividad
                                    cronogramaactividad.ponderacion = ponderacion
                                    cronogramaactividad.fechainicio = fechainicio
                                    cronogramaactividad.fechafin = fechafin
                                    # cronogramaactividad.entregable = entregable
                                    cronogramaactividad.save(request)


                                    # Consulto los ids originales de entregables de la actividad
                                    idsorigentregables = cronogramaactividad.lista_ids_entregables()

                                    # Guardo los entregables de la activividad
                                    if entregables:
                                        # Obtener los borrados en pantalla
                                        listaidentregables = identregables.split(",")
                                        listaentregables = entregables.split("|")
                                        excluidos = [c for c in idsorigentregables if str(c) not in listaidentregables]

                                        for id, entregable in zip(listaidentregables, listaentregables):
                                            if entregable != '':
                                                # nuevo
                                                if int(id) == 0:
                                                    entregableactividad = ProyectoInvestigacionCronogramaEntregable(
                                                        actividad=cronogramaactividad,
                                                        entregable=entregable
                                                    )
                                                    entregableactividad.save(request)
                                                else:
                                                    entregableactividad = ProyectoInvestigacionCronogramaEntregable.objects.get(pk=int(id))
                                                    entregableactividad.entregable = entregable
                                                    entregableactividad.save(request)

                                        # Borro los entregables de la actividad
                                        for entregableexcluido in excluidos:
                                            if entregableexcluido != '':
                                                entregableactividad = ProyectoInvestigacionCronogramaEntregable.objects.get(pk=entregableexcluido)
                                                entregableactividad.status = False
                                                entregableactividad.save(request)

                                    else:
                                        excluidos = idsorigentregables
                                        # En caso que haya borrado todos los entregables de la actividad
                                        # Borro los entregables de la atividad
                                        for entregableexcluido in excluidos:
                                            if entregableexcluido != '':
                                                entregableactividad = ProyectoInvestigacionCronogramaEntregable.objects.get(
                                                    pk=entregableexcluido)
                                                entregableactividad.status = False
                                                entregableactividad.save(request)


                                    # Consulto los ids originales de responsables de la actividad
                                    idsresponsables = cronogramaactividad.lista_ids_responsables()

                                    # Guardo los responsables de la actividad
                                    if responsables:
                                        # Obtener los borrados en pantalla
                                        listaresponsables = responsables.split(",")
                                        excluidos = [c for c in idsresponsables if str(c) not in listaresponsables]

                                        for responsable in listaresponsables:
                                            if responsable != '':
                                                # si no existe se lo crea
                                                if not ProyectoInvestigacionCronogramaResponsable.objects.filter(actividad=cronogramaactividad, persona_id=responsable, status=True).exists():
                                                    responsableactividad = ProyectoInvestigacionCronogramaResponsable(
                                                        actividad=cronogramaactividad,
                                                        persona_id=responsable
                                                    )
                                                    responsableactividad.save(request)

                                        # Borro los responsables de la actividad
                                        for personaexcluida in excluidos:
                                            if personaexcluida != '':
                                                responsableactividad = ProyectoInvestigacionCronogramaResponsable.objects.get(actividad=cronogramaactividad, persona_id=personaexcluida, status=True)
                                                responsableactividad.status = False
                                                responsableactividad.save(request)

                                    else:
                                        excluidos = idsresponsables
                                        # En caso que haya borrado todos los responsables de la actividad
                                        # Borro los responsables de la atividad
                                        for personaexcluida in excluidos:
                                            if personaexcluida != '':
                                                responsableactividad = ProyectoInvestigacionCronogramaResponsable.objects.get(actividad=cronogramaactividad, persona_id=personaexcluida, status=True)
                                                responsableactividad.status = False
                                                responsableactividad.save(request)

                    # Si el estado del proyecto NO ES ACEPTADO
                    if proyecto.estado.valor != 13:
                        proyecto.registrado = False
                        proyecto.verificado = None
                        proyecto.documentogenerado = False
                        proyecto.archivodocumentofirmado = None
                        proyecto.archivodocumentosindatint = None
                        proyecto.estadodocumentofirmado = 1

                    proyecto.save(request)

                    # Si tiene estado ERROR en requisitos, o REQUIERE MODIFICACIONES MENORES/MAYORES se debe poner estado EN EDICIÓN
                    if proyecto.estado.valor in [4, 15, 16, 38, 39]:
                        # Consulto el estado que voy a asignar

                        if proyecto.estado.valor == 4:
                            estado = obtener_estado_solicitud(3, 1)
                        elif proyecto.estado.valor == 15:
                            estado = obtener_estado_solicitud(3, 28)
                        elif proyecto.estado.valor == 16:
                            estado = obtener_estado_solicitud(3, 29)
                        elif proyecto.estado.valor == 38:
                            estado = obtener_estado_solicitud(3, 40)
                        else:
                            estado = obtener_estado_solicitud(3, 41)

                        # Actualizo estado
                        proyecto.estado = estado
                        proyecto.save(request)

                        # Creo el recorrido del proyecto
                        recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                   fecha=datetime.now().date(),
                                                                   observacion=estado.observacion,
                                                                   estado=estado
                                                                   )
                        recorrido.save(request)

                    log(u'%s editó cronograma de propuesta de proyecto de investigación: %s' % (persona, proyecto), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    x = f.errors
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'generardocumento':
            try:
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                ponderacion = proyecto.total_ponderacion_actividades()
                dif = abs(proyecto.montototal - proyecto.presupuesto)
                mesesactividades = proyecto.total_meses_actividades()
                cantidadintegrantes = proyecto.cantidad_integrantes_unemi()
                difmeses = proyecto.tiempomes - mesesactividades if proyecto.tiempomes >= mesesactividades else 0

                if ponderacion != 100 or dif > 0.05 or difmeses > 1 or cantidadintegrantes < proyecto.convocatoria.minintegranteu:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se puede generar el documento debido a que la información de la propuesta está incompleta", "showSwal": "True", "swalType": "warning"})

                if proyecto.integrantes_director_codirector_novedad():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se puede generar el documento debido a uno o más investigadores presentan novedades", "showSwal": "True", "swalType": "warning"})

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
                        detalle.entregable if detalle.entregable else detalle.lista_html_entregables(),
                        detalle.lista_html_nombres_responsables()
                    ])

                data['datoscronograma'] = datoscronograma
                data['listaobjetivos'] = listaobjetivos
                data['totalponderacion'] = totalponderacion
                data['objetivogeneralcronograma'] = reemplazar_fuente_para_formato_inscripcion(proyecto.objetivogeneral, "Berlin Sans FB Demi", "10")

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
                    proyecto.archivodocumentosindatint = None
                    proyecto.estadodocumentofirmado = 1
                else:
                    proyecto.archivodocumentoact = 'proyectoinvestigacion/documentos/' + nombrearchivoresultado

                proyecto.save(request)

                if not 'tipo' in request.POST:
                    # Guardar historial de archivos
                    tipodocumento = TipoDocumento.objects.get(pk=1)
                    guardar_historial_archivo_proyectos_investigacion(proyecto, tipodocumento, proyecto.archivodocumento, request)

                log(f'{persona} generó formulario de inscripción de proyecto: {proyecto}', request, "edit")
                return JsonResponse({"result": "ok", "idf": encrypt(proyecto.id)})
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

                proyecto.observacion = ''
                proyecto.observaciondocumentofirmado = ''
                proyecto.archivodocumentofirmado = archivo
                proyecto.save(request)

                # Guardar historial de archivos
                tipodocumento = TipoDocumento.objects.get(pk=2)
                guardar_historial_archivo_proyectos_investigacion(proyecto, tipodocumento, proyecto.archivodocumentofirmado, request)

                log(f'{persona} subió formato inscripción de proyecto firmado: {proyecto}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True, "id": encrypt(proyecto.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

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

                archivo._name = generar_nombre("presupuestofinal", archivo._name)

                proyecto.archivopresupuesto = archivo
                proyecto.save(request)

                log(u'%s subió archivo del presupuesto final del proyecto: %s' % (persona, proyecto), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True, "id": encrypt(proyecto.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'subircertificadoinvestigador':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivo = request.FILES['archivocertificado']
                descripcionarchivo = 'Archivo del Certificado de Registro'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto el integrante del Proyecto
                integrante = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.POST['id'])))
                proyecto = integrante.proyecto

                archivo._name = generar_nombre("certificadoinvestigador", archivo._name)

                integrante.archivoacreditado = archivo
                integrante.observacion = ''
                integrante.estadoacreditado = 1
                integrante.save(request)

                # Actualizar el proyecto si se presentaron novedades en la verificación o evaluaciones
                if proyecto.estado.valor in [4, 15, 16, 38, 39]:
                    # Consulto el estado que voy a asignar
                    if proyecto.estado.valor == 4:
                        estado = obtener_estado_solicitud(3, 1)
                    elif proyecto.estado.valor == 15:
                        estado = obtener_estado_solicitud(3, 28)
                    elif proyecto.estado.valor == 16:
                        estado = obtener_estado_solicitud(3, 29)
                    elif proyecto.estado.valor == 38:
                        estado = obtener_estado_solicitud(3, 40)
                    else:
                        estado = obtener_estado_solicitud(3, 41)

                    # Actualizo estado
                    proyecto.estado = estado
                    proyecto.save(request)

                    # Creo el recorrido del proyecto
                    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                               fecha=datetime.now().date(),
                                                               observacion=estado.observacion,
                                                               estado=estado
                                                               )
                    recorrido.save(request)

                log(f'{persona} subió certificado de registro de investigador para el integrante {integrante}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'subirhojavida':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivo = request.FILES['archivohojavida']
                descripcionarchivo = 'Archivo de la Hoja de vida'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto el integrante del Proyecto
                integrante = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.POST['id'])))
                proyecto = integrante.proyecto

                archivo._name = generar_nombre("hojavidainvexterno", archivo._name)

                integrante.archivohojavida = archivo
                integrante.save(request)

                if proyecto.estadointegrante == 4:
                    proyecto.estadointegrante = 1
                    proyecto.observacionintegrante = ''
                    proyecto.save(request)

                # Actualizar el proyecto si se presentaron novedades en la verificación o evaluaciones
                if proyecto.estado.valor in [4, 15, 16, 38, 39]:
                    # Consulto el estado que voy a asignar
                    if proyecto.estado.valor == 4:
                        estado = obtener_estado_solicitud(3, 1)
                    elif proyecto.estado.valor == 15:
                        estado = obtener_estado_solicitud(3, 28)
                    elif proyecto.estado.valor == 16:
                        estado = obtener_estado_solicitud(3, 29)
                    elif proyecto.estado.valor == 38:
                        estado = obtener_estado_solicitud(3, 40)
                    else:
                        estado = obtener_estado_solicitud(3, 41)

                    # Actualizo estado
                    proyecto.estado = estado
                    proyecto.save(request)

                    # Creo el recorrido del proyecto
                    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                               fecha=datetime.now().date(),
                                                               observacion=estado.observacion,
                                                               estado=estado
                                                               )
                    recorrido.save(request)

                log(f'{persona} subió hoja de vida para el integrante {integrante}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'finalizaedicion':
            try:
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                f = FinalizaEdicionForm(request.POST)
                if f.is_valid():
                    contenidocorreo = f.cleaned_data['contenido']

                    # Si tiene estado EN EDICIÓN
                    if proyecto.estado.valor == 1:
                        # Verifico si en el recorrido existe PROPUESTA DE PROYECTO REGISTRADA
                        tiene_estado_registrada = ProyectoInvestigacionRecorrido.objects.values("id").filter(status=True, proyecto=proyecto, estado__valor=2).exists()

                        # Consulto el estado que voy a asignar
                        estado = obtener_estado_solicitud(3, 2) # if tiene_estado_registrada is False else obtener_estado_solicitud(3, 5)
                        proyecto.estado = estado
                        proyecto.registrado = True
                        proyecto.save(request)

                        # Creo el recorrido del proyecto
                        recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                   fecha=datetime.now().date(),
                                                                   observacion='Propuesta de Proyecto Registrada', # if tiene_estado_registrada is False else 'PROPUESTA DE PROYECTO ACTUALIZADA',
                                                                   estado=estado
                                                                   )
                        recorrido.save(request)
                    else:
                        # Estado EN EDICIÓN por MODIFICACIONES MENORES / MAYORES
                        # Consulto el estado que voy a asignar
                        if proyecto.estado.valor == 28:
                            estado = obtener_estado_solicitud(3, 30)
                        elif proyecto.estado.valor == 29:
                            estado = obtener_estado_solicitud(3, 31)
                        elif proyecto.estado.valor == 40:
                            estado = obtener_estado_solicitud(3, 42)
                        else:
                            estado = obtener_estado_solicitud(3, 43)

                        proyecto.estado = estado
                        proyecto.registrado = True
                        proyecto.save(request)

                        # Creo el recorrido del proyecto
                        recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                   fecha=datetime.now().date(),
                                                                   observacion=estado.observacion,
                                                                   estado=estado
                                                                   )
                        recorrido.save(request)

                    # Envio de e-mail de notificacion al solicitante
                    # listacuentascorreo = [23, 24, 25, 26, 27]
                    # posgrado1_unemi@unemi.edu.ec
                    # posgrado2_unemi@unemi.edu.ec
                    # posgrado3_unemi@unemi.edu.ec
                    # posgrado4_unemi@unemi.edu.ec
                    # posgrado5_unemi@unemi.edu.ec

                    # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                    listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, . . .sga7@unemi.edu.ec

                    # Destinatarios
                    lista_email_envio = []
                    lista_email_cco = []
                    lista_adjuntos = [proyecto.archivodocumentofirmado]

                    lista_email_envio.append('proyectosdeinvestigacion@unemi.edu.ec')
                    for integrante in proyecto.integrantes_proyecto():
                        lista_email_envio += integrante.persona.lista_emails_envio()

                    fechaenvio = datetime.now().date()
                    horaenvio = datetime.now().time()
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
                    tituloemail = "Registro de Propuesta de Proyecto de Investigación"
                    titulo = "Proyectos de Investigación"
                    send_html_mail(tituloemail,
                                   "emails/propuestaproyectoinvestigacion.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'contenidocorreo': contenidocorreo,
                                    'tiponotificacion': 'REGDOC'
                                    },
                                   lista_email_envio,
                                   lista_email_cco,
                                   lista_adjuntos,
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )
                    log(f'{persona} finalizó edición de la propuesta de proyecto {proyecto}', request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

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

                # Obtengo el estado EN EJECUCIÓN
                estado = obtener_estado_solicitud(3, 20)

                # Guardo el archivo del contrato y actualizo el estado
                proyectoinvestigacion.archivocontratoejecucion = archivo
                proyectoinvestigacion.estado = estado
                proyectoinvestigacion.ejecucion = 1
                proyectoinvestigacion.save(request)

                # Creo el recorrido del proyecto
                recorrido = ProyectoInvestigacionRecorrido(proyecto=proyectoinvestigacion,
                                                           fecha=datetime.now().date(),
                                                           observacion='PROYECTO EN EJECUCIÓN',
                                                           estado=estado
                                                           )
                recorrido.save(request)

                # Crea el historial del archivo
                historialarchivo = ProyectoInvestigacionHistorialArchivo(
                    proyecto=proyectoinvestigacion,
                    tipo=5,
                    archivo=proyectoinvestigacion.archivocontratoejecucion
                )
                historialarchivo.save(request)

                # # Consulto el cronograma de actividades y se asigna estado EN EJECUCIÓN a aquellas que ya estén dentro del rango de fecha de inicio y fin de la actividad
                # # Para el caso de los proyectos 2020, para 2022 no se ejecuta la actualizacion de estado
                # hoy = datetime.now().date()
                # actividades = proyectoinvestigacion.cronograma_detallado()
                # for actividad in actividades:
                #     if actividad.fechainicio <= hoy <= actividad.fechafin:
                #         # Asignar estado EN EJECUCIÓN
                #         actividad.estado = 2
                #         actividad.save(request)
                #     elif hoy >= actividad.fechainicio and hoy > actividad.fechafin:
                #         # Asignar estado PENDIENTE
                #         actividad.estado = 4
                #         actividad.save(request)
                #
                # # Genero el detalle de fechas para los registros de informes del proyecto
                # fechainicio = proyectoinvestigacion.fechainicio
                # tiempo = proyectoinvestigacion.convocatoria.periodocidad.valor #Trimestral
                # duracion = proyectoinvestigacion.tiempomes
                # cantidad = ceil(duracion / tiempo)
                # desde = fechainicio
                #
                # # Informes según la periodicidad de tiempo (Ej: Informes trimestrales)
                # secuencia = 1
                # for n in range(1, cantidad):
                #     desde = desde + relativedelta(months=tiempo)
                #     hasta = (desde + relativedelta(months=tiempo)) - relativedelta(days=1)
                #     # Guardo registro informe PARCIAL
                #     informeproyecto = ProyectoInvestigacionInforme(
                #         proyecto=proyectoinvestigacion,
                #         tipo=1,
                #         secuencia=secuencia,
                #         fechainicio=desde,
                #         fechafin=hasta,
                #         generado=False,
                #         estado=1
                #     )
                #     informeproyecto.save(request)
                #     secuencia += 1
                #
                # # Informe final
                # desde = desde + relativedelta(months=tiempo)
                # hasta = (desde + relativedelta(months=tiempo)) - relativedelta(days=1)
                # # Guardo registro informe FINAL
                # informeproyecto = ProyectoInvestigacionInforme(
                #     proyecto=proyectoinvestigacion,
                #     tipo=2,
                #     secuencia=secuencia,
                #     fechainicio=desde,
                #     fechafin=hasta,
                #     generado=False,
                #     estado=1
                # )
                # informeproyecto.save(request)

                # # Informe final
                # desde = desde + relativedelta(months=tiempo)
                # hasta = (desde + relativedelta(months=1)) - relativedelta(days=1)
                #
                # # Guardo registro informe FINAL
                # informeproyecto = ProyectoInvestigacionInforme(
                #     proyecto=proyectoinvestigacion,
                #     tipo=2,
                #     secuencia=secuencia,
                #     fechainicio=desde,
                #     fechafin=hasta,
                #     generado=False,
                #     estado=1
                # )
                # informeproyecto.save(request)

                log(u'Agregó contrato de financiamiento al proyecto: %s' % (proyectoinvestigacion), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

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

        elif action == 'addinforme':
            try:
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                periodovigente = Periodo.objects.get(pk=int(encrypt(request.POST['idperiodovigente']))) if request.POST['idperiodovigente'] else None

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
                        tipo=int(request.POST['tipoinforme']),
                        secuencia=secuencia,
                        generado=False,
                        fecha=datetime.now().date(),
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

                        fechainicio = datetime.strptime(actividad['fechainicio'], '%d-%m-%Y').date()
                        fechafin = datetime.strptime(actividad['fechafin'], '%d-%m-%Y').date()

                        # Creo detalle de actividad del informe
                        actividadinforme = ProyectoInvestigacionInformeActividad(
                            informe=informeproyecto,
                            actividad_id=actividad['ida'],
                            entregable=actividad['entregable'],
                            fechainicio=fechainicio,
                            fechafin=fechafin,
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
                        actividadcronograma.fechainicio = fechainicio
                        actividadcronograma.fechafin = fechafin
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

                    # Notifico por e-mail a la coordinación de investigación
                    # De donde se origina el correo
                    listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, . . .sga7@unemi.edu.ec

                    # Destinatarios
                    # lista_email_envio = ['investigacion@unemi.edu.ec']
                    lista_email_envio = ['ivan_saltos_medina@hotmail.com']
                    lista_email_cco = ['isaltosm@unemi.edu.ec']

                    # for integrante in informeproyecto.proyecto.integrantes_proyecto():
                    #     lista_email_envio += integrante.persona.lista_emails_envio()

                    fechaenvio = datetime.now().date()
                    horaenvio = datetime.now().time()
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                    tituloemail = "Registro de Informe de avance de Proyecto de Investigación"
                    tiponotificacion = "AGREGAINFORME"

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
                                    'tipoinforme': 'un informe de avance' if informeproyecto.tipo == 1 else 'el informe final',
                                    'proyecto': proyecto
                                    },
                                   lista_email_envio,  # Destinatarioa
                                   lista_email_cco,  # Copia oculta
                                   lista_archivos_adjuntos,  # Adjunto(s)
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                    log(u'%s agregó informe al proyecto: %s' % (persona, informeproyecto.proyecto), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El número de informe ya ha sido ingresado", "showSwal": "True", "swalType": "warning"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editinforme':
            try:
                informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['id'])))
                proyecto = informeproyecto.proyecto

                # Verifico si fue revisado o rechazado por el técnico de investigación
                if informeproyecto.estado in [5, 7]:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el informe debido a que fue revisado por Investigación", "showSwal": "True", "swalType": "warning"})

                notificar = informeproyecto.estado in [6, 8]

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
                informeproyecto.tipo = int(request.POST['tipoinforme'])
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

                    fechainicio = datetime.strptime(actividad['fechainicio'], '%d-%m-%Y').date()
                    fechafin = datetime.strptime(actividad['fechafin'], '%d-%m-%Y').date()

                    # Nuevo
                    if int(actividad['idreg']) == 0:
                        # Creo detalle de actividad del informe
                        actividadinforme = ProyectoInvestigacionInformeActividad(
                            informe=informeproyecto,
                            actividad_id=actividad['ida'],
                            entregable=actividad['entregable'],
                            fechainicio=fechainicio,
                            fechafin=fechafin,
                            cantidadhora=actividad['cantidadhora'],
                            porcentajeejecucion=actividad['avance'],
                            observacion=actividad['observacion'],
                            estado=estado
                        )
                    else:
                        # Consulto y actualizo el detalle de actividad
                        actividadinforme = ProyectoInvestigacionInformeActividad.objects.get(pk=actividad['idreg'])
                        actividadinforme.entregable = actividad['entregable']
                        actividadinforme.fechainicio = fechainicio
                        actividadinforme.fechafin = fechafin
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
                    actividadcronograma.fechainicio = fechainicio
                    actividadcronograma.fechafin = fechafin
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
                informeproyecto.avanceesperado = proyecto.porcentaje_avance_esperado()
                informeproyecto.porcentajeejecucion = proyecto.porcentaje_avance_ejecucion()
                informeproyecto.save(request)

                # Notificar por e-mail a la coordinación de investigación
                if notificar:
                    # De donde se origina el correo
                    listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, . . .sga7@unemi.edu.ec

                    # Destinatarios
                    # lista_email_envio = ['investigacion@unemi.edu.ec']
                    lista_email_envio = ['ivan_saltos_medina@hotmail.com']
                    lista_email_cco = ['isaltosm@unemi.edu.ec']

                    # for integrante in informeproyecto.proyecto.integrantes_proyecto():
                    #     lista_email_envio += integrante.persona.lista_emails_envio()

                    fechaenvio = datetime.now().date()
                    horaenvio = datetime.now().time()
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                    tituloemail = "Actualización de Informe de Avance de Proyecto de Investigación" if informeproyecto.tipo == 1 else "Actualización de Informe Final de Proyecto de Investigación"
                    tiponotificacion = "EDITAINFORME"

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
                                    'tipoinforme': 'un informe de avance' if informeproyecto.tipo == 1 else 'el informe final',
                                    'proyecto': informeproyecto.proyecto
                                    },
                                   lista_email_envio,  # Destinatarioa
                                   lista_email_cco,  # Copia oculta
                                   lista_archivos_adjuntos,  # Adjunto(s)
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                log(u'%s editó informe del proyecto: %s' % (persona, informeproyecto.proyecto), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'informetecnicopdf':
            try:
                data = {}

                informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['id'])))

                if not informeproyecto.generado:
                    data['fechaactual'] = datetime.now().date()
                    data['informeproyecto'] = informeproyecto
                    data['proyecto'] = proyecto = informeproyecto.proyecto
                    data['avanceesperado'] = informeproyecto.avanceesperado
                    data['avanceejecucion'] = informeproyecto.porcentajeejecucion
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

                # return JsonResponse({"result": "ok", "documento": informeproyecto.archivogenerado.url})
                return JsonResponse({"result": "ok", "idi": encrypt(informeproyecto.id), "id": encrypt(informeproyecto.proyecto.id)})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento del informe. [%s]" % msg})

        elif action == 'informetecnicofinalpdf':
            try:
                data = {}

                informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['id'])))

                if not informeproyecto.generado:
                    data['informe'] = informeproyecto
                    data['proyecto'] = proyecto = informeproyecto.proyecto
                    data['instituciones'] = proyecto.instituciones_proyecto()
                    data['integrantes'] = integrantes = proyecto.integrantes_proyecto_informe()

                    # Creacion de los archivos por separado
                    directorio = SITE_STORAGE + '/media/proyectoinvestigacion/informes'
                    try:
                        os.stat(directorio)
                    except:
                        os.mkdir(directorio)

                    # Archivo de la parte 1 del informe
                    nombrearchivo = 'informeparte1_' + str(proyecto.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                    valida = convert_html_to_pdf(
                        'pro_proyectoinvestigacion/informefinalpdf.html',
                        {'pagesize': 'A4', 'data': data},
                        nombrearchivo,
                        directorio
                    )

                    if not valida:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento de la parte 1 del informe."})

                    archivo1 = directorio + "/" + nombrearchivo

                    # Archivo separador de anexos
                    data['tipoanexo'] = "ANEXOS EJECUCIÓN FINANCIERA"
                    nombrearchivo = 'separador1_' + str(proyecto.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                    valida = convert_html_to_pdf(
                        'pro_proyectoinvestigacion/separadorpdf.html',
                        {'pagesize': 'A4', 'data': data},
                        nombrearchivo,
                        directorio
                    )

                    if not valida:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento de la parte 1 del informe."})

                    archivosep1 = directorio + "/" + nombrearchivo

                    # Leer los archivos
                    pdf1Reader = PyPDF2.PdfFileReader(archivo1)
                    pdfSepReader = PyPDF2.PdfFileReader(archivosep1)

                    # Crea un nuevo objeto PdfFileWriter que representa un documento PDF en blanco
                    pdfWriter = PyPDF2.PdfFileWriter()

                    # Recorre todas las páginas del documento 1
                    for pageNum in range(pdf1Reader.numPages):
                        pageObj = pdf1Reader.getPage(pageNum)
                        pdfWriter.addPage(pageObj)

                    # Agregar documento con página separador
                    pageObj = pdfSepReader.getPage(0)
                    pdfWriter.addPage(pageObj)

                    # Recorrido detalle evidencias ejecución financiera
                    for evidencia in informeproyecto.ejecucion_financiera():
                        archivoevidencia = SITE_STORAGE + evidencia.archivo.url  # Archivo pdf evidencia
                        pdf2ReaderEvi = PyPDF2.PdfFileReader(archivoevidencia)

                        # Recorre todas las páginas del documento de evidencia: pdf2ReaderEvi
                        for pageNum in range(pdf2ReaderEvi.numPages):
                            pageObj = pdf2ReaderEvi.getPage(pageNum)
                            pdfWriter.addPage(pageObj)

                    # Si existen capacitaciones se debe adjuntar evidencias
                    if informeproyecto.aplicacapacitacion:
                        # Archivo separador de anexos
                        data['tipoanexo'] = "ANEXOS JORNADAS DE CAPACITACIÓN"
                        nombrearchivo = 'separador2_' + str(proyecto.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                        valida = convert_html_to_pdf(
                            'pro_proyectoinvestigacion/separadorpdf.html',
                            {'pagesize': 'A4', 'data': data},
                            nombrearchivo,
                            directorio
                        )

                        if not valida:
                            return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento de la parte 1 del informe."})

                        archivosep2 = directorio + "/" + nombrearchivo

                        pdfSepReader = PyPDF2.PdfFileReader(archivosep2)

                        # Agregar documento con página separador
                        pageObj = pdfSepReader.getPage(0)
                        pdfWriter.addPage(pageObj)

                        # Recorrido detalle evidencias capacitaciones realizadas
                        for evidencia in informeproyecto.capacitaciones_realizadas():
                            archivoevidencia = SITE_STORAGE + evidencia.archivo.url  # Archivo pdf evidencia
                            pdf2ReaderEvi = PyPDF2.PdfFileReader(archivoevidencia)

                            # Recorre todas las páginas del documento de evidencia: pdf2ReaderEvi
                            for pageNum in range(pdf2ReaderEvi.numPages):
                                pageObj = pdf2ReaderEvi.getPage(pageNum)
                                pdfWriter.addPage(pageObj)

                    # Archivo separador de anexos
                    data['tipoanexo'] = "ANEXOS PUBLICACIONES"
                    nombrearchivo = 'separador3_' + str(proyecto.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                    valida = convert_html_to_pdf(
                        'pro_proyectoinvestigacion/separadorpdf.html',
                        {'pagesize': 'A4', 'data': data},
                        nombrearchivo,
                        directorio
                    )

                    if not valida:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento de la parte 1 del informe."})

                    archivosep3 = directorio + "/" + nombrearchivo

                    pdfSepReader = PyPDF2.PdfFileReader(archivosep3)

                    # Agregar documento con página separador
                    pageObj = pdfSepReader.getPage(0)
                    pdfWriter.addPage(pageObj)

                    # Recorrido detalle evidencias publicaciones
                    for evidencia in informeproyecto.publicaciones():
                        archivoevidencia = SITE_STORAGE + evidencia.archivo.url  # Archivo pdf evidencia
                        pdf2ReaderEvi = PyPDF2.PdfFileReader(archivoevidencia)

                        # Recorre todas las páginas del documento de evidencia: pdf2ReaderEvi
                        for pageNum in range(pdf2ReaderEvi.numPages):
                            pageObj = pdf2ReaderEvi.getPage(pageNum)
                            pdfWriter.addPage(pageObj)

                    # Archivo separador de anexos
                    data['tipoanexo'] = "ANEXOS PARTICIPACIÓN EVENTOS CIENTÍFICOS"
                    nombrearchivo = 'separador4_' + str(proyecto.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                    valida = convert_html_to_pdf(
                        'pro_proyectoinvestigacion/separadorpdf.html',
                        {'pagesize': 'A4', 'data': data},
                        nombrearchivo,
                        directorio
                    )

                    if not valida:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento de la parte 1 del informe."})

                    archivosep4 = directorio + "/" + nombrearchivo

                    pdfSepReader = PyPDF2.PdfFileReader(archivosep4)

                    # Agregar documento con página separador
                    pageObj = pdfSepReader.getPage(0)
                    pdfWriter.addPage(pageObj)

                    # Recorrido detalle evidencias eventos científicos
                    for evidencia in informeproyecto.eventos_cientificos():
                        archivoevidencia = SITE_STORAGE + evidencia.archivo.url  # Archivo pdf evidencia
                        pdf2ReaderEvi = PyPDF2.PdfFileReader(archivoevidencia)

                        # Recorre todas las páginas del documento de evidencia: pdf2ReaderEvi
                        for pageNum in range(pdf2ReaderEvi.numPages):
                            pageObj = pdf2ReaderEvi.getPage(pageNum)
                            pdfWriter.addPage(pageObj)

                    # Luego de haberse copiado todas las paginas de todos los documentos, se las escribe en el documento en blanco
                    fecha = datetime.now().date()
                    hora = datetime.now().time()
                    nombrearchivoresultado = 'informefinalpdf' + fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__() + '.pdf'
                    pdfOutputFile = open(directorio + "/" + nombrearchivoresultado, "wb")
                    pdfWriter.write(pdfOutputFile)

                    # Borro los documento individuales creados a exepción del archivo del proyecto cargado por el docente
                    os.remove(archivo1)
                    os.remove(archivosep1)

                    if informeproyecto.aplicacapacitacion:
                        os.remove(archivosep2)

                    os.remove(archivosep3)
                    os.remove(archivosep4)

                    pdfOutputFile.close()

                    # Actualizo la ruta en el infome
                    informeproyecto.archivogenerado = 'proyectoinvestigacion/informes/' + nombrearchivoresultado
                    informeproyecto.generado = True
                    informeproyecto.save(request)

                    log(f'{persona} generó informe del proyecto {informeproyecto.proyecto}', request, "edit")

                return JsonResponse({"result": "ok", "idi": encrypt(informeproyecto.id), "id": encrypt(informeproyecto.proyecto.id)})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento del informe. [%s]" % msg})

        elif action == 'firmarinformeavance':
            try:
                if 'iddoc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivofirma = request.FILES['archivofirma']
                clavefirma = request.POST['cfirma']
                descripcionarchivo = 'Archivo de la firma electrónica'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivofirma, ['P12', 'PFX'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto el informe
                informe = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['iddoc'])))

                # Obtengo el archivo del informe
                archivoinforme = informe.archivogenerado
                rutapdfarchivo = SITE_STORAGE + archivoinforme.url
                textoabuscar = informe.nombre_firma_elabora()
                textofirma = 'Elaborado por:'
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
                informe.firmaelabora = True
                informe.save(request)

                log(u'%s firmó informe de proyecto de investigación : %s' % (persona, informe), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Documento firmado con éxito", "showSwal": True, "idi": encrypt(informe.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'subirinforme':
            try:
                if not 'idinforme' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['idinforme'])))

                # Verificar que el informe no hay sido validado o rechazado por la coordinación
                if informeproyecto.estado == 10:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se puede subir el archivo debido a que la coordinación ya realizó la revisión de un documento anterior", "showSwal": "True", "swalType": "warning"})

                archivo = request.FILES['archivoinforme']
                descripcionarchivo = 'Archivo del informe firmado'
                tipoinforme = "avance" if informeproyecto.tipo == 1 else "final"

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '10MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                archivo._name = generar_nombre("informeproyecto" + tipoinforme, archivo._name)

                # Guardo el archivo del informe
                informeproyecto.archivo = archivo
                informeproyecto.firmaelabora = True
                informeproyecto.estado = 4
                informeproyecto.save(request)

                log(u'Agregó archivo del informe firmado: %s' % (informeproyecto), request, "add")
                # return JsonResponse({"result": "ok"})
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                # return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})


        elif action == 'addinformefinal':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                if proyecto:
                    # Obtener secuencia y numeración del informe
                    secuencia = proyecto.secuencia_informe_avance()
                    numero = str(secuencia).zfill(3) + "-PROY-" + proyecto.codigo

                    # Obtener periodo vigente del distributivo del profesor
                    periodovigente = periodo_vigente_distributivo_docente_investigacion(proyecto.profesor)

                    # Obtener los valores de los campos del formulario
                    adenda = request.POST['adenda'] == '1'
                    prorroga = request.POST['prorroga'] == '1'
                    mesprorroga = int(request.POST['mesesprorroga']) if request.POST['mesesprorroga'] else 0
                    fechafinproyecto = datetime.strptime(request.POST['fechafin'], '%Y-%m-%d').date()
                    porcentajeejecucion = request.POST['promediocumpl']
                    montoejecutado = request.POST['montoejecutado']
                    porcentajepresup = request.POST['porcentajepresup']
                    aplicacapacitacion = request.POST['aplicacapacitacion'] == '1'
                    capacitacion = request.POST['detallecapacitacion'].strip()
                    aplicadisemresultado = request.POST['aplicadisemresultado'] == '1'
                    disemresultado = request.POST['detalledisemresultado'].strip()
                    obtuvoproductopat = request.POST['productopatentable'] == '1'
                    productopatentable = request.POST['detalleproductopatentable'].strip()
                    conclusion = reemplazar_fuente_para_informe(request.POST['conclusion'].strip())
                    continuacion = reemplazar_fuente_para_informe(request.POST['continuacion'].strip())
                    lineabase = reemplazar_fuente_para_informe(request.POST['lineabase'].strip())
                    indicadorgeneral = request.POST['indicadorgeneral'].strip()
                    fuentedatosgeneral = request.POST['fuentedatosgeneral'].strip()
                    lineabasegeneral = request.POST['lineabasegeneral'].strip()

                    # Obtener los valores de los detalles del formulario
                    # Cumplimiento técnico por cada objetivo específico
                    idsobjetivo_ejecucion = request.POST.getlist('idobjetivo_ejecucion[]')  # Ids objetivos ejecución
                    porcentajesejecucion = request.POST.getlist('porcentajeejecucion[]')  # Porcentajes de ejecución
                    # Ejecución Financiera
                    nfilas_ca_presup = json.loads(request.POST['lista_items1']) if 'lista_items1' in request.POST else []  # Números de filas que tienen lleno el campo archivo en detalle de presupuesto
                    nfilas_presup = request.POST.getlist('nfila_evidencia[]')  # Todos los número de filas del detalle de evidencias de presupuesto
                    descripciones_presup = request.POST.getlist('descripcion_evidencia[]')  # Todas las descripciones detalle presupuesto
                    archivos_presup = request.FILES.getlist('archivo_evidencia[]')  # Todos los archivos detalle presupuesto
                    # Cómo se cumplió con el objetivo general y los específicos planteados en la propuesta original
                    descripcionesobjetivo = request.POST.getlist('descripcionobjetivo[]')  # Descripciones de objetivos
                    detallesobjetivo = request.POST.getlist('detalleobjetivo[]')  # Detalles de cumplimiento de objetivos
                    # Resultados significativos del proyecto
                    resultados = request.POST.getlist('resultado[]')  # Resultados
                    descripcionesresultado = request.POST.getlist('descripcionresultado[]')  # Descripciones como se lograron los resultados
                    resultadosagregados = request.POST.getlist('agregado[]')  # Resultados agregados
                    # Oportunidades de entrenamiento y capacitación profesional
                    nfilas_ca_capacitacion = json.loads(request.POST['lista_items2']) if 'lista_items2' in request.POST else []  # Números de filas que tienen lleno el campo archivo en detalle de capacitaciones
                    nfilas_capacitacion = request.POST.getlist('nfila_capacitacion[]')  # Todos los número de filas del detalle de evidencias de capacitación
                    descripciones_capacitacion = request.POST.getlist('descripcion_capacitacion[]')  # Todas las descripciones detalle capacitaciones
                    fechas_inicio = request.POST.getlist('fecha_inicio[]')  # Todas las fechas inicio detalle capacitaciones
                    fechas_fin = request.POST.getlist('fecha_fin[]')  # Todas las fechas inicio detalle capacitaciones
                    lugares_capacitacion = request.POST.getlist('lugar_capacitacion[]')  # Todas los lugares detalle capacitaciones
                    npersonas_capacitadas = request.POST.getlist('personas_capacitadas[]')  # Todas las cantidades personas capacitadas detalle capacitaciones
                    archivos_capacitacion = request.FILES.getlist('archivo_capacitacion[]')  # Todos los archivos detalle capacitaciones
                    # Publicaciones
                    nfilas_ca_publicacion = json.loads(request.POST['lista_items3']) if 'lista_items3' in request.POST else []  # Números de filas que tienen lleno el campo archivo en detalle de publicaciones
                    nfilas_publicacion = request.POST.getlist('nfila_publicacion[]')  # Todos los número de filas del detalle de evidencias de publicaciones
                    titulos_publicacion = request.POST.getlist('titulo_publicacion[]')  # Todas los títulos de detalle publicaciones
                    revistas_publicacion = request.POST.getlist('revista_publicacion[]')  # Todas las revistas de detalle publicaciones
                    issns_publicacion = request.POST.getlist('issn_publicacion[]')  # Todas los ISSN de detalle publicaciones
                    indexaciones_publicacion = request.POST.getlist('indexacion_publicacion[]')  # Todas las indexaciones de detalle publicaciones
                    envios_publicacion = request.POST.getlist('envio_publicacion[]')  # Todas las fechas envío detalle publicaciones
                    aceptaciones_publicacion = request.POST.getlist('aceptacion_publicacion[]')  # Todas las fechas aceptación detalle publicaciones
                    archivos_publicacion = request.FILES.getlist('archivo_publicacion[]')  # Todos los archivos detalle publicaciones
                    # Participación en Eventos Científicos
                    nfilas_ca_evento = json.loads(request.POST['lista_items4']) if 'lista_items4' in request.POST else []  # Números de filas que tienen lleno el campo archivo en detalle de eventos
                    nfilas_evento = request.POST.getlist('nfila_evento[]')  # Todos los número de filas del detalle de evidencias de eventos
                    nombres_evento = request.POST.getlist('nombre_evento[]')  # Todas los nombres de detalle eventos
                    lugares_evento = request.POST.getlist('lugar_evento[]')  # Todas los lugares de detalle eventos
                    fechas_evento = request.POST.getlist('fecha_evento[]')  # Todas las fechas de detalle eventos
                    titulos_evento = request.POST.getlist('titulo_evento[]')  # Todas los títulos de detalle eventos
                    archivos_evento = request.FILES.getlist('archivo_evento[]')  # Todos los archivos detalle eventos
                    # Otros productos (manuales, instrumentos didácticos, libros, capítulos de libros etc.)
                    descripciones_otroproducto = request.POST.getlist('descripcion_otroproducto[]')  # Otros productos
                    # Personas
                    nombres_persona = request.POST.getlist('nombre_persona[]')  # Todos los nombres detalles personas
                    apellidos_persona = request.POST.getlist('apellido_persona[]')  # Todos los apellidos detalles personas
                    roles_persona = request.POST.getlist('rol_persona[]')  # Todos los roles detalles personas
                    instituciones_persona = request.POST.getlist('institucion_persona[]')  # Todos las instituciones detalles personas
                    emails_persona = request.POST.getlist('email_persona[]')  # Todos los e-mails detalles personas
                    idsobjetivo_persona = request.POST.getlist('idobjetivo_persona[]')  # Todos los objetivos detalles personas
                    # Instituciones
                    nombres_institucion = request.POST.getlist('nombre_institucion[]')  # Todos los nombres detalles instituciones
                    actividades_institucion = request.POST.getlist('actividad_institucion[]')  # Todos las actividades detalles instituciones
                    # Cambios y Problemas
                    descripciones_cambio = request.POST.getlist('descripcion_cambio[]')  # Todos los cambios detalles de cambios
                    descripciones_problema = request.POST.getlist('descripcion_problema[]')  # Todos los problemas detalles de problemas
                    # Equipamiento Adquirido
                    codigos_equipo = request.POST.getlist('codigo_equipo[]')  # Todos los código de barra detalles de equipos
                    nombres_equipo = request.POST.getlist('nombre_equipo[]')  # Todos los nombres detalles de equipos
                    descripciones_equipo = request.POST.getlist('descripcion_equipo[]')  # Todos las descripciones detalles de equipos
                    idsobjetivo_equipo = request.POST.getlist('idobjetivo_equipo[]')  # Todos los obejtivos detalles de equipos
                    ubicaciones_equipo = request.POST.getlist('ubicacion_equipo[]')  # Todos las ubicaciones detalles de equipos
                    lpersonal_equipo = request.POST.getlist('personal_equipo[]')  # Todos el personal detalles de equipos
                    # Indicadores
                    indicadores = request.POST.getlist('indicador[]')  # Todos los indicadores detalles de indicadores
                    descripcionesindicador = request.POST.getlist('descripcionindicador[]')  # Todos las descripciones detalles de indicadores
                    fuentesdatos = request.POST.getlist('fuentedatos[]')  # Todas los fuentes de atos detalles de indicadores
                    ldatoslineabase = request.POST.getlist('datoslineabase[]')  # Todos los datos linea base detalles de indicadores

                    # Validaciones
                    if mesprorroga == 0:
                        if fechafinproyecto < proyecto.fechafinplaneado:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La fecha de fin del proyecto debe ser mayor o igual a <b>{:%d-%m-%Y}. [Sección A]</b>".format(proyecto.fechafinplaneado), "showSwal": "True", "swalType": "warning"})
                    else:
                        if fechafinproyecto <= proyecto.fechafinplaneado:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La fecha de fin del proyecto debe ser mayor a <b>{:%d-%m-%Y}. [Sección A]</b>".format(proyecto.fechafinplaneado), "showSwal": "True", "swalType": "warning"})

                    # Valido los archivos cargados de detalle de presupuesto ejecutado
                    for nfila, archivo in zip(nfilas_ca_presup, archivos_presup):
                        descripcionarchivo = '<b>Sección E.2:</b> Evidencia '
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "{} en la fila # {}".format(resp["mensaje"], nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                    # Valido las fechas y los archivos cargados de detalle de capacitaciones
                    for nfila, fechainicio, fechafin, archivo in zip(nfilas_ca_capacitacion, fechas_inicio, fechas_fin, archivos_capacitacion):
                        if datetime.strptime(fechafin, '%Y-%m-%d').date() < datetime.strptime(fechainicio, '%Y-%m-%d').date():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "<b>Sección G.2:</b> La fecha de culminación debe ser mayor o igual a la fecha de inicio en la fila # {}".format(nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                        descripcionarchivo = '<b>Sección G.2</b>'
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "{} en la fila # {}".format(resp["mensaje"], nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                    # Valido las fechas y los archivos cargados de detalle de publicaciones
                    for nfila, fechainicio, fechafin, archivo in zip(nfilas_ca_publicacion, envios_publicacion, aceptaciones_publicacion, archivos_publicacion):
                        if datetime.strptime(fechafin, '%Y-%m-%d').date() < datetime.strptime(fechainicio, '%Y-%m-%d').date():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "<b>Sección H.1:</b> La fecha de aceptación debe ser mayor o igual a la fecha de envío en la fila # {}".format(nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                        descripcionarchivo = '<b>Sección H.1</b>'
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "{} en la fila # {}".format(resp["mensaje"], nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                    # Valido los archivos cargados de detalle de eventos científicos
                    for nfila, archivo in zip(nfilas_ca_evento, archivos_evento):
                        descripcionarchivo = '<b>Sección I</b>'
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "{} en la fila # {}".format(resp["mensaje"], nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                    # Guardo el informe
                    informeproyecto = ProyectoInvestigacionInforme(
                        proyecto=proyecto,
                        periodo=periodovigente,
                        tipo=2,
                        secuencia=secuencia,
                        generado=False,
                        fecha=datetime.now().date(),
                        numero=numero,
                        adenda=adenda,
                        prorroga=prorroga,
                        mesprorroga=mesprorroga,
                        fechafinproyecto=fechafinproyecto,
                        porcentajeejecucion=porcentajeejecucion,
                        montoejecutado=montoejecutado,
                        porcentajepresup=porcentajepresup,
                        aplicacapacitacion=aplicacapacitacion,
                        capacitacion=capacitacion,
                        aplicadisemresultado=aplicadisemresultado,
                        disemresultado=disemresultado,
                        obtuvoproductopat=obtuvoproductopat,
                        productopatentable=productopatentable,
                        conclusion=conclusion,
                        continuacion=continuacion,
                        lineabase=lineabase,
                        indicadorgeneral=indicadorgeneral,
                        fuentedatosgeneral=fuentedatosgeneral,
                        lineabasegeneral=lineabasegeneral,
                        personaverifica=proyecto.verificainforme,
                        personaaprueba=proyecto.apruebainforme,
                        aprobado=False,
                        estado=2
                    )
                    informeproyecto.save(request)

                    # Guarda detalle de Cumplimiento técnico por cada objetivo específico
                    for idobjetivo, porcentaje in zip(idsobjetivo_ejecucion, porcentajesejecucion):
                        ejecucionobjetivo = ProyectoInvestigacionInformeEjecucionObjetivo(
                            informe=informeproyecto,
                            objetivo_id=idobjetivo,
                            porcentajeejecucion=porcentaje
                        )
                        ejecucionobjetivo.save(request)

                    # Guarda detalle Ejecución Financiera
                    for nfila, descripcion in zip(nfilas_presup, descripciones_presup):
                        ejecucionpresupuesto = ProyectoInvestigacionInformeEvideciaPresupuesto(
                            informe=informeproyecto,
                            descripcion=descripcion.strip()
                        )
                        ejecucionpresupuesto.save(request)

                        # Guardo el archivo del detalle
                        for nfilaarchi, archivo in zip(nfilas_ca_presup, archivos_presup):
                            # Si la fila de la descripcion es igual a la fila que contiene archivo
                            if int(nfilaarchi['nfila']) == int(nfila):
                                # actualizo campo archivo del registro creado
                                archivoreg = archivo
                                archivoreg._name = generar_nombre("evidenciainformepresup_", archivoreg._name)
                                ejecucionpresupuesto.archivo = archivoreg
                                ejecucionpresupuesto.save(request)
                                break

                    # Guarda Cómo se cumplió con el objetivo general y los específicos planteados en la propuesta original
                    for descripcion, detalle in zip(descripcionesobjetivo, detallesobjetivo):
                        cumplimientoobjetivo = ProyectoInvestigacionInformeObjetivoResultado(
                            informe=informeproyecto,
                            descripcion=descripcion.strip(),
                            detalle=detalle.strip(),
                            tipo=1
                        )
                        cumplimientoobjetivo.save(request)

                    # Guarda Cómo se cumplió con Resultados significativos del proyecto
                    for resultado, descripcion, ragregado in zip(resultados, descripcionesresultado, resultadosagregados):
                        cumplimientoresultado = ProyectoInvestigacionInformeObjetivoResultado(
                            informe=informeproyecto,
                            descripcion=resultado.strip(),
                            detalle=descripcion.strip(),
                            tipo=2,
                            agregado=ragregado == 'S'
                        )
                        cumplimientoresultado.save(request)

                    # Guarda detalle Oportunidades de entrenamiento y capacitación profesional
                    for nfila, descripcion, fechainicio, fechafin, lugar, npersona in zip(nfilas_capacitacion, descripciones_capacitacion, fechas_inicio, fechas_fin, lugares_capacitacion, npersonas_capacitadas):
                        capacitacion = ProyectoInvestigacionInformeCapacitacion(
                            informe=informeproyecto,
                            tema=descripcion.strip(),
                            fechainicio=datetime.strptime(fechainicio, '%Y-%m-%d').date(),
                            fechafin=datetime.strptime(fechafin, '%Y-%m-%d').date(),
                            lugar=lugar.strip(),
                            personacapacitada=npersona
                        )
                        capacitacion.save(request)

                        # Guardo el archivo del detalle
                        for nfilaarchi, archivo in zip(nfilas_ca_capacitacion, archivos_capacitacion):
                            # Si la fila de la descripcion es igual a la fila que contiene archivo
                            if int(nfilaarchi['nfila']) == int(nfila):
                                # actualizo campo archivo del registro creado
                                archivoreg = archivo
                                archivoreg._name = generar_nombre("evidenciainformecap_", archivoreg._name)
                                capacitacion.archivo = archivoreg
                                capacitacion.save(request)
                                break

                    # Guarda detalle Publicaciones
                    for nfila, titulo, revista, issn, indexacion, fechaenvio, fechaaceptacion in zip(nfilas_publicacion, titulos_publicacion, revistas_publicacion, issns_publicacion, indexaciones_publicacion, envios_publicacion, aceptaciones_publicacion):
                        publicacion = ProyectoInvestigacionInformePublicacion(
                            informe=informeproyecto,
                            titulo=titulo.strip(),
                            revista=revista.strip(),
                            issn=issn.strip(),
                            indexacion=indexacion.strip(),
                            fechaenvio=datetime.strptime(fechaenvio, '%Y-%m-%d').date(),
                            fechaaceptacion=datetime.strptime(fechaaceptacion, '%Y-%m-%d').date()
                        )
                        publicacion.save(request)

                        # Guardo el archivo del detalle
                        for nfilaarchi, archivo in zip(nfilas_ca_publicacion, archivos_publicacion):
                            # Si la fila de la descripcion es igual a la fila que contiene archivo
                            if int(nfilaarchi['nfila']) == int(nfila):
                                # actualizo campo archivo del registro creado
                                archivoreg = archivo
                                archivoreg._name = generar_nombre("evidenciainformepub_", archivoreg._name)
                                publicacion.archivo = archivoreg
                                publicacion.save(request)
                                break

                    # Guarda detalle Participación en Eventos Científicos
                    for nfila, nombre, lugar, fecha, titulo in zip(nfilas_evento, nombres_evento, lugares_evento, fechas_evento, titulos_evento):
                        eventocientifico = ProyectoInvestigacionInformeEvento(
                            informe=informeproyecto,
                            nombre=nombre.strip(),
                            lugar=lugar.strip(),
                            fecha=datetime.strptime(fecha, '%Y-%m-%d').date(),
                            titulo=titulo.strip()
                        )
                        eventocientifico.save(request)

                        # Guardo el archivo del detalle
                        for nfilaarchi, archivo in zip(nfilas_ca_evento, archivos_evento):
                            # Si la fila de la descripcion es igual a la fila que contiene archivo
                            if int(nfilaarchi['nfila']) == int(nfila):
                                # actualizo campo archivo del registro creado
                                archivoreg = archivo
                                archivoreg._name = generar_nombre("evidenciainformeeve_", archivoreg._name)
                                eventocientifico.archivo = archivoreg
                                eventocientifico.save(request)
                                break

                    # Guarda detalle Otros productos (manuales, instrumentos didácticos, libros, capítulos de libros etc.)
                    for descripcion in descripciones_otroproducto:
                        otroproducto = ProyectoInvestigacionInformeOtroProducto(
                            informe=informeproyecto,
                            descripcion=descripcion.strip()
                        )
                        otroproducto.save(request)

                    # Guarda detalle de Personas
                    for nombre, apellido, rol, institucion, email, idsobjetivo in zip(nombres_persona, apellidos_persona, roles_persona, instituciones_persona, emails_persona, idsobjetivo_persona):
                        personaparticipante = ProyectoInvestigacionInformeParticipante(
                            informe=informeproyecto,
                            nombre=nombre.strip().upper(),
                            apellido=apellido.strip().upper(),
                            funcion=rol,
                            entidad=institucion.strip().upper(),
                            email=email.strip().lower()
                        )
                        personaparticipante.save(request)

                        # Guardo los objetivos en los que participó
                        if idsobjetivo:
                            for objetivo_id in idsobjetivo.split(","):
                                personaparticipante.objetivo.add(objetivo_id)

                            personaparticipante.save(request)

                    # Guarda detalle de Instituciones
                    for nombre, actividad in zip(nombres_institucion, actividades_institucion):
                        institucionparticipante = ProyectoInvestigacionInformeInstitucion(
                            informe=informeproyecto,
                            nombre=nombre.strip().upper(),
                            actividad=actividad.strip()
                        )
                        institucionparticipante.save(request)

                    # Guarda detalle de Cambios
                    for descripcion in descripciones_cambio:
                        cambio = ProyectoInvestigacionInformeCambioProblema(
                            informe=informeproyecto,
                            detalle=descripcion.strip(),
                            tipo=1
                        )
                        cambio.save(request)

                    # Guarda detalle de Problemas
                    for descripcion in descripciones_problema:
                        problema = ProyectoInvestigacionInformeCambioProblema(
                            informe=informeproyecto,
                            detalle=descripcion.strip(),
                            tipo=2
                        )
                        problema.save(request)

                    # Guarda detalle Equipamiento Adquirido
                    for codigo, nombre, descripcion, idsobjetivo, ubicacion, personal  in zip(codigos_equipo, nombres_equipo, descripciones_equipo, idsobjetivo_equipo, ubicaciones_equipo, lpersonal_equipo):
                        equipamiento = ProyectoInvestigacionInformeEquipamiento(
                            informe=informeproyecto,
                            codigo=codigo.strip(),
                            equipo=nombre.strip(),
                            descripcion=descripcion.strip(),
                            ubicacion=ubicacion.strip(),
                            custodio=personal.strip()
                        )
                        equipamiento.save(request)

                        # Guardo los objetivos en los que fue utilizado el equipo
                        for objetivo_id in idsobjetivo.split(","):
                            equipamiento.objetivo.add(objetivo_id)

                        equipamiento.save(request)

                    # Guarda detalle de Indicadores
                    for indicador, descripcion, fuente, lineabase in zip(indicadores, descripcionesindicador, fuentesdatos, ldatoslineabase):
                        indicadorresultado = ProyectoInvestigacionInformeIndicador(
                            informe=informeproyecto,
                            indicador=indicador.strip(),
                            descripcion=descripcion.strip(),
                            fuentedato=fuente.strip(),
                            lineabase=lineabase.strip()
                        )
                        indicadorresultado.save(request)

                    log(u'%s agregó informe final al proyecto: %s' % (persona, informeproyecto.numero), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El proyecto de investigación no existe", "showSwal": "True", "swalType": "warning"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editinformefinal':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['id'])))

                if informeproyecto:
                    # Verifico que no haya sido revisado por coordinación de investigación
                    if informeproyecto.estado in [5, 7]:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el registro debido a que fue revisado por la Coordinación de Investigación", "showSwal": "True", "swalType": "warning"})

                    proyecto = informeproyecto.proyecto

                    notificar = informeproyecto.estado in [6, 8]

                    # Obtener los valores de los campos del formulario
                    adenda = request.POST['adenda'] == '1'
                    prorroga = request.POST['prorroga'] == '1'
                    mesprorroga = int(request.POST['mesesprorroga']) if request.POST['mesesprorroga'] else 0
                    fechafinproyecto = datetime.strptime(request.POST['fechafin'], '%Y-%m-%d').date()
                    porcentajeejecucion = request.POST['promediocumpl']
                    montoejecutado = request.POST['montoejecutado']
                    porcentajepresup = request.POST['porcentajepresup']
                    aplicacapacitacion = request.POST['aplicacapacitacion'] == '1'
                    capacitacion = request.POST['detallecapacitacion'].strip()
                    aplicadisemresultado = request.POST['aplicadisemresultado'] == '1'
                    disemresultado = request.POST['detalledisemresultado'].strip()
                    obtuvoproductopat = request.POST['productopatentable'] == '1'
                    productopatentable = request.POST['detalleproductopatentable'].strip()
                    conclusion = reemplazar_fuente_para_informe(request.POST['conclusion'].strip())
                    continuacion = reemplazar_fuente_para_informe(request.POST['continuacion'].strip())
                    lineabase = reemplazar_fuente_para_informe(request.POST['lineabase'].strip())
                    indicadorgeneral = request.POST['indicadorgeneral'].strip()
                    fuentedatosgeneral = request.POST['fuentedatosgeneral'].strip()
                    lineabasegeneral = request.POST['lineabasegeneral'].strip()

                    # Obtener los valores de los detalles del formulario
                    # Cumplimiento técnico por cada objetivo específico
                    idsregobjejec = request.POST.getlist('idregobjejec[]')  # Todos los ids de detalle de Cumplimiento
                    idsobjetivo_ejecucion = request.POST.getlist('idobjetivo_ejecucion[]')  # Ids objetivos ejecución
                    porcentajesejecucion = request.POST.getlist('porcentajeejecucion[]')  # Porcentajes de ejecución
                    # Ejecución Financiera
                    nfilas_ca_presup = json.loads(request.POST['lista_items1']) if 'lista_items1' in request.POST else []  # Números de filas que tienen lleno el campo archivo en detalle de presupuesto
                    nfilas_presup = request.POST.getlist('nfila_evidencia[]')  # Todos los número de filas del detalle de evidencias de presupuesto
                    idsregpresup = request.POST.getlist('idregpresup[]')  # Todos los ids de detalle de ejecución financiera
                    descripciones_presup = request.POST.getlist('descripcion_evidencia[]')  # Todas las descripciones detalle presupuesto
                    archivos_presup = request.FILES.getlist('archivo_evidencia[]')  # Todos los archivos detalle presupuesto
                    ejecfinelim = json.loads(request.POST['lista_items5']) if 'lista_items5' in request.POST else [] # Ids registros de presupesto borrados
                    # Cómo se cumplió con el objetivo general y los específicos planteados en la propuesta original
                    idsregobjcump = request.POST.getlist('idregobjcump[]')  # Todos los ids de detalle de Cómo se cumplió
                    descripcionesobjetivo = request.POST.getlist('descripcionobjetivo[]')  # Descripciones de objetivos
                    detallesobjetivo = request.POST.getlist('detalleobjetivo[]')  # Detalles de cumplimiento de objetivos
                    # Resultados significativos del proyecto
                    idsregrescump = request.POST.getlist('idregrescump[]')  # Todos los ids de detalle Resultados significativos
                    resultados = request.POST.getlist('resultado[]')  # Resultados
                    descripcionesresultado = request.POST.getlist('descripcionresultado[]')  # Descripciones como se lograron los resultados
                    resultadosagregados = request.POST.getlist('agregado[]')  # Resultados agregados
                    resultelim = json.loads(request.POST['lista_items6']) if 'lista_items6' in request.POST else [] # Ids registros de resultados borrados
                    # Oportunidades de entrenamiento y capacitación profesional
                    nfilas_ca_capacitacion = json.loads(request.POST['lista_items2']) if 'lista_items2' in request.POST else []  # Números de filas que tienen lleno el campo archivo en detalle de capacitaciones
                    nfilas_capacitacion = request.POST.getlist('nfila_capacitacion[]')  # Todos los número de filas del detalle de evidencias de capacitación
                    idsregcapac = request.POST.getlist('idregcapac[]')  # Todos los ids de detalle de Oportunidades de entrenamiento
                    descripciones_capacitacion = request.POST.getlist('descripcion_capacitacion[]')  # Todas las descripciones detalle capacitaciones
                    fechas_inicio = request.POST.getlist('fecha_inicio[]')  # Todas las fechas inicio detalle capacitaciones
                    fechas_fin = request.POST.getlist('fecha_fin[]')  # Todas las fechas inicio detalle capacitaciones
                    lugares_capacitacion = request.POST.getlist('lugar_capacitacion[]')  # Todas los lugares detalle capacitaciones
                    npersonas_capacitadas = request.POST.getlist('personas_capacitadas[]')  # Todas las cantidades personas capacitadas detalle capacitaciones
                    archivos_capacitacion = request.FILES.getlist('archivo_capacitacion[]')  # Todos los archivos detalle capacitaciones
                    capacelim = json.loads(request.POST['lista_items7']) if 'lista_items7' in request.POST else [] # Ids registros de capacitaciones borradas
                    # Publicaciones
                    nfilas_ca_publicacion = json.loads(request.POST['lista_items3']) if 'lista_items3' in request.POST else []  # Números de filas que tienen lleno el campo archivo en detalle de publicaciones
                    nfilas_publicacion = request.POST.getlist('nfila_publicacion[]')  # Todos los número de filas del detalle de evidencias de publicaciones
                    idsregpub = request.POST.getlist('idregpub[]')  # Todos los ids de detalle de Publicaciones
                    titulos_publicacion = request.POST.getlist('titulo_publicacion[]')  # Todas los títulos de detalle publicaciones
                    revistas_publicacion = request.POST.getlist('revista_publicacion[]')  # Todas las revistas de detalle publicaciones
                    issns_publicacion = request.POST.getlist('issn_publicacion[]')  # Todas los ISSN de detalle publicaciones
                    indexaciones_publicacion = request.POST.getlist('indexacion_publicacion[]')  # Todas las indexaciones de detalle publicaciones
                    envios_publicacion = request.POST.getlist('envio_publicacion[]')  # Todas las fechas envío detalle publicaciones
                    aceptaciones_publicacion = request.POST.getlist('aceptacion_publicacion[]')  # Todas las fechas aceptación detalle publicaciones
                    archivos_publicacion = request.FILES.getlist('archivo_publicacion[]')  # Todos los archivos detalle publicaciones
                    pubelim = json.loads(request.POST['lista_items8']) if 'lista_items8' in request.POST else [] # Ids registros de publicaciones borradas
                    # Participación en Eventos Científicos
                    nfilas_ca_evento = json.loads(request.POST['lista_items4']) if 'lista_items4' in request.POST else []  # Números de filas que tienen lleno el campo archivo en detalle de eventos
                    nfilas_evento = request.POST.getlist('nfila_evento[]')  # Todos los número de filas del detalle de evidencias de eventos
                    idsregeve = request.POST.getlist('idregeve[]')  # Todos los ids de detalle de Participación en Eventos Científicos
                    nombres_evento = request.POST.getlist('nombre_evento[]')  # Todas los nombres de detalle eventos
                    lugares_evento = request.POST.getlist('lugar_evento[]')  # Todas los lugares de detalle eventos
                    fechas_evento = request.POST.getlist('fecha_evento[]')  # Todas las fechas de detalle eventos
                    titulos_evento = request.POST.getlist('titulo_evento[]')  # Todas los títulos de detalle eventos
                    archivos_evento = request.FILES.getlist('archivo_evento[]')  # Todos los archivos detalle eventos
                    evenelim = json.loads(request.POST['lista_items9']) if 'lista_items9' in request.POST else []  # Ids registros de eventos borrados
                    # Otros productos (manuales, instrumentos didácticos, libros, capítulos de libros etc.)
                    idsregotroprod = request.POST.getlist('idregotroprod[]')  # Todos los ids de detalle de Otros productos
                    descripciones_otroproducto = request.POST.getlist('descripcion_otroproducto[]')  # Otros productos
                    otroprodelim = json.loads(request.POST['lista_items10']) if 'lista_items10' in request.POST else []  # Ids registros de otros productos borrados
                    # Personas
                    idsregintpers = request.POST.getlist('idregintpers[]')  # Todos los ids de detalle de personas
                    nombres_persona = request.POST.getlist('nombre_persona[]')  # Todos los nombres detalles personas
                    apellidos_persona = request.POST.getlist('apellido_persona[]')  # Todos los apellidos detalles personas
                    roles_persona = request.POST.getlist('rol_persona[]')  # Todos los roles detalles personas
                    instituciones_persona = request.POST.getlist('institucion_persona[]')  # Todos las instituciones detalles personas
                    emails_persona = request.POST.getlist('email_persona[]')  # Todos los e-mails detalles personas
                    idsobjetivo_persona = request.POST.getlist('idobjetivo_persona[]')  # Todos los objetivos detalles personas
                    personaelim = json.loads(request.POST['lista_items11']) if 'lista_items11' in request.POST else []  # Ids registros de personas borradas
                    # Instituciones
                    idsregintinst = request.POST.getlist('idregintinst[]')  # Todos los ids de detalle de instituciones
                    nombres_institucion = request.POST.getlist('nombre_institucion[]')  # Todos los nombres detalles instituciones
                    actividades_institucion = request.POST.getlist('actividad_institucion[]')  # Todos las actividades detalles instituciones
                    institucionelim = json.loads(request.POST['lista_items12']) if 'lista_items12' in request.POST else []  # Ids registros de instituciones borradas
                    # Cambios
                    idsregcambio = request.POST.getlist('idregcambio[]')  # Todos los ids de detalle de Cambios
                    descripciones_cambio = request.POST.getlist('descripcion_cambio[]')  # Todos los cambios detalles de cambios
                    cambioelim = json.loads(request.POST['lista_items13']) if 'lista_items13' in request.POST else []  # Ids registros de cambios borrados
                    # Problemas
                    idsregproblema = request.POST.getlist('idregproblema[]')  # Todos los ids de detalle de Problemas
                    descripciones_problema = request.POST.getlist('descripcion_problema[]')  # Todos los problemas detalles de problemas
                    problemaelim = json.loads(request.POST['lista_items14']) if 'lista_items14' in request.POST else []  # Ids registros de problemas borrados
                    # Equipamiento Adquirido
                    idsregequipo = request.POST.getlist('idregequipo[]')  # Todos los ids de detalle de Equipamiento Adquirido
                    codigos_equipo = request.POST.getlist('codigo_equipo[]')  # Todos los código de barra detalles de equipos
                    nombres_equipo = request.POST.getlist('nombre_equipo[]')  # Todos los nombres detalles de equipos
                    descripciones_equipo = request.POST.getlist('descripcion_equipo[]')  # Todos las descripciones detalles de equipos
                    idsobjetivo_equipo = request.POST.getlist('idobjetivo_equipo[]')  # Todos los obejtivos detalles de equipos
                    ubicaciones_equipo = request.POST.getlist('ubicacion_equipo[]')  # Todos las ubicaciones detalles de equipos
                    lpersonal_equipo = request.POST.getlist('personal_equipo[]')  # Todos el personal detalles de equipos
                    equipoelim = json.loads(request.POST['lista_items15']) if 'lista_items15' in request.POST else []  # Ids registros de equipos borrados
                    # Indicadores
                    idsregindicador = request.POST.getlist('idregindicador[]')  # Todos los ids de detalle de Indicadores
                    indicadores = request.POST.getlist('indicador[]')  # Todos los indicadores detalles de indicadores
                    descripcionesindicador = request.POST.getlist('descripcionindicador[]')  # Todos las descripciones detalles de indicadores
                    fuentesdatos = request.POST.getlist('fuentedatos[]')  # Todas los fuentes de atos detalles de indicadores
                    ldatoslineabase = request.POST.getlist('datoslineabase[]')  # Todos los datos linea base detalles de indicadores
                    indicadorelim = json.loads(request.POST['lista_items16']) if 'lista_items16' in request.POST else []  # Ids registros de indicadores borrados

                    # Validaciones
                    if mesprorroga == 0:
                        if fechafinproyecto < proyecto.fechafinplaneado:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La fecha de fin del proyecto debe ser mayor o igual a <b>{:%d-%m-%Y}. [Sección A]</b>".format(proyecto.fechafinplaneado), "showSwal": "True", "swalType": "warning"})
                    else:
                        if fechafinproyecto <= proyecto.fechafinplaneado:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La fecha de fin del proyecto debe ser mayor a <b>{:%d-%m-%Y}. [Sección A]</b>".format(proyecto.fechafinplaneado), "showSwal": "True", "swalType": "warning"})

                    # Valido los archivos cargados de detalle de presupuesto ejecutado
                    for nfila, archivo in zip(nfilas_ca_presup, archivos_presup):
                        descripcionarchivo = '<b>Sección E.2:</b> Evidencia '
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "{} en la fila # {}".format(resp["mensaje"], nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                    # Valido las fechas y los archivos cargados de detalle de capacitaciones
                    for nfila, fechainicio, fechafin, archivo in zip(nfilas_ca_capacitacion, fechas_inicio, fechas_fin, archivos_capacitacion):
                        if datetime.strptime(fechafin, '%Y-%m-%d').date() < datetime.strptime(fechainicio, '%Y-%m-%d').date():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "<b>Sección G.2:</b> La fecha de culminación debe ser mayor o igual a la fecha de inicio en la fila # {}".format(nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                        descripcionarchivo = '<b>Sección G.2</b>'
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "{} en la fila # {}".format(resp["mensaje"], nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                    # Valido las fechas y los archivos cargados de detalle de publicaciones
                    for nfila, fechainicio, fechafin, archivo in zip(nfilas_ca_publicacion, envios_publicacion, aceptaciones_publicacion, archivos_publicacion):
                        if datetime.strptime(fechafin, '%Y-%m-%d').date() < datetime.strptime(fechainicio, '%Y-%m-%d').date():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "<b>Sección H.1:</b> La fecha de aceptación debe ser mayor o igual a la fecha de envío en la fila # {}".format(nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                        descripcionarchivo = '<b>Sección H.1</b>'
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "{} en la fila # {}".format(resp["mensaje"], nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                    # Valido los archivos cargados de detalle de eventos científicos
                    for nfila, archivo in zip(nfilas_ca_evento, archivos_evento):
                        descripcionarchivo = '<b>Sección I</b>'
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "{} en la fila # {}".format(resp["mensaje"], nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                    # Actualizo el informe
                    informeproyecto.generado = False
                    informeproyecto.adenda = adenda
                    informeproyecto.prorroga = prorroga
                    informeproyecto.mesprorroga = mesprorroga
                    informeproyecto.fechafinproyecto = fechafinproyecto
                    informeproyecto.porcentajeejecucion = porcentajeejecucion
                    informeproyecto.montoejecutado = montoejecutado
                    informeproyecto.porcentajepresup = porcentajepresup
                    informeproyecto.aplicacapacitacion = aplicacapacitacion
                    informeproyecto.capacitacion = capacitacion
                    informeproyecto.aplicadisemresultado = aplicadisemresultado
                    informeproyecto.disemresultado = disemresultado
                    informeproyecto.obtuvoproductopat = obtuvoproductopat
                    informeproyecto.productopatentable = productopatentable
                    informeproyecto.conclusion = conclusion
                    informeproyecto.continuacion = continuacion
                    informeproyecto.lineabase = lineabase
                    informeproyecto.indicadorgeneral = indicadorgeneral
                    informeproyecto.fuentedatosgeneral = fuentedatosgeneral
                    informeproyecto.lineabasegeneral = lineabasegeneral
                    informeproyecto.aprobado = False
                    informeproyecto.estado = 2
                    informeproyecto.observacionverificacion = ''
                    informeproyecto.fechaverificacion = None
                    informeproyecto.observacionaprobacion = ''
                    informeproyecto.fechaaprobacion = None
                    informeproyecto.save(request)

                    # Guarda detalle de Cumplimiento técnico por cada objetivo específico
                    for idreg, porcentaje in zip(idsregobjejec, porcentajesejecucion):
                        ejecucionobjetivo = ProyectoInvestigacionInformeEjecucionObjetivo.objects.get(pk=idreg)
                        ejecucionobjetivo.porcentajeejecucion = porcentaje
                        ejecucionobjetivo.save(request)

                    # Guarda detalle Ejecución Financiera
                    for idreg, nfila, descripcion in zip(idsregpresup, nfilas_presup, descripciones_presup):
                        # Si es registro nuevo
                        if int(idreg) == 0:
                            ejecucionpresupuesto = ProyectoInvestigacionInformeEvideciaPresupuesto(
                                informe=informeproyecto,
                                descripcion=descripcion.strip()
                            )
                        else:
                            ejecucionpresupuesto = ProyectoInvestigacionInformeEvideciaPresupuesto.objects.get(pk=idreg)
                            ejecucionpresupuesto.descripcion = descripcion.strip()

                        ejecucionpresupuesto.save(request)

                        # Guardo el archivo del detalle
                        for nfilaarchi, archivo in zip(nfilas_ca_presup, archivos_presup):
                            # Si la fila de la descripcion es igual a la fila que contiene archivo
                            if int(nfilaarchi['nfila']) == int(nfila):
                                # actualizo campo archivo del registro creado
                                archivoreg = archivo
                                archivoreg._name = generar_nombre("evidenciainformepresup_", archivoreg._name)
                                ejecucionpresupuesto.archivo = archivoreg
                                ejecucionpresupuesto.save(request)
                                break

                    # Elimino detalles Ejecución Financiera
                    if ejecfinelim:
                        for registro in ejecfinelim:
                            ejecucionpresupuesto = ProyectoInvestigacionInformeEvideciaPresupuesto.objects.get(pk=registro['idreg'])
                            ejecucionpresupuesto.status = False
                            ejecucionpresupuesto.save(request)

                    # Guarda Cómo se cumplió con el objetivo general y los específicos planteados en la propuesta original
                    for idreg, detalle in zip(idsregobjcump, detallesobjetivo):
                        cumplimientoobjetivo = ProyectoInvestigacionInformeObjetivoResultado.objects.get(pk=idreg)
                        cumplimientoobjetivo.detalle = detalle.strip()
                        cumplimientoobjetivo.save(request)

                    # Guarda Cómo se cumplió con Resultados significativos del proyecto
                    for idreg, resultado, descripcion, ragregado in zip(idsregrescump, resultados, descripcionesresultado, resultadosagregados):
                        # Si es registro nuevo
                        if int(idreg) == 0:
                            cumplimientoresultado = ProyectoInvestigacionInformeObjetivoResultado(
                                informe=informeproyecto,
                                descripcion=resultado.strip(),
                                detalle=descripcion.strip(),
                                tipo=2,
                                agregado=True
                            )
                        else:
                            cumplimientoresultado = ProyectoInvestigacionInformeObjetivoResultado.objects.get(pk=idreg)
                            cumplimientoresultado.descripcion = resultado.strip()
                            cumplimientoresultado.detalle = descripcion.strip()

                        cumplimientoresultado.save(request)

                    # Elimino detalles Cómo se cumplió con Resultados significativos del proyecto
                    if resultelim:
                        for registro in resultelim:
                            cumplimientoresultado = ProyectoInvestigacionInformeObjetivoResultado.objects.get(pk=registro['idreg'])
                            cumplimientoresultado.status = False
                            cumplimientoresultado.save(request)

                    # Guarda detalle Oportunidades de entrenamiento y capacitación profesional
                    for idreg, nfila, descripcion, fechainicio, fechafin, lugar, npersona in zip(idsregcapac, nfilas_capacitacion, descripciones_capacitacion, fechas_inicio, fechas_fin, lugares_capacitacion, npersonas_capacitadas):
                        # Si es registro nuevo
                        if int(idreg) == 0:
                            capacitacion = ProyectoInvestigacionInformeCapacitacion(
                                informe=informeproyecto,
                                tema=descripcion.strip(),
                                fechainicio=datetime.strptime(fechainicio, '%Y-%m-%d').date(),
                                fechafin=datetime.strptime(fechafin, '%Y-%m-%d').date(),
                                lugar=lugar.strip(),
                                personacapacitada=npersona
                            )
                        else:
                            capacitacion = ProyectoInvestigacionInformeCapacitacion.objects.get(pk=idreg)
                            capacitacion.tema = descripcion.strip()
                            capacitacion.fechainicio = datetime.strptime(fechainicio, '%Y-%m-%d').date()
                            capacitacion.fechafin = datetime.strptime(fechafin, '%Y-%m-%d').date()
                            capacitacion.lugar = lugar.strip()
                            capacitacion.personacapacitada = npersona

                        capacitacion.save(request)

                        # Guardo el archivo del detalle
                        for nfilaarchi, archivo in zip(nfilas_ca_capacitacion, archivos_capacitacion):
                            # Si la fila de la descripcion es igual a la fila que contiene archivo
                            if int(nfilaarchi['nfila']) == int(nfila):
                                # actualizo campo archivo del registro creado
                                archivoreg = archivo
                                archivoreg._name = generar_nombre("evidenciainformecap_", archivoreg._name)
                                capacitacion.archivo = archivoreg
                                capacitacion.save(request)
                                break

                    # Elimino detalles Oportunidades de entrenamiento y capacitación profesional
                    if capacelim:
                        for registro in capacelim:
                            capacitacion = ProyectoInvestigacionInformeCapacitacion.objects.get(pk=registro['idreg'])
                            capacitacion.status = False
                            capacitacion.save(request)

                    # Guarda detalle Publicaciones
                    for idreg, nfila, titulo, revista, issn, indexacion, fechaenvio, fechaaceptacion in zip(idsregpub, nfilas_publicacion, titulos_publicacion, revistas_publicacion, issns_publicacion, indexaciones_publicacion, envios_publicacion, aceptaciones_publicacion):
                        # Si es registro nuevo
                        if int(idreg) == 0:
                            publicacion = ProyectoInvestigacionInformePublicacion(
                                informe=informeproyecto,
                                titulo=titulo.strip(),
                                revista=revista.strip(),
                                issn=issn.strip(),
                                indexacion=indexacion.strip(),
                                fechaenvio=datetime.strptime(fechaenvio, '%Y-%m-%d').date(),
                                fechaaceptacion=datetime.strptime(fechaaceptacion, '%Y-%m-%d').date()
                            )
                        else:
                            publicacion = ProyectoInvestigacionInformePublicacion.objects.get(pk=idreg)
                            publicacion.titulo = titulo.strip()
                            publicacion.revista = revista.strip()
                            publicacion.issn = issn.strip()
                            publicacion.indexacion = indexacion.strip()
                            publicacion.fechaenvio = datetime.strptime(fechaenvio, '%Y-%m-%d').date()
                            publicacion.fechaaceptacion = datetime.strptime(fechaaceptacion, '%Y-%m-%d').date()

                        publicacion.save(request)

                        # Guardo el archivo del detalle
                        for nfilaarchi, archivo in zip(nfilas_ca_publicacion, archivos_publicacion):
                            # Si la fila de la descripcion es igual a la fila que contiene archivo
                            if int(nfilaarchi['nfila']) == int(nfila):
                                # actualizo campo archivo del registro creado
                                archivoreg = archivo
                                archivoreg._name = generar_nombre("evidenciainformepub_", archivoreg._name)
                                publicacion.archivo = archivoreg
                                publicacion.save(request)
                                break

                    # Elimino detalles Publicaciones
                    if pubelim:
                        for registro in pubelim:
                            publicacion = ProyectoInvestigacionInformePublicacion.objects.get(pk=registro['idreg'])
                            publicacion.status = False
                            publicacion.save(request)

                    # Guarda detalle Participación en Eventos Científicos
                    for idreg, nfila, nombre, lugar, fecha, titulo in zip(idsregeve, nfilas_evento, nombres_evento, lugares_evento, fechas_evento, titulos_evento):
                        # Si es registro nuevo
                        if int(idreg) == 0:
                            eventocientifico = ProyectoInvestigacionInformeEvento(
                                informe=informeproyecto,
                                nombre=nombre.strip(),
                                lugar=lugar.strip(),
                                fecha=datetime.strptime(fecha, '%Y-%m-%d').date(),
                                titulo=titulo.strip()
                            )
                        else:
                            eventocientifico = ProyectoInvestigacionInformeEvento.objects.get(pk=idreg)
                            eventocientifico.nombre = nombre.strip()
                            eventocientifico.lugar = lugar.strip()
                            eventocientifico.fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
                            eventocientifico.titulo = titulo.strip()

                        eventocientifico.save(request)

                        # Guardo el archivo del detalle
                        for nfilaarchi, archivo in zip(nfilas_ca_evento, archivos_evento):
                            # Si la fila de la descripcion es igual a la fila que contiene archivo
                            if int(nfilaarchi['nfila']) == int(nfila):
                                # actualizo campo archivo del registro creado
                                archivoreg = archivo
                                archivoreg._name = generar_nombre("evidenciainformeeve_", archivoreg._name)
                                eventocientifico.archivo = archivoreg
                                eventocientifico.save(request)
                                break

                    # Elimino detalles Eventos
                    if evenelim:
                        for registro in evenelim:
                            eventocientifico = ProyectoInvestigacionInformeEvento.objects.get(pk=registro['idreg'])
                            eventocientifico.status = False
                            eventocientifico.save(request)

                    # Guarda detalle Otros productos (manuales, instrumentos didácticos, libros, capítulos de libros etc.)
                    for idreg, descripcion in zip(idsregotroprod, descripciones_otroproducto):
                        # Si es registro nuevo
                        if int(idreg) == 0:
                            otroproducto = ProyectoInvestigacionInformeOtroProducto(
                                informe=informeproyecto,
                                descripcion=descripcion.strip()
                            )
                        else:
                            otroproducto = ProyectoInvestigacionInformeOtroProducto.objects.get(pk=idreg)
                            otroproducto.descripcion = descripcion.strip()

                        otroproducto.save(request)

                    # Elimino detalles Otros productos
                    if otroprodelim:
                        for registro in otroprodelim:
                            otroproducto = ProyectoInvestigacionInformeOtroProducto.objects.get(pk=registro['idreg'])
                            otroproducto.status = False
                            otroproducto.save(request)

                    # Guarda detalle de Personas
                    for idreg, nombre, apellido, rol, institucion, email, idsobjetivo in zip(idsregintpers, nombres_persona, apellidos_persona, roles_persona, instituciones_persona, emails_persona, idsobjetivo_persona):
                        # Si es registro nuevo
                        if int(idreg) == 0:
                            personaparticipante = ProyectoInvestigacionInformeParticipante(
                                informe=informeproyecto,
                                nombre=nombre.strip().upper(),
                                apellido=apellido.strip().upper(),
                                funcion=rol,
                                entidad=institucion.strip().upper(),
                                email=email.strip().lower()
                            )
                        else:
                            personaparticipante = ProyectoInvestigacionInformeParticipante.objects.get(pk=idreg)
                            personaparticipante.nombre = nombre.strip().upper()
                            personaparticipante.apellido = apellido.strip().upper()
                            personaparticipante.funcion = rol
                            personaparticipante.entidad = institucion.strip().upper()
                            personaparticipante.email = email.strip().lower()

                        personaparticipante.save(request)

                        # Borro los objetivos en los que participó
                        if int(idreg) > 0:
                            personaparticipante.objetivo.clear()

                        # Guardo los objetivos en los que participó
                        if idsobjetivo:
                            for objetivo_id in idsobjetivo.split(","):
                                personaparticipante.objetivo.add(objetivo_id)

                            personaparticipante.save(request)

                    # Elimino detalles Personas
                    if personaelim:
                        for registro in personaelim:
                            personaparticipante = ProyectoInvestigacionInformeParticipante.objects.get(pk=registro['idreg'])
                            personaparticipante.status = False
                            personaparticipante.objetivo.clear()
                            personaparticipante.save(request)

                    # Guarda detalle de Instituciones
                    for idreg, nombre, actividad in zip(idsregintinst, nombres_institucion, actividades_institucion):
                        # Si es registro nuevo
                        if int(idreg) == 0:
                            institucionparticipante = ProyectoInvestigacionInformeInstitucion(
                                informe=informeproyecto,
                                nombre=nombre.strip().upper(),
                                actividad=actividad.strip()
                            )
                        else:
                            institucionparticipante = ProyectoInvestigacionInformeInstitucion.objects.get(pk=idreg)
                            institucionparticipante.nombre = nombre.strip().upper()
                            institucionparticipante.actividad = actividad.strip()

                        institucionparticipante.save(request)

                    # Elimino detalles Instituciones
                    if institucionelim:
                        for registro in institucionelim:
                            institucionparticipante = ProyectoInvestigacionInformeInstitucion.objects.get(pk=registro['idreg'])
                            institucionparticipante.status = False
                            institucionparticipante.save(request)

                    # Guarda detalle de Cambios
                    for idreg, descripcion in zip(idsregcambio, descripciones_cambio):
                        # Si es registro nuevo
                        if int(idreg) == 0:
                            cambio = ProyectoInvestigacionInformeCambioProblema(
                                informe=informeproyecto,
                                detalle=descripcion.strip(),
                                tipo=1
                            )
                        else:
                            cambio = ProyectoInvestigacionInformeCambioProblema.objects.get(pk=idreg)
                            cambio.detalle = descripcion.strip()

                        cambio.save(request)

                    # Elimino detalles Cambios
                    if cambioelim:
                        for registro in cambioelim:
                            cambio = ProyectoInvestigacionInformeCambioProblema.objects.get(pk=registro['idreg'])
                            cambio.status = False
                            cambio.save(request)

                    # Guarda detalle de Problemas
                    for idreg, descripcion in zip(idsregproblema, descripciones_problema):
                        # Si es registro nuevo
                        if int(idreg) == 0:
                            problema = ProyectoInvestigacionInformeCambioProblema(
                                informe=informeproyecto,
                                detalle=descripcion.strip(),
                                tipo=2
                            )
                        else:
                            problema = ProyectoInvestigacionInformeCambioProblema.objects.get(pk=idreg)
                            problema.detalle = descripcion.strip()

                        problema.save(request)

                    # Elimino detalles Problemas
                    if problemaelim:
                        for registro in problemaelim:
                            problema = ProyectoInvestigacionInformeCambioProblema.objects.get(pk=registro['idreg'])
                            problema.status = False
                            problema.save(request)

                    # Guarda detalle Equipamiento Adquirido
                    for idreg, codigo, nombre, descripcion, idsobjetivo, ubicacion, personal in zip(idsregequipo, codigos_equipo, nombres_equipo, descripciones_equipo, idsobjetivo_equipo, ubicaciones_equipo, lpersonal_equipo):
                        # Si es registro nuevo
                        if int(idreg) == 0:
                            equipamiento = ProyectoInvestigacionInformeEquipamiento(
                                informe=informeproyecto,
                                codigo=codigo.strip(),
                                equipo=nombre.strip(),
                                descripcion=descripcion.strip(),
                                ubicacion=ubicacion.strip(),
                                custodio=personal.strip()
                            )
                        else:
                            equipamiento = ProyectoInvestigacionInformeEquipamiento.objects.get(pk=idreg)
                            equipamiento.codigo = codigo.strip()
                            equipamiento.equipo = nombre.strip()
                            equipamiento.descripcion = descripcion.strip()
                            equipamiento.ubicacion = ubicacion.strip()
                            equipamiento.custodio = personal.strip()

                        equipamiento.save(request)

                        # Borro los objetivos en los que participó
                        if int(idreg) > 0:
                            equipamiento.objetivo.clear()

                        # Guardo los objetivos en los que fue utilizado el equipo
                        for objetivo_id in idsobjetivo.split(","):
                            equipamiento.objetivo.add(objetivo_id)

                        equipamiento.save(request)

                    # Elimino detalles Equipamiento
                    if equipoelim:
                        for registro in equipoelim:
                            equipamiento = ProyectoInvestigacionInformeEquipamiento.objects.get(pk=registro['idreg'])
                            equipamiento.status = False
                            equipamiento.objetivo.clear()
                            equipamiento.save(request)

                    # Guarda detalle de Indicadores
                    for idreg, indicador, descripcion, fuente, lineabase in zip(idsregindicador, indicadores, descripcionesindicador, fuentesdatos, ldatoslineabase):
                        # Si es registro nuevo
                        if int(idreg) == 0:
                            indicadorresultado = ProyectoInvestigacionInformeIndicador(
                                informe=informeproyecto,
                                indicador=indicador.strip(),
                                descripcion=descripcion.strip(),
                                fuentedato=fuente.strip(),
                                lineabase=lineabase.strip()
                            )
                        else:
                            indicadorresultado = ProyectoInvestigacionInformeIndicador.objects.get(pk=idreg)
                            indicadorresultado.indicador = indicador.strip()
                            indicadorresultado.descripcion = descripcion.strip()
                            indicadorresultado.fuentedato = fuente.strip()
                            indicadorresultado.lineabase = lineabase.strip()

                        indicadorresultado.save(request)

                    # Elimino detalles Indicadores
                    if indicadorelim:
                        for registro in indicadorelim:
                            indicadorresultado = ProyectoInvestigacionInformeIndicador.objects.get(pk=registro['idreg'])
                            indicadorresultado.status = False
                            indicadorresultado.save(request)

                    log(u'%s editó informe final del proyecto: %s' % (persona, informeproyecto.proyecto), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El informe del proyecto de investigación no existe", "showSwal": "True", "swalType": "warning"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'finalizaredicion':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto el informe
                informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['id'])))

                resp = informeproyecto.informacion_completa()

                if resp["valido"]:
                    # Actualizo el estado del informe
                    informeproyecto.estado = 3
                    informeproyecto.save(request)

                    # Notificar por e-mail a la coordinación de investigación
                    # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                    listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, . . .sga7@unemi.edu.ec

                    # Destinatarios
                    # lista_email_envio = ['investigacion@unemi.edu.ec']
                    lista_email_cco = []
                    lista_email_envio = ['ivan_saltos_medina@hotmail.com']
                    lista_archivos_adjuntos = []

                    fechaenvio = datetime.now().date()
                    horaenvio = datetime.now().time()
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                    tituloemail = "Registro de Informe Final de Proyecto de Investigación"
                    titulo = "Proyectos de Investigación"
                    tiponotificacion = 'FINALIZAINFORMEFINAL'

                    send_html_mail(tituloemail,
                                   "emails/propuestaproyectoinvestigacion.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'tiponotificacion': tiponotificacion,
                                    'numeroinforme': informeproyecto.numero,
                                    'tipoinforme': 'un informe de avance' if informeproyecto.tipo == 1 else 'el informe final',
                                    'proyecto': informeproyecto.proyecto
                                    },
                                   lista_email_envio,  # Destinatarioa
                                   lista_email_cco,  # Copia oculta
                                   lista_archivos_adjuntos,  # Adjunto(s)
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )
                    log(u'%s agregó informe final al proyecto: %s' % (persona, informeproyecto.proyecto), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La información del informe está incompleta:" + resp["mensajes"], "showSwal": "True", "swalType": "warning"})
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

        elif action == 'finalizaredicionpresupuesto':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                permisoedicion = proyecto.permiso_edicion_vigente(1, 1)

                # Actualizar el permiso
                permisoedicion.finedi = datetime.now().date()
                permisoedicion.estado = 3
                permisoedicion.save(request)

                # Notificar por e-mail a la coordinación de investigación
                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, . . .sga7@unemi.edu.ec

                # Destinatarios
                lista_email_envio = ['investigacion@unemi.edu.ec']
                lista_email_cco = []
                lista_adjuntos = []

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
                tituloemail = "Edición de los Rubros del Presupuesto de Proyecto de Investigación Finalizado"
                titulo = "Proyectos de Investigación"

                send_html_mail(tituloemail,
                               "emails/propuestaproyectoinvestigacion.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': 'EDIPREFIN',
                                'proyecto': proyecto
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'%s finalizó edición de los rubros del presupuesto %s' % (persona, permisoedicion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al actualizar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'finalizaredicioncronograma':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                permisoedicion = proyecto.permiso_edicion_vigente(2, 1)

                # Actualizar el proyecto
                proyecto.cronoediprorroga = True
                proyecto.save(request)

                # Actualizar el permiso
                permisoedicion.finedi = datetime.now().date()
                permisoedicion.estado = 3
                permisoedicion.save(request)

                # Notificar por e-mail a la coordinación de investigación
                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, . . .sga7@unemi.edu.ec

                # Destinatarios
                lista_email_envio = ['investigacion@unemi.edu.ec']
                lista_email_cco = []
                lista_adjuntos = []

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
                tituloemail = "Edición del Cronograma de Actividades de Proyecto de Investigación Finalizado"
                titulo = "Proyectos de Investigación"

                send_html_mail(tituloemail,
                               "emails/propuestaproyectoinvestigacion.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': 'EDICROPRORRFIN',
                                'proyecto': proyecto
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'%s finalizó edición del cronograma de actividades %s' % (persona, permisoedicion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al actualizar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addavanceactividad':
            try:
                if 'idp' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['idp'])))
                fi = str(int(encrypt(request.POST['finicio'])))
                ff = str(int(encrypt(request.POST['ffin'])))
                inicio = datetime.strptime(f'{fi[0:4]}-{fi[4:6]}-{fi[6:8]}', '%Y-%m-%d').date()
                fin = datetime.strptime(f'{ff[0:4]}-{ff[4:6]}-{ff[6:8]}', '%Y-%m-%d').date()
                observacion = request.POST['observacion'].strip()

                # Obtiene los valores del detalle de actividades
                idsactividades = request.POST.getlist('idsactividad[]')
                ponderaciones = request.POST.getlist('ponderaciones[]')
                porcentajesavance = request.POST.getlist('porcentajesavance[]')
                avanceactual = Decimal(sum([float(p) for p in porcentajesavance]) / len(porcentajesavance)).quantize(Decimal('.01'))
                if avanceactual == 0:
                    estadoactual = 1
                elif avanceactual < 100:
                    estadoactual = 2
                else:
                    estadoactrual = 3

                # Validar que no esté repetido
                if ProyectoInvestigacionAvanceActividad.objects.filter(status=True, proyecto=proyecto, inicio=inicio).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"El registro de avances del mes de {getmonthname(inicio)} se encuentra repetido", "showSwal": "True", "swalType": "warning"})

                # Guardar el registro de avance
                avanceactividad = ProyectoInvestigacionAvanceActividad(
                    proyecto=proyecto,
                    inicio=inicio,
                    fin=fin,
                    avanceanterior=0,
                    estadoanterior=1,
                    avanceactual=avanceactual,
                    estadoactual=estadoactual,
                    observacion=observacion
                )
                avanceactividad.save(request)

                # Guardar los detalles de avances
                for idactividad, ponderacion, porcentajeavance in zip(idsactividades, ponderaciones, porcentajesavance):
                    # Obtener estado y calcular porcentaje de lo ejecutado en cuanto a la ponderación
                    porcentaje = float(porcentajeavance)
                    ponderacion = float(ponderacion)
                    if porcentaje == 0:
                        estado = 1
                    elif porcentaje < 100:
                        estado = 2
                    else:
                        estado = 3

                    porcpondejec = Decimal((porcentaje * ponderacion) / 100).quantize(Decimal('.01'))

                    # Guardar el detalle de avance
                    detalleavanceactividad = ProyectoInvestigacionDetalleAvanceActividad(
                        avanceactividad=avanceactividad,
                        actividad_id=idactividad,
                        pondavanceanterior=0,
                        avanceanterior=0,
                        estadoanterior=1,
                        pondavanceactual=porcpondejec,
                        avanceactual=porcentaje,
                        estadoactual=estado
                    )
                    detalleavanceactividad.save(request)

                log(f'{persona} agregó avances de actividades de proyecto de investigación {avanceactividad}', request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editavanceactividad':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el registro de avance
                avanceactividad = ProyectoInvestigacionAvanceActividad.objects.get(pk=int(encrypt(request.POST['id'])))
                observacion = request.POST['observacion'].strip()

                # Obtiene los valores del detalle de actividades
                idsdetalles = request.POST.getlist('idsdetalles[]')
                ponderaciones = request.POST.getlist('ponderaciones[]')
                porcentajesavance = request.POST.getlist('porcentajesavance[]')
                avanceactual = Decimal(sum([float(p) for p in porcentajesavance]) / len(porcentajesavance)).quantize(Decimal('.01'))
                if avanceactual == 0:
                    estadoactual = 1
                elif avanceactual < 100:
                    estadoactual = 2
                else:
                    estadoactrual = 3

                # Actualizar el registro de avance
                avanceactividad.avanceactual = avanceactual
                avanceactividad.estadoactual = estadoactual
                avanceactividad.observacion = observacion
                avanceactividad.save(request)

                # Acualizar los detalles de avances
                for iddetalle, ponderacion, porcentajeavance in zip(idsdetalles, ponderaciones, porcentajesavance):
                    # Obtener estado y calcular porcentaje de lo ejecutado en cuanto a la ponderación
                    porcentaje = float(porcentajeavance)
                    ponderacion = float(ponderacion)
                    if porcentaje == 0:
                        estado = 1
                    elif porcentaje < 100:
                        estado = 2
                    else:
                        estado = 3

                    porcpondejec = Decimal((porcentaje * ponderacion) / 100).quantize(Decimal('.01'))

                    # Consultar el detalle
                    detalleavanceactividad = ProyectoInvestigacionDetalleAvanceActividad.objects.get(pk=iddetalle)
                    detalleavanceactividad.pondavanceactual = porcpondejec
                    detalleavanceactividad.avanceactual = porcentaje
                    detalleavanceactividad.estadoactual = estado
                    detalleavanceactividad.save(request)

                log(f'{persona} editó avances de actividades de proyecto de investigación {avanceactividad}', request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})



        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Solicitud incorrecta.", "showSwal": "True", "swalType": "error"})

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'mostrarrecorrido':
                try:
                    title = u'Recorrido de la Propuesta de Proyecto'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['proyecto'] = proyecto
                    data['recorrido'] = proyecto.proyectoinvestigacionrecorrido_set.filter(status=True).order_by('id')
                    data['perfildocente'] = True
                    template = get_template("pro_proyectoinvestigacion/recorridopropuesta.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mostrarnovedad':
                try:
                    title = u"Novedades de la Propuesta de Proyecto de Investigación"
                    # propuestas = ProyectoInvestigacion.objects.filter(status=True, convocatoria_id=int(encrypt(request.GET['id'])), profesor__persona=persona, estado__valor__in=[4, 26]).order_by('-id')
                    propuestas = ProyectoInvestigacion.objects.filter(Q(estado__valor__in=[4, 26]) | Q(estadodatogeneral=4) | Q(estadointegrante=4) | Q(estadocontenido=4) | Q(estadopresupuesto=4) | Q(estadocronogramarev=4) | Q(estadodocumentofirmado=4), status=True, convocatoria_id=int(encrypt(request.GET['id'])), profesor__persona=persona).order_by('-id')
                    data['propuestas'] = propuestas
                    template = get_template("pro_proyectoinvestigacion/novedad.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

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

            elif action == 'addintegrante':
                try:
                    data['title'] = u'Agregar Integrante a Proyecto de Investigación'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    convocatoria = proyecto.convocatoria
                    data['proyecto'] = proyecto
                    data['tipopersona'] = TIPO_INTEGRANTE
                    data['funcionpersona'] = ((2, u'CO-DIRECTOR'),
                                             (3, u'INVESTIGADOR ASOCIADO'),
                                             (4, u'AYUDANTE DE INVESTIGACIÓN'),
                                             (5, u'INVESTIGADOR COLABORADOR'))

                    data['mostrarbotonagrexterno'] = proyecto.cantidad_integrantes_externos() < convocatoria.maxintegrantee

                    template = get_template("pro_proyectoinvestigacion/addintegrante.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editintegrante':
                try:
                    data['title'] = u'Editar Rol del Integrante'
                    integrante = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.GET['idi'])))
                    data['tipopersona'] = integrante.get_tipo_display()
                    data['tipoper'] = integrante.tipo
                    data['funcionper'] = integrante.funcion
                    data['integranteid'] = integrante.id
                    data['integrante'] = integrante.persona
                    data['funcionpersona'] = ((2, u'CO-DIRECTOR'),
                                             (3, u'INVESTIGADOR ASOCIADO'))

                    template = get_template("pro_proyectoinvestigacion/editintegrante.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

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
                                                        status=True,  ).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        personas = Profesor.objects.filter(persona__apellido1__icontains=s[0],
                                                           persona__apellido2__icontains=s[1],
                                                           status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso())} for x in personas]}
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

                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso())} for x in personas]}
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
                            "entregables": actividad.entregable if actividad.entregable else actividad.entregables()}

                    return JsonResponse(data)
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos [%s]" % msg})

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

                    template = get_template("pro_proyectoinvestigacion/adddetallepresupuesto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editdetallepresupuesto':
                try:
                    data['title'] = u'Editar Detalle del Presupuesto'
                    data['detalle'] = detalle = ProyectoInvestigacionItemPresupuesto.objects.get(pk=int(encrypt(request.GET['id'])))

                    # Si el tipo de recurso es MATERIALES, se arma una lista de lo existente en bodega más lo que han ingresado en proyectos
                    if detalle.tiporecurso.abreviatura == 'MAT':
                        lista_bodega = [producto.descripcion for producto in Producto.objects.filter(status=True).distinct().order_by('descripcion')]
                        lista_recurso_proyecto = [recurso.recurso for recurso in ProyectoInvestigacionItemPresupuesto.objects.filter(status=True, tiporecurso__abreviatura='MAT').distinct().order_by('recurso')]
                        materiales = list(dict.fromkeys(lista_bodega + lista_recurso_proyecto))
                        materiales.sort()
                        data['materiales'] = materiales

                    template = get_template("pro_proyectoinvestigacion/editdetallepresupuesto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'proformadetallepresupuesto':
                try:
                    data['title'] = u'Proformas del Rubro del Presupuesto'
                    data['detalle'] = detalle = ProyectoInvestigacionItemPresupuesto.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['tipoanexos'] = ", ".join(variable_valor("TIPOS_PROFORMAS_PROYECTOS_INV"))
                    data['tamanio'] = variable_valor("TAMANIO_PROFORMAS_PROYECTOS_INV")
                    data['obligatorio'] = 'S'
                    template = get_template("pro_proyectoinvestigacion/proformadetallepresupuesto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mostrarproformadetallepresupuesto':
                try:
                    data['title'] = u'Proformas del Rubro del Presupuesto'
                    data['detalle'] = detalle = ProyectoInvestigacionItemPresupuesto.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("adm_proyectoinvestigacion/modal/proformadetallepresupuesto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addactividadcronograma':
                try:
                    data['title'] = u'Agregar Actividad al Cronograma'
                    data['proyecto'] = proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    data['objetivo'] = objetivo = ProyectoInvestigacionObjetivo.objects.get(pk=int(encrypt(request.GET['idobj'])))
                    data['integrantes'] = proyecto.integrantes_proyecto_informe()
                    data['fecha'] = datetime.now().date()
                    data['numobj'] = request.GET['numobj']

                    template = get_template("pro_proyectoinvestigacion/addactividadcronograma.html")
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
                    data['editponderacion'] = not actividad.ultimo_avance_actividad()
                    template = get_template("pro_proyectoinvestigacion/editactividadcronograma.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addpropuestaproyecto':
                try:
                    data['title'] = u'Agregar Propuesta de Proyecto de Investigación'
                    convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.GET['idc'])))

                    institucionunemi = TituloInstitucion.objects.get(pk=1)
                    representante = DistributivoPersona.objects.get(denominacionpuesto_id=113, status=True)

                    form = RegistroPropuestaProyectoInvestigacionForm(initial={
                        'convocatoria': convocatoria.descripcion,
                        'nombreinsejec': institucionunemi.nombre,
                        'representanteinsejec': representante.persona.nombre_completo(),
                        'cedulainsejec': representante.persona.cedula,
                        'telefonoinsejec': institucionunemi.telefono,
                        'faxinsejec': '',
                        'emailinsejec': representante.persona.emailinst,
                        'direccioninsejec': institucionunemi.direccion,
                        'paginawebinsejec': institucionunemi.web
                    })

                    data['convocatoria'] = convocatoria
                    data['coordinaciones'] = Coordinacion.objects.filter(status=True, pk__lte=5).order_by('nombre')
                    form.cargarprogramas(convocatoria)
                    data['form'] = form
                    return render(request, "pro_proyectoinvestigacion/addproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'editpropuestaproyecto':
                try:
                    data['title'] = u'Editar Propuesta de Proyecto de Investigación'

                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    iejecutora = ProyectoInvestigacionInstitucion.objects.get(proyecto=proyecto, tipo=1)
                    existecoejecutora = 1 if ProyectoInvestigacionInstitucion.objects.filter(proyecto=proyecto, tipo=2, status=True).exists() else 2
                    form = RegistroPropuestaProyectoInvestigacionForm(initial={
                        'categoria': proyecto.categoria2,
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
                        'representanteinsejec': iejecutora.representante,
                        'cedulainsejec': iejecutora.cedula,
                        'telefonoinsejec': iejecutora.telefono,
                        'faxinsejec': iejecutora.fax,
                        'emailinsejec': iejecutora.email,
                        'direccioninsejec': iejecutora.direccion,
                        'paginawebinsejec': iejecutora.paginaweb,
                        'nombreinsejec': iejecutora.nombre,
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

                    return render(request, "pro_proyectoinvestigacion/editproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'contenidoproyecto':
                try:
                    data['title'] = u'Contenido de Proyecto de Investigación'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))

                    form = ContenidoProyectoInvestigacionForm(initial={
                        'titulo': proyecto.titulo
                    })

                    data['objetivos'] = objetivos = proyecto.objetivos_especificos()
                    data['totalobjetivos'] = len(objetivos)
                    resultados = proyecto.resultados_compromisos()
                    tiposresultados = []

                    if not resultados:
                        tiposresultados = TipoResultadoCompromiso.objects.filter(convocatoria=proyecto.convocatoria, status=True, fijo=True).order_by('numero')

                    data['resultados'] = resultados
                    data['tiposresultados'] = tiposresultados
                    data['totalresultados'] = len(tiposresultados) if tiposresultados else len(resultados)
                    data['form'] = form
                    data['id'] = request.GET['id']
                    data['existeresumen'] = True if proyecto.resumenpropuesta else False
                    data['puedeeditar'] = proyecto.estado.valor in [1, 4, 15, 16, 28, 29, 38, 39, 40, 41]

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
                    return render(request, "pro_proyectoinvestigacion/contenidoproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpresupuestoproyecto':
                try:
                    data['title'] = u'Agregar Presupuesto de Proyecto de Investigación'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))

                    if proyecto.compraequipo == 3:
                        montominimoequipos = 0
                    else:
                        regfin = ConvocatoriaMontoFinanciamiento.objects.get(convocatoria=proyecto.convocatoria, tipoequipamiento=proyecto.compraequipo)
                        montominimoequipos = Decimal(proyecto.montounemi * (regfin.porcentajecompra)/100).quantize(Decimal('.01'))


                    form = PresupuestoProyectoInvestigacionForm(initial={'titulo': proyecto.titulo,
                                                                         'compraequipo': proyecto.get_compraequipo_display(),
                                                                         'director': persona.nombre_completo(),
                                                                         'montototal': proyecto.montototal,
                                                                         'minimocompraequipo': montominimoequipos,
                                                                         'meses': str(proyecto.tiempomes) + ' MESES'})

                    tiposrecursos = TipoRecursoPresupuesto.objects.filter(status=True, vigente=True).order_by('orden', 'descripcion')
                    # if proyecto.compraequipo == 3:
                    #     tiposrecursos = tiposrecursos.exclude(orden=3)

                    data['tiposrecursos'] = tiposrecursos
                    data['form'] = form
                    data['id'] = request.GET['id']
                    data['idconvocatoria'] = proyecto.convocatoria.id
                    data['anioconvocatoria'] = proyecto.convocatoria.apertura.year
                    data['totalafinanciar'] = proyecto.montototal + Decimal(0.05).quantize(Decimal('.01'))
                    data['unidadesmedida'] = UnidadMedida.objects.filter(status=True).order_by('nombre')

                    lista_bodega = [producto.descripcion for producto in Producto.objects.filter(status=True).distinct().order_by('descripcion')]
                    lista_recurso_proyecto = [recurso.recurso for recurso in ProyectoInvestigacionItemPresupuesto.objects.filter(status=True, tiporecurso__abreviatura='MAT').distinct().order_by('recurso')]
                    productos = list(dict.fromkeys(lista_bodega + lista_recurso_proyecto))
                    productos.sort()
                    data['productos'] = productos
                    data['personalproyecto'] = proyecto.integrantes_proyecto()
                    return render(request, "pro_proyectoinvestigacion/addpresupuestoproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'editpresupuestoproyecto':
                try:
                    data['title'] = u'Editar Presupuesto de Proyecto de Investigación'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))

                    if proyecto.compraequipo == 3:
                        montominimoequipos = 0
                    else:
                        regfin = ConvocatoriaMontoFinanciamiento.objects.get(convocatoria=proyecto.convocatoria, tipoequipamiento=proyecto.compraequipo)
                        montominimoequipos = Decimal(proyecto.montounemi * (regfin.porcentajecompra)/100).quantize(Decimal('.01'))

                    form = PresupuestoProyectoInvestigacionForm(initial={'titulo': proyecto.titulo,
                                                                         'compraequipo': proyecto.get_compraequipo_display(),
                                                                         'director': persona.nombre_completo(),
                                                                         'montototal': proyecto.montototal,
                                                                         'minimocompraequipo': montominimoequipos,
                                                                         'meses': str(proyecto.tiempomes) + ' MESES'})

                    tiposrecursos = TipoRecursoPresupuesto.objects.filter(status=True, vigente=True).order_by('orden', 'descripcion')
                    # if proyecto.compraequipo == 3:
                    #     tiposrecursos = tiposrecursos.exclude(orden=3)

                    data['tiposrecursos'] = tiposrecursos
                    data['detallepresupuesto'] = proyecto.proyectoinvestigacionitempresupuesto_set.filter(status=True).order_by('id')

                    # data['detallepasajes'] = proyecto.proyectoinvestigacionpasajeintegrante_set.filter(status=True, tipopasaje=1).order_by('id')
                    data['detallepasajes'] = proyecto.proyectoinvestigacionpasajeintegrante_set.filter(status=True, tipopasaje__in=[1, 3]).order_by('id')
                    data['detallepasajesnac'] = proyecto.proyectoinvestigacionpasajeintegrante_set.filter(status=True, tipopasaje=2).order_by('id')
                    # data['detalleviaticos'] = proyecto.proyectoinvestigacionviaticointegrante_set.filter(status=True, tipoviatico=1).order_by('id')
                    data['detalleviaticos'] = proyecto.proyectoinvestigacionviaticointegrante_set.filter(status=True, tipoviatico__in=[1, 3]).order_by('id')
                    data['detalleviaticosnac'] = proyecto.proyectoinvestigacionviaticointegrante_set.filter(status=True, tipoviatico=2).order_by('id')

                    data['detallemovilizaciones'] = x = proyecto.proyectoinvestigacionmovilizacionintegrante_set.filter(status=True, tipomovilizacion__in=[1, 3]).order_by('id')


                    data['form'] = form
                    data['id'] = request.GET['id']
                    data['idconvocatoria'] = proyecto.convocatoria.id
                    data['anioconvocatoria'] = proyecto.convocatoria.apertura.year
                    data['totalafinanciar'] = proyecto.montototal + Decimal(0.05).quantize(Decimal('.01'))
                    data['unidadesmedida'] = UnidadMedida.objects.filter(status=True).order_by('nombre')

                    lista_bodega = [producto.descripcion for producto in Producto.objects.filter(status=True).distinct().order_by('descripcion')]
                    lista_recurso_proyecto = [recurso.recurso for recurso in ProyectoInvestigacionItemPresupuesto.objects.filter(status=True, tiporecurso__abreviatura='MAT').distinct().order_by('recurso')]
                    productos = list(dict.fromkeys(lista_bodega + lista_recurso_proyecto))
                    productos.sort()
                    data['productos'] = productos
                    data['personalproyecto'] = proyecto.integrantes_proyecto()
                    data['estadoproyecto'] = proyecto.estado.valor
                    data['puedeeditar'] = proyecto.estado.valor in [1, 4, 15, 16, 28, 29, 38, 39, 40, 41]

                    return render(request, "pro_proyectoinvestigacion/editpresupuestoproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcronograma':
                try:
                    data['title'] = u'Agregar Cronograma de Actividades de Proyecto de Investigación'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))

                    form = CronogramaActividadProyectoInvestigacionForm(initial={'titulo': proyecto.titulo,
                                                                                'director': persona.nombre_completo(),
                                                                                'montototal': proyecto.montototal,
                                                                                'totalpresupuesto': proyecto.presupuesto,
                                                                                'meses': str(proyecto.tiempomes) + ' MESES',
                                                                                'objetivogeneral': proyecto.objetivogeneral
                                                                                 })



                    data['objetivos'] = proyecto.objetivos_especificos()
                    data['personalproyecto'] = proyecto.integrantes_proyecto()
                    data['form'] = form
                    data['id'] = request.GET['id']
                    data['idconvocatoria'] = proyecto.convocatoria.id
                    return render(request, "pro_proyectoinvestigacion/addcronograma.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcronograma':
                try:
                    data['title'] = u'Editar Cronograma de Actividades de Proyecto de Investigación'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))

                    form = CronogramaActividadProyectoInvestigacionForm(initial={'titulo': proyecto.titulo,
                                                                                 'director': persona.nombre_completo(),
                                                                                 'montototal': proyecto.montototal,
                                                                                 'totalpresupuesto': proyecto.presupuesto,
                                                                                 'meses': str(proyecto.tiempomes) + ' MESES',
                                                                                 'objetivogeneral': proyecto.objetivogeneral})

                    data['objetivos'] = proyecto.objetivos_especificos()
                    data['personalproyecto'] = proyecto.integrantes_proyecto()
                    data['detallecronograma'] = proyecto.cronograma_actividades()
                    data['form'] = form
                    data['id'] = request.GET['id']
                    data['idconvocatoria'] = proyecto.convocatoria.id
                    data['estadoproyecto'] = proyecto.estado.valor
                    data['puedeeditar'] = proyecto.estado.valor in [1, 4, 15, 16, 28, 29, 38, 39, 40, 41, 13]

                    return render(request, "pro_proyectoinvestigacion/editcronograma.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirdocumento':
                try:
                    data['title'] = u'Subir Formato de Inscripción Firmado'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['proyecto'] = proyecto
                    template = get_template("pro_proyectoinvestigacion/subirdocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
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

            elif action == 'subircertificadoinvestigador':
                try:
                    data['title'] = u'Subir Certificado de Registro como Investigador'
                    data['integrante'] = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("pro_proyectoinvestigacion/modal/subircertificadoinvestigador.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subirhojavida':
                try:
                    data['title'] = u'Subir Hoja de Vida del Participante Externo'
                    data['integrante'] = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("pro_proyectoinvestigacion/modal/subirhojavida.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'finalizaedicion':
                try:
                    data['title'] = u'Finalizar Edición de la Propuesta de proyecto'
                    data['proyecto'] = proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    contenidocorreo = "Estimados, <br><br>Se les comunica que el docente <strong>" + proyecto.nombre_director_proyecto_inverso() + "</strong> registró una propuesta de proyecto de investigación con el título: <strong>" + proyecto.titulo + "</strong>"
                    data['contenidocorreo'] = contenidocorreo
                    form = FinalizaEdicionForm(initial={'contenido': contenidocorreo})
                    data['form'] = form

                    return render(request, "pro_proyectoinvestigacion/finalizaedicion.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento del proyecto."})

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
                    data['puedeeditar'] = proyecto.estado.valor in [1, 4, 15, 16, 28, 29, 38, 39, 41, 41]
                    data['minimou'] = convocatoria.minintegranteu
                    data['maximou'] = maximou = convocatoria.maxintegranteu
                    data['minimoe'] = convocatoria.minintegrantee
                    data['maximoe'] = maximoe = convocatoria.maxintegrantee
                    data['registradosu'] = registradosu = integrantes.filter(funcion__in=[1, 2, 3, 4]).count()
                    data['registradose'] = registradose = integrantes.filter(funcion=5).count()
                    data['mostrarboton'] = x = (registradosu + registradose) < (maximou + maximoe)
                    data['tituloconvocatoria'] = convocatoria.descripcion
                    data['mensajesintegrantes'] = mensaje_consideraciones_integrantes(proyecto)

                    return render(request, "pro_proyectoinvestigacion/personalproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'addexterno':
                try:
                    data['title'] = u'Agregar Integrante Externo'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))

                    form = ExternoForm()
                    data['proyecto'] = proyecto
                    data['form'] = form
                    return render(request, "pro_proyectoinvestigacion/addpersonaexterna.html", data)
                except Exception as ex:
                    pass

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
                                                'institucionlabora': integrante.externo.institucionlabora,
                                                'cargodesempena': integrante.externo.cargodesempena})

                    data['proyecto'] = proyecto
                    data['integrante'] = integrante
                    data['form'] = form

                    return render(request, "pro_proyectoinvestigacion/editpersonaexterna.html", data)
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


                    # regfin = ConvocatoriaMontoFinanciamiento.objects.get(convocatoria=proyecto.convocatoria, tipoequipamiento=proyecto.compraequipo)
                    data['montominimoequipos'] = Decimal(proyecto.montounemi * (regfin.porcentajecompra) / 100).quantize(Decimal('.01'))
                    data['totalequipos'] = proyecto.totales_detalle_equipos()['totaldetalle']
                    data['permisoedicion'] = proyecto.permiso_edicion_vigente(1, 1)
                    data['puedeeditar'] = proyecto.estado.valor in [1, 4, 15, 16, 28, 29, 38, 39, 40, 41, 13] or proyecto.puede_editar_rubros_presupuesto(1)
                    data['textoequipos'] = 'Máximo Compra Equipos:' if regfin.tipoporcentaje == 2 else 'Mínimo Compra Equipos:'
                    data['tipoporcentaje'] = regfin.tipoporcentaje

                    return render(request, "pro_proyectoinvestigacion/presupuesto.html", data)
                except Exception as ex:
                    pass

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

                    data['permisoedicion'] = proyecto.permiso_edicion_vigente(2, 1)
                    data['puedeeditar'] = proyecto.estado.valor in [1, 4, 15, 16, 28, 29, 38, 39, 40, 41] or proyecto.puede_editar_cronograma_actividades(1)
                    # data['puedeeditar'] = proyecto.puede_editar_cronograma()
                    data['fecha'] = datetime.now().date()

                    return render(request, "pro_proyectoinvestigacion/cronograma.html", data)
                except Exception as ex:
                    pass

            elif action == 'mostrarevaluaciones':
                try:
                    title = u'Evaluaciones de la Propuesta de Proyecto'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['proyecto'] = proyecto
                    data['evaluaciones'] = proyecto.evaluaciones().filter(estadoregistro=5)
                    data['rubricas'] = proyecto.convocatoria.rubricas_evaluacion()
                    data['perfildocente'] = True
                    template = get_template("pro_proyectoinvestigacion/evaluaciones.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
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

                    if 'vpd' in request.GET:
                        data['documento'] = proyecto.archivodocumentoact.url
                        data['titulodocumento'] = 'Documento Actualizado del Proyecto'

                    return render(request, "pro_proyectoinvestigacion/informacionproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'propuestas':
                try:
                    idf = request.GET.get('idf', '')
                    search, url_vars = request.GET.get('s', ''), '&action=' + action
                    idc, ids = request.GET.get('idc', ''), request.GET.get('id', '')
                    url_vars += '&idc=' + idc

                    convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.GET['idc'])))

                    if idf:
                        proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(idf)))
                        data['formatoinscripcion'] = proyecto.archivodocumento.url
                        data['tipoformato'] = 'Formato de Inscripción del Proyecto'

                    if 'id' in request.GET:
                        data['id'] = ids = request.GET['id']
                        proyectos_director = ProyectoInvestigacion.objects.filter(convocatoria=convocatoria, status=True, pk=int(encrypt(request.GET['id'])))
                        proyectos = proyectos_director
                        url_vars += '&id=' + ids
                    elif 's' in request.GET:
                        search = request.GET['s']
                        data['s'] = search
                        proyectos_director = ProyectoInvestigacion.objects.filter(convocatoria=convocatoria, status=True, profesor__persona=persona, titulo__icontains=search)
                        otros_proyectos = ProyectoInvestigacion.objects.filter(convocatoria=convocatoria,
                                                                               titulo__icontains=search,
                                                                               status=True,
                                                                               proyectoinvestigacionintegrante__persona=persona,
                                                                               proyectoinvestigacionintegrante__status=True,
                                                                               proyectoinvestigacionintegrante__tiporegistro__in=[1, 3, 4],
                                                                               proyectoinvestigacionintegrante__funcion__in=[2, 3, 4, 5])
                        proyectos = proyectos_director | otros_proyectos
                        proyectos = proyectos.distinct().order_by('-id')
                        url_vars += '&s=' + search
                    else:
                        proyectos_director = ProyectoInvestigacion.objects.filter(convocatoria=convocatoria, status=True, profesor__persona=persona)
                        otros_proyectos = ProyectoInvestigacion.objects.filter(convocatoria=convocatoria,
                                                                               status=True,
                                                                               proyectoinvestigacionintegrante__persona=persona,
                                                                               proyectoinvestigacionintegrante__status=True,
                                                                               proyectoinvestigacionintegrante__tiporegistro__in=[1, 3, 4],
                                                                               proyectoinvestigacionintegrante__funcion__in=[2, 3, 4, 5])
                        proyectos = proyectos_director | otros_proyectos
                        proyectos = proyectos.distinct().order_by('-id')

                    existenovedad = proyectos_director.filter(estado__valor__in=[4, 27]).exists()

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

                    # Verificar si alguno de los proyectos tiene novedades con la fecha de inicio del proyecto y fecha de inicio de actividades
                    novedades = []

                    # Si existe periodo de convocatoria vigente
                    if convocatoria.esta_abierta():
                        aplica = aplica_para_director_proyecto(persona.profesor(), convocatoria)
                        if aplica['puedeaplicar']:
                            data['mostrarboton'] = True
                        else:
                            data['mostrarboton'] = False
                            data['mensaje'] = aplica['mensaje']
                            data['clasemsg'] = aplica['clase']
                    else:
                        data['mostrarboton'] = False
                        data['mensaje'] = "Atención!!! El periodo de registro de propuestas de proyectos está cerrado" if not proyectos else ''
                        data['clasemsg'] = "alert alert-error"

                    data['title'] = u'Mis propuestas de Proyectos de Investigación'
                    data['tituloconvocatoria'] = convocatoria.descripcion if convocatoria else ''
                    data['novedades'] = novedades
                    data['convocatoriaid'] = convocatoria.id
                    data['convocatoria'] = convocatoria
                    data['existenovedad'] = existenovedad

                    return render(request, "pro_proyectoinvestigacion/propuestas.html", data)
                except Exception as ex:
                    pass

            elif action == 'subircontrato':
                try:
                    data['title'] = u'Subir Contrato de Financiamiento'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['proyecto'] = proyecto

                    template = get_template("pro_proyectoinvestigacion/subircontratofinanciamiento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subirpresupuesto':
                try:
                    data['title'] = u'Subir Presupuesto Final del proyecto'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['proyecto'] = proyecto

                    template = get_template("pro_proyectoinvestigacion/subirpresupuesto.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'evidenciasproyecto':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Evidencias del Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    data['objetivos'] = proyecto.cronograma_objetivo()

                    return render(request, "pro_proyectoinvestigacion/evidencias.html", data)
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

            elif action == 'informesproyecto':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Informes del Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    data['informes'] = proyecto.informes_tecnicos()
                    data['rolparticipante'] = proyecto.rol_participante(persona)['id']

                    if 'idi' in request.GET:
                        informe = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.GET['idi'])))
                        data['informe'] = informe.archivo.url if informe.archivo else informe.archivogenerado.url
                        data['tipoinforme'] = f'Informe firmado {informe.numero}' if informe.archivo else f'Informe sin firma {informe.numero}'

                    return render(request, "pro_proyectoinvestigacion/informes.html", data)
                except Exception as ex:
                    pass

            elif action == 'informesproyectoold':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Informes del Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    data['informes'] = proyecto.informes_tecnicos()
                    data['rolparticipante'] = proyecto.rol_participante(persona)['id']

                    return render(request, "pro_proyectoinvestigacion/informesold.html", data)
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

                    tiposinformes = []
                    # if secuencia == 1:
                    #     tiposinformes.append({"id": 1, "descripcion" : "AVANCE"})
                    # else:
                    tiposinformes.append({"id": 1, "descripcion": "AVANCE"})
                        # tiposinformes.append({"id": 2, "descripcion": "FINAL"})

                    # data['avanceesperado'] = proyecto.porcentaje_avance_esperado()
                    # data['avanceejecucion'] = proyecto.porcentaje_avance_ejecucion()

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
                    data['numero'] = numero
                    data['fecha'] = datetime.now().date()
                    data['evidencias'] = proyecto.evidencias_subidas_validadas()
                    data['periodovigente'] = periodo_vigente_distributivo_docente_investigacion(proyecto.profesor)
                    data['tiposinformes'] = tiposinformes
                    # form = InformeProyectoForm(initial={
                    #     'fecha': datetime.now().date(),
                    #     'numero': numero
                    # })
                    # data['form'] = form

                    return render(request, "pro_proyectoinvestigacion/addinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinformefinal':
                try:
                    data['title'] = u'Agregar Informe Final de Proyecto de Investigación'
                    data['proyecto'] = proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    data['objetivos'] = proyecto.objetivos_especificos()
                    data['fecha'] = datetime.now().date()
                    data['rolesintegrantes'] = FUNCION_INTEGRANTE

                    return render(request, "pro_proyectoinvestigacion/addinformefinal.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinformefinal':
                try:
                    data['informe'] = informe = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Editar Informe Final de Proyecto de Investigación'
                    data['proyecto'] = proyecto = informe.proyecto
                    data['objetivos'] = proyecto.objetivos_especificos()
                    data['fecha'] = datetime.now().date()
                    data['rolesintegrantes'] = FUNCION_INTEGRANTE

                    return render(request, "pro_proyectoinvestigacion/editinformefinal.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinformeold':
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
                    data['fechanotificacion'] = str(resolucionaprueba.fechanotificaaprobacion.day) + " de " + MESES_CHOICES[resolucionaprueba.fechanotificaaprobacion.month - 1][1].capitalize() + " del " + str(resolucionaprueba.fechanotificaaprobacion.year)
                    data['fechainicio'] = str(proyecto.fechainicio.day) + " de " + MESES_CHOICES[proyecto.fechainicio.month - 1][1].capitalize() + " del " + str(proyecto.fechainicio.year)
                    data['fechafinestimada'] = str(proyecto.fechafinplaneado.day) + " de " + MESES_CHOICES[proyecto.fechafinplaneado.month - 1][1].capitalize() + " del " + str(proyecto.fechafinplaneado.year)
                    data['mesinicio'] = MESES_CHOICES[proyecto.fechainicio.month - 1][1].capitalize() + " del " + str(proyecto.fechainicio.year)
                    data['integrantes'] = integrantes = proyecto.integrantes_proyecto_informe()
                    data['codirector'] = integrantes.filter(funcion=2)
                    data['investigadores'] = integrantes.filter(funcion=3)
                    data['asistentes'] = integrantes.filter(funcion=4)
                    data['numero'] = numero
                    data['fecha'] = datetime.now().date()
                    data['evidencias'] = proyecto.evidencias_subidas_validadas()
                    data['periodovigente'] = periodo_vigente_distributivo_docente_investigacion(proyecto.profesor)

                    form = InformeProyectoForm(initial={
                        'fecha': datetime.now().date(),
                        'numero': numero
                    })
                    data['form'] = form

                    return render(request, "pro_proyectoinvestigacion/addinformeold.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinforme':
                try:
                    data['informe'] = informe = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.GET['id'])))
                    tipoinforme = informe.get_tipo_display() if informe.tipo == 2 else informe.get_tipo_display() + ' ' + str(informe.secuencia)
                    data['title'] = u'Editar Informe de Proyecto de Investigación (INFORME ' + tipoinforme + ')'

                    tiposinformes = []
                    # if informe.secuencia == 1:
                    tiposinformes.append({"id": 1, "descripcion": "AVANCE"})
                    # else:
                        # tiposinformes.append({"id": 1, "descripcion": "AVANCE"})
                        # tiposinformes.append({"id": 2, "descripcion": "FINAL"})

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
                    data['actividades'] = actividades = informe.actividades()
                    data['totalactividades'] = actividades.count()
                    data['numero'] = numero = informe.numero
                    data['fecha'] = fecha = informe.fecha
                    data['evidencias'] = evidencias = informe.proyectoinvestigacioninformeanexo_set.filter(status=True).order_by('id')
                    data['totalevidencias'] = evidencias.count()
                    data['periodovigente'] = informe.periodo
                    data['tiposinformes'] = tiposinformes

                    return render(request, "pro_proyectoinvestigacion/editinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinformeold':
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
                    data['fecha'] = fecha = informe.fecha
                    data['evidencias'] = informe.proyectoinvestigacioninformeanexo_set.filter(status=True).order_by('id')
                    data['periodovigente'] = informe.periodo

                    form = InformeProyectoForm(initial={
                        'fecha': fecha,
                        'numero': numero
                    })
                    data['form'] = form

                    return render(request, "pro_proyectoinvestigacion/editinformeold.html", data)
                except Exception as ex:
                    pass

            elif action == 'firmarinformeavance':
                try:
                    data['title'] = u'Firmar Informe de Proyecto de Investigación'

                    informe = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['solicitud'] = informe
                    data['iddoc'] = informe.id  # ID del documento a firmar
                    data['idper'] = informe.proyecto.profesor.persona.id  # ID de la persona que firma
                    data['tipofirma'] = 'SOL'

                    data['mensaje'] = "Firma del Informe de Proyecto de Investigación N° <b>{}</b> del director de proyecto <b>{}</b>".format(informe.numero, informe.proyecto.profesor.persona.nombre_completo_inverso())
                    data['accionfirma'] = action

                    template = get_template("pro_becadocente/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subirinforme':
                try:
                    informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Subir Informe de Avance Firmado' if informeproyecto.tipo == 1 else u'Subir Informe Final Firmado'
                    data['informeproyecto'] = informeproyecto

                    template = get_template("pro_proyectoinvestigacion/subirinforme.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mostrardistributivo':
                try:
                    data['title'] = 'Distributivo Horas de Investigación'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    periodovigente = Periodo.objects.get(pk=int(encrypt(request.GET['idper']))) if request.GET['idper'] else None

                    data['proyecto'] = proyecto
                    data['periodovigente'] = periodovigente

                    integrantes = proyecto.integrantes_proyecto_informe()
                    # Obtengo los integrantes tipo PROFESOR
                    data['integrantes'] = integrantes.filter(tipo=1)

                    template = get_template("pro_proyectoinvestigacion/distributivoinvestigacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'proyectosevaluar':
                try:
                    search = None
                    ids = None

                    convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.GET['idc'])))

                    if 'id' in request.GET:
                        ids = request.GET['id']
                        proyectos = ProyectoInvestigacion.objects.filter(convocatoria=convocatoria, status=True, pk=int(encrypt(request.GET['id'])))
                    elif 's' in request.GET:
                        search = request.GET['s']
                        proyectos = ProyectoInvestigacion.objects.filter(convocatoria=convocatoria, status=True, proyectoinvestigacionevaluador__persona=persona, proyectoinvestigacionevaluador__tipo=1, proyectoinvestigacionevaluador__tipoproyecto=2, proyectoinvestigacionevaluador__status=True, titulo__icontains=search)
                    else:
                        proyectos = ProyectoInvestigacion.objects.filter(convocatoria=convocatoria, status=True, proyectoinvestigacionevaluador__persona=persona, proyectoinvestigacionevaluador__tipo=1, proyectoinvestigacionevaluador__tipoproyecto=2, proyectoinvestigacionevaluador__status=True).order_by('-id')

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


                    data['title'] = u'Proyectos de Investigación a Evaluar'
                    data['tituloconvocatoria'] = convocatoria.descripcion if convocatoria else ''

                    return render(request, "pro_proyectoinvestigacion/proyectosevaluar.html", data)
                except Exception as ex:
                    pass

            elif action == 'agregaractividadinforme':
                try:
                    data['title'] = u'Agregar Actividad a Informe de Proyecto de Investigación'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))

                    data['proyecto'] = proyecto
                    data['periodovigente'] = periodo_vigente_distributivo_docente_investigacion(proyecto.profesor)
                    data['objetivos'] = proyecto.objetivos_especificos()
                    # data['actividades'] = proyecto.cronograma_actividades_pendientes()
                    data['integrantes'] = proyecto.integrantes_proyecto_informe()

                    template = get_template("pro_proyectoinvestigacion/addactividadinforme.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mostrarevidenciasinforme':
                try:
                    informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['informe'] = informeproyecto
                    data['evidencias'] = evidencias = informeproyecto.evidencias() if informeproyecto.tipo == 1 else informeproyecto.evidencias_informe_final()

                    template = get_template("pro_proyectoinvestigacion/evidenciainforme.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
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
                    data['title'] = u'Avances de Actividades del Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    data['puedeagregar'] = not proyecto.avances_actividades()

                    return render(request, "pro_proyectoinvestigacion/avanceactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'addavanceactividad':
                try:
                    data['title'] = u'Agregar Avances de Actividades del Proyecto de Investigación'
                    data['proyecto'] = proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    data['objetivos'] = proyecto.objetivos_especificos()
                    fechainicio = datetime.strptime('2024-09-01', '%Y-%m-%d').date()
                    fechafin = getlastdayofmonth(fechainicio)
                    data['fechainicio'] = fechainicio
                    data['finicio'] = encrypt(fechainicio.strftime("%Y%m%d"))
                    data['ffin'] = encrypt(fechafin.strftime("%Y%m%d"))
                    data['estados'] = [
                        {"id": 1, "descripcion": "POR INICIAR"},
                        {"id": 2, "descripcion": "EN EJECUCIÓN"},
                        {"id": 3, "descripcion": "FINALIZADA"}
                    ]
                    return render(request, "pro_proyectoinvestigacion/addavanceactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'editavanceactividad':
                try:
                    data['title'] = u'Editar Avances de Actividades del Proyecto de Investigación'
                    data['avanceactividad'] = avanceactividad = ProyectoInvestigacionAvanceActividad.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['proyecto'] = proyecto = avanceactividad.proyecto
                    data['objetivos'] = proyecto.objetivos_especificos()
                    data['estados'] = [
                        {"id": 1, "descripcion": "POR INICIAR"},
                        {"id": 2, "descripcion": "EN EJECUCIÓN"},
                        {"id": 3, "descripcion": "FINALIZADA"}
                    ]
                    return render(request, "pro_proyectoinvestigacion/editavanceactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'convocatorias':
                try:
                    url_vars = ''
                    convocatorias = ConvocatoriaProyecto.objects.filter(status=True, visible=True).order_by('-apertura', '-cierre')
                    # convocatorias = ConvocatoriaProyecto.objects.filter(status=True).order_by('-apertura', '-cierre')

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
                    data['enlaceatras'] = "/pro_investigacion?action=convocatorias"

                    return render(request, "pro_proyectoinvestigacion/convocatoriaproyecto.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            url_vars = ''
            convocatorias = ConvocatoriaProyecto.objects.filter(status=True, visible=True).order_by('-apertura', '-cierre')
            # convocatorias = ConvocatoriaProyecto.objects.filter(status=True).order_by('-apertura', '-cierre')

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
            data['enlaceatras'] = "/pro_investigacion?action=convocatorias"

            return render(request, "pro_proyectoinvestigacion/convocatoriaproyecto.html", data)


def convocatoria_vigente():
    fechaactual = datetime.now().date()
    if ConvocatoriaProyecto.objects.filter(status=True, vigente=True, apertura__lte=fechaactual, cierre__gte=fechaactual).exists():
        convocatoria = ConvocatoriaProyecto.objects.get(status=True, vigente=True, apertura__lte=fechaactual, cierre__gte=fechaactual)
    else:
        convocatoria = None

    return convocatoria
