import json

import io
import os
import random

import xlsxwriter
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.template.loader import get_template
from django.forms import model_to_dict
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from datetime import datetime,date
from django.template.context import Context
from xlwt import easyxf

from core.firmar_documentos import obtener_posicion_x_y_saltolinea
from core.firmar_documentos_ec import JavaFirmaEc
from decorators import secure_module
from sagest.forms import AccionPersonalForm, AccionPersonalArchivoForm, AccionPersonal2Form, MotivoAccionPersonalForm, \
    MotivoAccionPersonalDetalleForm, BaseLegalAccionPersonalForm, AccionPersonalDocumentoForm
from sagest.funciones import encrypt_id
from sagest.models import AccionPersonal, TipoAccionPersonal, MotivoAccionPersonal, DenominacionPuesto, \
    DistributivoPersona, IndiceSeriePuesto, PermisoInstitucional, MotivoAccionPersonalDetalle, BaseLegalAccionPersonal, \
    RegimenLaboral, PermisoInstitucionalDetalle, HistoricoDocumentosPersonaAcciones, ESTADO_ARCHIVO_FIRMADO
from settings import SITE_STORAGE
from sga.adm_convenioempresa import buscar_dicc
from sga.commonviews import adduserdata
from sga.funciones import log, MiPaginador, generar_nombre, notificacion, remover_caracteres_tildes_unicode, \
    remover_caracteres_especiales_unicode
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdf_name_save, \
    conviert_html_to_pdf_name_saveaccionpersonal
from sga.models import MESES_CHOICES,CUENTAS_CORREOS
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from django.core.files import File as DjangoFile

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                indiceocup = None
                denominacionpuesto = None
                rmu = 0
                escalaocupacional = None
                tipogrado = 0
                nummaximo = 0
                form = AccionPersonalForm(request.POST)
                if form.is_valid():
                    if AccionPersonal.objects.filter(anio=form.cleaned_data['anio']).exists():
                        numeromaximo = AccionPersonal.objects.filter(anio=form.cleaned_data['anio'], status=True).order_by('-numero')[0]
                        nummaximo = numeromaximo.numero
                    if IndiceSeriePuesto.objects.filter(pk=request.POST['denominacionpuesto']).exists():
                        indiceocupacionalpropuesto = IndiceSeriePuesto.objects.get(pk=request.POST['denominacionpuesto'])
                        indiceocup = indiceocupacionalpropuesto.id
                        denominacionpuesto = indiceocupacionalpropuesto.denominacionpuesto.id
                        escalaocupacional = indiceocupacionalpropuesto.escalaocupacional.id
                        tipogrado = indiceocupacionalpropuesto.tipogrado
                        rmu = indiceocupacionalpropuesto.rmu
                    if form.cleaned_data['denominacionpuestoactual']:
                        denominacionpuestoactual = form.cleaned_data['denominacionpuestoactual']
                    else:
                        denominacionpuestoactual = None
                    if form.cleaned_data['numerocaucion']:
                        numerocaucion = form.cleaned_data['numerocaucion']
                    else:
                        numerocaucion = 0
                    if form.cleaned_data['numeroaccion']:
                        numeroaccion = form.cleaned_data['numeroaccion']
                    else:
                        numeroaccion = 0
                    if form.cleaned_data['personareemplaza'] in ['', 0]:
                        personareemplaza = None
                    else:
                        personareemplaza = form.cleaned_data['personareemplaza']
                    accionpersonal = AccionPersonal(persona_id=form.cleaned_data['persona'],
                                                    # subroganterector=form.cleaned_data['subroganterector'],
                                                    # personarector_id=form.cleaned_data['personarector'],
                                                    subroganterrhh=form.cleaned_data['subroganterrhh'],
                                                    personauath_id=form.cleaned_data['personarrhh'],
                                                    personaregistrocontrol_id=form.cleaned_data['personaregistrocontrol'],
                                                    numero=nummaximo + 1,
                                                    anio=form.cleaned_data['anio'],
                                                    abreviatura=form.cleaned_data['abreviatura'],
                                                    fechaelaboracion=form.cleaned_data['fechaelaboracion'],
                                                    tipo=form.cleaned_data['tipo'],
                                                    documento=form.cleaned_data['documento'],
                                                    fechaaprobacion=form.cleaned_data['fechaaprobacion'],
                                                    fechadesde=form.cleaned_data['fechadesde'],
                                                    fechahasta=form.cleaned_data['fechahasta'],
                                                    explicacion=form.cleaned_data['explicacion'],
                                                    regimenlaboral=form.cleaned_data['regimenlaboral'],
                                                    motivo=form.cleaned_data['motivo'],
                                                    departamentoactual=form.cleaned_data['departamentoactual'],
                                                    denominacionpuestoactual_id=denominacionpuestoactual,
                                                    escalaocupacionalactual=form.cleaned_data['escalaocupacionalactual'],
                                                    tipogradoactual=form.cleaned_data['tipogradoactual'],
                                                    lugartrabajoactual=form.cleaned_data['lugartrabajoactual'],
                                                    rmuactual=form.cleaned_data['rmuactual'],
                                                    partidapresupuestariaactual=form.cleaned_data['partidapresupuestariaactual'],
                                                    departamento=form.cleaned_data['departamento'],
                                                    indiceocupacionalpropuesto_id=indiceocup,
                                                    denominacionpuesto_id=denominacionpuesto,
                                                    escalaocupacional_id=escalaocupacional,
                                                    tipogrado=tipogrado,
                                                    lugartrabajo=form.cleaned_data['lugartrabajo'],
                                                    rmu=form.cleaned_data['rmu'],
                                                    partidapresupuestaria=form.cleaned_data['partidapresupuestaria'],
                                                    numeroactafinal=form.cleaned_data['numeroactafinal'],
                                                    fechaactafinal=form.cleaned_data['fechaactafinal'],
                                                    numerocaucion=numerocaucion,
                                                    fechacaucion=form.cleaned_data['fechacaucion'],
                                                    personareemplaza_id=personareemplaza,
                                                    denominacionpuestoreemplazo_id=form.cleaned_data['denominacionpuestoreemplazo'],
                                                    cesofunciones=form.cleaned_data['cesofunciones'],
                                                    numeroaccion=numeroaccion,
                                                    fecharegistroaccion=form.cleaned_data['fecharegistroaccion'],
                                                    colegioprofesionales=form.cleaned_data['colegioprofesionales']
                                                    )
                    accionpersonal.save(request)
                    log(u'Registro accion persona: %s' % accionpersonal, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
        #este add es para la accion de personal de vacaciones
        elif action == 'addv':
            try:
                permiso = PermisoInstitucionalDetalle.objects.get(pk=int(encrypt(request.POST['id'])))
                distributivo = DistributivoPersona.objects.get(persona= permiso.permisoinstitucional.solicita,denominacionpuesto=permiso.permisoinstitucional.denominacionpuesto,regimenlaboral=permiso.permisoinstitucional.regimenlaboral,status=True)
                motivo = MotivoAccionPersonalDetalle.objects.get(motivo=6,regimenlaboral=permiso.permisoinstitucional.regimenlaboral,status=True)
                tipogrado = 0
                nummaximo = 0
                anioactual = datetime.now()
                if AccionPersonal.objects.filter(anio=int(anioactual.year)).exists():
                    numeromaximo = AccionPersonal.objects.filter(anio=int(anioactual.year),motivoaccion_id=6).order_by('-numero')[0]
                    nummaximo = numeromaximo.numero
                doc='REGISTRO EN EL SISTEMA DE VACACIONES Y PERMISOS DE LA INSTITUCIÓN'
                form = AccionPersonal2Form(request.POST)
                if form.is_valid():

                    accionpersonal = AccionPersonal(persona_id=permiso.permisoinstitucional.solicita.id,
                                                    subroganterrhh=form.cleaned_data['subroganterrhh'],
                                                    personauath_id=form.cleaned_data['personarrhh'],
                                                    personaregistrocontrol_id=form.cleaned_data[
                                                        'personaregistrocontrol'],
                                                    numero=nummaximo + 1,
                                                    fechaelaboracion=permiso.permisoinstitucional.fecha_aprobacion(),
                                                    tipo_id=2,
                                                    motivoaccion_id=6,
                                                    anio=datetime.now().year,
                                                    fechaaprobacion=permiso.permisoinstitucional.fecha_aprobacion(),
                                                    fechadesde=permiso.fechainicio,
                                                    fechahasta=permiso.fechafin,
                                                    explicacion=form.cleaned_data['explicacion'],
                                                    regimenlaboral=distributivo.regimenlaboral,
                                                    documento=doc,
                                                    motivo=motivo,
                                                    lugartrabajoactual='MILAGRO',
                                                    abreviatura='VAC',
                                                    departamentoactual=permiso.permisoinstitucional.unidadorganica,
                                                    denominacionpuestoactual=distributivo.denominacionpuesto,
                                                    escalaocupacionalactual=distributivo.escalaocupacional,
                                                    tipogradoactual=distributivo.grado,
                                                    rmuactual=distributivo.rmupuesto,
                                                    partidapresupuestariaactual=form.cleaned_data[
                                                        'partidapresupuestariaactual'],
                                                    tipogrado=tipogrado,
                                                    fecharegistroaccion=permiso.permisoinstitucional.fecha_aprobacion(),
                                                    nroregistro=permiso.id
                                                    )
                    accionpersonal.save()
                    log(u'Registro accion persona: %s' % accionpersonal, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'subiraccionpersonal':
            try:
                periodopoa = AccionPersonal.objects.get(pk=encrypt(request.POST['id']))
                f = AccionPersonalArchivoForm(request.POST, request.FILES)
                if periodopoa.estadoarchivo == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, El usuario aun no sube el documento firmado"})
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 2621440:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 2 Mb."})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                else:
                        return JsonResponse({"result": "bad", "mensaje": u"No existe archivo"})
                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("accionpersonal_", newfile._name)
                        # periodopoa.archivo = newfile
                        historialdocumento = HistoricoDocumentosPersonaAcciones(personaaccionvacacion=periodopoa,
                                                                                archivofirmado=newfile)
                        historialdocumento.save(request)
                    if persona.es_directordepartamental_talentohumano() and periodopoa.estadoarchivo == 2:
                        periodopoa.estadoarchivo = 3
                    elif periodopoa.estadoarchivo == 1:
                        periodopoa.estadoarchivo = 2
                    periodopoa.save(request)
                    return JsonResponse({"result": False, 'to': request.path}, safe=False)
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'finaliza':
            try:
                accion = AccionPersonal.objects.get(pk=int(encrypt(request.POST['idaccion'])))
                # accion.finalizado = True
                # accion.save(request)

                data = {}
                data['accionpersona'] = accion
                data['numero'] = str(accion.numero).zfill(4)
                data['tipoaccion'] = TipoAccionPersonal.objects.filter(status=True)
                data['motivoaccion'] = MotivoAccionPersonal.objects.filter(status=True).order_by('pk')

                nombrepersona = str(accion.persona.identificacion())
                nombredocumento = '{}_{}'.format(nombrepersona, random.randint(1, 100000).__str__())
                directory = os.path.join(SITE_STORAGE, 'media', 'accionpersonal')
                try:
                    os.stat(directory)
                except:
                    os.mkdir(directory)
                valida = conviert_html_to_pdf_name_saveaccionpersonal('th_accionpersonal/accionpersonal_pdf.html', {'pagesize': 'A4', 'data': data, },
                                                        nombredocumento)
                if valida:
                    archivo = 'accionpersonal/' + nombredocumento + '.pdf'
                    accion.archivo = archivo
                    accion.save(request)

                asunto = u"ACCION DE PERSONAL DE VACACIONES"
                # email=['jguachuns@unemi.edu.ec',]
                email=accion.persona.lista_emails_envio()
                documentolista = [accion.archivo]
                mensaje = "La Unidad Administrativa de Talento Humano, " \
                          "solicita se firme la acción de personal con FIRMA ELECTRÓNICA, " \
                          "este documento debe ser firmado en el módulo hoja de vida, pestaña acción de personal. " \
                          "En el caso de existir alguna novedad en el documento, favor comunicar a: talento_humano@unemi.edu.ec."
                send_html_mail(asunto, "emails/legaliza_accion_personal.html",
                               {'sistema': request.session['nombresistema'],
                                'accion': accion, 'mensaje':mensaje},
                               email, [], documentolista, cuenta=CUENTAS_CORREOS[0][1])
                notificacion(asunto, mensaje, accion.persona, None, '/th_hojavida', accion.pk, 3, 'sagest - sga',
                             AccionPersonal, request)

                # notificacion(asunto, mensaje, accion.persona, None, '/th_hojavida', accion.pk, 3, 'sga',
                #              AccionPersonal, request)

                # log(u'Finaliza accion de personal: %s' % accion, request, "edit")
                log(u'Envia accion de personal: %s al usuario' % accion, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'legalizar':
            try:
                accion = AccionPersonal.objects.get(pk=encrypt(request.POST['id']))
                if accion.estadoarchivo == 4:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, esta accion ya se encuenta lagalizada."})
                accion.finalizado = True
                accion.save(request)

                data = {}
                data['accionpersona'] = accion
                data['numero'] = str(accion.numero).zfill(4)
                data['tipoaccion'] = TipoAccionPersonal.objects.filter(status=True)
                data['motivoaccion'] = MotivoAccionPersonal.objects.filter(status=True).order_by('pk')

                nombrepersona = str(accion.persona.identificacion())

                newfile = None
                form = AccionPersonalDocumentoForm(request.POST, request.FILES)
                if form.is_valid():
                    # accionpersonal = AccionPersonal.objects.get(pk=int(request.POST['id']))
                    if 'archivofirmado' in request.FILES:
                        newfile = request.FILES['archivofirmado']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 4194304:
                            return JsonResponse(
                                {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                        if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                            newfile._name = generar_nombre("AccionPersonalFirmado_", newfile._name)
                        else:
                            return JsonResponse(
                                {"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                        # accionpersonal.archivofirmado = newfile
                    historialdocumento = HistoricoDocumentosPersonaAcciones(personaaccionvacacion=accion,
                                                                            archivofirmado=newfile)
                    historialdocumento.save(request)
                    accion.estadoarchivo = 4
                    accion.save(request)

                    log(u'Adiciono Documento firmado en accion de personal vacaciones: %s' % accion, request, "add")

                    asunto = u"ACCION DE PERSONAL DE VACACIONES"
                    mensaje = "<b>  %s. </b>" \
                          "<br>La Unidad Administrativa de Talento Humano," \
                          "indica que su acción de personal fue legalizada. <br><br>" \
                          "En el caso de existir alguna novedad en el documento, favor comunicar a: <b>talento_humano@unemi.edu.ec.</b> <br><br>" \
                          "<b>Nota:</b> No firmar en Adobe Acrobat Reader." \
                              "<br>" % (accion.persona.nombre_completo_inverso())
                    notificacion(asunto, mensaje, accion.persona, None, '/th_hojavida', accion.pk, 3, 'sagest - sga',
                                 AccionPersonal, request)

                    log(u'Finaliza accion de personal: %s' % accion, request, "edit")
                    return JsonResponse({"result": False, 'to': request.path}, safe=False)
                else:
                    transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'edit':
            try:
                accionpersona = AccionPersonal.objects.get(pk=encrypt(request.POST['id']))
                indiceocup = None
                denominacionpuesto = None
                rmu = 0
                escalaocupacional = None
                tipogrado = 0
                if not accionpersona.motivo.motivo_id ==6:
                    form = AccionPersonalForm(request.POST)
                    if form.is_valid():
                        if IndiceSeriePuesto.objects.filter(pk=int(form.cleaned_data['denominacionpuesto'])).exists():
                            indiceocupacionalpropuesto = IndiceSeriePuesto.objects.get(pk=int(form.cleaned_data['denominacionpuesto']))
                            indiceocup = indiceocupacionalpropuesto.id
                            denominacionpuesto = indiceocupacionalpropuesto.denominacionpuesto.id
                            escalaocupacional = indiceocupacionalpropuesto.escalaocupacional.id
                            tipogrado = indiceocupacionalpropuesto.tipogrado
                            rmu = indiceocupacionalpropuesto.rmu
                        if form.cleaned_data['denominacionpuestoactual'] in [None, '', 0]:
                            denominacionpuestoactualid = None
                        else:
                            denominacionpuestoactualid = form.cleaned_data['denominacionpuestoactual']
                        accionpersona.persona_id = int(form.cleaned_data['persona'])
                        accionpersona.personauath_id = int(form.cleaned_data['personarrhh'])
                        accionpersona.personaregistrocontrol_id = int(form.cleaned_data['personaregistrocontrol'])
                        accionpersona.numero = form.cleaned_data['numero']
                        accionpersona.anio = form.cleaned_data['anio']
                        accionpersona.abreviatura = form.cleaned_data['abreviatura']
                        accionpersona.fechaelaboracion = form.cleaned_data['fechaelaboracion']
                        accionpersona.tipo_id = form.cleaned_data['tipo']
                        accionpersona.documento = form.cleaned_data['documento']
                        accionpersona.fechaaprobacion = form.cleaned_data['fechaaprobacion']
                        accionpersona.fechadesde = form.cleaned_data['fechadesde']
                        accionpersona.fechahasta = form.cleaned_data['fechahasta']
                        accionpersona.explicacion = form.cleaned_data['explicacion']
                        accionpersona.regimenlaboral_id = form.cleaned_data['regimenlaboral']
                        accionpersona.motivo_id = form.cleaned_data['motivo']
                        accionpersona.departamentoactual_id = form.cleaned_data['departamentoactual']
                        accionpersona.denominacionpuestoactual_id = denominacionpuestoactualid
                        accionpersona.escalaocupacionalactual_id = form.cleaned_data['escalaocupacionalactual']
                        accionpersona.tipogradoactual = form.cleaned_data['tipogradoactual']
                        accionpersona.lugartrabajoactual = form.cleaned_data['lugartrabajoactual']
                        accionpersona.rmuactual = form.cleaned_data['rmuactual']
                        accionpersona.partidapresupuestariaactual = form.cleaned_data['partidapresupuestariaactual']
                        accionpersona.departamento_id = form.cleaned_data['departamento']
                        accionpersona.indiceocupacionalpropuesto_id = indiceocup
                        accionpersona.denominacionpuesto_id = denominacionpuesto
                        accionpersona.escalaocupacional_id = escalaocupacional
                        accionpersona.tipogrado = tipogrado
                        accionpersona.lugartrabajo = form.cleaned_data['lugartrabajo']
                        accionpersona.rmu = float(form.cleaned_data['rmu'])
                        accionpersona.partidapresupuestaria = form.cleaned_data['partidapresupuestaria']
                        accionpersona.subroganterrhh = form.cleaned_data['subroganterrhh']
                        accionpersona.numeroactafinal = form.cleaned_data['numeroactafinal']
                        accionpersona.fechaactafinal = form.cleaned_data['fechaactafinal']
                        if form.cleaned_data['cesafunciones']:
                            accionpersona.numerocaucion = form.cleaned_data['numerocaucion']
                            accionpersona.fechacaucion = form.cleaned_data['fechacaucion']
                            accionpersona.personareemplaza_id = form.cleaned_data['personareemplaza']
                            accionpersona.denominacionpuestoreemplazo_id = form.cleaned_data['denominacionpuestoreemplazo']
                            accionpersona.cesofunciones = form.cleaned_data['cesofunciones']
                            accionpersona.numeroaccion = form.cleaned_data['numeroaccion']
                            accionpersona.fecharegistroaccion = form.cleaned_data['fecharegistroaccion']
                            accionpersona.colegioprofesionales = form.cleaned_data['colegioprofesionales']
                        accionpersona.save(request)
                        log(u'Modifico graduado: %s' % accionpersona, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                else:
                    form = AccionPersonal2Form(request.POST)
                    if form.is_valid():
                        accionpersona.personauath_id = int(form.cleaned_data['personarrhh'])
                        accionpersona.personaregistrocontrol_id = int(form.cleaned_data['personaregistrocontrol'])
                        accionpersona.partidapresupuestariaactual = form.cleaned_data['partidapresupuestariaactual']
                        accionpersona.subroganterrhh = form.cleaned_data['subroganterrhh']
                        accionpersona.explicacion = form.cleaned_data['explicacion']

                        accionpersona.save(request)
                        log(u'Modifico accion de personal: %s' % accionpersona, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editmotivo':
            try:
                form = MotivoAccionPersonalForm(request.POST)
                filtro = MotivoAccionPersonal.objects.get(id=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    filtro.nombre = form.cleaned_data['nombre']
                    filtro.abreviatura = form.cleaned_data['abreviatura']
                    filtro.save(request)
                    log(u'Edito motivo: %s' % filtro, request, action)
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})



        elif action == 'editbase':
            try:
                form = BaseLegalAccionPersonalForm(request.POST)
                filtro = BaseLegalAccionPersonal.objects.get(id=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    filtro.descripcion = form.cleaned_data['descripcion']
                    filtro.save(request)
                    log(u'Edito base legal: %s' % filtro, request, action)
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'finalizaraccionpersonal':
            try:
                objetivo = AccionPersonal.objects.get(pk=encrypt(request.POST['id']))
                descripcion = objetivo.persona.nombre_completo()
                idobjetivo = encrypt(objetivo.id)
                return JsonResponse({"result": "ok", 'descripcion': descripcion, 'idobjetivo': idobjetivo})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'pdfaccionpersonal':
            try:
                data = {}
                data['accionpersona'] = accionpersonal = AccionPersonal.objects.get(pk=encrypt(request.POST['id']))
                # titulotercernivel = Titulo.objects.filter(titulacion__persona=accionpersonal.personarector, nivel_id=3).order_by('-nivel__id')[0]
                # data['titulotercernivel'] = titulotercernivel.abreviatura
                #data['titulomayor'] = titulomayor.titulo.abreviatura
                data['numero'] = str(accionpersonal.numero).zfill(4)
                data['tipoaccion'] = TipoAccionPersonal.objects.filter(status=True)
                data['motivoaccion'] = MotivoAccionPersonal.objects.filter(status=True).order_by('pk')
                return conviert_html_to_pdf(
                    'th_accionpersonal/accionpersonal_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        elif action == 'addmotivo':
            try:
                form = MotivoAccionPersonalForm(request.POST)
                if form.is_valid():
                    motivo = MotivoAccionPersonal(nombre=form.cleaned_data['nombre'],
                                                  abreviatura=form.cleaned_data['abreviatura'])
                    motivo.save(request)
                    log(u'Registro motivo: %s' % motivo, request, "add")
                    return JsonResponse({'result': False, 'mensaje': 'Registro Exitoso'})
                raise NameError('Error en el formulario')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'addbaselegal':
            try:
                form = request.POST['descripcion'].strip('\n')
                filtro = BaseLegalAccionPersonal(descripcion=form)
                filtro.save(request)
                log(u'Registro base legal: %s' % filtro, request, "add")
                return JsonResponse({'result': False, 'mensaje': 'Registro Exitoso'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'addconfigurar':
            try:
                motivo = MotivoAccionPersonal.objects.get(pk=request.POST['id'])
                form = MotivoAccionPersonalDetalleForm(request.POST)
                if form.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    if not datos:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar personas."})
                    for d in datos:
                        id = d['id']
                        if not (MotivoAccionPersonalDetalle.objects.filter(status=True, motivo=motivo,regimenlaboral_id=id).exists()):
                            detalle = MotivoAccionPersonalDetalle(motivo=motivo,
                                                                  baselegal=form.cleaned_data['baselegal'],
                                                                  regimenlaboral_id=id
                                                                  )
                            detalle.save()
                            log(u'aconfiguro %s en accion de personal' % motivo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')

            except Exception as ex:
                pass

        elif action == 'delconfigurar':
            try:
                config = MotivoAccionPersonalDetalle.objects.get(pk=encrypt(request.POST['id']), status=True)
                config.status = False
                config.save(request)
                log(u'Elimino configuracion: %s' % config, request, "del")
                res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'legalizarsolo':
            try:
                accion = AccionPersonal.objects.get(pk=encrypt(request.POST['id']))
                if accion.estadoarchivo == 4:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, esta accion ya se encuenta lagalizada."})
                if len(accion.historial_documentos().values_list('id')) <= 1 or accion.estadoarchivo < 3:
                    return JsonResponse({"result": "bad", "mensaje": u"Aun no se ha subido el archivo firmado"})

                accion.finalizado = True
                accion.estadoarchivo = 4
                accion.save(request)
                log(u'Legaliza accion de personal: %s' % accion, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as e:
                print(e)
                transaction.set_rollback(True)
                pass

        elif action == 'firmaraccionpersonalmasivo':
            try:
                certificado = request.FILES["firma"]
                contrasenaCertificado = request.POST['palabraclave']
                razon = request.POST['razon'] if 'razon' in request.POST else ''
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()
                if persona.es_directordepartamental_talentohumano():
                    accionespersonal = AccionPersonal.objects.filter(status=True, estadoarchivo=2, personauath=persona)
                else:
                    accionespersonal = AccionPersonal.objects.filter(status=True, estadoarchivo=1, personaregistrocontrol=persona)
                cont = 0
                for accionpersonal in accionespersonal.order_by('-anio', '-numero', 'persona__apellido1'):
                    try:
                        firmas = []
                        archivo_ = accionpersonal.documento_firmado()
                        letra = ['O', '']
                        letra2 = ''
                        titulo_ter = persona.nombre_titulo().title()
                        if accionpersonal.personauath.sexo.id == 1:
                            letra = ['A', 'A']
                        if accionpersonal.subroganterrhh:
                            letra2 = '(S)'
                        if persona.es_directordepartamental_talentohumano():
                            director=f'DIRECTOR{letra[1]}{letra2} DE TALENTO HUMANO'
                            titulo = f'DELEGAD{letra[0]}-AUTORIDAD NOMINADORA {director}'
                            palabras = f'{titulo_ter} {titulo}'.strip()
                            palabras2 = f'{titulo_ter} {director}'.strip()
                            x, y, numPage = obtener_posicion_x_y_saltolinea(archivo_.url, palabras, False, True)
                            if x and y:
                                y = y - 15
                                firmas.append({'x': x, 'y': y, 'numPage': numPage})
                            x, y, numPage = obtener_posicion_x_y_saltolinea(archivo_.url, palabras2, False, True)
                            if x and y:
                                y = y - 15
                                firmas.append({'x': x, 'y': y, 'numPage': numPage})
                        elif accionpersonal.estadoarchivo == 1:
                            titulo = f'Responsable del Registro'
                            palabras = f'{titulo_ter} {titulo}'.strip()
                            x, y, numPage = obtener_posicion_x_y_saltolinea(archivo_.url, palabras, False, True)
                            if x and y:
                                y = y - 15
                                firmas.append({'x': x, 'y': y, 'numPage': numPage})
                        if firmas:
                            for membrete in firmas:
                                datau = JavaFirmaEc(
                                    archivo_a_firmar=archivo_, archivo_certificado=bytes_certificado, extension_certificado=extension_certificado,
                                    password_certificado=contrasenaCertificado,
                                    page=int(membrete["numPage"]), reason=razon, lx=membrete["x"], ly=membrete["y"]
                                ).sign_and_get_content_bytes()
                                archivo_ = io.BytesIO()
                                archivo_.write(datau)
                                archivo_.seek(0)

                            _name = f"accionpersonalfirmados_{len(accionpersonal.historial_documentos())}_{accionpersonal.id}_{accionpersonal.persona.usuario}"
                            file_obj = DjangoFile(archivo_, name=f"{_name}.pdf")

                            # accionpersonal.archivo = file_obj
                            if persona.es_directordepartamental_talentohumano() and accionpersonal.estadoarchivo == 2:
                                accionpersonal.estadoarchivo = 3
                            elif accionpersonal.estadoarchivo == 1:
                                accionpersonal.estadoarchivo = 2
                            accionpersonal.save(request)
                            log(f'Firmo Documento de acción de personal: {accionpersonal} | {archivo_}', request, "add")

                            historialdocumento = HistoricoDocumentosPersonaAcciones(personaaccionvacacion=accionpersonal,
                                                                                    archivofirmado=file_obj)
                            historialdocumento.save(request)
                            cont += 1
                            log(u'Edito estado firmado:  {}'.format(accionpersonal), request, "edit")
                    except Exception as ex:
                        if f'{ex}' == 'Certificado no es válido':
                            raise NameError(f'{ex}')
                    messages.success(request, f'Acciones de personal firmadas : {cont}')
                return JsonResponse({'result': False, 'mensaje': 'Guardado correctamente'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Nueva Accion Personal'
                    data['form'] = AccionPersonalForm()
                    anioactual = datetime.now().year
                    nummaximo = 0
                    if AccionPersonal.objects.filter(anio=int(anioactual)).exists():
                        numeromaximo = AccionPersonal.objects.filter(anio=int(anioactual)).order_by('-numero')[0]
                        nummaximo = numeromaximo.numero
                    data['numeromaximo'] = nummaximo + 1
                    # data['personarector'] = nombres = DistributivoPersona.objects.get(denominacionpuesto__descripcion='RECTOR/A', status=True, estadopuesto_id=1)
                    data['personarrhh'] = DistributivoPersona.objects.get(denominacionpuesto__descripcion='DIRECTOR DE TALENTO HUMANO', status=True, estadopuesto_id=1)
                    # data['nombres'] = nombres.persona
                    return render(request, "th_accionpersonal/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'subiraccionpersonal':
                try:
                    # data['title'] = u'Subir Archivo Accion Personal'
                    # data['accionpersonal'] = AccionPersonal.objects.get(pk=request.GET['id'])
                    # data['form'] = AccionPersonalArchivoForm()
                    # return render(request, 'th_accionpersonal/subirarchivo.html', data)
                    data['filtro'] = filtro = AccionPersonal.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['formmodal'] = AccionPersonalArchivoForm()
                    data['action'] = action
                    template = get_template("th_hojavida/modal/formdocumentofirmado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addv':
                try:
                    motivo=""
                    partida=0
                    data['permiso'] = permiso = PermisoInstitucionalDetalle.objects.get(pk=int(encrypt(request.GET['id'])))
                    if DistributivoPersona.objects.filter(persona=permiso.permisoinstitucional.solicita,denominacionpuesto=permiso.permisoinstitucional.denominacionpuesto,regimenlaboral=permiso.permisoinstitucional.regimenlaboral).exists():
                        partida = DistributivoPersona.objects.get(persona=permiso.permisoinstitucional.solicita,denominacionpuesto=permiso.permisoinstitucional.denominacionpuesto,regimenlaboral=permiso.permisoinstitucional.regimenlaboral).partidaindividual
                    data['partida'] = partida
                    data['title'] = u'Accion Personal de '+ permiso.permisoinstitucional.solicita.nombre_completo_inverso()
                    inicio = str(permiso.fechainicio.day)
                    fin = str(permiso.fechafin.day)
                    mesinicio = MESES_CHOICES[permiso.fechainicio.month - 1][1]
                    mesfin = MESES_CHOICES[permiso.fechafin.month - 1][1]
                    data['form'] = AccionPersonal2Form()
                    data['personarrhh'] = DistributivoPersona.objects.get(denominacionpuesto__descripcion__icontains='DIRECTOR DE TALENTO HUMANO', status=True, estadopuesto_id=1)
                    if DistributivoPersona.objects.values('id').filter(status=True, persona=persona).exists():
                        data['personaregistra'] = DistributivoPersona.objects.filter(status=True, persona=persona)[0]
                    else:
                        return HttpResponseRedirect("/?info=No esta registrado en la plantilla de talento humano.")
                    #data['personaregistra'] = DistributivoPersona.objects.get(pk=164527)
                    if  MotivoAccionPersonalDetalle.objects.filter(motivo_id=6,regimenlaboral=permiso.permisoinstitucional.regimenlaboral).exists():
                        motivo = MotivoAccionPersonalDetalle.objects.get(motivo_id=6,regimenlaboral=permiso.permisoinstitucional.regimenlaboral)
                        motivo= motivo.baselegal.descripcion
                    texto = """EN ATENCIÓN AL REGISTRO EN EL SISTEMA DE VACACIONES Y PERMISOS DE LA INSTITUCIÓN; EN EL CUAL %s DA A CONOCER EL CRONOGRAMA DE VACACIONES DEL PERSONAL A SU CARGO, DEBIDAMENTE AUTORIZADAS, RAZON POR LA CUAL SE REALIZA LA PRESENTE ACCION DE PERSONAL, DESDE EL %s DE %s AL %s DE %s,REINTEGRÁNDOSE A SUS ACTIVIDADES EL DIA LABORAL INMEDIATO [FECHA AQUI]""" % (permiso.permisoinstitucional.responsable2(), inicio,mesinicio, fin,mesfin)
                    data['explicacion'] = "%s %s" %(motivo, texto)

                    return render(request, "th_accionpersonal/addv.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    indiceocup = None
                    denominacionpuesto = None
                    rmu = 0
                    escalaocupacional = None
                    tipogrado = 0
                    data['title'] = u'Editar Accion Personal'
                    data['accionpersona'] = accionpersona = AccionPersonal.objects.get(pk=encrypt(request.GET['id']))

                    if accionpersona.personauath_id in [None, '', 0]:
                        data['personarrhh'] = personarrhh = 0
                    else:
                        data['personarrhh'] = personarrhh = accionpersona.personauath.id
                    if accionpersona.personaregistrocontrol_id in [None, '', 0]:
                        data['personaregistrocontrol'] = personaregistrocontrol = 0
                    else:
                        data[
                            'personaregistrocontrol'] = personaregistrocontrol = accionpersona.personaregistrocontrol.id

                    if not accionpersona.motivo.motivo_id == 6:
                        if accionpersona.indiceocupacionalpropuesto:
                            indiceocupacionalpropuesto = IndiceSeriePuesto.objects.get(pk=accionpersona.indiceocupacionalpropuesto.id)
                            indiceocup = indiceocupacionalpropuesto.id
                            denominacionpuesto = indiceocupacionalpropuesto.denominacionpuesto.id
                            escalaocupacional = indiceocupacionalpropuesto.escalaocupacional.id
                            tipogrado = indiceocupacionalpropuesto.tipogrado
                            rmu = indiceocupacionalpropuesto.rmu
                        # if accionpersona.personarector_id in [None, '', 0]:
                        #     data['personarector'] = personarector = 0
                        # else:
                        #     data['personarector'] = personarector = accionpersona.personarector.id

                        if accionpersona.indiceocupacionalpropuesto_id in [None, '', 0]:
                            data['indiceocupacionalpropuesto'] = indiceocupacionalpropuesto = 0
                        else:
                            data['indiceocupacionalpropuesto'] = indiceocupacionalpropuesto = accionpersona.indiceocupacionalpropuesto.id
                            data['nombreindiceocupacionalpropuesto'] = accionpersona.denominacionpuesto.descripcion
                        if accionpersona.denominacionpuestoactual_id in [None, '', 0]:
                            data['denominacionpuestoactual'] = denominacionpuestoactual = 0
                        else:
                            data['denominacionpuestoactual'] = denominacionpuestoactual = accionpersona.denominacionpuestoactual.id
                            data['nombredenominacionpuestoactual'] = accionpersona.denominacionpuestoactual.descripcion
                        if accionpersona.denominacionpuestoreemplazo_id in [None, '', 0]:
                            data['denominacionpuestoreemplazo'] = denominacionpuestoreemplazo = 0
                        else:
                            data['denominacionpuestoreemplazo'] = denominacionpuestoreemplazo = accionpersona.denominacionpuestoreemplazo.id
                            data['nombredenominacionpuestoreemplazo'] = accionpersona.denominacionpuestoreemplazo.descripcion
                        if accionpersona.personareemplaza_id in [None, '', 0]:
                            data['personareemplaza'] = personareemplaza = 0
                        else:
                            data['personareemplaza'] = personareemplaza = accionpersona.personareemplaza.id
                        data['form'] = AccionPersonalForm(initial={'persona': accionpersona.persona.id,
                                                                   'personarrhh': personarrhh,
                                                                   'personaregistrocontrol': personaregistrocontrol,
                                                                   'numero': accionpersona.numero,
                                                                   'anio': accionpersona.anio,
                                                                   'abreviatura': accionpersona.abreviatura,
                                                                   'fechaelaboracion': accionpersona.fechaelaboracion,
                                                                   'tipo': accionpersona.tipo,
                                                                   'documento': accionpersona.documento,
                                                                   'fechaaprobacion': accionpersona.fechaaprobacion,
                                                                   'fechadesde': accionpersona.fechadesde,
                                                                   'fechahasta': accionpersona.fechahasta,
                                                                   'explicacion': accionpersona.explicacion,
                                                                   'regimenlaboral': accionpersona.regimenlaboral,
                                                                   'motivo': accionpersona.motivo,
                                                                   'departamentoactual': accionpersona.departamentoactual,
                                                                   'denominacionpuestoactual': denominacionpuestoactual,
                                                                   'escalaocupacionalactual': accionpersona.escalaocupacionalactual,
                                                                   'tipogradoactual': accionpersona.tipogradoactual,
                                                                   'lugartrabajoactual': accionpersona.lugartrabajoactual,
                                                                   'rmuactual': accionpersona.rmuactual,
                                                                   'partidapresupuestariaactual': accionpersona.partidapresupuestariaactual,
                                                                   'departamento': accionpersona.departamento,
                                                                   'escalaocupacional': denominacionpuesto,
                                                                   'tipogrado': tipogrado,
                                                                   'lugartrabajo': accionpersona.lugartrabajo,
                                                                   'rmu': float(accionpersona.rmu),
                                                                   'partidapresupuestaria': accionpersona.partidapresupuestaria,
                                                                   'indiceocupacionalpropuesto': indiceocup,
                                                                   'numerocaucion': accionpersona.numerocaucion,
                                                                   'fechacaucion': accionpersona.fechacaucion,
                                                                   'personareemplaza': personareemplaza,
                                                                   'denominacionpuestoreemplazo': denominacionpuestoreemplazo,
                                                                   'cesofunciones': accionpersona.cesofunciones,
                                                                   'numeroaccion': accionpersona.numeroaccion,
                                                                   'fecharegistroaccion': accionpersona.fecharegistroaccion,
                                                                   'colegioprofesionales': accionpersona.colegioprofesionales,
                                                                   #'subroganterector': accionpersona.subroganterector,
                                                                   'subroganterrhh': accionpersona.subroganterrhh,
                                                                   'numeroactafinal': accionpersona.numeroactafinal,
                                                                   'fechaactafinal': accionpersona.fechaactafinal
                                                                   })
                        return render(request, "th_accionpersonal/edit.html", data)
                    else:
                        data['form'] = AccionPersonal2Form(initial={ 'personarrhh': personarrhh,
                                                                   'subroganterrhh': accionpersona.subroganterrhh,
                                                                   'personaregistrocontrol': personaregistrocontrol,
                                                                   'explicacion': accionpersona.explicacion,
                                                                   'partidapresupuestariaactual': accionpersona.partidapresupuestariaactual,
                                                                   })
                        return render(request, "th_accionpersonal/editv.html", data)

                except Exception as ex:
                    pass

            elif action == 'editmotivo':
                try:
                    data['title'] = u'Editar Motivo Accion Personal'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['action'] =  request.GET['action']
                    data['filtro'] = filtro = MotivoAccionPersonal.objects.get(id=id)
                    initial = model_to_dict(filtro)
                    form = MotivoAccionPersonalForm(initial=initial)
                    data['form'] = form
                    template = get_template("th_accionpersonal/modal/formmotivo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})

                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'anular':
                try:
                    data['criterio']=filtro = AccionPersonal.objects.get(id=int(encrypt(request.GET['id'])))
                    filtro.estadoarchivo = 5
                    #filtro.save(request)
                    template = get_template("th_accionpersonal/anulacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    pass

            elif action == 'accionanularp':
                try:
                    filtro = AccionPersonal.objects.get(id=int(request.GET['id']))
                    #data['observacion']=request.GET['observacion']
                    filtro.estadoarchivo = 5
                    filtro.observacion = request.GET['observacion']
                    filtro.save(request)

                except Exception as ex:
                    pass

            elif action == 'addmotivo':
                try:
                    data['title'] = u'Ingresar Motivo'
                    data['action'] = request.GET['action']
                    form = MotivoAccionPersonalForm()
                    data['form'] = form
                    template = get_template("th_accionpersonal/modal/formmotivo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'addbaselegal':
                try:
                    data['title'] = u'Ingresar Base Legal'
                    data['action'] = request.GET['action']
                    form = BaseLegalAccionPersonalForm()
                    data['form'] = form
                    template = get_template("th_accionpersonal/modal/formbaselegal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})


            elif action == 'editbase':
                try:
                    data['title'] = u'Editar Base Legal Accion Personal'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['action'] = request.GET['action']
                    data['filtro'] = filtro = BaseLegalAccionPersonal.objects.get(id=id)
                    initial = model_to_dict(filtro)
                    form = BaseLegalAccionPersonalForm(initial=initial)
                    data['form'] = form
                    template = get_template("th_accionpersonal/modal/formbaselegal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'viewvacaciones':
                try:
                    data['title'] = u'Acciones de personal pendientes por vacaciones'
                    search = None
                    ids = None
                    tipo = None
                    excluir = [x.nroregistro for x in AccionPersonal.objects.filter(status=True, nroregistro__gte=0)]
                    incluir = [x.pk if int(x.fechainicio.year)>=2020 else 0 for x in PermisoInstitucionalDetalle.objects.filter(status=True, permisoinstitucional__tipopermiso_id__in=[24,27],permisoinstitucional__estadosolicitud__in=[2,3]) ]

                    data['tipoid'] = tipo = 1
                    url_vars = f"&action=viewvacaciones"
                    if 't' in request.GET:
                        data['tipoid'] = tipo = int(request.GET['t'])

                    url_vars += f"&t={tipo}"

                    if 's' in request.GET:
                        search = request.GET['s'].upper()
                        ss = search.split(' ')

                        if len(ss) == 1:
                            plantillas = PermisoInstitucionalDetalle.objects.filter(Q(permisoinstitucional__solicita__nombres__icontains=search) |
                                                                             Q(permisoinstitucional__solicita__apellido1__icontains=search) |
                                                                             Q(permisoinstitucional__solicita__apellido2__icontains=search) |
                                                                             Q(permisoinstitucional__solicita__cedula__icontains=search) |
                                                                             Q(permisoinstitucional__solicita__pasaporte__icontains=search),permisoinstitucional__tipopermiso_id__in=[24,27],permisoinstitucional__estadosolicitud__in=[2,3],pk__in=incluir).distinct().exclude(pk__in=excluir).order_by('-fechainicio')

                        else:
                            plantillas = PermisoInstitucionalDetalle.objects.filter(
                                Q(permisoinstitucional__solicita__apellido1__icontains=ss[0]) & Q(permisoinstitucional__solicita__apellido2__icontains=ss[1]),permisoinstitucional__tipopermiso_id__in=[24,27],permisoinstitucional__estadosolicitud__in=[2,3],pk__in=incluir).distinct().exclude(pk__in=excluir).order_by('-fechainicio')
                        url_vars += f"&s={search}"
                    else:
                        plantillas = PermisoInstitucionalDetalle.objects.filter(permisoinstitucional__tipopermiso_id__in=[24,27],permisoinstitucional__estadosolicitud__in=[2,3],pk__in=incluir).distinct().exclude(pk__in=excluir)
                    if tipo==1:
                        plantillas = plantillas.order_by('-fechainicio')
                    else:
                        plantillas = plantillas.order_by('fechainicio')
                    paging = MiPaginador(plantillas, 20)

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
                    data['accionpersonal'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, 'th_accionpersonal/viewvacaciones.html', data)
                except Exception as ex:
                    pass

            elif action == 'viewmotivo':
                try:
                    data['title'] = u'Motivos'
                    search = None
                    ids = None
                    url_vars = f"&action=viewmotivo"
                    if 's' in request.GET:
                        search = request.GET['s'].upper()
                        motivos = MotivoAccionPersonal.objects.filter(nombre__icontains=search,status=True).order_by('pk')
                        url_vars += f"&s={search}"
                    else:
                        motivos = MotivoAccionPersonal.objects.filter(status=True).order_by('pk')
                    paging = MiPaginador(motivos, 20)

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
                    request.session['viewactivoaccionpersonal'] = 1
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['motivos'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, 'th_accionpersonal/viewmotivo.html', data)
                except Exception as ex:
                    pass

            elif action == 'viewbaselegal':
                try:
                    data['title'] = u'Base Legal'
                    search = None
                    ids = None
                    url_vars = f"&action=viewbaselegal"
                    if 's' in request.GET:
                        search = request.GET['s'].upper()
                        bases = BaseLegalAccionPersonal.objects.filter(descripcion__icontains=search,status=True).order_by('pk')
                        url_vars += f"&s={search}"
                    else:
                        bases = BaseLegalAccionPersonal.objects.filter(status=True).order_by('pk')
                    paging = MiPaginador(bases, 20)

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
                    request.session['viewactivoaccionpersonal'] = 2
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['url_vars'] = url_vars
                    data['baseslegales'] = page.object_list
                    return render(request, 'th_accionpersonal/viewbaselegal.html', data)
                except Exception as ex:
                    pass

            elif action == 'configurar':
                try:
                    data['motivo'] = motivo = MotivoAccionPersonal.objects.get(pk=request.GET['id'])
                    data['id'] = id = request.GET['id']
                    data['title'] = u'Configuración de %s' % motivo.nombre
                    url_vars = f"&action=configurar&id="+id
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')

                        if len(ss) == 1:
                            bases = MotivoAccionPersonalDetalle.objects.filter(motivo=motivo,regimenlaboral__descripcion__icontains=search,status=True).distinct().order_by('pk')
                        url_vars += f"&s={search}"
                    else:
                        bases = MotivoAccionPersonalDetalle.objects.filter(motivo=motivo,status=True).order_by('pk')
                    paging = MiPaginador(bases, 20)

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
                    data['detalles'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, 'th_accionpersonal/configuracion.html', data)
                except Exception as ex:
                    pass

            elif action == 'addconfigurar':
                try:
                    data['title'] = u'Configurar'
                    data['form'] = MotivoAccionPersonalDetalleForm()
                    data['motivo'] = MotivoAccionPersonal.objects.get(pk=request.GET['id'])
                    data['regimenes'] = RegimenLaboral.objects.filter(status=True)
                    return render(request, 'th_accionpersonal/addconfiguracion.html', data)
                except Exception as ex:
                    pass

            if action == 'verdetalle':
                try:
                    data = {}
                    detalle = PermisoInstitucionalDetalle.objects.get(pk=int(request.GET['id']))
                    data['permiso'] = detalle.permisoinstitucional
                    data['detallepermiso'] = detalle
                    data['aprobadores'] = detalle.permisoinstitucional.permisoaprobacion_set.all()
                    template = get_template("th_accionpersonal/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

# =============== GENERACION DE REPORTE DE ACCION DE PERSONAL | AUTH: ROALEX ===============

            elif action == 'generarreporte':
                try:

                    __author__ = 'Unemi'

                    desde = request.GET['desde']
                    hasta = request.GET['hasta']
                    regimen = request.GET['regimen']
                    regimen_nombre = request.GET['regimen_nombre']

                    filtros = Q(permisoinstitucional__fechasolicitud__range=(desde, hasta))
                    excluir = [x.nroregistro for x in AccionPersonal.objects.filter(status=True,
                                                                                    nroregistro__gte=0)]

                    incluir = [x.pk if int(x.fechainicio.year) >= 2020 else 0 for x in
                               PermisoInstitucionalDetalle.objects.filter(status=True,
                                                                          permisoinstitucional__estadosolicitud=3)]

                    permisos = PermisoInstitucionalDetalle.objects.filter(filtros,
                                                                          permisoinstitucional__regimenlaboral_id=regimen,
                                                                          permisoinstitucional__estadosolicitud=3,
                                                                          pk__in=incluir).distinct().exclude(pk__in=excluir).order_by('-permisoinstitucional__fechasolicitud')

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('accionpersonal')
                    ws.set_column(0, 10, 30)
                    ws.merge_range('A1:J1', 'REPORTE DE ACCIÓN DE PERSONAL - VACACIONES | DESDE: '+desde+ ' / HASTA: '+hasta+ ' DEL RÉGIMEN '+regimen_nombre)

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'border': 1, 'text_wrap': True, 'fg_color': '#EBF5FB'})
                    formatoceldaleft = workbook.add_format({'text_wrap': True, 'align': 'center'})

                    ws.write(1, 0, 'FECHA SOLICITUD', formatoceldacab)
                    ws.write(1, 1, 'CEDULA', formatoceldacab)
                    ws.write(1, 2, 'NOMBRES', formatoceldacab)
                    ws.write(1, 3, 'UNIDAD ORGANICA', formatoceldacab)
                    ws.write(1, 4, 'REGIMEN LABORAL', formatoceldacab)
                    ws.write(1, 5, 'TIPO PERSMISO', formatoceldacab)
                    ws.write(1, 6, 'TIPO SOLICITUD', formatoceldacab)
                    ws.write(1, 7, 'MOTIVO', formatoceldacab)
                    ws.write(1, 8, 'FECHA INICIO/FIN', formatoceldacab)
                    ws.write(1, 9, 'FECHA APROBACIÓN', formatoceldacab)

                    fila_permiso = 3
                    for permiso in permisos:

                        tipo_solicitud = ""
                        estado_solicitud = ""

                        if permiso.permisoinstitucional.tiposolicitud == 1:
                            tipo_solicitud = "SOLICITUD DE PERMISO"
                        elif permiso.permisoinstitucional.tiposolicitud == 2:
                            tipo_solicitud = "NOTIFICACIÓN DE INASISTENCIA"
                        elif permiso.permisoinstitucional.tiposolicitud == 3:
                            tipo_solicitud = "VACACIONES"

                        if permiso.permisoinstitucional.estadosolicitud == 1:
                            estado_solicitud = "SOLICITADO"
                        elif permiso.permisoinstitucional.estadosolicitud == 2:
                            estado_solicitud = "PENDIENTE"
                        elif permiso.permisoinstitucional.estadosolicitud == 3:
                            estado_solicitud = "APROBADO"
                        elif permiso.permisoinstitucional.estadosolicitud == 4:
                            estado_solicitud = "RECHAZADO"
                        elif permiso.permisoinstitucional.estadosolicitud == 5:
                            estado_solicitud = "VALIDADO"

                        fecha_inicio = permiso.fechainicio.strftime("%Y-%m-%d")
                        fecha_fin = permiso.fechafin.strftime("%Y-%m-%d")

                        ws.write('A%s' % fila_permiso,str(permiso.permisoinstitucional.fechasolicitud if permiso.permisoinstitucional.fechasolicitud else 'No existe registro'),formatoceldaleft)
                        ws.write('B%s' % fila_permiso, str(permiso.permisoinstitucional.solicita.cedula if permiso.permisoinstitucional.solicita.cedula else 'No existe registro'), formatoceldaleft)
                        ws.write('C%s' % fila_permiso, str(permiso.permisoinstitucional.solicita if permiso.permisoinstitucional.solicita else 'No existe registro'), formatoceldaleft)
                        ws.write('D%s' % fila_permiso, str(permiso.permisoinstitucional.unidadorganica if permiso.permisoinstitucional.unidadorganica else 'No existe registro'), formatoceldaleft)
                        ws.write('E%s' % fila_permiso, str(permiso.permisoinstitucional.regimenlaboral if permiso.permisoinstitucional.regimenlaboral else 'No existe registro'), formatoceldaleft)
                        ws.write('F%s' % fila_permiso, str(permiso.permisoinstitucional.tipopermiso if permiso.permisoinstitucional.tipopermiso else 'No existe registro'), formatoceldaleft)
                        ws.write('G%s' % fila_permiso, str(tipo_solicitud if tipo_solicitud else 'No existe registro'), formatoceldaleft)
                        ws.write('H%s' % fila_permiso, str(permiso.permisoinstitucional.motivo if permiso.permisoinstitucional.motivo else 'No existe registro'), formatoceldaleft)
                        ws.write('I%s' % fila_permiso, str(fecha_inicio+'\n'+fecha_fin), formatoceldaleft)
                        ws.write('J%s' % fila_permiso, str(permiso.permisoinstitucional.permisoaprobacion_set.last().fechaaprobacion), formatoceldaleft)

                        fila_permiso+=1

                    workbook.close()

                    output.seek(0)
                    filename = 'Accion de personal.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'cargar_regimen':
                try:
                    lista = []
                    regimen = RegimenLaboral.objects.filter(status=True).distinct()

                    for reg_detalle in regimen:
                        if not buscar_dicc(lista, 'id', reg_detalle.id):
                            lista.append({'id': reg_detalle.id, 'nombre': reg_detalle.descripcion})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'legalizar':
                try:
                    data['filtro'] = filtro = AccionPersonal.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['formmodal'] = AccionPersonalDocumentoForm()
                    data['action'] = action
                    template = get_template("th_hojavida/modal/formdocumentofirmado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'historialfirmados':
                try:
                    data['filtro'] = filtro = AccionPersonal.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['action'] = action
                    template = get_template("th_hojavida/modal/historialdocumentofirmado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as e:
                    print(e)
                    pass

            elif action == 'firmaraccionpersonalmasivo':
                try:
                    if not persona.es_directordepartamental_talentohumano():
                        total = len(AccionPersonal.objects.filter(status=True, estadoarchivo=1, personaregistrocontrol=persona))
                    else:
                        total = len(AccionPersonal.objects.filter(status=True, estadoarchivo=2, personauath=persona))

                    data['info_mensaje'] = f'Esta por firmas {total} documentos de accion de personal que se encuentran a su nombre'
                    template = get_template("formfirmaelectronicamasiva.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')
                    return HttpResponseRedirect(request.path)

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Accion Personal'
                search = request.GET.get('s','')
                ids = request.GET.get('id','')
                url_vars, estado, filtro = f"", request.GET.get('estado',''), Q(status=True,motivoaccion_id=6)

                if estado:
                    data['estado']=estado=int(estado)
                    filtro = filtro & Q(estadoarchivo=estado)
                    url_vars += f'&estado={estado}'

                if search:
                    search = request.GET['s'].upper()
                    ss = search.split(' ')
                    data['search'] = search

                    if len(ss) == 1:
                        filtro = filtro & (Q(persona__apellido1__icontains=search) |
                                           Q(persona__apellido2__icontains=search) |
                                           Q(persona__nombres__icontains=search))
                    else:
                        filtro = filtro & (Q(persona__apellido1__icontains=ss[0]) |
                                           Q(persona__apellido2__icontains=ss[1]))
                    url_vars += f"&s={search}"
                else:
                    if ids:
                        data['ids'] = ids = request.GET['id']
                        filtro = filtro & Q(pk=ids)

                accionpersonal = AccionPersonal.objects.filter(filtro).order_by('-anio', '-numero', 'persona__apellido1')

                paging = MiPaginador(accionpersonal, 25)
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
                data['accionpersonal'] = page.object_list
                data['url_vars'] = url_vars
                data['estados'] = ESTADO_ARCHIVO_FIRMADO
                return render(request, 'th_accionpersonal/view.html', data)
            except Exception as ex:
                pass