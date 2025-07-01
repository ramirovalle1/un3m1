# -*- coding: UTF-8 -*-
import io
import random
import sys

import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
import xlwt
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Context
from django.template.loader import get_template
from xlwt import *
from django.shortcuts import render, redirect

from core.firmar_documentos import obtener_posicion_x_y_saltolinea
from core.firmar_documentos_ec import JavaFirmaEc
from decorators import secure_module
from sagest.models import Departamento, SeccionDepartamento, OpcionSistema, BitacoraActividadDiaria
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funcionesxhtml2pdf import conviert_html_to_pdf_name_bitacora
from sga.templatetags.sga_extras import encrypt
from .adm_solicitudpago import registroHistorial, validarDiasSolicitud
from .forms import PerfilPuestoDipForm, RequisitoPagoDipForm, ReemplazarDocumentoRequisitoSolicitudForm, \
    SolicitudPagoForm, BitacoraActividadDiariaFixedForm, RequisitoPagoSolicitudForm
from sga.funciones import MiPaginador, log, generar_nombre, remover_caracteres_especiales_unicode, notificacion, \
    remover_caracteres_tildes_unicode, convertir_fecha_invertida
from sga.models import Administrativo, Persona, ProfesorMateria, CuentaBancariaPersona
from .models import *
from django.db.models import Sum, Q, F, FloatField
from django.db.models.functions import Coalesce
import fitz.utils

@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    # if not perfilprincipal.es_profesor():
    #     return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    data['profesor'] = profesor = perfilprincipal.profesor
    periodo = request.session['periodo']
    profesor = perfilprincipal.profesor

    if request.method == 'POST':
        res_json = []
        action = request.POST['action']

        if action == 'solicitarpago':
            try:
                with transaction.atomic():
                    # idcontrato = request.POST['idcontrato']
                    idcuota = request.POST['idcuota']
                    # contrato = ContratoDip.objects.get(pk=idcontrato)
                    cuotapago = ContratoDipMetodoPago.objects.get(id=idcuota)
                    procesop = ProcesoPago.objects.filter(status=True, mostrar=True)
                    if procesop.exists():
                        procesop = procesop.first()
                        if SolicitudPago.objects.filter(persona=persona, cuotapago=cuotapago, status=True).exists():
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Ya existe una solicitud con esta asignatura."}, safe=False)
                        if procesop.traer_pasos() == 0:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Proceso no tiene pasos configurado."}, safe=False)
                        if PasoProcesoPago.objects.filter(status=True, proceso=procesop, valida__isnull=True).exists():
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Uno de los pasos no tiene puesto validador."}, safe=False)
                        secuencia = SolicitudPago.objects.filter(persona=persona, status=True).count() + 1
                        codigo_secuencia = "pdip_{}".format(secuencia)
                        soli = SolicitudPago(persona=persona, cuotapago=cuotapago, proceso=procesop, numero=secuencia)
                        soli.save(request)
                        for paso in procesop.traer_pasos():
                            ps = PasoSolicitudPagos(solicitud=soli, paso=paso, fecha=datetime.now())
                            ps.save(request)
                            for rp in paso.requisitos():
                                reqpago = RequisitoPasoSolicitudPagos(paso=ps, requisito=rp.requisito)
                                reqpago.save(request)
                        #TIEMPOALERTA
                        paso = soli.paso_principal_validado()
                        fechaactual, fechalimite = datetime.now(), datetime.now()
                        validar = validarDiasSolicitud(request, fechaactual, data)
                        if validar['result']:
                            dias, horas = validar['dias'], paso.paso.tiempoalerta_carga
                            fechalimite = fechaactual + timedelta(days=dias) + timedelta(hours=paso.paso.tiempoalerta_carga)
                        registroHistorial(request, soli, paso, 0, persona, 'GENERO SOLICITUD', 0, fechaactual)
                        pasoanterior = soli.traer_ultimo_historial()
                        pasoanterior.estado = 3
                        pasoanterior.fecha_ejecucion = datetime.now()
                        pasoanterior.persona_ejecucion = persona
                        pasoanterior.save(request)
                        registroHistorial(request, paso.solicitud, paso, 2, persona, paso.paso.descripcion, 1, fechalimite)
                        log(u'Genero Solicitud: %s' % soli, request, "add")
                        idsolicitud = encrypt(soli.pk)
                        return JsonResponse({"result": False, 'to': '{}?action=addsolicitud&pk={}'.format(request.path, idsolicitud)}, safe=False)
                    else:
                        return JsonResponse({"result": True, "mensaje": "No existen procesos de pago activos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'addsolicitud':
            try:
                with transaction.atomic():
                    id, pasoid = request.POST['id'], request.POST['pasoid']
                    solicitud = SolicitudPago.objects.get(pk=id)
                    form = SolicitudPagoForm(request.POST)
                    if form.is_valid():
                        solicitud.cuentabancaria = form.cleaned_data['cuentabancaria']
                        solicitud.estado = 2
                        solicitud.save(request)
                        paso = PasoSolicitudPagos.objects.get(pk=pasoid)
                        for dr in paso.requisito_paso():
                            if 'doc_{}'.format(dr.pk) in request.FILES:
                                newfile = request.FILES['doc_{}'.format(dr.pk)]
                                extension = newfile._name.split('.')
                                tam = len(extension)
                                exte = extension[tam - 1]
                                if newfile.size > 15194304:
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                                if not exte.lower() in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                                nombre_persona = remover_caracteres_especiales_unicode(persona.apellido1).lower().replace(' ', '_')
                                newfile._name = generar_nombre("{}__{}".format(nombre_persona, dr.requisito.nombre_input()), newfile._name)
                                dr.archivo = newfile
                                dr.save(request)
                            else:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": True, "mensaje": "Suba todo los requisitos, {}.".format(dr.requisito.nombre)}, safe=False)
                        pasoanterior = solicitud.traer_ultimo_historial()
                        pasoanterior.estado = 3
                        pasoanterior.fecha_ejecucion = datetime.now()
                        pasoanterior.persona_ejecucion = persona
                        pasoanterior.save(request)
                        fechaactual, fechalimite = datetime.now(), datetime.now()
                        validar = validarDiasSolicitud(request, fechaactual, data)
                        if validar['result']:
                            dias, horas = validar['dias'], paso.paso.tiempoalerta_validacion
                            fechalimite = fechaactual + timedelta(days=dias) + timedelta(hours=paso.paso.tiempoalerta_validacion)
                        registroHistorial(request, paso.solicitud, paso, 2, persona, paso.paso.descripcion, 2, fechalimite)
                        paso.estado = 2
                        paso.save(request)
                        log(u'Adiciono Archivos Solicitud Pago: %s' % solicitud, request, "add")
                        respmensaje = 'Solicitud registrada con éxito, sus datos serán validados en un lapso de {} horas.'.format(paso.paso.tiempoalerta_validacion)
                        return JsonResponse({"result": False, 'modalsuccess': True, 'mensaje': respmensaje, 'to': '{}?action=verproceso&id={}'.format(request.path, encrypt(solicitud.pk))}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. {}".format(str(ex))}, safe=False)

        if action == 'deletesolicitud':
            try:
                with transaction.atomic():
                    instancia = SolicitudPago.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    registroHistorial(request, instancia, None, 5, persona, 'ELIMINO SOLICITUD')
                    log(u'Elimino Solicitud: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'deleterequisitopago':
            try:
                with transaction.atomic():
                    eRequisitoSolicitudPago = RequisitoSolicitudPago.objects.get(pk=int(request.POST['id']))
                    eRequisitoSolicitudPago.status = False
                    eRequisitoSolicitudPago.save(request)
                    log(u'Elimino requisito de pago: %s' % eRequisitoSolicitudPago, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'reemplazardocumento':
            try:
                instance = RequisitoPasoSolicitudPagos.objects.get(id=int(request.POST['id']))
                f = ReemplazarDocumentoRequisitoSolicitudForm(request.POST)
                if f.is_valid():
                    newfile = request.FILES['archivo']
                    extension = newfile._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if newfile.size > 15194304:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                    if not exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                    nombre_persona = remover_caracteres_especiales_unicode(persona.apellido1).lower().replace(' ', '_')
                    newfile._name = generar_nombre("{}__{}".format(nombre_persona, instance.requisito.nombre_input()), newfile._name)
                    instance.archivo = newfile
                    instance.estado = 0
                    instance.save(request)
                    log(u'Documento Requisito Solicitud %s %s' % (instance, instance.paso), request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)})

        if action == 'correcciondocumentos':
            try:
                with transaction.atomic():
                    paso = PasoSolicitudPagos.objects.get(pk=int(request.POST['id']))
                    paso.estado = 2
                    paso.save(request)
                    solicitud = SolicitudPago.objects.get(pk=paso.solicitud.pk)
                    pasoanterior = solicitud.traer_ultimo_historial()
                    pasoanterior.estado = 3
                    pasoanterior.fecha_ejecucion = datetime.now()
                    pasoanterior.persona_ejecucion = persona
                    pasoanterior.save(request)
                    fechaactual, fechalimite = datetime.now(), datetime.now()
                    validar = validarDiasSolicitud(request, fechaactual, data)
                    if validar['result']:
                        dias, horas = validar['dias'], paso.paso.tiempoalerta_validacion
                        fechalimite = fechaactual + timedelta(days=dias) + timedelta(hours=paso.paso.tiempoalerta_validacion)
                    registroHistorial(request, paso.solicitud, paso, 2, persona, paso.paso.descripcion, 2, fechalimite)
                    res_json = {"error": False, "mensaje": "Confirmación de corrección de requisitos, su solicitud sera validada en un lapso {} de horas".format(paso.paso.tiempoalerta_validacion)}
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'informe-administrativo-posgrado':
            try:
                data['hoy'] = hoy = datetime.now()
                id = request.POST.get('contrato_posgrado', None)
                certificado = request.FILES["firma"]
                contrasenaCertificado = request.POST['palabraclave']
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()

                reg = HistorialProcesoSolicitud.objects.get(status=True, id=int(encrypt(id)))
                requi = reg.requisito
                if HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona,requisito=reg.requisito,estado__in =[0,1,2,3,4,7]):
                    hist_ = HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona, requisito=reg.requisito).order_by('-id').first()
                    hist_.fecha_ejecucion = hoy
                else:
                    hist_ = HistorialProcesoSolicitud(
                        observacion=f'Informe firmado por {persona.__str__()}',
                        fecha_ejecucion=hoy,
                        persona_ejecucion=persona,
                        requisito=requi,
                        estado=0
                    )
                    hist_.save(request)
                palabras = f'{persona}'
                x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(reg.archivo.url, palabras)
                datau = JavaFirmaEc(
                    archivo_a_firmar=reg.archivo, archivo_certificado=bytes_certificado,
                    extension_certificado=extension_certificado,
                    password_certificado=contrasenaCertificado,
                    page=int(numpaginafirma), reason='', lx=x + 50, ly=y + 20
                ).sign_and_get_content_bytes()
                documento_a_firmar = io.BytesIO()
                documento_a_firmar.write(datau)
                documento_a_firmar.seek(0)
                hist_.archivo.save(f'{reg.archivo.name.split("/")[-1].replace(".pdf", "")}_firmado.pdf', ContentFile(documento_a_firmar.read()))
                requi.estado = 0
                requi.save(request)
                persona_notificacion = None
                redirect_mod = f'/adm_solicitudpago'
                estado_solicitud = 6
                requisito = hist_.requisito
                solicitud = requisito.solicitud
                contrato = solicitud.contrato
                if contrato.validadorgp:
                    persona_notificacion = contrato.validadorgp
                    redirect_mod = f'/adm_solicitudpago?action=viewinformesmen'
                    estado_solicitud = 3
                else:
                    persona_notificacion = contrato.gestion.responsable
                solicitud.estado = estado_solicitud
                solicitud.save(request)
                cuerpo = f"Informe mensual de posgrado generado y firmado por {persona}"
                obshisto = HistorialObseracionSolicitudPago(
                    solicitud=solicitud,
                    observacion=cuerpo,
                    persona=persona,
                    estado=estado_solicitud,
                    fecha=hoy
                )
                obshisto.save(request)
                notificacion("Solicitud de pago de %s para validación del informe mensual de posgrado" % hist_.requisito.solicitud.contrato.persona,cuerpo, persona_notificacion, None, redirect_mod,hist_.id, 1, 'sga', hist_, request)
                log(f'Firmo el informe mensual de la solicitud: {solicitud}',request,'change')
                res_json = {"result": False}
            except Exception as ex:
                err_ = f"Ocurrio un error: {ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"
                transaction.set_rollback(True)
                res_json = {"result": True, "mensaje": err_}
            return JsonResponse(res_json)

        elif action == 'informe-administrativo-posgrado-solo-firmado':
            try:
                data['hoy'] = hoy = datetime.now()
                id = request.POST.get('contrato_posgrado', None)
                certificado = request.FILES["firma"]
                contrasenaCertificado = request.POST['palabraclave']
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()

                reg = HistorialProcesoSolicitud.objects.get(status=True, id=int(encrypt(id)))
                requi = reg.requisito
                if HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona,requisito=reg.requisito,estado__in =[0,1,2,3,4,7]):
                    hist_ = HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona, requisito=reg.requisito).order_by('-id').first()
                    hist_.fecha_ejecucion = hoy
                else:
                    hist_ = HistorialProcesoSolicitud(
                        observacion=f'Informe firmado por {persona.__str__()}',
                        fecha_ejecucion=hoy,
                        persona_ejecucion=persona,
                        requisito=requi,
                        estado=0
                    )
                    hist_.save(request)
                palabras = f'{persona}'
                x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(reg.archivo.url, palabras)
                datau = JavaFirmaEc(
                    archivo_a_firmar=reg.archivo, archivo_certificado=bytes_certificado,
                    extension_certificado=extension_certificado,
                    password_certificado=contrasenaCertificado,
                    page=int(numpaginafirma), reason='', lx=x + 50, ly=y + 20
                ).sign_and_get_content_bytes()
                documento_a_firmar = io.BytesIO()
                documento_a_firmar.write(datau)
                documento_a_firmar.seek(0)
                hist_.archivo.save(f'{reg.archivo.name.split("/")[-1].replace(".pdf", "")}_firmado.pdf', ContentFile(documento_a_firmar.read()))
                requi.estado = 0
                requi.save(request)
                persona_notificacion = None
                redirect_mod = f'/adm_solicitudpago'

                requisito = hist_.requisito
                requisito.estado = 9#informe de actividad a estado firmado por profesional
                requisito.save(request)
                solicitud = requisito.solicitud
                contrato = solicitud.contrato

                cuerpo = f"Informe mensual de posgrado generado y firmado por {persona}"
                obshisto = HistorialObseracionSolicitudPago(
                    solicitud=solicitud,
                    observacion=cuerpo,
                    persona=persona,
                    estado=0,
                    fecha=hoy
                )
                obshisto.save(request)
                    # notificacion("Solicitud de pago de %s para validación del informe mensual de posgrado" % hist_.requisito.solicitud.contrato.persona,cuerpo, persona_notificacion, None, redirect_mod,hist_.id, 1, 'sga', hist_, request)
                log(f'Firmo el informe mensual de la solicitud: {solicitud}',request,'change')
                res_json = {"result": False}
            except Exception as ex:
                err_ = f"Ocurrio un error: {ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"
                transaction.set_rollback(True)
                res_json = {"result": True, "mensaje": err_}
            return JsonResponse(res_json)

        elif action == 'informe-administrativo-posgrado-solo-firmado-externo':
            try:
                data['hoy'] = hoy = datetime.now()
                id = request.POST.get('contrato_posgrado', None)
                certificado = request.FILES["file_input_archivo_firmado"]
                reg = HistorialProcesoSolicitud.objects.get(status=True, id=int(encrypt(id)))
                requi = reg.requisito
                if HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona,requisito=reg.requisito,estado__in =[0,1,2,3,4,7]):
                    hist_ = HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona, requisito=reg.requisito).order_by('-id').first()
                    hist_.fecha_ejecucion = hoy
                else:
                    hist_ = HistorialProcesoSolicitud(
                        observacion=f'Informe firmado por {persona.__str__()}',
                        fecha_ejecucion=hoy,
                        persona_ejecucion=persona,
                        requisito=requi,
                        estado=0
                    )
                    hist_.save(request)

                hist_.archivo = certificado
                hist_.save(request)
                requi.estado = 0
                requi.save(request)
                persona_notificacion = None
                redirect_mod = f'/adm_solicitudpago'
                requisito = hist_.requisito
                requisito.estado = 9#informe de actividad a estado firmado por profesional
                requisito.save(request)
                solicitud = requisito.solicitud
                contrato = solicitud.contrato
                cuerpo = f"Informe mensual de posgrado generado y firmado por {persona}"
                obshisto = HistorialObseracionSolicitudPago(
                    solicitud=solicitud,
                    observacion=cuerpo,
                    persona=persona,
                    estado=0,
                    fecha=hoy
                )
                obshisto.save(request)
                log(f'Firmo el informe mensual de la solicitud: {solicitud}',request,'change')
                res_json = {"result": False}
            except Exception as ex:
                err_ = f"Ocurrio un error: {ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"
                transaction.set_rollback(True)
                res_json = {"result": True, "mensaje": err_}
            return JsonResponse(res_json)

        elif action == 'generarinformeposgrado':
            try:
                data['hoy'] = hoy = datetime.now()
                id = request.POST.get('id', None)
                reg = HistorialProcesoSolicitud.objects.get(status=True, id=int(encrypt(id)))
                solicitud = reg.requisito.solicitud
                contrato = solicitud.contrato
                data['fi'], data['ff'] = solicitud.fechainicio, solicitud.fechaifin
                fecha_actual = solicitud.fechainicio
                fil_bitacora = Q(fecha__date__gte=solicitud.fechainicio.date(), fecha__date__lte=solicitud.fechaifin.date(), persona=persona, status=True)
                actividadesbitacora = BitacoraActividadDiaria.objects.filter(fil_bitacora).order_by('fecha')
                data['fechas'] = [fecha_actual + timedelta(days=d) for d in range((solicitud.fechaifin - solicitud.fechainicio).days + 1)]
                data['responsable'] = u"%s" % contrato.gestion.responsable
                data['contrato'] = contrato
                data['actividades'] = actividadesbitacora
                data['carreras'] = ContratoCarrera.objects.filter(contrato=contrato, status=True)
                data['areasprogramas'] = ContratoAreaPrograma.objects.filter(contrato=contrato, status=True)
                nombresinciales = ''
                nombre = persona.nombres.split()
                if len(nombre) > 1:
                    nombresiniciales = '{}{}'.format(nombre[0][0], nombre[1][0])
                else:
                    nombresiniciales = '{}'.format(nombre[0][0])
                inicialespersona = '{}{}{}'.format(nombresiniciales, persona.apellido1[0], persona.apellido2[0])
                name_file = f'informe_actividad_diaria_{inicialespersona.lower()}_{solicitud.numero}.pdf'
                resp = conviert_html_to_pdf_name_bitacora('th_hojavida/informe_actividad_mensual_administrativo_posgrado.html', {"data": data}, name_file)
                if resp[0]:
                    resp[1].seek(0)
                    fil_content = resp[1].read()
                    resp = ContentFile(fil_content)
                else:
                    return resp[1]
                requisito, hist_ = solicitud.actualizar_informe_de_actividades(request, requisito_id=14,
                                                                            observacion=f'Informe generado por {persona.__str__()}',
                                                                            hoy=hoy, persona=persona,
                                                                            observacion_historial=f'Informe firmado por {persona.__str__()}',
                                                                            name_file=name_file, resp=resp)
                solicitud.estado = 0
                solicitud.save(request)
                log(f'Genero el informe mensual de la solicitud: {solicitud}', request, 'change')
                res_json = {"error": False}
            except Exception as ex:
                err_ = f"Ocurrio un error: {ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"
                transaction.set_rollback(True)
                res_json = {"error": True, "message": err_}
            return JsonResponse(res_json)

        elif action == 'generarinformeposgradocoordinador':
            try:
                data['hoy'] = hoy = datetime.now()
                gender = 'a' if persona.es_mujer() else 'o'
                filtro = Q(persona=persona, status=True)
                mensaje = f"Estimad{gender} %s{gender}, usted no tiene registro de sus actividades en el periodo seleccionado."
                if not periodo.tipo.id in (3,4):
                    res_json = {"error": True, "message": "Debe seleccionar un periodo de posgrados."}
                    return JsonResponse(res_json)
                if not profesor:
                    res_json = {"error": True, "message": "Debe seleccionar perfil de profesor."}
                    return JsonResponse(res_json)
                if not BitacoraActividadDiaria.objects.values('id').filter(filtro).exists():
                    return HttpResponseRedirect(f"/pro_solicitudpago?info={mensaje % 'coordinador'}")

                if not BitacoraActividadDiaria.objects.values('id').filter(filtro).exists():
                    return HttpResponseRedirect(f"/pro_solicitudpago?info={mensaje % 'coordinador'}")


                gender = 'a' if persona.es_mujer() else 'o'
                id = request.POST.get('id', None)
                reg = HistorialProcesoSolicitud.objects.get(status=True, id=int(encrypt(id)))
                requisito = reg.requisito
                requisito.estado = 0
                requisito.save(request)
                solicitud = requisito.solicitud
                solicitud.estado = 0
                solicitud.save(request)
                contrato = solicitud.contrato
                finicio = solicitud.fechainicio
                ffin = solicitud.fechaifin

                filtro = Q(fecha__gte=finicio.date(),fecha__lte=ffin.date(), persona=persona, status=True)
                #
                sec_informe = contrato.secuencia_informe()
                nombresinciales = ''
                nombre = persona.nombres.split()
                if len(nombre) > 1:
                    nombresiniciales = '{}{}'.format(nombre[0][0], nombre[1][0])
                else:
                    nombresiniciales = '{}'.format(nombre[0][0])
                inicialespersona = '{}{}{}'.format(nombresiniciales, persona.apellido1[0],
                                                   persona.apellido2[0])
                name_file = f'informe_actividad_diaria_{inicialespersona.lower()}_{solicitud.numero}.pdf'

                resp = conviert_html_to_pdf_name_bitacora(
                    'adm_criteriosactividadesdocente/informe_actividad_diaria_coordinador_posgrado.html',
                    {"data": profesor.informe_actividades_mensual_coordinador_posgrado(periodo, finicio.strftime("%Y-%m-%d %H:%M:%S"), ffin.strftime("%Y-%m-%d 23:59:59"))},
                    name_file)
                documento = None
                if resp[0]:
                    resp[1].seek(0)
                    fil_content = resp[1].read()
                    documento = ContentFile(fil_content)
                else:
                    return resp[1]
                #

                if HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona,requisito=requisito,estado__in =[0,1,2,3,4,7]):
                    hist_= HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona,requisito=requisito).order_by('-id').first()
                    hist_.fecha_ejecucion=hoy
                else:
                    hist_ = HistorialProcesoSolicitud(
                        observacion=f'Informe coordinador firmado por {persona.__str__()}',
                        fecha_ejecucion=hoy,
                        persona_ejecucion=persona,
                        requisito=requisito
                    )
                hist_.archivo = None
                hist_.save()
                hist_.archivo.save(f'{name_file.replace(".pdf", "")}.pdf', documento)
                hist_.save(request)
                cuerpo = f"Informe mensual coordinador de posgrado generado por {persona}"

                obshisto = HistorialObseracionSolicitudPago(
                    solicitud=solicitud,
                    observacion=cuerpo,
                    persona=persona,
                    estado=0,
                    fecha=hoy
                )
                obshisto.save(request)
                log(f'Genero el informe mensual coordinador de la solicitud: {solicitud}', request, 'change')
                res_json = {"error": False}
            except Exception as ex:
                err_ = f"Ocurrio un error: {ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"
                transaction.set_rollback(True)
                res_json = {"error": True, "message": err_}
            return JsonResponse(res_json)

        elif action == 'editactividad':
            try:
                id = int(encrypt(request.POST.get('id', None)))
                bitacora = BitacoraActividadDiaria.objects.get(status=True, id=id)
                form = BitacoraActividadDiariaFixedForm(request.POST, request.FILES)
                archivo = None
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    ext = arch.name.split('.')[-1]
                    if ext not in ['pdf','jpeg','png','jpg']: raise NameError(f"El formato del archivo no es permitido, debe ser uno de los siguientes: '.pdf','.jpeg','.png','.jpg'")
                    if arch._size >0: raise NameError("El tamaño del archivo excede el límite de 12MB")
                    arch.name = generar_nombre('archivo_bitacora_',arch.name)
                    archivo = arch
                if not form.is_valid():
                    raise NameError(f"{[{k:v[0]} for k,v in form.errors.items()]}")
                bitacora.descripcion = form.cleaned_data['descripcion']
                bitacora.link = form.cleaned_data['link']
                bitacora.tiposistema = form.cleaned_data['tiposistema']
                bitacora.departamento_requiriente = form.cleaned_data['departamento_requiriente']
                if archivo: bitacora.archivo = archivo
                bitacora.corregida = True
                bitacora.save(request)
                log(f"Actualizo bitacora diaria de la revisión: {bitacora}", request, 'change')
                res_js = {'result':False}
            except Exception as ex:
                transaction.set_rollback(True)
                msg_err = f'{ex}({sys.exc_info()[-1].tb_lineno})'
                res_js = {'result':True, 'mensaje':msg_err}
            return JsonResponse(res_js)

        elif action == 'adicionar_requisito_pago':
            try:
                pk = int(request.POST.get('id','0'))
                if pk == 0:
                    raise NameError("Parametro no encontrado")

                eSolicitudPago = SolicitudPago.objects.get(pk=pk)

                form = RequisitoPagoDipForm(request.POST)
                if form.is_valid():
                    requisito = RequisitoSolicitudPago(
                        solicitud=eSolicitudPago,
                        requisito=form.cleaned_data['requisito'],
                        observacion=''
                    )
                    requisito.save(request)
                else:
                    raise NameError(f"{[{k: v[0]} for k, v in form.errors.items()]}")


                res_json = {"result": False}
            except Exception as ex:
                err_ = f"Ocurrio un error: {ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"
                transaction.set_rollback(True)
                res_json = {"result": True, "message": err_}
            return JsonResponse(res_json)

        elif action == 'subirrequisitopago':
            try:
                FACTURA=4
                hoy = datetime.now().date()
                pk = int(request.POST.get('id','0'))
                if pk == 0:
                    raise NameError("Parametro no encontrado")

                eRequisitoSolicitudPago = RequisitoSolicitudPago.objects.get(pk=pk)
                form = RequisitoPagoSolicitudForm(request.POST,request.FILES)
                observacion = 'requisito actualizado'
                archivo = None
                if 'archivo' in request.FILES:
                        arch = request.FILES['archivo']
                        ext = arch.name.split('.')[-1]
                        if ext not in ['pdf','.PDF','PDF','.pdf',]: raise NameError(
                            f"El formato del archivo no es permitido, debe ser uno de los siguientes: '.pdf'")

                        if arch.size > 10485760: raise NameError("El tamaño del archivo excede el límite de 10MB")
                        nombre_req = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode((eRequisitoSolicitudPago.requisito.nombre.__str__()).replace(' ', '_')))
                        arch.name = generar_nombre(f'{nombre_req}', arch.name)
                        hist_ = HistorialProcesoSolicitud(
                            observacion=observacion,
                            fecha_ejecucion=hoy,
                            persona_ejecucion=persona,
                            requisito=eRequisitoSolicitudPago
                        )
                        hist_.archivo= arch
                        hist_.save(request)
                        eRequisitoSolicitudPago.estado = 0
                        eRequisitoSolicitudPago.observacion = observacion
                        eRequisitoSolicitudPago.save(request)
                        if eRequisitoSolicitudPago.requisito.pk == FACTURA:
                            eRequisitoSolicitudPago.solicitud.notificar_factura_subida_por_el_colaborado(request)

                        if eRequisitoSolicitudPago.solicitud.get_detalle_acta_pago():
                            if  not eRequisitoSolicitudPago.solicitud.get_detalle_acta_pago().actapagoposgrado.acta_pago_enviado_epunemi() \
                                    or  eRequisitoSolicitudPago.solicitud.get_detalle_acta_pago().actapagoposgrado.acta_pago_enviado_vip() \
                                    or  eRequisitoSolicitudPago.solicitud.get_detalle_acta_pago().actapagoposgrado.acta_pago_legalizado()\
                                    or  eRequisitoSolicitudPago.solicitud.get_detalle_acta_pago().actapagoposgrado.acta_pago_por_legalizar()\
                                    or  eRequisitoSolicitudPago.solicitud.get_detalle_acta_pago().actapagoposgrado.acta_pago_legalizado():
                                eRequisitoSolicitudPago.solicitud.get_detalle_acta_pago().actapagoposgrado.generar_actualizar_check_list_pago_pdf(request)

                            # eRequisitoSolicitudPagoCheckList = RequisitoSolicitudPago.objects.filter(status=True,requisito_id=16,solicitud = eRequisitoSolicitudPago.solicitud)
                            # if eRequisitoSolicitudPagoCheckList.exists():
                            #     hist_ = HistorialProcesoSolicitud(
                            #         observacion='CHECK LIST ACTUALIZADO AUTOMATICAMENTE',
                            #         fecha_ejecucion=hoy,
                            #         persona_ejecucion=persona,
                            #         requisito=eRequisitoSolicitudPagoCheckList.first()
                            #     )
                            #     hist_.archivo = eRequisitoSolicitudPago.solicitud.generar_documento_pdf_check_list_de_pago_solicitud(request,eRequisitoSolicitudPago.solicitud.contrato.validadorgp)
                            #     hist_.save(request)
                        else:
                            eRequisitoSolicitudPago.solicitud.generar_documento_pdf_check_list_de_pago_solicitud(request,eRequisitoSolicitudPago.solicitud.contrato.validadorgp)
                            eRequisitoSolicitudPagoCheckList = RequisitoSolicitudPago.objects.filter(status=True,
                                                                                                     requisito_id=16,
                                                                                                     solicitud=eRequisitoSolicitudPago.solicitud)
                            if eRequisitoSolicitudPagoCheckList.exists():
                                hist_ = HistorialProcesoSolicitud(
                                    observacion='CHECK LIST ACTUALIZADO AUTOMATICAMENTE',
                                    fecha_ejecucion=hoy,
                                    persona_ejecucion=persona,
                                    requisito=eRequisitoSolicitudPagoCheckList.first()
                                )
                                hist_.archivo = eRequisitoSolicitudPago.solicitud.generar_documento_pdf_check_list_de_pago_solicitud( request, eRequisitoSolicitudPago.solicitud.contrato.validadorgp)
                                hist_.save(request)
                res_json = {"result": False}
            except Exception as ex:
                err_ = f"Ocurrio un error: {ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"
                transaction.set_rollback(True)
                res_json = {"result": True, "message": err_}
            return JsonResponse(res_json)

        elif action == 'enviar_solicitud_de_pago':
            try:
                hoy = datetime.now().date()
                PENDIENTE = 1
                PENDIENTE_G_P = 3
                id = request.POST.get('id', 0)
                redirect_mod = f'/adm_solicitudpago?action=viewinformesmen'
                eSolicitudPago = SolicitudPago.objects.get(pk=id)
                eSolicitudPago.estado = PENDIENTE_G_P
                eSolicitudPago.save(request)
                contrato = eSolicitudPago.contrato
                persona_notificacion = None
                if contrato.validadorgp:
                    persona_notificacion = contrato.validadorgp
                cuerpo = f"Solicitud de pago {persona} posgrado"
                obshisto = HistorialObseracionSolicitudPago(
                    solicitud=eSolicitudPago,
                    observacion=cuerpo,
                    persona=persona,
                    estado=PENDIENTE_G_P,
                    fecha=hoy
                )
                obshisto.save(request)
                notificacion(
                    "Solicitud de pago de %s para validación del informe mensual de posgrado" % contrato.persona,
                    cuerpo, persona_notificacion, None, redirect_mod, contrato.id, 1, 'sga', contrato, request)
                log(u"Solicitud de pago enviada a la gestion de posgrado", request, 'edit')
                return JsonResponse({'result': True})
            except Exception as ex:
                pass

        return JsonResponse({"result": True, "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'solicitarpago':
                try:
                    # idcontratos = SolicitudPago.objects.filter(status=True, persona=persona, contrato__isnull=False).values_list('cuotapago__id', flat=True)
                    # data['miscontratos'] = contratos = ContratoDip.objects.filter(status=True, persona=persona).exclude(id__in=idcontratos).order_by('codigocontrato')
                    data['cuota'] = ContratoDipMetodoPago.objects.get(id=request.GET['id'])
                    template = get_template("pro_solicitudpago/modal/solicitarpago.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addsolicitud':
                data['id'] = id = int(encrypt(request.GET['pk']))
                data['filtro'] = filtro = SolicitudPago.objects.get(pk=id)
                data['title'] = 'REQUISITOS SOLICITUD DE PAGO #{}'.format(filtro.numero)
                form = SolicitudPagoForm()
                form.fields['cuentabancaria'].queryset = CuentaBancariaPersona.objects.filter(status=True, persona=persona).order_by('banco__nombre')
                data['form'] = form
                return render(request, 'pro_solicitudpago/addsolicitud.html', data)

            elif action == 'reemplazardocumento':
                try:
                    data['filtro'] = solicitud = RequisitoPasoSolicitudPagos.objects.get(pk=int(request.GET['id']))
                    form = ReemplazarDocumentoRequisitoSolicitudForm(initial=model_to_dict(solicitud))
                    data['form2'] = form
                    template = get_template("pro_solicitudpago/modal/reemplazardocumento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verproceso':
                id = int(encrypt(request.GET['id']))
                data['filtro'] = filtro = SolicitudPago.objects.get(pk=id)
                data['title'] = 'SOLICITUD DE PAGO #{}'.format(filtro.numero)
                return render(request, 'pro_solicitudpago/verprocesosolicitud.html', data)

            elif action == 'verhistorial':
                try:
                    data['title'] = u'Ver Historial'
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = SolicitudPago.objects.get(pk=int(id))
                    data['detalle'] = HistorialProcesoSolicitud.objects.filter(status=True, solicitud=filtro).order_by('-pk')
                    template = get_template("adm_solicitudpago/modal/verhistorial.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'traercuotas':
                id = request.GET['id']
                url_vars = '&action=traercuotas'
                data['fechaactual'] = datetime.now().date()
                data['contrato'] = contrato = ContratoDip.objects.get(id=encrypt(id))
                query = SolicitudPago.objects.filter(status=True, contrato=contrato)
                paging = MiPaginador(query, 20)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginadorsoli' in request.session:
                        paginasesion = int(request.session['paginadorsoli'])
                    if 'pagesoli' in request.GET:
                        p = int(request.GET['pagesoli'])
                    else:
                        p = paginasesion
                    try:
                        page = paging.page(p)
                    except:
                        p = 1
                    page = paging.page(p)
                except:
                    page = paging.page(p)
                request.session['paginadorsoli'] = p
                data['pagingsoli'] = paging
                data['rangospagingsoli'] = paging.rangos_paginado(p)
                data['pagesoli'] = page
                data['url_varssoli'] = url_vars
                data['listado'] = page.object_list
                template = get_template('pro_solicitudpago/modal/listacuotas.html')
                return JsonResponse({"result": True, 'data': template.render(data)})

            elif action == 'viewrequisitosposgrado':
                try:
                    id = encrypt(request.GET['id'])
                    data['solicitud'] = query = SolicitudPago.objects.get(status=True, id=int(id))
                    data['tiene_observaciones'] = BitacoraActividadDiaria.objects.filter(status=True,corregida=False, observacion__isnull=False,fecha__date__gte=query.fechainicio.date(), fecha__date__lte=query.fechaifin.date(),persona=persona)
                    registro = RequisitoSolicitudPago.objects.filter(status=True,solicitud=query).order_by('orden')
                    data['lista'] = registro
                    template = get_template('pro_solicitudpago/modal/viewrequisitosposgrado.html')
                    res_js={'result':True,'data':template.render(data)}
                except Exception as ex:
                    err_ = f'Ocurrio un error: {ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}'
                    res_js = {'result':False, 'mensaje':err_}
                return JsonResponse(res_js)

            elif action == 'viewhistorialrequisito':
                try:
                    id = encrypt(request.GET['id'])
                    reg = HistorialProcesoSolicitud.objects.filter(status=True,requisito_id=int(id))
                    data['lista'] = reg
                    template = get_template('th_hojavida/informacionlaboral/modal/viewhistoryrequiposgrado.html')
                    res_js = {'result':True,'data':template.render(data)}
                except Exception as ex:
                    err_ = f'Ocurrio un error: {ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}'
                    res_js = {'result':False,'mensaje':err_}
                return JsonResponse(res_js)

            elif action == 'loadhisotryobser':
                try:
                    id = request.GET.get('id', None)
                    hsitobs = HistorialObseracionSolicitudPago.objects.filter(status=True, solicitud_id = int(encrypt(id)))
                    data['listado'] = hsitobs
                    template = get_template('pro_solicitudpago/modal/viewhistoryobservacion.html')
                    res_js = {'result': True, 'data': template.render(data)}
                except Exception as ex:
                    err_ = f'Ocurrio un error: {ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}'
                    res_js = {'result': False, 'mensaje': err_}
                return JsonResponse(res_js)

            elif action == 'viewrevisionactividades':
                try:
                    id = request.GET.get('id', None)
                    data['title'] = 'Corrección de actividades'
                    data['soicitu'] = solicitud = SolicitudPago.objects.get(status=True, id=int(encrypt(id)))
                    data['listado'] = actividades = BitacoraActividadDiaria.objects.filter(status=True, observacion__isnull=False, corregida=False, fecha__date__gte=solicitud.fechainicio.date(), fecha__date__lte=solicitud.fechaifin.date(),persona = persona)
                    return render(request, 'pro_solicitudpago/viewactividades.html', data)
                except Exception as ex:
                    msg_err = f'{ex}({sys.exc_info()[-1].tb_lineno})'
                    print(msg_err)
                    return HttpResponseRedirect(f'{request.path}?info={msg_err}')

            elif action == 'editactividad':
                try:
                    data['id'] = id = int(encrypt(request.GET.get('id', None)))
                    actividad = BitacoraActividadDiaria.objects.get(status=True, id=id)
                    form = BitacoraActividadDiariaFixedForm(initial=model_to_dict(actividad))
                    data['form'] = form
                    template = get_template('pro_solicitudpago/modal/formmodalbitacora.html')
                    res_js = {'result':True, 'data':template.render(data)}
                except Exception as ex:
                    msg_err = f'{ex}({sys.exc_info()[-1].tb_lineno})'
                    res_js = {'result':False,'mensaje':msg_err}
                return JsonResponse(res_js)

            elif action == 'adicionar_requisito_pago':
                try:
                    data['form2'] = form = RequisitoPagoDipForm()
                    data['id'] = int(request.GET.get('id','0'))
                    data['action'] = 'adicionar_requisito_pago'
                    template = get_template('pro_solicitudpago/modal/form_modal.html')
                    res_js = {'result':True, 'data':template.render(data)}
                except Exception as ex:
                    msg_err = f'{ex}({sys.exc_info()[-1].tb_lineno})'
                    res_js = {'result':False,'mensaje':msg_err}
                return JsonResponse(res_js)

            elif action == 'subirrequisitopago':
                try:
                    data['form2'] = form = RequisitoPagoSolicitudForm()
                    data['id'] = int(encrypt(request.GET.get('id','0')))
                    data['action'] = 'subirrequisitopago'
                    template = get_template('pro_solicitudpago/modal/form_modal.html')
                    res_js = {'result':True, 'data':template.render(data)}
                except Exception as ex:
                    msg_err = f'{ex}({sys.exc_info()[-1].tb_lineno})'
                    res_js = {'result':False,'mensaje':msg_err}
                return JsonResponse(res_js)

            elif action == 'solicitudes_pagos':
                try:
                    hoy = datetime.now()
                    id = request.GET['id']
                    url_vars = '&action=solicitudes_pagos'
                    data['fechaactual'] = datetime.now().date()
                    data['contrato'] = contrato = ContratoDip.objects.get(id=encrypt(id))
                    query = SolicitudPago.objects.filter(status=True, contrato=contrato)
                    paging = MiPaginador(query, 20)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginadorsoli' in request.session:
                            paginasesion = int(request.session['paginadorsoli'])
                        if 'pagesoli' in request.GET:
                            p = int(request.GET['pagesoli'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginadorsoli'] = p
                    data['pagingsoli'] = paging
                    data['rangospagingsoli'] = paging.rangos_paginado(p)
                    data['pagesoli'] = page
                    data['url_varssoli'] = url_vars
                    data['listado'] = page.object_list

                    return render(request, "pro_solicitudpago/solicitud_view.html", data)
                except  Exception as ex:
                    pass

            elif action == 'requisitos_solicitudes_pagos':
                try:
                    hoy = datetime.now()
                    id = request.GET['id']
                    data['solicitud'] = query = SolicitudPago.objects.get(status=True, id=int(encrypt(id)))
                    data['es_coordinador'] = SolicitudPago.objects.values('id').filter(Q(id=int(encrypt(id)), status=True) & Q(Q(contrato__cargo__nombre__icontains="COORDINADORA DEL PROGRAMA") | Q(contrato__cargo__nombre__icontains="COORDINADOR DEL PROGRAMA") | Q(contrato__cargo__nombre__icontains="COORDINADOR/A DEL PROGRAMA"))).exists()
                    data['tiene_observaciones'] = BitacoraActividadDiaria.objects.filter(status=True, corregida=False,
                                                                                         observacion__isnull=False,
                                                                                         fecha__date__gte=query.fechainicio.date(),
                                                                                         fecha__date__lte=query.fechaifin.date(),
                                                                                         persona=persona)
                    registro = RequisitoSolicitudPago.objects.filter(status=True, solicitud=query).order_by('orden')
                    data['lista'] = registro

                    url_vars = '&action=requisitos_solicitudes_pagos'
                    data['fechaactual'] = datetime.now().date()
                    data['contrato'] = contrato = query.contrato
                    query = SolicitudPago.objects.filter(status=True, contrato=contrato)
                    paging = MiPaginador(query, 20)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginadorsoli' in request.session:
                            paginasesion = int(request.session['paginadorsoli'])
                        if 'pagesoli' in request.GET:
                            p = int(request.GET['pagesoli'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginadorsoli'] = p
                    data['pagingsoli'] = paging
                    data['rangospagingsoli'] = paging.rangos_paginado(p)
                    data['pagesoli'] = page
                    data['url_varssoli'] = url_vars
                    data['listado'] = page.object_list

                    contratos = ContratoDip.objects.filter(status=True, persona=persona)
                    vigentes = contratos.filter(fechafin__gte=hoy).order_by('codigocontrato')
                    novigentes = contratos.filter(fechafin__lt=hoy).order_by('codigocontrato')

                    pagingn = MiPaginador(novigentes, 20)
                    p = 1
                    try:
                        paginasesionn = 1
                        if 'paginadorn' in request.session:
                            paginasesionn = int(request.session['paginadorn'])
                        if 'page' in request.GET:
                            p = int(request.GET['pagen'])
                            p = int(request.GET['pagen'])
                        else:
                            p = paginasesionn
                        try:
                            pagen = pagingn.page(p)
                        except:
                            p = 1
                        pagen = pagingn.page(p)
                    except:
                        pagen = pagingn.page(p)

                    data['contratos'] = contratos
                    data['novigentes'] = pagen.object_list

                    pagingnvigentes = MiPaginador(vigentes, 20)
                    p = 1
                    try:
                        paginasesionnvigentes = 1
                        if 'paginadornvigentes' in request.session:
                            paginasesionn = int(request.session['paginadornvigentes'])
                        if 'page' in request.GET:
                            p = int(request.GET['pagenvigentes'])
                            p = int(request.GET['pagenvigentes'])
                        else:
                            p = paginasesionnvigentes
                        try:
                            pagenvigentes = pagingnvigentes.page(p)
                        except:
                            p = 1
                        pagenvigentes = pagingnvigentes.page(p)
                    except:
                        pagenvigentes = pagingnvigentes.page(p)
                    data['vigentes'] = pagenvigentes.object_list

                    return render(request, "pro_solicitudpago/requisitossolicitud_view.html", data)



                except  Exception as ex:
                    pass
        else:
            data['title'] = u'Solicitudes de Pagos'
            hoy = datetime.now()
            search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
            if search:
                filtro = filtro & Q(materia__materia__asignatura__nombre__icontains=search)
                url_vars += '&s=' + search
                data['search'] = search
            listado = SolicitudPago.objects.filter(filtro).filter(contrato__persona=persona).order_by('-id')
            data['contratos'] = contratos = ContratoDip.objects.filter(status=True, persona=persona)
            vigentes = contratos.filter(fechafin__gte=hoy).order_by('codigocontrato')
            data['novigentes'] = novigentes = contratos.filter(fechafin__lt=hoy).order_by('codigocontrato')
            paging = MiPaginador(vigentes, 20)
            p = 1
            try:
                paginasesion = 1
                if 'paginador' in request.session:
                    paginasesion = int(request.session['paginador'])
                if 'page' in request.GET:
                    p = int(request.GET['page'])
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
            data["url_vars"] = url_vars
            data['vigentes'] = page.object_list
            #PAGINADOR DE CONTRATOS NO VIGENTES

            pagingn = MiPaginador(novigentes, 20)
            paging = MiPaginador(listado, 20)
            p = 1
            try:
                paginasesionn = 1
                if 'paginadorn' in request.session:
                    paginasesionn = int(request.session['paginadorn'])
                if 'page' in request.GET:
                    p = int(request.GET['pagen'])
                    p = int(request.GET['pagen'])
                else:
                    p = paginasesionn
                try:
                    pagen = pagingn.page(p)
                except:
                    p = 1
                pagen = pagingn.page(p)
            except:
                pagen = pagingn.page(p)
            request.session['paginadorn'] = p
            data['pagingn'] = pagingn
            data['rangospaging'] = pagingn.rangos_paginado(p)
            data['pagen'] = pagen
            data["url_vars"] = url_vars
            data['novigentes'] = pagen.object_list
            data['listado'] = page.object_list
            # data['totcount'] = listado.count()
            data['email_domain'] = EMAIL_DOMAIN
            return render(request, "pro_solicitudpago/view.html", data)


def obtener_posicion_y(urlpdf, palabras):  # posiscion Y, la obtiene correctamente--- posicion X, falta ajustar
    pdf = SITE_STORAGE + urlpdf
    documento = fitz.open(pdf)
    numpaginafirma = int(documento.page_count) - 1
    with fitz.open(pdf) as document:
        words_dict = {}
        for page_number, page in enumerate(document):
            if page_number == numpaginafirma:
                words = page.get_text("blocks")
                words_dict[0] = words
    valor = xx = y = None
    for cadena in words_dict[0]:
        if palabras in cadena[4]:
            valor = cadena
            if valor:
                y = 5000 - int(valor[3]) - 4120
                xx = 5000 - int(valor[1]) - 4565
            return xx, y, numpaginafirma
    return xx, y, numpaginafirma
