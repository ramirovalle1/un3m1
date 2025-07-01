# -*- coding: UTF-8 -*-
import os
import io
import sys
import time
import zipfile
from datetime import datetime, timedelta

import xlsxwriter
import xlwt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction, connections
from django.forms import model_to_dict
from django.template import Context
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.urls import reverse

from inno.models import HorarioTutoriaAcademica
from moodle import moodle
from decorators import secure_module, last_access
from sagest.models import SolicitudPublicacion, DistributivoPersonaHistorial
from settings import DEFAULT_PASSWORD, PROFESORES_GROUP_ID, UTILIZA_FICHA_MEDICA, EMAIL_DOMAIN, \
    EMAIL_INSTITUCIONAL_AUTOMATICO, ALUMNOS_GROUP_ID, EMPLEADORES_GRUPO_ID, SISTEMAS_GROUP_ID, CLAVE_USUARIO_CEDULA, \
    TIPO_DOCENTE_FIRMA, SITE_STORAGE
from sga.commonviews import adduserdata, obtener_reporte, justificar_asistencia
from sga.excelbackground import reporte_auditoria_background
from sga.forms import ProfesorForm, GrupoUsuarioForm, ActualizacionDatosForm, CalificacionDiaForm, TipoProfesorForm, \
    ProfesorZoomUrlForm, PresentacionDiapositivaEditForm, \
    TareaPracticaSilaboSemanalEditForm, TestSilaboSemanalEditForm, \
    CompendioSilaboSemanalEditForm, TareaPracticaSilaboSemanalEditForm, \
    TestSilaboSemanalEditForm, ForoSilaboSemanalEditForm, TareaSilaboSemanalEditForm, \
    MaterialAdicionalSilaboSemanalEditForm, GuiaDocenteSilaboSemanalEditForm, \
    GuiaEstudianteSilaboSemanalEditForm, VideoMagistralSilaboSemanalEditForm, ConfigurarRegistroAsistenciaForm, \
    FirmaPersonaForm, TestSilaboSemanalAdmisionEditForm
from sga.funciones import MiPaginador, calculate_username, log, puede_realizar_accion, generar_usuario, variable_valor, \
    null_to_decimal, resetear_clave, elimina_tildes, puede_realizar_accion_afirmativo, convertir_fecha
from sga.models import Profesor, Persona, Clase, Sesion, ProfesorTipo, miinstitucion, Administrativo, Turno, \
    CategorizacionDocente, Materia, ProfesorMateria, CUENTAS_CORREOS, ProfesorDistributivoHoras, TipoProfesor, \
    AsignaturaMallaPreferencia, Titulacion, AsignaturaMalla, ArticuloInvestigacion, HorarioPreferenciaObse, Silabo, \
    DetalleSilaboSemanalTema, PlanificacionClaseSilabo, CapituloLibroInvestigacion, LibroInvestigacion, \
    PonenciasInvestigacion, ProyectoInvestigacionExterno, RespuestaEvaluacionAcreditacion, MigracionEvaluacionDocente, \
    ResumenFinalProcesoEvaluacionIntegral, DiapositivaSilaboSemanal, TareaPracticaSilaboSemanal, TestSilaboSemanal, \
    CompendioSilaboSemanal, TareaPracticaSilaboSemanal, \
    TestSilaboSemanal, ForoSilaboSemanal, TareaSilaboSemanal, MaterialAdicionalSilaboSemanal, GuiaDocenteSilaboSemanal, \
    GuiaEstudianteSilaboSemanal, VideoMagistralSilaboSemanal, LogEntryBackup, LogEntryBackupdos, SesionZoom, \
    DesactivarSesionZoom, SilaboSemanal, DetalleDistributivo, ComplexivoClase, ComplexivoLeccion, AsistenciaLeccion, \
    HistorialPersonaPPL, Matricula, FirmaPersona, ClaseSincronica, ClaseAsincronica, TestSilaboSemanalAdmision, Notificacion
from sga.tasks import send_html_mail, conectar_cuenta
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.templatetags.sga_extras import encrypt
from xlwt import *
from django.contrib.admin.models import LogEntry, ADDITION, DELETION
from bd.models import LogEntryLogin
from sga.funciones import convertir_fecha, convertir_fecha_invertida

unicode = str


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request ):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    data['puede_modificar_silabos'] = puede_administrar = puede_realizar_accion_afirmativo(request,'sga.puede_modificar_silabos_adm')
    data['ids_permitido_asistencia'] = [810, 20533, 822, 25298, 10724, 22207, 840]
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:

                fecha_str = request.POST['fechaingreso']
                fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
                fecha_nueva_str = fecha_obj.strftime('%d-%m-%Y')

                fecha_str_naci = request.POST['nacimiento']
                fecha_obj_naci = datetime.strptime(fecha_str_naci, '%Y-%m-%d')
                fecha_nueva_str_naci = fecha_obj_naci.strftime('%d-%m-%Y')

                data = request.POST.copy()
                data['fechaingreso'] = fecha_nueva_str
                data['nacimiento'] = fecha_nueva_str_naci

                # form = ProfesorForm(data)

                f = ProfesorForm(data)
                if f.is_valid():
                    cedula = f.cleaned_data['cedula'].strip()
                    pasaporte = f.cleaned_data['pasaporte'].strip()
                    personaprofesor = None
                    if not cedula and not pasaporte:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe especificar un número de identificación."})
                    if cedula: #actualizar o crea persona por busqueda de cedula
                        if cedula and Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula)).exists():
                            personaprofesor = Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula)).last()
                            personaprofesor.pais = f.cleaned_data['pais']
                            personaprofesor.provincia = f.cleaned_data['provincia']
                            personaprofesor.canton = f.cleaned_data['canton']
                            personaprofesor.parroquia = f.cleaned_data['parroquia']
                            personaprofesor.sector = f.cleaned_data['sector']
                            personaprofesor.direccion = f.cleaned_data['direccion']
                            personaprofesor.direccion2 = f.cleaned_data['direccion2']
                            personaprofesor.num_direccion = f.cleaned_data['num_direccion']
                            personaprofesor.telefono = f.cleaned_data['telefono']
                            personaprofesor.telefono_conv = f.cleaned_data['telefono_conv']
                            personaprofesor.email = f.cleaned_data['email']
                            personaprofesor.save(request)
                        else:
                            personaprofesor = Persona(
                                nombres=f.cleaned_data['nombres'],
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
                                email=f.cleaned_data['email'])
                            personaprofesor.save(request)
                    else:
                        if pasaporte: #actualizar o crea persona por busqueda de pasaporte
                            if pasaporte and Persona.objects.filter(Q(cedula=pasaporte) | Q(pasaporte=pasaporte)).exists():
                                personaprofesor = Persona.objects.filter(Q(cedula=pasaporte) | Q(pasaporte=pasaporte)).last()
                                personaprofesor.pais = f.cleaned_data['pais']
                                personaprofesor.provincia = f.cleaned_data['provincia']
                                personaprofesor.canton = f.cleaned_data['canton']
                                personaprofesor.parroquia = f.cleaned_data['parroquia']
                                personaprofesor.sector = f.cleaned_data['sector']
                                personaprofesor.direccion = f.cleaned_data['direccion']
                                personaprofesor.direccion2 = f.cleaned_data['direccion2']
                                personaprofesor.num_direccion = f.cleaned_data['num_direccion']
                                personaprofesor.telefono = f.cleaned_data['telefono']
                                personaprofesor.telefono_conv = f.cleaned_data['telefono_conv']
                                personaprofesor.email = f.cleaned_data['email']
                                personaprofesor.save(request)
                            else:
                                personaprofesor = Persona(
                                    nombres=f.cleaned_data['nombres'],
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
                                    email=f.cleaned_data['email'])
                                personaprofesor.save(request)
                    if cedula: #consultar registro de docente por cedula
                        if Profesor.objects.filter(Q(persona__cedula=cedula) | Q(persona__pasaporte=cedula)).exists():
                            return JsonResponse({'result': 'bad', "mensaje": u"Error: El docente ya se encuentra registrado."})
                    if pasaporte: #consultar registro de docente por pasaporte
                        if Profesor.objects.filter(Q(persona__cedula=pasaporte) | Q(persona__pasaporte=pasaporte)).exists():
                           return JsonResponse({'result': 'bad', "mensaje": u"Error: El docente ya se encuentra registrado. Consultar con pasaporte."})
                    if not personaprofesor.usuario:
                        username = calculate_username(personaprofesor)
                        generar_usuario(personaprofesor, username, PROFESORES_GROUP_ID)
                        if EMAIL_INSTITUCIONAL_AUTOMATICO:
                            personaprofesor.emailinst = username + '@' + EMAIL_DOMAIN
                        else:
                            personaprofesor.emailinst = f.cleaned_data['emailinst']

                        correo = personaprofesor.lista_emails()
                        send_html_mail("Creación de cuenta institucional", "emails/nuevacuentacorreo.html",
                                       {'sistema': request.session['nombresistema'], 'persona': personaprofesor,
                                        'empleado': True,
                                        't': miinstitucion(), 'tipo_usuario': 'DOCENTE',
                                        'usuario': personaprofesor.usuario.username,
                                        'anio': str(personaprofesor.nacimiento)[0:4], 'tiposistema_': 2}, correo, [],
                                       cuenta=CUENTAS_CORREOS[4][1])

                    personaprofesor.save(request)
                    personaprofesor.datos_extension()
                    profesor = Profesor(persona=personaprofesor,
                                        activo=True,
                                        fechaingreso=f.cleaned_data['fechaingreso'],
                                        dedicacion=f.cleaned_data['dedicacion'],
                                        categoria=f.cleaned_data['categoria'],
                                        cargo=f.cleaned_data['cargo'],
                                        nivelescalafon=f.cleaned_data['nivelescalafon'],
                                        nivelcategoria=f.cleaned_data['nivelcategoria'],
                                        coordinacion=f.cleaned_data['coordinacion'],
                                        contrato=f.cleaned_data['contrato'])
                    profesor.save(request)
                    if f.cleaned_data['asignatura']:
                       for a in f.cleaned_data['asignatura']:
                           profesor.asignatura.add(a)
                    profesor.save(request)
                    personaprofesor.crear_perfil(profesor=profesor)
                    personaprofesor.mi_ficha()
                    personaprofesor.mi_perfil()
                    personaprofesor.datos_extension()
                    lista = ['gestionacademica@unemi.edu.ec', 'planificacionacademica@unemi.edu.ec']
                    send_html_mail("Nuevo Docente Creado", "emails/nuevacuentacorreo.html", {'sistema': request.session['nombresistema'], 'persona': personaprofesor, 't': miinstitucion(), 'tipo_usuario': 'DOCENTE'}, lista, [], cuenta=CUENTAS_CORREOS[4][1])
                    personaprofesor.creacion_persona(request.session['nombresistema'],persona)
                    log(u'Adiciono profesor: %s' % profesor, request, "add")
                    return JsonResponse({"result": "ok", "id": profesor.id})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % ex.__str__()})

        elif action == 'edit':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])

                fecha_str = request.POST['fechaingreso']
                fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
                fecha_nueva_str = fecha_obj.strftime('%d-%m-%Y')

                fecha_str_naci = request.POST['nacimiento']
                fecha_obj_naci = datetime.strptime(fecha_str_naci, '%Y-%m-%d')
                fecha_nueva_str_naci = fecha_obj_naci.strftime('%d-%m-%Y')

                data = request.POST.copy()
                data['fechaingreso'] = fecha_nueva_str
                data['nacimiento'] = fecha_nueva_str_naci


                f = ProfesorForm(data)
                persona = profesor.persona
                if f.is_valid():
                    persona.nombres = f.cleaned_data['nombres']
                    persona.apellido1 = f.cleaned_data['apellido1']
                    persona.apellido2 = f.cleaned_data['apellido2']
                    persona.nacimiento = f.cleaned_data['nacimiento']
                    persona.sexo = f.cleaned_data['sexo']
                    persona.paisnacimiento = f.cleaned_data['paisnacimiento']
                    persona.provincianacimiento = f.cleaned_data['provincianacimiento']
                    persona.cantonnacimiento = f.cleaned_data['cantonnacimiento']
                    persona.parroquianacimiento = f.cleaned_data['parroquianacimiento']
                    persona.nacionalidad = f.cleaned_data['nacionalidad']
                    persona.pais = f.cleaned_data['pais']
                    persona.provincia = f.cleaned_data['provincia']
                    persona.canton = f.cleaned_data['canton']
                    persona.parroquia = f.cleaned_data['parroquia']
                    persona.sector = f.cleaned_data['sector']
                    persona.direccion = f.cleaned_data['direccion']
                    persona.direccion2 = f.cleaned_data['direccion2']
                    persona.num_direccion = f.cleaned_data['num_direccion']
                    persona.telefono = f.cleaned_data['telefono']
                    persona.telefono_conv = f.cleaned_data['telefono_conv']
                    persona.email = f.cleaned_data['email']
                    persona.emailinst = f.cleaned_data['emailinst']
                    persona.save(request)
                    profesor.fechaingreso = f.cleaned_data['fechaingreso']
                    profesor.dedicacion = f.cleaned_data['dedicacion']
                    profesor.categoria = f.cleaned_data['categoria']
                    profesor.cargo = f.cleaned_data['cargo']
                    profesor.nivelescalafon = f.cleaned_data['nivelescalafon']
                    profesor.nivelcategoria = f.cleaned_data['nivelcategoria']
                    profesor.contrato = f.cleaned_data['contrato']
                    profesor.coordinacion = f.cleaned_data['coordinacion']
                    profesor.tienetoken = f.cleaned_data['tienetoken']
                    profesor.save(request)
                    profesor.asignatura.clear()
                    for r in f.cleaned_data['asignatura']:
                        profesor.asignatura.add(r)
                    log(u'Editó datos de profesor: %s' % profesor, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})



        elif action == 'addzoomurlmodal':
            try:
                profesor = Profesor.objects.get(pk=int(encrypt(request.POST['id'])))
                f = ProfesorZoomUrlForm(request.POST)
                if f.is_valid():
                    profesor.urlzoom = f.cleaned_data['urlzoom']
                    profesor.urlzoomdos = f.cleaned_data['urlzoomdos']
                    profesor.save(request)
                    for materia in Materia.objects.filter(profesormateria__profesor=profesor, profesormateria__activo=True, nivel__periodo=request.session['periodo']):
                        materia.actualizarhtml = True
                        materia.save()
                    log(u'Editó zoomurl de profesor: %s' % profesor, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'diasacalificar':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                form = CalificacionDiaForm(request.POST)
                if form.is_valid():
                    materia.usaperiodocalificaciones = form.cleaned_data['usaperiodocalificaciones']
                    materia.diasactivacioncalificaciones = form.cleaned_data['diasactivacioncalificaciones'] if not form.cleaned_data['usaperiodocalificaciones'] else 1
                    materia.save(request)
                    log(u'Cambio en fecha de calificaciones de materia: %s' % materia, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        elif action == 'actualizaciondatosmodal':
            try:
                profesor = Profesor.objects.get(pk=int(encrypt(request.POST['id'])))
                persona = profesor.persona
                form = ActualizacionDatosForm(request.POST)
                if form.is_valid():
                    if Persona.objects.filter(cedula__icontains=form.cleaned_data['cedula']).exists():
                        return JsonResponse({"result": True, "mensaje": u"El numero de cedula ya se encuentra registrado."})
                    persona.cedula = form.cleaned_data['cedula']
                    persona.save(request)
                    return JsonResponse({"result": False, "message": "registro exitoso"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'resetear':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                # user = profesor.persona.usuario
                # if CLAVE_USUARIO_CEDULA:
                #     if profesor.persona.cedula:
                #         password = profesor.persona.cedula.strip()
                #     elif profesor.persona.pasaporte:
                #         password = profesor.persona.pasaporte.strip()
                #     else:
                #         profesor.password = profesor.persona.ruc.strip()
                #     user.set_password(password)
                # else:
                #     user.set_password(DEFAULT_PASSWORD)
                # user.save()
                # profesor.persona.cambiar_clave()
                if not profesor.persona.emailinst:
                    return JsonResponse({"result": "bad", "mensaje": u"No tiene correo institucional."})
                resetear_clave(profesor.persona)
                log(f'Reseteó la clave del usuario {profesor.persona.usuario}', request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'activar':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                ui = profesor.persona.usuario
                ui.is_active = True
                ui.save()
                log(u'Activar profesor: %s' % ui, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'desactivar':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                ui = profesor.persona.usuario
                ui.is_active = False
                ui.save()
                log(u'Desactivar profesor: %s' % ui, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})



        elif action == 'addgrupomodal':
            try:
                profesor = Profesor.objects.get(pk=int(encrypt(request.POST['id'])))
                form = GrupoUsuarioForm(request.POST)
                if form.is_valid():
                    grupo = form.cleaned_data['grupo']
                    grupo.user_set.add(profesor.persona.usuario)
                    grupo.save()
                    log(u'Adiciono grupo de usuario al profesor: %s' % grupo, request, "add")
                    return JsonResponse({"result": False})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'pdf_horarios':
            data = {}
            data['periodo'] = periodo = request.session['periodo']
            if not request.user.has_perm('sga.puede_visible_periodo'):
                if not request.session['periodo'].visible:
                    return HttpResponseRedirect("/?info=No tiene permiso para imprimir en el periodo seleccionado.")
            data['profesor'] = profesor = Profesor.objects.filter().distinct().get(pk=request.POST['profesor'])
            data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'],
                              [6, 'Sabado'], [7, 'Domingo']]
            turnoclases = Turno.objects.filter(status=True, mostrar=True, clase__activo=True, clase__materia__nivel__periodo=periodo,
                                               clase__materia__profesormateria__profesor=profesor,
                                               clase__materia__profesormateria__principal=True).distinct().order_by(
                'comienza')
            turnoactividades = Turno.objects.filter(status=True, mostrar=True,
                claseactividad__detalledistributivo__distributivo__periodo=periodo,
                claseactividad__detalledistributivo__distributivo__profesor=profesor).distinct().order_by(
                'comienza')
            data['turnos'] = turnoclases | turnoactividades
            data['puede_ver_horario'] = request.user.has_perm('sga.puede_visible_periodo') or (periodo.visible == True and periodo.visiblehorario == True)
            data['aprobado'] = profesor.claseactividadestado_set.filter(status=True, periodo=periodo, estadosolicitud=2).exists()
            return conviert_html_to_pdf(
                'docentes/horario_pfd.html',
                {
                    'pagesize': 'A4',
                    'data': data,
                }
            )

        elif action == 'addadministrativo':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                if profesor.persona.administrativo_set.exists():
                    return JsonResponse({"result": "bad", "mensaje": u"El usuario ya tiene un perfil como administrativo."})
                administrativo = Administrativo(persona=profesor.persona,
                                                fechaingreso=datetime.now().date(),
                                                activo=True)
                administrativo.save(request)
                grupo = Group.objects.get(pk=variable_valor('ADMINISTRATIVOS_GROUP_ID'))
                grupo.user_set.add(profesor.persona.usuario)
                grupo.save()
                profesor.persona.crear_perfil(administrativo=administrativo)
                log(u'Adiciono administrativo: %s' % administrativo, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'desactivarperfil':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                profesor.activo = False
                profesor.save(request)
                log(u'Desactivo perfil de usuario: %s' % profesor, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'activarperfil':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                profesor.activo = True
                profesor.save(request)
                log(u'Activo perfil de usuario: %s' % profesor, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'rangocategoria':
            try:
                profesor = Profesor.objects.get(pk=request.POST['p'])
                if profesor.persona.titulacion_set.filter(principal=True):
                    titulacion = profesor.persona.titulacion_set.filter(principal=True)[0]
                    rango = ProfesorTipo.objects.filter(dedicacion__id=request.POST['id'], nivel=titulacion.titulo.nivel)
                    if rango.values('id').count() > 0:
                        rangos = []
                        for r in rango:
                            rangos.append({"id": r.id, "valor": unicode(r)})
                        return JsonResponse({"result": "ok", "data": rangos})
                return JsonResponse({"result": "bad"})
            except Exception as ex:
                return JsonResponse({"result": "bad"})

        elif action == 'nivelcategoria':
            try:
                rango = CategorizacionDocente.objects.filter(profesortipo=request.POST['id'])
                if rango.values('id').count() > 0:
                    rangos = []
                    for r in rango:
                        rangos.append({"id": r.id, "valor": unicode(r)})
                    return JsonResponse({"result": "ok", "data": rangos})
                return JsonResponse({"result": "bad"})
            except Exception as ex:
                return JsonResponse({"result": "bad"})

        elif action == 'actualizar_estudiantes_moodle':
            try:
                materia = Materia.objects.get(pk=request.POST['id'], status=True)
                tipourl=1
                if materia.coordinacion().id == 9:
                    tipourl=2
                else:
                    tipourl=1
                materia.crear_actualizar_estudiantes_curso(moodle, tipourl)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar."})

        elif action == 'actualizar_docentes_moodle':
            try:
                materia = Materia.objects.get(pk=request.POST['id'], status=True)
                tipourl = 1
                if materia.coordinacion().id == 9:
                    tipourl=2
                    materia.crear_actualizar_docente_curso_admision(moodle, tipourl)
                else:
                    tipourl=1
                    materia.crear_actualizar_docente_curso(moodle, tipourl)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos."})

        elif action == 'actualizar_silabos_moodle':
            try:
                materia = Materia.objects.get(pk=request.POST['id'], status=True)
                #materia.crear_actualizar_silabo_curso()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos."})

        elif action == 'deletetipoprofesor':
            try:
                tipoprofesor = TipoProfesor.objects.get(pk=request.POST['id'])
                log(u'Elimino : %s' % tipoprofesor.id, request, "del")
                tipoprofesor.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})



        elif action == 'addtipoprofesormod':
            try:
                f = TipoProfesorForm(request.POST)
                if f.is_valid():
                    tipoprofesor = TipoProfesor(nombre=f.cleaned_data['nombre'],tipoevaluar=f.cleaned_data['tipoevaluar'] )
                    tipoprofesor.save(request)
                    log(u'Adiciono : %s' % tipoprofesor, request, "addtipoprofesor")
                    return JsonResponse({"result": False, "message": "Registro Exitoso"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})




        elif action == 'editarTipoProfesorMod':
            try:
                tipoprofesor = TipoProfesor.objects.get(pk=int(encrypt(request.POST['id'])))
                f = TipoProfesorForm(request.POST)
                if f.is_valid():
                    tipoprofesor.nombre = f.cleaned_data['nombre']
                    tipoprofesor.tipoevaluar = f.cleaned_data['tipoevaluar']
                    tipoprofesor.save(request)
                    log(u'Modifico tipo profesor: %s' % tipoprofesor, request, "editar")
                    return JsonResponse({"result": False, "message": "Registro exitoso"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'grupodocentes':
            try:
                asignaturamallapreferencia = AsignaturaMallaPreferencia.objects.get(pk=request.POST['idp'])
                data['grupodocentes'] = AsignaturaMallaPreferencia.objects.filter(periodo=asignaturamallapreferencia.periodo, asignaturamalla=asignaturamallapreferencia.asignaturamalla, status=True).exclude(profesor=asignaturamallapreferencia.profesor).order_by('profesor__persona__apellido1')
                data['asignatura'] = asignaturamallapreferencia.asignaturamalla.asignatura
                data['title'] = u'Docentes'
                template = get_template("docentes/grupodocentes.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad"})

        elif action == 'afinidad_malla':
            try:
                # if 'idp' in request.POST:
                #     asignaturamallapreferencia = AsignaturaMallaPreferencia.objects.get(pk=request.POST['idp'])
                #     data['materia'] = asignaturamallapreferencia.asignaturamalla
                # else:
                #     asignaturamalla = AsignaturaMalla.objects.get(pk=request.POST['iditem'])
                #     data['materia'] = asignaturamalla
                #     data['listasesion'] = Materia.objects.values_list('nivel__sesion__id', 'nivel__sesion__nombre').filter(asignaturamalla=asignaturamalla, nivel__periodo=asignaturamallapreferencia.periodo, status=True).distinct()
                # data['titulacion'] = Titulacion.objects.filter(persona=asignaturamallapreferencia.profesor.persona, status=True, titulo__nivel__id=4).exclude(titulo__grado__id=3).order_by('titulo__grado__id')
                # data['title'] = u'Detalle Título'
                # template = get_template("docentes/afinidad.html")
                # json_content = template.render(data)
                # return JsonResponse({"result": "ok", 'data': json_content})
                return JsonResponse({"result": "ok", 'data': ''})
            except Exception as ex:
                return JsonResponse({"result": "bad"})

        elif action == 'afinidad_publicaciones':
            try:
                asignaturamallapreferencia = AsignaturaMallaPreferencia.objects.get(pk=request.POST['idp'])
                data['materia'] = asignaturamallapreferencia.asignaturamalla
                data['titulacion'] = ArticuloInvestigacion.objects.select_related().filter(participantesarticulos__profesor=asignaturamallapreferencia.profesor, status=True, participantesarticulos__status=True).order_by('-fechapublicacion')
                data['title'] = u'Detalle de Publicaciones de investifación'
                template = get_template("docentes/afinidadpublicaciones.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad"})

        elif action == 'editpresentacion':
            try:
                with transaction.atomic():
                    filtro = DiapositivaSilaboSemanal.objects.get(pk=request.POST['id'])
                    estadoant = filtro.estado
                    idmoodleant = filtro.iddiapositivamoodle
                    f = PresentacionDiapositivaEditForm(request.POST)
                    if f.is_valid():
                        filtro.estado = f.cleaned_data['estado']
                        filtro.iddiapositivamoodle = f.cleaned_data['iddiapositivamoodle']
                        filtro.save(request)
                        estadoact = filtro.estado
                        idmoodleact = filtro.iddiapositivamoodle
                        messages.success(request, 'Modificó Presentación Silabo')
                        log('Modificó Presentación Silabos ID: {} - Estado [{} - {}], IdMoodle [{} - {}]'.format(filtro.pk, estadoant, estadoact, idmoodleant, idmoodleact), request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editcompendio':
            try:
                with transaction.atomic():
                    filtro = CompendioSilaboSemanal.objects.get(pk=request.POST['id'])
                    estadoant = filtro.estado
                    idmoodleant = filtro.idmcompendiomoodle
                    f = CompendioSilaboSemanalEditForm(request.POST)
                    if f.is_valid():
                        filtro.estado = f.cleaned_data['estado']
                        filtro.idmcompendiomoodle = f.cleaned_data['idmcompendiomoodle']
                        filtro.save(request)
                        estadoact = filtro.estado
                        idmoodleact = filtro.idmcompendiomoodle
                        messages.success(request, 'Modificó Compendio Silabo')
                        # log(u'Modificó Compendio Silabos: %s' % filtro, request, "edit")
                        log('Modificó Compendio Silabos ID: {} - Estado [{} - {}], IdMoodle [{} - {}]'.format(filtro.pk, estadoant, estadoact, idmoodleant, idmoodleact), request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editvideo':
            try:
                with transaction.atomic():
                    filtro = VideoMagistralSilaboSemanal.objects.get(pk=request.POST['id'])
                    estadoant = filtro.estado
                    idmoodleant = filtro.idvidmagistralmoodle
                    f = VideoMagistralSilaboSemanalEditForm(request.POST)
                    if f.is_valid():
                        filtro.estado = f.cleaned_data['estado']
                        filtro.idvidmagistralmoodle = f.cleaned_data['idvidmagistralmoodle']
                        filtro.save(request)
                        estadoact = filtro.estado
                        idmoodleact = filtro.idvidmagistralmoodle
                        messages.success(request, 'Modificó Video Magistral Silabo')
                        # log(u'Modificó Video Magistral Silabos: %s' % filtro, request, "edit")
                        log('Modificó Video Magistral Silabos ID: {} - Estado [{} - {}], IdMoodle [{} - {}]'.format(filtro.pk, estadoant, estadoact, idmoodleant, idmoodleact), request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editguia':
            try:
                with transaction.atomic():
                    filtro = GuiaEstudianteSilaboSemanal.objects.get(pk=request.POST['id'])
                    estadoant = filtro.estado
                    idmoodleant = filtro.idguiaestudiantemoodle
                    f = GuiaEstudianteSilaboSemanalEditForm(request.POST)
                    if f.is_valid():
                        filtro.estado = f.cleaned_data['estado']
                        filtro.idguiaestudiantemoodle = f.cleaned_data['idguiaestudiantemoodle']
                        filtro.save(request)
                        estadoact = filtro.estado
                        idmoodleact = filtro.idguiaestudiantemoodle
                        messages.success(request, 'Modificó Guía Estudiante Silabo')
                        # log(u'Modificó Guía Estudiante Silabos: %s' % filtro, request, "edit")
                        log('Modificó Guía Estudiante Silabos ID: {} - Estado [{} - {}], IdMoodle [{} - {}]'.format(filtro.pk, estadoant, estadoact, idmoodleant, idmoodleact), request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editguiadocente':
            try:
                with transaction.atomic():
                    filtro = GuiaDocenteSilaboSemanal.objects.get(pk=request.POST['id'])
                    estadoant = filtro.estado
                    idmoodleant = filtro.idguiadocentemoodle
                    f = GuiaDocenteSilaboSemanalEditForm(request.POST)
                    if f.is_valid():
                        filtro.estado = f.cleaned_data['estado']
                        filtro.idguiadocentemoodle = f.cleaned_data['idguiadocentemoodle']
                        filtro.save(request)
                        estadoact = filtro.estado
                        idmoodleact = filtro.idguiadocentemoodle
                        messages.success(request, 'Modificó Guía Docente Silabo')
                        # log(u'Modificó Guía Docente Silabos: %s' % filtro, request, "edit")
                        log('Modificó Guía Docente Silabos ID: {} - Estado [{} - {}], IdMoodle [{} - {}]'.format(filtro.pk, estadoant, estadoact, idmoodleant, idmoodleact), request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editmaterial':
            try:
                with transaction.atomic():
                    filtro = MaterialAdicionalSilaboSemanal.objects.get(pk=request.POST['id'])
                    estadoant = filtro.estado
                    idmoodleant = filtro.idmaterialesmoodle
                    f = MaterialAdicionalSilaboSemanalEditForm(request.POST)
                    if f.is_valid():
                        filtro.estado = f.cleaned_data['estado']
                        filtro.idmaterialesmoodle = f.cleaned_data['idmaterialesmoodle']
                        filtro.save(request)
                        estadoact = filtro.estado
                        idmoodleact = filtro.idmaterialesmoodle
                        messages.success(request, 'Modificó Materiales Complementarios Silabo')
                        # log(u'Modificó Materiales Complementarios Silabos: %s' % filtro, request, "edit")
                        log('Modificó Materiales Complementarios Silabos ID: {} - Estado [{} - {}], IdMoodle [{} - {}]'.format(filtro.pk, estadoant, estadoact, idmoodleant, idmoodleact), request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'edittareasemanal':
            try:
                with transaction.atomic():
                    filtro = TareaSilaboSemanal.objects.get(pk=request.POST['id'])
                    estadoant = filtro.estado
                    idmoodleant = filtro.idtareamoodle
                    f = TareaSilaboSemanalEditForm(request.POST)
                    if f.is_valid():
                        filtro.estado = f.cleaned_data['estado']
                        filtro.idtareamoodle = f.cleaned_data['idtareamoodle']
                        filtro.save(request)
                        estadoact = filtro.estado
                        idmoodleact = filtro.idtareamoodle
                        messages.success(request, 'Modificó Tarea Silabo')
                        # log(u'Modificó Tarea Silabos: %s' % filtro, request, "edit")
                        log('Modificó Tarea Silabos ID: {} - Estado [{} - {}], IdMoodle [{} - {}]'.format(filtro.pk, estadoant, estadoact, idmoodleant, idmoodleact), request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editforos':
            try:
                with transaction.atomic():
                    filtro = ForoSilaboSemanal.objects.get(pk=request.POST['id'])
                    estadoant = filtro.estado
                    idmoodleant = filtro.idforomoodle
                    f = ForoSilaboSemanalEditForm(request.POST)
                    if f.is_valid():
                        filtro.estado = f.cleaned_data['estado']
                        filtro.idforomoodle = f.cleaned_data['idforomoodle']
                        filtro.save(request)
                        estadoact = filtro.estado
                        idmoodleact = filtro.idforomoodle
                        # log(u'Modificó Foro Silabos: %s' % filtro, request, "edit")
                        log('Modificó Foro Silabos ID: {} - Estado [{} - {}], IdMoodle [{} - {}]'.format(filtro.pk, estadoant, estadoact, idmoodleant, idmoodleact), request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'edittest':
            try:
                with transaction.atomic():
                    filtro = TestSilaboSemanal.objects.get(pk=request.POST['id'])
                    estadoant = filtro.estado
                    idmoodleant = filtro.idtestmoodle
                    f = TestSilaboSemanalEditForm(request.POST)
                    if f.is_valid():
                        filtro.estado = f.cleaned_data['estado']
                        filtro.idtestmoodle = f.cleaned_data['idtestmoodle']
                        filtro.save(request)
                        estadoact = filtro.estado
                        idmoodleact = filtro.idtestmoodle
                        messages.success(request, 'Modificó Test Silabo')
                        # log(u'Modificó Test Silabos: %s' % filtro, request, "edit")
                        log('Modificó Test Silabos ID: {} - Estado [{} - {}], IdMoodle [{} - {}]'.format(filtro.pk, estadoant, estadoact, idmoodleant, idmoodleact), request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'edittestnivelacion':
            try:
                with transaction.atomic():
                    filtro = TestSilaboSemanalAdmision.objects.get(pk=request.POST['id'])
                    estadoant = filtro.estado
                    idmoodleant = filtro.idtestmoodle
                    urlant = filtro.url1
                    f = TestSilaboSemanalAdmisionEditForm(request.POST)
                    if f.is_valid():
                        filtro.estado = f.cleaned_data['estado']
                        filtro.idtestmoodle = f.cleaned_data['idtestmoodle']
                        filtro.url1 = f.cleaned_data['url']
                        filtro.save(request)
                        estadoact = filtro.estado
                        idmoodleact = filtro.idtestmoodle
                        urlact = filtro.url1
                        materia = filtro.silabosemanal.silabo.materia
                        materia.actualizarhtml = True
                        materia.save(request)
                        messages.success(request, 'Modificó Test Silabo')
                        log('Modificó Test nivelacion Silabos ID: {} - Estado [{} - {}], IdMoodle [{} - {}]'.format(filtro.pk, estadoant, estadoact, idmoodleant, idmoodleact, urlant, urlact), request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'edittrabajopractico':
            try:
                with transaction.atomic():
                    filtro = TareaPracticaSilaboSemanal.objects.get(pk=request.POST['id'])
                    estadoant = filtro.estado
                    idmoodleant = filtro.idtareapracticamoodle
                    f = TareaPracticaSilaboSemanalEditForm(request.POST)
                    if f.is_valid():
                        filtro.estado = f.cleaned_data['estado']
                        filtro.idtareapracticamoodle = f.cleaned_data['idtareapracticamoodle']
                        filtro.save(request)
                        estadoact = filtro.estado
                        idmoodleact = filtro.idtareapracticamoodle
                        # log(u'Modificó Trabajo Practico Silabos: %s' % filtro, request, "edit")
                        log('Modificó Trabajo Practico Silabos ID: {} - Estado [{} - {}], IdMoodle [{} - {}]'.format(filtro.pk, estadoant, estadoact, idmoodleant, idmoodleact), request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'auditoria':
            try:
                baseDate = datetime.today()
                year = request.POST['year'] if 'year' in request.POST and request.POST['year'] else baseDate.year
                month = request.POST['month'] if 'month' in request.POST and request.POST['month'] else baseDate.month
                data['idi'] = request.POST['id']
                data['docente'] = docente_seleccionado = Profesor.objects.get(pk=int(encrypt(request.POST['id'])))
                logs = LogEntry.objects.filter(Q(change_message__icontains=docente_seleccionado.persona.__str__()) | Q(user=docente_seleccionado.persona.usuario), action_time__year=year).exclude(user__is_superuser=True)
                logs1 = LogEntryBackup.objects.filter(Q(change_message__icontains=docente_seleccionado.persona.__str__()) | Q(user=docente_seleccionado.persona.usuario), action_time__year=year).exclude(user__is_superuser=True)
                logs2 = LogEntryBackupdos.objects.filter(Q(change_message__icontains=docente_seleccionado.persona.__str__()) | Q(user=docente_seleccionado.persona.usuario), action_time__year=year).exclude(user__is_superuser=True)
                logs3 = LogEntryLogin.objects.filter(user=docente_seleccionado.persona.usuario, action_time__year=year).exclude(user__is_superuser=True, action_app=2)
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
                template = get_template('docentes/auditoria.html')
                json_contenido = template.render(data)
                return JsonResponse({"result": "ok", "contenido":json_contenido })
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        elif action == 'descargarauditoria':
            try:
                docente = Profesor.objects.get(pk=int(encrypt(request.POST['id'])))
                titulo = 'Generando reporte de auditoria'
                noti = Notificacion(cuerpo='Reporte de auditoria en progreso',
                                    titulo=titulo, destinatario=persona,
                                    url='',
                                    prioridad=1, app_label='sga-sagest',
                                    fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                    en_proceso=True)
                noti.save(request)
                data['persona'] = docente.persona
                reporte_auditoria_background(request=request, data=data, notif=noti.pk).start()
                return JsonResponse({'result':False, 'mensaje':titulo})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result':True, 'mensaje':f'Error: {ex}'})

        elif action == 'updatefechainicio':
            try:
                silabosemanal = SilaboSemanal.objects.get(pk=request.POST['idsilabosemanal'])
                if int(request.POST['tipo']) == 1:
                    fechainicio = convertir_fecha(request.POST['fecha'])
                    silabosemanal.fechainiciosemana = fechainicio
                    silabosemanal.semana = fechainicio.isocalendar()[1]
                if int(request.POST['tipo']) == 2:
                    fechainicio = convertir_fecha(request.POST['fecha'])
                    silabosemanal.fechafinciosemana = fechainicio

                silabosemanal.save(request)
                return JsonResponse({'result': 'ok', 'fecha': silabosemanal.fechainiciosemana.strftime("%d-%m-%Y")})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad'})

        elif action == 'viewAsistencia':
            try:
                if not 'ida' in request.POST:
                    raise NameError(u"Parametro de asistencia no encontrado")
                if not AsistenciaLeccion.objects.values("id").filter(pk=int(request.POST['ida'])).exists():
                    raise NameError(u"Asistencia no encontrada")
                asistencia = AsistenciaLeccion.objects.get(pk=int(request.POST['ida']))
                data['asistencia'] = asistencia

                data['solicitud_justificacion'] = None
                data['justificacion_manual'] = None


                palabra_buscar=u'Asistencia en clase: %s - %s - %s,' % (
                asistencia.materiaasignada.materia.asignatura.nombre,
                asistencia.materiaasignada.matricula.inscripcion.persona.nombre_completo_inverso(),
                asistencia.leccion.fecha.strftime("%Y-%m-%d"))

                data['logs'] = LogEntry.objects.filter(change_message__contains=palabra_buscar, action_time__date=asistencia.leccion.fecha).order_by('action_time')
                justificaciones = asistencia.detallemateriajustificacionasistencia_set.filter(status=True)
                if justificaciones.exists():
                    data['solicitud_justificacion'] = justificaciones.first().materiajustificacion.solicitudjustificacion
                justificacion = asistencia.justificacionausenciaasistencialeccion_set.filter(status=True)
                if justificacion.exists():
                    data['justificacion_manual'] = justificacion

                matricula = asistencia.materiaasignada.matricula
                data['puede_modificar_asistencia'] = True if not periodo.tipo_id == 2 or matricula.carrera_es_admision() else False
                data['sga_puede_modificar_asistencia'] = request.user.has_perm('sga.puede_modificar_asistencia')
                data['puede_modificar_asistencia_por_perfilusuario'] = persona.mis_carreras().values('id').filter(pk=matricula.inscripcion.carrera.id).exists()
                data['is_superuser'] = request.user.is_superuser
                if matricula.inscripcion.coordinacion in persona.mis_coordinaciones() or request.user.is_superuser:
                    data['puede_justificar_asistencia'] = request.user.has_perm('sga.puede_justificar_asistencia')
                template = get_template("pro_asistencias/view_asistencia.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", "html": json_content, "fecha": asistencia.fecha_creacion.strftime("%d-%m-%Y")})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__()})

        elif action == 'verdetalleppl':
            try:
                matricula = Matricula.objects.get(pk=int(encrypt(request.POST['idmatricula'])))
                data['historialppl'] = HistorialPersonaPPL.objects.filter(persona=matricula.inscripcion.persona, status=True).order_by('fechaingreso')
                template = get_template("pro_planificacion/verdetalleppl.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", "html": json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__()})

        elif action == 'configurarregistroasistencia':
            try:
                form = ConfigurarRegistroAsistenciaForm(request.POST)
                profesormateria = ProfesorMateria.objects.get(pk=int(encrypt(request.POST['id'])))
                if not form.is_valid():
                    # [(k, v[0]) for k, v in f.errors.items()]
                    for k, v in form.errors.items():
                        raise NameError(f'{k}:{v[0]}')
                puede_registrar = form.cleaned_data['puedemodificarasistencia']
                fecha_fin = form.cleaned_data['modificarasistenciafin'] if puede_registrar else None
                profesormateria.puedemodificarasistencia = puede_registrar
                profesormateria.modificarasistenciafin = fecha_fin
                profesormateria.save(request)
                log(u'Configuro registro de Asistencisa: %s' % profesormateria, request, "edit")
                return JsonResponse({"result": True, "mensaje": u"Se configuro  correctamente la materia %s" % (profesormateria)}, safe=False)
            except Exception as ex:
                msg = str(ex)
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        if action == 'asistencia':
            try:
                asistencialeccion = AsistenciaLeccion.objects.get(pk=request.POST['id'])
                # if not request.user.is_superuser:
                #     if LIMITE_HORAS_JUSTIFICAR:
                #         horas_extras = CANTIDAD_HORAS_JUSTIFICACION_ASISTENCIAS
                #         if asistencialeccion.leccion.leccion_grupo().dia in [5, 6, 7] and CANTIDAD_HORAS_JUSTIFICACION_ASISTENCIAS < 72:
                #             horas_extras += 48
                #         # if asistencialeccion.leccion.fecha < datetime.now().date() - timedelta(hours=horas_extras):
                #         #     return JsonResponse({"result": "bad", "mensaje": u"Las faltas menores a " + str(horas_extras) + " horas no pueden ser justificadas."}), content_type="application/json")
                #     if request.POST['todas'] == 'true':
                #         for asistencia in AsistenciaLeccion.objects.filter(materiaasignada__matricula=asistencialeccion.materiaasignada.matricula, leccion__fecha=asistencialeccion.leccion.fecha):
                #             justificar_asistencia(request, asistencia)
                #     else:
                #         # for asistencia in AsistenciaLeccion.objects.filter(materiaasignada=asistencialeccion.materiaasignada,materiaasignada__matricula=asistencialeccion.materiaasignada.matricula, leccion__fecha=asistencialeccion.leccion.fecha):
                #         result = justificar_asistencia(request)
                #         result['materiaasignada'] = None
                #         return JsonResponse(result)
                #     return JsonResponse({"result": "ok"})
                # else:
                todas_asistencias = AsistenciaLeccion.objects.filter(
                    materiaasignada__matricula=asistencialeccion.materiaasignada.matricula,
                    leccion__fecha=asistencialeccion.leccion.fecha,
                    asistio=False
                )#.exclude(id=asistencialeccion.id)
                datajson = []
                if request.POST['todas'] == 'true':
                    for asistencia in todas_asistencias:
                        result = justificar_asistencia(request, asistencia)
                        result['materiaasignada'] = result['materiaasignada'].id
                        datajson.append(result)
                else:
                    result = justificar_asistencia(request, asistencialeccion)
                    result['materiaasignada'] = result['materiaasignada'].id
                    datajson.append(result)
                return JsonResponse({"result": "ok", "asistenciasactulizadas":datajson})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos: "+str(ex)})

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
                        ruta = os.path.join(SITE_STORAGE, 'media', 'reportes', 'encabezados_pies', 'firmas', '')
                        rutapdf = ruta + u"%s_%s.png" % (firmapersona.persona.cedula, firmapersona.tipofirma)
                        if os.path.isfile(rutapdf):
                            os.remove(rutapdf)

                        archivofirma = request.FILES['firma']
                        archivofirma._name = u"%s_%s.png" % (firmapersona.persona.cedula, firmapersona.tipofirma)
                        firmapersona.firma = archivofirma
                        firmapersona.save(request)

                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'adicionarpersonafirmamodal':
            try:
                form = FirmaPersonaForm(request.POST, request.FILES)
                if 'firma' in request.FILES:
                    arch = request.FILES['firma']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 6291456:
                        return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 6 Mb."})
                    if not exte.lower() == 'png':
                        return JsonResponse({"result": True, "mensaje": u"Solo se permiten archivos .png"})
                if form.is_valid():
                    firmapersona = FirmaPersona(persona_id=int(encrypt(request.POST['id'])),
                                                tipofirma=form.cleaned_data['tipofirma']
                                                )
                    firmapersona.save(request)
                    if 'firma' in request.FILES:
                        ruta = os.path.join(SITE_STORAGE, 'media', 'reportes', 'encabezados_pies', 'firmas', '')
                        rutapdf = ruta + u"%s_%s.png" % (firmapersona.persona.cedula, firmapersona.tipofirma)
                        if os.path.isfile(rutapdf):
                            os.remove(rutapdf)

                        archivofirma = request.FILES['firma']
                        archivofirma._name = u"%s_%s.png" % (firmapersona.persona.cedula, firmapersona.tipofirma)
                        firmapersona.firma = archivofirma
                        firmapersona.save(request)

                    return JsonResponse({"result": False})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})


        elif action == 'deletefirmamodal':
            try:
                firma = FirmaPersona.objects.get(pk=request.POST['id'])
                log(u'Elimino : %s' % FirmaPersona.id, request, "del")
                firma.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'detalleaprobacion':
            try:
                data['silabo'] = silabo = Silabo.objects.get(pk=int(request.POST['id']))
                data['historialaprobacion'] = silabo.aprobarsilabo_set.filter(status=True).order_by('-id').exclude(estadoaprobacion=variable_valor('PENDIENTE_SILABO'))
                data['aprobar'] = variable_valor('APROBAR_SILABO')
                data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                template = get_template("pro_planificacion/detalleaprobacion.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'delsilabo':
            try:
                silabo = Silabo.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Eliminó cabecera de Sílabo: %s-%s la persona: %s' % (silabo.materia, silabo.fecha_creacion, persona), request, "del")
                silabo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'DeleteclassAsynchronous':
            with transaction.atomic():
                try:
                    puede_realizar_accion(request, 'sga.puede_eliminar_link_clase_sincronica_asincronica_administrativo')
                    if not 'id' in request.POST:
                        raise NameError(u"Parametro de asincrónica no encontrado")
                    clase = ClaseAsincronica.objects.get(pk=int(encrypt(request.POST['id'])))
                    clase.status = False
                    clase.save(request)
                    log(u'Elimino clase asincrónica: %s' % clase, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el dato. %s" % ex.__str__()})

        elif action == 'DeleteclassSynchronous':
            with transaction.atomic():
                try:
                    puede_realizar_accion(request, 'sga.puede_eliminar_link_clase_sincronica_asincronica_administrativo')
                    if not 'id' in request.POST:
                        raise NameError(u"Parametro de clase sincrónica no encontrado")
                    clase = ClaseSincronica.objects.get(pk=int(encrypt(request.POST['id'])))
                    clase.status = False
                    clase.save(request)
                    log(u'Elimino clase sincrónica: %s' % clase, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el dato. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Listado de profesores'
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'resetear':
                try:
                    puede_realizar_accion(request, 'sga.puede_resetear_clave_docente')
                    data['title'] = u'Resetear clave del usuario'
                    profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['profesor'] = profesor
                    return render(request, "docentes/resetear.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletefirmamodal':
                try:
                    data['title'] = u'Eliminar Firma'
                    data['firmaPersona']= firmaPersona  = FirmaPersona.objects.get(pk=request.GET['idfirma'])
                    data['persona_id']= firmaPersona.persona_id
                    return render(request, "docentes/modal/delfirmapersonamodal.html", data)
                except Exception as ex:
                    pass

            elif action == 'desactivar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_profesores')
                    profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['profesor'] = profesor
                    return render(request, "docentes/desactivar.html", data)
                except Exception as ex:
                    pass

            elif action == 'activar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_profesores')
                    profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['profesor'] = profesor
                    return render(request, "docentes/activar.html", data)
                except Exception as ex:
                    pass


            elif action == 'addgrupomodal':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_profesores')
                    data['id'] = request.GET['id']
                    profesor = Profesor.objects.get(pk=request.GET['id'])
                    gruposexcluidos = [PROFESORES_GROUP_ID, ALUMNOS_GROUP_ID, EMPLEADORES_GRUPO_ID, SISTEMAS_GROUP_ID]
                    grupos = Group.objects.all().exclude(id__in=gruposexcluidos)
                    form = GrupoUsuarioForm()
                    form.grupos(grupos)
                    data['form'] = form
                    data['profesor'] = profesor
                    template = get_template('docentes/modal/formModalAccionesDocentes.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'add':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_profesores')
                    data['title'] = u'Adicionar profesor'
                    form = ProfesorForm(initial={'nacimiento': datetime.now().date(),
                                                 'fechaingreso': datetime.now().date()})
                    # form.sin_nivelcategoria()
                    form.adicionar()
                    data['form'] = form
                    data['email_domain'] = EMAIL_DOMAIN
                    return render(request, "docentes/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_profesores')
                    data['title'] = u'Editar profesor'
                    profesor = Profesor.objects.get(pk=request.GET['id'])
                    form = ProfesorForm(initial={'nombres': profesor.persona.nombres,
                                                 'apellido1': profesor.persona.apellido1,
                                                 'apellido2': profesor.persona.apellido2,
                                                 'cedula': profesor.persona.cedula,
                                                 'pasaporte': profesor.persona.pasaporte,
                                                 'paisnacimiento': profesor.persona.paisnacimiento,
                                                 'provincianacimiento': profesor.persona.provincianacimiento,
                                                 'cantonnacimiento': profesor.persona.cantonnacimiento,
                                                 'parroquianacimiento': profesor.persona.parroquianacimiento,
                                                 'nacimiento': profesor.persona.nacimiento,
                                                 'nacionalidad': profesor.persona.nacionalidad,
                                                 'pais': profesor.persona.pais,
                                                 'provincia': profesor.persona.provincia,
                                                 'canton': profesor.persona.canton,
                                                 'parroquia': profesor.persona.parroquia,
                                                 'sexo': profesor.persona.sexo,
                                                 'sangre': profesor.persona.sangre,
                                                 'sector': profesor.persona.sector,
                                                 'direccion': profesor.persona.direccion,
                                                 'direccion2': profesor.persona.direccion2,
                                                 'num_direccion': profesor.persona.num_direccion,
                                                 'telefono': profesor.persona.telefono,
                                                 'telefono_conv': profesor.persona.telefono_conv,
                                                 'email': profesor.persona.email,
                                                 'emailinst': profesor.persona.emailinst,
                                                 'coordinacion': profesor.coordinacion,
                                                 'dedicacion': profesor.dedicacion,
                                                 'nivelcategoria': profesor.nivelcategoria,
                                                 'cargo': profesor.cargo,
                                                 'nivelescalafon': profesor.nivelescalafon,
                                                 'categoria': profesor.categoria,
                                                 'fechaingreso': profesor.fechaingreso,
                                                 'contrato': profesor.contrato,
                                                 'tienetoken': profesor.tienetoken,
                                                 'asignatura': profesor.asignatura.all(),})
                    form.minivelcategoria(profesor)
                    form.editar(profesor.persona)
                    data['form'] = form
                    data['profesor'] = profesor
                    data['rangocategoria'] = ProfesorTipo.objects.all()
                    data['email_domain'] = EMAIL_DOMAIN
                    return render(request, "docentes/edit.html", data)
                except Exception as ex:
                    pass



            elif action == 'addzoomurlmodal':
                try:
                    profesor = Profesor.objects.get(pk=request.GET['id'])
                    form = ProfesorZoomUrlForm(initial={'urlzoom': profesor.urlzoom, 'urlzoomdos': profesor.urlzoomdos})
                    data['form'] = form
                    data['id'] = request.GET['id']
                    data['profesor'] = profesor
                    return render(request, "docentes/zoomurl.html", data)

                except Exception as ex:
                    pass



            elif action == 'actualizaciondatosmodal':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_profesores')
                    data['id'] = request.GET['id']
                    data['action'] = request.GET['action']
                    profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['form'] = ActualizacionDatosForm(initial={'cedula': profesor.persona.cedula})
                    data['profesor'] = profesor
                    template = get_template('docentes/modal/modalTipoProfesorAcciones.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'horario':
                try:
                    hoy = datetime.now().date()
                    horaactual = datetime.now().time()
                    numerosemanaactual = datetime.today().isocalendar()[1]
                    data['hoy'] = hoy
                    data['horaactual'] = horaactual
                    data['numerosemanaactual'] = numerosemanaactual
                    data['diaactual'] = diaactual = hoy.isocalendar()[2]
                    data['title'] = u'Horario del profesor'
                    profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['profesor'] = profesor
                    data['semana'] = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
                    periodo = request.session['periodo']
                    semana = semanatutoria = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                    data['periodo'] = periodo
                    data['semana'] = semana
                    data['semanatutoria'] = semanatutoria
                    clases = Clase.objects.filter(status=True,
                                                  activo=True,
                                                  materia__fechafinasistencias__gte=hoy,
                                                  fin__gte=hoy,
                                                  materia__nivel__periodo=periodo,
                                                  materia__nivel__periodo__visible=True,
                                                  materia__nivel__periodo__visiblehorario=True,
                                                  materia__profesormateria__profesor=profesor,
                                                  materia__profesormateria__principal=True,
                                                  materia__profesormateria__tipoprofesor_id__in=[11, 12, 1, 2, 5, 8, 7, 10, 13, 14, 15, 17],
                                                  tipoprofesor_id__in=[11, 12, 1, 2, 5, 8, 7, 10, 13, 14, 15, 17]).order_by('inicio')
                    clasesayudante = Clase.objects.values_list('id').filter(status=True,
                                                                            activo=True,
                                                                            materia__fechafinasistencias__gte=hoy,
                                                                            fin__gte=hoy,
                                                                            materia__nivel__periodo=periodo,
                                                                            materia__nivel__periodo__visible=True,
                                                                            materia__nivel__periodo__visiblehorario=True,
                                                                            materia__profesormateria__profesor_id=profesor.id,
                                                                            profesorayudante_id=profesor.id,
                                                                            materia__profesormateria__principal=True).order_by('inicio')
                    clases_turnos = profesor.extraer_clases_y_turnos_practica(datetime.now().date(), periodo)
                    clases = Clase.objects.filter(Q(pk__in=clases.values_list('id')) | Q(pk__in=clasesayudante) | Q(pk__in=clases_turnos[0].values_list('id'))).distinct()
                    data['clases'] = clases
                    materiasnoprogramadas = ProfesorMateria.objects.filter(status=True,
                                                                           profesor_id=profesor.id,
                                                                           materia__nivel__periodo__visible=True,
                                                                           materia__nivel__periodo__visiblehorario=True,
                                                                           materia__nivel__periodo=periodo,
                                                                           tipoprofesor_id__in=[11, 12, 1, 2, 5, 8, 7, 10, 13, 14, 15, 17],
                                                                           hasta__gt=hoy,
                                                                           activo=True,
                                                                           principal=True).exclude(materia__id__in=clases.values_list("materia_id", flat=True), profesor=profesor)
                    data['materiasnoprogramadas'] = materiasnoprogramadas
                    idturnostutoria = []
                    if DetalleDistributivo.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, criteriodocenciaperiodo__criterio_id__in=[7]).exists():
                        if HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesor, periodo=periodo).exists():
                            idturnostutoria = HorarioTutoriaAcademica.objects.values_list('turno_id').filter(status=True, profesor=profesor, periodo=periodo).distinct()
                    clasecomplexivo = complexivo = ComplexivoClase.objects.filter(status=True, activo=True, materia__profesor__profesorTitulacion_id=profesor.id, materia__status=True)
                    data['clasecomplexivo'] = clasecomplexivo
                    sesiones = Sesion.objects.filter(Q(turno__id__in=clases.values_list('turno__id').distinct()) | Q(turno__complexivoclase__in=complexivo) | Q(turno__id__in=idturnostutoria)).distinct()
                    complexivoabierto = ComplexivoLeccion.objects.filter(status=True, abierta=True, clase__materia__profesor__profesorTitulacion_id=profesor.id)
                    disponiblecomplexivo = len(complexivoabierto) == 0
                    data['sesiones'] = sesiones

                    # if periodo.id < 76:
                    #     clases = Clase.objects.filter(activo=True, materia__nivel__periodo__visible=True, materia__nivel__periodo__visiblehorario=True, materia__profesormateria__profesor=profesor, materia__nivel__periodo=request.session['periodo']).exclude(materia__profesormateria__tipoprofesor=TIPO_DOCENTE_FIRMA)
                    # else:
                    #     clases = Clase.objects.filter(activo=True, materia__nivel__periodo__visible=True, materia__nivel__periodo__visiblehorario=True, profesor=profesor,materia__nivel__periodo=request.session['periodo']).exclude(materia__profesormateria__tipoprofesor=TIPO_DOCENTE_FIRMA)
                    # missesiones = []
                    # for clase in clases:
                    #     profesormateria = ProfesorMateria.objects.filter(materia=clase.materia, status=True, profesor=profesor)
                    #     if profesormateria:
                    #         tipoprofesor = profesormateria[0].tipoprofesor
                    #         if tipoprofesor == clase.tipoprofesor:
                    #             missesiones.append(clase.turno.sesion_id)
                    # data['sesiones'] = Sesion.objects.filter(id__in=missesiones)
                    # # clasespm = [(x, x.materia.profesormateria_set.filter(profesor=profesor)[:1].get(), x.tipoprofesor) for x in clases]
                    # clasespm = []
                    # for x in clases:
                    #     profesormateria = ProfesorMateria.objects.filter(materia=x.materia, status=True, profesor=profesor)
                    #     if profesormateria.exists():
                    #         tipoprofesor = profesormateria[0].tipoprofesor
                    #         if tipoprofesor == x.tipoprofesor:
                    #             clasespm.append([x, x.materia.profesormateria_set.filter(profesor=profesor)[:1].get(), x.tipoprofesor])
                    # data['clases'] = clasespm
                    data['reporte_2'] = obtener_reporte('horario_profesor')
                    return render(request, "docentes/horario.html", data)
                except Exception as ex:
                    pass

            elif action == 'addadministrativo':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Crear cuenta de administrativo'
                    data['profesor'] = Profesor.objects.get(pk=request.GET['id'])
                    return render(request, "docentes/addadministrativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'desactivarperfil':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Desactivar perfil de usuario'
                    data['profesor'] = Profesor.objects.get(pk=request.GET['id'])
                    return render(request, "docentes/desactivarperfil.html", data)
                except Exception as ex:
                    pass

            elif action == 'activarperfil':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Activar perfil de usuario'
                    data['profesor'] = Profesor.objects.get(pk=request.GET['id'])
                    return render(request, "docentes/activarperfil.html", data)
                except Exception as ex:
                    pass

            elif action == 'materias':
                try:
                    data['title'] = u'Materias del profesor'
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['periodo']= periodo = request.session['periodo']
                    data['profesor'] = profesor
                    data['materias'] = profesor.mis_materiastodas(periodo).order_by('materia__asignatura__nombre', 'materia__paralelomateria__nombre', 'tipoprofesor__nombre')
                    data['reporte_0'] = obtener_reporte('listado_asistencia_dias')
                    data['reporte_1'] = obtener_reporte('lista_alumnos_matriculados_materia')
                    data['reporte_2'] = obtener_reporte("control_academico")
                    data['pueden_configurar_registrar_asistencia'] = variable_valor('PUEDEN_CONFIGURAR_REGISTRO_ASISTENCIA')
                    return render(request, "docentes/materias.html", data)
                except Exception as ex:
                    pass

            elif action == 'preferencias':
                try:
                    data['title'] = u'Preferencia de asignaturas'
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    periodo = request.session['periodo']
                    data['asignaturaspreferencias'] = profesor.asignaturamallapreferencia_set.filter(periodo=periodo, status=True)
                    return render(request, "docentes/preferencias.html", data)
                except Exception as ex:
                    pass

            elif action == 'preferenciaactividad':
                try:
                    data['title'] = u'Preferencia de actividades'
                    data['t'] = None
                    if 't' in request.GET:
                        data['t'] = int(request.GET['t'])
                    periodo = request.session['periodo']
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['criteriodocencia'] = profesor.preferenciadetalleactividadescriterio_set.filter(criteriodocenciaperiodo__periodo=periodo, status=True).order_by('criteriodocenciaperiodo__actividad__nombre','criteriodocenciaperiodo__criterio__nombre')
                    data['criterioinvestigacion'] = profesor.preferenciadetalleactividadescriterio_set.filter(criterioinvestigacionperiodo__periodo=periodo, status=True).order_by('criterioinvestigacionperiodo__actividad__nombre','criterioinvestigacionperiodo__criterio__nombre')
                    data['criteriogestion'] = profesor.preferenciadetalleactividadescriterio_set.filter(criteriogestionperiodo__periodo=periodo, status=True).order_by('criteriogestionperiodo__actividad__nombre','criteriogestionperiodo__criterio__nombre')
                    return render(request, "docentes/preferenciasactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'preferenciahorario':
                try:
                    data['title'] = u'Preferencia de horarios'
                    data['periodo'] = periodo = request.session['periodo']
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    # data['turnos'] = Turno.objects.filter(sesion_id=1, status=True).distinct().order_by('comienza')
                    data['turnos'] = Turno.objects.filter(sesion_id=20, status=True, mostrar=True).distinct().order_by('comienza')
                    data['observacion'] = HorarioPreferenciaObse.objects.get(profesor=profesor, periodo=periodo) if HorarioPreferenciaObse.objects.filter(profesor=profesor, periodo=periodo).exists() else None
                    return render(request, "docentes/preferenciahorario.html", data)
                except Exception as ex:
                    pass

            elif action == 'abrirm':
                try:
                    puede_realizar_accion(request, 'sga.puede_abrir_materia')
                    materia = Materia.objects.get(pk=request.GET['id'])
                    if not materia.nivel.cerrado:
                        pofesorid = request.GET['pofesorid']
                        materia.cerrado = False
                        materia.save(request)
                        log(u'Abrió la materia: %s' % materia, request, "abrir")
                        return HttpResponseRedirect("/docentes?action=materias&id=" + str(pofesorid) )
                except Exception as ex:
                    transaction.set_rollback(True)

            # elif action == 'cerrarm':
            #     try:
            #         puede_realizar_accion(request, 'sga.puede_abrir_materia')
            #         materia = Materia.objects.get(pk=request.GET['id'])
            #         pofesorid = request.GET['pofesorid']
            #         materia.cerrado = True
            #         materia.save(request)
            #         return HttpResponseRedirect("/docentes?action=materias&id=" + str(pofesorid))
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         pass

            elif action == 'diasacalificar':
                try:
                    data['title'] = u'Dias para calificar la materia'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['profesor'] = Profesor.objects.get(pk=request.GET['pofesorid'])
                    data['form'] = CalificacionDiaForm(initial={'usaperiodocalificaciones': materia.usaperiodocalificaciones,
                                                                'diasactivacioncalificaciones': materia.diasactivacioncalificaciones})
                    return render(request, "docentes/diasacalificar.html", data)
                except Exception as ex:
                    pass

            elif action == 'confirmar_actualizacion_estudiantes':
                try:
                    data['title'] = u'Confirmar acualización de estudiantes'
                    data['profesor'] = Profesor.objects.get(pk=request.GET['idp'])
                    data['materia'] = Materia.objects.get(pk=request.GET['id'])
                    return render(request, "docentes/confirmar_actualizacion_estudiantes.html", data)
                except Exception as ex:
                    pass

            elif action == 'confirmar_actualizacion_docentes':
                try:
                    data['title'] = u'Confirmar acualización de docentes'
                    data['profesor'] = Profesor.objects.get(pk=request.GET['idp'])
                    data['materia'] = Materia.objects.get(pk=request.GET['id'])
                    return render(request, "docentes/confirmar_actualizacion_docentes.html", data)
                except Exception as ex:
                    pass

            elif action == 'confirmar_actualizacion_silabos':
                try:
                    data['title'] = u'Confirmar acualización de sílabo'
                    data['profesor'] = Profesor.objects.get(pk=request.GET['idp'])
                    data['materia'] = Materia.objects.get(pk=request.GET['id'])
                    return render(request, "docentes/confirmar_actualizacion_silabo.html", data)
                except Exception as ex:
                    pass

            elif action == 'tipoprofesor':
                try:
                    data['title'] = u'Tipo profesor'
                    data['tipoprofesores'] = TipoProfesor.objects.filter(status=True)
                    return render(request, "docentes/tipoprofesor.html", data)
                except Exception as ex:
                    pass


            elif action == 'addtipoprofesormod':
                try:

                    form = TipoProfesorForm()
                    data['form'] = form
                    template = get_template("docentes/modal/modalTipoProfesorAcciones.html")
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            elif action == 'editarTipoProfesorMod':

                try:
                    data['id'] = request.GET['id']
                    data['action'] = request.GET['action']

                    data['tipoprofesor'] = tipoprofesor = TipoProfesor.objects.get(
                        pk=request.GET['id'])

                    form = TipoProfesorForm(initial={'nombre': tipoprofesor.nombre, 'tipoevaluar': tipoprofesor.tipoevaluar})

                    data['form'] = form

                    template = get_template("docentes/modal/modalTipoProfesorAcciones.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'deletetipoprofesor':
                try:
                    data['title'] = u'Eliminar Tipo Profesor'
                    data['tipoprofesor'] = TipoProfesor.objects.get(pk=request.GET['idtipoprofesor'])
                    return render(request, "docentes/deletetipoprofesor.html", data)
                except Exception as ex:
                    pass

            elif action == 'versilabos':
                try:
                    data['title'] = u'SÍLABO'
                    data['fechahoy'] = datetime.now().date()
                    materiacerrada = False
                    data['periodoseleccionado'] = periodo
                    data['profesor'] = Profesor.objects.get(pk=request.GET['idp'])
                    data['materia'] = materia = Materia.objects.get(pk=int(request.GET['id']), status=True)
                    if materia.cerrado:
                        materiacerrada = True
                    data['materiacerrada'] = materiacerrada
                    data['silabomateria'] = materia.silabo_set.all()
                    return render(request, "docentes/viewsilabos.html", data)
                except Exception as ex:
                    pass

            elif action == 'delsilabo':
                try:
                    data['title'] = u'Eliminar Cabecera de Silabo'
                    data['silabo'] = silabo = Silabo.objects.get(pk=int(encrypt(request.GET['ids'])))
                    data['profesor'] = Profesor.objects.get(pk=request.GET['idp'])
                    return render(request, "docentes/delsilabo.html", data)
                except Exception as ex:
                    pass

            elif action == 'planrecursoclasevirtual':
                try:
                    data['title'] = u'PLANIFICACIÓN RECURSOS DE SÍLABO'
                    data['fechahoy'] = datetime.now().date()
                    materiacerrada = False
                    data['periodoseleccionado'] = periodo
                    data['profesor'] =Profesor.objects.get(id=request.GET['idprofesor'])
                    data['silabocab'] = silabocab = Silabo.objects.get(pk=int(encrypt(request.GET['silaboid'])), status=True)
                    if silabocab.materia.cerrado:
                        materiacerrada = True
                    data['materiacerrada'] = materiacerrada
                    data['idcoordinacion'] = silabocab.materia.asignaturamalla.malla.carrera.mi_coordinacion2()
                    data['silabosemanal'] = silabosemanal = silabocab.silabosemanal_set.filter(status=True).order_by('numsemana')
                    data['listadounidades'] = DetalleSilaboSemanalTema.objects.values_list('temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico_id').filter(silabosemanal_id__in=silabosemanal.values_list('id'), temaunidadresultadoprogramaanalitico__status=True).distinct()
                    # data['puede_videomagistral'] = silabocab.puede_videomagistral()
                    data['puede_videomagistral'] = silabocab.videomagistral
                    if silabocab.versionrecurso == 1:
                        return render(request, "docentes/planrecursoclasevirtual.html", data)
                    if silabocab.versionrecurso == 2:
                        data['semanaexamenes'] = PlanificacionClaseSilabo.objects.values_list('semana',flat=True).filter(tipoplanificacion__planificacionclasesilabo_materia__materia=silabocab.materia, examen=True,status=True).exclude(semana=0)
                        # return render(request, "docentes/plansemanalrecurso.html", data)
                        return render(request, "docentes/planrecursoclasevirtual.html", data)
                except Exception as ex:
                    pass

            elif action == 'thvidadocentesexc':
                try:
                    prf = Profesor.objects.get(pk=request.GET['id'])
                    persona = prf.persona
                    nombredocente = '{} {}'.format(elimina_tildes(prf.persona.apellido1), elimina_tildes(prf.persona.nombres))
                    nombredocente_str = '{}_{}'.format(elimina_tildes(prf.persona.apellido1.lower()), elimina_tildes(prf.persona.nombres.lower()))
                    __author__ = 'Unemi'
                    borders = Borders()
                    borders.left = Borders.THIN
                    borders.right = Borders.THIN
                    borders.top = Borders.THIN
                    borders.bottom = Borders.THIN
                    align = Alignment()
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style.borders = borders
                    font_style.alignment = align
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    font_style2.borders = borders
                    font_style2.alignment = align
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    title = easyxf('font: name Calibri, color-index black, bold on , height 260; alignment: horiz centre')
                    fuentecabecera = easyxf('font: name Calibri, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentetexto = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    fechahoy = datetime.now().date()
                    ws = wb.add_sheet('HOJA DE VIDA')
                    ws.write_merge(0, 0, 0, 1, '{}'.format(prf.persona.__str__()), title)
                    ws.write_merge(1, 1, 0, 1, 'DATOS PERSONALES', fuentecabecera)
                    ws.col(0).width = 10000
                    ws.col(1).width = 10000
                    ws.write(2, 0, 'APELLIDOS', fuentetexto)
                    ws.write(2, 1, '{} {}'.format(persona.apellido1, prf.persona.apellido2), fuentetexto)
                    ws.write(3, 0, 'NOMBRES', fuentetexto)
                    ws.write(3, 1, '{}'.format(persona.nombres), fuentetexto)
                    ws.write(4, 0, 'CÉDULA', fuentetexto)
                    ws.write(4, 1, '{}'.format(persona.identificacion()), fuentetexto)
                    ws.write(5, 0, 'TELÉFONO', fuentetexto)
                    ws.write(5, 1, '{}'.format(persona.telefonos()), fuentetexto)
                    ws.write(6, 0, 'DEPARTAMENTO', fuentetexto)
                    ws.write(6, 1, '{}'.format(persona.departamentopersona()), fuentetexto)
                    ws.write(7, 0, 'CARGO', fuentetexto)
                    if persona.distributivopersona_set.filter(estadopuesto_id=1,status=True).exists():
                        ws.write(7, 1, '{}'.format(persona.cargo_persona()), fuentetexto)
                    else:
                        ws.write(7, 1, '', fuentetexto)
                    ws.write_merge(8, 8, 0, 1, 'DETALLE', fuentecabecera)
                    ws.write(9, 0, 'TOTAL CAPACITACIONES', fuentetexto)
                    ws.write(9, 1, '{}'.format(prf.persona.mis_capacitaciones().count()), fuentetexto)
                    ws.write(10, 0, 'TOTAL ACCIONES DEL PERSONAL', fuentetexto)
                    ws.write(10, 1, '{}'.format(prf.persona.mis_acciones_hvida().count()), fuentetexto)
                    articulos = ArticuloInvestigacion.objects.select_related().filter((Q(participantesarticulos__profesor__persona=persona) |
                                                                                       Q(participantesarticulos__administrativo__persona=persona)),
                                                                                      status=True, aprobado=True, participantesarticulos__status=True).order_by('-fechapublicacion')
                    ponencias = PonenciasInvestigacion.objects.select_related().filter((Q(participanteponencias__profesor__persona=persona) |
                                                                                        Q(participanteponencias__administrativo__persona=persona)),
                                                                                       status=True, participanteponencias__status=True)
                    capitulos = CapituloLibroInvestigacion.objects.select_related().filter((Q(participantecapitulolibros__profesor__persona=persona)
                                                                                            | Q(participantecapitulolibros__profesor__persona=persona)),
                                                                                           status=True, participantecapitulolibros__status=True)
                    libros = LibroInvestigacion.objects.select_related().filter((Q(participantelibros__profesor__persona=persona) |
                                                                                 Q(participantelibros__profesor__persona=persona)),
                                                                                status=True, participantelibros__status=True)
                    solicitudes = SolicitudPublicacion.objects.filter(persona=persona, aprobado=False, status=True).order_by('-fecha_creacion')
                    ws.write(11, 0, 'TOTAL PUBLICACIONES ACADEMICAS', fuentetexto)
                    ws.write(11, 1, (articulos.count() + ponencias.count() + capitulos.count() + libros.count() + solicitudes.count()), fuentetexto)
                    ws.write(12, 0, 'TOTAL SOLICITUDES', fuentetexto)
                    ws.write(12, 1, solicitudes.count(), fuentetexto)
                    ws.write(13, 0, 'TOTAL ARTICULOS', fuentetexto)
                    ws.write(13, 1, articulos.count(), fuentetexto)
                    ws.write(14, 0, 'TOTAL PONENCIAS', fuentetexto)
                    ws.write(14, 1, ponencias.count(), fuentetexto)
                    ws.write(15, 0, 'TOTAL CAPITULOS', fuentetexto)
                    ws.write(15, 1, capitulos.count(), fuentetexto)
                    ws.write(16, 0, 'TOTAL LIBROS', fuentetexto)
                    ws.write(16, 1, libros.count(), fuentetexto)
                    proyectos_externos = ProyectoInvestigacionExterno.objects.filter(persona=persona, status=True)
                    proyectos_participante =  persona.profesor_set.filter(status=True)[0].participantesmatrices_set.filter(status=True)
                    ws.write(17, 0, 'TOTAL PROYECTOS', fuentetexto)
                    ws.write(17, 1, (proyectos_participante.count()+proyectos_externos.count()), fuentetexto)
                    existeactual = RespuestaEvaluacionAcreditacion.objects.values('profesor', 'proceso', 'proceso__mostrarresultados', 'proceso__periodo', 'proceso__periodo__nombre').filter(profesor=prf).distinct().order_by('proceso')
                    existeanterior = ResumenFinalProcesoEvaluacionIntegral.objects.filter(profesor=prf).exists()
                    existeanteriorcount = 0
                    if existeanterior:
                        existeanteriorcount = 1
                    periodoslect = MigracionEvaluacionDocente.objects.values('idperiodo', 'descperiodo', 'tipoeval').filter(idprofesor=prf.pk).distinct().order_by('idperiodo')

                    ws.write(18, 0, 'TOTAL EVALUACIONES', fuentetexto)
                    ws.write(18, 1, (existeactual.count() + periodoslect.count() + existeanteriorcount), fuentetexto)

                    ws = wb.add_sheet('CAPACITACIONES')
                    ws.write_merge(0, 0, 0, 4, 'CAPACITACIONES', title)
                    columns = [
                        (u"FECHA INICIO", 4000),
                        (u"FECHA FIN", 4000),
                        (u"INSTITUCIÓN", 8000),
                        (u"EVENTO", 10000),
                        (u"HORAS", 4000),
                    ]
                    row_num = 2
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 3
                    for cp in persona.mis_capacitaciones():
                        ws.write(row_num, 0, str(cp.fechainicio), fuentetexto)
                        ws.write(row_num, 1, str(cp.fechafin), fuentetexto)
                        ws.write(row_num, 2, cp.institucion, fuentetexto)
                        ws.write(row_num, 3, cp.nombre, fuentetexto)
                        ws.write(row_num, 4, cp.horas, fuentetexto)
                        row_num += 1

                    ws = wb.add_sheet('ACCIONES DEL PERSONAL')
                    ws.write_merge(0, 0, 0, 4, 'ACCIONES DEL PERSONAL', title)
                    columns = [
                        (u"FECHA", 4000),
                        (u"NÚMERO DE DOCUMENTO", 8000),
                        (u"TIPO", 10000),
                        (u"MOTIVO", 10000),
                        (u"UBICACIÓN DEL FISICO", 8000),
                    ]
                    row_num = 2
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 3
                    for cp in persona.mis_acciones_hvida():
                        ws.write(row_num, 0, str(cp.fecharige), fuentetexto)
                        ws.write(row_num, 1, cp.numerodocumento, fuentetexto)
                        ws.write(row_num, 2, cp.tipo.nombre if cp.tipo else '', fuentetexto)
                        ws.write(row_num, 3, cp.motivo.nombre if cp.motivo else '', fuentetexto)
                        ws.write(row_num, 4, cp.ubicacionfisico, fuentetexto)
                        row_num += 1

                    ws = wb.add_sheet('PUBLICACIONES ACADEMICAS')
                    ws.write_merge(0, 0, 0, 3, 'PUBLICACIONES ACADEMICAS', title)
                    ws.write_merge(1, 1, 0, 2, 'SOLICITUDES', fuentecabecera)
                    columns = [
                        (u"SOLICITUD", 10000),
                        (u"TIPO DE SOLICITUD", 4000),
                        (u"ESTADO", 4000),
                    ]
                    row_num = 2
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 3
                    for cp in solicitudes:
                        if cp.tiposolicitud == 1 or cp.tiposolicitud == 5 or cp.tiposolicitud == 3 or cp.tiposolicitud == 2:
                            ws.write(row_num, 0, cp.nombre, fuentetexto)
                        else:
                            ws.write(row_num, 0, cp.motivo, fuentetexto)
                        ws.write(row_num, 1, cp.get_tiposolicitud_display(), fuentetexto)
                        if not cp.aprobado and not cp.observacion:
                            ws.write(row_num, 2, 'PENDIENTE', fuentetexto)
                        elif not cp.aprobado and cp.observacion:
                            ws.write(row_num, 2, 'RECHAZADO', fuentetexto)
                        else:
                            ws.write(row_num, 2, '', fuentetexto)
                        row_num += 1

                    row_num += 2
                    ws.write_merge(row_num, row_num, 0, 2, 'ARTÍCULOS', fuentecabecera)
                    columns = [
                        (u"REVISTA", 8000),
                        (u"ARTÍCULO", 10000),
                        (u"PUBLICACIÓN", 4000),
                    ]
                    row_num += 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    for cp in articulos:
                        ws.write(row_num, 0, cp.revista.nombre if cp.revista else '', fuentetexto)
                        ws.write(row_num, 1, cp.nombre, fuentetexto)
                        ws.write(row_num, 2, str(cp.fechapublicacion), fuentetexto)
                        row_num += 1

                    row_num += 2
                    ws.write_merge(row_num, row_num, 0, 4, 'PONENCIAS', fuentecabecera)
                    columns = [
                        (u"PONENCIA", 8000),
                        (u"EVENTO", 10000),
                        (u"PAÍS", 4000),
                        (u"CIUDAD", 4000),
                        (u"PUBLICACIÓN", 4000),
                    ]
                    row_num += 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    for cp in ponencias:
                        ws.write(row_num, 0, cp.nombre, fuentetexto)
                        ws.write(row_num, 1, cp.evento, fuentetexto)
                        ws.write(row_num, 2, cp.pais.nombre if cp.pais else '', fuentetexto)
                        ws.write(row_num, 3, cp.ciudad if cp.ciudad else '', fuentetexto)
                        ws.write(row_num, 4, str(cp.fechapublicacion), fuentetexto)
                        row_num += 1

                    row_num += 2
                    ws.write_merge(row_num, row_num, 0, 2, 'CAPITULOS', fuentecabecera)
                    columns = [
                        (u"CAPÍTULO", 8000),
                        (u"LIBRO", 10000),
                        (u"PUBLICACIÓN", 4000),
                    ]
                    row_num += 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    for cp in capitulos:
                        ws.write(row_num, 0, cp.titulocapitulo.upper(), fuentetexto)
                        ws.write(row_num, 1, cp.titulolibro.upper(), fuentetexto)
                        ws.write(row_num, 2, str(cp.fechapublicacion), fuentetexto)
                        row_num += 1

                    row_num += 2
                    ws.write_merge(row_num, row_num, 0, 3, 'LIBROS', fuentecabecera)
                    columns = [
                        (u"CÓDIGO", 8000),
                        (u"NOMBRE", 10000),
                        (u"PUBLICACIÓN", 4000),
                        (u"ÁREA DE CONOCIMIENTO", 4000),
                    ]
                    row_num += 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    for cp in libros:
                        ws.write(row_num, 0, "{}-{}-LIB".format(cp.codisbn,cp.pk), fuentetexto)
                        ws.write(row_num, 1, cp.nombrelibro, fuentetexto)
                        ws.write(row_num, 2, str(cp.fechapublicacion), fuentetexto)
                        ws.write(row_num, 3, cp.areaconocimiento.nombre if cp.areaconocimiento else '', fuentetexto)
                        row_num += 1

                    ws = wb.add_sheet('PROYECTOS')
                    ws.write_merge(0, 0, 0, 7, 'PROYECTOS', title)

                    columns = [
                        (u"CODIGO", 10000),
                        (u"NOMBRE CERTIFICADO", 14000),
                    ]
                    row_num = 2
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 3
                    for cp in proyectos_participante:
                        ws.write(row_num, 0, cp.proyecto.programa.nombre if cp.proyecto else '', fuentetexto)
                        ws.write(row_num, 1, cp.proyecto.nombre if cp.proyecto else '', fuentetexto)
                        row_num += 1

                    row_num += 2
                    ws.write_merge(row_num, row_num, 0, 1, 'PROYECTOS DE INVESTIGACIÓN EXTERNOS', fuentecabecera)
                    columns = [
                        (u"PROYECTO", 10000),
                        (u"INSTITUCION", 14000),
                    ]
                    row_num += 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    for cp in proyectos_externos:
                        ws.write(row_num, 0, cp.nombre, fuentetexto)
                        ws.write(row_num, 1, cp.institucion if cp.institucion else '', fuentetexto)
                        row_num += 1

                    ws = wb.add_sheet('EVALUACIONES')
                    ws.write_merge(0, 0, 0, 1, 'EVALUACIONES', title)
                    columns = [
                        (u"CODIGO", 4000),
                        (u"NOMBRE CERTIFICADO", 14000),
                    ]
                    row_num = 2
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 3
                    for cp in existeactual:
                        ws.write(row_num, 0, '228', fuentetexto)
                        ws.write(row_num, 1, 'CERTIFICADO MODELO INTEGRAL DE EVALUACIÓN DOCENTE {}'.format(cp['proceso__periodo__nombre']),
                                 fuentetexto)
                        row_num += 1
                    if existeanterior:
                        ws.write(row_num, 0, '173', fuentetexto)
                        ws.write(row_num, 1, 'CERTIFICADO DE EVALUACIÓN DOCENTE PERIODO MAYO / SEPTIEMBRE 2015',
                                 fuentetexto)
                        row_num += 1
                    for cp in periodoslect:
                        ws.write(row_num, 0, cp['idperiodo'], fuentetexto)
                        ws.write(row_num, 1, 'CERTIFICADO DE EVALUACIÓN DOCENTE {}'.format(cp['descperiodo']), fuentetexto)
                        row_num += 1

                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename={}.xls'.format(nombredocente_str)
                    wb.save(response)
                    return response
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    print(ex)
                    messages.error(request, ex)

            elif action == 'thvidadocentesval':
                try:
                    prf = Profesor.objects.get(pk=request.GET['id'])
                    time.sleep(5)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    messages.error(request, ex)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'thdocenteslist':
                try:
                    profesores = Profesor.objects.select_related().filter(nivelcategoria_id=1).exclude(persona__apellido1__icontains='TECNICO').exclude(persona__apellido1__icontains='DOCENTE').order_by('-persona__usuario__is_active',
                                                                                                                                                                                                          'persona__apellido1', 'persona__apellido2',
                                                                                                                                                                                                          'persona__nombres')
                    listaenviar = list(profesores.values('id','persona__apellido1','persona__apellido2','persona__nombres'))
                    return JsonResponse({"result": "ok", "cantidad": len(listaenviar), "inscritos": listaenviar})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'thvidadocentesexcmasv':
                try:
                    directory = os.path.join(SITE_STORAGE, 'zipav')
                    try:
                        os.stat(directory)
                    except:
                        os.mkdir(directory)
                    url = os.path.join(SITE_STORAGE, 'media', 'zipav', 'hojavidadocentes.zip'.__str__())
                    fantasy_zip = zipfile.ZipFile(url, 'w')
                    profesores = Profesor.objects.select_related().filter(nivelcategoria_id=1).exclude(persona__apellido1__icontains='TECNICO').exclude(persona__apellido1__icontains='DOCENTE').order_by('-persona__usuario__is_active', 'persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    for prf in profesores:
                        nombredocente = '{} {}'.format(elimina_tildes(prf.persona.apellido1), elimina_tildes(prf.persona.nombres))
                        nombredocente_str = '{}_{}'.format(elimina_tildes(prf.persona.apellido1.lower()), elimina_tildes(prf.persona.nombres.lower()))
                        __author__ = 'Unemi'
                        borders = Borders()
                        borders.left = Borders.THIN
                        borders.right = Borders.THIN
                        borders.top = Borders.THIN
                        borders.bottom = Borders.THIN
                        align = Alignment()
                        font_style = XFStyle()
                        font_style.font.bold = True
                        font_style.borders = borders
                        font_style.alignment = align
                        font_style2 = XFStyle()
                        font_style2.font.bold = False
                        font_style2.borders = borders
                        font_style2.alignment = align
                        style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                        style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                        style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                        title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                        style1 = easyxf(num_format_str='D-MMM-YY')
                        title = easyxf('font: name Calibri, color-index black, bold on , height 260; alignment: horiz centre')
                        fuentecabecera = easyxf('font: name Calibri, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                        fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                        fuentetexto = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                        font_style = XFStyle()
                        font_style.font.bold = True
                        font_style2 = XFStyle()
                        font_style2.font.bold = False
                        wb = Workbook(encoding='utf-8')
                        fechahoy = datetime.now().date()
                        ws = wb.add_sheet('HOJA DE VIDA')
                        ws.write_merge(0, 0, 0, 3, 'HOJA VIDA', title)
                        columns = [
                            (u"BANDERA ACTUALIZACIÓN", 8000),
                            (u"RÉGIMEN LABOAL", 10000),
                            (u"ACTUALIZACIÓN DE DATOS", 10000),
                            (u"VALOR PORCENTUAL", 4000),
                        ]
                        row_num = 1
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                            ws.col(col_num).width = columns[col_num][1]
                        row_num = 2
                        ws.write_merge(row_num, row_num, 0, 0, 'ACTUALIZADO', font_style2)
                        date_format = xlwt.XFStyle()
                        date_format.num_format_str = 'yyyy-mm-dd'
                        date_formatreverse = xlwt.XFStyle()
                        date_formatreverse.num_format_str = 'dd/mm/yyyy'
                        response = HttpResponse(content_type="application/ms-excel")
                        response['Content-Disposition'] = 'attachment; filename={}.xls'.format(nombredocente_str)
                        wb.save(response)
                        fantasy_zip.write(response, '{}.xls'.format(nombredocente_str))
                    fantasy_zip.close()
                    responsezip = HttpResponse(open(url, 'rb'), content_type='application/zip')
                    responsezip['Content-Disposition'] = 'attachment; filename=hojavidadocentes.zip'
                    return responsezip
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    messages.error(request, ex)

            elif action == 'editpresentacion':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = DiapositivaSilaboSemanal.objects.get(pk=request.GET['id'])
                    data['form2'] = PresentacionDiapositivaEditForm(initial=model_to_dict(filtro))
                    template = get_template("docentes/modal/formpresentacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editcompendio':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = CompendioSilaboSemanal.objects.get(pk=request.GET['id'])
                    data['form2'] = CompendioSilaboSemanalEditForm(initial=model_to_dict(filtro))
                    template = get_template("docentes/modal/formpresentacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editvideo':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = VideoMagistralSilaboSemanal.objects.get(pk=request.GET['id'])
                    data['form2'] = VideoMagistralSilaboSemanalEditForm(initial=model_to_dict(filtro))
                    template = get_template("docentes/modal/formpresentacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editguia':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = GuiaEstudianteSilaboSemanal.objects.get(pk=request.GET['id'])
                    data['form2'] = GuiaEstudianteSilaboSemanalEditForm(initial=model_to_dict(filtro))
                    template = get_template("docentes/modal/formpresentacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editguiadocente':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = GuiaDocenteSilaboSemanal.objects.get(pk=request.GET['id'])
                    data['form2'] = GuiaDocenteSilaboSemanalEditForm(initial=model_to_dict(filtro))
                    template = get_template("docentes/modal/formpresentacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editmaterial':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = MaterialAdicionalSilaboSemanal.objects.get(pk=request.GET['id'])
                    data['form2'] = MaterialAdicionalSilaboSemanalEditForm(initial=model_to_dict(filtro))
                    template = get_template("docentes/modal/formpresentacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edittareasemanal':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = TareaSilaboSemanal.objects.get(pk=request.GET['id'])
                    data['form2'] = TareaSilaboSemanalEditForm(initial=model_to_dict(filtro))
                    template = get_template("docentes/modal/formpresentacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editforos':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ForoSilaboSemanal.objects.get(pk=request.GET['id'])
                    data['form2'] = ForoSilaboSemanalEditForm(initial=model_to_dict(filtro))
                    template = get_template("docentes/modal/formpresentacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edittest':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = TestSilaboSemanal.objects.get(pk=request.GET['id'])
                    data['form2'] = TestSilaboSemanalEditForm(initial=model_to_dict(filtro))
                    template = get_template("docentes/modal/formpresentacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edittestnivelacion':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = TestSilaboSemanalAdmision.objects.get(pk=request.GET['id'])
                    data['form2'] = TestSilaboSemanalAdmisionEditForm(initial={'nombretest': filtro.titulo,
                                                                               'idtestmoodle': filtro.idtestmoodle,
                                                                               'estado': filtro.estado,
                                                                               'url': filtro.url1})
                    template = get_template("docentes/modal/formpresentacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edittrabajopractico':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = TareaPracticaSilaboSemanal.objects.get(pk=request.GET['id'])
                    data['form2'] = TareaPracticaSilaboSemanalEditForm(initial=model_to_dict(filtro))
                    template = get_template("docentes/modal/formpresentacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'asistenciamateria':
                try:
                    idp = None
                    idpm =None
                    idm =None
                    data['title'] = u'Asistencias de alumnos'
                    if 'idp' in request.GET:
                        idp = int(request.GET['idp'])
                    if 'idpm' in request.GET:
                        idpm = int(request.GET['idpm'])
                    if 'idm' in request.GET:
                        idm = int(request.GET['idm'])
                    profesoresmaterias = None
                    if idpm is None:
                        if not ProfesorMateria.objects.values("id").filter(materia_id=idm, profesor_id=idp, status=True).exists():
                            raise NameError(u"Profesor de la materia no encontrado")
                        profesoresmaterias = ProfesorMateria.objects.filter(materia_id=idm, profesor_id=idp, status=True)
                    else:
                        if not ProfesorMateria.objects.values("id").filter(pk=idpm, status=True).exists():
                            raise NameError(u"Profesor de la materia no encontrado")
                        profesoresmaterias = ProfesorMateria.objects.filter(pk=idpm, status=True)
                    profesor = profesoresmaterias[0].profesor
                    materia = profesoresmaterias[0].materia
                    data['profesor'] = profesor
                    data['asistenciaaprobar'] = materia.modeloevaluativo.asistenciaaprobar
                    data['materia'] = materia
                    data['profesoresmaterias'] = profesoresmaterias
                    return render(request, "docentes/calendarioasistencias.html", data)
                except Exception as ex:
                    if idp is None:
                        return HttpResponseRedirect(f"/docentes")
                    return HttpResponseRedirect(f"/docentes?action=materias&id={idp}")

            elif action == 'cambiaasistencia':
                try:
                    activo = True
                    # observacion = request.GET['observacion'].strip().upper()
                    observacion = 'VALIDACIÓN DE ASISTENCIA AUTORIZADO POR VICERECTORADO ACADÉMICO'
                    asistencia = SesionZoom.objects.get(pk=request.GET['id'])
                    if asistencia.activo:
                        asistencia.activo = False
                        activo = False
                        if not observacion:
                            #observacion="DESACTIVADA POR DOCENTE"
                            return JsonResponse({"result": "bad",
                                                 "mensaje": u"Ingrese observación"})
                    else:
                        # if date.today()<= asistencia.fecha+timedelta(days=1):
                        asistencia.activo = True
                        activo = True
                        if not observacion:
                            return JsonResponse({"result": "bad",
                                                 "mensaje": u"Ingrese observación"})
                            #observacion = "ACTIVADA POR DOCENTE"
                        # else:
                        #     return JsonResponse({"result": "bad", "mensaje": u"Sólo puede activar asistencia dentro de las 24 horas posteriores a su clase."})
                    asistencia.save(request)
                    obser = DesactivarSesionZoom(sesion=asistencia, observacion=observacion)
                    obser.save(request)
                    por = 0
                    id = asistencia.materiaasignada.pk
                    if asistencia.materiaasignada.asistencias_zoom_valida() > 0:
                        por = round(((asistencia.materiaasignada.asistencias_zoom_valida() * 100) / asistencia.materiaasignada.cantidad_asistencias_zoom()),0)
                    asistencia.materiaasignada.asistenciafinal = por
                    asistencia.materiaasignada.save()


                    log(u'Cambió asistencia: %s ' % asistencia, request, "edit")

                    return JsonResponse({"result": "ok","activo":activo,"por":por,"id":id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'abrirmasistencia':
                try:
                    puede_realizar_accion(request, 'sga.puede_abrir_materia')
                    idm = int(request.GET['idm'])
                    idp = request.GET['idp']
                    materia = Materia.objects.get(pk=idm)
                    materia.cerrado = False
                    materia.save(request)
                    log(u'Se abrió el acta: codigomateria(%s) - %s' % (materia.id, materia), request, "edit")
                    for asig in materia.asignados_a_esta_materia():
                        asig.cerrado = True
                        asig.save(request, actualiza=False)
                    return HttpResponseRedirect("{}?action=asistenciamateria&idm={}&idp={}".format(request.path, idm, idp))
                except Exception as ex:
                    transaction.set_rollback(True)

            elif action == 'descargardocentes':
                try:
                    profesores = Profesor.objects.select_related().all().order_by('id', '-persona__usuario__is_active',
                                                                                  'persona__apellido1',
                                                                                  'persona__apellido2',
                                                                                  'persona__nombres')
                    __author__ = 'Unemi'
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('plantilla_')
                    ws.set_column(0, 100, 60)

                    formatoceldagris = workbook.add_format(
                        {'align': 'center', 'border': 1, 'text_wrap': True, 'fg_color': '#B6BFC0'})

                    ws.write(0, 0, 'IDENTIFICACIÓN', formatoceldagris)
                    ws.write(0, 1, 'NOMBRES', formatoceldagris)
                    ws.write(0, 2, 'COORDINACIÓN', formatoceldagris)
                    ws.write(0, 3, 'TIPO', formatoceldagris)
                    ws.write(0, 4, 'CATEGORÍA', formatoceldagris)
                    ws.write(0, 5, 'DEDICACIÓN', formatoceldagris)
                    ws.write(0, 6, 'PERFIL', formatoceldagris)
                    ws.write(0, 7, 'TITULO 3ER NIVEL', formatoceldagris)
                    ws.write(0, 8, 'TITULO 4TO NIVEL', formatoceldagris)
                    ws.write(0, 9, 'CORREO', formatoceldagris)
                    ws.write(0, 10, 'CORREO INSTITUCIONAL', formatoceldagris)
                    ws.write(0, 11, 'TELÉFONO', formatoceldagris)
                    cont=1

                    for profesor in profesores:
                        ws.write(cont,0, str(profesor.persona.identificacion()))
                        ws.write(cont,1, str(profesor.persona))
                        ws.write(cont,2, str(profesor.coordinacion))
                        ws.write(cont,3, str(profesor.nivelcategoria if profesor.nivelcategoria else '' ))
                        ws.write(cont,4, str(profesor.categoria if profesor.categoria else ''))
                        ws.write(cont,5, str(profesor.dedicacion.nombre if profesor.dedicacion else ''))
                        ws.write(cont,6, str(profesor.activo))
                        ws.write(cont,7, str(profesor.persona.titulo_3er_nivel() if profesor.persona.titulo_3er_nivel() else ''))
                        ws.write(cont,8, str(profesor.persona.titulo_4to_nivel() if profesor.persona.titulo_4to_nivel() else ''))
                        ws.write(cont,9, str(profesor.persona.email if profesor.persona.email else ''))
                        ws.write(cont,10, str(profesor.persona.emailinst if profesor.persona.emailinst else ''))
                        ws.write(cont,11, str(profesor.persona.telefono if profesor.persona.telefono else ''))
                        cont+=1
                    workbook.close()
                    output.seek(0)
                    filename = 'reporte_docentes.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'descargardocenteshistorial':
                try:
                    profesores = Profesor.objects.select_related().filter(activo=True).order_by(
                                                                                  'persona__apellido1',
                                                                                  'persona__apellido2',
                                                                                  'persona__nombres')
                    __author__ = 'Unemi'
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('plantilla_')
                    ws.set_column(0, 100, 60)

                    formatoceldagris = workbook.add_format(
                        {'align': 'center', 'border': 1, 'text_wrap': True, 'fg_color': '#B6BFC0'})

                    ws.write(0, 0, 'IDENTIFICACIÓN', formatoceldagris)
                    ws.write(0, 1, 'NOMBRES', formatoceldagris)
                    ws.write(0, 2, 'UNIDAD ORGÁNICA', formatoceldagris)
                    ws.write(0, 3, 'GRADO', formatoceldagris)
                    ws.write(0, 4, 'MODALIDAD LABORAL', formatoceldagris)
                    ws.write(0, 5, 'CARGO', formatoceldagris)
                    ws.write(0, 6, 'FECHA', formatoceldagris)
                    ws.write(0, 7, 'CORREO', formatoceldagris)
                    ws.write(0, 8, 'CORREO INSTITUCIONAL', formatoceldagris)
                    ws.write(0, 9, 'TELÉFONO', formatoceldagris)
                    cont=1

                    for profesor in profesores:
                        distributivo = DistributivoPersonaHistorial.objects.filter(persona=profesor.persona)
                        for distri in distributivo:
                            ws.write(cont,0, str(distri.persona.identificacion()))
                            ws.write(cont,1, str(distri.persona))
                            ws.write(cont,2, str(distri.unidadorganica))
                            ws.write(cont,3, str(distri.grado ))
                            ws.write(cont,4, str(distri.modalidadlaboral))
                            ws.write(cont,5, str(distri.denominacionpuesto))
                            ws.write(cont,6, str(distri.fechahistorial))
                            ws.write(cont,7, str(distri.persona.email))
                            ws.write(cont,8, str(distri.persona.emailinst))
                            ws.write(cont,9, str(distri.persona.telefono))
                            cont+=1
                    workbook.close()
                    output.seek(0)
                    filename = 'reporte_docentes_historial.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass


            elif action == 'detalle_clasesvideo':
                try:
                    profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['title'] = u'Detalle clases sincrónicas y asincrónicas'
                    data['hoy'] = hoy = datetime.now().date()
                    listaasistencias = []
                    cursor = connections['default'].cursor()
                    sql = f"""
                            SELECT DISTINCT 
                                ten.codigoclase, ten.dia, ten.turno_id,
                                ten.inicio, ten.fin, ten.materia_id,
                                ten.tipohorario, ten.horario, ten.rangofecha,
                                ten.rangodia, sincronica.fecha AS sincronica, asincronica.fechaforo AS asincronica, 
                                asignatura, paralelo,
                                CASE 
                                    WHEN asincronica.idforomoodle IS NOT  NULL THEN asincronica.idforomoodle 
                                    ELSE sincronica.idforomoodle 
                                END  idforomoodle, ten.comienza, ten.termina,
                                nolaborables.fecha, nolaborables.observaciones, ten.nivelmalla,
                                ten.idnivelmalla, ten.idcarrera, ten.idcoordinacion,
                                ten.tipoprofesor_id,EXTRACT(week FROM ten.rangofecha::date) AS numerosemana,ten.tipoprofesor
                            FROM ( SELECT DISTINCT  
                                        cla.tipoprofesor_id,cla.id AS	codigoclase,
                                        cla.dia,cla.turno_id,cla.inicio,cla.fin,cla.materia_id, cla.tipohorario, 
                                        CASE WHEN cla.tipohorario IN(2,8)  THEN 2 WHEN cla.tipohorario in(7,9)  THEN 7 END AS horario,
                                        CURRENT_DATE + GENERATE_SERIES(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE ) AS rangofecha,
                                        EXTRACT (isodow  FROM  CURRENT_DATE + GENERATE_SERIES(cla.inicio- CURRENT_DATE, 
                                        cla.fin - CURRENT_DATE )) AS rangodia,asig.nombre AS asignatura, mate.paralelo AS paralelo,
                                        tur.comienza,tur.termina,nimalla.nombre AS nivelmalla,nimalla.id AS idnivelmalla,
                                        malla.carrera_id AS idcarrera,coorcar.coordinacion_id AS idcoordinacion,
                                        tipro.nombre AS tipoprofesor 
                                    FROM sga_clase cla , sga_materia mate,
                                     sga_asignaturamalla asimalla,sga_asignatura asig,
                                     sga_turno tur,sga_nivel niv,sga_nivelmalla nimalla,
                                     sga_malla malla,sga_carrera carre, 
                                     sga_coordinacion_carrera coorcar, 
                                     sga_tipoprofesor tipro 
                                    WHERE	
                                        cla.profesor_id={profesor.id} AND	
                                        cla.materia_id = mate.id AND mate.asignaturamalla_id = asimalla.id AND 
                                        asimalla.malla_id=malla.id AND asimalla.asignatura_id = asig.id AND	 
                                        cla.turno_id=tur.id AND asimalla.nivelmalla_id=nimalla.id AND	 
                                        malla.carrera_id=carre.id AND	 coorcar.carrera_id=carre.id AND 
                                        cla.tipohorario IN (8, 9, 2, 7) AND mate.nivel_id=niv.id AND	 
                                        cla.activo=True AND cla.tipoprofesor_id=tipro.id AND niv.periodo_id={periodo.id}) AS ten
                                LEFT JOIN(  SELECT 
                                                clas.id  clase_id, clas.materia_id,asi.fecha_creacion::timestamp::date AS fecha, clas.tipoprofesor_id,
                                                asi.fecha_creacion AS fecharegistro, asi.fechaforo AS fechaforo, asi.idforomoodle idforomoodle 
                                            FROM sga_clasesincronica asi, sga_clase clas 
                                            WHERE asi.clase_id=clas.id AND asi.status=true AND clas.profesor_id={profesor.id}) AS sincronica 
                                    ON (ten.rangofecha=fechaforo AND ten.horario=2 AND sincronica.materia_id=ten.materia_id  AND sincronica.tipoprofesor_id=ten.tipoprofesor_id)OR 
                                       (sincronica.materia_id=ten.materia_id AND sincronica.fechaforo=ten.rangofecha AND EXTRACT(dow from  sincronica.fechaforo)=ten.rangodia AND sincronica.tipoprofesor_id=ten.tipoprofesor_id)
                                LEFT JOIN(  SELECT   
                                                clas.id  clase_id,  clas.materia_id,asi.fechaforo,asi.idforomoodle, clas.tipoprofesor_id 
                                            FROM sga_claseasincronica asi, sga_clase clas 
                                            WHERE asi.clase_id=clas.id AND asi.status=true) AS asincronica 
                                    ON (asincronica.materia_id=ten.materia_id AND ten.rangofecha=asincronica.fechaforo AND	ten.horario=2  AND asincronica.tipoprofesor_id=ten.tipoprofesor_id)OR 
                                        (asincronica.materia_id=ten.materia_id  AND	 asincronica.fechaforo=ten.rangofecha AND  EXTRACT(dow from  asincronica.fechaforo)=ten.rangodia AND asincronica.tipoprofesor_id=ten.tipoprofesor_id)        
                                LEFT JOIN (SELECT 
                                            nolab.observaciones, nolab.fecha 
                                            FROM sga_diasnolaborable nolab 
                                            WHERE nolab.periodo_id={periodo.id}) AS nolaborables ON nolaborables.fecha = ten.rangofecha   
                            WHERE 
                                ten.dia=ten.rangodia AND 
                                ten.rangofecha <'{hoy}'
                            ORDER BY ten.rangofecha,materia_id,ten.turno_id,tipohorario                
                            """
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    totalsincronica = 0
                    totalasincronica = 0
                    totalplansincronica = 0
                    totalplanasincronica = 0
                    for cuentamarcadas in results:
                        materia = None
                        moodle_url = None
                        if Materia.objects.values("id").filter(pk=cuentamarcadas[5]).exists():
                            materia = Materia.objects.get(pk=cuentamarcadas[5])
                            mi_coordinacion = materia.coordinacion()
                            if mi_coordinacion:
                                if mi_coordinacion.id == 9:
                                    moodle_url = f'https://aulanivelacion.unemi.edu.ec/mod/url/view.php?id={cuentamarcadas[14]}'
                                elif mi_coordinacion.id in [1, 2, 3, 4, 5, 12]:
                                    if materia.asignaturamalla.malla.modalidad_id in [1, 2]:
                                        moodle_url = f'https://aulagradoa.unemi.edu.ec/mod/url/view.php?id={cuentamarcadas[14]}'
                                    elif materia.asignaturamalla.malla.modalidad_id == 3:
                                        moodle_url = f'https://aulagradob.unemi.edu.ec/mod/url/view.php?id={cuentamarcadas[14]}'
                                    else:
                                        moodle_url = f'https://aulagrado.unemi.edu.ec/mod/url/view.php?id={cuentamarcadas[14]}'
                        sinasistencia = periodo.tiene_dias_nolaborables(fecha=cuentamarcadas[8], materia=materia)
                        dianolaborable = periodo.dias_nolaborables(fecha=cuentamarcadas[8], materia=materia)
                        hoy = datetime.now().date()
                        codigoclase = cuentamarcadas[0]
                        clase = Clase.objects.get(pk=codigoclase)
                        clases = Clase.objects.filter(materia=clase.materia, dia=clase.dia, tipoprofesor=clase.tipoprofesor, tipohorario=clase.tipohorario)
                        if clases.exists():
                            clases = clases.order_by('-id')
                            clasetrue = clases.filter(inicio__lte=hoy, fin__gte=hoy)
                            if clasetrue.exists():
                                clasetrue = clasetrue.order_by('-turno__comienza')[0]
                            else:
                                clasetrue = clases.order_by('-turno__comienza')[0]
                            codigoclase = clasetrue.id
                        # sinasistencia = False
                        # if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22],carrera_id=cuentamarcadas[21],nivelmalla_id=cuentamarcadas[20], status=True).exists():
                        #     if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22],carrera_id=cuentamarcadas[21],nivelmalla_id=cuentamarcadas[20], fecha=cuentamarcadas[8], status=True).exists():
                        #         sinasistencia = True
                        # else:
                        #     if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, status=True).exists():
                        #         if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                        #             sinasistencia = True
                        #     else:
                        #         if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                        #             if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                        #                 sinasistencia = True
                        #         else:
                        #             if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                        #                 if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                        #                     sinasistencia = True
                        listaasistencias.append(
                            [codigoclase, cuentamarcadas[1], cuentamarcadas[2], cuentamarcadas[3],
                             cuentamarcadas[4], cuentamarcadas[5], cuentamarcadas[6], cuentamarcadas[7],
                             cuentamarcadas[8], cuentamarcadas[9], cuentamarcadas[10], cuentamarcadas[11],
                             cuentamarcadas[12], cuentamarcadas[13], cuentamarcadas[14], cuentamarcadas[15],
                             cuentamarcadas[16], cuentamarcadas[17], cuentamarcadas[18], cuentamarcadas[19],
                             sinasistencia, cuentamarcadas[24], cuentamarcadas[25], dianolaborable,
                             moodle_url, clase])

                        if cuentamarcadas[7] == 2:
                            totalsincronica += 1
                        if cuentamarcadas[7] == 7:
                            totalasincronica += 1
                        # if cuentamarcadas[10]:
                        #     totalplansincronica += 1
                        totalplansincronica += 1
                        if cuentamarcadas[11]:
                            totalplanasincronica += 1
                    data['listaasistencias'] = listaasistencias
                    data['totalsincronica'] = totalsincronica
                    data['totalasincronica'] = totalasincronica
                    data['totalplansincronica'] = totalplansincronica
                    data['totalplanasincronica'] = totalplanasincronica
                    # data['procentajesincronica'] = (totalplansincronica * 100) / totalsincronica
                    # data['procentajeasincronica'] = (totalplanasincronica * 100) / totalasincronica
                    data['profesor'] = profesor
                    # profesoresingresar = [1459,1450]

                    # puedeingresar = False
                    # if profesor.id in profesoresingresar:
                    #     puedeingresar = True
                    #     fechainiplan = '2020-11-28'
                    #     fechafinplan = '2021-03-05'
                    # else:
                    #     fechainiplan = '2021-01-14'
                    #     fechafinplan = '2021-01-14'
                    # data['puedeingresar'] = puedeingresar
                    # data['fechainicio'] = date(int(fechainiplan[0:4]), int(fechainiplan[5:7]), int(fechainiplan[8:10]))
                    # data['fechafinal'] = date(int(fechafinplan[0:4]), int(fechafinplan[5:7]), int(fechafinplan[8:10]))
                    return render(request, "docentes/detalle_clasesvideo.html", data)
                except Exception as ex:
                    pass

            elif action == 'configurarregistroasistencia':
                try:

                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['profesormateria'] = profesormateria = ProfesorMateria.objects.get(pk=id)
                    data['title'] = u'Configuración Registro de Asistencia %s' %profesormateria.materia
                    data['form'] = ConfigurarRegistroAsistenciaForm(initial=model_to_dict(profesormateria))
                    data['action'] = action
                    template = get_template("docentes/modal/formconfigurarregistroasistencia.html")
                    return JsonResponse({"result": True, 'data': template.render(data), 'title': data['title']})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al editar los datos."})

            if action == 'listadofirmas':
                try:
                    data['title'] = u'Persona'
                    data['personafirma'] = personafirma = Persona.objects.get(pk=int(request.GET['idpersona']))
                    data['listadofirma'] = FirmaPersona.objects.filter(persona=personafirma, status=True)
                    d = datetime.now()
                    data['horasegundo'] = d.strftime('%Y%m%d_%H%M%S')
                    return render(request, "docentes/listadofirmas.html", data)
                except Exception as ex:
                    pass

            elif action == 'adicionarpersonafirma':
                try:
                    data['title'] = u'Adicionar firma'
                    data['personafirma'] = Persona.objects.get(pk=int(request.GET['idpersona']))
                    form = FirmaPersonaForm()
                    data['form'] = form
                    return render(request, "docentes/adicionarpersonafirma.html", data)
                except Exception as ex:
                    pass

            elif action == 'adicionarpersonafirmamodal':
                try:
                    data['id'] = request.GET['id']
                    data['personafirma'] = Persona.objects.get(pk=int(request.GET['id']))
                    form = FirmaPersonaForm()
                    data['form'] = form
                    template = get_template('docentes/modal/formModalAccionesDocentes.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'loadDetailClassSynchronousAsynchronous':
                try:
                    if not 'id' in request.GET:
                        raise NameError(u"No se encontro parametro de lección")
                    if not 'num_semana' in request.GET:
                        raise NameError(u"Parametro de numero de la semana de la clase no encontrado")
                    clase = Clase.objects.filter(pk=int(encrypt(request.GET['id']))).first()
                    numero_semana = request.GET['num_semana']
                    if clase is None:
                        raise NameError(u"Lección/Clase no encontrada")

                    clases_sincronicas = clase.clasesincronica_set.filter(numerosemana=numero_semana, status=True)
                    clases_asincronicas = clase.claseasincronica_set.filter(numerosemana=numero_semana, status=True)

                    data['clase'] = clase
                    data['num_semana'] = numero_semana
                    data['title'] = u'Clase %s'%(clase)
                    data['clases_sincronicas'] = clases_sincronicas
                    data['clases_asincronicas'] = clases_asincronicas
                    template = get_template(f"docentes/modal/listadoclase_sincronicas_asincronicas.html")
                    json_content = template.render(data, request=request)
                    return JsonResponse({"result": "ok", 'html': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            return HttpResponseRedirect(request.path)

        else:
            try:
                search = None
                ids = None
                perfil = None
                activodistributivo = None
                url_vars = ''
                profesores = Profesor.objects.select_related().all().order_by('id', '-persona__usuario__is_active', 'persona__apellido1', 'persona__apellido2', 'persona__nombres')
                if 's' in request.GET:
                    search = request.GET['s']
                    ss = search.split(' ')
                    if len(ss) == 1:
                        profesores = profesores.filter(Q(persona__nombres__icontains=search) |
                                                       Q(persona__apellido1__icontains=search) |
                                                       Q(persona__apellido2__icontains=search) |
                                                       Q(persona__cedula__icontains=search) |
                                                       Q(persona__pasaporte__icontains=search)).distinct().order_by('-persona__usuario__is_active', 'persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        profesores = profesores.filter(Q(persona__apellido1__icontains=ss[0]) &
                                                       Q(persona__apellido2__icontains=ss[1])).distinct().order_by('-persona__usuario__is_active', 'persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    url_vars += f"&s={search}"
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    profesores = profesores.filter(id=ids)
                    url_vars += f"&id={ids}"

                if 'perfil' in request.GET:
                    perfil = request.GET['perfil']
                    if perfil == '1':
                        profesores = profesores.filter(activo=True).distinct()
                    elif perfil == '2':
                        profesores = profesores.filter(activo=False).distinct()
                    url_vars += f"&perfil={perfil}"
                if 'activodistributivo' in request.GET:
                    activodistributivo = request.GET['activodistributivo']
                    if not activodistributivo == '0':
                        if activodistributivo == '1':
                            url_vars += f"&activodistributivo={activodistributivo}"
                            dis = ProfesorDistributivoHoras.objects.values_list('profesor__id', flat=True).filter(status=True, activo=True)
                        elif activodistributivo == '2':
                            url_vars += f"&activodistributivo={activodistributivo}"
                            dis = ProfesorDistributivoHoras.objects.values_list('profesor__id').filter(status=True, activo=False)
                        profesores = profesores.filter(id__in =dis).distinct()

                paging = MiPaginador(profesores, 27)
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
                data['reporte_1'] = obtener_reporte('hoja_vida_sagest')
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['perfil'] = perfil if perfil else ""
                data['activodistributivo'] = activodistributivo if activodistributivo else ""
                data['profesores'] = page.object_list
                data['alum'] = 0
                data['utiliza_ficha_medica'] = UTILIZA_FICHA_MEDICA
                data['reporte_0'] = obtener_reporte('listado_clases_abiertas')
                data['url_vars'] = url_vars
                return render(request, "docentes/view.html", data)
            except Exception as ex:
                pass
