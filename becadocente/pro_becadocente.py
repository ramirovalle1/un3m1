# -*- coding: UTF-8 -*-
import io
import json
import os
import statistics
from datetime import datetime

import PyPDF2
import pyqrcode
import code128
from core.firmar_documentos_ec import JavaFirmaEc
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q, Sum, Avg
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from fitz import fitz
from xlwt import easyxf, XFStyle, Workbook
from django.core.files import File as DjangoFile
import random
import shutil
import math

from becadocente.models import Convocatoria, TIPO_ESTUDIO, TIPO_PERMISO, TIPO_LICENCIA, Solicitud, SolicitudRequisito, RecorridoRegistro, SolicitudPresupuesto, SolicitudPresupuestoRubro, SolicitudPresupuestoRubroDetalle, SolicitudDocumento, Documento, DocumentoConvocatoria, Requisito, \
    InformeFactibilidad, ResolucionComite
from core.firmar_documentos import firmar
from investigacion.funciones import nombre_archivo_cedula, nombre_archivo_papeleta_votacion, analista_investigacion, diff_month, secuencia_solicitud_beca, coordinador_investigacion, vicerrector_investigacion_posgrado, salto_linea_nombre_firma_encontrado, secretaria_comite_becas
from sagest.commonviews import obtener_estado_solicitud
from sagest.models import Departamento
from settings import SITE_STORAGE, DEBUG
from sga.funcionesxhtml2pdf import convert_html_to_pdf
from sga.models import RespuestaEvaluacionAcreditacion, ProcesoEvaluativoAcreditacion, RubricaPreguntas, ResumenFinalEvaluacionAcreditacion, InstitucionEducacionSuperior, Pais, Modalidad, LineaInvestigacion, CUENTAS_CORREOS, MESES_CHOICES, FirmaPersona, PersonaDocumentoPersonal
from sagest.models import DistributivoPersona
from decorators import secure_module
from sga.commonviews import adduserdata
from django.template import Context
from django.template.loader import get_template

from sga.funciones import MiPaginador, null_to_decimal, validar_archivo, generar_nombre, log, cuenta_email_disponible_para_envio, variable_valor, moneda_a_letras
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    data['profesor'] = profesor = persona.profesor()

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'subirdocumentopersonal':
            try:
                if 'id' not in request.POST or 'idc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                if 'archivocedula' in request.FILES:
                    archivo = request.FILES['archivocedula']
                    descripcionarchivo = 'Archivo de la cédula de ciudadanía'

                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocertificado' in request.FILES:
                    archivo = request.FILES['archivocertificado']
                    descripcionarchivo = 'Archivo del certificado de votación'

                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Obtengo los documentos personales
                documentos = persona.documentos_personales()

                # Si no tiene documentos se crea, sino se actualiza
                if not documentos:
                    archivocedula = request.FILES['archivocedula']
                    archivocertificado = request.FILES['archivocertificado']

                    archivocedula._name = generar_nombre("cedula", archivocedula._name)
                    archivocertificado._name = generar_nombre("papeleta", archivocertificado._name)

                    documentos = PersonaDocumentoPersonal(
                        persona=persona,
                        cedula=archivocedula,
                        estadocedula=1,
                        papeleta=archivocertificado,
                        estadopapeleta=1
                    )
                else:
                    if 'archivocedula' in request.FILES:
                        archivocedula = request.FILES['archivocedula']
                        archivocedula._name = generar_nombre("cedula", archivocedula._name)
                        documentos.cedula = archivocedula
                        documentos.estadocedula = 1

                    if 'archivocertificado' in request.FILES:
                        archivocertificado = request.FILES['archivocertificado']
                        archivocertificado._name = generar_nombre("papeleta", archivocertificado._name)
                        documentos.papeleta = archivocertificado
                        documentos.estadopapeleta = 1

                documentos.save(request)

                log(u'%s actualizó sus documentos personales' % (persona), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True, "idc": request.POST['idc']})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addpostulacion':
            try:
                if 'idc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.POST['idc'])))

                # Validar que no esté repetida la solicitud
                if not Solicitud.objects.values("id").filter(convocatoria=convocatoria, profesor=profesor, status=True).exists():
                    # Validar que la fecha de fin de estudios sea mayor a la fecha de inicio de estudios
                    inicio = datetime.strptime(request.POST['inicio'], '%Y-%m-%d').date()
                    fin = datetime.strptime(request.POST['fin'], '%Y-%m-%d').date()

                    if fin <= inicio:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de estudios debe ser mayor a la fecha de inicio de estudios", "showSwal": "True", "swalType": "warning"})

                    # Obtiene la ruta del archivo de certificado de evaluación docente, cédula y papaleta de votación
                    certificadoedocente = request.POST['archivoevaldoc']

                    # Obtiene los valores de los arreglos del detalle de requisitos
                    idrequisitos = request.POST.getlist('idrequisito[]')  # IDs de los requisitos
                    numerorequisitos = request.POST.getlist('numerorequisito[]')  # Número de los requisitos
                    nfilas_ca_evi = json.loads(request.POST['lista_items1'])  # Números de filas que tienen lleno el campo archivo
                    nfilas_evi = request.POST.getlist('nfila_evidencia[]')  # Todos los número de filas del detalle de requisitos
                    archivos_evi = request.FILES.getlist('archivo_evidencia[]')  # Todos los archivos

                    # Valido los archivos cargados de detalle de requisitos
                    for nfila, archivo in zip(nfilas_ca_evi, archivos_evi):
                        descripcionarchivo = 'Archivo de requisito'
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"] + " para el requisito # " + str(nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                    # Obtengo estado SOLICITADO
                    estado = obtener_estado_solicitud(13, 1)

                    fechaactual = datetime.now().date()

                    # Guardo la solicitud
                    solicitud = Solicitud(
                        convocatoria=convocatoria,
                        profesor=profesor,
                        tipoestudio=request.POST['tipoestudio'],
                        programa=request.POST['programa'].strip(),
                        tituloobtener=request.POST['tituloobtener'].strip(),
                        institucion_id=request.POST['institucion'],
                        pais_id=request.POST['pais'],
                        provincia_id=request.POST['provincia'],
                        canton_id=request.POST['canton'],
                        parroquia_id=None,
                        inicio=inicio,
                        fin=fin,
                        modalidad_id=request.POST['modalidad'],
                        tienetematitulacion=True if 'tienetematitulacion' in request.POST else False,
                        tematitulacion=request.POST['tematitulacion'].strip() if 'tienetematitulacion' in request.POST else '',
                        lineainvestigacion_id=request.POST['lineainvestigacion'] if 'tienetematitulacion' in request.POST else None,
                        ausentismo=True if 'ausentismo' in request.POST else False,
                        tipopermiso=request.POST['tipopermiso'] if 'ausentismo' in request.POST else None,
                        tiempomes=request.POST['tiempomes'] if 'ausentismo' in request.POST else 0,
                        tipolicencia=request.POST['tipolicencia'] if 'ausentismo' in request.POST else None,
                        imparteclase=True if 'imparteclase' in request.POST else False,
                        presupuesto=0,
                        criteriojuridico=False,
                        observacion='',
                        estado=estado
                    )
                    solicitud.save(request)

                    # Rutas origen y destino dónde se va a guardar el certificado de evaluación que fue generado
                    if certificadoedocente:
                        nombrearchivoeval = certificadoedocente.split("/")[-1]
                        rutaarchivobase = "becadocente/requisito/" + str(fechaactual.year) + "/" + str(fechaactual.month).zfill(2) + "/" + str(fechaactual.day).zfill(2) + "/" + nombrearchivoeval
                        rutaorigenevaluacion = SITE_STORAGE + "/" + certificadoedocente
                        rutadestinoevaluacion = SITE_STORAGE + '/media/' + rutaarchivobase

                    # Guardo los requisitos y evidencias de la solicitud
                    for nfila, idrequisito in zip(nfilas_evi, idrequisitos):
                        requisto_id = int(idrequisito)
                        solicitudrequisito = SolicitudRequisito(
                            solicitud=solicitud,
                            requisito_id=requisto_id,
                            estado=6
                        )
                        solicitudrequisito.save(request)

                        # Si el id de requisito es 1, debo crear el 2 de manera automática
                        if requisto_id == 1:
                            # Creo el detalle con el requisito ID 2
                            solicitudrequisito2 = SolicitudRequisito(
                                solicitud=solicitud,
                                requisito_id=2,
                                estado=6
                            )
                            solicitudrequisito2.save(request)

                        if requisto_id == 1:
                            nombrearchivo = "certificadoth"
                        elif requisto_id == 3:
                            nombrearchivo = "cedula"
                        elif requisto_id == 4:
                            nombrearchivo = "papeleta"
                        elif requisto_id == 5:
                            nombrearchivo = "cartaaceptacion"
                        elif requisto_id == 6:
                            nombrearchivo = "programaestudio"
                        elif requisto_id == 7:
                            nombrearchivo = "acreditacionuni"
                        elif requisto_id == 8:
                            nombrearchivo = "declaracionnodeuda"
                        elif requisto_id == 9:
                            nombrearchivo = "declaracionnofinanc"

                        # Guardo el archivo del requisito
                        for nfilaarchi, archivo in zip(nfilas_ca_evi, archivos_evi):
                            # Si la fila del requisito a la fila que contiene archivo
                            if int(nfilaarchi['nfila']) == int(nfila):
                                # actualizo campo archivo del registro creado

                                pdf2ReaderEvi = PyPDF2.PdfFileReader(archivo)

                                archivoreg = archivo
                                archivoreg._name = generar_nombre(nombrearchivo, archivoreg._name)
                                solicitudrequisito.archivo = archivoreg
                                solicitudrequisito.estado = 1
                                solicitudrequisito.numeropagina = pdf2ReaderEvi.numPages
                                solicitudrequisito.save(request)
                                break

                    # Muevo el archivo generado a la ruta donde se almacenan las evidencias de requisitos
                    if certificadoedocente:
                        shutil.move(rutaorigenevaluacion, rutadestinoevaluacion)

                        # Guardo el archivo de la evaluación docente
                        requisitoevaluacion = SolicitudRequisito.objects.get(solicitud=solicitud, requisito_id=2, status=True)

                        pdf2ReaderEvi = PyPDF2.PdfFileReader(rutadestinoevaluacion)

                        requisitoevaluacion.archivo = rutaarchivobase
                        requisitoevaluacion.estado = 1
                        requisitoevaluacion.numeropagina = pdf2ReaderEvi.numPages
                        requisitoevaluacion.save(request)

                    # En caso de que la cédula y papeleta ya existan en hoja de vida, se debe crear ese detalle de requisito y copiar el archivo
                    # Obtengo los documentos personales
                    documentos = persona.documentos_personales()
                    if documentos:
                        if documentos.cedula:
                            # Creo el detalle con el requisito ID 3
                            archivodocumento = ContentFile(documentos.cedula.file.read())

                            pdf2ReaderEvi = PyPDF2.PdfFileReader(archivodocumento)

                            archivodocumento.name = generar_nombre("cedula", nombre_archivo_cedula(documentos))

                            solicitudrequisito = SolicitudRequisito(
                                solicitud=solicitud,
                                requisito_id=3,
                                archivo=archivodocumento,
                                numeropagina=pdf2ReaderEvi.numPages,
                                estado=1
                            )
                            solicitudrequisito.save(request)

                        if documentos.papeleta:
                            # Creo el detalle con el requisito ID 4
                            archivodocumento = ContentFile(documentos.papeleta.file.read())

                            pdf2ReaderEvi = PyPDF2.PdfFileReader(archivodocumento)

                            archivodocumento.name = generar_nombre("papeleta", nombre_archivo_papeleta_votacion(documentos))

                            solicitudrequisito = SolicitudRequisito(
                                solicitud=solicitud,
                                requisito_id=4,
                                archivo=archivodocumento,
                                numeropagina=pdf2ReaderEvi.numPages,
                                estado=1
                            )
                            solicitudrequisito.save(request)

                    # Guardo el recorrido de la solicitud
                    recorrido = RecorridoRegistro(
                        tiporegistro=2,
                        registroid=solicitud.id,
                        fecha=datetime.now().date(),
                        departamento=persona.mi_cargo_actual().unidadorganica,
                        persona=persona,
                        observacion='SOLICITUD EN EDICIÓN',
                        estado=estado
                    )
                    recorrido.save(request)

                    log(u'%s agregó postulación de becas para docentes: %s' % (persona, solicitud), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La postulación a beca para el docente ya ha sido ingresada", "showSwal": "True", "swalType": "warning"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editpostulacion':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                postulacion = Solicitud.objects.get(pk=int(encrypt(request.POST['id'])))

                # Validar que la fecha de fin de estudios sea mayor a la fecha de inicio de estudios
                inicio = datetime.strptime(request.POST['inicio'], '%Y-%m-%d').date()
                fin = datetime.strptime(request.POST['fin'], '%Y-%m-%d').date()

                if fin <= inicio:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de estudios debe ser mayor a la fecha de inicio de estudios", "showSwal": "True", "swalType": "warning"})

                # Obtiene los valores de los arreglos del detalle de requisitos
                iddetalles = request.POST.getlist('iddetalle[]')  # IDs de los detalles
                numerorequisitos = request.POST.getlist('numerorequisito[]')  # Número de los requisitos
                nfilas_ca_evi = json.loads(request.POST['lista_items1'])  # Números de filas que tienen lleno el campo archivo
                nfilas_evi = request.POST.getlist('nfila_evidencia[]')  # Todos los número de filas del detalle de requisitos
                archivos_evi = request.FILES.getlist('archivo_evidencia[]')  # Todos los archivos

                # Valido los archivos cargados de detalle de requisitos
                for nfila, archivo in zip(nfilas_ca_evi, archivos_evi):
                    descripcionarchivo = 'Archivo de requisito'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"] + " para el requisito # " + str(nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                iniciooriginal = postulacion.inicio
                finoriginal = postulacion.fin

                # Si tiene estado P. NOVEDADES se debe actualizar el estado de al postulación y guardar recorrido
                actualizaestado = postulacion.estado.valor == 4

                # Actualiza la solicitud
                postulacion.tipoestudio = request.POST['tipoestudio']
                postulacion.programa = request.POST['programa'].strip()
                postulacion.tituloobtener = request.POST['tituloobtener'].strip()
                postulacion.institucion_id = request.POST['institucion']
                postulacion.pais_id = request.POST['pais']
                postulacion.provincia_id = request.POST['provincia']
                postulacion.canton_id = request.POST['canton']
                postulacion.parroquia_id = None
                postulacion.inicio = inicio
                postulacion.fin = fin
                postulacion.modalidad_id = request.POST['modalidad']
                postulacion.tienetematitulacion = True if 'tienetematitulacion' in request.POST else False
                postulacion.tematitulacion = request.POST['tematitulacion'].strip() if 'tienetematitulacion' in request.POST else ''
                postulacion.lineainvestigacion_id = request.POST['lineainvestigacion'] if 'tienetematitulacion' in request.POST else None
                postulacion.ausentismo = True if 'ausentismo' in request.POST else False
                postulacion.tipopermiso = request.POST['tipopermiso'] if 'ausentismo' in request.POST else None
                postulacion.tiempomes = request.POST['tiempomes'] if 'ausentismo' in request.POST else 0
                postulacion.tipolicencia = request.POST['tipolicencia'] if 'ausentismo' in request.POST else None
                postulacion.imparteclase = True if 'imparteclase' in request.POST else False
                postulacion.observacion = ''
                postulacion.fechasolicitud = None
                postulacion.validada = False
                postulacion.estadovalidacion = None
                postulacion.save(request)

                # Actualizo los requisitos y evidencias de la solicitud que hayan sido cargadas
                for nfila, archivo in zip(nfilas_ca_evi, archivos_evi):
                    numerorequisito = int(nfila['nfila'])

                    if numerorequisito == 1:
                        nombrearchivo = "certificadoth"
                    elif numerorequisito == 2:
                        nombrearchivo = "evaluaciondoc"
                    elif numerorequisito == 3:
                        nombrearchivo = "cedula"
                    elif numerorequisito == 4:
                        nombrearchivo = "papeleta"
                    elif numerorequisito == 5:
                        nombrearchivo = "cartaaceptacion"
                    elif numerorequisito == 6:
                        nombrearchivo = "programaestudio"
                    elif numerorequisito == 7:
                        nombrearchivo = "acreditacionuni"
                    elif numerorequisito == 8:
                        nombrearchivo = "declaracionnodeuda"
                    elif numerorequisito == 9:
                        nombrearchivo = "declaracionnofinanc"

                    archivoreg = archivo
                    archivoreg._name = generar_nombre(nombrearchivo, archivoreg._name)

                    # Si el número de requisito no es 5 ( carta de aceptación)
                    if numerorequisito != 5:
                        # Consulto detalle
                        detallerequisito = SolicitudRequisito.objects.get(solicitud=postulacion, requisito__numero=numerorequisito, status=True)

                        # Actualizo detalle
                        pdf2ReaderEvi = PyPDF2.PdfFileReader(archivo)

                        detallerequisito.archivo = archivoreg
                        detallerequisito.numeropagina = pdf2ReaderEvi.numPages
                        detallerequisito.personarevisa = None
                        detallerequisito.fecharevisa = None
                        detallerequisito.observacion = ''
                        detallerequisito.estado = 1
                        detallerequisito.save(request)
                    else:
                        # Consulto si no existe el detalle del requisito # 5
                        if not SolicitudRequisito.objects.values("id").filter(solicitud=postulacion, requisito__numero=numerorequisito, status=True).exists():
                            # Consulto requisito # 5
                            requisito = Requisito.objects.get(status=True, numero=5, vigente=True)

                            # Guardo del detalle con el requisito # 5
                            detallerequisito = SolicitudRequisito(
                                solicitud=postulacion,
                                requisito=requisito,
                                archivo=archivoreg,
                                numeropagina=pdf2ReaderEvi.numPages,
                                estado=1
                            )
                        else:
                            detallerequisito = SolicitudRequisito.objects.get(solicitud=postulacion, requisito__numero=numerorequisito, status=True)
                            # Actualizo detalle
                            pdf2ReaderEvi = PyPDF2.PdfFileReader(archivo)

                            detallerequisito.archivo = archivoreg
                            detallerequisito.numeropagina = pdf2ReaderEvi.numPages
                            detallerequisito.personarevisa = None
                            detallerequisito.fecharevisa = None
                            detallerequisito.observacion = ''
                            detallerequisito.estado = 1

                        detallerequisito.save(request)

                # Si las fechas inicio y fin originales son diferentes a las nuevas
                if inicio != iniciooriginal or fin != finoriginal:
                    # Si tiene presupuesto registrado
                    if postulacion.tiene_presupuesto():
                        presupuesto = postulacion.presupuesto_solicitud()
                        periodospresupuesto = presupuesto.numeroperiodo

                        # obtener cantidad de periodos
                        cantidadperiodos = (postulacion.fin.year - postulacion.inicio.year) + 1
                        difanios = inicio.year - iniciooriginal.year

                        if cantidadperiodos == periodospresupuesto:
                            if difanios != 0:
                                # Actualizar años del detalle de presupuesto
                                detallesrubros = presupuesto.detalle_presupuesto_rubros()
                                for detalle in detallesrubros:
                                    detalle.anio += difanios
                                    detalle.save(request)

                        elif cantidadperiodos < periodospresupuesto:
                            # Eliminar los detalles de los periodos sobrantes
                            for periodo in range(periodospresupuesto, cantidadperiodos, -1):
                                detallesrubros = presupuesto.detalle_presupuesto_rubros_periodo(periodo)
                                for detalle in detallesrubros:
                                    detalle.status = False
                                    detalle.save(request)

                            if difanios != 0:
                                # Actualizar años del detalle de presupuesto
                                detallesrubros = presupuesto.detalle_presupuesto_rubros()
                                for detalle in detallesrubros:
                                    detalle.anio += difanios
                                    detalle.save(request)

                            # Actualizar el total del presupuesto en tabla de presupuesto
                            totalpresupuesto = presupuesto.total_general()
                            presupuesto.numeroperiodo = cantidadperiodos
                            presupuesto.total = totalpresupuesto
                            presupuesto.save(request)

                            # Actualizar el total del presupuesto tabla de postulación
                            postulacion.presupuesto = totalpresupuesto
                            postulacion.save(request)
                        else:
                            # Agregar los detalles de los periodos faltantes
                            anio = finoriginal.year + 1
                            for periodo in range(periodospresupuesto + 1, cantidadperiodos + 1):
                                presupuestorubros = presupuesto.rubros()
                                for presupuestorubro in presupuestorubros:
                                    detallerubro = SolicitudPresupuestoRubroDetalle(
                                        presupuestorubro=presupuestorubro,
                                        periodo=periodo,
                                        anio=anio,
                                        valorunitario=presupuestorubro.valorunitario,
                                        cantidad=0,
                                        subtotal=0
                                    )
                                    detallerubro.save(request)

                                anio += 1

                            if difanios != 0:
                                # Actualizar años del detalle de presupuesto
                                detallesrubros = presupuesto.detalle_presupuesto_rubros()
                                for detalle in detallesrubros:
                                    detalle.anio += difanios
                                    detalle.save(request)

                            # Actualizar el total de periodos en tabla de presupuesto
                            presupuesto.numeroperiodo = cantidadperiodos
                            presupuesto.save(request)

                # Se debe actualizar el estado de al postulación y guardar recorrido en caso que tenga estado NOVEDADES
                if actualizaestado:
                    # Obtengo estado EN EDICIÓN
                    estado = obtener_estado_solicitud(13, 1)
                    postulacion.estado = estado

                    postulacion.save(request)

                    # Guardo el recorrido de la solicitud
                    recorrido = RecorridoRegistro(
                        tiporegistro=2,
                        registroid=postulacion.id,
                        fecha=datetime.now().date(),
                        departamento=persona.mi_cargo_actual().unidadorganica,
                        persona=persona,
                        observacion='SOLICITUD EN EDICIÓN',
                        estado=estado
                    )
                    recorrido.save(request)

                # Consulto el documento solicitud de beca
                documentos = postulacion.documentos()
                if documentos:
                    documento = documentos.filter(documento__tipo=1)[0]

                    # Actualizo los campos del documento solicitud de beca
                    documento.archivo = None
                    documento.archivofirmado = None
                    documento.numeropagina = 0
                    documento.personarevisa = None
                    documento.fecharevisa = None
                    documento.observacion = ''
                    documento.estado = 6
                    documento.save(request)

                log(u'%s editó postulación de becas para docentes: %s' % (persona, postulacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addpresupuesto':
            try:
                if 'ids' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la postulación
                solicitud = Solicitud.objects.get(pk=int(encrypt(request.POST['ids'])))
                anioinicio = solicitud.inicio.year

                # Obtengo los valores de los campos del formulario
                numeroperiodo = request.POST['numero_periodo']
                total = request.POST['total_general']

                # Obtiene los valores de los arreglos
                idrubros = request.POST.getlist('idrubro[]')  # IDs de los rubros
                tiposrubros = request.POST.getlist('tiporubro[]')  # Tipos de rubros
                valoresrubros = request.POST.getlist('valorrubro[]')  # Valores unitarios de los rubros
                matcantidades = request.POST.getlist('mat_cantidad[]')  # Cantidades rubro matricula
                matsubtotales = request.POST.getlist('mat_subtotal[]')  # Subtotales rubro matricula
                psjcantidades = request.POST.getlist('psj_cantidad[]')  # Cantidades rubro pasaje
                psjsubtotales = request.POST.getlist('psj_subtotal[]')  # Subtotales rubro pasaje
                pubcantidades = request.POST.getlist('pub_cantidad[]')  # Cantidades rubro gastos por publicacion
                pubsubtotales = request.POST.getlist('pub_subtotal[]')  # Subtotales rubro gastos por publicacion
                segcantidades = request.POST.getlist('seg_cantidad[]')  # Cantidades rubro seguro de salud
                segsubtotales = request.POST.getlist('seg_subtotal[]')  # Subtotales rubro seguro de salud
                impcantidades = request.POST.getlist('imp_cantidad[]')  # Cantidades rubro impresión
                impsubtotales = request.POST.getlist('imp_subtotal[]')  # Subtotales rubro impresión
                mbicantidades = request.POST.getlist('mbi_cantidad[]')  # Cantidades rubro material biblio.
                mbisubtotales = request.POST.getlist('mbi_subtotal[]')  # Subtotales rubro material biblio.
                mancantidades = request.POST.getlist('man_cantidad[]')  # Cantidades rubro manuntención
                mansubtotales = request.POST.getlist('man_subtotal[]')  # Subtotales rubro manuntención

                # Actualizo el campo presupuesto en la solicitud
                solicitud.presupuesto = total
                solicitud.save(request)

                # Guardo presupuesto de la postulación
                solicitudpresupuesto = SolicitudPresupuesto(
                    solicitud=solicitud,
                    numeroperiodo=numeroperiodo,
                    total=total
                )
                solicitudpresupuesto.save(request)

                # Guardo los rubros del presupuesto
                for rubroid, tipo, valorunitario in zip(idrubros, tiposrubros, valoresrubros):
                    presupuestorubro = SolicitudPresupuestoRubro(
                        solicitudpresupuesto=solicitudpresupuesto,
                        rubro_id=rubroid,
                        valorunitario=valorunitario
                    )
                    presupuestorubro.save(request)

                    # Guardo el detalle de los rubros del presupuesto
                    anio = anioinicio
                    periodo = 1

                    if tipo == '1':  # Matrícula, colegiatura y derechos de grado
                        for cantidad, subtotal in zip(matcantidades, matsubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle(
                                presupuestorubro=presupuestorubro,
                                periodo=periodo,
                                anio=anio,
                                valorunitario=valorunitario,
                                cantidad=cantidad,
                                subtotal=subtotal
                            )
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1
                    elif tipo == '2':  # Pasaje ida y retorno
                        for cantidad, subtotal in zip(psjcantidades, psjsubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle(
                                presupuestorubro=presupuestorubro,
                                periodo=periodo,
                                anio=anio,
                                valorunitario=valorunitario,
                                cantidad=cantidad,
                                subtotal=subtotal
                            )
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1
                    elif tipo == '3':  # Gastos por publicación de artículos científicos (Q1 o Q2)
                        for cantidad, subtotal in zip(pubcantidades, pubsubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle(
                                presupuestorubro=presupuestorubro,
                                periodo=periodo,
                                anio=anio,
                                valorunitario=valorunitario,
                                cantidad=cantidad,
                                subtotal=subtotal
                            )
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1
                    elif tipo == '4':  # Seguro de salud y de vida
                        for cantidad, subtotal in zip(segcantidades, segsubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle(
                                presupuestorubro=presupuestorubro,
                                periodo=periodo,
                                anio=anio,
                                valorunitario=valorunitario,
                                cantidad=cantidad,
                                subtotal=subtotal
                            )
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1
                    elif tipo == '5':  # Impresión de tesis
                        for cantidad, subtotal in zip(impcantidades, impsubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle(
                                presupuestorubro=presupuestorubro,
                                periodo=periodo,
                                anio=anio,
                                valorunitario=valorunitario,
                                cantidad=cantidad,
                                subtotal=subtotal
                            )
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1
                    elif tipo == '6':  # Material bibliográfico
                        for cantidad, subtotal in zip(mbicantidades, mbisubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle(
                                presupuestorubro=presupuestorubro,
                                periodo=periodo,
                                anio=anio,
                                valorunitario=valorunitario,
                                cantidad=cantidad,
                                subtotal=subtotal
                            )
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1
                    else:  # Manutención: Alimentación, hospedaje y transporte interno
                        for cantidad, subtotal in zip(mancantidades, mansubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle(
                                presupuestorubro=presupuestorubro,
                                periodo=periodo,
                                anio=anio,
                                valorunitario=valorunitario,
                                cantidad=cantidad,
                                subtotal=subtotal
                            )
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1

                log(u'%s agregó presupuesto a postulación de becas para docentes: %s' % (persona, solicitud), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editpresupuesto':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la postulación
                postulacion = Solicitud.objects.get(pk=int(encrypt(request.POST['id'])))

                # Si tiene estado P. NOVEDADES se debe actualizar el estado de al postulación y guardar recorrido
                actualizaestado = postulacion.estado.valor == 4

                anioinicio = postulacion.inicio.year

                # Obtengo los valores de los campos del formulario
                numeroperiodo = request.POST['numero_periodo']
                total = request.POST['total_general']

                # Obtiene los valores de los arreglos
                idrubros = request.POST.getlist('idrubro[]')  # IDs de los rubros
                tiposrubros = request.POST.getlist('tiporubro[]')  # Tipos de rubros
                valoresrubros = request.POST.getlist('valorrubro[]')  # Valores unitarios de los rubros
                matcantidades = request.POST.getlist('mat_cantidad[]')  # Cantidades rubro matricula
                matsubtotales = request.POST.getlist('mat_subtotal[]')  # Subtotales rubro matricula
                psjcantidades = request.POST.getlist('psj_cantidad[]')  # Cantidades rubro pasaje
                psjsubtotales = request.POST.getlist('psj_subtotal[]')  # Subtotales rubro pasaje
                pubcantidades = request.POST.getlist('pub_cantidad[]')  # Cantidades rubro gastos por publicacion
                pubsubtotales = request.POST.getlist('pub_subtotal[]')  # Subtotales rubro gastos por publicacion
                segcantidades = request.POST.getlist('seg_cantidad[]')  # Cantidades rubro seguro de salud
                segsubtotales = request.POST.getlist('seg_subtotal[]')  # Subtotales rubro seguro de salud
                impcantidades = request.POST.getlist('imp_cantidad[]')  # Cantidades rubro impresión
                impsubtotales = request.POST.getlist('imp_subtotal[]')  # Subtotales rubro impresión
                mbicantidades = request.POST.getlist('mbi_cantidad[]')  # Cantidades rubro material biblio.
                mbisubtotales = request.POST.getlist('mbi_subtotal[]')  # Subtotales rubro material biblio.
                mancantidades = request.POST.getlist('man_cantidad[]')  # Cantidades rubro manuntención
                mansubtotales = request.POST.getlist('man_subtotal[]')  # Subtotales rubro manuntención

                # Actualizo el campo presupuesto en la solicitud
                postulacion.validada = False
                postulacion.estadovalidacion = None
                postulacion.fechasolicitud = None
                postulacion.presupuesto = total
                postulacion.save(request)

                # Actualizo presupuesto de la postulación
                solicitudpresupuesto = SolicitudPresupuesto.objects.get(solicitud=postulacion, status=True)
                solicitudpresupuesto.total = total
                solicitudpresupuesto.save(request)

                # Actualizo los rubros del presupuesto
                for rubroid, tipo, valorunitario in zip(idrubros, tiposrubros, valoresrubros):
                    presupuestorubro = SolicitudPresupuestoRubro.objects.get(solicitudpresupuesto=solicitudpresupuesto, rubro_id=rubroid, status=True)
                    presupuestorubro.valorunitario = valorunitario
                    presupuestorubro.save(request)

                    # Actualizo el detalle de los rubros del presupuesto
                    anio = anioinicio
                    periodo = 1

                    if tipo == '1':  # Matrícula, colegiatura y derechos de grado
                        for cantidad, subtotal in zip(matcantidades, matsubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle.objects.get(presupuestorubro=presupuestorubro, periodo=periodo, anio=anio, status=True)
                            detallerubro.valorunitario = valorunitario
                            detallerubro.cantidad = cantidad
                            detallerubro.subtotal = subtotal
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1
                    elif tipo == '2':  # Pasaje ida y retorno
                        for cantidad, subtotal in zip(psjcantidades, psjsubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle.objects.get(presupuestorubro=presupuestorubro, periodo=periodo, anio=anio, status=True)
                            detallerubro.valorunitario = valorunitario
                            detallerubro.cantidad = cantidad
                            detallerubro.subtotal = subtotal
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1
                    elif tipo == '3':  # Gastos por publicación de artículos científicos (Q1 o Q2)
                        for cantidad, subtotal in zip(pubcantidades, pubsubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle.objects.get(presupuestorubro=presupuestorubro, periodo=periodo, anio=anio, status=True)
                            detallerubro.valorunitario = valorunitario
                            detallerubro.cantidad = cantidad
                            detallerubro.subtotal = subtotal
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1
                    elif tipo == '4':  # Seguro de salud y de vida
                        for cantidad, subtotal in zip(segcantidades, segsubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle.objects.get(presupuestorubro=presupuestorubro, periodo=periodo, anio=anio, status=True)
                            detallerubro.valorunitario = valorunitario
                            detallerubro.cantidad = cantidad
                            detallerubro.subtotal = subtotal
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1
                    elif tipo == '5':  # Impresión de tesis
                        for cantidad, subtotal in zip(impcantidades, impsubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle.objects.get(presupuestorubro=presupuestorubro, periodo=periodo, anio=anio, status=True)
                            detallerubro.valorunitario = valorunitario
                            detallerubro.cantidad = cantidad
                            detallerubro.subtotal = subtotal
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1
                    elif tipo == '6':  # Material bibliográfico
                        for cantidad, subtotal in zip(mbicantidades, mbisubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle.objects.get(presupuestorubro=presupuestorubro, periodo=periodo, anio=anio, status=True)
                            detallerubro.valorunitario = valorunitario
                            detallerubro.cantidad = cantidad
                            detallerubro.subtotal = subtotal
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1
                    else:  # Manutención: Alimentación, hospedaje y transporte interno
                        for cantidad, subtotal in zip(mancantidades, mansubtotales):
                            detallerubro = SolicitudPresupuestoRubroDetalle.objects.get(presupuestorubro=presupuestorubro, periodo=periodo, anio=anio, status=True)
                            detallerubro.valorunitario = valorunitario
                            detallerubro.cantidad = cantidad
                            detallerubro.subtotal = subtotal
                            detallerubro.save(request)
                            anio += 1
                            periodo += 1

                # Se debe actualizar el estado de al postulación y guardar recorrido en caso que tenga estado NOVEDADES
                if actualizaestado:
                    # Obtengo estado EN EDICIÓN
                    estado = obtener_estado_solicitud(13, 1)
                    postulacion.estado = estado

                    postulacion.save(request)

                    # Guardo el recorrido de la solicitud
                    recorrido = RecorridoRegistro(
                        tiporegistro=2,
                        registroid=postulacion.id,
                        fecha=datetime.now().date(),
                        departamento=persona.mi_cargo_actual().unidadorganica,
                        persona=persona,
                        observacion='SOLICITUD EN EDICIÓN',
                        estado=estado
                    )
                    recorrido.save(request)

                # Consulto el documento solicitud de beca
                documentos = postulacion.documentos()
                if documentos:
                    documento = documentos.filter(documento__tipo=1)[0]

                    # Actualizo los campos del documento solicitud de beca
                    documento.archivo = None
                    documento.archivofirmado = None
                    documento.numeropagina = 0
                    documento.personarevisa = None
                    documento.fecharevisa = None
                    documento.observacion = ''
                    documento.estado = 6
                    documento.save(request)

                log(u'%s editó presupuesto a postulación de becas para docentes: %s' % (persona, postulacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'solicitudbecapdf':
            try:
                data = {}

                # Consulto la solicitud de beca
                solicitud = Solicitud.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que el tipo de documento SOLICITUD DE BECA esté asignado a la convocatoria
                if not DocumentoConvocatoria.objects.filter(status=True, convocatoria=solicitud.convocatoria, documento__tipo=1).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"El documento [Solicitud de Beca] no está asignado a la convocatoria"})

                # Si no tiene fecha de solicitud actualizo ese campo
                if not solicitud.fechasolicitud:
                    solicitud.fechasolicitud = datetime.now()

                # Si no tiene número de solicitud actualizo ese campo
                if not solicitud.numero:
                    numero = secuencia_solicitud_beca(solicitud.convocatoria)
                    solicitud.numero = numero

                solicitud.save(request)

                data['solicitud'] = solicitud
                data['fechasolicitud'] = str(solicitud.fechasolicitud.day) + " de " + MESES_CHOICES[solicitud.fechasolicitud.month - 1][1].capitalize() + " del " + str(solicitud.fechasolicitud.year)
                data['inicioestudio'] = str(solicitud.inicio.day) + " de " + MESES_CHOICES[solicitud.inicio.month - 1][1].capitalize() + " del " + str(solicitud.inicio.year)
                data['finestudio'] = str(solicitud.fin.day) + " de " + MESES_CHOICES[solicitud.fin.month - 1][1].capitalize() + " del " + str(solicitud.fin.year)

                mesesestudio = diff_month(solicitud.inicio, solicitud.fin)
                anios = math.trunc(mesesestudio / 12)
                meses = mesesestudio - (anios * 12)

                if anios > 0 and meses > 0:
                    if anios > 1:
                        if meses > 1:
                            textoduracionestudio = "los " + str(anios) + " años y " + str(meses) + " meses"
                        else:
                            textoduracionestudio = "los " + str(anios) + " años y " + str(meses) + " mes"
                    else:
                        if meses > 1:
                            textoduracionestudio = "el " + str(anios) + " año y " + str(meses) + " meses"
                        else:
                            textoduracionestudio = "el" + str(anios) + " año y " + str(meses) + " mes"
                elif anios > 0 and meses == 0:
                    if anios > 1:
                        textoduracionestudio = "los " + str(anios) + " años"
                    else:
                        textoduracionestudio = "el " + str(anios) + "año"
                else:
                    textoduracionestudio = "los " + str(meses) + " meses"

                data['textoduracionestudio'] = textoduracionestudio

                # Creacion del archivo
                directorio = SITE_STORAGE + '/media/certificadoedocente'
                try:
                    os.stat(directorio)
                except:
                    os.mkdir(directorio)

                # Archivo de la solicitud de beca
                nombrearchivo = generar_nombre('solicitudbeca', 'solicitudbeca.pdf')

                valida = convert_html_to_pdf(
                    'pro_becadocente/solicitudbecapdf.html',
                    {'pagesize': 'A4', 'data': data},
                    nombrearchivo,
                    directorio
                )

                if not valida:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el documento de la solicitud de beca.", "showSwal": "True", "swalType": "error"})

                # archivo = 'media/certificadoedocente/' + nombrearchivo
                archivo = SITE_STORAGE + '/media/certificadoedocente/' + nombrearchivo

                # Aperturo el archivo generado
                with open(archivo, 'rb') as f:
                    data = f.read()

                buffer = io.BytesIO()
                buffer.write(data)
                pdfcopia = buffer.getvalue()
                buffer.seek(0)
                buffer.close()

                # Extraigo el contenido
                archivocopiado = ContentFile(pdfcopia)
                archivocopiado.name = nombrearchivo

                # Guardo o actualizo el archivo de la solicitud
                if not solicitud.solicituddocumento_set.values("id").filter(status=True, documento__tipo=1).exists():
                    # Consulto el tipo de documento
                    documento = Documento.objects.get(tipo=1)

                    # Guardo el documento de la solicitud
                    solicituddocumento = SolicitudDocumento(
                        solicitud=solicitud,
                        documento=documento,
                        archivo=archivocopiado,
                        numeropagina=1,
                        estado=1
                    )
                else:
                    solicituddocumento = SolicitudDocumento.objects.get(solicitud=solicitud, documento__tipo=1, status=True)
                    solicituddocumento.archivo = archivocopiado
                    solicituddocumento.archivofirmado = None
                    solicituddocumento.numeropagina = 1
                    solicituddocumento.estado = 1
                    solicituddocumento.observacion = ''

                solicituddocumento.save(request)

                # Borro la solicitud creada de manera general, no la del registro
                os.remove(archivo)

                # Si tiene estado P. NOVEDADES se debe actualizar el estado de al postulación y guardar recorrido
                if solicitud.estado.valor == 4:
                    # Obtengo estado EN EDICIÓN
                    estado = obtener_estado_solicitud(13, 1)
                    solicitud.estado = estado

                    solicitud.save(request)

                    # Guardo el recorrido de la solicitud
                    recorrido = RecorridoRegistro(
                        tiporegistro=2,
                        registroid=solicitud.id,
                        fecha=datetime.now().date(),
                        departamento=persona.mi_cargo_actual().unidadorganica,
                        persona=persona,
                        observacion='SOLICITUD EN EDICIÓN',
                        estado=estado
                    )
                    recorrido.save(request)

                return JsonResponse({"result": "ok", "documento": solicituddocumento.archivo.url})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar documento de la solicitud de beca. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'subirsolicitud':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivo = request.FILES['archivosolicitud']
                descripcionarchivo = 'Archivo de la solicitud firmada'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                numeropagina = 0

                # Obtengo número de páginas del archivo
                pdf2ReaderEvi = PyPDF2.PdfFileReader(archivo)
                numeropagina = pdf2ReaderEvi.numPages

                # Consulto la solicitud de beca
                postulacion = Solicitud.objects.get(pk=int(encrypt(request.POST['id'])))

                # Si tiene estado P. NOVEDADES se debe actualizar el estado de al postulación y guardar recorrido
                actualizaestado = postulacion.estado.valor == 4

                # Se debe actualizar el estado de al postulación y guardar recorrido en caso que tenga estado NOVEDADES
                if actualizaestado:
                    # Obtengo estado EN EDICIÓN
                    estado = obtener_estado_solicitud(13, 1)

                    postulacion.validada = False
                    postulacion.estadovalidacion = None
                    postulacion.estado = estado
                    postulacion.save(request)

                    # Guardo el recorrido de la solicitud
                    recorrido = RecorridoRegistro(
                        tiporegistro=2,
                        registroid=postulacion.id,
                        fecha=datetime.now().date(),
                        departamento=persona.mi_cargo_actual().unidadorganica,
                        persona=persona,
                        observacion='SOLICITUD EN EDICIÓN',
                        estado=estado
                    )
                    recorrido.save(request)

                archivo._name = generar_nombre("solicitudbeca", archivo._name)

                # Guardo o actualizo el archivo de la solicitud
                if not postulacion.solicituddocumento_set.values("id").filter(status=True, documento__tipo=1).exists():
                    # Consulto el tipo de documento
                    documento = Documento.objects.get(tipo=1)

                    # Guardo el documento de la solicitud
                    solicituddocumento = SolicitudDocumento(
                        solicitud=postulacion,
                        documento=documento,
                        archivo=archivo,
                        numeropagina=numeropagina,
                        estado=1
                    )
                else:
                    solicituddocumento = SolicitudDocumento.objects.get(solicitud=postulacion, documento__tipo=1, status=True)
                    solicituddocumento.archivo = archivo
                    solicituddocumento.numeropagina = numeropagina
                    solicituddocumento.estado = 1
                    solicituddocumento.observacion = ''

                solicituddocumento.save(request)

                log(u'%s subió solicitud de beca firmada para la solicitud: %s' % (persona, postulacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'firmarsolicitud':
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

                # Consulto la solicitud de beca
                postulacion = Solicitud.objects.get(pk=int(encrypt(request.POST['iddoc'])))

                # Obtengo el archivo de la solicitud
                documentosolicitud = postulacion.archivo_solicitud()
                archivosolicitud = documentosolicitud.archivo
                rutapdfarchivo = SITE_STORAGE + archivosolicitud.url
                textoabuscar = persona.nombre_completo_inverso()

                vecescontrado = 0
                ocurrencia = 2

                # Obtener coordenadas para ubicar al firma dependiendo de donde se encuentra ubicado el nombre de la persona
                documento = fitz.open(rutapdfarchivo)
                numpaginafirma = int(documento.page_count) - 1

                saltolinea = False
                words_dict = {}
                for page_number, page in enumerate(documento):
                    if page_number == numpaginafirma:
                        words = page.get_text("blocks")
                        words_dict[0] = words

                valor = None
                for cadena in words_dict[0]:
                    linea = cadena[4].replace("\n", " ")
                    if linea:
                        linea = linea.strip()

                    if textoabuscar in linea:
                        valor = cadena

                        vecescontrado += 1
                        if vecescontrado == ocurrencia:
                            break

                if valor:
                    y = 5000 - int(valor[3]) - 4110 # 4130
                else:
                    y = 0

                # x = 87  # izq
                x = 230  # cent
                # x = 374  # der

                # Si no existe el nombre de la persona en el documento
                if y == 0:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"No se encuentra el nombre del firmante en el documento", "showSwal": "True", "swalType": "warning"})

                # Obtener extensión y leer archivo de la firma
                extfirma = os.path.splitext(archivofirma.name)[1][1:]
                bytesfirma = archivofirma.read()

                # Firma del documento
                datau = JavaFirmaEc(
                    archivo_a_firmar=archivosolicitud,
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


                # # Firma del documento
                # generar_archivo_firmado = io.BytesIO()
                # datau, datas = firmar(request, clavefirma, archivofirma, archivosolicitud, numpaginafirma, x, y, 150, 45)
                # if not datau:
                #     return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % datas, "showSwal": "True", "swalType": "error"})
                #
                # generar_archivo_firmado.write(datau)
                # generar_archivo_firmado.write(datas)
                # generar_archivo_firmado.seek(0)

                nombrearchivofirmado = generar_nombre('solicitudbecafirmada', 'solicitudbecafirmada.pdf')
                objarchivo = DjangoFile(generar_archivo_firmado, nombrearchivofirmado)

                documentosolicitud.estado = 1
                documentosolicitud.archivofirmado = objarchivo
                documentosolicitud.save(request)

                # Si tiene estado P. NOVEDADES se debe actualizar el estado de al postulación y guardar recorrido
                if postulacion.estado.valor == 4:
                    # Obtengo estado EN EDICIÓN
                    estado = obtener_estado_solicitud(13, 1)
                    postulacion.estado = estado

                    postulacion.save(request)

                    # Guardo el recorrido de la solicitud
                    recorrido = RecorridoRegistro(
                        tiporegistro=2,
                        registroid=postulacion.id,
                        fecha=datetime.now().date(),
                        departamento=persona.mi_cargo_actual().unidadorganica,
                        persona=persona,
                        observacion='SOLICITUD EN EDICIÓN',
                        estado=estado
                    )
                    recorrido.save(request)

                log(u'%s firmó solicitud de beca para la postulación: %s' % (persona, postulacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Documento firmado con éxito", "showSwal": True, "documento": documentosolicitud.archivofirmado.url})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'confirmarpostulacion':
            try:
                # Consulto la postulación
                postulacion = Solicitud.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que tenga estado EN EDICIÓN
                if not postulacion.estado.valor == 1:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el Registro porque no tiene estado EN EDICIÓN", "showSwal": "True", "swalType": "warning"})

                # Obtengo estado SOLICITADO
                estado = obtener_estado_solicitud(13, 2)

                # Actualizo la postulación
                postulacion.estado = estado
                postulacion.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion='SOLICITUD REGISTRADA',
                    estado=estado
                )
                recorrido.save(request)

                # Consulto el document de la solicitud firmada
                documentosolicitud = postulacion.archivo_solicitud().archivofirmado

                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec

                # E-mail del destinatario
                # lista_email_envio = persona.lista_emails_envio()
                lista_email_envio = ['isaltosm@unemi.edu.ec']
                lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                lista_archivos_adjuntos = [documentosolicitud]

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                asuntoemail = "Registro de Postulación a Beca Docente"
                titulo = "Postulación Beca Docente"
                tiponotificacion = "REGSOL"

                # send_html_mail(asuntoemail,
                #                "emails/postulacionbecadocente.html",
                #                {'sistema': u'SGA - UNEMI',
                #                 'titulo': titulo,
                #                 'fecha': fechaenvio,
                #                 'hora': horaenvio,
                #                 'tiponotificacion': tiponotificacion,
                #                 'saludo': 'Estimada' if persona.sexo_id == 1 else 'Estimado',
                #                 'nombrepersona': persona.nombre_completo_inverso(),
                #                 'postulacion': postulacion
                #                 },
                #                lista_email_envio,
                #                lista_email_cco,
                #                lista_archivos_adjuntos,
                #                cuenta=CUENTAS_CORREOS[cuenta][1]
                #                )

                # Notificar por e-mail al Analista de Investigación
                personadestinatario = analista_investigacion()

                # E-mail del destinatario
                # lista_email_envio = personadestinatario.lista_emails_envio()
                lista_email_envio = ['isaltosm@unemi.edu.ec']

                asuntoemail = "Registro de Postulación a Beca Docente"
                titulo = "Postulación Beca Docente"
                tiponotificacion = "REGANLINV"

                # send_html_mail(asuntoemail,
                #                "emails/postulacionbecadocente.html",
                #                {'sistema': u'SGA - UNEMI',
                #                 'titulo': titulo,
                #                 'fecha': fechaenvio,
                #                 'hora': horaenvio,
                #                 'tiponotificacion': tiponotificacion,
                #                 'saludo': 'Estimada' if personadestinatario.sexo_id == 1 else 'Estimado',
                #                 'nombrepersona': personadestinatario.nombre_completo_inverso(),
                #                 'nombredocente': persona.nombre_completo_inverso(),
                #                 'saludodocente': 'la docente' if persona.sexo_id == 1 else 'el docente',
                #                 'postulacion': postulacion
                #                 },
                #                lista_email_envio,
                #                lista_email_cco,
                #                lista_archivos_adjuntos,
                #                cuenta=CUENTAS_CORREOS[cuenta][1]
                #                )

                log(u'%s confirmó postulación de becas para docentes: %s' % (persona, postulacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro de postulación confirmado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'delpostulacion':
            try:
                # Consulto la postulación
                postulacion = Solicitud.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que tenga estado EN EDICIÓN
                if not postulacion.estado.valor == 1:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede eliminar el Registro porque no tiene estado EN EDICIÓN", "showSwal": "True", "swalType": "warning"})

                # Obtengo estado ANULADO
                estado = obtener_estado_solicitud(13, 5)

                # Elimino la postulación
                postulacion.estado = estado
                postulacion.observacion = "ELIMINADA POR EL SOLICITANTE"
                postulacion.status = False
                postulacion.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion='SOLICITUD ELIMINADA',
                    estado=estado
                )
                recorrido.save(request)

                log(u'%s eliminó postulación de becas para docentes: %s' % (persona, postulacion), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al eliminar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'revisarinforme':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto el informe de otorgamiento de beca
                informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.POST['id'])))
                postulacion = informe.solicitud

                # Si no se puede revisar el informe de la postulación
                if not postulacion.puede_revisar_informe_otorgamiento():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se puede actualizar el registro debido a que el informe ha sido actualizado en la Coordinación de Investigación", "showSwal": "True", "swalType": "warning"})

                estado = int(request.POST['estado'])
                observacionrevision = ''
                # archivo = None

                # Estado REVISADO del informe
                if estado == 3:
                    # Obtengo estado INFORME DE FACTIBILIDAD REVISADO POR DOCENTE
                    estadosolicitud = obtener_estado_solicitud(13, 14)

                    # archivo = request.FILES['archivoinforme']
                    # descripcionarchivo = 'Archivo del Informe Firmado'
                    #
                    # # Validar el archivo
                    # resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '10MB')
                    # if resp['estado'] != "OK":
                    #     return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})
                    #
                    # numeropagina = 0
                    # # Verifica que el archivo no presente problemas
                    # try:
                    #     pdf2ReaderEvi = PyPDF2.PdfFileReader(archivo)
                    #     numeropagina = pdf2ReaderEvi.numPages
                    #
                    #     # Obtengo estado INFORME DE FACTIBILIDAD VALIDADO POR DOCENTE
                    #     estadosolicitud = obtener_estado_solicitud(13, 14)
                    # except Exception as ex:
                    #     return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El archivo presenta problemas", "showSwal": "True", "swalType": "warning"})
                else:
                    # Obtengo estado INFORME DE FACTBILIDAD CON NOVEDADES
                    estadosolicitud = obtener_estado_solicitud(13, 16)

                    observacionrevision = request.POST['observacion'].strip().upper()


                # Actualizo la postulación
                postulacion.estadoinformeo = 1 if estado == 3 else 3
                postulacion.estado = estadosolicitud
                postulacion.save(request)

                # Actualizo el informe
                informe.observacion = observacionrevision
                # if archivo:
                #     archivo._name = generar_nombre("informeotorgamiento", archivo._name)

                # informe.archivopostulante = archivo
                informe.estado = estado
                # informe.validado = estado == 3
                informe.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion=observacionrevision if observacionrevision else estadosolicitud.observacion,
                    estado=estadosolicitud
                )
                recorrido.save(request)

                # # Si fue VALIDADA notifico al Coordinador de investigación
                # if estado == 3:
                #     personadestinatario = coordinador_investigacion()
                #     cargovicerrector = informe.cargodestinatario.descripcion
                # else:
                #     # Notificar al Analista de investigación
                #     personadestinatario = analista_investigacion()

                # Si tiene NOVEDAD notifico al Analista de Investigación
                if estado == 5:
                    personadestinatario = analista_investigacion()

                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                # E-mail del destinatario
                # lista_email_envio = personadestinatario.lista_emails_envio()
                lista_email_envio = ['isaltosm@unemi.edu.ec']
                lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                lista_archivos_adjuntos = [informe.archivofirmado] if estado == 3 else []

                if estado == 3:
                #     asuntoemail = "Informe de Factibilidad de Otorgamiento de Beca Aceptado"
                #     titulo = "Postulación Beca Docente"
                #     tiponotificacion = "INFACEPDOC"
                #
                #     send_html_mail(asuntoemail,
                #                    "emails/postulacionbecadocente.html",
                #                    {'sistema': u'SGA - UNEMI',
                #                     'titulo': titulo,
                #                     'fecha': fechaenvio,
                #                     'hora': horaenvio,
                #                     'nombrepersona': postulacion.profesor.persona.nombre_completo_inverso(),
                #                     'articulodocente': 'la' if postulacion.profesor.persona.sexo_id == 1 else 'el',
                #                     'nombrecoordinador': personadestinatario.nombre_completo_inverso(),
                #                     'postulacion': postulacion,
                #                     'observacionrevision': observacionrevision,
                #                     'tiponotificacion': tiponotificacion,
                #                     'saludo': 'Estimada' if personadestinatario.sexo_id == 1 else 'Estimado',
                #                     'cargovicerrector': cargovicerrector
                #                     },
                #                    lista_email_envio,
                #                    lista_email_cco,
                #                    lista_archivos_adjuntos,
                #                    cuenta=CUENTAS_CORREOS[cuenta][1]
                #                    )

                    log(u'%s revisó y aceptó informe de factibilidad de otorgamiento de beca: %s' % (persona, informe), request, "edit")
                else:
                    asuntoemail = "Novedades con Informe de Factibilidad de Otorgamiento de beca"
                    titulo = "Postulación Beca Docente"
                    tiponotificacion = "RECHREV"

                    send_html_mail(asuntoemail,
                                   "emails/postulacionbecadocente.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'nombrepersona': postulacion.profesor.persona.nombre_completo_inverso(),
                                    'articulodocente': 'la' if postulacion.profesor.persona.sexo_id == 1 else 'el',
                                    'nombreanalista': personadestinatario.nombre_completo_inverso(),
                                    'postulacion': postulacion,
                                    'observacionrevision': observacionrevision,
                                    'tiponotificacion': tiponotificacion,
                                    'saludo': 'Estimada' if personadestinatario.sexo_id == 1 else 'Estimado'
                                    },
                                   lista_email_envio,
                                   lista_email_cco,
                                   lista_archivos_adjuntos,
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                    log(u'%s rechazó informe de factibilidad de otorgamiento de beca: %s' % (persona, informe), request, "edit")

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'firmarinformeotorgamiento':
            try:
                if 'iddoc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto el informe
                informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.POST['iddoc'])))
                postulacion = informe.solicitud

                # Verifico si puede firmar el informe
                if not postulacion.puede_firmar_informe_otorgamiento_docente():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se puede actualizar el registro debido a que el informe ha sido notificado al Vicerrector de Investigación y Posgrado", "showSwal": "True", "swalType": "warning"})

                tipofirma = request.POST['tipofirma']
                archivofirma = request.FILES['archivofirma']
                clavefirma = request.POST['cfirma']
                descripcionarchivo = 'Archivo de la firma electrónica'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivofirma, ['P12', 'PFX'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Obtengo el archivo del informe
                archivoinforme = informe.archivofirmado
                rutapdfarchivo = SITE_STORAGE + archivoinforme.url

                textoabuscar = profesor.persona.nombre_completo_inverso()[:20]
                textofirma = 'Validado por:'
                ocurrencia = 1

                vecescontrado = 0
                documento = fitz.open(rutapdfarchivo)
                numpaginafirma = int(documento.page_count) - 1

                # Busca la página donde se encuentran ubicados los textos: Elaborado por, Validado por, Verificado por y Aprobado por
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

                valor = None
                for cadena in words_dict[0]:
                    linea = cadena[4].replace("\n", "")
                    if linea:
                        linea = linea.strip()

                    if textoabuscar in linea:
                        valor = cadena

                        vecescontrado += 1
                        if vecescontrado == ocurrencia:
                            saltolinea = salto_linea_nombre_firma_encontrado(cadena[4])
                            break

                saltolinea = False

                if valor:
                    if not saltolinea:
                        # y = 5000 - int(valor[3]) - 4140
                        y = 5000 - int(valor[3]) - 4125
                    else:
                        # y = 5000 - int(valor[3]) - 4130
                        y = 5000 - int(valor[3]) - 4100
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

                # # Firma del documento
                # generar_archivo_firmado = io.BytesIO()
                # datau, datas = firmar(request, clavefirma, archivofirma, archivoinforme, numpaginafirma, x, y, 150, 45)
                # if not datau:
                #     return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % datas, "showSwal": "True", "swalType": "error"})
                #
                # generar_archivo_firmado.write(datau)
                # generar_archivo_firmado.write(datas)
                # generar_archivo_firmado.seek(0)

                nombrearchivofirmado = generar_nombre('informeotorgamientobecafirmado', 'informeotorgamientobecafirmado.pdf')
                objarchivo = DjangoFile(generar_archivo_firmado, nombrearchivofirmado)

                informe.archivofirmado = objarchivo
                informe.firmavalida = True
                informe.estado = 4
                informe.save(request)

                # Actualizar postulación
                if postulacion.estado.valor != 15:
                    # Obtengo estado INFORME DE OTORGAMIENTO VALIDADO POR DOCENTE
                    estadosolicitud = obtener_estado_solicitud(13, 15)

                    postulacion.estadoinformeo = 2
                    postulacion.estado = estadosolicitud
                    postulacion.save(request)

                    # Guardo el recorrido de la solicitud
                    recorrido = RecorridoRegistro(
                        tiporegistro=2,
                        registroid=postulacion.id,
                        fecha=datetime.now().date(),
                        departamento=persona.mi_cargo_actual().unidadorganica,
                        persona=persona,
                        observacion=estadosolicitud.observacion,
                        estado=estadosolicitud
                    )
                    recorrido.save(request)

                    # Notificar al Coordinador de Investigación
                    personadestinatario = coordinador_investigacion()
                    cargovicerrector = informe.cargodestinatario.descripcion

                    # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                    listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec

                    fechaenvio = datetime.now().date()
                    horaenvio = datetime.now().time()
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                    # E-mail del destinatario
                    # lista_email_envio = personadestinatario.lista_emails_envio()
                    lista_email_envio = ['isaltosm@unemi.edu.ec']
                    lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                    lista_archivos_adjuntos = [informe.archivofirmado]

                    asuntoemail = "Informe de Factibilidad de Otorgamiento de Beca Aceptado"
                    titulo = "Postulación Beca Docente"
                    tiponotificacion = "INFACEPDOC"

                    send_html_mail(asuntoemail,
                                   "emails/postulacionbecadocente.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'nombrepersona': postulacion.profesor.persona.nombre_completo_inverso(),
                                    'articulodocente': 'la' if postulacion.profesor.persona.sexo_id == 1 else 'el',
                                    'nombrecoordinador': personadestinatario.nombre_completo_inverso(),
                                    'postulacion': postulacion,
                                    'observacionrevision': '',
                                    'tiponotificacion': tiponotificacion,
                                    'saludo': 'Estimada' if personadestinatario.sexo_id == 1 else 'Estimado',
                                    'cargovicerrector': cargovicerrector
                                    },
                                   lista_email_envio,
                                   lista_email_cco,
                                   lista_archivos_adjuntos,
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                log(u'%s firmó informe de otorgamiento de solicitud de beca: %s' % (persona, informe), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Documento firmado con éxito", "showSwal": True, "documento": informe.archivofirmado.url})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'revisarresolucion':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la resolución
                resolucion = ResolucionComite.objects.get(pk=int(encrypt(request.POST['id'])))
                postulacion = resolucion.solicitud

                # Si no se puede revisar el informe de la postulación
                if not postulacion.puede_revisar_resolucion_comite():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se puede actualizar el registro debido a que la resolución ha sido actualizada en la Coordinación de Investigación", "showSwal": "True", "swalType": "warning"})

                # Valores del formulario
                estado = int(request.POST['estado'])
                observacionrevision = request.POST['observacion'].strip().upper() if estado == 2 else ''

                # Obtengo estado RESOLUCIÓN REVISADA POR EL SOLICITANTE
                estadosolicitud = obtener_estado_solicitud(13, 24)

                # Actualizo la postulación
                postulacion.estado = estadosolicitud
                postulacion.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion=estadosolicitud.observacion,
                    estado=estadosolicitud
                )
                recorrido.save(request)

                # Si el resultado de la resolución es FAVORABLE
                if resolucion.resultado == 1:
                    # Obtengo el estado a asignar: POSTULACIÓN ACEPTADA POR COMITÉ DE BECAS o NOVEDAD EN RESOLUCIÓN
                    estadosolicitud = obtener_estado_solicitud(13, 25) if estado == 1 else obtener_estado_solicitud(13, 26)
                else:
                    # Obtengo el estado a asignar: POSTULACIÓN DENEGADA POR COMITÉ DE BECAS o RESULTADO DE RESOLUCIÓN APELADA POR SOLICITANTE
                    estadosolicitud = obtener_estado_solicitud(13, 27) if estado == 1 else obtener_estado_solicitud(13, 28)

                # Actualizo la postulación
                postulacion.estado = estadosolicitud
                postulacion.save(request)

                # Guardo el recorrido de la solicitud
                recorrido = RecorridoRegistro(
                    tiporegistro=2,
                    registroid=postulacion.id,
                    fecha=datetime.now().date(),
                    departamento=persona.mi_cargo_actual().unidadorganica,
                    persona=persona,
                    observacion=observacionrevision if observacionrevision else estadosolicitud.observacion,
                    estado=estadosolicitud
                )
                recorrido.save(request)

                # Actualizo la resolucion
                resolucion.aceptada = estado == 1
                if resolucion.resultado == 2:
                    resolucion.apelacion = estado == 2

                resolucion.observacion = observacionrevision
                resolucion.save(request)

                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                # Si el resultado de la resolución es FAVORABLE
                if resolucion.resultado == 1:
                    # Si aceptó el resultado notificar al Comité de Becas y al Coordinador de Investigación
                    if estado == 1:
                        # Notificar al comité de becas y solicitante
                        persona_destinatario = secretaria_comite_becas(postulacion.convocatoria)
                        # lista_email_envio = persona_destinatario.lista_emails_envio()
                        # lista_email_envio = lista_email_envio + postulacion.profesor.persona.lista_emails_envio()

                        lista_email_envio = ['isaltosm@unemi.edu.ec']
                        lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                        lista_archivos_adjuntos = []

                        asuntoemail = "Resolución del Comité de Becas Revisada y Aceptada por el Postulante (Postulación Aceptada)"
                        titulo = "Postulación Beca Docente"
                        tiponotificacion = "RESFAVACE"

                        send_html_mail(asuntoemail,
                                       "emails/postulacionbecadocente.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'titulo': titulo,
                                        'fecha': fechaenvio,
                                        'hora': horaenvio,
                                        'nombredocente': postulacion.profesor.persona.nombre_completo_inverso(),
                                        'articulodocente': 'la' if postulacion.profesor.persona.sexo_id == 1 else 'el',
                                        'postulacion': postulacion,
                                        'resolucion': resolucion,
                                        'observacionrevision': '',
                                        'tiponotificacion': tiponotificacion,
                                        'saludo': 'Estimados',
                                        },
                                       lista_email_envio,
                                       lista_email_cco,
                                       lista_archivos_adjuntos,
                                       cuenta=CUENTAS_CORREOS[cuenta][1]
                                       )

                        # Notificar por e-mail al Coordnador de Investigación
                        personadestinatario = coordinador_investigacion()

                        # E-mail del destinatario
                        # lista_email_envio = personadestinatario.lista_emails_envio()
                        lista_email_envio = ['isaltosm@unemi.edu.ec']
                        lista_archivos_adjuntos = [resolucion.archivofirmado]

                        asuntoemail = "Postulación a Beca Docente Aceptada por el Comité Institucional de Becas"
                        titulo = "Postulación Beca Docente"
                        tiponotificacion = "RESFAVCOOR"

                        send_html_mail(asuntoemail,
                                       "emails/postulacionbecadocente.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'titulo': titulo,
                                        'fecha': fechaenvio,
                                        'hora': horaenvio,
                                        'tiponotificacion': tiponotificacion,
                                        'saludo': 'Estimada' if personadestinatario.sexo_id == 1 else 'Estimado',
                                        'nombrepersona': personadestinatario.nombre_completo_inverso(),
                                        'nombredocente': postulacion.profesor.persona.nombre_completo_inverso(),
                                        'genpersona': 'de la docente' if postulacion.profesor.persona.sexo_id == 1 else 'del docente',
                                        'postulacion': postulacion,
                                        'resolucion': resolucion
                                        },
                                       lista_email_envio,
                                       lista_email_cco,
                                       lista_archivos_adjuntos,
                                       cuenta=CUENTAS_CORREOS[cuenta][1]
                                       )

                        log(u'%s revisó y aceptó resultado de la resolución del comité de becas: %s' % (persona, resolucion), request, "edit")
                    else:
                        # Notificar al comité de becas y solicitante
                        persona_destinatario = secretaria_comite_becas(postulacion.convocatoria)
                        # lista_email_envio = persona_destinatario.lista_emails_envio()
                        # lista_email_envio = lista_email_envio + postulacion.profesor.persona.lista_emails_envio()

                        lista_email_envio = ['isaltosm@unemi.edu.ec']
                        lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                        lista_archivos_adjuntos = []

                        asuntoemail = "Resolución del Comité de Becas Revisada y No Aceptada por el Postulante - Novedades Encontradas"
                        titulo = "Postulación Beca Docente"
                        tiponotificacion = "RESFAVNOV"

                        send_html_mail(asuntoemail,
                                       "emails/postulacionbecadocente.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'titulo': titulo,
                                        'fecha': fechaenvio,
                                        'hora': horaenvio,
                                        'nombredocente': postulacion.profesor.persona.nombre_completo_inverso(),
                                        'articulodocente': 'la' if postulacion.profesor.persona.sexo_id == 1 else 'el',
                                        'postulacion': postulacion,
                                        'resolucion': resolucion,
                                        'observacionrevision': observacionrevision,
                                        'tiponotificacion': tiponotificacion,
                                        'saludo': 'Estimados',
                                        },
                                       lista_email_envio,
                                       lista_email_cco,
                                       lista_archivos_adjuntos,
                                       cuenta=CUENTAS_CORREOS[cuenta][1]
                                       )

                        log(u'%s revisó y no aceptó resultado de la resolución del comité de becas: %s' % (persona, resolucion), request, "edit")
                else:
                    # Si aceptó el resultado notificar al Comité de Becas y al Coordinador de Investigación
                    if estado == 1:
                        # Notificar al comité de becas y solicitante
                        persona_destinatario = secretaria_comite_becas(postulacion.convocatoria)
                        # lista_email_envio = persona_destinatario.lista_emails_envio()
                        # lista_email_envio = lista_email_envio + postulacion.profesor.persona.lista_emails_envio()

                        lista_email_envio = ['isaltosm@unemi.edu.ec']
                        lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                        lista_archivos_adjuntos = []

                        asuntoemail = "Resolución del Comité de Becas Revisada y Aceptada por el Postulante (Postulación Denegada)"
                        titulo = "Postulación Beca Docente"
                        tiponotificacion = "RESNOFAVACE"

                        send_html_mail(asuntoemail,
                                       "emails/postulacionbecadocente.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'titulo': titulo,
                                        'fecha': fechaenvio,
                                        'hora': horaenvio,
                                        'nombredocente': postulacion.profesor.persona.nombre_completo_inverso(),
                                        'articulodocente': 'la' if postulacion.profesor.persona.sexo_id == 1 else 'el',
                                        'postulacion': postulacion,
                                        'resolucion': resolucion,
                                        'observacionrevision': '',
                                        'tiponotificacion': tiponotificacion,
                                        'saludo': 'Estimados',
                                        },
                                       lista_email_envio,
                                       lista_email_cco,
                                       lista_archivos_adjuntos,
                                       cuenta=CUENTAS_CORREOS[cuenta][1]
                                       )

                        log(u'%s revisó y aceptó resultado de la resolución del comité de becas: %s' % (persona, resolucion), request, "edit")
                    else:
                        # Notificar al comité de becas y solicitante
                        persona_destinatario = secretaria_comite_becas(postulacion.convocatoria)
                        # lista_email_envio = persona_destinatario.lista_emails_envio()
                        # lista_email_envio = lista_email_envio + postulacion.profesor.persona.lista_emails_envio()

                        lista_email_envio = ['isaltosm@unemi.edu.ec']
                        lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                        lista_archivos_adjuntos = []

                        asuntoemail = "Resolución del Comité de Becas Revisada y No Aceptada por el Postulante - Apelación Registrada"
                        titulo = "Postulación Beca Docente"
                        tiponotificacion = "RESNOFAVAPE"

                        send_html_mail(asuntoemail,
                                       "emails/postulacionbecadocente.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'titulo': titulo,
                                        'fecha': fechaenvio,
                                        'hora': horaenvio,
                                        'nombredocente': postulacion.profesor.persona.nombre_completo_inverso(),
                                        'articulodocente': 'la' if postulacion.profesor.persona.sexo_id == 1 else 'el',
                                        'postulacion': postulacion,
                                        'resolucion': resolucion,
                                        'observacionrevision': observacionrevision,
                                        'tiponotificacion': tiponotificacion,
                                        'saludo': 'Estimados',
                                        },
                                       lista_email_envio,
                                       lista_email_cco,
                                       lista_archivos_adjuntos,
                                       cuenta=CUENTAS_CORREOS[cuenta][1]
                                       )

                        log(u'%s revisó y no aceptó resultado de la resolución del comité de becas, apelación registrada: %s' % (persona, resolucion), request, "edit")

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})


        # elif action == 'subirinformefirmado':
        #     try:
        #         if 'archivoinforme' in request.FILES:
        #             archivo = request.FILES['archivoinforme']
        #             descripcionarchivo = 'Archivo de informe de factibilidad firmada'
        #             resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
        #             if resp['estado'] != "OK":
        #                 return JsonResponse(
        #                     {"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True",
        #                      "swalType": "warning"})
        #             try:
        #                 pdf2ReaderEvi = PyPDF2.PdfFileReader(archivo)
        #                 numeropagina = pdf2ReaderEvi.numPages
        #             except Exception as ex:
        #                 return JsonResponse(
        #                     {"result": "bad", "titulo": "Atención!!!", "mensaje": "El archivo presenta problemas",
        #                      "showSwal": "True", "swalType": "warning"})
        #             archivo._name = generar_nombre("informefactibilidad", archivo._name)
        #             postulacion = Solicitud.objects.get(id=int(request.POST['id']))
        #             estadosolicitud = obtener_estado_solicitud(13, 16)
        #             postulacion.estado = estadosolicitud
        #             analistainvestigacion = DistributivoPersona.objects.filter(status=True,denominacionpuesto_id=variable_valor('ID_CARGO_ANALISTA_INV'),estadopuesto_id=1)
        #             informefactibilidad = InformeFactibilidad.objects.get(solicitud_id=postulacion.id)
        #             informefactibilidad.archivopostulante = archivo
        #             informefactibilidad.estado = 5
        #             postulacion.save(request)
        #             informefactibilidad.save(request)
        #             recorrido = RecorridoRegistro(
        #                 tiporegistro=2,
        #                 registroid=postulacion.id,
        #                 fecha=datetime.now().date(),
        #                 departamento=persona.mi_cargo_actual().unidadorganica,
        #                 persona=persona,
        #                 observacion=estadosolicitud.observacion,
        #                 estado=estadosolicitud
        #             )
        #             recorrido.save(request)
        #             fechaenvio = datetime.now().date()
        #             horaenvio = datetime.now().time()
        #             asuntoemail = "Informe de factibilidad cargado"
        #             titulo = "Informe de factibilidad cargado"
        #             tiponotificacion = "INFORCARG"
        #             send_html_mail(asuntoemail,
        #                            "emails/postulacionbecadocente.html",
        #                            {'sistema': u'SGA - UNEMI',
        #                             'titulo': titulo,
        #                             'fecha': fechaenvio,
        #                             'hora': horaenvio,
        #                             'nombrepersona': postulacion.profesor.persona.nombre_completo_inverso(),
        #                             'articulodocente': 'la' if postulacion.profesor.persona.sexo_id == 1 else 'el',
        #                             'nombreanalista': analistainvestigacion[1].persona,
        #                             'postulacion': postulacion,
        #                             'tiponotificacion': tiponotificacion,
        #                             # 'saludo': 'Estimada' if postulacion.profesor.persona.sexo_id == 1 else 'Estimado',
        #                             'saludo': 'Estimada' if analistainvestigacion[1].persona.sexo_id == 1 else 'Estimado',
        #                             },
        #                            ['jidrovoc@unemi.edu.ec'],
        #                            [],
        #                            cuenta=CUENTAS_CORREOS[16][1]
        #                            )
        #             log(u'Subió informe factibilidad firmado: %s' % informefactibilidad, request, "act")
        #             return JsonResponse({"result": 'ok','titulo':'Datos correctos','mensaje':'Informe subido con éxito'})
        #     except Exception as ex:
        #         pass

        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Solicitud incorrecta.", "showSwal": "True", "swalType": "error"})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'verificardocumentopersonal':
                try:
                    # Obtengo los documentos personales
                    documentos = persona.documentos_personales()
                    subirdocumentos = False

                    if not documentos:
                        subirdocumentos = True
                    else:
                        # Si tiene cédula y papeleta se puede mostrar la pantalla de postulación
                        if documentos.cedula and documentos.papeleta:
                            return JsonResponse({"result": "ok"})
                        else:
                            subirdocumentos = True

                    if subirdocumentos:
                        data['title'] = u'Subir Documentos Personales'
                        data['idc'] = request.GET['idc']
                        data['cedula'] = documentos.cedula if documentos else None
                        data['papeleta'] = documentos.papeleta if documentos else None

                        template = get_template("pro_becadocente/subirdocumentopersonal.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "bad", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la consulta. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            elif action == 'addpostulacion':
                try:
                    data['title'] = u'Agregar Postulación a Beca'

                    fecha = datetime.now().date()
                    hora = datetime.now().time()

                    data['convocatoria'] = convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.GET['idc'])))
                    lista_requisitos = []

                    # Obtengo los requisitos de la convocatoria
                    requisitosc = convocatoria.requisitos()

                    # Obtengo los documentos personales
                    documentos = persona.documentos_personales()

                    evaluacion = None
                    archivocertificado = None

                    # Obtengo evaluación docente más reciente
                    # evaluaciones = None
                    evaluaciones = RespuestaEvaluacionAcreditacion.objects.values('profesor', 'proceso', 'proceso__periodo', 'proceso__periodo_id', 'proceso__periodo__nombre', 'proceso__periodo__tipo_id').filter(profesor=profesor, status=True, proceso__mostrarresultados=True).exclude(proceso__periodo__tipo_id__in=[3, 4]).distinct().order_by('-proceso')
                    if evaluaciones:
                        for eval in evaluaciones:
                            if profesor.puede_vercertificado(eval['proceso__periodo']):
                                evaluacion = eval
                                break

                    # Si existe evaluación debo generar el pdf del certificado
                    if evaluacion:
                        # Generar PDF inicio
                        directorio = SITE_STORAGE + '/media/certificadoedocente'
                        try:
                            os.stat(directorio)
                        except:
                            os.mkdir(directorio)

                        data['datospersona'] = persona
                        data['profesor'] = profesor
                        data['nomperiodo'] = evaluacion['proceso__periodo__nombre']

                        periodoe = evaluacion['proceso__periodo']
                        periodoe_id = evaluacion['proceso__periodo_id']
                        respuestas = []
                        promediovirtual = 0

                        data['departamento'] = departamento = Departamento.objects.get(pk=128)
                        data['firma'] = FirmaPersona.objects.get(persona=departamento.responsable)

                        data['procesoperiodo'] = ProcesoEvaluativoAcreditacion.objects.get(periodo=periodoe, status=True)

                        if RubricaPreguntas.objects.filter(rubrica__tipo_criterio=1, rubrica__informativa=False, rubrica__para_nivelacionvirtual=True, detallerespuestarubrica__respuestarubrica__respuestaevaluacion__tipoinstrumento=1, detallerespuestarubrica__respuestarubrica__respuestaevaluacion__profesor=profesor, detallerespuestarubrica__respuestarubrica__respuestaevaluacion__proceso__periodo=periodoe).distinct().exists():
                            for prome in RubricaPreguntas.objects.values_list('id').filter(rubrica__tipo_criterio=1,
                                                                                           rubrica__informativa=False,
                                                                                           rubrica__para_nivelacionvirtual=True,
                                                                                           detallerespuestarubrica__respuestarubrica__respuestaevaluacion__tipoinstrumento=1,
                                                                                           detallerespuestarubrica__respuestarubrica__respuestaevaluacion__profesor=profesor,
                                                                                           detallerespuestarubrica__respuestarubrica__respuestaevaluacion__proceso__periodo=periodoe).annotate(prom=Avg('detallerespuestarubrica__valor')):
                                respuestas.append(null_to_decimal(prome[1], 2))
                            promedio = statistics.mean(respuestas) if respuestas else 0
                            promediovirtual = null_to_decimal(promedio, 2) if promedio else 0
                        data['promediovirtual'] = promediovirtual
                        promedionovirtual = 0
                        respuestas2 = []
                        if RubricaPreguntas.objects.filter(rubrica__tipo_criterio=1, rubrica__informativa=False, rubrica__para_nivelacionvirtual=False, detallerespuestarubrica__respuestarubrica__respuestaevaluacion__tipoinstrumento=1, detallerespuestarubrica__respuestarubrica__respuestaevaluacion__profesor=profesor, detallerespuestarubrica__respuestarubrica__respuestaevaluacion__proceso__periodo=periodoe).distinct().exists():
                            for prome in RubricaPreguntas.objects.values_list('id').filter(rubrica__tipo_criterio=1,
                                                                                           rubrica__informativa=False,
                                                                                           rubrica__para_nivelacionvirtual=False,
                                                                                           detallerespuestarubrica__respuestarubrica__respuestaevaluacion__tipoinstrumento=1,
                                                                                           detallerespuestarubrica__respuestarubrica__respuestaevaluacion__profesor=profesor,
                                                                                           detallerespuestarubrica__respuestarubrica__respuestaevaluacion__proceso__periodo=periodoe).annotate(prom=Avg('detallerespuestarubrica__valor')):
                                respuestas2.append(null_to_decimal(prome[1], 2))
                            promedio = statistics.mean(respuestas2) if respuestas2 else 0
                            promedionovirtual = null_to_decimal(promedio, 2) if promedio else 0
                        data['promedionovirtual'] = promedionovirtual
                        data['resultados'] = porcentaje = ResumenFinalEvaluacionAcreditacion.objects.get(distributivo__profesor=profesor, distributivo__periodo=periodoe)
                        data['porcentaje'] = notaporcentaje = round(((porcentaje.resultado_total * 100) / 5), 2)
                        data['fechactual'] = datetime.now().strftime("%d") + '/' + datetime.now().strftime("%m") + '/' + datetime.now().strftime("%y") + ' ' + datetime.now().strftime("%H:%M")
                        notaporcen = str(periodoe_id) + "-" + persona.cedula + "-" + str(notaporcentaje)

                        qrname = 'evaluaciondoc' + fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__()

                        # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente', 'qr'))
                        # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                        rutapdf = folder + qrname + '.pdf'
                        rutaimg = folder + qrname + '.png'
                        if os.path.isfile(rutapdf):
                            os.remove(rutaimg)
                            os.remove(rutapdf)
                        url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/evaluaciondocente/' + qrname + '.pdf')
                        imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                        imagebarcode = code128.image(notaporcen).save(folder + qrname + "_bar.png")
                        data['qrname'] = 'qr' + qrname
                        data['storage'] = SITE_STORAGE

                        data['url_path'] = 'http://127.0.0.1:8000'
                        if not DEBUG:
                            data['url_path'] = 'https://sga.unemi.edu.ec'

                        nombrearchivo = qrname + '.pdf'
                        valida = convert_html_to_pdf(
                            'pro_certificados/pdfqrce_modeloactual.html',
                            {'pagesize': 'A4', 'listadoevaluacion': data},
                            nombrearchivo,
                            directorio
                        )
                        # Generar PDF fin

                        # archivocertificado = directorio + "/" + nombrearchivo
                        archivocertificado = 'media/certificadoedocente/' + nombrearchivo

                    # Verifico el tipo de requisito
                    for requisitoc in requisitosc:
                        # Si es requisito general
                        if requisitoc.requisito.tipo == 1:
                            datos = {
                                'id': requisitoc.requisito.id,
                                'secuencia': requisitoc.secuencia,
                                'descripcion': requisitoc.requisito.descripcion,
                                'subirarchivo': True,
                                'obligatorio': requisitoc.requierearchivo,
                                'observacion': '',
                                'urlarchivo': ''
                            }
                        # Si es cédula o papeleta de votación
                        elif requisitoc.requisito.tipo == 2 or requisitoc.requisito.tipo == 3:
                            # Si tiene documentos y cédula y/o papeleta subida
                            urlarchivo = ''
                            if documentos:
                                if requisitoc.requisito.tipo == 2:
                                    urlarchivo = documentos.cedula.url if documentos.cedula else ''
                                else:
                                    urlarchivo = documentos.papeleta.url if documentos.papeleta else ''

                            datos = {
                                'id': requisitoc.requisito.id,
                                'secuencia': requisitoc.secuencia,
                                'descripcion': requisitoc.requisito.descripcion,
                                'subirarchivo': False if urlarchivo else True,
                                'obligatorio': False if urlarchivo else True,
                                'observacion': 'EL DOCUMENTO NO HA SIDO CARGADO EN MÓDULO HOJA DE VIDA' if not urlarchivo else '',
                                'urlarchivo': urlarchivo
                            }
                        # Evaluación de desempeño docente
                        else:
                            datos = {
                                'id': requisitoc.requisito.id,
                                'secuencia': requisitoc.secuencia,
                                'descripcion': requisitoc.requisito.descripcion,
                                'subirarchivo': False,
                                'obligatorio': False,
                                'observacion': '' if archivocertificado else 'NO EXISTE INFORMACIÓN DE EVALUACIÓN DOCENTE',
                                'urlarchivo': archivocertificado
                            }

                        lista_requisitos.append(datos)

                    data['requisitos'] = lista_requisitos
                    data['tipoestudio'] = TIPO_ESTUDIO
                    data['universidades'] = InstitucionEducacionSuperior.objects.filter(status=True).order_by('nombre')
                    data['paises'] = Pais.objects.filter(status=True).order_by('nombre')
                    data['modalidades'] = Modalidad.objects.filter(status=True).order_by('nombre')
                    data['lineasinvestigacion'] = LineaInvestigacion.objects.filter(vigente=True, status=True).order_by('nombre')
                    data['tipopermiso'] = TIPO_PERMISO
                    data['tipolicencia'] = TIPO_LICENCIA
                    data['fecha'] = fecha
                    data['archivocertificado'] = archivocertificado

                    return render(request, "pro_becadocente/addpostulacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'editpostulacion':
                try:
                    data['title'] = u'Editar Postulación a Beca'

                    fecha = datetime.now().date()

                    data['postulacion'] = solicitud = Solicitud.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['convocatoria'] = solicitud.convocatoria
                    data['requisitos'] = solicitud.requisitos()

                    data['tipoestudio'] = TIPO_ESTUDIO
                    data['universidades'] = InstitucionEducacionSuperior.objects.filter(status=True).order_by('nombre')
                    data['paises'] = Pais.objects.filter(status=True).order_by('nombre')
                    data['modalidades'] = Modalidad.objects.filter(status=True).order_by('nombre')
                    data['lineasinvestigacion'] = LineaInvestigacion.objects.filter(vigente=True, status=True).order_by('nombre')
                    data['tipopermiso'] = TIPO_PERMISO
                    data['tipolicencia'] = TIPO_LICENCIA

                    return render(request, "pro_becadocente/editpostulacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpresupuesto':
                try:
                    data['title'] = u'Agregar Presupuesto a Postulación de Beca'
                    data['solicitud'] = solicitud = Solicitud.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['convocatoria'] = convocatoria = solicitud.convocatoria

                    listaanios = []
                    anioi = solicitud.inicio.year
                    aniof = solicitud.fin.year
                    total = (aniof - anioi) + 1

                    for n in range(total):
                        listaanios.append(anioi)
                        anioi += 1

                    data['cantidadperiodos'] = cantidadperiodos = (solicitud.fin.year - solicitud.inicio.year) + 1
                    data['colspancab'] = (cantidadperiodos * 2) + 4
                    data['anios'] = listaanios
                    data['rubros'] = convocatoria.rubros()

                    return render(request, "pro_becadocente/addpresupuesto.html", data)
                except Exception as ex:
                    pass

            elif action == 'editpresupuesto':
                try:
                    data['title'] = u'Editar Presupuesto a Postulación de Beca'
                    data['postulacion'] = postulacion = Solicitud.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['convocatoria'] = convocatoria = postulacion.convocatoria
                    data['presupuesto'] = presupuesto = postulacion.presupuesto_solicitud()
                    data['cantidadperiodos'] = cantidadperiodos = presupuesto.numeroperiodo

                    listaanios = []
                    anioi = postulacion.inicio.year
                    aniof = postulacion.fin.year
                    total = (aniof - anioi) + 1

                    for n in range(total):
                        listaanios.append(anioi)
                        anioi += 1

                    data['colspancab'] = (cantidadperiodos * 2) + 4
                    data['anios'] = listaanios
                    data['rubros'] = postulacion.rubros()

                    return render(request, "pro_becadocente/editpresupuesto.html", data)
                except Exception as ex:
                    pass

            elif action == 'mostrarrecorrido':
                try:
                    title = u'Recorrido de la Postulación a Beca'
                    solicitud = Solicitud.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitud'] = solicitud
                    data['recorrido'] = solicitud.recorrido()
                    template = get_template("pro_becadocente/recorridopostulacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mostrarinformacion':
                try:
                    data['title'] = u'Información de la Postulación a Beca'
                    postulacion = Solicitud.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['postulacion'] = postulacion
                    data['requisitos'] = requisitos = postulacion.requisitos()
                    data['primerdocumento'] = requisitos[0]
                    data['documentos'] = postulacion.documentos()
                    data['faltacarta'] = faltacarta = requisitos.filter(requisito__numero=5, estado=6).exists()
                    data['requisitocarta'] = requisitos.filter(requisito__numero=5)[0].requisito.descripcion if faltacarta else ''
                    data['presupuesto'] = presupuesto = postulacion.presupuesto_solicitud()
                    data['cantidadperiodos'] = cantidadperiodos = presupuesto.numeroperiodo

                    listaanios = []
                    anioi = postulacion.inicio.year
                    aniof = postulacion.fin.year
                    total = (aniof - anioi) + 1

                    for n in range(total):
                        listaanios.append(anioi)
                        anioi += 1

                    data['colspancab'] = (cantidadperiodos * 2) + 4
                    data['anios'] = listaanios
                    data['rubros'] = postulacion.rubros()

                    return render(request, "pro_becadocente/informacionpostulacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'mostrarnovedad':
                try:
                    title = u'Novedades de la Postulación a Beca'
                    postulaciones = Solicitud.objects.filter(status=True, convocatoria_id=int(encrypt(request.GET['id'])), profesor=profesor, estado__valor__in=[4, 6]).order_by('-fechasolicitud')
                    data['postulaciones'] = postulaciones
                    template = get_template("pro_becadocente/novedadpostulacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subirsolicitud':
                try:
                    data['title'] = u'Subir Solicitud de Beca Firmada'

                    solicitud = Solicitud.objects.get(pk=int(encrypt(request.GET['id'])))

                    # Verifico que el tipo de documento SOLICITUD DE BECA esté asignado a la convocatoria
                    if not DocumentoConvocatoria.objects.filter(status=True, convocatoria=solicitud.convocatoria, documento__tipo=1).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El documento [Solicitud de Beca] no está asignado a la convocatoria"})

                    data['solicitud'] = solicitud

                    template = get_template("pro_becadocente/subirsolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'firmarsolicitud':
                try:
                    data['title'] = u'Firmar Solicitud de Beca'

                    solicitud = Solicitud.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['solicitud'] = solicitud
                    data['iddoc'] = solicitud.id  # ID del documento a firmar
                    data['idper'] = solicitud.profesor.persona.id  # ID de la persona que firma
                    data['tipofirma'] = 'SOL'

                    data['mensaje'] = "Firma de Solicitud de Beca del docente <b>{}</b> para el programa <b>{}</b>".format(solicitud.profesor.persona.nombre_completo_inverso(), solicitud.programa)
                    data['accionfirma'] = action

                    template = get_template("pro_becadocente/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'revisarinforme':
                try:
                    data['title'] = u'Revisar Informe de Factibilidad de Otorgamiento de Beca'
                    data['informe'] = informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitud'] = informe.solicitud

                    estados = []
                    estados.append({"id": 3, "descripcion": "REVISADO"})
                    estados.append({"id": 5, "descripcion": "NOVEDADES"})
                    data['estados'] = estados

                    template = get_template("pro_becadocente/revisarinforme.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'postulaciones':
                try:
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), '&action=' + action
                    idc, ids = request.GET.get('idc', ''), request.GET.get('id', '')
                    url_vars += '&idc=' + idc

                    data['convocatoria'] = convocatoria = Convocatoria.objects.get(pk=int(encrypt(idc)))

                    if ids:
                        filtro = filtro & (Q(pk=int(encrypt(ids))))
                        url_vars += '&ids=' + ids
                    else:
                        filtro = filtro & (Q(convocatoria=convocatoria) & Q(profesor=profesor))

                    postulaciones = Solicitud.objects.filter(filtro).order_by('-fechasolicitud')

                    existenovedad = postulaciones.filter(estado__valor__in=[4, 6]).exists()

                    paging = MiPaginador(postulaciones, 25)
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
                    data['postulaciones'] = page.object_list
                    data['title'] = u'Mis postulaciones a Becas de Docentes'
                    data['existenovedad'] = existenovedad

                    return render(request, "pro_becadocente/postulaciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'revisarinformefactibilidad':
                try:
                    data['title'] = u'Revisar Informe de factibilidad'
                    postulacion = Solicitud.objects.get(id=int(encrypt(request.GET['id'])))
                    informefactibilidad = InformeFactibilidad.objects.get(solicitud_id=postulacion.id)
                    data['postulacion'] = postulacion
                    data['informefactibilidad'] = informefactibilidad
                    data['action'] = 'revisarinformefactibilidad'
                    template = get_template('pro_becadocente/revisarinformefactibilidad.html')
                    return JsonResponse({"result": 'ok', 'data': template.render(data)})
                    # return render(request, "pro_becadocente/revisarinformefactibilidad.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirinformefirmado':
                try:
                    data['action'] = 'subirinformefirmado'
                    data['postulacion'] = postulacion = Solicitud.objects.get(id=int(encrypt(request.GET['id'])))
                    template = get_template('pro_becadocente/subirinformefirmado.html')
                    return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'firmarinformeotorgamiento':
                try:
                    tipofirma = request.GET['tipofirma']
                    data['informe'] = informe = InformeFactibilidad.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['iddoc'] = informe.id
                    data['tipofirma'] = tipofirma

                    solicitud = informe.solicitud

                    data['title'] = u'Firmar Informe Otorgamiento de Beca'
                    data['idper'] = persona.id   # Persona que valida
                    data['mensaje'] = "Firma de Informe de Otorgamiento de Beca N° <b>{}</b> del docente <b>{}</b> para el programa <b>{}</b>".format(informe.numero, solicitud.profesor.persona.nombre_completo_inverso(), solicitud.programa)
                    data['accionfirma'] = "firmarinformeotorgamiento"

                    template = get_template("pro_becadocente/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'revisarresolucion':
                try:
                    data['title'] = u'Revisar Resolución del Comité Institucional de Becas'
                    data['resolucion'] = resolucion = ResolucionComite.objects.get(pk=int(encrypt(request.GET['id'])))

                    estados = []

                    if resolucion.resultado == 1:
                        estados.append({"id": 1, "descripcion": "RESULTADO ACEPTADO"})
                        estados.append({"id": 2, "descripcion": "NOVEDAD EN RESOLUCIÓN"})
                    else:
                        estados.append({"id": 1, "descripcion": "RESULTADO ACEPTADO"})
                        estados.append({"id": 2, "descripcion": "APELACIÓN DE RESULTADO"})

                    data['estados'] = estados

                    template = get_template("pro_becadocente/revisarresolucion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            return HttpResponseRedirect(request.path)
        else:
            try:
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''

                # if search:
                #     data['s'] = search
                #     filtro = filtro & (Q(nombre__unaccent__icontains=search))
                #     url_vars += '&s=' + search
                convocatorias = Convocatoria.objects.filter(filtro).order_by('-iniciopos', '-finpos')

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
                data['title'] = u'Convocatorias para Becas y/o Ayudas Económicas para Docentes'
                data['enlaceatras'] = "/pro_investigacion?action=convocatorias"

                return render(request, "pro_becadocente/view.html", data)
            except Exception as ex:
                pass
