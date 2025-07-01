# -*- coding: latin-1 -*-
#decoradores
import collections
import sys
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from django.forms import model_to_dict
from decorators import last_access, secure_module
from postulate.models import Convocatoria, Partida, PersonaAplicarPartida, RequisitoDocumentoContrato, PersonaRequisitoDocumentoContrato, HistorialPersonaRequisitoDocument, PersonaPeriodoConvocatoria, PersonaRequisitosConvocatoria, TIPO_REQUISITO, HistorialPersonaPeriodoConvocatoria,TituloSugerido
from sagest.commonviews import obtener_estado_solicitud
from settings import EMAIL_INSTITUCIONAL_AUTOMATICO, GENERAR_TUMBAIL

from django.contrib import messages
from django.template import Context
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime, timedelta

from med.models import PersonaExtension
from mobile.views import make_thumb_picture, make_thumb_fotopersona

from sagest.forms import RedPersonaForm, CapacitacionPersonaForm
from sagest.models import ExperienciaLaboral, SolicitudPublicacion, Publicacion

from sga.commonviews import adduserdata
from sga.forms import SolicitudPublicacionLibroForm, SolicitudPublicacionCapituloLibroForm, DocumentoPersonalesHojaVidaEncuentraEmpleoForm
from sga.funciones import generar_nombre, log, email_valido, tituloinstitucion, validar_archivo
from sga.funcionesxhtml2pdf import conviert_html_to_pdf_name
from sga.models import Persona, PersonaDocumentoPersonal, NivelTitulacion, Titulacion, Graduado, Titulo, RedPersona, FotoPersona, CertificadoIdioma, CUENTAS_CORREOS, Capacitacion, SubAreaEspecificaConocimientoTitulacion, SubAreaConocimientoTitulacion, CamposTitulosPostulacion, AreaConocimientoTitulacion, CertificacionPersona, Notificacion
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt

from postulate.forms import PersonaForm, ExperienciaLaboralForm, TitulacionPersonaForm, TituloHojaVidaForm, CertificadoIdiomaForm, SolicitudPublicacionForm, RevistaInvestigacionForm, CapacitacionPersonaPostulateForm, PublicacionForm, CustomDateInput, CargarRequisitoConvocatoriaForm, SugenciaTituloForm, CertificadoPersonaPostulateForm, SubirEvidenciaExperiencia


@login_required(redirect_field_name='ret', login_url='/loginpostulate')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['url_'] = request.path
    persona = request.session['persona']
    periodo = request.session['periodo']
    data['currenttime'] = datetime.now()

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'editdatospersonales':
            try:
                personasession = request.session['persona']
                persona = Persona.objects.get(pk=personasession.id)
                f = PersonaForm(request.POST, request.FILES)
                if f.is_valid():
                    if f.cleaned_data['nombres']:
                        persona.nombres = f.cleaned_data['nombres']
                    if f.cleaned_data['apellido1']:
                        persona.apellido1 = f.cleaned_data['apellido1']
                    if f.cleaned_data['apellido2']:
                        persona.apellido2 = f.cleaned_data['apellido2']
                    if f.cleaned_data['cedula']:
                        persona.cedula = f.cleaned_data['cedula']
                    if f.cleaned_data['nacimiento']:
                        persona.nacimiento = f.cleaned_data['nacimiento']
                    # persona.paisnacimiento = f.cleaned_data['paisnacimiento']
                    # persona.provincianacimiento = f.cleaned_data['provincianacimiento']
                    # persona.cantonnacimiento = f.cleaned_data['cantonnacimiento']
                    # persona.parroquianacimiento = f.cleaned_data['parroquianacimiento']
                    persona.pais = f.cleaned_data['pais']
                    persona.provincia = f.cleaned_data['provincia']
                    persona.canton = f.cleaned_data['canton']
                    persona.parroquia = f.cleaned_data['parroquia']
                    persona.pasaporte = f.cleaned_data['pasaporte']
                    persona.sexo = f.cleaned_data['sexo']
                    persona.direccion = f.cleaned_data['direccion']
                    persona.direccion2 = f.cleaned_data['direccion2']
                    persona.num_direccion = f.cleaned_data['num_direccion']
                    persona.lgtbi=f.cleaned_data['lgtbi']
                    persona.sector = f.cleaned_data['sector']
                    persona.telefono = f.cleaned_data['telefono']
                    persona.telefono_conv = f.cleaned_data['telefono_conv']
                    persona.email = f.cleaned_data['email']
                    perfil = persona.mi_perfil()
                    perfil.raza = f.cleaned_data['etnia']
                    perfil.save(request)
                    if not EMAIL_INSTITUCIONAL_AUTOMATICO:
                        persona.emailinst = f.cleaned_data['emailinst']
                    # persona.sangre = f.cleaned_data['sangre']
                    if persona.personaextension_set.exists():
                        extra = persona.personaextension_set.all()[0]
                        extra.estadocivil = f.cleaned_data['estadocivil']
                        extra.save(request)
                    else:
                        extra = PersonaExtension(persona=persona,
                                                 estadocivil=f.cleaned_data['estadocivil'])
                        extra.save(request)
                    persona.save(request)
                    request.session['persona'] = persona
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
                    log(u'Edito datos personales alumno en hoja de vida : %s [%s]- perfil: %s' % (persona, persona.id, perfil), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al enviar datos."})

        if action == 'addtitulacion':
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
                                            # fechaobtencion=f.cleaned_data['fechaobtencion'],
                                            # fechaegresado=f.cleaned_data['fechaegresado'],
                                            registro=f.cleaned_data['registro'],
                                            pais=f.cleaned_data['pais'],
                                            provincia=f.cleaned_data['provincia'],
                                            canton=f.cleaned_data['canton'],
                                            parroquia=f.cleaned_data['parroquia'],
                                            cursando=f.cleaned_data['cursando'],
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
                    # campotitulo.save()
                    log(u'Adiciono titulacion: %s' % persona, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'edittitulacion':
            try:
                persona = request.session['persona']
                f = TitulacionPersonaForm(request.POST, request.FILES)
                if f.is_valid():
                    titulacion = Titulacion.objects.get(pk=int(request.POST['idtitulacion']))
                    titulacion.titulo = f.cleaned_data['titulo']
                    titulacion.registro = f.cleaned_data['registro']
                    titulacion.pais = f.cleaned_data['pais']
                    titulacion.provincia = f.cleaned_data['provincia']
                    titulacion.canton = f.cleaned_data['canton']
                    titulacion.parroquia = f.cleaned_data['parroquia']
                    titulacion.institucion = f.cleaned_data['institucion']
                    titulacion.cursando = f.cleaned_data['cursando']
                    titulacion.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("titulacion_", newfile._name)
                        titulacion.archivo = newfile
                        titulacion.save(request)
                    campotitulo = None

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
                    raise NameError(f'{[{k:v[0]} for k,v in f.errors.items()]}')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'deltitulacion':
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

        if action == 'addtitulo':
            try:
                f = TituloHojaVidaForm(request.POST)
                if f.is_valid():
                    if Titulo.objects.filter(nombre__unaccent=f.cleaned_data['nombre'].upper()).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El registro ya existe."})
                    if Titulo.objects.filter(nombre=f.cleaned_data['nombre'].upper(), nivel=f.cleaned_data['nivel']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El registro ya existe."})
                    if f.cleaned_data['nivel'].id ==4 and not f.cleaned_data['grado']:
                        return JsonResponse({"result": "bad", "mensaje": u"Por favor seleccione grado."})

                    titulo = Titulo(nombre=f.cleaned_data['nombre'],
                                    abreviatura=f.cleaned_data['abreviatura'],
                                    areaconocimiento=f.cleaned_data['areaconocimiento'],
                                    subareaconocimiento=f.cleaned_data['subareaconocimiento'],
                                    subareaespecificaconocimiento=f.cleaned_data['subareaespecificaconocimiento'],
                                    nivel=f.cleaned_data['nivel'],
                                    grado=f.cleaned_data['grado'])
                    titulo.save(request)
                    log(u'Adiciono nuevo titulo desde postulacion: %s' % titulo, request, "add")
                    # messages.success(request, 'Se guado exitosamente')
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'detalletitulo':
            try:
                data['titulacion'] = titulacion = Titulacion.objects.get(pk=int(request.POST['id']))
                data['campostitulo'] = CamposTitulosPostulacion.objects.filter(status=True, titulo=titulacion.titulo)
                dettitu = titulacion.detalletitulacionbachiller_set.filter(status=True)
                data['detalletitulacionbachiller'] = dettitu.last()
                if titulacion.usuario_creacion:
                    data['personacreacion'] = Persona.objects.get(
                        usuario=titulacion.usuario_creacion) if titulacion.usuario_creacion.id > 1 else ""
                template = get_template("postu_requisitos/detalletitulo.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'addexperiencia':
            try:
                form = ExperienciaLaboralForm(request.POST, request.FILES)
                persona = Persona.objects.get(pk=int(encrypt(request.POST['id'])))
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not (ext == '.pdf' or ext == '.png' or ext == '.jpg' or ext == '.jpeg'):
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, solo archivos .pdf, png, jpg, jpeg."})
                else:
                    return JsonResponse({"result": True, "mensaje": u"El archivo de evidencia es requerido."})
                if form.is_valid():
                    fechafin = None
                    if not form.cleaned_data['vigente']:
                        fechafin = form.cleaned_data['fechafin']
                        if fechafin <= form.cleaned_data['fechainicio']:
                            return JsonResponse({"result": True, "mensaje": u"La fecha de fin no puede ser menor o igual a fecha de inicio."})
                    experiencialaboral = ExperienciaLaboral(persona=persona,
                                                            institucion=form.cleaned_data['lugar'],
                                                            actividadlaboral=form.cleaned_data['actividadlaboral'],
                                                            cargo=form.cleaned_data['cargo'],
                                                            fechainicio=form.cleaned_data['fechainicio'],
                                                            fechafin=fechafin)
                    experiencialaboral.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("experiencialaboral_", newfile._name)
                        experiencialaboral.archivo = newfile
                        experiencialaboral.save(request)

                else:
                    raise NameError('Error')
                log(u'Agregar Experiencia: %s' % persona, request, "addexperienciapersona")
                return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        if action == 'editexperiencia':
            try:
                form = ExperienciaLaboralForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 4194304:
                        return JsonResponse({"result": True, "mensaje": u"Error, archivo mayor a 4 Mb."})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not (ext == '.pdf' or ext == '.png' or ext == '.jpg' or ext == '.jpeg'):
                            return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf, png, jpg, jpeg."})

                if form.is_valid():
                    fechafin = None
                    if not form.cleaned_data['vigente']:
                        fechafin = form.cleaned_data['fechafin']
                        if fechafin <= form.cleaned_data['fechainicio']:
                            return JsonResponse({"result": True, "mensaje": u"La fecha de fin no puede ser menor o igual a fecha de inicio."})
                    experiencialaboral = ExperienciaLaboral.objects.get(pk=int(encrypt(request.POST['ide'])))
                    # experiencialaboral.tipoinstitucion = form.cleaned_data['tipoinstitucion']
                    experiencialaboral.institucion = form.cleaned_data['lugar']
                    experiencialaboral.cargo = form.cleaned_data['cargo']
                    # experiencialaboral.departamento = form.cleaned_data['departamento']
                    # experiencialaboral.pais = form.cleaned_data['pais']
                    # experiencialaboral.provincia = form.cleaned_data['provincia']
                    # experiencialaboral.canton = form.cleaned_data['canton']
                    # experiencialaboral.parroquia = form.cleaned_data['parroquia']
                    experiencialaboral.fechainicio = form.cleaned_data['fechainicio']
                    experiencialaboral.fechafin = fechafin
                    # experiencialaboral.motivosalida = motivosalida
                    # experiencialaboral.regimenlaboral = form.cleaned_data['regimenlaboral']
                    # experiencialaboral.horassemanales = form.cleaned_data['horassemanales']
                    # experiencialaboral.dedicacionlaboral = form.cleaned_data['dedicacionlaboral']
                    experiencialaboral.actividadlaboral = form.cleaned_data['actividadlaboral']
                    # experiencialaboral.observaciones = form.cleaned_data['observaciones']
                    experiencialaboral.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("experiencialaboral_", newfile._name)
                        experiencialaboral.archivo = newfile
                        experiencialaboral.save(request)
                    log(u'Modifico experiencia laboral: %s' % experiencialaboral, request, "add")
                    return JsonResponse({'result': False})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        if action == 'delexperiencia':
            try:
                with transaction.atomic():
                    idexpe = request.POST['id']
                    experienciapersona = ExperienciaLaboral.objects.get(pk=idexpe)
                    experienciapersona.delete()
                    log(u'Elimino Registro de experiencia: %s' % experienciapersona, request, "deleteexperiencia")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'consultacedula':
            try:
                cedula = request.POST['cedula'].strip()
                datospersona = None
                provinciaid = 0
                cantonid = 0
                cantonnom = ''
                lugarestudio = ''
                carrera = ''
                profesion = ''
                institucionlabora = ''
                cargo = ''
                teleoficina = ''
                idgenero = 0
                habilitaemail = 0
                if Persona.objects.filter(cedula=cedula).exists():
                    datospersona = Persona.objects.get(cedula=cedula)
                elif Persona.objects.filter(pasaporte=cedula).exists():
                    datospersona = Persona.objects.get(pasaporte=cedula)
                if datospersona:
                    if datospersona.sexo:
                        idgenero = datospersona.sexo_id
                    return JsonResponse({"result": "ok", "apellido1": datospersona.apellido1, "apellido2": datospersona.apellido2,
                                         "nombres": datospersona.nombres, "email": datospersona.email, "telefono": datospersona.telefono, "idgenero": idgenero})
                else:
                    return JsonResponse({"result": "no"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addred':
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

        if action == 'editred':
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
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

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

        if action == 'chargefoto':
            try:
                persona = Persona.objects.get(pk=int(request.POST['id']))
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
                # make_thumb_picture(persona)
                # if GENERAR_TUMBAIL:
                #     make_thumb_fotopersona(persona)
                log(u'Adicionó foto de persona: %s' % foto, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente la foto')
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"La imagen seleccionada no cumple los requisitos. %s" % ex.__str__()})

        if action == 'addcertificadoidioma':
            try:
                persona = request.session['persona']
                f = CertificadoIdiomaForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    newfilesd = d._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if ext == '.pdf':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                    if d.size > 2194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 2 Mb."})
                if f.is_valid():
                    if f.cleaned_data['validainst'] and not f.cleaned_data['otrainstitucion']:
                        return JsonResponse({"result": True, "mensaje": u"Por favor coloque el nombre de otra institucion."})
                    elif not f.cleaned_data['validainst'] and not f.cleaned_data['institucion']:
                        return JsonResponse({"result": True, "mensaje": u"Por favor seleccione una institucion."})
                    certificado = CertificadoIdioma(persona=persona,
                                                       idioma=f.cleaned_data['idioma'],
                                                       institucioncerti=f.cleaned_data['institucion'],
                                                       validainst=f.cleaned_data['validainst'],
                                                       otrainstitucion=f.cleaned_data['otrainstitucion'],
                                                       nivelsuficencia=f.cleaned_data['nivel'],
                                                       fechacerti=f.cleaned_data['fecha'])
                    certificado.save(request)
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("certificado_otro_", newfile._name)
                        certificado.archivo = newfile
                        certificado.save(request)
                    log(u'Adiciono certificado internacional: %s' % persona, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({"result": True, "mensaje": u"Error, al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': False, 'mensaje': u'Error al guardar los datos'})

        if action == 'editcertificadoidioma':
            try:
                persona = request.session['persona']
                certificado = CertificadoIdioma.objects.get(pk=int(encrypt(request.POST['idc'])))
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 2194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 2 Mb."})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not (ext == '.pdf'):
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf"})
                f = CertificadoIdiomaForm(request.POST, request.FILES)
                if f.is_valid():

                    certificado.idioma = f.cleaned_data['idioma']
                    certificado.institucioncerti = f.cleaned_data['institucion']
                    certificado.otrainstitucion = f.cleaned_data['otrainstitucion']
                    certificado.nivelsuficencia = f.cleaned_data['nivel']
                    certificado.fechacerti = f.cleaned_data['fecha']
                    certificado.validainst = f.cleaned_data['validainst']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("certificado_otro_", newfile._name)
                        certificado.archivo = newfile
                    certificado.save(request)
                    log(u'Modifico certificación de idioma personal: %s' % persona, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({"result": True, "mensaje": u"Error, al guardar los datos."})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        if action == 'delcertificadoidioma':
            try:
                with transaction.atomic():
                    certificadopersona = CertificadoIdioma.objects.get(pk=request.POST['id'])
                    certificadopersona.status = False
                    certificadopersona.save(request)
                    log(u'Eliminó un certificado internacional personal a la hoja de vida: %s - la persona: %s' % (certificadopersona, persona), request, "delcertificadoidioma")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'detalleotroscertificacion':
            try:
                data['certificacion'] = certificacion = CertificadoIdioma.objects.get(pk=int(request.POST['id']))
                if certificacion.usuario_creacion:
                    data['personacreacion'] = Persona.objects.get(
                        usuario=certificacion.usuario_creacion) if certificacion.usuario_creacion.id > 1 else ""
                template = get_template("postulate/requisitos/modal/detalleidiomas.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'addpublicacion':
            try:
                f = PublicacionForm(request.POST, request.FILES)

                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    extension = newfile._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad",
                                             "mensaje": u"Error, Tamaño de archivo Publicación Máximo permitido es de 10Mb"})
                    if exte.lower() not in ['pdf', 'doc', 'docx']:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Solo se permiten archivos .pdf, .doc y .docx (Publicación)"})

                if f.is_valid():
                    if Publicacion.objects.filter(status=True, tiposolicitud=f.cleaned_data['tiposolicitud'],
                                                           nombre=f.cleaned_data['nombre']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El título para ese tipo de publicación ya existe"})

                    publicacion = Publicacion(persona=persona,tiposolicitud=f.cleaned_data['tiposolicitud'],
                                                                nombre=f.cleaned_data['nombre'],
                                                                fecha=f.cleaned_data['fecha'],)
                    publicacion.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("publicacion_", newfile._name)
                        publicacion.archivo = newfile
                        publicacion.save(request)

                    log(u'Adicionar Publicación: %s' % publicacion, request, "addpublicacion")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({"result": True, "mensaje": u"Error, al guardar los datos."})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        if action == 'editpublicacion':
            try:
                f = PublicacionForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    extension = newfile._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Publicación Máximo permitido es de 10Mb"})
                    if exte.lower() not in ['pdf', 'doc', 'docx']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf, .doc y .docx (Publicación)"})

                if f.is_valid():
                    publicacion = Publicacion.objects.get(pk=int(encrypt(request.POST['id'])))
                    if Publicacion.objects.filter(status=True, tiposolicitud=publicacion.tiposolicitud, nombre=f.cleaned_data['nombre']).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El título para ese tipo de publicación ya existe"})

                    publicacion.nombre = f.cleaned_data['nombre']
                    publicacion.tiposolicitud=f.cleaned_data['tiposolicitud']
                    publicacion.fecha = f.cleaned_data['fecha']
                    publicacion.save(request)

                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("publicacion_", newfile._name)
                        publicacion.archivo = newfile
                        publicacion.save(request)

                    log(u'Modifico Publicación: %s' % publicacion, request, "editpublicacion")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({"result": True, "mensaje": u"Error, al guardar los datos."})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        if action == 'delpublicacion':
            try:
                with transaction.atomic():
                    publicacion = Publicacion.objects.get(pk=request.POST['id'])
                    publicacion.status = False
                    publicacion.save(request)
                    log(u'Eliminó publicacion %s - la persona: %s' % (publicacion, persona), request, "delpublicacion")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'detallecapacitacion':
            try:
                data['capacitacion'] = capacitacion = Capacitacion.objects.get(pk=int(request.POST['id']))
                if capacitacion.usuario_creacion:
                    data['personacreacion'] = Persona.objects.get(usuario=capacitacion.usuario_creacion) if capacitacion.usuario_creacion.id > 1 else ""
                template = get_template("th_hojavida/detallecapacitacion.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'detallecertificacion':
            try:
                data['certificacion'] = certificacion = CertificacionPersona.objects.get(pk=int(request.POST['id']))
                if certificacion.usuario_creacion:
                    data['personacreacion'] = Persona.objects.get(usuario=certificacion.usuario_creacion) if certificacion.usuario_creacion.id > 1 else ""
                template = get_template("th_hojavida/detallecertificacion.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'addcapacitacion':
            try:
                persona = request.session['persona']
                f = CapacitacionPersonaPostulateForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf' or ext == '.PDF' or ext == '.png' or ext == '.jpg' or ext == '.jpeg':
                            if f.is_valid():
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("capacitacion_", newfile._name)
                                capacitacion = Capacitacion(persona=persona,
                                                            institucion=f.cleaned_data['institucion'],
                                                            tipo=f.cleaned_data['tipo'],
                                                            nombre=f.cleaned_data['nombre'],
                                                            descripcion=f.cleaned_data['descripcion'],
                                                            tipocurso=f.cleaned_data['tipocurso'],
                                                            tipocapacitacion=f.cleaned_data['tipocapacitacion'],
                                                            tipocertificacion=f.cleaned_data['tipocertificacion'],
                                                            tipoparticipacion=f.cleaned_data['tipoparticipacion'],
                                                            anio=f.cleaned_data['anio'],
                                                            contextocapacitacion=f.cleaned_data['contexto'],
                                                            detallecontextocapacitacion=f.cleaned_data[
                                                                'detallecontexto'],
                                                            auspiciante=f.cleaned_data['auspiciante'],
                                                            areaconocimiento=f.cleaned_data['areaconocimiento'],
                                                            subareaconocimiento=f.cleaned_data['subareaconocimiento'],
                                                            subareaespecificaconocimiento=f.cleaned_data[
                                                                'subareaespecificaconocimiento'],
                                                            pais=f.cleaned_data['pais'],
                                                            provincia=f.cleaned_data['provincia'],
                                                            canton=f.cleaned_data['canton'],
                                                            parroquia=f.cleaned_data['parroquia'],
                                                            fechainicio=f.cleaned_data['fechainicio'],
                                                            fechafin=f.cleaned_data['fechafin'],
                                                            horas=f.cleaned_data['horas'],
                                                            expositor=f.cleaned_data['expositor'],
                                                            modalidad=f.cleaned_data['modalidad'],
                                                            otramodalidad=f.cleaned_data['otramodalidad'],
                                                            archivo=newfile)
                                capacitacion.save(request)

                                log(u'Adiciono capacitacion: %s' % persona, request, "add")
                                return JsonResponse({'result': 'ok'})
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, al guardar los datos."})
                        else:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, solo archivos .pdf, png, jpg, jpeg."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No existe archivo"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'editcapacitacion':
            try:
                persona = request.session['persona']
                capacitacion = Capacitacion.objects.get(pk=int(request.POST['id']))
                if not capacitacion.archivo and not 'archivo' in request.FILES:
                    return JsonResponse({'result': 'bad', 'mensaje': u'No ha seleccionado archivo'})
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not (ext == '.pdf' or ext == '.png' or ext == '.jpg' or ext == '.jpeg'):
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, solo archivos .pdf, png, jpg, jpeg."})
                f = CapacitacionPersonaPostulateForm(request.POST, request.FILES)
                if f.is_valid():
                    capacitacion.institucion = f.cleaned_data['institucion']
                    capacitacion.nombre = f.cleaned_data['nombre']
                    capacitacion.tipo = f.cleaned_data['tipo']
                    capacitacion.descripcion = f.cleaned_data['descripcion']
                    capacitacion.tipocurso = f.cleaned_data['tipocurso']
                    capacitacion.tipocapacitacion = f.cleaned_data['tipocapacitacion']
                    capacitacion.tipocertificacion = f.cleaned_data['tipocertificacion']
                    capacitacion.tipoparticipacion = f.cleaned_data['tipoparticipacion']
                    capacitacion.auspiciante = f.cleaned_data['auspiciante']
                    capacitacion.areaconocimiento = f.cleaned_data['areaconocimiento']
                    capacitacion.subareaconocimiento = f.cleaned_data['subareaconocimiento']
                    capacitacion.subareaespecificaconocimiento = f.cleaned_data['subareaespecificaconocimiento']
                    capacitacion.pais = f.cleaned_data['pais']
                    capacitacion.anio = f.cleaned_data['anio']
                    capacitacion.contextocapacitacion = f.cleaned_data['contexto']
                    capacitacion.detallecontextocapacitacion = f.cleaned_data['detallecontexto']
                    capacitacion.provincia = f.cleaned_data['provincia']
                    capacitacion.canton = f.cleaned_data['canton']
                    capacitacion.parroquia = f.cleaned_data['parroquia']
                    capacitacion.fechainicio = f.cleaned_data['fechainicio']
                    capacitacion.fechafin = f.cleaned_data['fechafin']
                    capacitacion.horas = f.cleaned_data['horas']
                    capacitacion.expositor = f.cleaned_data['expositor']
                    capacitacion.modalidad = f.cleaned_data['modalidad']
                    capacitacion.otramodalidad = f.cleaned_data['otramodalidad']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("capacitacion_", newfile._name)
                        capacitacion.archivo = newfile
                    # capacitacion.tiempo = f.cleaned_data['tiempo']
                    capacitacion.save(request)
                    log(u'Modifoco capacitacion: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, al guardar los datos."})

                # else:
                #     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})


        if action == 'delcapacitacion':
            try:
                with transaction.atomic():
                    publicacion = Capacitacion.objects.get(pk=request.POST['id'])
                    publicacion.status = False
                    publicacion.save(request)
                    log(u'Eliminó capacitacion %s - la persona: %s' % (publicacion, persona), request, "delcapacitacion")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'subirrequisito':
            try:
                requisito = RequisitoDocumentoContrato.objects.get(pk=int(request.POST['id']))
                if not 'archivo' in request.FILES:
                    raise NameError(f"Favor cargue un archivo")
                archivofile = request.FILES['archivo']
                if archivofile.size > 10220000:
                    raise NameError(u"Archivo mayor a 10Mb.")
                fotofileod = archivofile._name
                ext = fotofileod[fotofileod.rfind("."):]
                if not ext in ['.pdf']:
                    raise NameError(u"Solo archivo con extensión. pdf.")
                archivofile._name = generar_nombre("foto_", archivofile._name)
                personaarchivo = requisito.personaarchivo()
                if personaarchivo:
                    personaarchivo.archivo = archivofile
                else:
                    personaarchivo = PersonaRequisitoDocumentoContrato(persona=persona,requisito=requisito, archivo=archivofile)
                personaarchivo.save(request)
                log(u'Adicionó archivo de requisito: %s' % personaarchivo, request, "add")
                historial = HistorialPersonaRequisitoDocument(
                    personareq = personaarchivo,
                    estado= 1,
                    observacion = 'Inicio'
                )
                historial.save(request)
                log(u'Adicionó historial de archivo de requisito: %s' % historial, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el archivo')
                res_json = {'result': 'ok'}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'result':'bad', "mensaje":f"Error: {ex.__str__()}"}
            return JsonResponse(res_json)

        if action == 'editrequisito':
            try:
                requisito = PersonaRequisitoDocumentoContrato.objects.get(pk=int(request.POST['personarequisito']))
                if not 'archivo' in request.FILES:
                    raise NameError(f"Favor carge un archivo")
                archivofile = request.FILES['archivo']
                if archivofile.size > 10220000:
                    raise NameError(u"Archivo mayor a 10Mb.")
                fotofileod = archivofile._name
                ext = fotofileod[fotofileod.rfind("."):]
                if not ext in ['.pdf']:
                    raise NameError(u"Solo archivo con extensión. pdf.")
                archivofile._name = generar_nombre("foto_", archivofile._name)
                requisito.archivo = archivofile
                requisito.save(request)
                log(u'Editó archivo de requisito: %s' % requisito, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el archivo')
                res_json = {'result': False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'result': True, "mensaje": f"Error: {ex.__str__()}"}
            return JsonResponse(res_json)

        if action == 'deleteperrequisito':
            try:
                requisitoperso = PersonaRequisitoDocumentoContrato.objects.get(pk = int(encrypt(request.POST['id'])))
                requisitoperso.status = False
                requisitoperso.save(request)
                log(u'Eliminó registro del requisito %s'%requisitoperso,request, "delete")
                res_json = {'result': 'ok'}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": f"Error: {ex.__str__()}"}
            return JsonResponse(res_json)

        if action == 'cargarrequisitoconvocatoria':
            try:
                form = CargarRequisitoConvocatoriaForm(request.POST, request.FILES)
                filtro = PersonaRequisitosConvocatoria.objects.get(id=int(encrypt(request.POST['id'])))
                participacion_ = filtro.participacion
                requisito_ = filtro.requisito
                if form.is_valid():
                    if requisito_.varchivo:
                        if not 'archivo' in request.FILES and not filtro.archivo:
                            return JsonResponse({'result': True, 'mensaje': u'Debe subir un archivo en formato .pdf'})
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            import PyPDF2
                            # pdf_file = open(newfile)
                            read_pdf = PyPDF2.PdfFileReader(newfile)
                            number_of_pages = read_pdf.getNumPages()
                            newfile._name = generar_nombre(f"requisito{filtro.participacion.id}_", newfile._name)
                            filtro.archivo = newfile
                            filtro.numhojas = number_of_pages
                    if requisito_.vdescripcion:
                        if not 'descripcion' in request.POST:
                            return JsonResponse({'result': True, 'mensaje': u'Debe añadir una descripción según lo detalla l requisito'})
                        filtro.descripcion = request.POST['descripcion']
                    filtro.fecha_subida = datetime.now()
                    filtro.estado = 1
                    filtro.save(request)
                    if filtro.participacion.subiotodoslosarchivos():
                        if participacion_.estado == 3:
                            historial = HistorialPersonaPeriodoConvocatoria(
                                personaperiodo=participacion_,
                                observacion='Corrigiendo documentos',
                                estado=participacion_.estado
                            )
                            historial.save(request)
                        participacion_.estado = 1
                        participacion_.save(request)
                    if participacion_.estado == 3:
                        participacion_.estado = 0
                        participacion_.save(request)
                        historial = HistorialPersonaPeriodoConvocatoria(
                            personaperiodo = participacion_,
                            observacion='Corrigiendo documentos',
                            estado=participacion_.estado
                        )
                        historial.save(request)
                    messages.success(request, f'Requisito cargado')
                    log(f'Cargo requisito: {filtro.__str__()}', request, "addpostulantemasivo")
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        elif action == 'addhojavidaencuentraempleo':
            try:
                form = DocumentoPersonalesHojaVidaEncuentraEmpleoForm(request.POST, request.FILES)
                if form.is_valid():
                    newfile = request.FILES['hojavidaencuentraempleo']
                    newfile._name = generar_nombre("hojavidaencuentraempleo_{}_".format(persona.usuario.username), newfile._name)
                    documento = persona.documentos_personales()
                    # if documento.archivobaja:
                    #     log(u'Edito archivo de hoja de vida de encuentra empleo: persona = %s - [%s], archivo antiguo = %s, archivo nuevo = %s' % (
                    #         persona, persona.id, activo.archivobaja, newfile), request, "edit")
                    # else:
                    #     log(u'Adiciono archivo de hoja de vida de encuentra empleo: persona = %s - [%s], archivo = %s' % (
                    #         persona, persona.id, newfile), request, "add")
                    if documento is None:
                        documento = PersonaDocumentoPersonal(persona=persona,hojavidaencuentraempleo=newfile,estadohojavidaencuentraempleo=1)
                        log(u'Adiciono archivo de hoja de vida de encuentra empleo: persona = %s - [%s], archivo = %s' % (
                            persona, persona.id, newfile), request, "add")
                    else:
                        if documento.hojavidaencuentraempleo:
                            log(u'Edito archivo de hoja de vida de encuentra empleo: persona = %s - [%s], archivo antiguo = %s, archivo nuevo = %s' % (
                                persona, persona.id, documento.hojavidaencuentraempleo, newfile), request, "edit")
                        else:
                            log(u'Adiciono archivo de hoja de vida de encuentra empleo: persona = %s - [%s], archivo = %s' % (
                                persona, persona.id, newfile), request, "add")
                        documento.hojavidaencuentraempleo = newfile
                        documento.estadohojavidaencuentraempleo = 1
                    #activo = ActivoFijo.objects.get(pk=encrypt(request.POST['id']))
                    documento.save(request)
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Debe subir archivo pdf con los MG especificado')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. "})

        if action == 'deletehojavidaencuentraempleo':
            try:
                documento = persona.documentos_personales()
                documento.estadohojavidaencuentraempleo = None
                documento.hojavidaencuentraempleo.delete()
                log(u'Elimino hoja de vida de encuentra empleo: %s' % documento, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addsugerenciatit':
            try:
                with transaction.atomic():
                    form = SugenciaTituloForm(request.POST)
                    if form.is_valid():
                        if Titulo.objects.filter(status=True, usoseleccion=True, nombre__unaccent__iexact=form.cleaned_data['titulo'].upper(), nivel= form.cleaned_data['nivel']).exists():
                            return JsonResponse({"result": True, "mensaje": u"Este título ya se encuentra registrado"})
                        else:
                            titulosugerido = TituloSugerido(status=True, persona=persona, nombre=form.cleaned_data['titulo'].upper(), nivel=form.cleaned_data['nivel'],estado=1)
                            titulosugerido.save()

                            #envio de notificación
                            personas_notificar = Persona.objects.filter(usuario__groups__id=355).order_by('usuario__username').distinct('usuario__username').exclude(usuario__groups__id=3)
                            for notipersona in personas_notificar:
                                saludo = 'Estimada' if notipersona.sexo_id == 1 else 'Estimado'
                                notificacion = Notificacion(titulo='Sugerencia de título registrada',
                                                            cuerpo=f'''
                                                                        {saludo} {notipersona.nombre_completo()}:
                                                                        Le comunicamos que {titulosugerido.persona} ha ingresado una sugerencia de título,
                                                                        con descripción: {titulosugerido.nombre}.
                                                                        Usted puede validar o rechazar esta solicitud.
                                                                        ''',
                                                            destinatario_id=notipersona.id,
                                                            url=f'/th_titulos?action=viewtitulossugeridos&id={encrypt(titulosugerido.id)}',
                                                            object_id=titulosugerido.pk,
                                                            prioridad=1,
                                                            app_label='sagest',
                                                            fecha_hora_visible=datetime.now() + timedelta(days=1)
                                                            )
                                notificacion.save(request)
                            log(u'Adiciono titulo sugerido: %s' % persona, request, "edit")
                            return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                lineaerror = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. {} {}".format(str(ex), lineaerror)})

        if action == 'editsugerenciatit':
            try:
                titulosugerido = TituloSugerido.objects.get(pk=int(encrypt(request.POST['id'])))
                form = SugenciaTituloForm(request.POST)
                if form.is_valid():
                    if TituloSugerido.objects.filter(status=True, nombre=form.cleaned_data['titulo'].upper(), nivel=form.cleaned_data['nivel'], estado=2).exists():
                        return JsonResponse({"result": True, "mensaje": u"Esta sugerencia ya existe"})
                    elif Titulo.objects.filter(status=True, usoseleccion=True, nombre=form.cleaned_data['titulo'].upper(), nivel=form.cleaned_data['nivel']).exists():
                        return JsonResponse({"result": True, "mensaje": u"Este título ya se encuentra registrado"})
                    else:
                        titulosugerido.nombre = form.cleaned_data['titulo'].upper()
                        titulosugerido.nivel = form.cleaned_data['nivel']
                        titulosugerido.save()
                        log(u'Modifico titulo sugerido: %s' % persona, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({"result": True, "mensaje": u"Error al editar los datos."})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        if action == 'delsugerenciatit':
            try:
                with transaction.atomic():
                    titulosugerido = TituloSugerido.objects.get(pk=int(request.POST['id']))
                    titulosugerido.status = False
                    titulosugerido.save(request)
                    log(u'Eliminó titulo sugerido %s - la persona: %s' % (titulosugerido, persona), request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addcertificacion':
            try:
                persona = request.session['persona']
                f = CertificadoPersonaPostulateForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    newfilesd = d._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if ext == '.pdf':
                        a = 1
                    else:
                        return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf."})
                    if d.size > 2194304:
                        return JsonResponse({"result": True, "mensaje": u"Error, archivo mayor a 2 Mb."})
                if f.is_valid():
                    certificado = CertificacionPersona(persona=persona,
                                                       nombres=f.cleaned_data['nombres'],
                                                       autoridad_emisora=f.cleaned_data['autoridad_emisora'].upper(),
                                                       numerolicencia=f.cleaned_data['numerolicencia'],
                                                       enlace=f.cleaned_data['enlace'],
                                                       vigente=f.cleaned_data['vigente'],
                                                       fechadesde=f.cleaned_data['fechadesde'],
                                                       fechahasta=f.cleaned_data['fechahasta'])
                    certificado.save(request)
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("certificado_", newfile._name)
                        certificado.archivo = newfile
                        certificado.save(request)
                    log(u'Adiciono certificado: %s' % persona, request, "add")
                    return JsonResponse({"result": False})
                else:
                    return JsonResponse({"result": True, "mensaje": u"Error, al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        elif action == 'editcertificacion':
            try:
                persona = request.session['persona']
                certificado = CertificacionPersona.objects.get(pk=int(encrypt(request.POST['id'])))
                f = CertificadoPersonaPostulateForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    newfilesd = d._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if ext == '.pdf':
                        a = 1
                    else:
                        return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf."})
                    if d.size > 2194304:
                        return JsonResponse({"result": True, "mensaje": u"Error, archivo mayor a 2 Mb."})
                if f.is_valid():
                    certificado.persona=persona
                    certificado.nombres=f.cleaned_data['nombres']
                    certificado.autoridad_emisora=f.cleaned_data['autoridad_emisora']
                    certificado.numerolicencia=f.cleaned_data['numerolicencia']
                    certificado.enlace=f.cleaned_data['enlace']
                    certificado.vigente=f.cleaned_data['vigente']
                    certificado.fechadesde=f.cleaned_data['fechadesde']
                    certificado.fechahasta=f.cleaned_data['fechahasta']
                    certificado.save(request)

                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("certificado_", newfile._name)
                        certificado.archivo = newfile
                        certificado.save(request)
                    log(u'Edito certificado: %s' % persona, request, "edit")
                    return JsonResponse({"result": False})
                else:
                    return JsonResponse({"result": True, "mensaje": u"Error, al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        if action == 'delcertificacion':
            try:
                with transaction.atomic():
                    certificacion = CertificacionPersona.objects.get(pk=request.POST['id'])
                    certificacion.status = False
                    certificacion.save(request)
                    log(u'Elimino certificacion %s - la persona: %s' % (certificacion, persona), request, "delpublicacion")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addevidenciaexp':
            try:
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not (ext == '.pdf' or ext == '.png' or ext == '.jpg' or ext == '.jpeg'):
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, solo archivos .pdf, png, jpg, jpeg."})
                else:
                    return JsonResponse({"result": True, "mensaje": u"El archivo de evidencia es requerido."})
                experiencialaboral = ExperienciaLaboral.objects.get(pk=int(encrypt(request.POST['id'])))
                newfile = request.FILES['archivo']
                newfile._name = generar_nombre("experiencialaboral_", newfile._name)
                experiencialaboral.archivo = newfile
                experiencialaboral.save(request)
                log(u'Adicionó certificado experiencia laboral: %s' % experiencialaboral, request, "add")
                return JsonResponse({"result": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'editdatospersonales':
                try:
                    data['title'] = u'Modificar datos personales'
                    datosextension = persona.datos_extension()
                    perfil = persona.mi_perfil()
                    form = PersonaForm(initial={'nombres': persona.nombres,
                                                'apellido1': persona.apellido1,
                                                'apellido2': persona.apellido2,
                                                'cedula': persona.cedula,
                                                'pasaporte': persona.pasaporte,
                                                'nacimiento': persona.nacimiento,
                                                # 'paisnacimiento': persona.paisnacimiento,
                                                # 'provincianacimiento': persona.provincianacimiento,
                                                # 'cantonnacimiento': persona.cantonnacimiento,
                                                # 'parroquianacimiento': persona.parroquianacimiento,
                                                'sexo': persona.sexo,
                                                'nacionalidad': persona.nacionalidad,
                                                'pais': persona.pais,
                                                'provincia': persona.provincia,
                                                'canton': persona.canton,
                                                'parroquia': persona.parroquia,
                                                'direccion': persona.direccion,
                                                'direccion2': persona.direccion2,
                                                'num_direccion': persona.num_direccion,
                                                'sector': persona.sector,
                                                'telefono': persona.telefono,
                                                'telefono_conv': persona.telefono_conv,
                                                'email': persona.email,
                                                'emailinst': persona.emailinst,
                                                'etnia': persona.mi_perfil().raza,
                                                'lgtbi':persona.lgtbi,
                                                'estadocivil': datosextension.estadocivil,
                                                'tienediscapacidad': perfil.tienediscapacidad,
                                                'tipodiscapacidad': perfil.tipodiscapacidad,
                                                'porcientodiscapacidad': perfil.porcientodiscapacidad,
                                                'carnetdiscapacidad': perfil.carnetdiscapacidad,
                                                'institucionvalida': perfil.institucionvalida,})
                    form.editar(persona)
                    tienearchivo = True if perfil.archivo else False
                    if EMAIL_INSTITUCIONAL_AUTOMATICO:
                        form.sin_emailinst()
                    data['form'] = form
                    data['tienearchivo'] = tienearchivo
                    return render(request, "postulate/requisitos/editdatospersonales.html", data)
                except Exception as ex:
                    pass

            if action == 'addtitulacion':
                try:
                    data['title'] = u'Adicionar titulación'
                    data['action'] = action
                    form = TitulacionPersonaForm()
                    form.fields['titulo'].queryset = Titulo.objects.filter(status=True, usoseleccion=True, nivel__nivel__in=[3, 4])
                    form.fields['titulo'].widget.attrs.pop('fieldbuttons')
                    form.adicionar()
                    data['form'] = form
                    return render(request, "postulate/requisitos/formtitulacion.html", data)
                except Exception as ex:
                    pass

            if action == 'buscartitulos':
                try:
                    # id = request.GET['id']
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    #querybase = Titulo.objects.filter(nivel_id__in=[3, 4, 21, 22, 23, 30], status=True)
                    querybase = Titulo.objects.filter(nivel__nivel__in=[3, 4], status=True)
                    # if len(s) == 1:
                    per = querybase.filter((Q(nombre__icontains=q) | Q(abreviatura__icontains=q)), Q(status=True)).distinct()[:30]
                    # elif len(s) == 2:
                    #     per = querybase.filter((Q(nombre__contains=s[0]) & Q(nombre__contains=s[1])) | (Q(abreviatura__icontains=s[0]) & Q(abreviatura__icontains=s[1]))).filter(status=True).distinct()[:30]
                    # else:
                    #     per = querybase.filter((Q(nombre__contains=s[0]) & Q(nombre__contains=s[1])) | (Q(abreviatura__contains=s[0]) & Q(abreviatura__contains=s[1]))).filter(status=True).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.abreviatura, x.nombre)} for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'cargaradicionartitulo':
                try:
                    form = TituloHojaVidaForm()
                    form.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.none()
                    form.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.none()
                    data['form'] = form
                    data['idt'] = request.GET['idt']
                    data['action'] = request.GET['redireccion']
                    template = get_template('postulate/requisitos/modal/addtitulo.html')
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

            if action == 'edittitulacion':
                try:
                    data['title'] = u'Editar titulación'
                    data['action'] = action
                    data['titulacion'] = titulacion = Titulacion.objects.get(pk=int(request.GET['id']))
                    campotitulo, campoamplio, campoespecifico, campodetallado = None, None, None, None
                    if CamposTitulosPostulacion.objects.filter(status=True, titulo=titulacion.titulo).exists():
                        campotitulo = CamposTitulosPostulacion.objects.filter(status=True, titulo=titulacion.titulo).first()
                        campoamplio = AreaConocimientoTitulacion.objects.filter(status=True, id__in=campotitulo.campoamplio.all().values_list('id', flat=True))
                        campoespecifico = SubAreaConocimientoTitulacion.objects.filter(status=True, id__in=campotitulo.campoespecifico.all().values_list('id', flat=True))
                        campodetallado = SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, id__in=campotitulo.campodetallado.all().values_list('id', flat=True))
                    form = TitulacionPersonaForm(initial={'titulo': titulacion.titulo,
                                                          'institucion': titulacion.institucion,
                                                          'cursando': titulacion.cursando,
                                                          'registro': titulacion.registro,
                                                          'pais': titulacion.pais,
                                                          'provincia': titulacion.provincia,
                                                          'canton': titulacion.canton,
                                                          'campoamplio': campoamplio,
                                                          'campoespecifico': campoespecifico,
                                                          'campodetallado': campodetallado,
                                                          # 'anios': titulacion.anios,
                                                          })
                    form.fields['titulo'].widget.attrs.pop('fieldbuttons')
                    form.editar(titulacion)
                    data['form'] = form
                    # data['idins'] = inscripcion.id
                    # data['idper'] = request.GET['idper']
                    return render(request, "postulate/requisitos/formtitulacion.html", data)
                except:
                    pass

            if action == 'addexperiencia':
                try:
                    persona = Persona.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['id'] = int(encrypt(request.GET['id']))
                    data['form'] = ExperienciaLaboralForm()
                    template = get_template("postulate/requisitos/modal/formexperiencia.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editexperiencia':
                try:
                    data['title'] = u'Editar experiencia'
                    data['action']=action
                    data['experiencia'] = experiencia = ExperienciaLaboral.objects.get(pk=int(encrypt(request.GET['id'])))
                    vigente = True
                    fechafin = None
                    if experiencia.fechafin:
                        vigente = False
                        fechafin = experiencia.fechafin
                    data['form'] = ExperienciaLaboralForm(initial={
                                                                   'lugar': experiencia.institucion,
                                                                   'cargo': experiencia.cargo,
                                                                   # 'departamento': experiencia.departamento,
                                                                   # 'pais': experiencia.pais,
                                                                   # 'provincia': experiencia.provincia,
                                                                   # 'canton': experiencia.canton,
                                                                   # 'parroquia': experiencia.parroquia,
                                                                   'fechainicio': experiencia.fechainicio,
                                                                   'fechafin': fechafin,
                                                                   # 'motivosalida': experiencia.motivosalida,
                                                                   'vigente': vigente,
                                                                    'archivo':experiencia.archivo,
                                                                   # 'regimenlaboral': experiencia.regimenlaboral,
                                                                   # 'horassemanales': experiencia.horassemanales,
                                                                   # 'dedicacionlaboral': experiencia.dedicacionlaboral,
                                                                   'actividadlaboral': experiencia.actividadlaboral,
                                                                   # 'observaciones': experiencia.observaciones
                                                                    })
                    template = get_template("postulate/requisitos/modal/formexperiencia.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addred':
                try:
                    data['form2'] = RedPersonaForm()
                    data['action']=action
                    template = get_template("postulate/requisitos/modal/formred.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editred':
                try:
                    data['title'] = u"Editar Red"
                    data['action'] = action
                    data['red'] = red = RedPersona.objects.get(pk = request.GET['id'])
                    initial = model_to_dict(red)
                    data['form2'] = RedPersonaForm(initial=initial)
                    template = get_template("postulate/requisitos/modal/formred.html")
                    return JsonResponse({"result":True,"data":template.render(data)})
                except Exception as ex:
                    pass

            if action == 'chargefoto':
                try:
                    data['persona'] = Persona.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['id'] = int(encrypt(request.GET['id']))
                    data['title'] = u'Subir foto'
                    template = get_template("postulate/requisitos/modal/formfoto.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addcertificadoidioma':
                try:
                    data['title'] = u'Adicionar Certificado de Idioma'
                    data['persona'] = persona
                    form = CertificadoIdiomaForm()
                    data['form'] = form
                    template = get_template("postulate/requisitos/modal/formidioma.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editcertificadoidioma':
                try:
                    data['title'] = u'Editar Certificado Idioma'
                    data['certificado'] = certificado = CertificadoIdioma.objects.get(pk=request.GET['id'])

                    data['form'] = CertificadoIdiomaForm(initial={'idioma': certificado.idioma,

                                                             'institucion': certificado.institucioncerti,
                                                             'otrainstitucion': certificado.otrainstitucion,
                                                             'validainst':certificado.validainst,
                                                             'fecha': certificado.fechacerti,
                                                             'nivel': certificado.nivelsuficencia})
                    template = get_template("postulate/requisitos/modal/formidioma.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addpublicacion':
                try:
                    data['title'] = u'Adicionar Publicación'
                    form = PublicacionForm()
                    data['form'] = form
                    template = get_template("postulate/requisitos/modal/formpublicacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editpublicacion':
                try:
                    data['title'] = u'Editar Publicacion'
                    data['publicacion'] = publicacion = Publicacion.objects.get(pk=request.GET['id'])
                    form = PublicacionForm(initial=model_to_dict(publicacion))
                    data['form'] = form
                    template = get_template("postulate/requisitos/modal/formpublicacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editsolicitudlibro':
                try:
                    data['title'] = u'Editar Solicitud de Libro'
                    data['solicitud'] = solicitud = SolicitudPublicacion.objects.get(pk=request.GET['id'])
                    form = SolicitudPublicacionLibroForm(initial={'tiposolicitud': solicitud.tiposolicitud,
                                                                  'titulo': solicitud.nombre,
                                                                  'motivo': solicitud.motivo,
                                                                  'fechapublicacion': solicitud.fechapublicacion,
                                                                  'areaconocimiento': solicitud.areaconocimiento,
                                                                  'subareaconocimiento': solicitud.subareaconocimiento,
                                                                  'subareaespecificaconocimiento': solicitud.subareaespecificaconocimiento
                                                                  })

                    form.editar(solicitud)
                    data['form'] = form
                    return render(request, "postulate/requisitos/formarticulo.html", data)
                except Exception as ex:
                    pass

            if action == 'editsolicitudcapitulo':
                try:
                    data['title'] = u'Editar Solicitud de capítulo de Libro'
                    data['solicitud'] = solicitud = SolicitudPublicacion.objects.get(pk=request.GET['id'])
                    form = SolicitudPublicacionCapituloLibroForm(initial={'tiposolicitud': solicitud.tiposolicitud,
                                                                          'resumen': solicitud.motivo})
                    form.editar(solicitud)
                    data['form'] = form
                    return render(request, "th_hojavida/editsolicitudcapitulo.html", data)
                except Exception as ex:
                    pass

            if action == 'addcapacitacion':
                try:
                    data['title'] = u'Adicionar capacitación'
                    form = CapacitacionPersonaPostulateForm()
                    form.adicionar()
                    form.fields['fechainicio'].widget = CustomDateInput(attrs={'type': 'date', 'class': 'form-control'})
                    form.fields['fechafin'].widget = CustomDateInput(attrs={'type': 'date', 'class': 'form-control'})
                    data['form'] = form
                    return render(request, "postulate/requisitos/addcapacitacion.html", data)
                except Exception as ex:
                    pass

            if action == 'editcapacitacion':
                try:
                    data['title'] = u'Editar capacitación'
                    data['capacitacion'] = capacitacion = Capacitacion.objects.get(pk=int(request.GET['id']))
                    data['modalidad1'] = capacitacion.modalidad
                    form = CapacitacionPersonaPostulateForm(initial=model_to_dict(capacitacion))
                    form.editar(capacitacion)
                    form.fields['fechainicio'].widget = CustomDateInput(attrs={'type': 'date', 'class': 'form-control'})
                    form.fields['fechafin'].widget = CustomDateInput(attrs={'type': 'date', 'class': 'form-control'})
                    data['form'] = form
                    return render(request, "postulate/requisitos/editcapacitacion.html", data)
                except Exception as ex:
                    pass

            if action == 'listcampoespecifico':
                try:
                    campoamplio = request.GET.get('campoamplio')
                    listcampoamplio = campoamplio
                    if len(campoamplio) > 1:
                        listcampoamplio = campoamplio.split(',')
                    querybase = SubAreaConocimientoTitulacion.objects.filter(status=True, areaconocimiento__in=listcampoamplio).order_by('codigo')
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "idca": x.areaconocimiento.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'listcampodetallado':
                try:
                    campoespecifico = request.GET.get('campoespecifico')
                    listcampoespecifico = campoespecifico
                    if len(campoespecifico) > 1:
                        listcampoespecifico = campoespecifico.split(',')
                    querybase = SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, areaconocimiento__in=listcampoespecifico).order_by('codigo')
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'subirrequisito':
                try:
                    data['requi'] = RequisitoDocumentoContrato.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['id'] = int(encrypt(request.GET['id']))
                    data['title'] = u'Subir requisito'
                    template = get_template("postulate/requisitos/modal/formrequisito.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editrequisito':
                try:
                    data['perrequi'] = personarequi = PersonaRequisitoDocumentoContrato.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['requi'] = personarequi.requisito
                    data['id'] = int(encrypt(request.GET['id']))
                    data['title'] = u'Subir requisito'
                    template = get_template("postulate/requisitos/modal/formrequisito.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verrequisitosconvocatoria':
                try:
                    data['title'] = 'Cargar Requisitos de Ingreso'
                    data['filtro'] = filtro = PersonaPeriodoConvocatoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['id'] = int(encrypt(request.GET['id']))
                    return render(request, "postulate/requisitos/requisitosconvocatoria.html", data)
                except Exception as ex:
                    pass

            if action == 'cargarrequisitoconvocatoria':
                try:
                    data['filtro'] = filtro = PersonaRequisitosConvocatoria.objects.get(id=int(request.GET['id']))
                    form = CargarRequisitoConvocatoriaForm()
                    if filtro.requisito:
                        if not filtro.requisito.varchivo:
                            del form.fields['archivo']
                        else:
                            form.fields['archivo'].initial = filtro.archivo if filtro.archivo else None
                            form.fields["archivo"].widget.attrs['data-default-file'] = filtro.archivo.url if filtro.archivo else ""
                        if not filtro.requisito.vdescripcion:
                            del form.fields['descripcion']
                        else:
                            form.fields['descripcion'].initial = filtro.descripcion if filtro.descripcion else ''
                    data['form'] = form
                    template = get_template("postulate/requisitos/modal/formcargarrequisitoconvocatoria.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addhojavidaencuentraempleo':
                try:

                    documento = persona.documentos_personales()
                    if documento is None:
                        form2 = DocumentoPersonalesHojaVidaEncuentraEmpleoForm()
                        data['form2'] = form2
                    else:
                        if documento.hojavidaencuentraempleo:
                            data['filtro'] = filtro = PersonaDocumentoPersonal.objects.get(persona=persona)
                            data['form2'] = DocumentoPersonalesHojaVidaEncuentraEmpleoForm(initial=model_to_dict(filtro))
                        else:
                            form2 = DocumentoPersonalesHojaVidaEncuentraEmpleoForm()
                            data['form2'] = form2
                    template = get_template("postulate/requisitos/modal/formhojavidaencuentraempleo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'checklist':
                try:
                    data['filtro'] = filtro = PersonaPeriodoConvocatoria.objects.get(id=int(encrypt(request.GET['id'])))
                    tipo_requisitos = TIPO_REQUISITO
                    data['tipo_requ'] = tipo_requisitos
                    #GrupoRequisitoConvocatoria
                    name = "check_list"
                    template = "postulate/requisitos/checklist.html"
                    return conviert_html_to_pdf_name(template,{'pagesize': 'A4', 'data': data,},name)
                except Exception as ex:
                    import sys
                    print(ex)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            if action == 'addcertificacion':
                try:
                    data['persona'] = persona
                    form = CertificadoPersonaPostulateForm()
                    data['form'] = form
                    template = get_template("postulate/requisitos/modal/addcertificacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editcertificacion':
                try:
                    data['persona'] = persona
                    data['certificado'] = certificado = CertificacionPersona.objects.get(pk=int(encrypt(request.GET['id'])))
                    initial = model_to_dict(certificado)
                    data['form'] = f = CertificadoPersonaPostulateForm(initial=initial)
                    if certificado.vigente == True :
                        f.fields['fechahasta'].widget.attrs['disabled'] = True
                    template = get_template("postulate/requisitos/modal/addcertificacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addsugerenciatit':
                try:
                    data['title'] = u'Adicionar Sugerencia de Título'
                    form = SugenciaTituloForm()
                    data['form'] = form
                    template = get_template("postulate/requisitos/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editsugerenciatit':
                try:
                    data['title'] = u'Editar Titulo Sugerido'
                    data['id']= titulosugerido = TituloSugerido.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = SugenciaTituloForm(initial={'titulo': titulosugerido.nombre,
                                                               'nivel': titulosugerido.nivel})
                    data['form'] = form
                    template = get_template("postulate/requisitos/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addevidenciaexp':
                try:
                    data['id']= ExperienciaLaboral.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = SubirEvidenciaExperiencia()
                    template = get_template("postulate/requisitos/modal/formsubirevidenciaexperiencia.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Hoja de Vida'
                hoy = datetime.now().date()
                if 'tab' in request.GET:
                    data['tab'] = request.GET['tab']
                data['perfil'] = persona.mi_perfil()
                data['periodo'] = periodo
                docs = persona.documentos_personales()
                if docs:
                    if docs.hojavidaencuentraempleo:
                        data['hvencuentraempleo'] = docs
                data['otrascertificaciones'] = CertificadoIdioma.objects.filter(status=True, persona=persona).order_by('id')
                # data['niveltitulo'] = NivelTitulacion.objects.filter(nivel__in=[3,4], status=True).order_by('-rango')
                data['convocatorias_vigente'] = convocatorias = Convocatoria.objects.values('id').filter(status=True, finicio__lte=hoy, ffin__gte=hoy, vigente=True).exists()
                data['solicitudes'] = SolicitudPublicacion.objects.filter(persona=persona, aprobado=False, status=True).order_by('-fecha_creacion')
                data['numpartidas'] = Partida.objects.filter(status=True, convocatoria__vigente=True, convocatoria__finicio__lte=hoy, convocatoria__ffin__gte=hoy, vigente=True).count()
                data['desbloquear'] = desbloquear = False if PersonaAplicarPartida.objects.values('id').filter(persona=persona, status=True, estado=0, partida__vigente=True).exists() else True
                idtitulaciones = Titulacion.objects.filter(status=True, persona=persona).values_list(
                    'titulo__nivel__id', flat=True)
                data['niveltitulo'] = NivelTitulacion.objects.filter(status=True, id__in=idtitulaciones,nivel__in=[3,4]).order_by('-rango')
                # data['requisitos'] = requisitos = RequisitoDocumentoContrato.objects.filter(status=True, activo=True, anio__year=datetime.today().date().year)
                # data['requisitossub'] = PersonaRequisitoDocumentoContrato.objects.filter(status=True,requisito__in = requisitos.values_list('id',flat=True))
                data['requisitosperiodoconvocatoria'] = requisitosperiodoconvocatoria = PersonaPeriodoConvocatoria.objects.filter(status=True, persona=persona).order_by('-id')
                data['periodorequisitopendiente'] = periodorequisitopendiente = requisitosperiodoconvocatoria.filter(status=True, persona=persona, estado=0).exists()
                return render(request, "postulate/requisitos/view.html", data)
            except Exception as ex:
                import sys
                return JsonResponse({'resp': 'Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, ex)})

