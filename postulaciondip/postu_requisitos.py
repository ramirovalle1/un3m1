# -*- coding: UTF-8 -*-
import os
import random
from datetime import datetime, timedelta
from http.client import HTTPResponse

import pyqrcode
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from psycopg2._json import Json
from requests import request

from decorators import secure_module, last_access
from postulaciondip.forms import RequisitosConvocatoriaInscripcionForm, DatoPersonalForm, ExperienciaLaboralForm, \
    TitulacionPersonaForm, DatosDomicilioForm, DiscapacidadForm, \
    RequisitosInscripcionForm, DatosPersonalesForm, CuentaBancariaPersonaForm, ArchivoInvitacionForm, LinkVideoForm
from postulaciondip.models import Convocatoria, InscripcionConvocatoria, InscripcionConvocatoriaRequisitos, \
    RequisitosConvocatoria, RequisitoGenerales, RequisitoGeneralesPersona, ActividadEconomica, InscripcionInvitacion, HistorialInvitacion, \
    ClasificacionAC, Requisito, \
    InscripcionRequisito, PasosProceso, RequisitosProceso, HistorialAprobacionInscripcion, InscripcionPostulante, HistorialAprobacion, \
    InscripcionRequisitoPreAprobado, PersonalAContratar, PersonalApoyoMaestria
from sagest.forms import TituloHojaVidaPostulacionForm, RedPersonaForm
from sagest.models import ExperienciaLaboral
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre, log, convertirfecha, variable_valor, null_to_decimal, remover_caracteres_tildes_unicode, \
    remover_caracteres_especiales_unicode
from sga.funcionesxhtml2pdf import conviert_html_to_pdf_save_file_model
from sga.models import Persona, FotoPersona, Titulo, Titulacion, RedPersona, PersonaDocumentoPersonal, \
    CuentaBancariaPersona, AreaConocimientoTitulacion, \
    SubAreaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacion, Graduado, CamposTitulosPostulacion, \
    CUENTAS_CORREOS, MESES_CHOICES
from sga.templatetags.sga_extras import encrypt
from mobile.views import make_thumb_picture, make_thumb_fotopersona
from settings import SITE_STORAGE, GENERAR_TUMBAIL
from django.contrib import messages
from django.db.models import Q
from sga.tasks import conectar_cuenta, send_html_mail, conectar_cuenta2
from postulaciondip.forms import DatoPersonalExtraForm
@login_required(redirect_field_name='ret', login_url='/loginpostulacion')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    hoy = datetime.now().date()
    adduserdata(request, data)
    persona = request.session['persona']
    postulante = request.session['postulante']
    perfilprincipal = request.session['perfilprincipal']
    data['url_'] = request.path
    data['inscripcion'] =None
    data['IS_DEBUG'] = IS_DEBUG = variable_valor('IS_DEBUG')
    if InscripcionPostulante.objects.values('id').filter(persona=persona).exists():
        data['inscripcion'] =  InscripcionPostulante.objects.filter(persona=persona)[0]
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'listadorequisitos':
            try:
                data['convocatoria'] = convocatoria = Convocatoria.objects.get(
                    pk=int(encrypt(request.POST['idconvocatoria'])))
                data['listadorequisitos'] = convocatoria.requisitosconvocatoria_set.filter(status=True)
                template = get_template("postu_requisitos/listadorequisitos.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'postular':
            try:
                convocatoria = Convocatoria.objects.get(pk=int(encrypt(request.POST['idcv'])))
                postu = InscripcionPostulante.objects.get(persona=persona, status=True)
                if postu:
                    inscripcion = InscripcionConvocatoria(postulante=postu, convocatoria=convocatoria)
                    postu.estado = 2
                    postu.save(request)
                    inscripcion.save()

                    if 'postulante' in request.session:
                        del request.session['postulante']
                    request.session['postulante'] = inscripcion
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'cargamasiva':
            try:
                inscripcionconvocatoria = InscripcionConvocatoria.objects.get(pk=request.POST['id'])
                listadorequisitosconvocatoria = RequisitosConvocatoria.objects.filter(
                    convocatoria=inscripcionconvocatoria.convocatoria, status=True)
                for requi in listadorequisitosconvocatoria:
                    nombrefile = 'requisito' + str(requi.id)
                    if nombrefile in request.FILES:
                        if not InscripcionConvocatoriaRequisitos.objects.filter(requisito=requi,
                                                                                inscripcionconvocatoria=inscripcionconvocatoria,
                                                                                status=True).exists():
                            requisitomaestria = InscripcionConvocatoriaRequisitos(requisito=requi,
                                                                                  inscripcionconvocatoria=inscripcionconvocatoria)
                            requisitomaestria.save(request)
                            newfile = request.FILES[nombrefile]
                            newfile._name = generar_nombre("requisitoconv_" + str(requi.id) + "_", newfile._name)
                            requisitomaestria.archivo = newfile
                            requisitomaestria.save(request)
                            log(u'Adicionó requisito de postulante convocatoria: %s' % requisitomaestria.requisito,
                                request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cargamasivageneral':
            try:
                listadorequisitosgennerales = RequisitoGenerales.objects.filter(status=True)
                for requi in listadorequisitosgennerales:
                    nombrefile = 'requisitogen' + str(requi.id)
                    if nombrefile in request.FILES:
                        if not RequisitoGeneralesPersona.objects.filter(requisitogeneral=requi, persona=persona,
                                                                        status=True).exists():
                            requisitogeneral = RequisitoGeneralesPersona(requisitogeneral=requi,
                                                                         persona=persona)
                            requisitogeneral.save(request)
                            newfile = request.FILES[nombrefile]
                            newfile._name = generar_nombre("requisitogen_" + str(requi.id) + "_", newfile._name)
                            requisitogeneral.archivo = newfile
                            requisitogeneral.save(request)
                            log(u'Adicionó requisito general de postulante convocatoria: %s' % requisitogeneral.requisitogeneral,
                                request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cargararchivo2':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                f = RequisitosConvocatoriaInscripcionForm(request.POST)
                if f.is_valid():
                    inscripcionconvocatoria = InscripcionConvocatoria.objects.get(pk=request.POST['id'])
                    requisitosconvocatoria = RequisitosConvocatoria.objects.get(pk=request.POST['idevidencia'])
                    if not InscripcionConvocatoriaRequisitos.objects.filter(requisito=requisitosconvocatoria,
                                                                            inscripcionconvocatoria=inscripcionconvocatoria,
                                                                            status=True).exists():
                        requisitoinscripcion = InscripcionConvocatoriaRequisitos(requisito=requisitosconvocatoria,
                                                                                 inscripcionconvocatoria=inscripcionconvocatoria)
                        requisitoinscripcion.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("requisitoconv_", newfile._name)
                            requisitoinscripcion.archivo = newfile
                            requisitoinscripcion.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile.size > 10485760:
                                return JsonResponse({"result": "bad",
                                                     "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                            else:
                                newfiles = request.FILES['archivo']
                                newfilesd = newfiles._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if not ext.lower() == '.pdf':
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        f = RequisitosConvocatoriaInscripcionForm(request.POST)
                        requisito = InscripcionConvocatoriaRequisitos.objects.get(requisito=requisitosconvocatoria,
                                                                                  inscripcionconvocatoria=inscripcionconvocatoria,
                                                                                  status=True)
                        if f.is_valid():
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("requisitoconv_", newfile._name)
                                requisito.archivo = newfile
                                requisito.save(request)
                            return JsonResponse({"result": "ok"})
                        else:
                            raise NameError('Error')
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cargararchivogeneral':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                f = RequisitosConvocatoriaInscripcionForm(request.POST)
                if f.is_valid():
                    requisitogeneral = RequisitoGenerales.objects.get(pk=request.POST['idevidencia'])
                    if not RequisitoGeneralesPersona.objects.filter(requisitogeneral=requisitogeneral, persona=persona,
                                                                    status=True).exists():
                        requisitogeneralpersona = RequisitoGeneralesPersona(requisitogeneral=requisitogeneral,
                                                                            persona=persona)
                        requisitogeneralpersona.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("requisitogen_", newfile._name)
                            requisitogeneralpersona.archivo = newfile
                            requisitogeneralpersona.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile.size > 10485760:
                                return JsonResponse({"result": "bad",
                                                     "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                            else:
                                newfiles = request.FILES['archivo']
                                newfilesd = newfiles._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if not ext.lower() == '.pdf':
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        f = RequisitosConvocatoriaInscripcionForm(request.POST)
                        requisito = RequisitoGeneralesPersona.objects.get(requisitogeneral=requisitogeneral,
                                                                          persona=persona, status=True)
                        if f.is_valid():
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("requisitogen_", newfile._name)
                                requisito.archivo = newfile
                                requisito.save(request)
                            return JsonResponse({"result": "ok"})
                        else:
                            raise NameError('Error')
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editdatopersonal':
            try:
                form = DatoPersonalForm(request.POST)
                persona = Persona.objects.get(pk=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    persona.apellido1 = form.cleaned_data['apellido1']
                    persona.apellido2 = form.cleaned_data['apellido2']
                    persona.nombres = form.cleaned_data['nombres']
                    persona.telefono = form.cleaned_data['telefono']
                    persona.email = form.cleaned_data['email']
                    persona.save(request)
                    log(u'Edito Dato Personal: %s' % persona, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'add_hoja_vida_postulante':
            try:
                form = ArchivoInvitacionForm(request.POST, request.FILES)
                pk = int (encrypt(request.POST.get('id')))
                eInscripcionPostulante = InscripcionPostulante.objects.get(pk=pk)
                if form.is_valid() and request.FILES.get('archivo', None):
                    newfile = request.FILES.get('archivo')
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):].lower()
                            if ext == '.pdf':
                                _name = generar_nombre(f"{eInscripcionPostulante.id.__str__()}._{eInscripcionPostulante.persona.__str__()}_", '')
                                _name = remover_caracteres_tildes_unicode( remover_caracteres_especiales_unicode(_name)).lower().replace(' ', '_').replace('-','_')
                                newfile._name = generar_nombre(u"%s_" % _name, f"{_name}.pdf")
                                eInscripcionPostulante.hoja_vida = newfile
                                eInscripcionPostulante.save(request)
                                messages.success(request, f'Actualizo documento hoja de vida')
                                log(u'subio hoja de vida: {}'.format(_name), request, "add")
                                return JsonResponse({"result": False}, safe=False)
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivos PDF"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error en el archivo"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'add_video_postulante':
            try:
                form = LinkVideoForm(request.POST)
                pk = int (encrypt(request.POST.get('id')))
                eInscripcionConvocatoria = InscripcionConvocatoria.objects.get(pk=pk)
                if form.is_valid():
                    eInscripcionConvocatoria.link = form.cleaned_data['link']
                    eInscripcionConvocatoria.save(request)
                    log(f'Actualizo link video clase posgrado {eInscripcionConvocatoria.link}', request,"add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error en el formulario.", "form": [{k: v[0]} for k, v in form.errors.items()]})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addexperienciapersona':
            try:
                form = ExperienciaLaboralForm(request.POST)
                persona = Persona.objects.get(pk=int(encrypt(request.POST['id'])))

                if form.is_valid():
                    experiencialaboral = ExperienciaLaboral(persona=persona,
                                                            institucion=form.cleaned_data['institucion'],
                                                            cargo=form.cleaned_data['cargo'],
                                                            fechainicio=form.cleaned_data['fechainicio'],
                                                            fechafin=form.cleaned_data['fechafin'] if not form.cleaned_data['vigente'] else None)
                    experiencialaboral.save(request)
                    log(u'Agregó experiencia laboral POSTULACIONDIP: %s (%s)' % (persona, experiencialaboral), request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error en el formulario.", "form": [{k: v[0]} for k, v in form.errors.items()]})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addinscripcionconvocatoria':
            try:
                form = ExperienciaLaboralForm(request.POST)
                persona = Persona.objects.get(pk=int(encrypt(request.POST['id'])))

                if form.is_valid():
                    fechafin = None
                    if not form.cleaned_data['vigente']:
                        fechafin = form.cleaned_data['fechafin']
                    experiencialaboral = ExperienciaLaboral(persona=persona,
                                                            institucion=form.cleaned_data['institucion'],
                                                            cargo=form.cleaned_data['cargo'],
                                                            fechainicio=form.cleaned_data['fechainicio'],
                                                            fechafin=fechafin)
                    experiencialaboral.save(request)
                    log(u'Agregar Experiencia: %s' % persona, request, "addexperienciapersona")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error en el formulario.", "form": [{k: v[0]} for k, v in form.errors.items()]})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editexperienciapersona':
            try:
                form = ExperienciaLaboralForm(request.POST)
                experiencia = ExperienciaLaboral.objects.get(pk=int(encrypt(request.POST['id'])))
                persona = Persona.objects.get(pk=int(experiencia.persona_id))

                if form.is_valid():
                    fechafin = None
                    if not form.cleaned_data['vigente']:
                        fechafin = form.cleaned_data['fechafin']
                    experiencia.institucion = form.cleaned_data['institucion']
                    experiencia.cargo = form.cleaned_data['cargo']
                    experiencia.fechainicio = form.cleaned_data['fechainicio']
                    experiencia.fechafin = fechafin
                    experiencia.save(request)
                    log(u'Agregar Experiencia: %s' % persona, request, "editexperienciapersona")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deleteexperienciapersona':
            try:
                with transaction.atomic():
                    idexpe = request.POST['id']
                    experienciapersona = ExperienciaLaboral.objects.get(pk=idexpe)
                    experienciapersona.delete()

                    log(u'Elimino Plantilla: %s' % experienciapersona, request, "deleteexperienciapersona")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'deleteactividad':
            try:
                with transaction.atomic():
                    idact = request.POST['id']
                    actividad = ActividadEconomica.objects.get(pk=idact)
                    actividad.delete()
                    log(u'Elimino actividad: %s' % actividad, request, "deleteactividad")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'rechazarinvitacion':
            try:
                with transaction.atomic():
                    ii = InscripcionInvitacion.objects.get(pk=request.POST['id'])
                    ii.estadoinvitacion = 5
                    ii.save(request)
                    InscripcionConvocatoria.objects.filter(pk=ii.inscripcion.pk, status=True).update(estadogen=3)
                    InscripcionPostulante.objects.filter(pk=ii.inscripcion.postulante.pk, status=True).update(estado=1)
                    log(u'Rechazó la invitacion de postulante: %s' % ii, request, "del")
                    ePersonalApoyoMaestrias = PersonalApoyoMaestria.objects.filter(status=True, carrera=ii.inscripcion.convocatoria.carrera, periodo=ii.inscripcion.convocatoria.periodo)
                    ii.notificar_estado_invitacion_a_analistas(request, ePersonalApoyoMaestrias,ii)
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'aceptarinvitacion':
            try:
                with transaction.atomic():
                    invitacion=InscripcionInvitacion.objects.get(pk=request.POST.get('id'))
                    dominio_sistema = 'http://127.0.0.1:8000'
                    if not IS_DEBUG:
                        dominio_sistema = 'https://sga.unemi.edu.ec'
                    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema
                    temp = lambda x: remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(x.__str__()))
                    # Validacion de choque de horario
                    # response = valida_choque_horario_pregrado(request, invitacion=invitacion)
                    # if not response.get('result'): return JsonResponse(response)

                    pasosiguiente = PasosProceso.objects.get(proceso=invitacion.pasosproceso.proceso, pasoanterior=invitacion.pasosproceso)
                    invitacion.pasosproceso = pasosiguiente
                    invitacion.estadoinvitacion = 4
                    invitacion.fechaaceptacion = hoy
                    invitacion.save(request)
                    historial = HistorialInvitacion(invitacion=invitacion, pasosproceso=pasosiguiente, fechaaceptacion=hoy, estadoinvitacion=4, observacion=u"Aceptó invitación")
                    historial.save()
                    postu = invitacion.inscripcion.postulante
                    postu.estado = 3
                    postu.save(request)
                    fecha = invitacion.fechaaceptacion
                    data['eInscripcionInvitacion'] = invitacion
                    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)

                    #
                    qrname = 'qr_certificado_cartaaceptacion_' + str(invitacion.id)
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'cartaaceptacionposgrado', 'qr'))
                    directory = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'cartaaceptacionposgrado'))
                    os.makedirs(f'{directory}/qr/', exist_ok=True)
                    try:
                        os.stat(directory)
                    except:
                        os.mkdir(directory)
                    nombrepersona = temp(invitacion.inscripcion.postulante.persona.__str__()).replace(' ', '_')
                    htmlname = 'cartaaceptacion_{}_{}'.format(nombrepersona, random.randint(1, 100000).__str__())
                    data['url_qr'] = url_qr = f'{SITE_STORAGE}/media/qrcode/cartaaceptacionposgrado/qr/{htmlname}.png'
                    url = pyqrcode.create(f'FIRMADO POR: {nombrepersona}\nfirmado desde https://sga.unemi.edu.ec\n FECHA: {datetime.today()}\n{dominio_sistema}/media/qrcode/cartaaceptacionposgrado/{htmlname}.pdf\n2.10.1')
                    imageqr = url.png(f'{directory}/qr/{htmlname}.png', 16, '#000000')
                    data['qrname'] = 'qr' + qrname
                    pdf_file, response = conviert_html_to_pdf_save_file_model(
                        'adm_postulacion/docs/cartaaceptacioninvitacion.html',
                        {'pagesize': 'A4', 'data': data},
                    )
                    #
                    invitacion.generar_acta_aceptacion(request, pdf_file)

                    ePersonalApoyoMaestrias = PersonalApoyoMaestria.objects.filter(status=True, carrera=invitacion.inscripcion.convocatoria.carrera, periodo=invitacion.inscripcion.convocatoria.periodo)
                    invitacion.notificar_estado_invitacion_a_analistas(request,ePersonalApoyoMaestrias,invitacion)

                    log(u'Acepto invitación: %s' % invitacion, request, "add")



                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'deletered':
            try:
                with transaction.atomic():
                    idredpersona = request.POST['id']
                    itemredpersona = RedPersona.objects.get(pk=idredpersona)
                    itemredpersona.delete()
                    log(u'Elimino red persona: %s' % itemredpersona, request, "deletered")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'guardafinalizar':
            try:
                with transaction.atomic():

                    listadoinvitacion=InscripcionInvitacion.objects.filter(inscripcion__postulante=postulante, pasosproceso_id=2, status=True, inscripcion__status=True, inscripcion__postulante__status=True)
                    InscripcionPostulante.objects.filter(id=postulante.pk, status=True).update(estado=4)
                    pasosiguiente = PasosProceso.objects.get(proceso_id=2, pasoanterior_id=2)
                    for invitacion in listadoinvitacion:
                        ePersonalApoyoMaestrias = PersonalApoyoMaestria.objects.filter(status=True,
                                                                                       carrera=invitacion.inscripcion.convocatoria.carrera,
                                                                                       periodo=invitacion.inscripcion.convocatoria.periodo)

                        invitacion.pasosproceso=pasosiguiente
                        invitacion.estado = 4 #revisión
                        invitacion.save(request)
                        historial = HistorialInvitacion(invitacion=invitacion,
                                                        pasosproceso=pasosiguiente,
                                                        fechaaceptacion=hoy,
                                                        estado=4,
                                                        observacion=u"Envió requisitos")
                        invitacion.notificar_subida_requisitos_completos_a_analistas(request, ePersonalApoyoMaestrias, invitacion)
                        historial.save(request)
                    log(u'Acepto invitación: %s' % invitacion, request, "aceptarinvitacion")
                    return JsonResponse({'result': 'ok'})
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'ponerprincipal':
            try:
                with transaction.atomic():
                    idprincipal = int(request.POST['idprincipal'])
                    listadoactividades=ActividadEconomica.objects.filter(persona=postulante.postulante.persona, status=True)
                    for actividad in listadoactividades:
                        if actividad.id == idprincipal:
                            actividad.principal = True
                        else:
                            actividad.principal = False
                        actividad.save(request)
                    log(u'Activo principal: %s' % actividad, request, "ponerprincipal")
                    return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar principal. %s" % ex.__str__()})

        elif action == 'chargefoto':
            persona = Persona.objects.get(pk=int(request.POST['id']))
            try:
                if not 'foto' in request.FILES:
                    raise NameError(f"Favor carge una foto")
                fotofile = request.FILES['foto']
                if fotofile.size > 524288:
                    raise NameError(u"Archivo mayor a 500Kb.")
                fotofileod = fotofile._name
                ext = fotofileod[fotofileod.rfind("."):]
                if not ext in ['.jpg']:
                    raise NameError(u"Solo archivo con extensión. jpg.")
                fotofile._name = generar_nombre("foto_", fotofile._name)
                foto = persona.foto()
                if foto:
                    foto.foto = fotofile
                else:
                    foto = FotoPersona(persona=persona, foto=fotofile)
                foto.save(request)
                make_thumb_picture(persona)
                if GENERAR_TUMBAIL:
                    make_thumb_fotopersona(persona)
                log(u'Adicionó foto de persona: %s' % foto, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente la foto')
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"La imagen seleccionada no cumple los requisitos. %s" % ex.__str__()})

        elif action == 'addtitulacion':
            try:
                persona = request.session['persona']
                f = TitulacionPersonaForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extencion = arch._name.split('.')
                    exte = extencion[-1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                    if not exte == 'pdf' and not exte == 'png' and not exte == 'jpg' and not exte == 'jpeg' and not exte == 'jpg':
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Archivo Título solo en formato .pdf, jpg, jpeg, png"})
                if 'registroarchivo' in request.FILES:
                    registroarchivo = request.FILES['registroarchivo']
                    extencion1 = registroarchivo._name.split('.')
                    exte1 = extencion1[1]
                    if registroarchivo.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                    if not exte1 == 'pdf' and not exte1 == 'png' and not exte1 == 'jpg' and not exte1 == 'jpeg' and not exte1 == 'jpg':
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Archivo SENESCYT solo en formato .pdf, jpg, jpeg, png"})
                if f.is_valid():
                    titulacion = Titulacion(persona=persona,
                                            titulo=f.cleaned_data['titulo'],
                                            # areatitulo=f.cleaned_data['areatitulo'],
                                            # fechainicio=f.cleaned_data['fechainicio'],
                                            fechaobtencion=f.cleaned_data['fechaobtencion'],
                                            # fechaegresado=f.cleaned_data['fechaegresado'],
                                            registro=f.cleaned_data['registro'],
                                            pais=f.cleaned_data['pais'],
                                            provincia=f.cleaned_data['provincia'],
                                            canton=f.cleaned_data['canton'],
                                            parroquia=f.cleaned_data['parroquia'],
                                            educacionsuperior=True,
                                            institucion=f.cleaned_data['institucion'])
                    titulacion.save(request)
                    if not titulacion.cursando:
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile:
                                newfile._name = generar_nombre("titulacion_", newfile._name)
                                titulacion.archivo = newfile
                                titulacion.save(request)
                        if 'registroarchivo' in request.FILES:
                            newfile2 = request.FILES['registroarchivo']
                            if newfile2:
                                newfile2._name = generar_nombre("archivosenecyt_", newfile2._name)
                                titulacion.registroarchivo = newfile2
                                titulacion.save(request)

                    campotitulo = None
                    if CamposTitulosPostulacion.objects.filter(status=True, titulo=f.cleaned_data['titulo']).exists():
                        campotitulo = CamposTitulosPostulacion.objects.filter(status=True,
                                                                              titulo=f.cleaned_data['titulo']).first()
                    else:
                        campotitulo = CamposTitulosPostulacion(titulo=f.cleaned_data['titulo'])
                        campotitulo.save(request)
                    for ca in f.cleaned_data['areaconocimiento']:
                        if not campotitulo.campoamplio.filter(id=ca.id):
                            campotitulo.campoamplio.add(ca)
                    for ce in f.cleaned_data['subareaconocimiento']:
                        if not campotitulo.campoespecifico.filter(id=ce.id):
                            campotitulo.campoespecifico.add(ce)
                    for cd in f.cleaned_data['subareaespecificaconocimiento']:
                        if not campotitulo.campodetallado.filter(id=cd.id):
                            campotitulo.campodetallado.add(cd)
                    campotitulo.save()

                    log(u'Adiciono titulacion: %s' % persona, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'cargaradicionartitulo':
            try:
                data['form'] = TituloHojaVidaPostulacionForm()
                template = get_template('postu_requisitos/addtitulo.html')
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

        elif action == 'addTitulo':
            try:
                f = TituloHojaVidaPostulacionForm(request.POST)
                if f.is_valid():
                    if Titulo.objects.filter(Q(nombre__unaccent=f.cleaned_data['nombre']) | Q(nombre__icontains=f.cleaned_data['nombre']) | Q(nombre=f.cleaned_data['nombre'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El titulo ya existe. Intente buscarlo sin acentos."})
                    titulo = Titulo(nombre=f.cleaned_data['nombre'],
                                    abreviatura=f.cleaned_data['abreviatura'],
                                    nivel=f.cleaned_data['nivel'],
                                    grado=f.cleaned_data['grado'],
                                    # areaconocimiento=f.cleaned_data['areaconocimiento'],
                                    # subareaconocimiento=f.cleaned_data['subareaconocimiento'],
                                    # subareaespecificaconocimiento=f.cleaned_data['subareaespecificaconocimiento']
                                    )
                    titulo.save(request)
                    log(u'Adiciono nuevo titulo desde postulacion: %s' % titulo, request, "add")
                    messages.success(request, 'Se guado exitosamente')
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edittitulacion':
            try:
                persona = request.session['persona']
                f = TitulacionPersonaForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extencion = arch._name.split('.')
                    exte = extencion[1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                    if not exte == 'pdf' and not exte == 'png' and not exte == 'jpg' and not exte == 'jpeg' and not exte == 'jpg':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf, jpg, jpeg, png"})

                if 'registroarchivo' in request.FILES:
                    registroarchivo = request.FILES['registroarchivo']
                    extencion1 = registroarchivo._name.split('.')
                    exte1 = extencion1[1]
                    if registroarchivo.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                    if not exte1 == 'pdf' and not exte1 == 'png' and not exte1 == 'jpg' and not exte1 == 'jpeg' and not exte1 == 'jpg':
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Archivo SENESCYT solo en formato .pdf, jpg, jpeg, png"})
                if f.is_valid():
                    titulacion = Titulacion.objects.get(pk=int(request.POST['id']))
                    titulacion.titulo = f.cleaned_data['titulo']
                    titulacion.fechaobtencion = f.cleaned_data['fechaobtencion']
                    titulacion.registro = f.cleaned_data['registro']
                    titulacion.pais = f.cleaned_data['pais']
                    titulacion.provincia = f.cleaned_data['provincia']
                    titulacion.canton = f.cleaned_data['canton']
                    titulacion.parroquia = f.cleaned_data['parroquia']
                    titulacion.educacionsuperior = True
                    titulacion.cursando = False
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("titulacion_", newfile._name)
                        titulacion.archivo = newfile
                    if 'registroarchivo' in request.FILES:
                        newfile2 = request.FILES['registroarchivo']
                        if newfile2:
                            newfile2._name = generar_nombre("archivosenecyt_", newfile2._name)
                            titulacion.registroarchivo = newfile2
                    titulacion.save(request)
                    campotitulo = None
                    if CamposTitulosPostulacion.objects.filter(status=True, titulo=f.cleaned_data['titulo']).exists():
                        campotitulo = CamposTitulosPostulacion.objects.filter(status=True, titulo=f.cleaned_data['titulo']).first()
                    else:
                        campotitulo = CamposTitulosPostulacion(titulo=f.cleaned_data['titulo'])
                        campotitulo.save(request)
                    for ca in f.cleaned_data['areaconocimiento']:
                        if not campotitulo.campoamplio.filter(id=ca.id):
                            campotitulo.campoamplio.add(ca)
                    for ce in f.cleaned_data['subareaconocimiento']:
                        if not campotitulo.campoespecifico.filter(id=ce.id):
                            campotitulo.campoespecifico.add(ce)
                    for cd in f.cleaned_data['subareaespecificaconocimiento']:
                        if not campotitulo.campodetallado.filter(id=cd.id):
                            campotitulo.campodetallado.add(cd)
                    campotitulo.save()
                    request.session['instruccion'] = 1
                    if Graduado.objects.filter(status=True, inscripcion__persona__id=persona.id).exists():
                        datos = Persona.objects.get(status=True, id=persona.id)
                        if 'personales' in request.session and 'nacimiento' in request.session and 'domicilio' in request.session and 'etnia' in request.session and 'instruccion' in request.session and datos.datosactualizados == 0:
                            if request.session['personales'] == 1 and request.session['nacimiento'] == 1 and \
                                    request.session['domicilio'] == 1 and request.session['etnia'] == 1 and \
                                    request.session['instruccion'] == 1 and datos.datosactualizados == 0:
                                datos.datosactualizados = 1
                                datos.save(request)
                    log(u'Modifico titulacion: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'deletetitulacion':
            try:
                with transaction.atomic():
                    idtit = request.POST['id']
                    itemtitulacion = Titulacion.objects.get(pk=idtit)
                    itemtitulacion.status = False
                    itemtitulacion.save()
                    log(u'Elimino Plantilla titulacion dip: %s' % itemtitulacion, request, "deletetitulacion")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'detalletitulo':
            try:
                data['titulacion'] = titulacion = Titulacion.objects.get(pk=int(request.POST['id']))
                data['eCamposTitulosPostulacion'] = eCamposTitulosPostulacion = CamposTitulosPostulacion.objects.filter(status=True,titulo = titulacion.titulo).first()
                dettitu = titulacion.detalletitulacionbachiller_set.filter(status=True)
                data['detalletitulacionbachiller'] = dettitu.last()
                if titulacion.usuario_creacion:
                    data['personacreacion'] = Persona.objects.get( usuario=titulacion.usuario_creacion) if titulacion.usuario_creacion.id > 1 else ""
                template = get_template("postu_requisitos/detalletitulo.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'detalle_convocatoria':
            try:
                id = request.POST.get('id',0)
                if id == 0:
                    JsonResponse({"result": "bad", "mensaje": u"Parametro no encontrado."})

                eConvocatoria =Convocatoria.objects.get(pk=id)
                data['eConvocatoria'] = eConvocatoria
                template = get_template("postu_requisitos/modal/detalle_convocatoria.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addred':
            try:
                f = RedPersonaForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                newredpersona = RedPersona(persona = persona,
                                           tipo = f.cleaned_data['tipo'],
                                           enlace = f.cleaned_data['enlace'])
                newredpersona.save(request)
                log(u'Ingreso Red : %s' % persona, request, "add")
                return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'editred':
            try:
                f = RedPersonaForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                editredpersona = RedPersona.objects.get(pk = request.POST['id'])
                editredpersona.tipo = f.cleaned_data['tipo']
                editredpersona.enlace = f.cleaned_data['enlace']
                editredpersona.save(request)
                log(u'Edición red: %s' % persona, request, "add")
                return JsonResponse({"result": False},safe=False)
                pass
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'datosdomicilio':
            try:
                if 'archivocroquis' in request.FILES:
                    newfile = request.FILES['archivocroquis']
                    if newfile.size > 2194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 2Mb"})
                persona = request.session['persona']
                f = DatosDomicilioForm(request.POST)
                if 'pais' in request.POST and request.POST['pais'] and int(request.POST['pais']) == 1:
                    if 'provincia' in request.POST and not request.POST['provincia']:
                        raise NameError('Debe ingresa una provincia')
                    if 'canton' in request.POST and not request.POST['canton']:
                        raise NameError('Debe ingresa una canton')
                    if 'parroquia' in request.POST and not request.POST['parroquia']:
                        raise NameError('Debe ingresa una parroquia')

                if f.is_valid():
                    newfile = None
                    persona.pais = f.cleaned_data['pais']
                    persona.provincia = f.cleaned_data['provincia']
                    persona.canton = f.cleaned_data['canton']
                    persona.sector = f.cleaned_data['sector']
                    persona.parroquia = f.cleaned_data['parroquia']
                    persona.direccion = f.cleaned_data['direccion']
                    persona.direccion2 = f.cleaned_data['direccion2']
                    persona.num_direccion = f.cleaned_data['num_direccion']
                    persona.telefono_conv = f.cleaned_data['telefono_conv']
                    persona.telefono = f.cleaned_data['telefono']
                    persona.tipocelular = f.cleaned_data['tipocelular']
                    persona.referencia = f.cleaned_data['referencia']
                    persona.save(request)
                    if 'archivocroquis' in request.FILES:
                        newfile = request.FILES['archivocroquis']
                        newfile._name = generar_nombre("croquis_", newfile._name)
                        persona.archivocroquis = newfile
                        persona.save(request)
                    log(u'Modifico datos de domicilio: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos, %s' % ex})

        elif action == 'addcuentabancaria':
            try:
                persona = request.session['persona']
                f = CuentaBancariaPersonaForm(request.POST)
                if f.is_valid():
                    cuentabancaria = CuentaBancariaPersona(persona=persona,
                                                           numero=f.cleaned_data['numero'],
                                                           banco=f.cleaned_data['banco'],
                                                           tipocuentabanco=f.cleaned_data['tipocuentabanco'], )
                    cuentabancaria.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            newfile._name = generar_nombre("cuentabancaria_", newfile._name)
                            cuentabancaria.archivo = newfile
                            cuentabancaria.save(request)
                    log(u'Adiciono cuenta bancaria: %s' % persona, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'editcuentabancaria':
            try:
                persona = request.session['persona']
                f = CuentaBancariaPersonaForm(request.POST)
                if f.is_valid():
                    cuentabancaria = CuentaBancariaPersona.objects.get(pk=int(request.POST['id']))
                    if persona.cuentabancariapersona_set.filter(numero=f.cleaned_data['numero']).exclude(
                            id=cuentabancaria.id).exists():
                        return JsonResponse(
                            {'result': 'bad', 'mensaje': u'La cuenta bancaria se encuentra registrada.'})
                    if cuentabancaria.verificado:
                        return JsonResponse({'result': 'bad', 'mensaje': u'No puede modificar la cuenta bancaria, ya que está validada por talento humano.'})
                    cuentabancaria.numero = f.cleaned_data['numero']
                    cuentabancaria.banco = f.cleaned_data['banco']
                    cuentabancaria.tipocuentabanco = f.cleaned_data['tipocuentabanco']
                    cuentabancaria.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            newfile._name = generar_nombre("cuentabancaria_", newfile._name)
                            cuentabancaria.archivo = newfile
                            cuentabancaria.save(request)
                    log(u'Modifico cuenta bancaria: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'delcuentabancaria':
            try:
                persona = request.session['persona']
                cuentabancaria = CuentaBancariaPersona.objects.get(pk=int(request.POST['id']))
                if cuentabancaria.verificado:
                    return JsonResponse({'result': 'bad', 'mensaje': u'No puede eliminar la cuenta bancaria.'})
                log(u'Elimino cuenta bancaria: %s' % cuentabancaria, request, "del")
                cuentabancaria.delete()
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al eliminar los datos'})

        elif action == 'delconvocatoria':
            try:
                convocatoria = InscripcionConvocatoria.objects.get(pk=int(encrypt(request.POST['id'])))
                convocatoria.status = False
                convocatoria.save(request)
                log(u'Elimino convocatoria: %s' % convocatoria, request, "del")
                return JsonResponse({"result": "ok", "mensaje":u"Inscripción Convocatoria eliminada correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al eliminar los datos'})

        elif action == 'discapacidad':
            try:
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                persona = request.session['persona']
                f = DiscapacidadForm(request.POST, request.FILES)
                if f.is_valid():
                    newfile = None
                    perfil = persona.mi_perfil()
                    perfil.tienediscapacidad = f.cleaned_data['tienediscapacidad']
                    perfil.tipodiscapacidad = f.cleaned_data['tipodiscapacidad']
                    perfil.porcientodiscapacidad = f.cleaned_data['porcientodiscapacidad'] if f.cleaned_data[
                        'porcientodiscapacidad'] else 0
                    perfil.carnetdiscapacidad = f.cleaned_data['carnetdiscapacidad']
                    perfil.institucionvalida = f.cleaned_data['institucionvalida']

                    if not f.cleaned_data['tienediscapacidad']:
                        perfil.archivo = None
                        perfil.estadoarchivodiscapacidad = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivosdiscapacidad_", newfile._name)
                        perfil.archivo = newfile
                        perfil.estadoarchivodiscapacidad = 1

                    perfil.save(request)
                    log(u'Modifico tipo de discapacidad: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'addactividadeconomica':
            try:
                idpersona = request.POST['idpersona']
                listaactividad = request.POST['lista'].split(',')
                for elemento in listaactividad:
                    actividad = ActividadEconomica(actividad_id=elemento,
                                                   principal=False,
                                                   persona_id=idpersona)
                    actividad.save()
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cargararchivo':
            try:
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        newfile._name = generar_nombre("requisitoconvocatoria_", newfilesd)

                f = RequisitosConvocatoriaInscripcionForm(request.POST)
                f.del_observacion()
                if f.is_valid():
                    inscripcioninvitacion = InscripcionInvitacion.objects.get(pk=request.POST['id'])
                    if pk := int(request.POST.get('pk', 0)):
                        icr = InscripcionConvocatoriaRequisitos.objects.get(pk=pk)
                    else:
                        icr = InscripcionConvocatoriaRequisitos(inscripcioninvitacion=inscripcioninvitacion, requisito_id=request.POST['idevidencia'], observacion='Ninguna', estado=1)

                    ha = HistorialAprobacion(inscripcionrequisito=icr, observacion='Ninguna', estado=1, tiporevision=1)
                    if newfile:
                        icr.archivo = ha.archivo = newfile

                    icr.save(request)
                    ha.save(request)
                    log(u'Editó inscripcion convocatoria requisito de postulaciondip: %s' % icr, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error en el formulario, algunos campos se encuentran vacíos.')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        elif action == 'cargararchivopostulante':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                f = RequisitosInscripcionForm(request.POST)
                if f.is_valid():
                    postulante = request.session['postulante']
                    postuinvitacion = InscripcionInvitacion.objects.filter(inscripcion__postulante=postulante).order_by('-id').first()
                    requisito = RequisitosProceso.objects.get(pk=int(request.POST['idevidencia']), status=True)
                    if not InscripcionRequisito.objects.filter(inscripcioninvitacion=postuinvitacion,requisitoproceso=requisito,status=True).exists():
                        insrequisito = InscripcionRequisito(inscripcioninvitacion=postuinvitacion,
                                                            requisitoproceso=requisito)
                        insrequisito.save(request)
                        historial = HistorialAprobacionInscripcion(inscripcionrequisito=insrequisito,
                                                                   estado=insrequisito.estado,
                                                                   tiporevision=1,
                                                                   observacion='Ninguna')
                        historial.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("requisitopgrado_", newfile._name)
                            insrequisito.archivo = newfile
                            insrequisito.save(request)
                        log(u'Adicionó requisito de postulaciondip: %s' % insrequisito, request,"add")
                        return JsonResponse({"result": "ok"})
                    else:
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                            else:
                                newfiles = request.FILES['archivo']
                                newfilesd = newfiles._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if not ext.lower() == '.pdf':
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        f = RequisitosInscripcionForm(request.POST)
                        insrequisito = InscripcionRequisito.objects.get(inscripcioninvitacion=postuinvitacion,requisitoproceso=requisito,status=True)
                        insrequisito.estado=1
                        insrequisito.observacion=''
                        insrequisito.save(request)
                        historial = HistorialAprobacionInscripcion(inscripcionrequisito=insrequisito,
                                                                   estado=insrequisito.estado,
                                                                   tiporevision=1,
                                                                   observacion='Ninguna')
                        historial.save(request)
                        if f.is_valid():
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("requisitopgrado_", newfile._name)
                                insrequisito.archivo = newfile
                                insrequisito.save(request)
                            log(u'Editó requisito de postulaciondip: %s' % insrequisito, request, "edit")
                            return JsonResponse({"result": "ok"})
                        else:
                            raise NameError('Error')
                else:
                    raise NameError('Error en el formulario, algunos campos se encuentran vacíos.')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'datospersonales':
            try:
                persona = request.session['persona']
                persona = Persona.objects.get(id=persona.id)
                f = DatosPersonalesForm(request.POST, request.FILES)
                if 'archivocedula' in request.FILES:
                    arch = request.FILES['archivocedula']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if f.is_valid():
                    persona.pasaporte = f.cleaned_data['pasaporte']
                    persona.anioresidencia = f.cleaned_data['anioresidencia']
                    persona.nacimiento = f.cleaned_data['nacimiento']
                    persona.nacionalidad = f.cleaned_data['nacionalidad']
                    persona.sexo = f.cleaned_data['sexo']
                    persona.email = f.cleaned_data['email']
                    persona.libretamilitar = f.cleaned_data['libretamilitar']
                    persona.save(request)
                    personaextension = persona.datos_extension()
                    personaextension.estadocivil = f.cleaned_data['estadocivil']
                    personaextension.save(request)

                    if 'archivocedula' in request.FILES:
                        newfile = request.FILES['archivocedula']
                        newfile._name = generar_nombre("cedula", newfile._name)

                        documento = persona.documentos_personales()
                        if documento is None:
                            documento = PersonaDocumentoPersonal(persona=persona,
                                                                 cedula=newfile,
                                                                 estadocedula=1)
                        else:
                            documento.cedula = newfile
                            documento.estadocedula = 1

                        documento.save(request)

                    if 'papeleta' in request.FILES:
                        newfile = request.FILES['papeleta']
                        newfile._name = generar_nombre("papeleta", newfile._name)

                        documento = persona.documentos_personales()
                        if documento is None:
                            documento = PersonaDocumentoPersonal(persona=persona,
                                                                 papeleta=newfile,
                                                                 estadopapeleta=1)
                        else:
                            documento.papeleta = newfile
                            documento.estadopapeleta = 1

                        documento.save(request)

                    if 'archivolibretamilitar' in request.FILES:
                        newfile = request.FILES['archivolibretamilitar']
                        newfile._name = generar_nombre("libretamilitar", newfile._name)

                        documento = persona.documentos_personales()
                        if documento is None:
                            documento = PersonaDocumentoPersonal(persona=persona,
                                                                 libretamilitar=newfile,
                                                                 estadolibretamilitar=1)
                        else:
                            documento.libretamilitar = newfile
                            documento.estadolibretamilitar = 1
                        documento.save(request)
                    log(u'Modifico datos personales: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'cambiarestadoinscripcion':
            try:
                inscripcion = InscripcionPostulante.objects.get(pk=int(request.POST['id']))
                inscripcion.estado=2
                inscripcion.save(request)
                if 'postulante' in request.session:
                    del request.session['postulante']
                request.session['postulante'] = inscripcion
                send_html_mail("Finalización de registro",
                               "postu_requisitos/email/finalizacionregistro.html",
                               {'sistema': u'POSTULACION - UNEMI',
                                'inscripcion': inscripcion,
                                },
                               inscripcion.persona.lista_emails(),
                               [],
                               cuenta=CUENTAS_CORREOS[31][1]
                               )
                log(u'finaliza registro en el sistema de selección docentes posgrado: %s' %inscripcion , request, "del")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al eliminar los datos'})

        elif action == 'subareaconocimiento':
            try:
                areaconocimiento = request.POST['id'][:-1]
                listAc = areaconocimiento
                if len(areaconocimiento) > 1:
                    listAc = areaconocimiento.split(',')
                lista = []
                for subarea in SubAreaConocimientoTitulacion.objects.filter(areaconocimiento_id__in=listAc, status=True, tipo=1):
                    lista.append([subarea.id, subarea.nombre])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'subareaespecificaconocimiento':
            try:
                listarea = request.POST.get('id[]')
                if len(listarea) > 1:
                    listarea = listarea.split(',')

                lista = []
                for subarea in SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True,
                                                                                      areaconocimiento_id__in=listarea, tipo=1):
                    lista.append([subarea.id, subarea.nombre])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'agregardatosextra':
            try:
                ip = InscripcionConvocatoria.objects.get(pk=int(encrypt(request.POST['id'])))
                form = DatoPersonalExtraForm(request.POST, request.FILES)
                if form.is_valid():
                    ip.link = form.cleaned_data['link']
                    ip.save(request)
                    return JsonResponse({"result": False}, safe=False)
                    pass
                else:
                    return JsonResponse({"result": False, "mensaje": u"Error al validar los datos."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error de conexión."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'seguimientopostulacion':
                try:
                    convocatoria = Convocatoria.objects.get(pk=request.GET.get('pk'))
                    candidaturas = InscripcionConvocatoria.objects.filter(postulante__persona=persona, convocatoria=convocatoria, status=True).first()

                    data['candidaturas'] = candidaturas
                    data['convocatoria'] = convocatoria
                    template = get_template("postu_requisitos/modal/seguimientopostulacion.html")
                    json_content = template.render(data)
                    return JsonResponse({'result': 'ok', 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'listsubareaconocimiento':
                try:
                    campoamplio = request.GET.get('campoamplio')
                    listcampoamplio = campoamplio
                    if len(campoamplio) > 1:
                        listcampoamplio = campoamplio.split(',')
                    querybase = SubAreaConocimientoTitulacion.objects.filter(status=True,
                                                                             areaconocimiento__in=listcampoamplio).order_by(
                        'codigo')
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[
                                        :30]
                    data = {"result": "ok", "results": [
                        {"id": x.id, "idca": x.areaconocimiento.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x
                        in
                        querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'listadoactividadeconomica':
                try:
                    lista = []
                    idpersona=request.GET['idpersona']
                    listadoactividad = ClasificacionAC.objects.filter(status=True, activo=True).exclude(pk__in=ActividadEconomica.objects.values_list('actividad_id').filter(persona_id=idpersona,status=True)).order_by('codigo')
                    for lis in listadoactividad:
                        lista.append([lis.id, lis.codigo, lis.descripcion, lis.nivel])
                    data = {"results": "ok", 'listadoactividad': lista}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'cargararchivo':
                try:
                    data['title'] = u'Evidencias de requisitos de maestría'
                    data['id'] = request.GET.get('id')
                    data['idevidencia'] = request.GET['idevidencia']
                    requisito = RequisitosConvocatoria.objects.get(pk=int(request.GET['idevidencia']), status=True)
                    form = RequisitosConvocatoriaInscripcionForm()
                    form.del_observacion()
                    data['form2'] = form
                    data['pk'] = request.GET.get('pk')
                    template = get_template("postu_requisitos/modal/formmodal_b5.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content,
                                         "nombre": "SUBIR DOCUMENTO DE REQUISITO " + str(requisito.requisito.nombre)})
                except Exception as ex:
                    pass

            elif action == 'cargararchivopostulante':
                try:
                    data['title'] = u'Evidencias de requisitos de maestría'
                    data['id'] = request.GET['id']
                    data['idevidencia'] = request.GET['idevidencia']
                    requisito = RequisitosProceso.objects.get(pk=int(request.GET['idevidencia']), status=True)
                    form = RequisitosInscripcionForm()
                    data['form'] = form
                    template = get_template("postu_requisitos/cargararchivopostulante.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, "nombre": "SUBIR DOCUMENTO DE REQUISITO " + str(requisito.requisito.nombre)})
                except Exception as ex:
                    pass

            elif action == 'datosdomicilio':
                try:
                    data['title'] = u'Datos de domicilio'
                    form = DatosDomicilioForm(initial={'pais': persona.pais,
                                                       'provincia': persona.provincia,
                                                       'canton': persona.canton,
                                                       'parroquia': persona.parroquia,
                                                       'direccion': persona.direccion,
                                                       'direccion2': persona.direccion2,
                                                       'sector': persona.sector,
                                                       'num_direccion': persona.num_direccion,
                                                       'referencia': persona.referencia,
                                                       'telefono': persona.telefono,
                                                       'telefono_conv': persona.telefono_conv,
                                                       'tipocelular': persona.tipocelular})
                    form.editar(persona)
                    data['form'] = form
                    return render(request, "postu_requisitos/datosdomicilio.html", data)
                except Exception as ex:
                    pass

            elif action == 'discapacidad':
                try:
                    data['title'] = u'Discapacidad'
                    perfil = persona.mi_perfil()
                    form = DiscapacidadForm(initial={'tienediscapacidad': perfil.tienediscapacidad,
                                                     'tipodiscapacidad': perfil.tipodiscapacidad,
                                                     'porcientodiscapacidad': perfil.porcientodiscapacidad,
                                                     'carnetdiscapacidad': perfil.carnetdiscapacidad,
                                                     'institucionvalida': perfil.institucionvalida})
                    tienearchivo = True if perfil.archivo else False
                    data['form'] = form
                    data['tienearchivo'] = tienearchivo
                    return render(request, "postu_requisitos/discapacidad.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcuentabancaria':
                try:
                    data['title'] = u'Adicionar cuenta bancaria'
                    data['form'] = CuentaBancariaPersonaForm()
                    return render(request, "postu_requisitos/addcuentabancaria.html", data)
                except Exception as ex:
                    pass
            # EDITAR CUENTA POST#--------

            # ELIMINAR CUENTA POST-------

            #EDITAR CUENTA GET#--------
            elif action == 'editcuentabancaria':
                try:
                    data['title'] = u'Editar cuenta bancaria'
                    data['cuentabancaria'] = cuentabancaria = CuentaBancariaPersona.objects.get(
                        pk=int(request.GET['id']))
                    data['form'] = CuentaBancariaPersonaForm(initial={'numero': cuentabancaria.numero,
                                                                      'banco': cuentabancaria.banco,
                                                                      'tipocuentabanco': cuentabancaria.tipocuentabanco})
                    return render(request, "postu_requisitos/editcuentabancaria.html", data)
                except Exception as ex:
                    pass

            #---------------------------------

            elif action == 'cargararchivogeneral':
                try:
                    data['title'] = u'Evidencias de requisito general'
                    data['id'] = request.GET['id']
                    data['idevidencia'] = request.GET['idevidencia']
                    requisito = RequisitoGenerales.objects.get(pk=int(request.GET['idevidencia']), status=True)
                    form = RequisitosConvocatoriaInscripcionForm()
                    data['form'] = form
                    template = get_template("postu_requisitos/add_requisitogeneral.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content,
                                         "nombre": "SUBIR DOCUMENTO DE REQUISITO " + str(requisito.requisito.nombre)})
                except Exception as ex:
                    pass

            elif action == 'mispostulaciones':
                try:
                    data['title'] = u'Listado de postulaciones'
                    data['listadomisconvocatorias'] = postulante.inscripcionconvocatoria_set.filter(status=True)
                    return render(request, "postu_requisitos/mispostulaciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadopostulaciones':
                try:
                    data['title'] = u'Listado de postulaciones'
                    mispostulaciones = postulante.inscripcionconvocatoria_set.values_list('convocatoria_id').filter(
                        status=True)
                    data['listadoconvocatorias'] = Convocatoria.objects.filter(activo=True, status=True).exclude(
                        pk__in=mispostulaciones)
                    return render(request, "postu_requisitos/listadopostulaciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'editdatopersonal':
                try:
                    persona = Persona.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['id'] = int(encrypt(request.GET['id']))
                    data['form'] = DatoPersonalForm(initial={'apellido1': persona.apellido1,
                                                             'apellido2': persona.apellido2,
                                                             'nombres': persona.nombres,
                                                             'telefono': persona.telefono,
                                                             'email': persona.email})
                    template = get_template("postu_requisitos/modal/editdatopersonal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'add_hoja_vida_postulante':
                try:
                    pk = int(request.GET.get('id','0'))
                    eInscripcionPostulante = InscripcionPostulante.objects.get(pk=pk)
                    data['eInscripcionPostulante '] = eInscripcionPostulante
                    data['id'] = eInscripcionPostulante.pk
                    data['form'] = form = ArchivoInvitacionForm()
                    template = get_template("postu_requisitos/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'add_video_postulante':
                try:
                    pk = int(request.GET.get('id','0'))
                    eInscripcionConvocatoria = InscripcionConvocatoria.objects.get(pk=pk)
                    data['eInscripcionConvocatoria '] = eInscripcionConvocatoria
                    data['id'] = eInscripcionConvocatoria.pk
                    data['form'] = form = LinkVideoForm()
                    template = get_template("postu_requisitos/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addexperienciapersona':
                try:
                    persona = Persona.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['id'] = int(encrypt(request.GET['id']))
                    data['form'] = ExperienciaLaboralForm()
                    template = get_template("postu_requisitos/modal/addexperienciapersona.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editexperienciapersona':
                try:
                    filtro = ExperienciaLaboral.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['id'] = int(encrypt(request.GET['id']))
                    form = ExperienciaLaboralForm(initial=model_to_dict(filtro))
                    if filtro.fechafin is None:
                        form.initial['vigente'] = True

                    data['form'] = form
                    template = get_template("postu_requisitos/modal/addexperienciapersona.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addred':
                try:
                    data['form2'] = RedPersonaForm()
                    template = get_template("postu_requisitos/modal/addred.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editred':
                try:
                    data['title'] = u"Editar Red"
                    data['red'] = red = RedPersona.objects.get(pk = request.GET['id'])
                    initial = model_to_dict(red)
                    data['id'] = red.pk
                    data['form2'] = RedPersonaForm(initial=initial)
                    template = get_template("postu_requisitos/modal/addred.html")
                    return JsonResponse({"result":True,"data":template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'chargefoto':
                try:
                    data['persona'] = Persona.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['id'] = int(encrypt(request.GET['id']))
                    data['title'] = u'Subir foto'
                    template = get_template("postu_requisitos/modal/chargefoto.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'requisitospreaprobados':
                try:
                    data['title'] = u"Requisitos de Contratación"
                    data['invitacion'] = invitacion = InscripcionInvitacion.objects.get(pk=request.GET.get('id'))
                    data['personaposgrado'] = Persona.objects.get(pk=persona.id)
                    ePersonalAContratar = invitacion.get_personal_a_contratar()
                    data['listadorequisitos'] = ePersonalAContratar.get_requisitos_convocatoria_para_postulante()
                    data['invitacionesaceptadas'] = invitacion.pasosproceso_id == 2
                    cantidad_requisitos_configurados= ePersonalAContratar.get_requisitos_configurados().filter(estado_requisito__in = (3,1),requisitoconvocatoria__opcional = False).count()
                    data['puede_enviar_requisitos'] = True if invitacion.listadorequisitoscargados().filter(archivo ='',requisito__opcional = False).count() == 0 and (cantidad_requisitos_configurados == invitacion.listadorequisitoscargados().exclude(archivo='').filter(requisito__opcional = False).count())  else False

                    return render(request, 'postu_requisitos/requisitospreaprobados.html', data)
                except Exception as ex:
                    pass

            elif action == 'listadorequisitosinscripcion':
                try:
                    data['title'] = u'Listado de requisitos'
                    data['inscripcionconvocatoria'] = inscripcionconvocatoria = InscripcionConvocatoria.objects.get(pk=request.GET.get('id'))
                    data['requisitosgenerales'] = RequisitoGenerales.objects.filter(status=True)
                    ventanaactiva = 1

                    try:
                        data['permisorequisito'] = inscripcionconvocatoria.convocatoria.fechafinrequisito >= hoy
                        data['tienerequisitos'] = inscripcionconvocatoria.inscripcionconvocatoriarequisitos_set.filter(status=True).exists()
                        if persona.requisitogeneralespersona_set.filter(status=True).exists():
                            ventanaactiva = 2
                            data['tienerequisitosgenerales'] = True
                    except Exception as ex:
                        pass

                    data['persona'] = persona
                    data['ventanaactiva'] = ventanaactiva
                    return render(request, "postu_requisitos/listadorequisitosinscripcion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addtitulacion':
                try:
                    data['title'] = u'Adicionar titulación'
                    form = TitulacionPersonaForm()
                    form.fields['titulo'].queryset = Titulo.objects.none()
                    form.adicionar()
                    data['form'] = form

                    if 't' in request.GET:
                        if CamposTitulosPostulacion.objects.filter(titulo_id=int(request.GET['t']), status=True).exists():
                            titulo = CamposTitulosPostulacion.objects.filter(titulo_id=int(request.GET['t']), status=True).first()
                            list_ca = titulo.campoamplio.values_list('id', 'codigo', 'nombre').filter(status=True)
                            list_ce = titulo.campoespecifico.values_list('id', 'codigo', 'nombre').filter(status=True)
                            list_cd = titulo.campodetallado.values_list('id', 'codigo', 'nombre').filter(status=True)
                            data = {"result": "ok",
                                    "areacon": [{"id": x[0], "name": "[{}] - {}".format(x[1], x[2])} for x in list(list_ca) if list_ca],
                                    "subareacon": [{"id": x[0], "name": "[{}] - {}".format(x[1], x[2])} for x in list(list_ce) if list_ce],
                                    "subareaespecon": [{"id": x[0], "name": "[{}] - {}".format(x[1], x[2])} for x in list(list_cd) if list_cd]}
                            # else:
                            #     data = {"result": "bad"}
                        else:
                            data = {"result": "bad"}
                        return JsonResponse(data)
                    return render(request, "postu_requisitos/addtitulacion.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/?info=Error de conexión.")

            elif action == 'edittitulacion':
                try:
                    data['title'] = u'Editar titulación'
                    data['titulacion'] = titulacion = Titulacion.objects.get(pk=int(request.GET['id']))
                    campotitulo, campoamplio, campoespecifico, campodetallado = None, None, None, None
                    if CamposTitulosPostulacion.objects.filter(status=True, titulo=titulacion.titulo).exists():
                        campotitulo = CamposTitulosPostulacion.objects.filter(status=True, titulo=titulacion.titulo).first()
                        campoamplio = AreaConocimientoTitulacion.objects.filter(status=True,id__in=campotitulo.campoamplio.all().values_list('id', flat=True))
                        campoespecifico = SubAreaConocimientoTitulacion.objects.filter(status=True,id__in=campotitulo.campoespecifico.all().values_list('id', flat=True))
                        campodetallado = SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True,id__in=campotitulo.campodetallado.all().values_list('id', flat=True))
                    form = TitulacionPersonaForm(initial={'titulo': titulacion.titulo,
                                                          'areatitulo': titulacion.areatitulo,
                                                          'fechainicio': titulacion.fechainicio,
                                                          'institucion': titulacion.institucion,
                                                          'fechaobtencion': titulacion.fechaobtencion if not titulacion.cursando else datetime.now().date(),
                                                          'fechaegresado': titulacion.fechaegresado if not titulacion.cursando else datetime.now().date(),
                                                          'registro': titulacion.registro,
                                                          'pais': titulacion.pais,
                                                          'provincia': titulacion.provincia,
                                                          'canton': titulacion.canton,
                                                          'parroquia': titulacion.parroquia,
                                                          'areaconocimiento': campoamplio,
                                                          'subareaconocimiento': campoespecifico,
                                                          'subareaespecificaconocimiento': campodetallado,
                                                          })
                    form.editar(titulacion)
                    data['form'] = form
                    return render(request, "postu_requisitos/edittitulacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscartitulos':
                try:
                    q = request.GET['q'].upper().strip()
                    querybase = Titulo.objects.filter(nivel__status=True, status=True)
                    per = querybase.filter((Q(nombre__icontains=q) | Q(abreviatura__icontains=q))).distinct()
                    data = {"result": "ok", "results": [{"id": x.id, "name": f"{x.abreviatura} - {x.nombre}"} for x in per[:10]] if len(per) else []}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'datospersonales':
                try:
                    data['title'] = u'Datos personales'
                    persona = Persona.objects.get(id=persona.id)
                    form = DatosPersonalesForm(initial={'nombres': persona.nombres,
                                                        'apellido1': persona.apellido1,
                                                        'apellido2': persona.apellido2,
                                                        'cedula': persona.cedula,
                                                        'pasaporte': persona.pasaporte,
                                                        'sexo': persona.sexo,
                                                        'anioresidencia': persona.anioresidencia,
                                                        'nacimiento': persona.nacimiento,
                                                        'nacionalidad': persona.nacionalidad,
                                                        'email': persona.email,
                                                        'estadocivil': persona.estado_civil(),
                                                        'libretamilitar': persona.libretamilitar,
                                                        'estadogestacion': persona.estadogestacion,
                                                        })
                    form.editar()
                    data['form'] = form
                    data['persona'] = persona
                    banderalibreta = 0
                    banderapapeleta = 0
                    banderacedula = 0
                    documentos = PersonaDocumentoPersonal.objects.filter(persona=persona)
                    if documentos:
                        if documentos[0].libretamilitar:
                            banderalibreta = 1
                        if documentos[0].papeleta:
                            banderapapeleta = 1
                        if documentos[0].cedula:
                            banderacedula = 1

                    data['banderacedula'] = banderacedula
                    data['banderalibreta'] = banderalibreta
                    data['banderapapeleta'] = banderapapeleta
                    return render(request, "postu_requisitos/datospersonales.html", data)
                except Exception as ex:
                    pass

            elif action == 'validar_choque_horario_postulacion':
                id_convocatoria = int(request.GET.get('id_convocatoria','0'))
                if  id_convocatoria == 0:
                    raise NameError("Parametro no encotrado.")
                eConvocatoria = Convocatoria.objects.get(pk=id_convocatoria)
                if eConvocatoria.get_horario().exists():
                    # Validacion de choque de horario
                    response = valida_choque_horario_pregrado_pre_postulacion(request, persona=persona, horarioClases=eConvocatoria.get_horario())
                    if response.get('puede'):
                        response = valida_choque_horario_en_actas_generadas_pre_postulacion(request, persona=persona , horarioClases=eConvocatoria.get_horario())

                    return JsonResponse(response)
                else:
                    return JsonResponse({'result': True,'puede':True})

            elif action == 'agregardatosextra':
                try:
                    data['inscripcion'] = ip = InscripcionConvocatoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = form = DatoPersonalExtraForm()
                    form.del_archivo()
                    data['id'] = ip.pk
                    data['action'] = 'agregardatosextra'
                    template = get_template('postu_requisitos/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": str(ex)})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Administración del sistema'

                if persona.sexo.id == 1:
                    icon_user_access_profile = "/static/images/iconos/user_access_profile_women.png"
                elif persona.sexo.id == 2:
                    icon_user_access_profile = "/static/images/iconos/user_access_profile_men.png"
                else:
                    icon_user_access_profile = "/static/images/iconos/user_access_profile.png"
                menu_panel = [
                    {"url": "/postu_requisitos?action=mispostulaciones",
                     "img": "/static/images/iconos/users.png",
                     "title": "Mi Postulaciones",
                     "description": "Listado de todas mis postulaciones",
                     },
                    {"url": "/postu_requisitos?action=listadopostulaciones",
                     "img": "/static/images/iconos/groups.png",
                     "title": "Postulaciones",
                     "description": "Listado de postulaciones",
                     },
                    {"url": "/th_hojavida",
                     "img": "/static/images/iconos/hojadevida.png",
                     "title": "Hoja de vida",
                     "description": "Actualizar ficha de datos personales",
                     },
                ]
                data['menu_panel'] = menu_panel
                #return render(request, "postu_requisitos/inscripcionpostulacion.html", data)
                return HttpResponseRedirect("/")
            except Exception as ex:
                pass


def valida_choque_horario_pregrado(request, **kwargs):
    from sga.models import Clase, ProfesorMateria
    from .models import HorarioClases
    try:
        persona = request.session.get('persona')
        invitacion = kwargs.pop('invitacion', None)
        personal = invitacion.inscripcion.personalacontratar_set.filter(actaparalelo__acta__actaconvocatoria__convocatoria=invitacion.inscripcion.convocatoria, tipoinscripcion=1, status=True)
        paralelos = [p.actaparalelo for p in personal]

        if paralelos:
            horariosclases = HorarioClases.objects.filter(actaparalelo__in=paralelos)
            for horario in horariosclases:
                lista_turnos = horario.turno.all()
                dia = horario.dia
                inicio = horario.inicio
                fin = horario.fin
                profesormateria = ProfesorMateria.objects.filter(profesor__persona=persona, materia__cerrado=False, materia__inicio__lte=inicio, materia__fin__gte=fin)
                for pm in profesormateria:
                    tipoprofesor = pm.tipoprofesor
                    periodo = pm.materia.nivel.periodo
                    profesor = pm.profesor
                    materia = pm.materia
                    claseconflicto = Clase.objects.filter(Q(inicio__lte=inicio, fin__gte=inicio) | Q(inicio__lte=fin, fin__gte=fin) | Q(inicio__gte=inicio, fin__lte=fin), Q(turno=turno, dia=dia, activo=True, materia__cerrado=False, profesor=profesor))
                    if claseconflicto: raise NameError(u"El profesor ya tiene asignada una materia en ese turno y día.")

                    # CONFLICTO OTRAS CLASES
                    if not ProfesorMateria.objects.filter(profesor=profesor, novalidahorario=True, activo=True, tipoprofesor=profesor, materia=materia).exists():
                        if claseconflicto.values('id').filter(tipoprofesor=profesor, profesor=profesor, materia__asignatura_id=materia.asignatura.id).exists():
                            raise NameError(u"La materia ya existe en este turno, dia y profesor en ese rango de fechas.")
                        elif claseconflicto.values('id').filter(tipoprofesor=tipoprofesor, profesor=profesor).exists():
                            raise NameError(u"El profesor ya tiene asignada una materia en ese turno y día.")

                        claseconflicto = Clase.objects.filter(Q(inicio__lte=inicio, fin__gte=inicio) | Q(inicio__lte=fin, fin__gte=fin) | Q(inicio__gte=inicio, fin__lte=fin), materia__nivel__periodo=periodo, turno=turno, dia=dia, activo=True, materia__cerrado=False)
                        if claseconflicto.values('id').filter(tipoprofesor=tipoprofesor, profesor=profesor, materia__asignatura_id=materia.asignatura.id).exists():
                            raise NameError(u"La materia ya existe en este turno, dia, aula y profesor en ese rango de fechas.")

                        elif claseconflicto.values('id').filter(tipoprofesor=tipoprofesor, profesor=profesor).exists():
                            raise NameError(u"El profesor ya tiene asignada una materia en ese turno, día y aula.")

                    if materia.tipomateria == 1:
                        for turno in lista_turnos:
                            verificar_conflito_docente = profesor.existe_conflicto_docente(periodo, materia, tipoprofesor, inicio, fin, dia, turno)
                            if verificar_conflito_docente[0]: raise NameError(verificar_conflito_docente[1])

                    elif materia.coordinacion().id != 9:
                        for turno in lista_turnos:
                            verificar_conflito_docente = profesor.existe_conflicto_docente(periodo, materia, tipoprofesor, inicio, fin, dia, turno)
                            if verificar_conflito_docente[0]: raise NameError(verificar_conflito_docente[1])

            return {'result': True}
        else:
            return {'result': True}
    except Exception as ex:
        return {'result':False, 'mensaje': u"%s" % ex.__str__()}


def valida_choque_horario_pregrado_pre_postulacion(request: object, **kwargs: object) -> object:
    from sga.models import Clase, ProfesorMateria
    from .models import HorarioClases
    try:
        eHorarioClases = kwargs.pop('horarioClases', None)
        persona = kwargs.pop('persona', None)

        for horario in eHorarioClases:
            lista_turnos = horario.turno.all()
            dia = horario.dia
            inicio = horario.inicio
            fin = horario.fin
            profesormateria = ProfesorMateria.objects.filter(profesor__persona=persona, materia__cerrado=False, materia__inicio__lte=inicio, materia__fin__gte=fin)
            for pm in profesormateria:
                tipoprofesor = pm.tipoprofesor
                periodo = pm.materia.nivel.periodo
                profesor = pm.profesor
                materia = pm.materia
                for turno in lista_turnos:
                    claseconflicto = Clase.objects.filter(Q(inicio__lte=inicio, fin__gte=inicio) | Q(inicio__lte=fin, fin__gte=fin) | Q(inicio__gte=inicio, fin__lte=fin), Q(turno=turno, dia=dia, activo=True, materia__cerrado=False, profesor=profesor))
                    if claseconflicto: raise NameError(f"El profesor ya tiene asignada una materia en el  turno : {turno} y día: {dia}.")

                # CONFLICTO OTRAS CLASES
                # if not ProfesorMateria.objects.filter(profesor=profesor, novalidahorario=True, activo=True, tipoprofesor=profesor, materia=materia).exists():
                #     if claseconflicto.values('id').filter(tipoprofesor=profesor, profesor=profesor, materia__asignatura_id=materia.asignatura.id).exists():
                #         raise NameError(u"La materia ya existe en este turno, dia y profesor en ese rango de fechas.")
                #     elif claseconflicto.values('id').filter(tipoprofesor=tipoprofesor, profesor=profesor).exists():
                #         raise NameError(u"El profesor ya tiene asignada una materia en ese turno y día.")
                for turno in lista_turnos:
                    claseconflicto = Clase.objects.filter(Q(inicio__lte=inicio, fin__gte=inicio) | Q(inicio__lte=fin, fin__gte=fin) | Q(inicio__gte=inicio, fin__lte=fin), materia__nivel__periodo=periodo, turno=turno, dia=dia, activo=True, materia__cerrado=False)
                    if claseconflicto.values('id').filter(tipoprofesor=tipoprofesor, profesor=profesor, materia__asignatura_id=materia.asignatura.id).exists():
                        raise NameError(f"La materia ya existe en este turno: {turno}, dia : {dia}, aula y profesor en ese rango de fechas.")

                    elif claseconflicto.values('id').filter(tipoprofesor=tipoprofesor, profesor=profesor).exists():
                        raise NameError(f"El profesor ya tiene asignada una materia en ese turno: {turno}, día: {dia} y aula.")

                if materia.tipomateria == 1:
                    for turno in lista_turnos:
                        verificar_conflito_docente = profesor.existe_conflicto_docente(periodo, materia, tipoprofesor, inicio, fin, dia, turno)
                        if verificar_conflito_docente[0]: raise NameError(verificar_conflito_docente[1])

                elif materia.coordinacion().id != 9:
                    for turno in lista_turnos:
                        verificar_conflito_docente = profesor.existe_conflicto_docente(periodo, materia, tipoprofesor, inicio, fin, dia, turno)
                        if verificar_conflito_docente[0]: raise NameError(verificar_conflito_docente[1])

        return {'result': True,'puede':True}

    except Exception as ex:
        return {'result':True,'puede':False ,'mensaje': u"%s" % ex.__str__()}

def valida_choque_horario_en_actas_generadas_pre_postulacion(request: object, **kwargs: object) -> object:
    from .models import HorarioClases
    try:
        eHorarioClases_new = kwargs.pop('horarioClases', None)
        persona = kwargs.pop('persona', None)
        ePersonalAContratars =PersonalAContratar.objects.filter(status=True, inscripcion__postulante__persona = persona,actaparalelo__acta__estado =4)
        for horario in eHorarioClases_new:
            lista_turnos = horario.turno.all()
            dia = horario.dia
            inicio = horario.inicio
            fin = horario.fin
            for turno in lista_turnos:
                for ePersonalAContratar in ePersonalAContratars:
                    eActaParalelo = ePersonalAContratar.actaparalelo
                    eHorarioClasesePersonalAContratar = HorarioClases.objects.filter(status=True,actaparalelo = eActaParalelo).filter(
                        Q(dia=dia) &((Q(turno__comienza__gte=turno.comienza) & Q(turno__termina__lte=turno.termina)) |
                         (Q(turno__comienza__lte=turno.comienza) & Q(turno__termina__gte=turno.termina)) |
                         (Q(turno__comienza__lte=turno.termina) & Q(turno__comienza__gte=turno.comienza)) |
                         (Q(turno__termina__gte=turno.comienza) & Q(turno__termina__lte=turno.termina))) &
                        ((Q(inicio__gte=inicio) & Q(fin__lte=fin)) |(Q(inicio__lte=inicio) & Q(fin__gte=fin)) | Q(inicio__lte=fin) & Q(inicio__gte=inicio)) | (Q(fin__gte=inicio) & Q(fin__lte=fin))
                    )
                    if eHorarioClasesePersonalAContratar.exists():
                        raise NameError(f"Conficto de horarios en acta: {eActaParalelo.acta} - {eActaParalelo}")


        return {'result': True,'puede':True}

    except Exception as ex:
        return {'result':True,'puede':False ,'mensaje': u"%s" % ex.__str__()}
