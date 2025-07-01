# -*- coding: UTF-8 -*-
import json
import io
import os
import zipfile
import pyqrcode
import time
import sys
import random
import xlsxwriter
from datetime import datetime, date, timedelta
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction, connections
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from decorators import secure_module, last_access
from inno.forms import FechaPlanificacionSedeVirtualExamenForm
from settings import SITE_STORAGE, DEBUG
from sga.commonviews import adduserdata
from sga.forms import CapSolicitudNecesidadForm, CapSolicitudNecesidadWriteDraftForm, \
    CapSolicitudNecesidadFacilitadorForm, CapSolicitudNecesidadFirmaElectronicaIndividualForm, \
    CapSolicitudNecesidadRechazarForm, CapSolicitudNecesidadFirmaDocumentoForm
from sga.funciones import log, generar_nombre, tituloinstitucion, lista_correo
from sga.models import CapPeriodoDocente, CapCronogramaNecesidad, CapSolicitudNecesidad, \
    CapSolicitudNecesidadFacilitador, CoordinadorCarrera, AreaConocimientoTitulacion, SubAreaConocimientoTitulacion, \
    SubAreaEspecificaConocimientoTitulacion, Carrera, Persona, CapSolicitudNecesidadSeguimiento, \
    ResponsableCoordinacion, Coordinacion, CUENTAS_CORREOS, Notificacion
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
def view(request):
    global ex
    data = {}
    lista = []
    adduserdata(request, data)
    now = datetime.now()
    persona = request.session['persona']
    periodo = request.session['periodo']
    puede_ingresar = False
    es_director = False
    es_decano = False
    es_evaluacion = False
    grupos = []
    if persona.usuario.is_superuser:
        puede_ingresar = True
        grupos = [1, 2, 3, 4, 5]
    else:
        if persona.grupo_evaluacion():
            puede_ingresar = True
            es_evaluacion = True
            grupos.append(1)
        if persona.es_responsablecoordinacion(periodo):
            # DECANO DE FACULTAD
            puede_ingresar = True
            es_decano = True
            grupos.append(2)
        if persona.es_coordinadorcarrera(periodo):
            # DIRECTOR DE CARRERA
            puede_ingresar = True
            es_director = True
            grupos.append(3)
        if persona.distributivopersona_set.values("id").filter(denominacionpuesto_id__in=[70, 51, 795], estadopuesto_id=1, status=True).exists():
            # TESORERA GENERAL [70, 51]
            # VICERRECTOR ACADEMICO [795]
            puede_ingresar = True
            grupos.append(4)
            grupos.append(5)

    if puede_ingresar is False:
        return HttpResponseRedirect("/?info=Este módulo solo es para uso de la perfeccionamiento académico o autoridades académicas.")

    if request.method == 'POST':
        action = request.POST.get('action', None)
        if not action is None:

            if action == 'createSolicitudNecesidad':
                with transaction.atomic():
                    try:
                        form = CapSolicitudNecesidadForm(request.POST)
                        form.create(periodo, persona)
                        if not form.is_valid():
                            for k, v in form.errors.items():
                                raise NameError(v[0])
                        # if CapSolicitudNecesidad.objects.values("id").filter(periodo=form.cleaned_data['periodo'], carrera=form.cleaned_data['carrera']).exists():
                        #     raise NameError(u"Solicitud de necesidad en la carrera ya registra")
                        eCarrera = form.cleaned_data['carrera']
                        eCoordinacion = eCarrera.coordinacion_set.filter(status=True).first()
                        if not eCoordinacion:
                            raise NameError(u"Carrera no tiene asignado coordinación (facultad)")
                        eCapSolicitudNecesidad = CapSolicitudNecesidad(periodo=form.cleaned_data['periodo'],
                                                                       carrera=form.cleaned_data['carrera'],
                                                                       facultad=eCoordinacion,
                                                                       estado=CapSolicitudNecesidad.Estados.BORRADOR)
                        eCapSolicitudNecesidad.save(request)
                        log(u'Adiciono solicitud de necesidad de capacitación: %s' % eCapSolicitudNecesidad, request, 'add')
                        eCapSolicitudNecesidadSeguimiento = CapSolicitudNecesidadSeguimiento(solicitud=eCapSolicitudNecesidad,
                                                                                             estado=CapSolicitudNecesidad.Estados.BORRADOR)
                        eCapSolicitudNecesidadSeguimiento.save(request)
                        return JsonResponse({"result": True, "id": encrypt(eCapSolicitudNecesidad.pk)})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'addFacilitador':
                with transaction.atomic():
                    try:
                        id = int(encrypt(request.POST.get('id', encrypt('0'))))
                        if id == 0:
                            raise NameError(u"No se encontro solicitud")
                        try:
                            eCapSolicitudNecesidad = CapSolicitudNecesidad.objects.get(pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"No se encontro la solicitud a editar.")
                        form = CapSolicitudNecesidadFacilitadorForm(request.POST)
                        form.construir(request.POST)
                        if not form.is_valid():
                            for k, v in form.errors.items():
                                raise NameError(v[0])
                        if int(form.cleaned_data['tipo']) == 0:
                            raise NameError(u"Debe seleccionar un tipo de facilitador")
                        elif int(form.cleaned_data['tipo']) == 1:
                            if CapSolicitudNecesidadFacilitador.objects.values("id").filter(solicitud=eCapSolicitudNecesidad, facilitador=form.cleaned_data['facilitador']).exists():
                                raise NameError(u"Facilitador ya existe registrado")
                        elif int(form.cleaned_data['tipo']) == 2:
                            if CapSolicitudNecesidadFacilitador.objects.values("id").filter(solicitud=eCapSolicitudNecesidad, otro=form.cleaned_data['otro']).exists():
                                raise NameError(u"Facilitador ya existe registrado")

                        eCapSolicitudNecesidadFacilitador = CapSolicitudNecesidadFacilitador(solicitud=eCapSolicitudNecesidad,
                                                                                             tipo=form.cleaned_data['tipo'],
                                                                                             facilitador=form.cleaned_data['facilitador'] if 'facilitador' in form.cleaned_data else None,
                                                                                             otro=form.cleaned_data['otro'] if 'otro' in form.cleaned_data else None)
                        eCapSolicitudNecesidadFacilitador.save(request)
                        log(u'Adiciono facilitador a la solicitud (%s) de necesidad de capacitación: %s' % (eCapSolicitudNecesidadFacilitador, eCapSolicitudNecesidad), request, 'add')
                        data['eCapSolicitudNecesidad'] = eCapSolicitudNecesidad
                        template = get_template("adm_capacitaciondocente/formulario/listFacilitador.html")
                        return JsonResponse({"result": True, 'html': template.render(data)})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'deleteFacilitador':
                with transaction.atomic():
                    try:
                        id = int(request.POST.get('id', '0'))
                        try:
                            eCapSolicitudNecesidadFacilitador = deleteCapSolicitudNecesidadFacilitador = CapSolicitudNecesidadFacilitador.objects.get(pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"No se encontro la solicitud a eliminar.")
                        eCapSolicitudNecesidadFacilitador.delete()
                        log(u'Elimino facilitador de la solicitud de necesidad de capacitación: %s' % (deleteCapSolicitudNecesidadFacilitador), request, "del")
                        data['eCapSolicitudNecesidad'] = deleteCapSolicitudNecesidadFacilitador.solicitud
                        template = get_template("adm_capacitaciondocente/formulario/listFacilitador.html")
                        return JsonResponse({"result": True, "message": u"Se elimino correctamente el facilitador.", 'html': template.render(data)})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": False, "message": u"Error al eliminar la solicitud."})

            elif action == 'deleteSolicitudNecesidad':
                with transaction.atomic():
                    try:
                        id = int(request.POST.get('id', '0'))
                        try:
                            eCapSolicitudNecesidad = deleteCapSolicitudNecesidad = CapSolicitudNecesidad.objects.get(pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"No se encontro la solicitud a eliminar.")
                        eCapSolicitudNecesidad.delete()
                        log(u'Elimino solicitud de necesidad de capacitación: %s' % (deleteCapSolicitudNecesidad), request, "del")
                        return JsonResponse({"result": True, "message": u"Se elimino correctamente la solicitud."})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": False, "message": u"Error al eliminar la solicitud."})

            elif action == 'saveChangeSolicitudNecesidadWriteDraft':
                with transaction.atomic():
                    try:
                        id = request.POST.get('id', 0)
                        try:
                            eCapSolicitudNecesidad = CapSolicitudNecesidad.objects.get(pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"No existe registro de borrador")
                        form = CapSolicitudNecesidadWriteDraftForm(request.POST)
                        pData = {'periodo': periodo,
                                 'persona': persona,
                                 'data': request.POST}
                        form.write_draft(pData)
                        if not form.is_valid():
                            for k, v in form.errors.items():
                                raise NameError(v[0])
                        # if CapSolicitudNecesidad.objects.values("id").filter(periodo=eCapSolicitudNecesidad.periodo, carrera=form.cleaned_data['carrera']).exclude(pk=eCapSolicitudNecesidad.pk).exists():
                        #     raise NameError(u"Solicitud de necesidad en la carrera ya registra")
                        eCarrera = form.cleaned_data['carrera']
                        eCoordinacion = eCarrera.coordinacion_set.filter(status=True).first()
                        if not eCoordinacion:
                            raise NameError(u"Carrera no tiene asignado coordinación (facultad)")
                        desde, hasta = None, None
                        if 'desde' in form.cleaned_data or 'hasta' in form.cleaned_data:
                            if 'desde' in form.cleaned_data:
                                desde = form.cleaned_data['desde']
                            if 'hasta' in form.cleaned_data:
                                hasta = form.cleaned_data['hasta']
                        if desde and hasta:
                            if desde > hasta:
                                raise NameError(u"Fecha seguerida desde debe ser menor hasta la fecha fin del cronograma")

                        eCapSolicitudNecesidad.carrera = form.cleaned_data['carrera']
                        eCapSolicitudNecesidad.facultad = eCoordinacion
                        eCapSolicitudNecesidad.tema = form.cleaned_data['tema']
                        eCapSolicitudNecesidad.area = form.cleaned_data['area'] if 'area' in form.cleaned_data else None
                        eCapSolicitudNecesidad.subarea = form.cleaned_data['subarea'] if 'subarea' in form.cleaned_data else None
                        eCapSolicitudNecesidad.campo_detallado = form.cleaned_data['campo_detallado'] if 'campo_detallado' in form.cleaned_data else None
                        eCapSolicitudNecesidad.justificacion = form.cleaned_data['justificacion']
                        eCapSolicitudNecesidad.objetivo = form.cleaned_data['objetivo']
                        eCapSolicitudNecesidad.contenido = form.cleaned_data['contenido']
                        eCapSolicitudNecesidad.resultado = form.cleaned_data['resultado']
                        eCapSolicitudNecesidad.num_horas_referida = form.cleaned_data['num_horas_referida']
                        eCapSolicitudNecesidad.capacidad_participante = form.cleaned_data['capacidad_participante']
                        eCapSolicitudNecesidad.modalidad = form.cleaned_data['modalidad']
                        eCapSolicitudNecesidad.desde = desde
                        eCapSolicitudNecesidad.hasta = hasta
                        eCapSolicitudNecesidad.save(request)
                        log(u'Edito borrador solicitud de necesidad de capacitación: %s' % eCapSolicitudNecesidad, request, 'edit')
                        return JsonResponse({"result": True, "id": encrypt(eCapSolicitudNecesidad.pk)})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'saveSolicitudNecesidad':
                with transaction.atomic():
                    try:
                        from sga.funcionesxhtml2pdf import convert_html_to_pdf
                        id = request.POST.get('id', 0)
                        try:
                            eCapSolicitudNecesidad = CapSolicitudNecesidad.objects.get(pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"No existe registro de borrador")
                        form = CapSolicitudNecesidadWriteDraftForm(request.POST)
                        pData = {'periodo': periodo,
                                 'persona': persona,
                                 'data': request.POST}
                        form.completo(pData)
                        if not form.is_valid():
                            for k, v in form.errors.items():
                                raise NameError(v[0])
                        # if CapSolicitudNecesidad.objects.values("id").filter(periodo=eCapSolicitudNecesidad.periodo, carrera=form.cleaned_data['carrera']).exclude(pk=eCapSolicitudNecesidad.pk).exists():
                        #     raise NameError(u"Solicitud de necesidad en la carrera ya registra")
                        eCarrera = form.cleaned_data['carrera']
                        eCoordinacion = eCarrera.coordinacion_set.filter(status=True).first()
                        if not eCoordinacion:
                            raise NameError(u"Carrera no tiene asignado coordinación (facultad)")
                        desde, hasta = None, None
                        if 'desde' in form.cleaned_data or 'hasta' in form.cleaned_data:
                            if 'desde' in form.cleaned_data:
                                desde = form.cleaned_data['desde']
                            if 'hasta' in form.cleaned_data:
                                hasta = form.cleaned_data['hasta']
                        if desde and hasta:
                            if desde > hasta:
                                raise NameError(u"Fecha seguerida desde debe ser menor hasta la fecha fin del cronograma")

                        eCapSolicitudNecesidad.carrera = form.cleaned_data['carrera']
                        eCapSolicitudNecesidad.facultad = eCoordinacion
                        eCapSolicitudNecesidad.tema = form.cleaned_data['tema']
                        eCapSolicitudNecesidad.area = form.cleaned_data['area']
                        eCapSolicitudNecesidad.subarea = form.cleaned_data['subarea']
                        eCapSolicitudNecesidad.campo_detallado = form.cleaned_data['campo_detallado']
                        eCapSolicitudNecesidad.justificacion = form.cleaned_data['justificacion']
                        eCapSolicitudNecesidad.objetivo = form.cleaned_data['objetivo']
                        eCapSolicitudNecesidad.contenido = form.cleaned_data['contenido']
                        eCapSolicitudNecesidad.resultado = form.cleaned_data['resultado']
                        eCapSolicitudNecesidad.num_horas_referida = form.cleaned_data['num_horas_referida']
                        eCapSolicitudNecesidad.capacidad_participante = form.cleaned_data['capacidad_participante']
                        eCapSolicitudNecesidad.modalidad = form.cleaned_data['modalidad']
                        eCapSolicitudNecesidad.desde = desde
                        eCapSolicitudNecesidad.hasta = hasta
                        eCapSolicitudNecesidad.borrador = False
                        eCapSolicitudNecesidad.estado = CapSolicitudNecesidad.Estados.LEGALIZAR_DIRECTOR
                        eCapSolicitudNecesidad.save(request)

                        # Generar archivo
                        filename = f"final_solicitud_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(random.randint(1, 10000))}.pdf"
                        filepath = u"capacitacion/docente/solicitud"

                        os.makedirs(os.path.join(SITE_STORAGE, 'media', 'capacitacion', 'docente', 'solicitud', ''), exist_ok=True)
                        os.makedirs(os.path.join(SITE_STORAGE, 'media', 'capacitacion', 'docente', 'solicitud', ''), exist_ok=True)

                        data['eCapSolicitudNecesidad'] = eCapSolicitudNecesidad
                        data['fecha_creacion'] = datetime.now()
                        data['periodo'] = periodo
                        data['pagesize'] = 'A4'
                        if newfile := convert_html_to_pdf('adm_capacitaciondocente/pdf_html/solicitud.html', data, filename, os.path.join(os.path.join(SITE_STORAGE, 'media', filepath, ''))):
                            eCapSolicitudNecesidad.archivo = filepath + '/' + filename
                            eCapSolicitudNecesidad.save(request)
                        eCapSolicitudNecesidadSeguimiento = CapSolicitudNecesidadSeguimiento(solicitud=eCapSolicitudNecesidad,
                                                                                             estado=CapSolicitudNecesidad.Estados.LEGALIZAR_DIRECTOR)
                        eCapSolicitudNecesidadSeguimiento.save(request)
                        log(u'Guardo solicitud de necesidad de capacitación: %s' % eCapSolicitudNecesidad, request, 'edit')
                        return JsonResponse({"result": True, "id": encrypt(eCapSolicitudNecesidad.pk)})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'rechazarSolicitudNecesidad':
                with transaction.atomic():
                    try:
                        id = request.POST.get('id', 0)
                        try:
                            eCapSolicitudNecesidad = CapSolicitudNecesidad.objects.get(pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"No existe registro de solicitud")
                        form = CapSolicitudNecesidadRechazarForm(request.POST)
                        if not form.is_valid():
                            for k, v in form.errors.items():
                                raise NameError(v[0])
                        eCapSolicitudNecesidad.borrador = True
                        eCapSolicitudNecesidad.estado = CapSolicitudNecesidad.Estados.BORRADOR
                        eCapSolicitudNecesidad.archivo = None
                        eCapSolicitudNecesidad.save(request)
                        observacion = form.cleaned_data['observacion']
                        eCapSolicitudNecesidadSeguimiento = CapSolicitudNecesidadSeguimiento(solicitud=eCapSolicitudNecesidad,
                                                                                             estado=CapSolicitudNecesidad.Estados.RECHAZADO,
                                                                                             observacion=observacion)
                        eCapSolicitudNecesidadSeguimiento.save(request)
                        eCapSolicitudNecesidadSeguimiento = CapSolicitudNecesidadSeguimiento(solicitud=eCapSolicitudNecesidad,
                                                                                             estado=CapSolicitudNecesidad.Estados.BORRADOR)
                        eCapSolicitudNecesidadSeguimiento.save(request)
                        log(u'Rechazo solicitud de necesidad de capacitación: %s' % eCapSolicitudNecesidad, request, 'edit')
                        director = eCapSolicitudNecesidad.director_carrera(periodo)
                        if director:
                            eDirector = director.get('persona', None)
                            if eDirector:
                                send_html_mail("Solicitud de identificación de necesidades rechazada",
                                               "adm_capacitaciondocente/emails/solicitud_inc_rechazada.html",
                                               {
                                                   'sistema': u'SGA',
                                                   'persona': eDirector,
                                                   'eCapSolicitudNecesidad': eCapSolicitudNecesidad,
                                                   'observacion': observacion,
                                                   'fecha': datetime.now().date(),
                                                   'hora': datetime.now().time(),
                                                   't': tituloinstitucion()
                                               }, eDirector.lista_emails_interno(), [],
                                               cuenta=CUENTAS_CORREOS[0][1])
                                eNotificacion = Notificacion(titulo="Solicitud de identificación de necesidades rechazada",
                                                             cuerpo=f"Su solicitud de fecha de creación {eCapSolicitudNecesidad.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S')} con el tema {eCapSolicitudNecesidad.tema} fue rechazada",
                                                             destinatario=eDirector,
                                                             url='/adm_capacitaciondocente/formulario',
                                                             content_type=None,
                                                             object_id=None,
                                                             prioridad=1,
                                                             app_label='sga',
                                                             perfil=eDirector.perfilusuario_administrativo(),
                                                             fecha_hora_visible=datetime.now() + timedelta(days=3)
                                                             )
                                eNotificacion.save()
                        return JsonResponse({"result": True, "message": f"Solicitud de necesidad fue rechazada"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'firmaDirectorSolicitudNecesidad':
                with transaction.atomic():
                    try:
                        from sga.funcionesxhtml2pdf import convert_html_to_pdf
                        from django.core.files.base import ContentFile
                        from core.firmar_documentos_ec import JavaFirmaEc
                        from core.firmar_documentos import obtener_posicion_x_y_saltolinea
                        from core.firmar_documentos import firmar
                        id = request.POST.get('id', 0)
                        tipo = request.POST.get('tipo', None)
                        if tipo is None:
                            raise NameError(u"No se pudo identificar el tipo")
                        try:
                            eCapSolicitudNecesidad = CapSolicitudNecesidad.objects.get(pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"No existe registro de borrador")
                        if tipo == 'FirmaEC':
                            certificado = request.FILES.get('firma', None)
                            passfirma = request.POST.get('palabraclave', None)
                            if certificado is None:
                                raise NameError(u"No existe archivo de firma")
                            if passfirma is None:
                                raise NameError(u"No existe ontraseña de archivo de firma")

                            documento_a_firmar = eCapSolicitudNecesidad.archivo
                            name_documento_a_firmar, extension_documento_a_firmar = os.path.splitext(documento_a_firmar.name)
                            extension_certificado = os.path.splitext(certificado.name)[1][1:]
                            bytes_certificado = certificado.read()
                            palabras = None
                            if (director := eCapSolicitudNecesidad.director_carrera(periodo)) is not None:
                                palabras = u"%s" % director['persona'].nombre_titulos3y4()
                            if palabras is None:
                                raise NameError(u"No se encontro ubicación de firma")
                            posx, posy, numpaginafirma = obtener_posicion_x_y_saltolinea(documento_a_firmar.url, palabras)
                            if not posy: raise NameError(f"No se encontró el nombre {palabras} en el archivo del informe, por favor verifique si el nombre de esta persona se encuentra en la sección de firmas.")
                            posx, posy = posx + 30, posy + 10

                            try:
                                datau = JavaFirmaEc(archivo_a_firmar=documento_a_firmar,
                                                    archivo_certificado=bytes_certificado,
                                                    extension_certificado=extension_certificado,
                                                    password_certificado=passfirma,
                                                    page=numpaginafirma,
                                                    reason=f"Legalizar solicitud por director de carrera",
                                                    lx=posx,
                                                    ly=posy).sign_and_get_content_bytes()
                            except Exception as x:
                                datau, datas = firmar(request, passfirma, certificado, documento_a_firmar, numpaginafirma, posx, posy, 150, 45)

                            if not datau:
                                raise NameError(f'Documento con inconsistencia en la firma.')

                            documento_a_firmar = io.BytesIO()
                            documento_a_firmar.write(datau)
                            documento_a_firmar.seek(0)

                            _name = name_documento_a_firmar.__str__().split('/')[-1].replace('.pdf', '') + '_director_signed_.pdf'
                            eCapSolicitudNecesidad.archivo.save(_name, ContentFile(documento_a_firmar.read()))
                        elif tipo == 'uploadDocumento':
                            nfileArchivo = request.FILES.get('documento', None)
                            if nfileArchivo is None:
                                raise NameError(u"Archivo es requerido")
                            if nfileArchivo:
                                extensionDocumento = nfileArchivo._name.split('.')
                                tamDocumento = len(extensionDocumento)
                                exteDocumento = extensionDocumento[tamDocumento - 1]
                                if nfileArchivo.size > 15000000:
                                    raise NameError(u"Archivo de documento, el tamaño del archivo es mayor a 15 Mb.")
                                if not exteDocumento.lower() == 'pdf':
                                    raise NameError(u"Archivo de documento, solo se permiten archivos formato pdf")
                            filename = f"final_solicitud_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(random.randint(1, 10000))}_director_signed_.pdf"
                            nfileArchivo._name = filename
                            eCapSolicitudNecesidad.archivo = nfileArchivo
                        else:
                            raise NameError(u"No se pudo identificar el tipo")
                        eCapSolicitudNecesidad.estado = CapSolicitudNecesidad.Estados.LEGALIZAR_DECANO
                        eCapSolicitudNecesidad.save(request)
                        eCapSolicitudNecesidadSeguimiento = CapSolicitudNecesidadSeguimiento(solicitud=eCapSolicitudNecesidad,
                                                                                             estado=CapSolicitudNecesidad.Estados.FIRMA_DIRECTOR)
                        eCapSolicitudNecesidadSeguimiento.save(request)
                        eCapSolicitudNecesidadSeguimiento = CapSolicitudNecesidadSeguimiento(solicitud=eCapSolicitudNecesidad,
                                                                                             estado=CapSolicitudNecesidad.Estados.LEGALIZAR_DECANO)
                        eCapSolicitudNecesidadSeguimiento.save(request)
                        log(u'Firmo director/a solicitud de necesidad de capacitación: %s' % eCapSolicitudNecesidad, request, 'edit')
                        decano = eCapSolicitudNecesidad.decano_facultad(periodo)
                        if decano:
                            eDecano = decano.get('persona', None)
                            if eDecano:
                                send_html_mail("Solicitud de identificación de necesidades pendiente de legalizar",
                                               "adm_capacitaciondocente/emails/solicitud_pendiente_legalizar.html",
                                               {
                                                   'sistema': u'SGA',
                                                   'persona': eDecano,
                                                   'eCapSolicitudNecesidad': eCapSolicitudNecesidad,
                                                   'fecha': datetime.now().date(),
                                                   'hora': datetime.now().time(),
                                                   't': tituloinstitucion()
                                               }, eDecano.lista_emails_interno(), [],
                                               cuenta=CUENTAS_CORREOS[0][1])
                                eNotificacion = Notificacion(titulo="Solicitud de identificación de necesidades pendiente de legalizar",
                                                             cuerpo=f"Solicitud de fecha de creación {eCapSolicitudNecesidad.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S')} con el tema {eCapSolicitudNecesidad.tema} se encuentra pendiente de legalizar",
                                                             destinatario=eDecano,
                                                             url='/adm_capacitaciondocente/formulario',
                                                             content_type=None,
                                                             object_id=None,
                                                             prioridad=1,
                                                             app_label='sga',
                                                             perfil=eDecano.perfilusuario_administrativo(),
                                                             fecha_hora_visible=datetime.now() + timedelta(days=3)
                                                             )
                                eNotificacion.save()
                        return JsonResponse({"result": True, "message": "Documento firmado correctamente" if tipo == 'FirmaEC' else "Documento subido correctamente", "archivo": eCapSolicitudNecesidad.archivo.url})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'firmaDecanoSolicitudNecesidad':
                with transaction.atomic():
                    try:
                        from sga.funcionesxhtml2pdf import convert_html_to_pdf
                        from django.core.files.base import ContentFile
                        from core.firmar_documentos_ec import JavaFirmaEc
                        from core.firmar_documentos import obtener_posicion_x_y_saltolinea
                        from core.firmar_documentos import firmar
                        id = request.POST.get('id', 0)
                        tipo = request.POST.get('tipo', None)
                        if tipo is None:
                            raise NameError(u"No se pudo identificar el tipo")
                        try:
                            eCapSolicitudNecesidad = CapSolicitudNecesidad.objects.get(pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"No existe registro de borrador")
                        if tipo == 'FirmaEC':
                            certificado = request.FILES.get('firma', None)
                            passfirma = request.POST.get('palabraclave', None)

                            if certificado is None:
                                raise NameError(u"No existe archivo de firma")
                            if passfirma is None:
                                raise NameError(u"No existe ontraseña de archivo de firma")

                            documento_a_firmar = eCapSolicitudNecesidad.archivo
                            name_documento_a_firmar, extension_documento_a_firmar = os.path.splitext(documento_a_firmar.name)
                            extension_certificado = os.path.splitext(certificado.name)[1][1:]
                            bytes_certificado = certificado.read()
                            palabras = None
                            if (decano := eCapSolicitudNecesidad.decano_facultad(periodo)) is not None:
                                palabras = u"%s" % decano['persona'].nombre_titulos3y4()
                            if palabras is None:
                                raise NameError(u"No se encontro ubicación de firma")
                            posx, posy, numpaginafirma = obtener_posicion_x_y_saltolinea(documento_a_firmar.url, palabras)
                            if not posy: raise NameError(f"No se encontró el nombre {palabras} en el archivo del informe, por favor verifique si el nombre de esta persona se encuentra en la sección de firmas.")
                            posx, posy = posx + 30, posy + 10

                            try:
                                datau = JavaFirmaEc(archivo_a_firmar=documento_a_firmar,
                                                    archivo_certificado=bytes_certificado,
                                                    extension_certificado=extension_certificado,
                                                    password_certificado=passfirma,
                                                    page=numpaginafirma,
                                                    reason=f"Legalizar solicitud por decano de la facultad",
                                                    lx=posx,
                                                    ly=posy).sign_and_get_content_bytes()
                            except Exception as x:
                                datau, datas = firmar(request, passfirma, certificado, documento_a_firmar, numpaginafirma, posx, posy, 150, 45)

                            if not datau:
                                raise NameError(f'Documento con inconsistencia en la firma.')

                            documento_a_firmar = io.BytesIO()
                            documento_a_firmar.write(datau)
                            documento_a_firmar.seek(0)

                            _name = name_documento_a_firmar.__str__().split('/')[-1].replace('.pdf', '') + '_decano_signed_.pdf'
                            eCapSolicitudNecesidad.archivo.save(_name, ContentFile(documento_a_firmar.read()))
                        elif tipo == 'uploadDocumento':
                            nfileArchivo = request.FILES.get('documento', None)
                            if nfileArchivo is None:
                                raise NameError(u"Archivo es requerido")
                            if nfileArchivo:
                                extensionDocumento = nfileArchivo._name.split('.')
                                tamDocumento = len(extensionDocumento)
                                exteDocumento = extensionDocumento[tamDocumento - 1]
                                if nfileArchivo.size > 15000000:
                                    raise NameError(u"Archivo de documento, el tamaño del archivo es mayor a 15 Mb.")
                                if not exteDocumento.lower() == 'pdf':
                                    raise NameError(u"Archivo de documento, solo se permiten archivos formato pdf")
                            filename = f"final_solicitud_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(random.randint(1, 10000))}_decano_signed_.pdf"
                            nfileArchivo._name = filename
                            eCapSolicitudNecesidad.archivo = nfileArchivo
                        else:
                            raise NameError(u"No se pudo identificar el tipo")

                        eCapSolicitudNecesidad.estado = CapSolicitudNecesidad.Estados.ENTREGADO
                        eCapSolicitudNecesidad.save(request)
                        eCapSolicitudNecesidadSeguimiento = CapSolicitudNecesidadSeguimiento(solicitud=eCapSolicitudNecesidad,
                                                                                             estado=CapSolicitudNecesidad.Estados.FIRMA_DECANO)
                        eCapSolicitudNecesidadSeguimiento.save(request)
                        eCapSolicitudNecesidadSeguimiento = CapSolicitudNecesidadSeguimiento(solicitud=eCapSolicitudNecesidad,
                                                                                             estado=CapSolicitudNecesidad.Estados.ENTREGADO)
                        eCapSolicitudNecesidadSeguimiento.save(request)
                        log(u'Firmo director/a solicitud de necesidad de capacitación: %s' % eCapSolicitudNecesidad, request, 'edit')
                        for ePersona in Persona.objects.filter(usuario__groups__id__in=[43]).distinct():
                            eNotificacion = Notificacion(titulo="Entrega de solicitud de identificación de necesidades",
                                                         cuerpo=f"Entrega de solicitud de la carrera {eCapSolicitudNecesidad.carrera.nombre} con el tema {eCapSolicitudNecesidad.tema}",
                                                         destinatario=ePersona,
                                                         url='/adm_capacitaciondocente/formulario',
                                                         content_type=None,
                                                         object_id=None,
                                                         prioridad=1,
                                                         app_label='sga',
                                                         perfil=ePersona.perfilusuario_administrativo(),
                                                         fecha_hora_visible=datetime.now() + timedelta(days=3)
                                                         )
                            eNotificacion.save()
                        return JsonResponse({"result": True, "message": "Documento firmado correctamente", "archivo": eCapSolicitudNecesidad.archivo.url})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": False, 'message': str(ex)})

        return JsonResponse({"result": False, 'message': 'Acción no permitida'})
    else:
        action = request.GET.get('action', None)
        if not action is None:
            if action == 'newSolicitud':
                try:
                    data['idForm'] = 'formSolicitudNecesidad'
                    data['action'] = 'createSolicitudNecesidad'
                    form = CapSolicitudNecesidadForm(initial={})
                    form.create(persona=persona, periodo=periodo)
                    data['form'] = form
                    template = get_template("adm_capacitaciondocente/formulario/create.html")
                    return JsonResponse({"result": True, 'html': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'loadFormFacilitador':
                try:
                    data['idForm'] = 'formFacilitador'
                    data['action'] = 'addFacilitador'
                    id = int(encrypt(request.GET.get('id', encrypt('0'))))
                    if id == 0:
                        raise NameError(u"No se encontro solicitud")
                    try:
                        eCapSolicitudNecesidad = CapSolicitudNecesidad.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro la solicitud a editar.")
                    data['eCapSolicitudNecesidad'] = eCapSolicitudNecesidad
                    form = CapSolicitudNecesidadFacilitadorForm(initial={})
                    # form.construir(None)
                    data['form'] = form
                    template = get_template("adm_capacitaciondocente/formulario/frmFacilitador.html")
                    return JsonResponse({"result": True, 'html': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'loadFormRechazar':
                try:
                    data['idForm'] = 'formRechazar'
                    data['action'] = 'rechazarSolicitudNecesidad'
                    id = int(encrypt(request.GET.get('id', encrypt('0'))))
                    if id == 0:
                        raise NameError(u"No se encontro solicitud")
                    try:
                        eCapSolicitudNecesidad = CapSolicitudNecesidad.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro la solicitud a editar.")
                    data['eCapSolicitudNecesidad'] = eCapSolicitudNecesidad
                    form = CapSolicitudNecesidadRechazarForm(initial={})
                    # form.construir(None)
                    data['form'] = form
                    template = get_template("adm_capacitaciondocente/formulario/frmRechazar.html")
                    return JsonResponse({"result": True, 'html': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'searchPersonas':
                try:
                    q = request.GET['q'].upper().strip()
                    filtro = Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)

                    search = q.strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        filtro = filtro & (Q(cedula__icontains=search) |
                                           Q(pasaporte__icontains=search) |
                                           Q(nombres__icontains=search) |
                                           Q(apellido1__icontains=search) |
                                           Q(apellido2__icontains=search))
                    else:
                        filtro = filtro & (Q(nombres__icontains=search) |
                                           Q(apellido1__icontains=ss[0]) &
                                           Q(apellido2__icontains=ss[1]))
                    ePersonas = Persona.objects.filter(filtro).distinct().order_by('apellido1', 'apellido2', 'nombres')[:15]
                    aData = {"results": [{"id": x.id, "name": "({}) - {}".format(x.documento(), x.nombre_completo())} for x in ePersonas]}
                    return JsonResponse({"result": True, 'mensaje': '', 'aData': aData})
                except Exception as ex:
                    return JsonResponse({"result": True, 'mensaje': f'{ex.__str__()}', 'aData': {"results": []}})

            elif action == 'writeDraftSolicitudNecesidad':
                try:
                    id = int(encrypt(request.GET.get('id', encrypt('0'))))
                    if id == 0:
                        raise NameError(u"No se encontro borrador a editar")
                    try:
                        eCapSolicitudNecesidad = CapSolicitudNecesidad.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro la solicitud a editar.")
                    data['eCapSolicitudNecesidad'] = eCapSolicitudNecesidad
                    data['eAreas'] = AreaConocimientoTitulacion.objects.filter(status=True, vigente=True)
                    data['title'] = u'Borrador del registro de identificación de necesidades'
                    data['sub_title'] = eCapSolicitudNecesidad.periodo.nombre
                    filtro = Q(periodo=periodo) & Q(status=True)
                    if not persona.usuario.is_superuser:
                        filtro = filtro & Q(persona=persona)
                    data['eCarreras'] = eCarreras = Carrera.objects.filter(pk__in=CoordinadorCarrera.objects.values_list("carrera__id", flat=True).filter(filtro))
                    data['eModalidades'] = CapSolicitudNecesidad.TypeModalidades.choices
                    return render(request, "adm_capacitaciondocente/formulario/write_draft.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'loadSubArea':
                try:
                    idarea = int(request.GET.get('idarea', '0'))
                    eSubAreaConocimientoTitulaciones = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento_id=idarea, status=True, vigente=True)
                    lista = []
                    for eSubAreaConocimientoTitulacion in eSubAreaConocimientoTitulaciones:
                        lista.append([eSubAreaConocimientoTitulacion.id, eSubAreaConocimientoTitulacion.nombre])
                    return JsonResponse({"result": True, "data": lista})
                except Exception as ex:
                    return JsonResponse({"result": False, "message": u"Error al cargar los datos."})

            elif action == 'loadCampoDetallado':
                try:
                    idsubarea = int(request.GET.get('idsubarea', '0'))
                    eSubAreaEspecificaConocimientoTitulaciones = SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento_id=idsubarea, status=True, vigente=True)
                    lista = []
                    for eSubAreaEspecificaConocimientoTitulacion in eSubAreaEspecificaConocimientoTitulaciones:
                        lista.append([eSubAreaEspecificaConocimientoTitulacion.id, eSubAreaEspecificaConocimientoTitulacion.nombre])
                    return JsonResponse({"result": True, "data": lista})
                except Exception as ex:
                    return JsonResponse({"result": False, "message": u"Error al cargar los datos."})

            elif action == 'loadFormFirma':
                try:
                    id = int(encrypt(request.GET.get('id', encrypt('0'))))
                    action_x = request.GET.get('action_x', None)
                    modal_x = request.GET.get('modal_x', None)
                    if id == 0:
                        raise NameError(u"No se encontro solicitud")
                    if action_x is None:
                        raise NameError(u"No se encontro acción")
                    if modal_x is None:
                        raise NameError(u"No se encontro modal")
                    try:
                        eCapSolicitudNecesidad = CapSolicitudNecesidad.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro la solicitud a editar.")
                    eProfesor = None
                    tipo = ''
                    if action_x == 'firmaDirectorSolicitudNecesidad':
                        director = eCapSolicitudNecesidad.director_carrera(periodo)
                        if director:
                            eProfesor = director.get('profesor', None)
                    elif action_x == 'firmaDecanoSolicitudNecesidad':
                        decano = eCapSolicitudNecesidad.decano_facultad(periodo)
                        if decano:
                            eProfesor = decano.get('profesor', None)
                    if eProfesor is None:
                        raise NameError(u"Cargo no identificado (Profesor)")
                    if not eProfesor.tienetoken:
                        data['form'] = CapSolicitudNecesidadFirmaElectronicaIndividualForm()
                        template = get_template("adm_capacitaciondocente/formulario/firmarDocumento.html")
                        tipo = 'FirmaEC'
                    else:
                        data['form'] = CapSolicitudNecesidadFirmaDocumentoForm()
                        template = get_template("adm_capacitaciondocente/formulario/subirDocumentoFirmado.html")
                        tipo = 'uploadDocumento'
                    data['eCapSolicitudNecesidad'] = eCapSolicitudNecesidad
                    data['modal'] = modal_x
                    data['action'] = action_x
                    return JsonResponse({"result": True, "data": {'html': template.render(data), 'tipo': tipo}})
                except Exception as ex:
                    return JsonResponse({"result": False, "message": u"Error al cargar los datos."})

            elif action == 'loadSeguimientoSolicitud':
                try:
                    id = int(encrypt(request.GET.get('id', encrypt('0'))))
                    if id == 0:
                        raise NameError(u"No se encontro solicitud")
                    try:
                        eCapSolicitudNecesidad = CapSolicitudNecesidad.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro la solicitud a editar.")
                    data['eCapSolicitudNecesidad'] = eCapSolicitudNecesidad
                    template = get_template("adm_capacitaciondocente/formulario/viewSeguimiento.html")
                    return JsonResponse({"result": True, "data": template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "message": u"Error al cargar los datos."})

            elif action == 'generateReporteCapacitaciones':
                try:
                    import xlwt
                    import html
                    from django.utils.safestring import mark_safe
                    __author__ = 'Unemi'
                    style0 = xlwt.easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = xlwt.easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = xlwt.easyxf('font: name Times New Roman, color-index blue, bold on')
                    style1 = xlwt.easyxf(num_format_str='D-MMM-YY')
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    font_style2 = xlwt.XFStyle()
                    font_style2.font.bold = False
                    wb = xlwt.Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Reporte')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Lista_Identificacion_Necesidades_Capacitaciones_' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"FACULTAD", 2000),
                        (u"CARRERA", 5000),
                        (u"CURSO", 10000),
                        (u"CANT. PARTICIPANTES", 10000),
                        (u"FACILITADOR", 10000),
                        (u"FECHA INICIO", 10000),
                        (u"FECHA FIN", 10000),
                        (u"URL", 16000)
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    pid = int(request.GET.get('pid', '0'))
                    filtro = Q(status=True) & Q(periodo_id=pid)
                    if not persona.usuario.is_superuser:
                        if es_director:
                            eCarrera_ids = CoordinadorCarrera.objects.values_list("carrera__id", flat=True).filter(persona=persona, periodo=periodo, tipo=3, status=True)
                            filtro = filtro & Q(carrera_id__in=eCarrera_ids)
                        elif es_decano:
                            eResponsables = ResponsableCoordinacion.objects.values_list("coordinacion__id", flat=True).filter(persona=persona, periodo=periodo, tipo=1)
                            filtro = filtro & Q(facultad_id__in=eResponsables)
                        elif es_evaluacion:
                            filtro = filtro & Q(estado__in=[CapSolicitudNecesidad.Estados.ENTREGADO])
                    coid = int(request.GET.get('coid', '0'))
                    caid = int(request.GET.get('caid', '0'))
                    if coid != 0:
                        filtro = filtro & Q(facultad_id=coid)
                        if caid != 0:
                            filtro = filtro & Q(carrera_id=caid)
                    listado = CapSolicitudNecesidad.objects.filter(filtro)
                    row_num = 1
                    i = 0
                    for index, dato in enumerate(listado):
                        facilitadores = []
                        for facilitador in dato.facilitadores():
                            facilitadores.append(facilitador['nombre'])
                        facilitador_display = ', '.join(facilitadores) if len(facilitadores) else ''
                        campo0 = dato.facultad.nombre
                        campo1 = dato.carrera.nombre
                        campo2 = html.unescape(dato.tema) if dato.tema else ''
                        campo3 = dato.capacidad_participante
                        campo4 = facilitador_display
                        campo5 = dato.desde
                        campo6 = dato.hasta
                        campo7 = f"https://sga.unemi.edu.ec{dato.archivo.url}" if dato.archivo else ''
                        ws.write(row_num, 0, campo0, font_style2)
                        ws.write(row_num, 1, campo1, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, campo3, font_style2)
                        ws.write(row_num, 4, campo4, font_style2)
                        ws.write(row_num, 5, campo5, date_format)
                        ws.write(row_num, 6, campo6, date_format)
                        ws.write(row_num, 7, campo7, font_style2)
                        row_num += 1

                    wb.save(response)
                    return response
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'generateZIPCapacitaciones':
                try:
                    pid = int(request.GET.get('pid', '0'))
                    filtro = Q(status=True) & Q(periodo_id=pid)
                    if not persona.usuario.is_superuser:
                        if es_director:
                            eCarrera_ids = CoordinadorCarrera.objects.values_list("carrera__id", flat=True).filter(persona=persona, periodo=periodo, tipo=3, status=True)
                            filtro = filtro & Q(carrera_id__in=eCarrera_ids)
                        elif es_decano:
                            eResponsables = ResponsableCoordinacion.objects.values_list("coordinacion__id", flat=True).filter(persona=persona, periodo=periodo, tipo=1)
                            filtro = filtro & Q(facultad_id__in=eResponsables)
                        elif es_evaluacion:
                            filtro = filtro & Q(estado__in=[CapSolicitudNecesidad.Estados.ENTREGADO])
                    coid = int(request.GET.get('coid', '0'))
                    caid = int(request.GET.get('caid', '0'))
                    if coid != 0:
                        filtro = filtro & Q(facultad_id=coid)
                        if caid != 0:
                            filtro = filtro & Q(carrera_id=caid)
                    eCapSolicitudNecesidades = CapSolicitudNecesidad.objects.filter(filtro)

                    # dominiosistema = request.build_absolute_uri('/')[:-1].strip("/")
                    os.makedirs(os.path.join(SITE_STORAGE, 'media', 'capacitacion', 'zip', ''), exist_ok=True)
                    url = os.path.join(SITE_STORAGE, 'media', 'capacitacion', 'zip', 'solicitudes.zip')
                    url_zip = url
                    fantasy_zip = zipfile.ZipFile(url, 'w')

                    if not eCapSolicitudNecesidades.values("id").exists():
                        raise NameError('No existe archivo a descargar')
                    for eCoordinacion in Coordinacion.objects.filter(pk__in=eCapSolicitudNecesidades.values_list('facultad__id', flat=True)):
                        folder = f"{eCoordinacion.alias}/"
                        for eCarrera in Carrera.objects.filter(pk__in=eCapSolicitudNecesidades.values_list('carrera__id', flat=True).filter(facultad=eCoordinacion)):
                            folder = folder + f"{eCarrera.nombre}/"
                            for eCapSolicitudNecesidad in eCapSolicitudNecesidades.filter(facultad=eCoordinacion, carrera=eCarrera):
                                if eCapSolicitudNecesidad.archivo:
                                    # Agregar el archivo PDF a la carpeta dentro del ZIP
                                    fantasy_zip.write(eCapSolicitudNecesidad.archivo.path, folder + os.path.basename(eCapSolicitudNecesidad.archivo.path))
                            # fantasy_zip.write(ins.rutapdf.path)
                    fantasy_zip.close()
                    response = HttpResponse(open(url_zip, 'rb'), content_type='application/zip')
                    response['Content-Disposition'] = 'attachment; filename=solicitudes.zip'
                    return response
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")
        else:
            try:
                data['title'] = u'Registro de identificación de necesidades'
                data['sub_title'] = u'Gestionar formulario de registro de identificación de necesidades'
                data['eCapPeriodoDocentes'] = eCapPeriodoDocentes = CapPeriodoDocente.objects.filter(status=True, utilizacronograma=True).order_by('fechainicio')
                data['eCapPeriodoDocente'] = eCapPeriodoDocentes.filter(fechainicio__year__gt=now.year).order_by('fechainicio').first()
                data['eCoordinaciones'] = eCoordinaciones = Coordinacion.objects.filter(sede_id=1, pk__in=[1, 2, 3, 4, 5])
                data['es_director'] = es_director
                data['es_decano'] = es_decano
                data['es_evaluacion'] = es_evaluacion
                data['pid'] = pid = int(request.GET.get('pid', '0'))
                data['coid'] = coid = int(request.GET.get('coid', '0'))
                data['caid'] = caid = int(request.GET.get('caid', '0'))
                data['s'] = s = request.GET.get('s', '')
                filtro = Q(status=True)
                if pid != 0:
                    filtro = filtro & Q(periodo_id=pid)
                    data['eCapPeriodoDocente'] = eCapPeriodoDocentes.filter(pk=pid).order_by('fechainicio').first()
                if coid != 0:
                    filtro = filtro & Q(facultad_id=coid)
                    data['eCarreras'] = Carrera.objects.filter(pk__in=eCoordinaciones.values_list('carrera__id', flat=True).filter(pk=coid))
                    if caid != 0:
                        filtro = filtro & Q(carrera_id=caid)
                if not persona.usuario.is_superuser:
                    if es_decano:
                        eResponsables = ResponsableCoordinacion.objects.values_list("coordinacion__id", flat=True).filter(persona=persona, periodo=periodo, tipo=1)
                        filtro = filtro & Q(facultad_id__in=eResponsables)
                    elif es_director:
                        eCarrera_ids = CoordinadorCarrera.objects.values_list("carrera__id", flat=True).filter(persona=persona, periodo=periodo, tipo=3, status=True)
                        filtro = filtro & Q(carrera_id__in=eCarrera_ids)
                    elif es_evaluacion:
                        filtro = filtro & Q(estado__in=[CapSolicitudNecesidad.Estados.ENTREGADO,
                                                        CapSolicitudNecesidad.Estados.LEGALIZAR_DECANO,
                                                        CapSolicitudNecesidad.Estados.LEGALIZAR_DIRECTOR,
                                                        CapSolicitudNecesidad.Estados.FIRMA_DECANO,
                                                        CapSolicitudNecesidad.Estados.FIRMA_DIRECTOR,
                                                        CapSolicitudNecesidad.Estados.RECHAZADO
                                                        ])
                    else:
                        filtro = filtro & Q(id=0)
                if s:
                    filtro = filtro & Q(Q(tema__icontains=s) | Q(carrera__nombre__icontains=s) | Q(facultad__nombre__icontains=s) | Q(justificacion__icontains=s) | Q(objetivo__icontains=s))
                data['eCapSolicitudNecesidades'] = CapSolicitudNecesidad.objects.filter(filtro)
                data['horasegundo'] = now.strftime('%Y%m%d_%H%M%S')
                return render(request, "adm_capacitaciondocente/formulario/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f"/?info={ex.__str__()}")