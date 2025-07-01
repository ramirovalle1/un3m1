# -*- coding: UTF-8 -*-
import random
from datetime import datetime
from _decimal import Decimal
from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required
from django.db import transaction,connections, connection
from django.http import JsonResponse, request
from django.http.response import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from decorators import secure_module, last_access
from django.template.context import Context
from django.template.loader import get_template
import xlwt
from django.core.paginator import Paginator
from itertools import chain
from xlwt import *
from sagest.models import Rubro, TipoOtroRubro
from sga.commonviews import adduserdata
from sga.forms import VirtualIncidenteForm, VirtualIncidenteAsignadoForm, EditarSoporteInscripcionForm, \
    ReporteSoporteUsuarioForm, DetalleReporteSoporteForm, TipoActividadVirtualForm, EditDetalleReporteSoporteForm, \
    DocumentoEntregadoForm, AnexosReporteUsuarioVirtualForm, VirtualIncidenteMasivoForm
from sga.funciones import log, generar_nombre, MiPaginador, querymysqlsakai, convertir_fecha, convertir_fecha_hora, \
    resetear_clave_admision_manual,resetear_clave_admision_ldap, convertir_fecha_invertida, querymysqlconsulta, null_to_decimal, resetear_clave
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import VirtualSoporteUsuario, VirtualSoporteUsuarioIncidentes, VirtualSoporteUsuarioInscripcion, \
    VirtualCausaIncidente, VirtualIncidenteAsignado, VirtualSoporteAsignado, Inscripcion, VirtualSoporteUsuarioProfesor, \
    Persona, miinstitucion, CUENTAS_CORREOS, Materia, ActividadesSakaiAlumno, ReporteSoporteVirtual, \
    DetalleReporteSoporteVirtual, TipoActividadVirtual, DocumentoEntregado, AnexosReporteUsuarioVirtual, Carrera, \
    MateriaAsignada, HorarioVirtual, Matricula, NivelMalla, Clase, Sesion, PlanificacionClaseSilabo, Silabo, \
    EjeFormativo, AsignaturaMalla, PeriodoGrupoSocioEconomico, TIPO_RECURSOS, TIPO_LINK, TIPO_ACTIVIDAD
from sga.templatetags.sga_extras import encrypt
from settings import EMAIL_DOMAIN, PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD, RUBRO_ARANCEL, RUBRO_MATRICULA
from sga.tasks import send_html_mail, conectar_cuenta


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['periodo'] = periodo = request.session['periodo']
    data['inicio'] = str(periodo.inicio.day)+"-"+str(periodo.inicio.month)+"-"+str(periodo.inicio.year)
    data['hoy'] = str(datetime.now().date().day)+"-"+str(datetime.now().date().month)+"-"+str(datetime.now().date().year)
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'virtual_incidente':
                try:
                    if 'archivo' in request.FILES:
                        d = request.FILES['archivo']
                        if d.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                    form = VirtualIncidenteForm(request.POST)
                    if form.is_valid():
                        incidente = VirtualSoporteUsuarioIncidentes.objects.get(pk=int(encrypt(request.POST['id'])))
                        if form.cleaned_data['actualizar']:
                            if incidente.soporteiniscripcion:
                                actualizapersona = incidente.soporteiniscripcion.matricula.inscripcion.persona
                            else:
                                actualizapersona = incidente.soporteprofesor.profesor.persona
                            actualizapersona.email = form.cleaned_data['email']
                            actualizapersona.telefono = form.cleaned_data['telefono']
                            actualizapersona.telefono2 = form.cleaned_data['telefono2']
                            actualizapersona.telefono_conv = form.cleaned_data['telefono_conv']
                            actualizapersona.pais = form.cleaned_data['pais']
                            actualizapersona.provincia = form.cleaned_data['provincia']
                            actualizapersona.canton = form.cleaned_data['canton']
                            actualizapersona.parroquia = form.cleaned_data['parroquia']
                            actualizapersona.sector = form.cleaned_data['sector']
                            actualizapersona.direccion = form.cleaned_data['direccion']
                            actualizapersona.direccion2 = form.cleaned_data['direccion2']
                            actualizapersona.num_direccion = form.cleaned_data['num_direccion']
                            actualizapersona.save(request)
                            # if incidente.soporteiniscripcion:
                            #     if periodo.usa_sakai and periodo.pre_virtual:
                            #         sql ="update SAKAI_USER set EMAIL= '"+ actualizapersona.email +"',EMAIL_LC= '"+ actualizapersona.email +"' where USER_ID in(select USER_ID from SAKAI_USER_ID_MAP where EID='"+ incidente.soporteiniscripcion.matricula.inscripcion.persona.cedula +"')"
                            #         querymysqlsakai(sql)
                            #     elif periodo.usa_moodle and periodo.pre_virtual:
                            #         data['admision'] = admision = not incidente.soporteiniscripcion.matricula.inscripcion.mi_coordinacion().id == 9
                            #         if not admision:
                            #             cursor = connections['db_moodle_virtual'].cursor()
                            #         else:
                            #             cursor=connections['db_moodle_semestre'].cursor()
                            #         query = "SELECT * FROM mooc_user WHERE username='" + str(actualizapersona.usuario.username) + "'"
                            #         cursor.execute(query)
                            #         resultado = cursor.fetchall()
                            #         if resultado.__len__() == 0:
                            #             return JsonResponse({"result": "bad", "mensaje": u"El usuario no se encuentra registrado en el campus virtual"})
                            #         else:
                            #             sql_update_correo="update mooc_user set email='"+str(actualizapersona.email)+"' where username='"+str(actualizapersona.usuario.username)+"'"
                            #             cursor.execute(sql_update_correo)

                        if incidente.soporteiniscripcion:
                            if form.cleaned_data['desertaonline'] == True and  not incidente.soporteiniscripcion.matricula.inscripcion.desertaonline:
                                incidente.soporteiniscripcion.matricula.inscripcion.desertaonline = True
                                incidente.soporteiniscripcion.matricula.inscripcion.observaciondesertaonline = form.cleaned_data['planaccion']
                                incidente.soporteiniscripcion.matricula.inscripcion.save()
                        if form.cleaned_data['estado'] == '2':
                            incidente.fecha_finalizaticket = datetime.now()
                            incidente.causaincidente = form.cleaned_data['causaincidente']
                            incidente.estado = int(form.cleaned_data['estado'])
                            incidente.save(request)
                            detalleincidente = incidente.virtualincidenteasignado_set.filter(status=True).order_by('-id')[0]
                            detalleincidente.planaccion = form.cleaned_data['planaccion']
                            detalleincidente.estado = int(form.cleaned_data['estado'])
                            detalleincidente.fecha_finalizaasignacion = datetime.now()
                            detalleincidente.finalizado = True
                            detalleincidente.save(request)
                            if incidente.soporteiniscripcion:
                                incidente.envio_correo_incidente(20, request)
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("evidenciaincidente", newfile._name)
                                detalleincidente.archivo = newfile
                                detalleincidente.save(request)
                        if form.cleaned_data['estado'] == '3':
                            incidente.causaincidente = form.cleaned_data['causaincidente']
                            incidente.estado = int(form.cleaned_data['estado'])
                            incidente.save(request)
                            detalleincidente = incidente.virtualincidenteasignado_set.filter(status=True).order_by('-id')[0]
                            detalleincidente.planaccion = form.cleaned_data['planaccion']
                            detalleincidente.fecha_finalizaasignacion = datetime.now()
                            detalleincidente.save(request)
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("evidenciaincidente", newfile._name)
                                detalleincidente.archivo = newfile
                                detalleincidente.save(request)
                            incidenteasignado = VirtualIncidenteAsignado(incidente=incidente,
                                                                         soporteusuarioasignado=form.cleaned_data['personaasignar'],
                                                                         fecha_creaasignacion=datetime.now(),
                                                                         estado=3
                                                                         )
                            incidenteasignado.save(request)

                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'tipoprioridad':
                try:
                    causa = VirtualCausaIncidente.objects.get(pk=request.POST['idcausa'])
                    return JsonResponse({"result": "ok", "prioridad": causa.prioridad})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'listaincidente':
                try:
                    esTutor=False
                    if 'esTutor' in request.POST:
                        esTutor = True if request.POST['esTutor'] == 'true' else False
                    if esTutor:
                        data['soporteprofesor'] = soporteprofesor = VirtualSoporteUsuarioProfesor.objects.get(pk=int(request.POST['id']))
                        data['incidente'] = soporteprofesor.virtualsoporteusuarioincidentes_set.filter(status=True).order_by('fecha_creaticket')
                    else:
                        data['soporteusuario'] = soporteusuario = VirtualSoporteUsuarioInscripcion.objects.get(pk=int(request.POST['id']))
                        data['incidente'] = soporteusuario.virtualsoporteusuarioincidentes_set.filter(status=True).order_by('fecha_creaticket')
                    template = get_template("virtual_soporte_online/listaincidente.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'detalleincidente':
                try:
                    data['incidente'] = incidente = VirtualSoporteUsuarioIncidentes.objects.get(pk=int(request.POST['id']))
                    data['detalle'] = incidente.virtualincidenteasignado_set.filter(status=True).order_by('id')
                    template = get_template("virtual_soporte_online/detalleincidente.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'resetear_clave_admision_virtual':
                try:
                    inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                    if inscripcion.carrera.mi_coordinacion2()==9:
                        resetear_clave_admision_ldap(inscripcion.persona)
                        # from moodle import moodle
                        # bestudiante = moodle.BuscarUsuario(periodo, 2, 'idnumber', inscripcion.persona.identificacion())
                        # if not bestudiante:
                        #     bestudiante = moodle.BuscarUsuario(periodo, 2, 'idnumber', inscripcion.persona.identificacion())
                        # if bestudiante['users']:
                        #     if 'auth' in bestudiante['users'][0]:
                        #         auth = bestudiante['users'][0]['auth']
                        #         if auth=='ldap':
                        #             resetear_clave_admision_ldap(inscripcion.persona)
                        #         else:
                        #             resetear_clave_admision_manual(inscripcion.persona)
                    else:
                        resetear_clave(inscripcion.persona)
                    log(u'Reseteo clave de inscripcion virtual: %s' % inscripcion, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editarsoporteinscripcion':
                try:
                    form = EditarSoporteInscripcionForm(request.POST)
                    if form.is_valid():
                        inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
                        inscripcion.persona.email = form.cleaned_data['email']
                        inscripcion.persona.telefono = form.cleaned_data['telefono']
                        inscripcion.persona.telefono2 = form.cleaned_data['telefono2']
                        inscripcion.persona.telefono_conv = form.cleaned_data['telefono_conv']
                        inscripcion.persona.pais = form.cleaned_data['pais']
                        inscripcion.persona.provincia = form.cleaned_data['provincia']
                        inscripcion.persona.canton = form.cleaned_data['canton']
                        inscripcion.persona.parroquia = form.cleaned_data['parroquia']
                        inscripcion.persona.sector = form.cleaned_data['sector']
                        inscripcion.persona.direccion = form.cleaned_data['direccion']
                        inscripcion.persona.direccion2 = form.cleaned_data['direccion2']
                        inscripcion.persona.num_direccion = form.cleaned_data['num_direccion']
                        inscripcion.persona.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'ver_horario':
                try:
                    data = {}
                    resultados=None
                    data['inscripcion']=inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                    try:
                        sql = "select * from horario h where h.cedula='" + str(inscripcion.persona.identificacion()) + "'"
                        resultados = querymysqlconsulta(sql, True)
                    except Exception as ex:
                        pass
                    data['resultados'] = resultados
                    template = get_template("virtual_soporte_online/ver_horario.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == "enviar_horario":
                try:
                    if VirtualSoporteUsuario.objects.filter(persona=persona, activo=True, status=True).exists():
                        soporteusuario = VirtualSoporteUsuario.objects.get(persona=persona, activo=True)
                    else:
                        return HttpResponseRedirect("/?info=No tiene asignado usuarios soporte online.")
                    # sql = "select distinct h.cedula from horario h where enviohorario=0"
                    # resultados = querymysqlconsulta(sql, True)
                    # lista = []
                    # for x in resultados:
                    #     lista.append(x[0])
                    # listapersonainscripcion = VirtualSoporteUsuarioInscripcion.objects.filter(Q(inscripcion__persona__cedula__in =lista) | Q(inscripcion__persona__pasaporte__in =lista),
                    #                                                                           inscripcion__modalidad_id=3,
                    #                                                                           inscripcion__envioemail=False,
                    #                                                                           soporteusuario=soporteusuario, inscripcion__id=51006).order_by('inscripcion__persona__apellido1','inscripcion__persona__apellido2')[:10]

                    listapersonainscripcion = VirtualSoporteUsuarioInscripcion.objects.filter(
                        inscripcion__modalidad_id=3,
                        inscripcion__envioemail=False,
                        soporteusuario=soporteusuario).order_by('inscripcion__persona__apellido1',
                                                                'inscripcion__persona__apellido2')[:10]
                    listacorreos = [8,9,10,11,12,13,20]
                    cuenta = random.choice(listacorreos)
                    for personainscripcion in listapersonainscripcion:
                        # lista = ['jplacesc@unemi.edu.ec']
                        lista = []
                        lista = personainscripcion.inscripcion.persona.lista_emails()
                        if lista:
                            sql = "select * from horario h where h.cedula='" + str(personainscripcion.inscripcion.persona.identificacion()) + "'"
                            resultados = querymysqlconsulta(sql, True)
                            if resultados:
                                try:
                                    sql = "update horario set enviohorario=1 where cedula='" + str(personainscripcion.inscripcion.persona.identificacion()) + "'"
                                    querymysqlconsulta(sql)
                                except Exception as ex:
                                    pass

                                personainscripcion.inscripcion.envioemail = True
                                if request:
                                    personainscripcion.inscripcion.save(request)
                                else:
                                    personainscripcion.inscripcion.save()
                                nombrecorto = personainscripcion.inscripcion.persona.nombres.split(" ")
                                send_html_mail("Mensaje desde el Campus Virtual UNEMI",
                                               "emails/envio_horario_adm_virtual.html",
                                               {'sistema': u'Horario de examenes',
                                                'fecha': datetime.now().date,
                                                'nombrecorto': nombrecorto[0],
                                                'persona': personainscripcion.inscripcion, 'resultados': resultados,
                                                't': miinstitucion(),
                                                'dominio': EMAIL_DOMAIN}, lista, [],
                                               cuenta=CUENTAS_CORREOS[cuenta][1])

                        # personainscripcion.inscripcion.envio_correo_horario_admision(20, request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    pass

            elif action == "enviar_horario_estudiante":
                try:
                    inscripciones = Inscripcion.objects.filter(modalidad_id=3,envioemail=False, id=request.POST['id'])
                    listacorreos = [8,9,10,11,12,13,20]
                    cuenta = random.choice(listacorreos)
                    for inscripcion in inscripciones:
                        # lista = ['jplacesc@unemi.edu.ec']
                        lista = []
                        lista = inscripcion.persona.lista_emails()
                        if lista:
                            sql = "select * from horario h where h.cedula='" + str(inscripcion.persona.identificacion()) + "'"
                            resultados = querymysqlconsulta(sql, True)
                            if resultados:
                                try:
                                    sql = "update horario set enviohorario=1 where cedula='" + str(inscripcion.persona.identificacion()) + "'"
                                    querymysqlconsulta(sql)
                                except Exception as ex:
                                    pass

                                inscripcion.envioemail = True
                                if request:
                                    inscripcion.save(request)
                                else:
                                    inscripcion.save()
                                nombrecorto = inscripcion.persona.nombres.split(" ")
                                send_html_mail("Mensaje desde el Campus Virtual UNEMI",
                                               "emails/envio_horario_adm_virtual.html",
                                               {'sistema': u'Horario de examenes',
                                                'fecha': datetime.now().date,
                                                'nombrecorto': nombrecorto[0],
                                                'persona': inscripcion, 'resultados': resultados,
                                                't': miinstitucion(),
                                                'dominio': EMAIL_DOMAIN}, lista, [],
                                               cuenta=CUENTAS_CORREOS[cuenta][1])

                        # personainscripcion.inscripcion.envio_correo_horario_admision(20, request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    pass

            elif action == "notificar_pendiente":
                try:
                    inscripcion = Inscripcion.objects.get(pk=int(request.POST['idinscripcionid']))
                    if request.POST['actualiza'] == '1':
                        inscripcion.persona.email = request.POST['correo']
                        inscripcion.persona.save(request)

                    actividad = ActividadesSakaiAlumno.objects.filter(pk=request.POST['ida'])[0]
                    # email = request.POST['correo']
                    # inscripciones = Inscripcion.objects.filter(modalidad_id=3, id=request.POST['id'])
                    cuenta = 20
                    # lista = ['yarmijosp@unemi.edu.ec', 'farevaloc@unemi.edu.ec', 'felipe-arevalo@hotmail.com',
                    #          'felipe-arevalo@hotmail.com']
                    lista = []
                    lista = actividad.inscripcion.persona.lista_emails()

                    nombrecorto = actividad.inscripcion.persona.nombres.split(" ")
                    send_html_mail("Mensaje desde el Campus Virtual UNEMI",
                                   "emails/notificacion_actividad_pendiente.html",
                                   {'sistema': u'Horario de examenes',
                                    'fecha': datetime.now().date,
                                    'nombrecorto': nombrecorto[0],
                                    'persona': actividad.inscripcion, 'actividad': actividad,"usuario":persona.usuario.username,
                                    't': miinstitucion(),
                                    'dominio': EMAIL_DOMAIN}, lista, [],
                                   cuenta=CUENTAS_CORREOS[cuenta][1])

                    actividad.total_notificacion()


                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    pass

            elif action == "notificar_general_pendientes":
                try:
                    inscripcion = Inscripcion.objects.get(pk=int(request.POST['idinscripcionid']))
                    if request.POST['actualiza'] == '1':
                        inscripcion.persona.email = request.POST['correo']
                        inscripcion.persona.save(request)
                    cuenta = 20
                    lista = inscripcion.persona.lista_emails()
                    lista.append(persona.emailinst)
                    nombrecorto = inscripcion.persona.nombres.split(" ")
                    send_html_mail("Mensaje desde el Campus Virtual UNEMI","emails/notificar_general_pendientes.html",
                                   {'sistema': u'Horario de examenes',
                                    'fecha': datetime.now().date,
                                    'nombrecorto': nombrecorto[0],
                                    'periodo':periodo,
                                    'fini': request.POST['fini'],
                                    'ffin':request.POST['ffin'],
                                    'inscripcion': inscripcion, "usuario":persona.usuario.username,
                                    't': miinstitucion(),
                                    'dominio': EMAIL_DOMAIN}, lista, [],
                                   cuenta=CUENTAS_CORREOS[cuenta][1])
                    for materia in inscripcion.materias(periodo):
                        if inscripcion.actividades_pendientes_asignatura(materia.materia,request.POST['fini'],request.POST['ffin']):
                            for actividad in inscripcion.actividades_pendientes_asignatura(materia.materia,request.POST['fini'],request.POST['ffin']):
                                actividad.notificado = actividad.total_notificacion()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    pass

            if action == 'addreporte':
                try:
                    form = ReporteSoporteUsuarioForm(request.POST)
                    soporteusuario = VirtualSoporteUsuario.objects.get(persona=persona, activo=True)
                    if form.is_valid():
                        if ReporteSoporteVirtual.objects.filter(numeroinforme=form.cleaned_data['numeroreporte'],semestre=form.cleaned_data['semestre']).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe el reporte en el semestre especificado"})
                        reporte = ReporteSoporteVirtual(soporteusuario=soporteusuario,
                            numeroinforme=form.cleaned_data['numeroreporte'],
                            semestre=form.cleaned_data['semestre'],
                            fechaentrega=form.cleaned_data['fechaentrega'],
                            horaentrega=form.cleaned_data['horaentrega'],
                            fechaelaboracion=form.cleaned_data['fechaelaboracion'],
                            horaelaboracion=form.cleaned_data['horaelaboracion'],
                            objetivo=form.cleaned_data['objetivo'])
                        reporte.save()
                        log(u'Agrego un nuevo reporte virtual: %s' % reporte, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'addactividad':
                try:
                    form = DetalleReporteSoporteForm(request.POST)
                    reporte = ReporteSoporteVirtual.objects.get(pk=int(request.POST['id_reporte']))
                    tipoactividad = TipoActividadVirtual.objects.get(pk=int(request.POST['tipoactividad']))
                    if form.is_valid():
                        detalle = DetalleReporteSoporteVirtual(reporte=reporte,
                                                               fechaactividad=form.cleaned_data['fechaactividad'],
                                                               tipoactividad=tipoactividad,
                                                               tiposistema='',
                                                               nombreactividad=form.cleaned_data['nombreactividad']
                                                               )
                        detalle.save()
                        log(u'Agrego una nueva actividad virtual: %s' % detalle, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'adddocumento':
                try:
                    form = DocumentoEntregadoForm(request.POST)
                    reporte = ReporteSoporteVirtual.objects.get(pk=int(request.POST['id_reporte']))
                    if form.is_valid():
                        documento = DocumentoEntregado(reporte=reporte,
                            nombredocumento=form.cleaned_data['nombredocumento'])
                        documento.save()
                        log(u'Agrego una nuevo documento: %s' % documento, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'addtipoactividad':
                try:
                    form = TipoActividadVirtualForm(request.POST)
                    if form.is_valid():
                        if not TipoActividadVirtual.objects.filter(titulo=form.cleaned_data['titulo']).exists():
                            tipo = TipoActividadVirtual(titulo=form.cleaned_data['titulo'])
                            tipo.save(request)
                            log(u'Agrego una nuevo tipo de actividad: %s' % tipo, request, "add")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe este tipo de actividad"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'addanexo':
                try:
                    documento = DocumentoEntregado.objects.get(pk=int(request.POST['id_documento']))
                    form = AnexosReporteUsuarioVirtualForm(request.POST, request.FILES)
                    if form.is_valid():
                        newfile = request.FILES['anexo']
                        newfile._name = generar_nombre("anexo_", newfile._name)
                        anexo = AnexosReporteUsuarioVirtual(documento=documento,
                                                            anexo=newfile,
                                                            tituloanexo=form.cleaned_data['tituloanexo'],
                                                            )
                        anexo.save()
                        log(u'Agrego una nuevo anexo cirtual: %s' % anexo, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"La imagen seleccionada no cumple los requisitos, de tamaño o formato o hubo un error al guardar fichero."})

            if action == 'editreporte':
                try:
                    reporte = ReporteSoporteVirtual.objects.get(pk=int(request.POST['id']))
                    form = ReporteSoporteUsuarioForm(request.POST)
                    if form.is_valid():
                        reporte.numeroinforme = form.cleaned_data['numeroreporte']
                        reporte.semestre = form.cleaned_data['semestre']
                        reporte.fechaelaboracion = form.cleaned_data['fechaelaboracion']
                        reporte.fechaentrega = form.cleaned_data['fechaentrega']
                        reporte.horaentrega = form.cleaned_data['horaentrega']
                        reporte.horaelaboracion = form.cleaned_data['horaelaboracion']
                        reporte.objetivo = form.cleaned_data['objetivo']
                        reporte.save()
                        log(u'Editar reporte virtual: %s' % reporte, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editactividad':
                try:
                    actividad = DetalleReporteSoporteVirtual.objects.get(pk=int(request.POST['id']))
                    form = EditDetalleReporteSoporteForm(request.POST)
                    if form.is_valid():
                        actividad.tipoactividad = form.cleaned_data['tipoactividad']
                        actividad.nombreactividad = form.cleaned_data['nombreactividad']
                        actividad.fechaactividad = form.cleaned_data['fechaactividad']
                        actividad.save()
                        log(u'Editar actividad virtual: %s' % actividad, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editdocumento':
                try:
                    documento = DocumentoEntregado.objects.get(pk=int(request.POST['id']))
                    form = DocumentoEntregadoForm(request.POST)
                    if form.is_valid():
                        documento.nombredocumento = form.cleaned_data['nombredocumento']
                        documento.save()
                        log(u'Editar documento virtual: %s' % documento, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'edittipoactividad':
                try:
                    actividad = TipoActividadVirtual.objects.get(pk=int(request.POST['id']))
                    form = TipoActividadVirtualForm(request.POST)
                    if form.is_valid():
                        actividad.titulo = form.cleaned_data['titulo']
                        actividad.save()
                        log(u'Editar tipo de actividad virtual: %s' % actividad, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'delactividad':
                try:
                    actividad = DetalleReporteSoporteVirtual.objects.get(pk=int(request.POST['id']))
                    actividad.delete()
                    log(u'Elimino actividad virtual: %s' % actividad, request, "del")
                    return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente.."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'deltipoactividad':
                try:
                    actividad = TipoActividadVirtual.objects.get(pk=int(request.POST['id']))
                    actividad.delete()
                    log(u'Elimino tipo de actividad virtual: %s' % actividad, request, "del")
                    return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente.."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'deldocumento':
                try:
                    data['documento'] = documento = DocumentoEntregado.objects.get(pk=int(request.POST['id']))
                    documento.delete()
                    log(u'Elimino documento virtual: %s' % documento, request, "del")
                    return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente.."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'delanexo':
                try:
                    data['anexo'] = anexo = AnexosReporteUsuarioVirtual.objects.get(pk=int(request.POST['id']))
                    data['documento'] = anexo.documento
                    anexo.delete()
                    log(u'Elimino anexo virtual: %s' % anexo, request, "del")
                    return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente.."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'generar_ticket_masivo':
                try:
                    carrera = Carrera.objects.get(pk=int(request.POST['carrera']))
                    nivel = 0
                    if 'nivel'  in request.POST:
                        nivel = int(request.POST['nivel'])
                    form = VirtualIncidenteMasivoForm(request.POST)
                    if form.is_valid():
                        if VirtualSoporteUsuario.objects.filter(persona=persona, activo=True, status=True).exists():
                            soporteusuario = VirtualSoporteUsuario.objects.get(persona=persona, activo=True)
                        else:
                            return HttpResponseRedirect("/?info=No tiene asignado usuarios soporte online.")
                        usuariosonline = soporteusuario.virtualsoporteusuarioinscripcion_set.filter(status=True,
                                                                                                    activo=True,matricula__inscripcion__carrera=carrera,
                                                                                                    matricula__nivel__periodo=periodo).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                        if nivel > 0:
                            nivel = NivelMalla.objects.get(pk=nivel)
                            usuariosonline=usuariosonline.filter(matricula__nivelmalla=nivel)

                        for virtualsoporteinscripcion in usuariosonline:
                            if not virtualsoporteinscripcion.virtualsoporteusuarioincidentes_set.filter(estado__in=[1,3],status=True):
                                incidente = VirtualSoporteUsuarioIncidentes(soporteiniscripcion=virtualsoporteinscripcion,
                                                                            fecha_creaticket=datetime.now())
                                incidente.save(request)
                                incidenteasignado = VirtualIncidenteAsignado(incidente=incidente,
                                                                             soporteusuarioasignado=incidente.soporteiniscripcion.soporteusuario,
                                                                             fecha_creaasignacion=datetime.now())
                                incidenteasignado.save(request)
                            else:
                                incidente = virtualsoporteinscripcion.virtualsoporteusuarioincidentes_set.get(estado__in=[1,3])

                            if form.cleaned_data['estado'] == '2':
                                incidente.fecha_finalizaticket = datetime.now()
                                incidente.causaincidente = form.cleaned_data['causaincidente']
                                incidente.estado = int(form.cleaned_data['estado'])
                                incidente.save(request)
                                detalleincidente = \
                                incidente.virtualincidenteasignado_set.filter(status=True).order_by('-id')[0]
                                detalleincidente.planaccion = form.cleaned_data['planaccion']
                                detalleincidente.estado = int(form.cleaned_data['estado'])
                                detalleincidente.fecha_finalizaasignacion = datetime.now()
                                detalleincidente.finalizado = True
                                detalleincidente.save(request)
                                if incidente.soporteiniscripcion:
                                    incidente.envio_correo_incidente(20, request)
                        log(u'genero ticket masivo por carrera: %s  la persona %s' % (carrera, persona), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'informeactividades_pendientes':
                try:
                    __author__ = 'Unemi'
                    tipo=0
                    actividades=None
                    usuariosonline=None
                    idmaterias=None
                    cursor = connections['sga_select'].cursor()
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('actividades')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=actividades' + random.randint(1,10000).__str__() + '.xls'
                    columns = [
                        (u"carrera", 5000),
                        (u"cedula", 5000),
                        (u"apellidos", 5000),
                        (u"nombres", 5000),
                        (u"email", 5000),
                        (u"email institucional", 5000),
                        (u"telefono", 5000),
                        (u"asignatura", 5000),
                        (u"paralelo", 5000),
                        (u"actividad", 5000),
                        (u"tipo actividad", 5000),
                        (u"fecha inicio", 5000),
                        (u"fecha fin", 5000),
                    ]
                    row_num = 4
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 5
                    soporteusuario = VirtualSoporteUsuario.objects.db_manager('sga_select').get(persona=persona, activo=True)
                    usuariosonline = soporteusuario.virtualsoporteusuarioinscripcion_set.db_manager('sga_select').filter(status=True,
                                                                                                activo=True,
                                                                                                matricula__nivel__periodo=periodo)
                    if int(request.POST['idcarrera']) > 0:
                        carrera = Carrera.objects.db_manager('sga_select').get(id=int(request.POST['idcarrera']))
                        usuariosonline = usuariosonline.filter(matricula__inscripcion__carrera=carrera).order_by('id')

                        lista = ""
                        for x in usuariosonline:
                            if x.id != usuariosonline.order_by('-id')[0].id:
                                if x.matricula.inscripcion.id:
                                    lista += str(x.matricula.inscripcion.id) + ","
                            else:
                                lista += str(x.matricula.inscripcion.id)

                        # idmaterias = MateriaAsignada.objects.db_manager('sga_select').values_list('materia__id', flat=True).filter(status=True, matricula__inscripcion__id__in=usuariosonline,
                        #                                           matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera)
                        sql = """
                            SELECT DISTINCT  carr.nombre ||' '|| carr.mencion AS carrera ,pers.cedula, pers.apellido1 ||' '|| pers.apellido2 AS apellidos, pers.nombres AS nombres, 
                            pers.email, pers.emailinst,pers.telefono,
                            asig.nombre AS asignatura, mate.paralelo,
                             act.nombreactividadsakai AS actividad, 
                             (CASE WHEN act.tipo=1 THEN 'TAREA' WHEN act.tipo=2 THEN 'FORO' WHEN act.tipo=3 THEN 'TEST' WHEN act.tipo=4 THEN 'EXAMEN' END) 
                            AS actividad_tipo, act.fechainicio, act.fechafin
                            FROM sga_actividadessakaialumno act
                            INNER JOIN sga_materia mate ON mate.id=act.materia_id
                            INNER JOIN sga_asignatura asig ON asig.id=mate.asignatura_id
                            INNER JOIN sga_inscripcion ins ON ins.id=act.inscripcion_id
                            INNER JOIN sga_carrera carr ON carr.id=ins.carrera_id
                            INNER JOIN sga_persona pers ON pers.id=ins.persona_id
                            INNER JOIN sga_matricula mat ON mat.inscripcion_id=ins.id
                            INNER JOIN sga_nivel niv ON niv.id=mat.nivel_id
                            INNER JOIN sga_periodo per ON per.id=niv.periodo_id
                            WHERE per.id=%s AND act.pendiente=True AND ins.id IN (%s)
                        """ %(periodo.id, lista)
                        cursor.execute(sql)
                        actividades = cursor.fetchall()
                        # actividades = ActividadesSakaiAlumno.objects.db_manager('sga_select').filter(status=True,
                        #                                                                          pendiente=True,
                        #                                                                          inscripcion__id__in=usuariosonline,  materia__id__in=idmaterias )
                        # if int(request.POST['tipo']) > 0:
                        #     tipo = int(request.POST['tipo'])
                        #     actividades = actividades.filter(tipo=tipo)
                        if actividades:
                            for actividad in actividades:
                                ws.write(row_num, 0, actividad[0], font_style2)
                                ws.write(row_num, 1, actividad[1], font_style2)
                                ws.write(row_num, 2, actividad[2], font_style2)
                                ws.write(row_num, 3, actividad[3], font_style2)
                                ws.write(row_num, 4, actividad[4], font_style2)
                                ws.write(row_num, 5, actividad[5], font_style2)
                                ws.write(row_num, 6, actividad[6], font_style2)
                                ws.write(row_num, 7, actividad[7], font_style2)
                                ws.write(row_num, 8, str(actividad[8]), font_style2)
                                ws.write(row_num, 9, actividad[9], font_style2)
                                ws.write(row_num, 10, actividad[10], date_format)
                                ws.write(row_num, 11, actividad[11], date_format)
                                ws.write(row_num, 12, actividad[12], date_format)

                                # ws.write(row_num, 0, actividad.inscripcion.persona.identificacion(), font_style2)
                                # ws.write(row_num, 1,
                                #          actividad.inscripcion.persona.apellido1 + " " + actividad.inscripcion.persona.apellido2,
                                #          font_style2)
                                # ws.write(row_num, 2, actividad.inscripcion.persona.nombres, font_style2)
                                # ws.write(row_num, 3, actividad.inscripcion.persona.email, font_style2)
                                # ws.write(row_num, 4, actividad.inscripcion.persona.emailinst, font_style2)
                                # ws.write(row_num, 5, actividad.inscripcion.persona.telefonos(), font_style2)
                                # ws.write(row_num, 6, actividad.inscripcion.carrera.nombre_completo(), font_style2)
                                # ws.write(row_num, 7, actividad.materia.nombre_completo(), font_style2)
                                # ws.write(row_num, 8, str(actividad.get_tipo_display()), font_style2)
                                # ws.write(row_num, 9, actividad.nombreactividadsakai, font_style2)
                                # ws.write(row_num, 10, actividad.fechainicio, date_format)
                                # ws.write(row_num, 11, actividad.fechafin, date_format)
                                row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex})

            elif action == 'detalle_matricula':
                try:
                    matricula = Matricula.objects.get(pk=int(request.POST['idmatricula']))
                    cursor = connection.cursor()
                    sql = "select am.nivelmalla_id, count(am.nivelmalla_id) as cantidad_materias_seleccionadas " \
                          " from sga_materiaasignada ma, sga_materia m, sga_asignaturamalla am where ma.status=true and ma.matricula_id=" + str(matricula.id) + " and " \
                          " m.status=true and m.id=ma.materia_id and am.status=true and am.id=m.asignaturamalla_id GROUP by am.nivelmalla_id, am.malla_id order by count(am.nivelmalla_id) desc, am.nivelmalla_id desc limit 1;"
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    nivel = 0
                    for per in results:
                        nivel = per[0]
                        cantidad_seleccionadas = per[1]
                    cantidad_nivel = 0
                    materiasnivel=[]
                    for asignaturamalla in AsignaturaMalla.objects.filter(nivelmalla__id=nivel, status=True, malla=matricula.inscripcion.mi_malla()):
                        if Materia.objects.values('id').filter(nivel__periodo=matricula.nivel.periodo, asignaturamalla=asignaturamalla).exists():
                            if matricula.inscripcion.estado_asignatura(asignaturamalla.asignatura) != 1:
                                cantidad_nivel += 1
                    porcentaje_seleccionadas = int(round(Decimal((float(cantidad_nivel) * float(PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD)) / 100).quantize(Decimal('.00')), 0))
                    cobro = 0
                    if matricula.inscripcion.estado_gratuidad == 1 or matricula.inscripcion.estado_gratuidad == 2:
                        if (cantidad_seleccionadas < porcentaje_seleccionadas):
                            mensaje = u"Estudiante irregular, se ha matriculado en menos de %s, debe cancelar por todas las asignaturas." % PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD
                            cobro = 1
                        else:
                            mensaje = u"Debe cancelar por las asignaturas que se matriculó por más de una vez."
                            cobro = 2
                    else:
                        if matricula.inscripcion.estado_gratuidad == 2:
                            mensaje = u"Su estado es de pérdida parcial de la gratuidad. Debe cancelar por las asignaturas que se matriculó por más de una vez."
                            cobro = 2
                        else:
                            mensaje = u"Alumno Regular"
                            cobro = 3
                    if matricula.inscripcion.persona.tiene_otro_titulo(inscripcion=matricula.inscripcion):
                        mensaje = u"El estudiante registra título  en otra IES Pública. Su estado es de pérdida total de la gratuidad. Debe cancelar por todas las asignaturas."
                        cobro = 3
                    if cobro > 0:
                        for materiaasignada in matricula.materiaasignada_set.filter(status=True):
                            if cobro == 1:
                                materiasnivel.append(materiaasignada.materia)
                            else:
                                if cobro == 2:
                                    if materiaasignada.matriculas > 1:
                                        materiasnivel.append(materiaasignada.materia)
                                else:
                                    materiasnivel.append(materiaasignada.materia)
                    valorgrupo = PeriodoGrupoSocioEconomico.objects.filter(status=True, periodo=matricula.nivel.periodo, gruposocioeconomico=matricula.matriculagruposocioeconomico())[0].valor
                    data['mensaje'] = mensaje
                    data['valorgrupo'] = valorgrupo
                    data['materiasnivel'] = materiasnivel
                    data['matricula'] = matricula
                    tiporubroarancel = TipoOtroRubro.objects.filter(pk=RUBRO_ARANCEL)[0]
                    tiporubromatricula = TipoOtroRubro.objects.filter(pk=RUBRO_MATRICULA)[0]
                    valorarancel = null_to_decimal(Rubro.objects.filter(matricula=matricula, status=True,tipo=tiporubroarancel).aggregate(valor=Sum('valortotal'))['valor'])
                    valormatricula = null_to_decimal(Rubro.objects.filter(matricula=matricula, status=True,tipo=tiporubromatricula).aggregate(valor=Sum('valortotal'))['valor'])
                    data['valorarancel'] = valorarancel
                    data['valormatricula'] = valormatricula
                    data['valorpagar'] = valorarancel + valormatricula
                    template = get_template("virtual_soporte_online/detalle_matricula.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'excellistado':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=alumnos_online' + random.randint(1, 10000).__str__() + '.xls'

                    columns = [
                        (u"CEDULA", 3500),
                        (u"APELLIDOS Y NOMBRES", 10000),
                        (u"EMAIL", 8000),
                        (u"TELEFONO", 4000),
                        (u"# INCIDENTES", 4000),
                        (u"PPL", 4000),
                        (u"PAIS", 4000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listadoinscripcion = VirtualSoporteUsuarioInscripcion.objects.filter(soporteusuario__persona=persona, activo=True,matricula__nivel__periodo=periodo).order_by('matricula__inscripcion__persona__apellido1')
                    row_num = 4
                    for listado in listadoinscripcion:
                        i = 0
                        campo1 = listado.matricula.inscripcion.persona.cedula
                        campo2 = listado.matricula.inscripcion.persona
                        campo3 = listado.matricula.inscripcion.persona.email
                        campo4 = listado.matricula.inscripcion.persona.telefono
                        campo5 = listado.virtualsoporteusuarioincidentes_set.filter(status=True).count()
                        campo6 = ''
                        campo7 = ''
                        if listado.matricula.inscripcion.persona.ppl:
                            campo6 = 'SI'
                        if listado.matricula.inscripcion.persona.pais:
                            campo7 = listado.matricula.inscripcion.persona.pais.nombre

                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2.__str__(), font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteincidentesexcell':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 0, 'FECHA DESDE:', font_style)
                    ws.write_merge(1, 1, 1, 3, request.GET['fechainicio'], font_style2)
                    ws.write_merge(2, 2, 0, 0, 'FECHA HASTA', font_style)
                    ws.write_merge(2, 2, 1, 3, request.GET['fechafin'], font_style2)

                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Reporte' + random.randint(
                        1, 10000).__str__() + '.xls'
                    fech_ini = request.GET['fechainicio']
                    fech_fin = request.GET['fechafin'] + ' 23:59'

                    columns = [
                        (u"N#", 4000),
                        (u"Usuario", 4000),
                        (u"cedula", 4000),
                        (u"apellidos y nombres", 10000),
                        (u"email", 6000),
                        (u"telefono", 4000),
                        (u"fecha inicio ticket", 5000),
                        (u"fecha finaliza ticket", 5000),
                        (u"causa", 10000),
                        (u"detalle", 10000),
                        (u"prioridad", 5000),
                        (u"estado", 5000),
                        (u"estado detalle", 5000),
                    ]

                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd h:mm'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'

                    listadoincidentesdetalle = VirtualIncidenteAsignado.objects.filter(Q(incidente__soporteiniscripcion__soporteusuario__persona=persona) | Q(incidente__soporteprofesor__soporteusuario__persona=persona) ,
                                                                                       incidente__fecha_creaticket__gte=fech_ini, incidente__fecha_creaticket__lte=fech_fin,
                                                                                       incidente__status=True,status=True).order_by('id')
                    row_num = 4
                    i = 0
                    for listado in listadoincidentesdetalle:
                        i += 1
                        persona=None
                        if listado.incidente.soporteiniscripcion:
                            persona = listado.incidente.soporteiniscripcion.matricula.inscripcion.persona
                        else:
                            persona = listado.incidente.soporteprofesor.profesor.persona
                        campo1 = persona.cedula
                        campo2 = persona.apellido1 + ' ' + persona.apellido2 + ' ' + persona.nombres
                        campo3 = persona.email
                        campo4 = persona.telefono
                        campo5 = listado.fecha_creaasignacion
                        campo6 = listado.fecha_finalizaasignacion
                        if listado.incidente.causaincidente:
                            campo9 = listado.incidente.causaincidente.descripcion
                            campo10 = listado.incidente.causaincidente.get_prioridad_display()
                        else:
                            campo9 = ''
                            campo10 = ''
                        campo11 = listado.incidente.get_estado_display()
                        campo12 = listado.planaccion
                        campo13 = listado.get_estado_display()
                        campo14 = listado.incidente.id
                        campo15 = "ALUMNO" if listado.incidente.soporteiniscripcion else "TUTOR"
                        ws.write(row_num, 0, campo14, font_style2)
                        ws.write(row_num, 1, campo15, font_style2)
                        ws.write(row_num, 2, campo1, font_style2)
                        ws.write(row_num, 3, campo2, font_style2)
                        ws.write(row_num, 4, campo3, font_style2)
                        ws.write(row_num, 5, campo4, font_style2)
                        ws.write(row_num, 6, campo5, date_format)
                        ws.write(row_num, 7, campo6, date_format)
                        ws.write(row_num, 8, campo9, font_style2)
                        ws.write(row_num, 9, campo12, font_style2)
                        ws.write(row_num, 10, campo10, font_style2)
                        ws.write(row_num, 11, campo11, font_style2)
                        ws.write(row_num, 12, campo13, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'estudiante_asignado':
                try:
                    __author__ = 'Unemi'

                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('resumen')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write(1, 0, "SECCIÓN DE ADMISIÓN Y NIVELACIÓN", font_style2)
                    ws.write(2, 0, "LISTADO DE ESTUDIANTES ASIGNADOS", font_style2)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=resumen' + random.randint(1,10000).__str__() + '.xls'
                    columns = [
                        (u"Cedula .", 5000),
                        (u"Carrera .", 5000),
                        (u"Alumno .", 5000),
                    ]
                    row_num = 4
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 6
                    campo1 = ''
                    campo2 = ''
                    campo3 = ''

                    soporteusuario = VirtualSoporteUsuario.objects.get(persona=persona, activo=True)

                    for usuario in soporteusuario.asignados(periodo):
                        campo1 = str(usuario.matricula.inscripcion.persona.identificacion())
                        campo2 = str(usuario.matricula.inscripcion.carrera)
                        campo3 = str(usuario.matricula.inscripcion.persona.nombre_completo_inverso())
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass



            elif action == 'virtual_incidente':
                try:
                    data['title'] = u'Incidente'
                    data['virtualsoporteincidente'] = virtualsoporteinscripcion = VirtualSoporteUsuarioInscripcion.objects.get(pk=request.GET['idticket'], status=True)
                    if not virtualsoporteinscripcion.virtualsoporteusuarioincidentes_set.filter(estado__in=[1,3],status=True):
                        incidente = VirtualSoporteUsuarioIncidentes(soporteiniscripcion=virtualsoporteinscripcion,
                                                                    fecha_creaticket=datetime.now())
                        incidente.save(request)
                        incidenteasignado = VirtualIncidenteAsignado(incidente=incidente,
                                                                     soporteusuarioasignado=incidente.soporteiniscripcion.soporteusuario,
                                                                     fecha_creaasignacion=datetime.now())
                        incidenteasignado.save(request)
                    else:
                        incidente = virtualsoporteinscripcion.virtualsoporteusuarioincidentes_set.get(estado__in=[1,3])
                    data['incidente'] = incidente
                    data['listaasignado'] = incidente.virtualincidenteasignado_set.filter(status=True).order_by('id')
                    userasignado = None
                    f = VirtualSoporteAsignado.objects.filter(soporteusuario=incidente.soporteiniscripcion.soporteusuario)
                    if VirtualSoporteAsignado.objects.filter(soporteusuario=incidente.soporteiniscripcion.soporteusuario,periodo=periodo):
                        userasignado = VirtualSoporteAsignado.objects.get(soporteusuario=incidente.soporteiniscripcion.soporteusuario,periodo=periodo)
                        userasignado = userasignado.soporte
                    form = VirtualIncidenteForm(initial={'causaincidente': incidente.causaincidente,
                                                         'telefono': incidente.soporteiniscripcion.matricula.inscripcion.persona.telefono,
                                                         'telefono2': incidente.soporteiniscripcion.matricula.inscripcion.persona.telefono2,
                                                         'telefono_conv': incidente.soporteiniscripcion.matricula.inscripcion.persona.telefono_conv,
                                                         'estado': incidente.estado,
                                                         'personaasignar': userasignado,
                                                         'email': incidente.soporteiniscripcion.matricula.inscripcion.persona.email,
                                                         'pais': incidente.soporteiniscripcion.matricula.inscripcion.persona.pais,
                                                         'provincia': incidente.soporteiniscripcion.matricula.inscripcion.persona.provincia,
                                                         'canton': incidente.soporteiniscripcion.matricula.inscripcion.persona.canton,
                                                         'parroquia': incidente.soporteiniscripcion.matricula.inscripcion.persona.parroquia,
                                                         'sector': incidente.soporteiniscripcion.matricula.inscripcion.persona.sector,
                                                         'direccion': incidente.soporteiniscripcion.matricula.inscripcion.persona.direccion,
                                                         'direccion2': incidente.soporteiniscripcion.matricula.inscripcion.persona.direccion2,
                                                         'num_direccion': incidente.soporteiniscripcion.matricula.inscripcion.persona.num_direccion,
                                                         'desertaonline': incidente.soporteiniscripcion.matricula.inscripcion.desertaonline,
                                                         'observaciondesertaonline': incidente.soporteiniscripcion.matricula.inscripcion.observaciondesertaonline,
                                                         })
                    if userasignado:
                        form.editar(userasignado.id)
                    data['form'] = form
                    return render(request, "virtual_soporte_online/virtual_incidente.html", data)
                except Exception as ex:
                    pass

            elif action == 'virtual_incidente_tutor':
                try:
                    data['title'] = u'Incidente'
                    data['virtualsoporteprofesor'] = virtualsoporteprofesor = VirtualSoporteUsuarioProfesor.objects.get(pk=request.GET['idticket'], status=True)
                    if not virtualsoporteprofesor.virtualsoporteusuarioincidentes_set.filter(estado__in=[1,3],status=True).exists():
                        incidente = VirtualSoporteUsuarioIncidentes(soporteprofesor=virtualsoporteprofesor,
                                                                    fecha_creaticket=datetime.now())
                        incidente.save(request)
                        incidenteasignado = VirtualIncidenteAsignado(incidente=incidente,
                                                                     soporteusuarioasignado=incidente.soporteprofesor.soporteusuario,
                                                                     fecha_creaasignacion=datetime.now())
                        incidenteasignado.save(request)
                    else:
                        incidente = VirtualSoporteUsuarioIncidentes.objects.filter(status=True,estado__in=[1,3],soporteprofesor=virtualsoporteprofesor)[0]
                    data['incidente'] = incidente
                    data['listaasignado'] = incidente.virtualincidenteasignado_set.filter(status=True).order_by('id') if incidente.virtualincidenteasignado_set.filter(status=True).exists() else None
                    userasignado = None
                    f = VirtualSoporteAsignado.objects.filter(soporteusuario=incidente.soporteprofesor.soporteusuario)
                    if VirtualSoporteAsignado.objects.filter(soporteusuario=incidente.soporteprofesor.soporteusuario):
                        userasignado = VirtualSoporteAsignado.objects.get(soporteusuario=incidente.soporteprofesor.soporteusuario,periodo=periodo)
                        userasignado = userasignado.soporte
                    form = VirtualIncidenteForm(initial={'causaincidente': incidente.causaincidente,
                                                         'telefono': incidente.soporteprofesor.profesor.persona.telefono,
                                                         'telefono2': incidente.soporteprofesor.profesor.persona.telefono2,
                                                         'telefono_conv': incidente.soporteprofesor.profesor.persona.telefono_conv,
                                                         'estado': incidente.estado,
                                                         'personaasignar': userasignado,
                                                         'email': incidente.soporteprofesor.profesor.persona.email,
                                                         'pais': incidente.soporteprofesor.profesor.persona.pais,
                                                         'provincia': incidente.soporteprofesor.profesor.persona.provincia,
                                                         'canton': incidente.soporteprofesor.profesor.persona.canton,
                                                         'parroquia': incidente.soporteprofesor.profesor.persona.parroquia,
                                                         'sector': incidente.soporteprofesor.profesor.persona.sector,
                                                         'direccion': incidente.soporteprofesor.profesor.persona.direccion,
                                                         'direccion2': incidente.soporteprofesor.profesor.persona.direccion2,
                                                         'num_direccion': incidente.soporteprofesor.profesor.persona.num_direccion,
                                                         })
                    if userasignado:
                        form.editar(userasignado.id)
                    form.quitarcampos()
                    data['form'] = form
                    return render(request, "virtual_soporte_online/virtual_incidente_tutor.html", data)
                except Exception as ex:
                    pass

            elif action == 'imprimiractividadalumno':
                try:
                    inscripcion = Inscripcion.objects.get(pk=int(str(request.GET['idinscripcion'])))
                    lista_asignaturas = inscripcion.asignaturas_sakai()
                    return conviert_html_to_pdf('imprimiractividadalumnogeneralsakai.html',
                                                {'pagesize': 'A4',
                                                 'data': data,
                                                 'inscripcion':inscripcion,
                                                 'lista_asignaturas':lista_asignaturas
                                                 })
                except Exception as ex:
                    pass

            elif action == 'resetear_clave_admision_virtual':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_inscripciones')
                    data['title'] = u'Resetear clave del usuario'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    # puede_modificar_inscripcion(request, inscripcion)
                    return render(request, "virtual_soporte_online/resetear_clave_admision_virtual.html", data)
                except Exception as ex:
                    pass

            elif action == 'listatutores':
                try:
                    data['title'] = u'Listado de tutores online'
                    search = None
                    ids = None
                    inscripcionid = None
                    if VirtualSoporteUsuario.objects.filter(persona=persona, activo=True, status=True).exists():
                        soporteusuario = VirtualSoporteUsuario.objects.get(persona=persona, activo=True)
                    else:
                        return HttpResponseRedirect("/?info=No tiene asignado usuarios soporte online.")
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            usuariosonline = soporteusuario.virtualsoporteusuarioprofesor_set.filter(
                                Q(profesor__persona__nombres__icontains=search) |
                                Q(profesor__persona__apellido1__icontains=search) |
                                Q(profesor__persona__apellido2__icontains=search) |
                                Q(profesor__persona__cedula__icontains=search) |
                                Q(profesor__persona__pasaporte__icontains=search) |
                                Q(profesor__persona__telefono__icontains=search) |
                                Q(profesor__persona__email__icontains=search), status=True)
                        else:
                            usuariosonline = soporteusuario.virtualsoporteusuarioprofesor_set.filter(
                                Q(profesor__persona__apellido1__icontains=ss[0]) &
                                Q(profesor__persona__apellido2__icontains=ss[1]), status=True)
                    else:
                        usuariosonline = soporteusuario.virtualsoporteusuarioprofesor_set.all().order_by('profesor__persona__apellido1','profesor__persona__apellido2').order_by('-id')
                    paging = MiPaginador(usuariosonline, 20)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['usuariosonline'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['inscripcionid'] = inscripcionid if inscripcionid else ""
                    return render(request, "virtual_soporte_online/listadotutores.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarsoporteinscripcion':
                try:
                    data['title'] = u'Incidente'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'], status=True)
                    form = EditarSoporteInscripcionForm(initial={
                                                         'telefono': inscripcion.persona.telefono,
                                                         'telefono2': inscripcion.persona.telefono2,
                                                         'telefono_conv': inscripcion.persona.telefono_conv,
                                                         'email': inscripcion.persona.email,
                                                         'pais': inscripcion.persona.pais,
                                                         'provincia': inscripcion.persona.provincia,
                                                         'canton': inscripcion.persona.canton,
                                                         'parroquia': inscripcion.persona.parroquia,
                                                         'sector': inscripcion.persona.sector,
                                                         'direccion': inscripcion.persona.direccion,
                                                         'direccion2': inscripcion.persona.direccion2,
                                                         'num_direccion': inscripcion.persona.num_direccion,
                                                         })
                    data['form'] = form
                    return render(request, "virtual_soporte_online/editarsoporteinscripcion.html", data)
                except Exception as ex:
                    pass

            elif action == 'seguimiento_asignaturas_alumno':
                try:
                    data['title'] = u'Asignaturas'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['matricula']= matricula = Matricula.objects.get(pk=request.GET['idm'])
                    data['materiassga'] = inscripcion.materias(periodo)
                    data['valor_pendiente'] = matricula.total_saldo_rubro()
                    data['valor_pagados'] = matricula.total_pagado_rubro()
                    return render(request, "virtual_soporte_online/actividadessakai.html", data)
                except Exception as ex:
                    pass

            elif action == 'ver_actividades':
                try:
                    data['title'] = u'Actividades'
                    data['inscripcion'] = Inscripcion.objects.get(pk=int(request.GET['idinscripcion']))
                    data['materia'] = Materia.objects.get(id=int(request.GET['idcurso']))
                    return render(request, "virtual_soporte_online/ver_actividades_sakai.html", data)
                except Exception as ex:
                    pass

            elif action == 'actividades_pendientes':
                try:
                    data['hoy'] = hoy = datetime.now()
                    data['title'] = u'Actividades Pendientes'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=int(request.GET['idinscripcion']))
                    data['materia'] = materia = Materia.objects.get(id=int(request.GET['idcurso']))
                    return render(request, "virtual_soporte_online/actividades_pendientes.html", data)
                except Exception as ex:
                    pass

            elif action == 'ver_actividades_generales_pendientes':
                try:
                    data['title'] = u'Actividades Pendientes'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=int(request.GET['idinscripcionid']))
                    data['periodo']=periodo
                    data['fini']=request.GET['fini']
                    data['ffin']=request.GET['ffin']
                    data['usuario']= persona.usuario.username,
                    return render(request, "virtual_soporte_online/actividades_generales_pendientes.html", data)
                except Exception as ex:
                    pass

            elif action == 'lista_reportes_soporte':
                try:
                    soporteusuario = VirtualSoporteUsuario.objects.get(persona=persona, activo=True)
                    data['title'] = u'Reportes Generados'
                    data['reportes'] = soporteusuario.reportesoportevirtual_set.all()
                    return render(request,"virtual_soporte_online/lista_reportes_soporte.html", data)
                except Exception as ex:
                    pass

            elif action == 'addreporte':
                try:
                    data['title'] = u'Adicionar Reporte'
                    data['form'] = ReporteSoporteUsuarioForm(initial={'semestre':'IISEM2018','objetivo':'Informar Actividades que se han realizado en el perfil designado como Personal de Apoyo Académico durante el mes de abril del 2019.'})
                    data['soporteusuario'] = soporteusuario = VirtualSoporteUsuario.objects.get(persona=persona, activo=True)
                    return render(request, 'virtual_soporte_online/addreporte.html', data)
                except Exception as ex:
                    pass

            elif action == 'editreporte':
                try:
                    data['title'] = u'Editar Reporte'
                    data['reporte'] = reporte = ReporteSoporteVirtual.objects.get(pk=int(request.GET['id']))
                    data['form'] = ReporteSoporteUsuarioForm(initial={'numeroreporte':reporte.numeroinforme,
                                                                      'fechaelaboracion':reporte.fechaelaboracion,
                                                                      'fechaentrega':reporte.fechaentrega,
                                                                      'horaelaboracion':reporte.horaelaboracion,
                                                                      'horaentrega':reporte.horaentrega,
                                                                      'objetivo':reporte.objetivo,
                                                                      'semestre':reporte.semestre})
                    data['soporteusuario'] = soporteusuario = VirtualSoporteUsuario.objects.get(persona=persona, activo=True)
                    return render(request, 'virtual_soporte_online/editreporte.html', data)
                except Exception as ex:
                    pass

            elif action == 'addactividad':
                try:
                    data['title'] = u'Adicionar Actividades'
                    data['form'] = DetalleReporteSoporteForm()
                    data['reporte'] = reporte = ReporteSoporteVirtual.objects.get(pk=int(request.GET['idreporte']))
                    return render(request, 'virtual_soporte_online/addactividad.html', data)
                except Exception as ex:
                    pass

            elif action == 'editactividad':
                try:
                    data['title'] = u'Editar Actividades'
                    data['actividad'] = actividad = DetalleReporteSoporteVirtual.objects.get(pk=int(request.GET['id']))
                    form = EditDetalleReporteSoporteForm(initial={'fechaactividad': actividad.fechaactividad,'tipoactividad':actividad.tipoactividad, 'nombreactividad': actividad.nombreactividad,'tiposistema':actividad.tiposistema})
                    form.editar(actividad)
                    data['form'] = form
                    return render(request, 'virtual_soporte_online/editactividad.html', data)
                except Exception as ex:
                    pass

            elif action == 'adddocumento':
                try:
                    data['title'] = u'Adicionar Documento'
                    data['form'] = DocumentoEntregadoForm()
                    data['reporte'] = reporte = ReporteSoporteVirtual.objects.get(pk=int(request.GET['idreporte']))
                    return render(request, 'virtual_soporte_online/adddocumento.html', data)
                except Exception as ex:
                    pass

            elif action == 'addtipoactividad':
                try:
                    data['title'] = u'Adicionar Tipo de Actividad'
                    data['form'] = TipoActividadVirtualForm()
                    if 'idreporte' in request.GET:
                        data['reporte'] = reporte = ReporteSoporteVirtual.objects.get(pk=int(request.GET['idreporte']))
                    return render(request, 'virtual_soporte_online/addtipoactividad.html', data)
                except Exception as ex:
                    pass

            elif action == 'edittipoactividad':
                try:
                    data['title'] = u'Editar Tipo de Actividad'
                    data['actividad'] = actividad = TipoActividadVirtual.objects.get(pk=int(request.GET['id']))
                    data['form'] = TipoActividadVirtualForm(initial={'titulo':actividad.titulo})
                    return render(request, 'virtual_soporte_online/edittipoactividad.html', data)
                except Exception as ex:
                    pass

            elif action == 'editdocumento':
                try:
                    data['title'] = u'Editar Documento'
                    data['documento'] = documento = DocumentoEntregado.objects.get(pk=int(request.GET['id']))
                    form = DocumentoEntregadoForm(initial={'nombredocumento':documento.nombredocumento})
                    data['form'] = form
                    return render(request, 'virtual_soporte_online/editdocumento.html', data)
                except Exception as ex:
                    pass

            elif action == 'addanexo':
                try:
                    data['title'] = u'Adicionar Anexo'
                    data['form'] = AnexosReporteUsuarioVirtualForm()
                    data['documento'] = documento = DocumentoEntregado.objects.get(pk=int(request.GET['id']))
                    return render(request, 'virtual_soporte_online/addanexo.html', data)
                except Exception as ex:
                    pass

            elif action == 'listar_actividades_soporte':
                try:
                    data['title'] = u'Actividades y Documentos Realizados'
                    data['form'] = DetalleReporteSoporteForm()
                    data['reporte'] = reporte = ReporteSoporteVirtual.objects.get(pk=int(request.GET['idreporte']))
                    data['listadoactividades'] = reporte.detallereportesoportevirtual_set.all().order_by('fechaactividad')
                    data['documentos'] = reporte.documentoentregado_set.all().order_by('id')
                    return render(request, 'virtual_soporte_online/listadoactividades.html', data)
                except Exception as ex:
                    pass

            elif action == 'listar_anexos':
                try:
                    data['title'] = u'Listado de Anexos'
                    data['documento'] = documento = DocumentoEntregado.objects.get(pk=int(request.GET['id']))
                    return render(request, 'virtual_soporte_online/listado_anexos.html', data)
                except Exception as ex:
                    pass

            elif action == 'extraer_actividades':
                try:
                    data['title'] = u'Actividades  Realizados'
                    documento = DocumentoEntregado.objects.get(pk=int(request.GET['iddocumento']))
                    if VirtualIncidenteAsignado.objects.filter(Q(incidente__soporteiniscripcion__soporteusuario__persona=persona) | Q(incidente__soporteprofesor__soporteusuario__persona=persona), incidente__fecha_creaticket__gte=request.GET['fechainicio'], incidente__fecha_creaticket__lte=request.GET['fechafin'],incidente__status=True, status=True):
                        listadoincidentesdetalle = VirtualIncidenteAsignado.objects.filter(Q(incidente__soporteiniscripcion__soporteusuario__persona=persona) | Q(incidente__soporteprofesor__soporteusuario__persona=persona), incidente__fecha_creaticket__gte=request.GET['fechainicio'], incidente__fecha_creaticket__lte=request.GET['fechafin'],incidente__status=True, status=True).order_by('id')
                        AnexosReporteUsuarioVirtual.objects.filter(documento=documento).delete()
                        for insertar in listadoincidentesdetalle:
                            anexo = AnexosReporteUsuarioVirtual(documento=documento,incidente=insertar)
                            anexo.save()
                        data['listadoincidentesdetalle'] = listadoincidentesdetalle
                        return render(request, 'virtual_soporte_online/extraer_actividades.html', data)
                except Exception as ex:
                    pass

            elif action == 'delactividad':
                try:
                    data['title'] = u'Eliminar Actividad'
                    data['actividad'] = actividad = DetalleReporteSoporteVirtual.objects.get(pk=int(request.GET['id']))
                    data['idreporte'] = actividad.reporte.id
                    return render(request, "virtual_soporte_online/delactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'deltipoactividad':
                try:
                    data['title'] = u'Eliminar Actividad'
                    data['actividad'] = actividad = TipoActividadVirtual.objects.get(pk=int(request.GET['id']))
                    return render(request, "virtual_soporte_online/deltipoactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'deldocumento':
                try:
                    data['title'] = u'Eliminar Documento'
                    data['documento'] = documento = DocumentoEntregado.objects.get(pk=int(request.GET['id']))
                    return render(request, "virtual_soporte_online/deldocumento.html", data)
                except Exception as ex:
                    pass

            elif action == 'delanexo':
                try:
                    data['title'] = u'Eliminar Anexo'
                    data['anexo'] = anexo = AnexosReporteUsuarioVirtual.objects.get(pk=int(request.GET['id']))
                    return render(request, "virtual_soporte_online/delanexo.html", data)
                except Exception as ex:
                    pass

            elif action == 'generar_reporte_soporte_resumen':
                try:
                    data['reporte'] = reporte = ReporteSoporteVirtual.objects.get(pk=int(request.GET['id']))
                    return conviert_html_to_pdf('virtual_soporte_online/imprimir_reporte_soporte.html',
                                                {'pagesize': 'A4',
                                                 'data': data,
                                                 'reporte': reporte,
                                                 })
                except Exception as ex:
                    pass

            elif action == 'generar_reporte_soporte':
                try:
                    data['reporte'] = reporte = ReporteSoporteVirtual.objects.get(pk=int(request.GET['id']))
                    return conviert_html_to_pdf('virtual_soporte_online/imprimir_reporte.html',
                                                {'pagesize': 'A4',
                                                 'data': data,
                                                 'reporte': reporte,
                                                 })
                except Exception as ex:
                    pass

            elif action == 'generar_ticket_masivo':
                try:
                    data['carrera'] = carrera = Carrera.objects.get(id=int(request.GET['idcarrera']))
                    data['nivel'] = nivel = int(request.GET['nivel'])
                    data['title'] = u'TICKET MASIVO A ' + str(carrera.nombre_completo())
                    form = VirtualIncidenteMasivoForm()
                    data['form'] = form
                    return render(request, "virtual_soporte_online/generar_ticket_masivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'ver_notas':
                try:
                    data['inscripcion'] = Inscripcion.objects.filter(id=request.GET['idinscripcion'])[0]
                    data['materiasasignadas'] = maateriaasignada = MateriaAsignada.objects.filter(id=request.GET['idcurso'])
                    return render(request, "virtual_soporte_online/segmento.html", data)
                except Exception as ex:
                    pass

            elif action == 'horarioexamen':
                try:
                    data['title'] = u'Horario Exámen'
                    data['horariovirtual'] = None
                    data['horarioasignaturas'] = None
                    data['matricula'] = matricula = Matricula.objects.filter(id=request.GET['id'])[0]
                    data['periodo'] = request.session['periodo']
                    if not matricula:
                        return HttpResponseRedirect("/?info=No ha sido matriculado")
                    if HorarioVirtual.objects.filter(participanteshorariovirtual__matricula=matricula, tipo=1, status=True):
                        data['horariovirtual'] = horariovirtual = HorarioVirtual.objects.filter(participanteshorariovirtual__matricula=matricula,tipo=1, status=True)
                    if HorarioVirtual.objects.filter(participanteshorariovirtual__matricula=matricula, tipo=2, status=True):
                        data['horariovirtualrecu'] = horariovirtualrecu = HorarioVirtual.objects.filter(participanteshorariovirtual__matricula=matricula,tipo=2, status=True)
                    return render(request, "virtual_soporte_online/horarioexamen.html", data)
                except Exception as ex:
                    pass

            elif action == 'horario':
                try:
                    data['title'] = u'Horario del estudiante'
                    data['matricula'] = matricula = Matricula.objects.get(pk=request.GET['id'])
                    data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                    hoy = datetime.now().date()
                    data['misclases'] = clases = Clase.objects.filter(activo=True, materia__materiaasignada__matricula=matricula, materia__materiaasignada__retiramateria=False).order_by('inicio')
                    # data['misclases'] = clases = Clase.objects.filter(activo=True, fin__gte=hoy, materia__materiaasignada__matricula=matricula, materia__materiaasignada__retiramateria=False).order_by('inicio')
                    data['inscripcion'] = matricula.inscripcion
                    data['sesiones'] = Sesion.objects.filter(turno__clase__in=clases).distinct()
                    data['idperiodo'] = periodo.id
                    return render(request, "virtual_soporte_online/horario.html", data)
                except Exception as ex:
                    pass

            elif action == 'rubros':
                try:
                    nivel=None
                    data['title'] = u'Listado de rubros'
                    data['cliente'] = cliente = Persona.objects.get(pk=request.GET['id'])
                    rubrosnocancelados = cliente.rubro_set.filter(cancelado=False, status=True).order_by('cancelado', 'fechavence')
                    rubroscanceldos = cliente.rubro_set.filter(cancelado=True, status=True).order_by('fechavence')
                    rubros = list(chain(rubrosnocancelados, rubroscanceldos))
                    data['nivel']=nivel
                    paging = Paginator(rubros, 30)
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
                    data['page'] = page
                    data['rubros'] = page.object_list
                    return render(request, "virtual_soporte_online/rubros.html", data)
                except Exception as ex:
                    pass

            elif action == 'pagos':
                try:
                    data['rubro'] = rubro = Rubro.objects.get(pk=request.GET['id'])
                    data['title'] = u'Pagos del rubro '
                    data['pagos'] = rubro.pago_set.all()
                    return render(request, "virtual_soporte_online/pagos.html", data)
                except Exception as ex:
                    pass

            elif action == 'silabovirtual':
                try:
                    data['title'] = u'Sílabos'
                    data['materiaasignada'] =materiaasignada= MateriaAsignada.objects.get(pk=request.GET['id'])
                    data['silabos'] = materiaasignada.materia.silabo_set.all()
                    return render(request, "virtual_soporte_online/silabodocentevirtual.html", data)
                except Exception as ex:
                    pass

            elif action == 'tiene_programaanaliticovirtual':
                try:
                    materia = Materia.objects.get(pk=int(request.GET['id']))
                    if not materia.asignaturamalla.programaanaliticoasignatura_set.filter(activo=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"No Tiene Programa Analitico."})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'planclasevirtual':
                try:
                    data['title'] = u'PLANIFICACIÓN SEMANAL DE SÍLABO'
                    data['idmateriaasignada']=int(request.GET['idmateriaasignada'])
                    data['silabocab'] = silabocab = Silabo.objects.get(pk=int(request.GET['silaboid']), status=True)
                    data['tiporecurso'] = TIPO_RECURSOS
                    data['tipolink'] = TIPO_LINK
                    data['tipoactividad'] = TIPO_ACTIVIDAD
                    if not PlanificacionClaseSilabo.objects.filter(tipoplanificacion__planificacionclasesilabo_materia__materia=silabocab.materia, status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Noo tiene cronograma académico."})
                    data['planificacion'] = PlanificacionClaseSilabo.objects.filter(tipoplanificacion__planificacionclasesilabo_materia__materia=silabocab.materia, status=True).exclude(semana=0).order_by('orden')
                    lista = []
                    for p in PlanificacionClaseSilabo.objects.filter(tipoplanificacion__planificacionclasesilabo_materia__materia=silabocab.materia, status=True).exclude(semana=0).order_by('orden'):
                        semana =None
                        idcodigo = 0
                        if silabocab.silabosemanal_set.filter(fechainiciosemana__gte=p.fechainicio, fechafinciosemana__lte=p.fechafin, status=True).exists():
                            lissemana = silabocab.silabosemanal_set.filter(fechainiciosemana__gte=p.fechainicio, fechafinciosemana__lte=p.fechafin, status=True)[0]
                            idcodigo = lissemana.id
                            semana = lissemana
                        idcodigo = idcodigo
                        modelosilabo = semana
                        lista.append([p.fechainicio.isocalendar()[1], p.fechainicio, p.fechafin,idcodigo ,modelosilabo ])
                    data['fechas'] = lista
                    data['porcentaje_semanas_registradas'] = silabocab.estado_semanas_llenas(lista.__len__())
                    return render(request, "virtual_soporte_online/listado_plancasevirtual.html", data)
                except Exception as ex:
                    pass

            elif action == 'alumalla':
                try:
                    listas_asignaturasmallas = []
                    data['title'] = u'Malla del alumno'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['inscripcion_malla'] = inscripcionmalla = inscripcion.malla_inscripcion()
                    data['malla'] = malla = inscripcionmalla.malla
                    data['nivelesdemallas'] = nivelmalla = NivelMalla.objects.all().order_by('id')
                    data['ejesformativos'] = EjeFormativo.objects.all().order_by('nombre')
                    listadoasignaturamalla = AsignaturaMalla.objects.filter(malla=malla)
                    for x in listadoasignaturamalla.exclude(ejeformativo_id=4):
                        listas_asignaturasmallas.append([x, inscripcion.aprobadaasignatura(x)])
                    for ni in nivelmalla:
                        listadooptativa = listadoasignaturamalla.filter(nivelmalla=ni, ejeformativo_id=4)
                        if inscripcion.recordacademico_set.filter(asignatura__in=listadooptativa.values_list('asignatura__id', flat=True)).exists():
                            for d in listadooptativa:
                                if inscripcion.aprobadaasignatura(d):
                                    listas_asignaturasmallas.append([d, inscripcion.aprobadaasignatura(d)])
                        else:
                            for d in listadooptativa:
                                listas_asignaturasmallas.append([d, inscripcion.aprobadaasignatura(d)])
                    data['asignaturasmallas'] = listas_asignaturasmallas
                    resumenniveles = [{'id': x.id, 'horas': x.total_horas(malla), 'creditos': x.total_creditos(malla)} for x in NivelMalla.objects.all().order_by('id')]
                    data['resumenes'] = resumenniveles
                    return render(request, "virtual_soporte_online/alumalla.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'record':
                try:
                    data['title'] = u'Registro académico'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['records'] = inscripcion.recordacademico_set.filter(status=True).order_by('asignaturamalla__nivelmalla', 'asignatura', 'fecha')
                    data['total_creditos'] = inscripcion.total_creditos()
                    data['total_creditos_malla'] = inscripcion.total_creditos_malla()
                    data['total_creditos_modulos'] = inscripcion.total_creditos_modulos()
                    data['total_creditos_otros'] = inscripcion.total_creditos_otros()
                    data['total_horas'] = inscripcion.total_horas()
                    data['promedio'] = inscripcion.promedio_record()
                    data['aprobadas'] = inscripcion.recordacademico_set.filter(aprobada=True, valida=True).count()
                    data['reprobadas'] = inscripcion.recordacademico_set.filter(aprobada=False, valida=True).count()
                    data['idasignaturasingles'] = []
                    data['idasignaturasingles'] = AsignaturaMalla.objects.values_list('asignatura_id', flat=True).filter(status=True, malla__carrera__id=34).distinct()
                    data['tiene_permiso'] = persona.persona_tiene_permiso(inscripcion.id)
                    return render(request, "virtual_soporte_online/record.html", data)
                except Exception as ex:
                    pass

            elif action == 'asistencias':
                try:
                    matricula = Matricula.objects.get(pk=request.GET['id'])
                    data['matricula'] = matricula
                    cantidadmaxima = 0
                    for materia in matricula.materiaasignada_set.all():
                        if materia.cantidad_asistencias_lecciones() > cantidadmaxima:
                            cantidadmaxima = materia.cantidad_asistencias_lecciones()
                    materiaasignadas = []
                    for materia in matricula.materiaasignada_set.filter(retiramateria=False).order_by(
                            'materia__asignatura'):
                        materiaasignadas.append(
                            [materia, materia.asistencias_lecciones(), cantidadmaxima, materia.asistencia_plan(),
                             cantidadmaxima - materia.cantidad_asistencias_lecciones(), materia.asistencia_real(),
                             materia.real_dias_asistencia(),
                             materia.real_dias_asistencia() - materia.asistencia_real()])
                    data['materiasasiganadas'] = materiaasignadas
                    data['cantidad'] = cantidadmaxima
                    data[
                        'puede_modificar_asistencia'] = True if not periodo.tipo_id == 2 or matricula.carrera_es_admision() else False
                    data['puede_modificar_asistencia_por_perfilusuario'] = persona.mis_carreras().values('id').filter(
                        pk=matricula.inscripcion.carrera.id).exists()
                    return render(request, "virtual_soporte_online/asistencias.html", data)
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Listado de estudiantes online'
                search = None
                ids = None
                inscripcionid = None
                carr = None
                nivel = None
                modalidad = None
                if VirtualSoporteUsuario.objects.filter(persona=persona, activo=True,status=True).exists():
                    soporteusuario = VirtualSoporteUsuario.objects.get(persona=persona,activo=True)
                else:
                    return HttpResponseRedirect("/?info=No tiene asignado usuarios soporte online.")
                usuariosonline=soporteusuario.virtualsoporteusuarioinscripcion_set.filter(status=True, activo=True, matricula__nivel__periodo=periodo ).order_by('matricula__inscripcion__persona__apellido1','matricula__inscripcion__persona__apellido2')
                listacarrerass=soporteusuario.virtualsoporteusuarioinscripcion_set.values_list('matricula__inscripcion__carrera__id', flat=True).filter(status=True, activo=True, matricula__nivel__periodo=periodo ).distinct()
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        usuariosonline = usuariosonline.filter(Q(matricula__inscripcion__persona__nombres__icontains=search) |
                                                                                                    Q(matricula__inscripcion__persona__apellido1__icontains=search) |
                                                                                                    Q(matricula__inscripcion__persona__apellido2__icontains=search) |
                                                                                                    Q(matricula__inscripcion__persona__cedula__icontains=search) |
                                                                                                    Q(matricula__inscripcion__persona__pasaporte__icontains=search) |
                                                                                                    Q(matricula__inscripcion__persona__telefono__icontains=search) |
                                                                                                    Q(matricula__inscripcion__persona__email__icontains=search))
                    else:
                        usuariosonline = usuariosonline.filter(Q(matricula__inscripcion__persona__apellido1__icontains=ss[0]) & Q(matricula__inscripcion__persona__apellido2__icontains=ss[1]))
                if 'carr' in request.GET:
                    carr = int(request.GET['carr'])
                    if carr > 0:
                        usuariosonline=usuariosonline.filter(matricula__inscripcion__carrera__id=carr)
                if 'nivel' in request.GET:
                    nivel = int(request.GET['nivel'])
                    if nivel > 0:
                        usuariosonline=usuariosonline.filter(matricula__nivelmalla__id=nivel)
                if 'modalidad' in request.GET:
                    modalidad = int(request.GET['modalidad'])
                    if modalidad > 0:
                        usuariosonline=usuariosonline.filter(matricula__inscripcion__modalidad__id=modalidad)
                paging = MiPaginador(usuariosonline, 20)
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
                data['page'] = page
                data['rangospaging'] = paging.rangos_paginado(p)
                data['usuariosonline'] = page.object_list
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['inscripcionid'] = inscripcionid if inscripcionid else ""
                data['carreras'] = Carrera.objects.filter(id__in=listacarrerass)
                data['carreraselect'] = carr if carr else ""
                data['nivselect'] = nivel if nivel else ""
                data['modalidadselect'] = modalidad if modalidad else ""
                data['cant'] = usuariosonline.count()
                data['nivel'] = NivelMalla.objects.filter(status=True)
                return render(request, "virtual_soporte_online/view.html", data)
            except Exception as ex:
                pass
