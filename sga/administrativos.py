# -*- coding: UTF-8 -*-
import os
from datetime import datetime

import xlwt
import random
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models.query_utils import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from xlwt import *
from decorators import secure_module, last_access
from settings import PROFESORES_GROUP_ID, ALUMNOS_GROUP_ID, EMAIL_INSTITUCIONAL_AUTOMATICO, EMAIL_DOMAIN, \
    EMPLEADORES_GRUPO_ID, SITE_STORAGE
from sga.commonviews import adduserdata
from sga.forms import AdministrativosForm, GrupoUsuarioForm, NuevaInscripcionForm, FirmaPersonaForm, \
    PersonaDepartamentoFirmasForm, DepartamentoFirmaForm, TipoPersonaDepartamentoFirmaForm
from sga.funciones import MiPaginador, calculate_username, log, puede_realizar_accion, lista_correo, \
    generar_usuario, resetear_clave, variable_valor
from sga.models import Persona, miinstitucion, Profesor, TiempoDedicacionDocente, Administrativo, Coordinacion, \
    Inscripcion, InscripcionTesDrive, DocumentosDeInscripcion, CUENTAS_CORREOS, FirmaPersona, LogEntryBackup, \
    LogEntryBackupdos
from sagest.models import PersonaDepartamentoFirmas, DenominacionPuesto, TipoPersonaDepartamentoFirma, \
    DepartamentoFirma, Departamento
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt
from django.contrib.admin.models import LogEntry, ADDITION, DELETION
from django.template.context import Context
from django.template.loader import get_template
from bd.models import LogEntryLogin, MenuFavoriteProfile


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = AdministrativosForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['cedula'] and Persona.objects.filter(cedula=f.cleaned_data['cedula']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El numero de cedula ya esta registrado."})
                    if f.cleaned_data['pasaporte'] and Persona.objects.filter(pasaporte=f.cleaned_data['pasaporte']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El numero de pasaporte ya esta registrado."})
                    if not f.cleaned_data['cedula'] and not f.cleaned_data['pasaporte']:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe especificar un numero de identificación."})
                    personaadmin = Persona(nombres=f.cleaned_data['nombres'],
                                           apellido1=f.cleaned_data['apellido1'],
                                           apellido2=f.cleaned_data['apellido2'],
                                           cedula=f.cleaned_data['cedula'],
                                           pasaporte=f.cleaned_data['pasaporte'],
                                           nacimiento=f.cleaned_data['nacimiento'],
                                           sexo=f.cleaned_data['sexo'],
                                           paisnacimiento=f.cleaned_data['paisnacimiento'],
                                           provincianacimiento=f.cleaned_data['provincianacimiento'],
                                           cantonnacimiento=f.cleaned_data['cantonnacimiento'],
                                           parroquianacimiento=f.cleaned_data['parroquianacimiento'],
                                           nacionalidad=f.cleaned_data['nacionalidad'],
                                           pais=f.cleaned_data['pais'],
                                           provincia=f.cleaned_data['provincia'],
                                           canton=f.cleaned_data['canton'],
                                           parroquia=f.cleaned_data['parroquia'],
                                           sector=f.cleaned_data['sector'],
                                           direccion=f.cleaned_data['direccion'],
                                           direccion2=f.cleaned_data['direccion2'],
                                           num_direccion=f.cleaned_data['num_direccion'],
                                           telefono=f.cleaned_data['telefono'],
                                           telefono_conv=f.cleaned_data['telefono_conv'],
                                           sangre=f.cleaned_data['sangre'],
                                           email=f.cleaned_data['email'])
                    personaadmin.save(request)
                    administrativo = Administrativo(persona=personaadmin,
                                                    contrato='',
                                                    fechaingreso=datetime.now().date(),
                                                    activo=True)
                    administrativo.save(request)
                    username = calculate_username(personaadmin)
                    generar_usuario(personaadmin, username, variable_valor('ADMINISTRATIVOS_GROUP_ID'))
                    if EMAIL_INSTITUCIONAL_AUTOMATICO:
                        personaadmin.emailinst = username + '@' + EMAIL_DOMAIN
                    else:
                        personaadmin.emailinst = f.cleaned_data['emailinst']
                    personaadmin.save(request)
                    personaadmin.crear_perfil(administrativo=administrativo)
                    personaadmin.mi_ficha()
                    personaadmin.mi_perfil()
                    personaadmin.datos_extension()
                    correo = []
                    correo.append(personaadmin.email)
                    #send_html_mail("Crear nueva cuenta de correo ", "emails/nuevacuentacorreo.html", {'sistema': request.session['nombresistema'], 'persona': administrativo, 't': miinstitucion(), 'tipo_usuario': 'ESTUDIANTE', 'usuario': username, 'anio':str(personaadmin.nacimiento)[0:4]}, lista_correo([variable_valor('ADMINISTRADOR_CORREO_GROUP_ID')]), [], cuenta=CUENTAS_CORREOS[16][1])
                    send_html_mail("Crear nueva cuenta de correo ", "emails/nuevacuentacorreo.html", {'sistema': request.session['nombresistema'], 'persona': personaadmin, 't': miinstitucion(), 'tipo_usuario': 'ADMINISTRATIVO', 'usuario': username, 'anio':str(personaadmin.nacimiento)[0:4], 'tiposistema_': 2}, correo, [], cuenta=CUENTAS_CORREOS[16][1])
                    personaadmin.creacion_persona(request.session['nombresistema'],persona)
                    log(u'Adiciono personal administrativo: %s' % administrativo, request, "add")
                    return JsonResponse({"result": "ok", "id": administrativo.id})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': "bad", "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos." })

        elif action == 'adicionacarrera':
            try:
                f = NuevaInscripcionForm(request.POST)
                if f.is_valid():
                    administrativo = Administrativo.objects.get(pk=request.POST['id'])
                    carrera = f.cleaned_data['carrera']
                    sesion = f.cleaned_data['sesion']
                    modalidad = f.cleaned_data['modalidad']
                    sede = f.cleaned_data['sede']
                    if Inscripcion.objects.filter(persona=administrativo.persona, carrera=carrera).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra registrado en esa carrera."})
                    nuevainscripcion = Inscripcion(persona=administrativo.persona,
                                                   fecha=f.cleaned_data['fecha'],
                                                   carrera=carrera,
                                                   modalidad=modalidad,
                                                   sesion=sesion,
                                                   sede=sede)
                    nuevainscripcion.save()
                    hoy = datetime.now().date()
                    inscripciontesdrive = InscripcionTesDrive(inscripcion=nuevainscripcion,
                                                              licencia=f.cleaned_data['licencia'],
                                                              record=f.cleaned_data['record'],
                                                              certificado_tipo_sangre=f.cleaned_data['certificado_tipo_sangre'],
                                                              prueba_psicosensometrica=f.cleaned_data['prueba_psicosensometrica'],
                                                              certificado_estudios=f.cleaned_data['certificado_estudios'])
                    inscripciontesdrive.save()
                    nuevainscripcion.malla_inscripcion()
                    log(u'Adiciono inscripcion desde Administrativo: %s' % nuevainscripcion, request, "add")
                    documentos = DocumentosDeInscripcion(inscripcion=nuevainscripcion,
                                                         titulo=f.cleaned_data['titulo'],
                                                         acta=f.cleaned_data['acta'],
                                                         cedula=f.cleaned_data['cedula2'],
                                                         votacion=f.cleaned_data['votacion'],
                                                         actaconv=f.cleaned_data['actaconv'],
                                                         partida_nac=f.cleaned_data['partida_nac'],
                                                         pre=f.cleaned_data['prenivelacion'],
                                                         observaciones_pre=f.cleaned_data['observacionespre'],
                                                         fotos=f.cleaned_data['fotos'])
                    documentos.save()
                    administrativo.persona.crear_perfil(inscripcion=nuevainscripcion)
                    return JsonResponse({"result": "ok", "id": nuevainscripcion.id})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'adicionarpersonafirma':
            try:
                form = FirmaPersonaForm(request.POST, request.FILES)
                if 'firma' in request.FILES:
                    arch = request.FILES['firma']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 6291456:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 6 Mb."})
                    if not exte.lower() == 'png':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .png"})
                if form.is_valid():
                    firmapersona = FirmaPersona(persona_id=int(request.POST['id']),
                                                tipofirma=form.cleaned_data['tipofirma']
                                                )
                    firmapersona.save(request)
                    if 'firma' in request.FILES:
                        ruta = os.path.join(SITE_STORAGE, 'media', 'reportes', 'encabezados_pies', 'firmas','')
                        rutapdf = ruta + u"%s_%s.png" % (firmapersona.persona.cedula,firmapersona.tipofirma)
                        if os.path.isfile(rutapdf):
                            os.remove(rutapdf)

                        archivofirma = request.FILES['firma']
                        archivofirma._name = u"%s_%s.png" % (firmapersona.persona.cedula,firmapersona.tipofirma)
                        firmapersona.firma = archivofirma
                        firmapersona.save(request)

                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                f = AdministrativosForm(request.POST)
                if f.is_valid():
                    administrativo = Administrativo.objects.get(pk=request.POST['id'])
                    personaadmin = administrativo.persona
                    personaadmin.nombres = f.cleaned_data['nombres']
                    personaadmin.apellido1 = f.cleaned_data['apellido1']
                    personaadmin.apellido2 = f.cleaned_data['apellido2']
                    personaadmin.nacimiento = f.cleaned_data['nacimiento']
                    personaadmin.sexo = f.cleaned_data['sexo']
                    personaadmin.paisnacimiento = f.cleaned_data['paisnacimiento']
                    personaadmin.provincianacimiento = f.cleaned_data['provincianacimiento']
                    personaadmin.cantonnacimiento = f.cleaned_data['cantonnacimiento']
                    personaadmin.parroquianacimiento = f.cleaned_data['parroquianacimiento']
                    personaadmin.nacionalidad = f.cleaned_data['nacionalidad']
                    personaadmin.pais = f.cleaned_data['pais']
                    personaadmin.provincia = f.cleaned_data['provincia']
                    personaadmin.canton = f.cleaned_data['canton']
                    personaadmin.parroquia = f.cleaned_data['parroquia']
                    personaadmin.sector = f.cleaned_data['sector']
                    personaadmin.direccion = f.cleaned_data['direccion']
                    personaadmin.direccion2 = f.cleaned_data['direccion2']
                    personaadmin.num_direccion = f.cleaned_data['num_direccion']
                    personaadmin.telefono = f.cleaned_data['telefono']
                    personaadmin.telefono_conv = f.cleaned_data['telefono_conv']
                    personaadmin.email = f.cleaned_data['email']
                    personaadmin.emailinst = f.cleaned_data['emailinst']
                    personaadmin.sangre = f.cleaned_data['sangre']
                    personaadmin.save(request)
                    log(u'Modifico administrativo: %s' % administrativo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'resetear':
            try:
                administrativo = Administrativo.objects.get(pk=request.POST['id'])
                resetear_clave(administrativo.persona)
                log(u'Reseteo clave de usuario: %s' % administrativo, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addprofesor':
            try:
                administrativo = Administrativo.objects.get(pk=request.POST['id'])
                if administrativo.persona.profesor_set.exists():
                    return JsonResponse({"result": "bad", "mensaje": u"El usuario ya tiene un perfil como profesor."})
                profesor = Profesor(persona=administrativo.persona,
                                    activo=True,
                                    fechaingreso=datetime.now().date(),
                                    coordinacion=Coordinacion.objects.all()[0],
                                    dedicacion=TiempoDedicacionDocente.objects.all()[0])
                profesor.save()
                grupo = Group.objects.get(pk=PROFESORES_GROUP_ID)
                grupo.user_set.add(administrativo.persona.usuario)
                grupo.save()
                administrativo.persona.crear_perfil(profesor=profesor)
                log(u'Adiciono profesor: %s' % profesor, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'activar':
            try:
                administrativo = Administrativo.objects.get(pk=request.POST['id'])
                usuario = administrativo.persona.usuario
                usuario.is_active = True
                usuario.save()
                log(u'Activo usuario: %s' % administrativo, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'activarperfil':
            try:
                administrativo = Administrativo.objects.get(pk=request.POST['id'])
                administrativo.activo = True
                administrativo.save()
                log(u'Activo perfil de usuario: %s' % administrativo, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'desactivar':
            try:
                administrativo = Administrativo.objects.get(pk=request.POST['id'])
                ui = administrativo.persona.usuario
                ui.is_active = False
                ui.save()
                log(u'Desactivo usuario: %s' % administrativo, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'desactivarperfil':
            try:
                administrativo = Administrativo.objects.get(pk=request.POST['id'])
                administrativo.activo = False
                administrativo.save()
                log(u'Desactivo perfil de usuario: %s' % administrativo, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addgrupo':
            try:
                administrativo = Administrativo.objects.get(pk=request.POST['id'])
                form = GrupoUsuarioForm(request.POST)
                if form.is_valid():
                    grupo = form.cleaned_data['grupo']
                    grupo.user_set.add(administrativo.persona.usuario)
                    grupo.save()
                    log(u'Adiciono grupo de usuarios: %s - %s' % (grupo, administrativo), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delgrupo':
            try:
                puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                administrativo = Administrativo.objects.get(pk=request.POST['id'])
                grupo = Group.objects.get(pk=request.POST['idg'])
                if grupo.id in [PROFESORES_GROUP_ID, ALUMNOS_GROUP_ID, EMPLEADORES_GRUPO_ID]:
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar del grupo seleccionado."})
                if administrativo.persona.usuario.groups.exclude(id__in=[PROFESORES_GROUP_ID, ALUMNOS_GROUP_ID, EMPLEADORES_GRUPO_ID]).count() <= 1:
                    return JsonResponse({"result": "bad", "mensaje": u"El usuario debe de pertenecer a un grupo."})
                grupo.user_set.remove(administrativo.persona.usuario)
                grupo.save()
                log(u'Elimino de grupo de usuarios: %s - %s' % (grupo, administrativo), request, "del")

                pers = administrativo.persona
                # eTemplateBaseSetting = request.session['eTemplateBaseSetting']
                for perfil in pers.mis_perfilesusuarios():
                    eMenuFavoriteProfile = MenuFavoriteProfile.objects.filter(setting_id__in=[1, 2], profile=perfil)
                    for favorito in eMenuFavoriteProfile:
                        grupo_modulos = grupo.modulogrupo_set.filter(status=True)
                        for grupo_m in grupo_modulos:
                            for modulo in grupo_m.modules():
                                favorito.modules.remove(modulo.id)
                                log(u'Quito modulo favorito: %s de la APP: %s' % (modulo, favorito.setting), request, "del")

                return JsonResponse({"result": "ok", "mensaje":u"Grupo eliminado correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletefirma':
            try:
                firma = FirmaPersona.objects.get(pk=request.POST['id'])
                firma.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addhistorial':
            try:
                form = PersonaDepartamentoFirmasForm(request.POST)
                if form.is_valid():
                    personadepartamento = None
                    tipopersonadepartamento = None
                    denominacionpuesto = None
                    departamento = None
                    departamentofirma = None

                    if int(request.POST['personadepartamento']) > 0:
                        personadepartamento = Persona.objects.get(pk=int(request.POST['personadepartamento']))

                    if int(request.POST['tipopersonadepartamento']) > 0:
                        tipopersonadepartamento = TipoPersonaDepartamentoFirma.objects.get(pk=int(request.POST['tipopersonadepartamento']))

                    if int(request.POST['denominacionpuesto']) > 0:
                        denominacionpuesto = DenominacionPuesto.objects.get(pk=int(request.POST['denominacionpuesto']))

                    if int(request.POST['departamento']) > 0:
                        departamento = Departamento.objects.get(pk=int(request.POST['departamento']))

                    if int(request.POST['departamentofirma']) > 0:
                        departamentofirma = DepartamentoFirma.objects.get(pk=int(request.POST['departamentofirma']))

                    personafirma = PersonaDepartamentoFirmas(
                        personadepartamento=personadepartamento,
                        tipopersonadepartamento=tipopersonadepartamento,
                        denominacionpuesto=denominacionpuesto,
                        departamento=departamento,
                        departamentofirma=departamentofirma,
                        tiposubrogante=form.cleaned_data['tiposubrogante'],
                        activo=form.cleaned_data['activo'],
                        actualidad=form.cleaned_data['actualidad'],
                        fechainicio=form.cleaned_data['fechainicio'],
                        fechafin=form.cleaned_data['fechafin']
                    )
                    personafirma.save(request)
                    log(u'Adiciono historial firma a una persona: %s' % personafirma, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edithistorial':
            try:
                form = PersonaDepartamentoFirmasForm(request.POST)
                if form.is_valid():
                    personadepartamento = None
                    tipopersonadepartamento = None
                    denominacionpuesto = None
                    departamento = None
                    departamentofirma = None
                    if int(request.POST['personadepartamento']) > 0:
                        personadepartamento = Persona.objects.get(pk=int(request.POST['personadepartamento']))

                    if int(request.POST['tipopersonadepartamento']) > 0:
                        tipopersonadepartamento = TipoPersonaDepartamentoFirma.objects.get(pk=int(request.POST['tipopersonadepartamento']))

                    if int(request.POST['denominacionpuesto']) > 0:
                        denominacionpuesto = DenominacionPuesto.objects.get(pk=int(request.POST['denominacionpuesto']))

                    if int(request.POST['departamento']) > 0:
                        departamento = Departamento.objects.get(pk=int(request.POST['departamento']))

                    if int(request.POST['departamentofirma']) > 0:
                        departamentofirma = DepartamentoFirma.objects.get(pk=int(request.POST['departamentofirma']))

                    personafirma = PersonaDepartamentoFirmas.objects.get(pk=request.POST['id'])
                    personafirma.personadepartamento=personadepartamento
                    personafirma.tipopersonadepartamento=tipopersonadepartamento
                    personafirma.denominacionpuesto=denominacionpuesto
                    personafirma.departamento=departamento
                    personafirma.departamentofirma=departamentofirma
                    personafirma.tiposubrogante=form.cleaned_data['tiposubrogante']
                    personafirma.activo=form.cleaned_data['activo']
                    personafirma.actualidad=form.cleaned_data['actualidad']
                    personafirma.fechainicio=form.cleaned_data['fechainicio']
                    personafirma.fechafin=form.cleaned_data['fechafin']

                    personafirma.save(request)
                    log(u'Adiciono historial firma a una persona: %s' % personafirma, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delhistorial':
            try:
                personafirma = PersonaDepartamentoFirmas.objects.get(pk=request.POST['id'])
                personafirma.status = False
                personafirma.save(request)
                log(u'Elimino Historial Firma: %s' % personafirma, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'adddepartamentofirma':
            try:
                form = DepartamentoFirmaForm(request.POST)
                if form.is_valid():

                    departamentofirma = DepartamentoFirma(
                        nombre=form.cleaned_data['nombre']
                    )
                    departamentofirma.save(request)
                    log(u'Adiciono Departamento Firma: %s' % departamentofirma, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editdepartamentofirma':
            try:
                form = DepartamentoFirmaForm(request.POST)
                if form.is_valid():
                    departamentofirma = DepartamentoFirma.objects.get(pk=request.POST['id'])
                    departamentofirma.nombre=form.cleaned_data['nombre']
                    departamentofirma.save(request)
                    log(u'Modifico Departamento de  firma: %s' % departamentofirma, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deldepartamentofirma':
            try:
                departamentofirma = DepartamentoFirma.objects.get(pk=request.POST['id'])
                departamentofirma.status = False
                departamentofirma.save(request)
                log(u'Elimino Departamento de Firma: %s' % departamentofirma, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addtipodepartamentofirma':
            try:
                form = TipoPersonaDepartamentoFirmaForm(request.POST)
                if form.is_valid():

                    tipodepartamentofirma = TipoPersonaDepartamentoFirma(
                        nombre=form.cleaned_data['nombre']
                    )
                    tipodepartamentofirma.save(request)
                    log(u'Adiciono Tipo Departamento Firma: %s' % tipodepartamentofirma, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edittipodepartamentofirma':
            try:
                form = TipoPersonaDepartamentoFirmaForm(request.POST)
                if form.is_valid():
                    tipodepartamentofirma = TipoPersonaDepartamentoFirma.objects.get(pk=request.POST['id'])
                    tipodepartamentofirma.nombre=form.cleaned_data['nombre']
                    tipodepartamentofirma.save(request)
                    log(u'Modifico Tipo Departamento de  firma: %s' % tipodepartamentofirma, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deltipodepartamentofirma':
            try:
                tipodepartamentofirma = TipoPersonaDepartamentoFirma.objects.get(pk=request.POST['id'])
                tipodepartamentofirma.status = False
                tipodepartamentofirma.save(request)
                log(u'Elimino Tipo Departamento de Firma: %s' % tipodepartamentofirma, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})


        elif action == 'auditoria':
            try:
                baseDate = datetime.today()
                year = request.POST['year'] if 'year' in request.POST and request.POST['year'] else baseDate.year
                month = request.POST['month'] if 'month' in request.POST and request.POST['month'] else baseDate.month
                data['idi'] = request.POST['id']
                data['administrativo'] = administrativo_seleccionado = Administrativo.objects.get(pk=int(encrypt(request.POST['id'])))
                logs = LogEntry.objects.filter(Q(change_message__icontains=administrativo_seleccionado.persona.__str__()) | Q(user=administrativo_seleccionado.persona.usuario), action_time__year=year).exclude(user__is_superuser=True)
                logs1 = LogEntryBackup.objects.filter(Q(change_message__icontains=administrativo_seleccionado.persona.__str__()) | Q(user=administrativo_seleccionado.persona.usuario), action_time__year=year).exclude(user__is_superuser=True)
                logs2 = LogEntryBackupdos.objects.filter(Q(change_message__icontains=administrativo_seleccionado.persona.__str__()) | Q(user=administrativo_seleccionado.persona.usuario), action_time__year=year).exclude(user__is_superuser=True)
                logs3 = LogEntryLogin.objects.filter(user=administrativo_seleccionado.persona.usuario, action_time__year=year).exclude(user__is_superuser=True, action_app=2)
                if int(month):
                    logs = logs.filter(action_time__month=month)
                    logs1 = logs1.filter(action_time__month=month)
                    logs2 = logs2.filter(action_time__month=month)
                    logs3 = logs3.filter(action_time__month=month)
                logslist0 = list(logs.values_list("action_time", "action_flag", "change_message", "user__username"))
                logslist1 = list(logs1.values_list("action_time", "action_flag", "change_message", "user__username"))
                logslist2 = list(logs2.values_list("action_time", "action_flag", "change_message", "user__username"))
                logslist=logslist0+logslist1+logslist2
                aLogList = []
                for xItem in logslist:
                    #print(xItem)
                    if xItem[1] == 1:
                        action_flag = '<label class="label label-success">AGREGAR</label>'
                    elif xItem[1] == 2:
                        action_flag = '<label class="label label-info">EDITAR</label>'
                    elif xItem[1] == 3:
                        action_flag = '<label class="label label-important">ELIMINAR</label>'
                    else:
                        action_flag = '<label class="label label-warning">OTRO</label>'
                    aLogList.append({"action_time": xItem[0],
                                     "action_flag": action_flag,
                                     "change_message": xItem[2],
                                     "username": xItem[3]})
                for xItem in list(logs3.values_list("action_time", "action_flag", "change_message", "user__username", "id")):
                    l = LogEntryLogin.objects.get(pk=xItem[4])
                    if xItem[1] == 1:
                        action_flag = '<label class="label label-success">EXITOSO</label>'
                    elif xItem[1] == 2:
                        action_flag = '<label class="label label-warning">FALLIDO</label>'
                    else:
                        action_flag = '<label class="label label-important">DESCONOCIDO</label>'
                    aLogList.append({"action_time": xItem[0],
                                     "action_flag": action_flag,
                                     "change_message": l.get_data_message(),
                                     "username": xItem[3]
                                     })
                my_time = datetime.min.time()
                datalogs = aLogList
                data['logs'] = sorted(datalogs, key=lambda x: x['action_time'], reverse=True)
                numYear = 6
                dateListYear = []
                for x in range(0, numYear):
                    dateListYear.append((baseDate.year)-x)
                data['list_years'] = dateListYear
                data['year_now'] = int(year)
                data['month_now'] = int(month)
                template = get_template('administrativos/auditoria.html')
                json_contenido = template.render(data)
                return JsonResponse({"result": "ok", "contenido":json_contenido })
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Listado de personal administrativo'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Adicionar personal administrativo'
                    form = AdministrativosForm()
                    form.adicionar()
                    data['email_domain'] = EMAIL_DOMAIN
                    data['form'] = form
                    return render(request, "administrativos/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'adicionacarrera':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Inscribir Administrativo en carrera'
                    data['administrativo'] = administrativo = Administrativo.objects.get(pk=request.GET['id'])
                    data['form'] = NuevaInscripcionForm(initial={'fecha': datetime.now().date()})
                    data['dominio'] = EMAIL_DOMAIN
                    return render(request, "administrativos/adicionacarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'listadofirmas':
                try:
                    data['title'] = u'Persona'
                    data['personafirma'] = personafirma = Persona.objects.get(pk=int(request.GET['idpersona']))
                    data['listadofirma'] = FirmaPersona.objects.filter(persona=personafirma, status=True)
                    d = datetime.now()
                    data['horasegundo'] = d.strftime('%Y%m%d_%H%M%S')
                    return render(request, "administrativos/listadofirmas.html", data)
                except Exception as ex:
                    pass

            elif action == 'adicionarpersonafirma':
                try:
                    data['title'] = u'Adicionar firma'
                    data['personafirma'] = Persona.objects.get(pk=int(request.GET['idpersona']))
                    form = FirmaPersonaForm()
                    data['form'] = form
                    return render(request, "administrativos/adicionarpersonafirma.html", data)
                except Exception as ex:
                    pass

            elif action == 'desactivar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Desactivar usuario'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    return render(request, "administrativos/desactivar.html", data)
                except Exception as ex:
                    pass

            elif action == 'desactivarperfil':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Desactivar perfil de usuario'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    return render(request, "administrativos/desactivarperfil.html", data)
                except Exception as ex:
                    pass

            elif action == 'activar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Activar usuario'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    return render(request, "administrativos/activar.html", data)
                except Exception as ex:
                    pass

            elif action == 'activarperfil':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Activar perfil de usuario'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    return render(request, "administrativos/activarperfil.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data = verificarbusqueda(request, data)
                    data['title'] = u'Editar personal administrativo'
                    data['administrativo'] = administrativo = Administrativo.objects.get(pk=request.GET['id'])
                    personaadmin = administrativo.persona
                    form = AdministrativosForm(initial={'nombres': personaadmin.nombres,
                                                        'apellido1': personaadmin.apellido1,
                                                        'apellido2': personaadmin.apellido2,
                                                        'cedula': personaadmin.cedula,
                                                        'sexo': personaadmin.sexo,
                                                        'pasaporte': personaadmin.pasaporte,
                                                        'nacimiento': personaadmin.nacimiento,
                                                        'paisnacimiento': personaadmin.paisnacimiento,
                                                        'provincianacimiento': personaadmin.provincianacimiento,
                                                        'cantonnacimiento': personaadmin.cantonnacimiento,
                                                        'parroquianacimiento': personaadmin.parroquianacimiento,
                                                        'nacionalidad': personaadmin.nacionalidad,
                                                        'pais': personaadmin.pais,
                                                        'provincia': personaadmin.provincia,
                                                        'canton': personaadmin.canton,
                                                        'parroquia': personaadmin.parroquia,
                                                        'sector': personaadmin.sector,
                                                        'direccion': personaadmin.direccion,
                                                        'direccion2': personaadmin.direccion2,
                                                        'num_direccion': personaadmin.num_direccion,
                                                        'telefono': personaadmin.telefono,
                                                        'telefono_conv': personaadmin.telefono_conv,
                                                        'email': personaadmin.email,
                                                        'emailinst': personaadmin.emailinst,
                                                        'sangre': personaadmin.sangre})
                    form.editar(personaadmin)
                    data['form'] = form
                    data['email_domain'] = EMAIL_DOMAIN
                    return render(request, "administrativos/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'addgrupo':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Adicionar grupo'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    form = GrupoUsuarioForm()
                    form.grupos(Group.objects.all().exclude(id__in=[PROFESORES_GROUP_ID, ALUMNOS_GROUP_ID, EMPLEADORES_GRUPO_ID]).order_by('name'))
                    data['form'] = form
                    return render(request, "administrativos/addgrupo.html", data)
                except Exception as ex:
                    pass

            elif action == 'resetear':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Resetear clave del usuario'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    return render(request, "administrativos/resetear.html", data)
                except Exception as ex:
                    pass

            elif action == 'addprofesor':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Crear cuenta de profesor'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    return render(request, "administrativos/addprofesor.html", data)
                except Exception as ex:
                    pass

            elif action == 'delgrupo':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Eliminar de grupo'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    data['grupo'] = Group.objects.get(pk=request.GET['idg'])
                    return render(request, "administrativos/delgrupo.html", data)
                except Exception as ex:
                    pass

            elif action == 'exportarexcel':
                try:
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    administrativos = Administrativo.objects.filter(status=True)
                    ws = wb.add_sheet("administrativos")
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=administrativos' + random.randint( 1, 10000).__str__() + '.xls'
                    columns = [
                        (u"No.", 1500),
                        (u"Nombres", 6000),
                        (u"Cédula", 6000),
                        (u"Contrato", 6000),
                        (u"Correo personal", 6000),
                        (u"Correo institucional", 6000),
                        (u"Teléfono", 6000)
                    ]
                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 2
                    i=0
                    for x in administrativos:
                        i+=1
                        campo1 = x.persona.nombre_completo_inverso()
                        campo2 = x.persona.cedula
                        campo3 = x.contrato
                        campo4 = x.persona.email
                        campo5 = x.persona.emailinst
                        campo6 = x.persona.telefono

                        ws.write(row_num, 0, i, font_style2)
                        ws.write(row_num, 1, campo1, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, campo3, font_style2)
                        ws.write(row_num, 4, campo4, font_style2)
                        ws.write(row_num, 5, campo5, font_style2)
                        ws.write(row_num, 6, campo6, font_style2)

                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'viewhistorial':
                try:
                    data['title'] = u'Historial'
                    search = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            firmas = PersonaDepartamentoFirmas.objects.filter(
                                Q(personadepartamento__nombres__icontains=search) |
                                Q(personadepartamento__apellido1__icontains=search) |
                                Q(personadepartamento__apellido2__icontains=search) |
                                Q(personadepartamento__cedula__icontains=search) |
                                Q(personadepartamento__pasaporte__icontains=search)).order_by('departamentofirma_id','-fechainicio')
                        else:
                            firmas = PersonaDepartamentoFirmas.objects.filter(Q(personadepartamento__apellido1__icontains=ss[0]) &
                                                                              Q(personadepartamento__apellido2__icontains=ss[1]), status=True).order_by('departamentofirma_id','-fechainicio')
                    else:
                        firmas = PersonaDepartamentoFirmas.objects.filter(status=True).order_by('departamentofirma_id','-fechainicio')
                    paging = MiPaginador(firmas, 30)
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
                    data['listado'] = page.object_list
                    return render(request, "administrativos/viewhistorial.html", data)
                except Exception as ex:
                    pass

            elif action == 'addhistorial':
                try:
                    data['title'] = u'Adicionar Historial Firmas'
                    form = PersonaDepartamentoFirmasForm()
                    data['form'] = form
                    return render(request, "administrativos/addhistorial.html", data)
                except Exception as ex:
                    pass

            elif action == 'edithistorial':
                try:
                    data['title'] = u'Editar Historial Firma'
                    data['personafirma'] = personafirma = PersonaDepartamentoFirmas.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(personafirma)
                    data['form'] = PersonaDepartamentoFirmasForm(initial=initial)
                    return render(request, "administrativos/edithistorial.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewdepartamentofirma':
                try:
                    data['title'] = u'Listado Departamento Firma'
                    search = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        departamentosfirmas = DepartamentoFirma.objects.filter(Q(nombre__icontains=search))
                        ss = search.split(' ')
                        if len(ss) == 1:
                            departamentosfirmas = DepartamentoFirma.objects.filter(Q(nombre__icontains=search), Q(status=True))
                    else:
                        departamentosfirmas = DepartamentoFirma.objects.filter(status=True)
                    paging = MiPaginador(departamentosfirmas, 30)
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
                    data['listado'] = page.object_list
                    return render(request, "administrativos/viewdepartamentofirma.html", data)
                except Exception as ex:
                    pass

            elif action == 'adddepartamentofirma':
                try:
                    data['title'] = u'Adicionar Departamento Firma'
                    form = DepartamentoFirmaForm()
                    data['form'] = form
                    return render(request, "administrativos/adddepartamentofirma.html", data)
                except Exception as ex:
                    pass



            elif action == 'editdepartamentofirma':
                try:
                    data['title'] = u'Editar Historial Firma'
                    data['departamentofirma'] = departamentofirma = DepartamentoFirma.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(departamentofirma)
                    data['form'] = DepartamentoFirmaForm(initial=initial)
                    return render(request, "administrativos/editdepartamentofirma.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewtipodepartamentofirma':
                try:
                    data['title'] = u'Listado Tipo Departamento Firma'
                    search = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        tipodepartamentosfirmas = TipoPersonaDepartamentoFirma.objects.filter(Q(nombre__icontains=search))
                        ss = search.split(' ')
                        if len(ss) == 1:
                            tipodepartamentosfirmas = TipoPersonaDepartamentoFirma.objects.filter(Q(nombre__icontains=search), Q(status=True))
                    else:
                        tipodepartamentosfirmas = TipoPersonaDepartamentoFirma.objects.filter(status=True)
                    paging = MiPaginador(tipodepartamentosfirmas, 30)
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
                    data['listado'] = page.object_list
                    return render(request, "administrativos/viewtipodepartamentofirma.html", data)
                except Exception as ex:
                    pass

            elif action == 'addtipodepartamentofirma':
                try:
                    data['title'] = u'Adicionar Tipo Departamento Firma'
                    form = TipoPersonaDepartamentoFirmaForm()
                    data['form'] = form
                    return render(request, "administrativos/addtipodepartamentofirma.html", data)
                except Exception as ex:
                    pass



            elif action == 'edittipodepartamentofirma':
                try:
                    data['title'] = u'Editar Historial Firma'
                    data['tipodepartamentofirma'] = tipodepartamentofirma = TipoPersonaDepartamentoFirma.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(tipodepartamentofirma)
                    data['form'] = TipoPersonaDepartamentoFirmaForm(initial=initial)
                    return render(request, "administrativos/edittipodepartamentofirma.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                perfil = request.GET.get('perfil','')
                search = request.GET.get('s','')
                gruposelect = request.GET.get('gruposelect',0)
                url_vars = ''

                grupos = Group.objects.all()
                listagrupo = grupos.values_list('id')
                if int(gruposelect) > 0:
                    filtros = Q(persona__usuario__groups__in=[int(gruposelect)])
                    data['gruposelect'] = int(gruposelect)
                    url_vars += f"&gruposelect={gruposelect}"
                else:
                    filtros = Q(persona__usuario__groups__in=listagrupo)
                    url_vars += f"&gruposelect={gruposelect}"
                    data['gruposelect'] = int(gruposelect)

                if search:
                    data['s'] = search = request.GET['s'].strip()
                    ss = search.split(' ')
                    url_vars += "&s={}".format(search)
                    if len(ss) == 1:
                        filtros = filtros & (Q(persona__nombres__icontains=search) |
                                                                 Q(persona__apellido1__icontains=search) |
                                                                 Q(persona__apellido2__icontains=search) |
                                                                 Q(persona__cedula__icontains=search) |
                                                                 Q(persona__pasaporte__icontains=search))
                        url_vars += f"&s={search}"
                    else:
                        filtros = filtros & (Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1]))
                        url_vars += f"&s={ss}"

                if perfil:
                    if perfil == '1':
                        filtros = filtros & (Q(activo=True))
                    elif perfil == '2':
                        filtros = filtros & (Q(activo=False))
                    data['perfil'] = perfil
                    url_vars += f"&perfil={perfil}"
                if 'id' in request.GET:
                    id = request.GET['id']
                    filtros = filtros & (Q(id=id))

                administrativos = Administrativo.objects.filter(filtros).distinct()
                paging = MiPaginador(administrativos, 25)
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
                data['administrativos'] = page.object_list
                # data['grupo_docentes'] = PROFESORES_GROUP_ID
                # data['grupo_empleadores'] = EMPLEADORES_GRUPO_ID
                # data['grupo_estudiantes'] = ALUMNOS_GROUP_ID
                # data['grupo_aspirantes'] = 199
                data["url_vars"] = url_vars
                data["url_params"] = url_vars
                # data['grupo_administrativos'] = variable_valor('ADMINISTRATIVOS_GROUP_ID')
                data['ids_group_default'] = list(map(int, variable_valor('IDS_GRUPOS_ESTATICOS')))
                data['grupos'] = grupos
                return render(request, "administrativos/view.html", data)
            except Exception as ex:
                pass


def verificarbusqueda(request, data):
    perfil = None
    search = None
    gruposelect = None
    regreso=False
    if 'g' in request.GET:
        gruposelect = request.GET['g']
        regreso=True
    if 's' in request.GET:
        search = request.GET['s']
        regreso = True
    if 'perfil' in request.GET:
        perfil = request.GET['perfil']
        regreso = True
    data['gruposelect'] = gruposelect
    data['search'] = search
    data['perfil'] = perfil
    data['regreso'] = regreso
    return data
