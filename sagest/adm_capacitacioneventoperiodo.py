# -*- coding: UTF-8 -*-
import json
import os
import pyqrcode
from googletrans import Translator
from datetime import datetime, date, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from settings import DEBUG
from xlwt import *
from decorators import secure_module
from sagest.forms import CapEventoPeriodoForm, CapInscribirForm, CapPeriodoForm, CapEventoForm, CapEnfocadaForm, \
    CapTurnoForm, CapInstructorForm, CapClaseForm, CapConfiguracionForm, CapAsistenciaForm
from sagest.models import CapEventoPeriodo, CapPeriodo, DistributivoPersona, CapCabeceraSolicitud, CapDetalleSolicitud, \
    CapEvento, CapEnfocada, CapTurno, CapInstructor, CapClase, CapConfiguracion, CapCabeceraAsistencia, \
    CapDetalleAsistencia, CapEventoPeriodoFirmas, DenominacionPuesto
from settings import PUESTO_ACTIVO_ID, SITE_STORAGE
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import BibliografiaProgramaAnaliticoAsignaturaForm, CapEventoPeriodoFirmasForm
from sga.funciones import MiPaginador, log, variable_valor, generar_nombre, suma_dias_habiles
from sga.models import Administrativo, Persona, Pais, Provincia, Canton, Parroquia, DIAS_CHOICES, CUENTAS_CORREOS
from django.template.context import Context
from django.db.models import Max, Q
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdfsaveqrcertificado
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret',login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    global ex
    data = {}
    lista = []
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']
        #PERIODO
        if action == 'addperiodo':
            try:
                form = CapPeriodoForm(request.POST, request.FILES)
                if form.is_valid():
                    nombres=form.cleaned_data['nombre']
                    if form.cleaned_data['fechainicio']< form.cleaned_data['fechafin']:
                        if CapPeriodo.objects.values('id').filter(nombre=nombres, status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                        periodo=CapPeriodo(nombre=form.cleaned_data['nombre'],
                                           descripcion=form.cleaned_data['descripcion'],
                                           abreviatura=form.cleaned_data['abreviatura'],
                                           fechainicio=form.cleaned_data['fechainicio'],
                                           fechafin=form.cleaned_data['fechafin'])

                        periodo.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("capacitacionTH_", newfile._name)
                            periodo.archivo = newfile
                            periodo.save(request)
                        log(u'Agrego Período de Evento: %s - [%s]' % (periodo,periodo.id), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Las fechas no concuerdan"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "mensaje":translator.translate(ex.__str__(),'es').text})

        elif action == 'editperiodo':
            try:
                form = CapPeriodoForm(request.POST,request.FILES)
                if form.is_valid():
                    periodo = CapPeriodo.objects.get(pk=int(request.POST['id']))
                    periodo.descripcion = form.cleaned_data['descripcion']
                    periodo.nombre = form.cleaned_data['nombre']
                    periodo.abreviatura = form.cleaned_data['abreviatura']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("capacitacionTH_", newfile._name)
                        periodo.archivo = newfile
                    if periodo.esta_cap_evento_periodo_activo():
                        periodo.save(request)
                        log(u'Editar Período de Evento: %s' % periodo, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        if form.cleaned_data['fechainicio'] < form.cleaned_data['fechafin']:
                            periodo.fechainicio = form.cleaned_data['fechainicio']
                            periodo.fechafin = form.cleaned_data['fechafin']
                            periodo.save(request)
                            log(u'Editar Período de Evento: %s - [%s]' % (periodo,periodo.id), request, "edit")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"La Fecha esta mal ingresados."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'LoadCargo':
            try:
                if 'id' in request.POST:
                    id = int(request.POST['id'])
                    capeven = DistributivoPersona.objects.filter(persona__id=id, status = True)

                    lista = []
                    for cap in capeven:
                        lista.append([cap.denominacionpuesto.id, cap.denominacionpuesto.descripcion])


                    return JsonResponse({"result": "ok", 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        elif action == 'delperiodo':
            try:
                periodo = CapPeriodo.objects.get(pk=int(request.POST['id']))
                if periodo.esta_cap_evento_periodo_activo():
                    return JsonResponse({"result": "bad","mensaje": u"No se puede Eliminar el Periodo, tiene planificacion de evento Activas.."})
                log(u'Elimino Período de Evento: %s - [%s]' % (periodo,periodo.id), request, "del")
                periodo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        # EVENTO
        elif action == 'addevento':
            try:
                form = CapEventoForm(request.POST)
                if form.is_valid():
                    if CapEvento.objects.values('id').filter(nombre=form.cleaned_data['nombre'], status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                    evento = CapEvento(nombre=form.cleaned_data['nombre'],
                                       tipocurso=form.cleaned_data['tipocurso'])
                    evento.save(request)
                    log(u'Agrego Evento: %s - [%s]' % (evento,evento.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editevento':
            try:
                form = CapEventoForm(request.POST)
                if form.is_valid():
                    evento = CapEvento.objects.get(pk=int(request.POST['id']))
                    evento.nombre = form.cleaned_data['nombre']
                    if not evento.esta_cap_evento_activo():
                        evento.tipocurso = form.cleaned_data['tipocurso']
                    evento.save(request)
                    log(u'Editar Evento: %s - [%s]' % (evento,evento.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delevento':
            try:
                evento = CapEvento.objects.get(pk=int(request.POST['id']))
                if evento.esta_cap_evento_activo():
                    return JsonResponse({"result": "bad","mensaje": u"No se puede Eliminar, se esta utilizando en Planificación de Eventos.."})
                log(u'Elimino Evento: %s - [%s]' % (evento,evento.id), request, "del")
                evento.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        #ENFOQUE
        elif action == 'addenfoque':
            try:
                form = CapEnfocadaForm(request.POST)
                if form.is_valid():
                    if CapEnfocada.objects.values('id').filter(nombre=form.cleaned_data['nombre'], status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                    enfo=CapEnfocada(nombre=form.cleaned_data['nombre'])
                    enfo.save(request)
                    log(u'Agrego Capacitación Enfoque: %s - [%s]' % (enfo,enfo.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editenfoque':
            try:
                form = CapEnfocadaForm(request.POST)
                if form.is_valid():
                    enfo = CapEnfocada.objects.get(pk=int(request.POST['id']))
                    enfo.nombre = form.cleaned_data['nombre']
                    enfo.save(request)
                    log(u'Editar Capacitación Enfoque: %s - [%s]' % (enfo,enfo.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delenfoque':
            try:
                enfo = CapEnfocada.objects.get(pk=int(request.POST['id']))
                if enfo.capeventoperiodo_set.values('id').filter(status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar, esta usado en planificación de evento."})
                log(u'Elimino Capacitación Enfoque: %s - [%s]' % (enfo,enfo.id), request, "del")
                enfo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        #TURNO
        elif action == 'addturno':
            try:
                form = CapTurnoForm(request.POST)
                if form.is_valid():
                    if CapTurno.objects.values('id').filter(turno=form.cleaned_data['turno'], status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El Turno ya existe."})
                    if CapTurno.objects.values('id').filter(horainicio=form.cleaned_data['horainicio'], status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La hora inicio ya existe."})
                    if CapTurno.objects.values('id').filter(horafin=form.cleaned_data['horafin'], status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La hora fin ya existe."})
                    if form.cleaned_data['horainicio']>form.cleaned_data['horafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"Las hora fin no debe ser mayor."})
                    datos = json.loads(request.POST['lista_items1'])
                    horas=0
                    for elemento in datos:
                        horas=float(elemento['horas'])
                    turno=CapTurno(turno=request.POST['turno'],
                                   horainicio=form.cleaned_data['horainicio'],
                                   horafin=form.cleaned_data['horafin'],
                                   horas=horas)
                    turno.save(request)
                    log(u'Agrego Turno de Capacitación: %s - [%s]' % (turno,turno.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editturno':
            try:
                form = CapTurnoForm(request.POST)
                if form.is_valid():
                    turno = CapTurno.objects.get(pk=int(request.POST['id']))
                    if CapTurno.objects.values('id').filter(horainicio=form.cleaned_data['horainicio'], status=True).exclude(pk=turno.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La hora inicio ya existe."})
                    if CapTurno.objects.values('id').filter(horafin=form.cleaned_data['horafin'], status=True).exclude(pk=turno.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La hora fin ya existe."})
                    if form.cleaned_data['horainicio']>form.cleaned_data['horafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"Las hora fin no debe ser mayor."})
                    datos = json.loads(request.POST['lista_items1'])
                    horas = 0
                    for elemento in datos:
                        horas = float(elemento['horas'])
                    turno.horainicio = form.cleaned_data['horainicio']
                    turno.horafin = form.cleaned_data['horafin']
                    turno.horas= horas
                    turno.save(request)
                    log(u'Editar Turno de Capacitación: %s - [%s]' % (turno,turno.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delturno':
            try:
                turno = CapTurno.objects.get(pk=int(request.POST['id']))
                if turno.capclase_set.values('id').filter(status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, se esta usando en horarios"})
                log(u'Elimino Turno en Capacitación: %s - [%s]' % (turno,turno.id), request, "del")
                turno.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        #CONFIGURACION
        elif action == 'configuracion':
            try:
                form = CapConfiguracionForm(request.POST)
                if form.is_valid():
                    if not form.cleaned_data['minasistencia'] > 0 and not form.cleaned_data['minnota'] > 0:
                        return JsonResponse({"result": "bad", "mensaje": u"La minima nota y asistencia debe ser mayor a cero ."})
                    configuracion = CapConfiguracion.objects.filter()
                    if configuracion.values('id').exists():
                        configuracion=configuracion[0]
                        log(u'Edito configuración de capacitación UATH: %s' % configuracion, request, "edit")
                    else:
                        configuracion = CapConfiguracion()
                        log(u'Adiciono configuración de capacitación UATH: %s' % configuracion, request, "add")
                    revisado = DistributivoPersona.objects.get(pk=form.cleaned_data['revisado'])
                    aprobado1 = DistributivoPersona.objects.get(pk=form.cleaned_data['aprobado1'])
                    aprobado2 = DistributivoPersona.objects.get(pk=form.cleaned_data['aprobado2'])
                    aprobado3 = DistributivoPersona.objects.get(pk=form.cleaned_data['aprobado3'])
                    configuracion.minasistencia = form.cleaned_data['minasistencia']
                    configuracion.minnota = form.cleaned_data['minnota']
                    configuracion.revisado = revisado.persona
                    configuracion.aprobado1 = aprobado1.persona
                    configuracion.aprobado2 = aprobado2.persona
                    configuracion.aprobado3 = aprobado3.persona
                    configuracion.denominacionrevisado = revisado.denominacionpuesto
                    configuracion.denominacionaprobado1 = aprobado1.denominacionpuesto
                    configuracion.denominacionaprobado2 = aprobado2.denominacionpuesto
                    configuracion.denominacionaprobado3 = aprobado3.denominacionpuesto
                    configuracion.abreviaturadepartamento = form.cleaned_data['abreviaturadepartamento']
                    configuracion.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        #EVENTO PERIODO
        elif action == 'addperiodoevento':
            try:
                form = CapEventoPeriodoForm(request.POST)
                if form.is_valid():
                    periodo=CapPeriodo.objects.get(pk=int(request.POST['periodo']))
                    if not form.cleaned_data['responsable'] > 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Ingrese un responsable."})
                    if not form.cleaned_data['fechainicio'] >=periodo.fechainicio or not form.cleaned_data['fechafin'] <= periodo.fechafin:
                        return JsonResponse({"result": "bad", "mensaje": u"Las fecha no puede ser mayor a las fecha del periodo."})
                    if not form.cleaned_data['fechainicio'] <= form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ser mayor la fecha de inicio."})
                    if not form.cleaned_data['regimenlaboral']:
                        return JsonResponse({"result": "bad", "mensaje": u"Ingrese un regimen laboral."})
                    configuracion=CapConfiguracion.objects.all()
                    evento=CapEventoPeriodo(periodo=periodo,
                                            capevento=form.cleaned_data['capevento'],
                                            departamento=form.cleaned_data['departamento'],
                                            horas= form.cleaned_data['horas'],
                                            horasautonoma=form.cleaned_data['horasautonoma'],
                                            horaspropedeutica=form.cleaned_data['horaspropedeutica'],
                                            objetivo=form.cleaned_data['objetivo'],
                                            observacion=form.cleaned_data['observacion'],
                                            minasistencia=form.cleaned_data['minasistencia'],
                                            minnota=form.cleaned_data['minnota'],
                                            regimenlaboral=form.cleaned_data['regimenlaboral'],
                                            tipoparticipacion=form.cleaned_data['tipoparticipacion'],
                                            contextocapacitacion=form.cleaned_data['contextocapacitacion'],
                                            modalidad=form.cleaned_data['modalidad'],
                                            tipocertificacion=form.cleaned_data['tipocertificacion'],
                                            tipocapacitacion=form.cleaned_data['tipocapacitacion'],
                                            pais=form.cleaned_data['pais'],
                                            provincia=form.cleaned_data['provincia'],
                                            canton=form.cleaned_data['canton'],
                                            parroquia=form.cleaned_data['parroquia'],
                                            areaconocimiento=form.cleaned_data['areaconocimiento'],
                                            subareaconocimiento=form.cleaned_data['subareaconocimiento'],
                                            subareaespecificaconocimiento=form.cleaned_data['subareaespecificaconocimiento'],
                                            aula=form.cleaned_data['aula'],
                                            fechainicio=form.cleaned_data['fechainicio'],
                                            fechafin=form.cleaned_data['fechafin'],
                                            cupo=form.cleaned_data['cupo'],
                                            enfoque=form.cleaned_data['enfoque'],
                                            visualizar=form.cleaned_data['visualizar'],
                                            contenido=form.cleaned_data['contenido'],
                                            revisado = configuracion[0].revisado,
                                            aprobado1 = configuracion[0].aprobado1,
                                            aprobado2 = configuracion[0].aprobado2,
                                            aprobado3=configuracion[0].aprobado3,
                                            denominacionrevisado = configuracion[0].denominacionrevisado,
                                            denominacionaprobado1 = configuracion[0].denominacionaprobado1,
                                            denominacionaprobado2 = configuracion[0].denominacionaprobado2,
                                            denominacionaprobado3=configuracion[0].denominacionaprobado3,
                                            codigo=form.cleaned_data['codigo'],
                                            abreviaturadepartamento=configuracion[0].abreviaturadepartamento,
                                            responsable=Administrativo.objects.get(pk=form.cleaned_data['responsable']).persona,
                                            observacionreporte=form.cleaned_data['observacionreporte'])
                    evento.save(request)
                    log(u'Agrego Planificación de Evento: %s - [%s] ' % (evento,evento.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editperiodoevento':
            try:
                form = CapEventoPeriodoForm(request.POST)
                if form.is_valid():
                    evento = CapEventoPeriodo.objects.get(pk=int(request.POST['id']))
                    if not form.cleaned_data['fechainicio']>=evento.periodo.fechainicio or not form.cleaned_data['fechafin']<=evento.periodo.fechafin:
                        return JsonResponse({"result": "bad", "mensaje": u"Las fecha no puede ser mayor a las fecha del periodo."})
                    if not form.cleaned_data['fechainicio'] <= form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ser mayor la fecha de inicio."})
                    evento.capevento = form.cleaned_data['capevento']
                    evento.horas = form.cleaned_data['horas']
                    evento.horasautonoma = form.cleaned_data['horasautonoma']
                    evento.departamento = form.cleaned_data['departamento']
                    evento.horaspropedeutica = form.cleaned_data['horaspropedeutica']
                    evento.objetivo = form.cleaned_data['objetivo']
                    evento.observacion = form.cleaned_data['observacion']
                    evento.minasistencia = form.cleaned_data['minasistencia']
                    evento.minnota = form.cleaned_data['minnota']
                    evento.folder = form.cleaned_data['folder']
                    if not evento.exiten_inscritos():
                        evento.regimenlaboral = form.cleaned_data['regimenlaboral']
                    evento.aula = form.cleaned_data['aula']
                    evento.fechainicio = form.cleaned_data['fechainicio']
                    evento.fechafin = form.cleaned_data['fechafin']
                    evento.tipoparticipacion = form.cleaned_data['tipoparticipacion']
                    evento.contextocapacitacion = form.cleaned_data['contextocapacitacion']
                    evento.modalidad = form.cleaned_data['modalidad']
                    evento.tipocertificacion = form.cleaned_data['tipocertificacion']
                    evento.tipocapacitacion = form.cleaned_data['tipocapacitacion']
                    evento.pais = form.cleaned_data['pais']
                    evento.provincia = form.cleaned_data['provincia']
                    evento.canton = form.cleaned_data['canton']
                    evento.parroquia = form.cleaned_data['parroquia']
                    evento.areaconocimiento = form.cleaned_data['areaconocimiento']
                    evento.subareaconocimiento = form.cleaned_data['subareaconocimiento']
                    evento.subareaespecificaconocimiento = form.cleaned_data['subareaespecificaconocimiento']
                    evento.visualizar = form.cleaned_data['visualizar']
                    evento.contenido = form.cleaned_data['contenido']
                    evento.enfoque = form.cleaned_data['enfoque']
                    evento.cupo = form.cleaned_data['cupo']
                    evento.responsable = Administrativo.objects.get(pk=form.cleaned_data['responsable']).persona
                    if form.cleaned_data['actualizar']:
                        configuracion = CapConfiguracion.objects.all()
                        evento.revisado = configuracion[0].revisado
                        evento.aprobado1 = configuracion[0].aprobado1
                        evento.aprobado2 = configuracion[0].aprobado2
                        evento.aprobado3 = configuracion[0].aprobado3
                        evento.abreviaturadepartamento = configuracion[0].abreviaturadepartamento
                        evento.denominacionrevisado = configuracion[0].denominacionrevisado
                        evento.denominacionaprobado1 = configuracion[0].denominacionaprobado1
                        evento.denominacionaprobado2 = configuracion[0].denominacionaprobado2
                        evento.denominacionaprobado3 = configuracion[0].denominacionaprobado3
                        log(u'Actualizo los aprobados, revisar y abreviaturas del departamento en el evento: %s [%s] - %s - %s - %s - %s - %s - %s - %s - %s - %s ' % (evento, evento.id, evento.revisado, evento.aprobado1, evento.aprobado2, evento.aprobado3, evento.abreviaturadepartamento, evento.denominacionrevisado, evento.denominacionaprobado1, evento.denominacionaprobado2, evento.denominacionaprobado3), request, "edit")
                    evento.codigo=form.cleaned_data['codigo']
                    evento.observacionreporte = form.cleaned_data['observacionreporte']
                    evento.save(request)
                    log(u'Edito Planificación de Evento: %s - [%s] ' % (evento,evento.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delperiodoevento':
            try:
                evento = CapEventoPeriodo.objects.get(pk=int(request.POST['id']))
                if evento.puede_eliminar_planificacion_evento():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, porque tiene "+evento.puede_eliminar_planificacion_evento()+" activos"})
                log(u'Elimino Evento Periodo: %s' % evento, request, "del")
                evento.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'updatecupo':
            try:
                evento = CapEventoPeriodo.objects.get(pk=int(request.POST['eid']))
                valor = int(request.POST['vc'])
                if valor > 999:
                    return JsonResponse({"result": "bad", "mensaje": u"No puede establecer un cupo menor a" + str(999 + 1)})
                if valor < evento.contar_inscripcion_evento_periodo():
                    return JsonResponse({"result": "bad", "mensaje": u"El cupo no puede ser menor a la cantidad de inscrito"})
                cupoanterior = evento.cupo
                evento.cupo = valor
                evento.save(request)
                log(u'Actualizo cupo a evento: %s cupo anterior: %s cupo actual: %s' % (evento, str(cupoanterior), str(evento.cupo)), request, "add")
                return JsonResponse({'result': 'ok', 'valor': evento.cupo})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al eliminar los datos."})

        elif action == 'addinscribir':
            try:
                f = CapInscribirForm(request.POST)
                if f.is_valid():
                    listadatos = json.loads(request.POST['lista_items1'])
                    if listadatos:
                        listadistributivo = DistributivoPersona.objects.filter(id__in=[int(datos['iddistributivo']) for datos in listadatos]) if listadatos else []
                        for distributivo in listadistributivo:
                            if not CapEventoPeriodo.objects.get(pk=int(request.POST['eventoperiodo'])).hay_cupo_inscribir():
                                return JsonResponse({"result": "bad", "mensaje": u"No hay cupo para continuar adicionando"})
                            if CapCabeceraSolicitud.objects.values('id').filter(participante=distributivo.persona, capeventoperiodo_id=int(request.POST['eventoperiodo'])).exists():
                                return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra inscrito o está en estado solicitado"})
                            cabecera = CapCabeceraSolicitud(capeventoperiodo_id=int(request.POST['eventoperiodo']),
                                                            solicita=persona,
                                                            fechasolicitud=datetime.now().date(),
                                                            estadosolicitud=variable_valor('APROBADO_CAPACITACION'),
                                                            fechaultimaestadosolicitud=datetime.now().date(),
                                                            participante=distributivo.persona)
                            cabecera.save(request)
                            log(u'Ingreso Cabecera Inscribio en Evento: %s (participante: %s )(estado solicitud : %s) - [%s]' % (cabecera,cabecera.participante,cabecera.estadosolicitud,cabecera.id), request, "add")
                            detalle = CapDetalleSolicitud(cabecera=cabecera,
                                                          aprueba=persona,
                                                          observacion=f.cleaned_data['observacion'],
                                                          fechaaprobacion=datetime.now().date(),
                                                          estado=2)
                            detalle.save(request)
                            detalle.mail_notificar_talento_humano(request.session['nombresistema'], True)
                            log(u'Ingreso Detalle Inscribio de Evento : %s  (fechaaprobacion: %s)-[%id]' % (detalle,detalle.fechaaprobacion,detalle.id), request, "add")
                    else:
                        distributivo=DistributivoPersona.objects.get(id=f.cleaned_data['participante'])
                        if CapCabeceraSolicitud.objects.values('id').filter(participante=distributivo.persona,capeventoperiodo_id=int(request.POST['eventoperiodo'])).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra inscrito o está en estado solicitado"})
                        if not CapEventoPeriodo.objects.get(pk=int(request.POST['eventoperiodo'])).hay_cupo_inscribir():
                            return JsonResponse({"result": "bad", "mensaje": u"No hay cupo para continuar adicionando"})
                        cabecera = CapCabeceraSolicitud(capeventoperiodo_id=int(request.POST['eventoperiodo']),
                                                        solicita=persona,
                                                        fechasolicitud=datetime.now().date(),
                                                        estadosolicitud=variable_valor('APROBADO_CAPACITACION'),
                                                        fechaultimaestadosolicitud=datetime.now(),
                                                        participante=distributivo.persona)
                        cabecera.save(request)
                        log(u'Ingreso Cabecera Inscribio en Evento : %s' % cabecera, request, "add")
                        detalle = CapDetalleSolicitud(cabecera=cabecera,
                                                      aprueba=persona,
                                                      observacion=f.cleaned_data['observacion'],
                                                      fechaaprobacion=datetime.now().date(),
                                                      estado=2)
                        detalle.save(request)
                        detalle.mail_notificar_talento_humano(request.session['nombresistema'], True)
                        log(u'Ingreso Detalle Inscribio de Evento : %s  (fechaaprobacion: %s)-[%id]' % (detalle,detalle.fechaaprobacion,detalle.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Llene todos los campos"})

        elif action == 'delinscrito':
            try:
                cabecera = CapCabeceraSolicitud.objects.get(pk=int(request.POST['id']))
                if not cabecera.puede_eliminar_inscrito():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, el inscrito ya cuenta con asistencia"})
                cabecera.capdetallesolicitud_set.all().delete()
                # cabecera.mail_notificar_talento_humano(request.session['nombresistema'])
                log(u'Elimino Inscrito cabecera y sus detalle de Solicitud : %s' % cabecera, request, "del")
                cabecera.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'bloqueopublicacion':
            try:
                evento = CapEventoPeriodo.objects.get(pk=request.POST['id'])
                evento.visualizar = True if request.POST['val'] == 'y' else False
                evento.save(request)
                log(u'Visualiza o no en capacitacion evento periodo : %s (%s)' % (evento,evento.visualizar), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        elif action == 'reporte_asistencia':
            try:
                persona_cargo_tercernivel=None
                revisadotercernivel=None
                aprobado1tercernivel=None
                aprobado2tercernivel=None
                data['idp'] = request.POST['id']
                data['evento'] = evento = CapEventoPeriodo.objects.get(status=True, id=int(request.POST['id']))
                data['fechas'] = fechas = evento.todas_fechas_asistencia()
                lista_fechas = CapCabeceraAsistencia.objects.values_list("fecha").filter(clase__capeventoperiodo=evento).distinct('fecha').order_by('fecha')
                contarcolumnas= CapCabeceraAsistencia.objects.filter(Q(clase__capeventoperiodo=evento)& Q(fecha__in=lista_fechas)).count()+6
                data['vertical_horizontal']= True if contarcolumnas>10 else False
                data['ubicacion_promedio'] = contarcolumnas-3
                data['elabora_persona'] = persona
                cargo=None
                if DistributivoPersona.objects.values('id').filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,status=True).exists():
                    cargo = DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,status=True)[0]
                data['persona_cargo'] = cargo
                titulo = persona.titulacion_principal_senescyt_registro()
                if not titulo == '':
                    titulo_3 = persona.titulacion_set.filter(titulo__nivel=3).order_by( '-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                    titulo_4 = persona.titulacion_set.filter(titulo__nivel=4).order_by('-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                    if titulo_4:
                        titulo = titulo_4[0]
                    elif titulo_3:
                        titulo = titulo_3[0]
                if not titulo == '':
                    persona_cargo_tercernivel = persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if titulo.titulo.nivel_id == 4 else None
                data['persona_cargo_titulo'] = titulo
                revisado = ''
                if evento.revisado:
                    revisado = evento.revisado.titulacion_principal_senescyt_registro()
                data['revisado'] = revisado
                revisadotercernivel = ''
                if evento.revisado:
                    revisadotercernivel= evento.revisado.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if revisado.titulo.nivel_id == 4 else None
                data['aprobado1'] = aprobado1 = evento.aprobado1.titulacion_principal_senescyt_registro()
                if aprobado1:
                    aprobado1tercernivel = evento.aprobado1.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if aprobado1.titulo.nivel_id == 4 else None
                data['aprobado2'] = aprobado2 = evento.aprobado2.titulacion_principal_senescyt_registro()
                if aprobado2:
                    aprobado2tercernivel= evento.aprobado2.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if aprobado2.titulo.nivel_id == 4 else None
                data['persona_cargo_tercernivel']=persona_cargo_tercernivel
                data['revisadotercernivel']=revisadotercernivel
                data['aprobado1tercernivel']=aprobado1tercernivel
                data['aprobado2tercernivel']=aprobado2tercernivel
                ultima_fecha=fechas.order_by('-fecha')[0].fecha
                if ultima_fecha.weekday() >= 0 and ultima_fecha.weekday() <= 3 or ultima_fecha.weekday() == 6:
                    dias = timedelta(days=1)
                else:
                    dias = timedelta(days=2)
                data['fecha_corte'] = ultima_fecha + dias
                return conviert_html_to_pdf('adm_capacitacioneventoperiodo/informe_asistencia_pdf.html',{'pagesize': 'A4', 'data': data})
            except Exception as ex:
                pass

        elif action == 'ver_certificado_pdf':
            try:
                persona_cargo_tercernivel = None
                cargo = None
                tamano = 0
                cabecera = CapCabeceraSolicitud.objects.get(status=True, id=int(request.POST['id']))
                data['listadofirmas'] = listadofirmas = cabecera.capeventoperiodo.capeventoperiodofirmas_set.filter(status=True)
                firma1 = None
                firma2 = None
                firma3 = None

                data['viceacad'] = viceacad = Persona.objects.get(pk=26905)
                data['viceacadpuesto'] = viceacadpuesto = DenominacionPuesto.objects.get(pk=115)

                cargo_firama1 = ''
                cargo_firama2 = ''
                cargo_firama3 = ''

                if listadofirmas.filter(tipofirmaevento=1):
                    firma1 = listadofirmas.filter(tipofirmaevento=1)[0]

                if listadofirmas.filter(tipofirmaevento=2):
                    firma2 = listadofirmas.filter(tipofirmaevento=2)[0]
                if listadofirmas.filter(tipofirmaevento=3):
                    firma3 = listadofirmas.filter(tipofirmaevento=3)[0]

                data['firma1'] = firma1
                data['firma2'] = firma2
                data['firma3'] = firma3
                data['evento'] = evento = cabecera.capeventoperiodo

                evento.actualizar_folio()

                cargo_firama1 = ''
                cargo_firama2 = ''
                cargo_firama3 = ''

                if firma1:
                    if firma1.cargo:
                        cargo_firama1 = firma1.cargo.descripcion

                if firma2:
                    if firma2.cargo:
                        cargo_firama2 = firma2.cargo.descripcion

                if firma3:
                    if firma3.cargo:
                        cargo_firama3 = firma3.cargo.descripcion

                data['cargo_firama1'] = cargo_firama1
                data['cargo_firama2'] = cargo_firama2
                data['cargo_firama3'] = cargo_firama3

                firmacertificado = 'robles'
                fechacambio = (datetime(2019, 11, 1, 0, 0, 0)).date()
                if evento.fechafin >= fechacambio:
                    firmacertificado = 'firmaguillermo'
                data['firmacertificado'] = firmacertificado
                data['elabora_persona'] = persona
                if DistributivoPersona.objects.values('id').filter(persona_id=persona,
                                                                   estadopuesto__id=PUESTO_ACTIVO_ID,
                                                                   status=True).exists():
                    cargo = DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,
                                                               status=True)[0]
                data['persona_cargo'] = cargo
                titulo = persona.titulacion_principal_senescyt_registro()
                if not titulo == '':
                    titulo_3 = persona.titulacion_set.filter(titulo__nivel=3).order_by(
                        '-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                    titulo_4 = persona.titulacion_set.filter(titulo__nivel=4).order_by(
                        '-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                    if titulo_4:
                        titulo = titulo_4[0]
                    elif titulo_3:
                        titulo = titulo_3[0]
                if not titulo == '':
                    persona_cargo_tercernivel = \
                        persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[
                            0] if titulo.titulo.nivel_id == 4 else None
                data['persona_cargo_titulo'] = titulo
                data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
                data['inscrito'] = cabecera
                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                       "octubre", "noviembre", "diciembre"]

                fechainicio = evento.fechainicio
                fechafin = evento.fechafin
                #fechacertificado = fechafin + timedelta(days=1)

                fechacertificado = suma_dias_habiles(fechafin, 7)

                data['fecha'] = u"Milagro, %s de %s del %s" % (
                    fechacertificado.day, str(mes[fechacertificado.month - 1]), fechacertificado.year)

                #data['fecha'] = u"Milagro, %s de %s del %s" % (
                #    datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)

                if fechainicio == fechafin:
                    fechascapacitacion = "el %s de %s del %s" % (fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year)
                elif fechainicio.month != fechafin.month:
                    if fechainicio.year == fechafin.year:
                        fechascapacitacion = "del %s de %s al %s de %s del %s" % (fechainicio.day, str(mes[fechainicio.month - 1]), fechafin.day, str(mes[fechafin.month - 1]), fechafin.year)
                    else:
                        fechascapacitacion = "del %s de %s del %s al %s de %s del %s" % (fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year, fechafin.day, str(mes[fechafin.month - 1]), fechafin.year)
                else:
                    fechascapacitacion = "del %s al %s de %s del %s" % (fechainicio.day, fechafin.day, str(mes[fechainicio.month - 1]), fechainicio.year)

                data['fechascapacitacion'] = fechascapacitacion

                data['listado_contenido'] = listado = evento.contenido.split("\n")
                if evento.objetivo.__len__() < 290:
                    if listado.__len__() < 21:
                        tamano = 120
                    elif listado.__len__() < 35:
                        tamano = 100
                    elif listado.__len__() < 41:
                        tamano = 70
                data['controlar_bajada_logo'] = tamano

                url_path = 'http://127.0.0.1:8000'
                if not DEBUG:
                    url_path = 'https://sga.unemi.edu.ec'

                qrname = 'uath_qr_certificado_' + str(cabecera.id)
                # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                url = pyqrcode.create(f'{url_path}//media/qrcode/certificados/' + qrname + '.pdf')
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = 'qr' + qrname
                data['url_qr'] = f'{url_path}/media/qrcode/certificados/qr{qrname}.png'

                return conviert_html_to_pdf(
                    'adm_capacitacioneventoperiodo/certificado_individual_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )

            except Exception as ex:
                pass

        elif action == 'enviar_certificado_pdf':
            try:
                persona_cargo_tercernivel=None
                cargo = None
                tamano=0
                cabecera = CapCabeceraSolicitud.objects.get(status=True, id=int(request.POST['id']))
                data['listadofirmas'] = listadofirmas = cabecera.capeventoperiodo.capeventoperiodofirmas_set.filter(
                    status=True)
                firma1 = None
                firma2 = None
                firma3 = None

                cargo_firama1 = ''
                cargo_firama2 = ''
                cargo_firama3 = ''

                if listadofirmas.filter(tipofirmaevento=1):
                    firma1 = listadofirmas.filter(tipofirmaevento=1)[0]
                if listadofirmas.filter(tipofirmaevento=2):
                    firma2 = listadofirmas.filter(tipofirmaevento=2)[0]
                if listadofirmas.filter(tipofirmaevento=3):
                    firma3 = listadofirmas.filter(tipofirmaevento=3)[0]
                data['firma1'] = firma1
                data['firma2'] = firma2
                data['firma3'] = firma3
                data['evento'] = evento = cabecera.capeventoperiodo

                if firma1:
                    if firma1.cargo:
                        cargo_firama1 = firma1.cargo.descripcion

                if firma2:
                    if firma2.cargo:
                        cargo_firama2 = firma2.cargo.descripcion

                if firma3:
                    if firma3.cargo:
                        cargo_firama3 = firma3.cargo.descripcion

                data['cargo_firama1'] = cargo_firama1
                data['cargo_firama2'] = cargo_firama2
                data['cargo_firama3'] = cargo_firama3

                evento.actualizar_folio()
                # firmacertificado = 'robles'
                # fechacambio = (datetime(2019, 11, 1, 0, 0, 0)).date()
                # if evento.fechafin >= fechacambio:
                #     firmacertificado = 'firmaguillermo'

                firmacertificado = 'robles'
                fechacambio = (datetime(2019, 11, 1, 0, 0, 0)).date()
                if evento.fechafin >= fechacambio and evento.fechafin.year < 2021:
                    firmacertificado = 'firmaguillermo'
                else:
                    if evento.fechafin.year > 2020:
                        firmacertificado = 'firmachacon'

                data['firmacertificado'] = firmacertificado
                
                data['elabora_persona'] = persona
                if DistributivoPersona.objects.values('id').filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,status=True).exists():
                    cargo = DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,status=True)[0]
                data['persona_cargo'] = cargo
                titulo = persona.titulacion_principal_senescyt_registro()
                if not titulo == '':
                    titulo_3 = persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                    titulo_4 = persona.titulacion_set.filter(titulo__nivel=4).order_by('-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                    if titulo_4:
                        titulo = titulo_4[0]
                    elif titulo_3:
                        titulo = titulo_3[0]
                if not titulo == '':
                    persona_cargo_tercernivel = persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if titulo.titulo.nivel_id == 4 else None
                data['persona_cargo_titulo'] = titulo
                data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
                data['inscrito'] = cabecera
                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre","octubre", "noviembre", "diciembre"]

                # data['fecha'] =  u"Milagro, %s de %s del %s" % (datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)

                fechainicio = evento.fechainicio
                fechafin = evento.fechafin
                # fechacertificado = fechafin + timedelta(days=1)

                fechacertificado = suma_dias_habiles(fechafin, 7)

                data['fecha'] = u"Milagro, %s de %s del %s" % (
                    fechacertificado.day, str(mes[fechacertificado.month - 1]), fechacertificado.year)

                # data['fecha'] = u"Milagro, %s de %s del %s" % (
                #    datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)

                if fechainicio == fechafin:
                    fechascapacitacion = "el %s de %s del %s" % (
                        fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year)
                elif fechainicio.month != fechafin.month:
                    if fechainicio.year == fechafin.year:
                        fechascapacitacion = "del %s de %s al %s de %s del %s" % (
                            fechainicio.day, str(mes[fechainicio.month - 1]), fechafin.day, str(mes[fechafin.month - 1]),
                            fechafin.year)
                    else:
                        fechascapacitacion = "del %s de %s del %s al %s de %s del %s" % (
                            fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year, fechafin.day,
                            str(mes[fechafin.month - 1]), fechafin.year)
                else:
                    fechascapacitacion = "del %s al %s de %s del %s" % (
                        fechainicio.day, fechafin.day, str(mes[fechainicio.month - 1]), fechainicio.year)

                data['fechascapacitacion'] = fechascapacitacion

                data['listado_contenido']= listado = evento.contenido.split("\n")
                if evento.objetivo.__len__()<290:
                    if listado.__len__() < 21:
                        tamano = 120
                    elif listado.__len__() < 35:
                        tamano = 100
                    elif listado.__len__() < 41:
                        tamano = 70
                data['controlar_bajada_logo'] = tamano


                data['viceacad'] = viceacad = Persona.objects.get(pk=26905)
                data['viceacadpuesto'] = viceacadpuesto = DenominacionPuesto.objects.get(pk=115)
                url_path = 'http://127.0.0.1:8000'
                if not DEBUG:
                    url_path = 'https://sga.unemi.edu.ec'
                qrname = 'uath_qr_certificado_' + str(cabecera.id)
                # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/certificados/' + qrname + '.pdf')
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = 'qr' + qrname
                data['url_qr'] = f'{url_path}/media/qrcode/certificados/qr{qrname}.png'

                valida = conviert_html_to_pdfsaveqrcertificado(
                    'adm_capacitacioneventoperiodo/certificado_individual_pdf.html',
                    {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                )

                if valida:
                    os.remove(rutaimg)
                    cabecera.rutapdf = 'qrcode/certificados/' + qrname + '.pdf'
                    cabecera.notificado = True
                    cabecera.fechanotifica = datetime.now().date()
                    cabecera.personanotifica = persona
                    cabecera.save(request)
                    asunto = u"CERTIFICADO - " + cabecera.capeventoperiodo.capevento.nombre

                    #micorreo = Persona.objects.get(cedula='0923704928')
                    # micorreo.lista_emails_envio(), <- esto va dentro del send_html_mail

                    # correosga = CUENTAS_CORREOS[0][1]
                    # correosagest = CUENTAS_CORREOS[1][1]

                    send_html_mail(asunto,
                                   "emails/notificar_certificado_uath.html",
                                   {'sistema': request.session['nombresistema'],
                                    'inscrito': cabecera,
                                    'evento': evento
                                    },
                                   #micorreo.lista_emails_envio(),
                                   cabecera.participante.lista_emails_envio(),
                                   [],
                                   cuenta=CUENTAS_CORREOS[1][1])

                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte."})

            except Exception as ex:
                pass

        #INSTRUCTOR
        elif action == 'addinstructor':
            try:
                form = CapInstructorForm(request.POST)
                if form.is_valid():
                    if CapInstructor.objects.values('id').filter(instructor=form.cleaned_data['instructor'],capeventoperiodo_id=int(request.POST['eventoperiodo']), status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                    instructor=CapInstructor(capeventoperiodo_id=int(request.POST['eventoperiodo']),
                                             instructor_id=form.cleaned_data['instructor'],
                                             tipo=form.cleaned_data['tipo'],
                                             instructorprincipal=form.cleaned_data['instructorprincipal'])
                    instructor.save(request)
                    if form.cleaned_data['instructorprincipal']==True and CapInstructor.objects.values('id').filter(capeventoperiodo=instructor.capeventoperiodo,status=True,instructorprincipal=True).exclude(pk=instructor.id).exists():
                        editarprincipales=CapInstructor.objects.filter(capeventoperiodo=instructor.capeventoperiodo, status=True,instructorprincipal=True).exclude(pk=instructor.id)
                        for editarprincipal in editarprincipales:
                            editarprincipal.instructorprincipal=False
                            editarprincipal.save(request)
                            log(u'Edito Instructor Principan en Capacitacion Instructor: %s - [%s]' % (editarprincipal, editarprincipal.id), request,"edit")
                    log(u'Agrego Capacitacion Instructor: %s - [%s]' % (instructor,instructor.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editinstructor':
            try:
                form = CapInstructorForm(request.POST)
                if form.is_valid():
                    instructor = CapInstructor.objects.get(pk=int(request.POST['id']))
                    if CapInstructor.objects.values('id').filter(instructor=form.cleaned_data['instructor'],capeventoperiodo=instructor.capeventoperiodo,status=True).exclude(pk=instructor.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                    if form.cleaned_data['instructorprincipal']==True and CapInstructor.objects.values('id').filter(capeventoperiodo=instructor.capeventoperiodo,status=True,instructorprincipal=True).exclude(pk=instructor.id).exists():
                        editarprincipales=CapInstructor.objects.filter(capeventoperiodo=instructor.capeventoperiodo, status=True,instructorprincipal=True).exclude(pk=instructor.id)
                        for editarprincipal in editarprincipales:
                            editarprincipal.instructorprincipal=False
                            editarprincipal.save(request)
                            log(u'Edito Instructor Principan en Capacitacion Instructor: %s - [%s]' % (editarprincipal, editarprincipal.id), request, "edit")
                    instructor.instructor_id = form.cleaned_data['instructor']
                    instructor.tipo = form.cleaned_data['tipo']
                    instructor.instructorprincipal = form.cleaned_data['instructorprincipal']
                    instructor.save(request)
                    log(u'Editar Capacitación Instructor: %s - [%s]' % (instructor,instructor.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delinstructor':
            try:
                enfo = CapInstructor.objects.get(pk=int(request.POST['id']))
                log(u'Elimino Capacitación Instructor: %s' % enfo, request, "del")
                enfo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        # HORARIOS
        elif action == 'addclase':
            try:
                form = CapClaseForm(request.POST)
                if form.is_valid():
                    periodo = CapEventoPeriodo.objects.get(id=int(request.POST['cepid']))
                    if CapClase.objects.values('id').filter(capeventoperiodo_id=int(request.POST['cepid']),dia=form.cleaned_data['dia'], turno=form.cleaned_data['turno'],fechainicio=form.cleaned_data['fechainicio'],fechafin=form.cleaned_data['fechafin'], status=True).exists():
                        return JsonResponse({"result": "bad","mensaje": u"Hay una Clase que existe con las misma fechas y turno."})
                    if not form.cleaned_data['fechainicio'] >= periodo.periodo.fechainicio and form.cleaned_data['fechafin'] <= periodo.periodo.fechafin:
                        return JsonResponse({"result": "bad","mensaje": u"Las fecha no puede ser mayor a las fecha del periodo."})
                    if not form.cleaned_data['fechainicio'] <= form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ser mayor la fecha de inicio."})
                    if form.cleaned_data['fechainicio'] == form.cleaned_data['fechafin']:
                        if not int(form.cleaned_data['dia']) == form.cleaned_data['fechainicio'].weekday()+1:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha no concuerdan con el dia."})
                    clase = CapClase(capeventoperiodo_id=int(request.POST['cepid']),
                                     turno=form.cleaned_data['turno'],
                                     dia=form.cleaned_data['dia'],
                                     fechainicio=form.cleaned_data['fechainicio'],
                                     fechafin=form.cleaned_data['fechafin'])
                    clase.save(request)
                    log(u'Adicionado horario de Evento: %s' % clase, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editclase':
            try:
                form = CapClaseForm(request.POST)
                if form.is_valid():
                    clase = CapClase.objects.get(pk=int(request.POST['claseid']))
                    if CapClase.objects.values('id').filter(capeventoperiodo=clase.capeventoperiodo, dia=clase.dia,turno=clase.turno, fechainicio=form.cleaned_data['fechainicio'],fechafin=form.cleaned_data['fechafin'], status=True).exclude(pk=clase.id).exists():
                        return JsonResponse({"result": "bad","mensaje": u"Hay una Clase que existe con las misma fechas y turno."})
                    if not form.cleaned_data['fechainicio'] >= clase.capeventoperiodo.fechainicio and form.cleaned_data['fechafin'] <= clase.capeventoperiodo.fechafin:
                        return JsonResponse({"result": "bad","mensaje": u"Las fecha no puede ser mayor a las fecha del periodo."})
                    if not form.cleaned_data['fechainicio'] <= form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ser mayor la fecha de inicio."})
                    if form.cleaned_data['fechainicio'] == form.cleaned_data['fechafin']:
                        if not clase.dia == form.cleaned_data['fechainicio'].weekday()+1:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha no concuerdan con el dia."})
                    clase.fechainicio = form.cleaned_data['fechainicio']
                    clase.fechafin = form.cleaned_data['fechafin']
                    clase.save(request)
                    log(u'Edito horario de Evento: %s' % clase, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delclase':
            try:
                clase = CapClase.objects.get(pk=int(request.POST['id']))
                if clase.capcabeceraasistencia_set.values('id').filter(status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar, porque tiene asistencias registradas."})
                log(u'Elimino horario de Evento: %s' % clase, request, "del")
                clase.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        #ASISTENCIAS
        elif action == 'asistencia':
            try:
                asis = CapCabeceraAsistencia.objects.filter(fecha=datetime.now().date() if not 'fecha' in request.POST else datetime.strptime(request.POST["fecha"], '%d-%m-%Y'),clase_id=int(request.POST["idc"]), status=True)
                if not CapClase.objects.get(pk=int(request.POST['idc'])).capeventoperiodo.exiten_inscritos():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede continuar, porque no existe inscrito."})
                if 'fecha' in request.POST:
                    fecha=datetime.strptime(request.POST["fecha"], '%d-%m-%Y')
                    if asis.values('id').exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe asistencia en esa fecha y clase."})
                    if not CapClase.objects.values('id').filter(Q(pk=int(request.POST['idc'])),(Q(fechainicio__lte=fecha) & Q(fechafin__gte=fecha)), status=True,dia=fecha.weekday() + 1).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"No esta en rango de fecha o en dia."})
                if not asis.values('id').exists():
                    clase=CapClase.objects.get(pk=int(request.POST['idc']))
                    asistencia=CapCabeceraAsistencia(clase_id=int(request.POST['idc']),
                                                     fecha= fecha.date() if 'fecha' in request.POST else datetime.now().date(),
                                                     horaentrada=clase.turno.horainicio,
                                                     horasalida=clase.turno.horafin,
                                                     contenido="SIN CONTENIDO",
                                                     observaciones="SIN OBSERVACIONES")
                    asistencia.save(request)
                    log(u'Agrego Asistencia: %s [%s]' % (asistencia,asistencia.id), request, "add")
                    for integrante in clase.capeventoperiodo.inscritos_aprobado():
                        resultadovalores = CapDetalleAsistencia(cabecerasolicitud=integrante,cabeceraasistencia=asistencia, asistio=False)
                        resultadovalores.save(request)
                else:
                    asistencia=asis[0]
                return JsonResponse({"result": "ok",'id':asistencia.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addasistenciagrupal':
            try:
                cadenaselect = request.POST['cadenaselect']
                cadenanoselect = request.POST['cadenanoselect']
                cadenadatos = cadenaselect.split(',')
                cadenanodatos = cadenanoselect.split(',')
                asistencia=CapCabeceraAsistencia.objects.get(pk=int(request.POST["id"]))
                for cadena in cadenadatos:
                    if cadena:
                        if asistencia.capdetalleasistencia_set.values('id').filter(cabecerasolicitud_id=cadena,status=True).exists():
                            resultadovalores =asistencia.capdetalleasistencia_set.get(cabecerasolicitud_id=cadena,status=True)
                            resultadovalores.asistio = True
                            resultadovalores.save(request)
                        else:
                            resultadovalores = CapDetalleAsistencia(cabecerasolicitud_id=cadena,cabeceraasistencia=asistencia,asistio=True)
                            resultadovalores.save(request)
                for cadenano in cadenanodatos:
                    if cadenano:
                        if asistencia.capdetalleasistencia_set.values('id').filter(cabecerasolicitud_id=cadenano,status=True).exists():
                            resultadovalores =asistencia.capdetalleasistencia_set.get(cabecerasolicitud_id=cadenano,status=True)
                            resultadovalores.asistio = False
                            resultadovalores.save(request)
                        else:
                            resultadovalores = CapDetalleAsistencia(cabecerasolicitud_id=cadenano,cabeceraasistencia=asistencia,asistio=False)
                            resultadovalores.save(request)
                log(u'Edito Asistencia: %s [%s]' % (asistencia,asistencia.id), request, "edit")
                data = {"result": "ok", "results": [{"id": x.cabecerasolicitud.id, "porcientoasist": x.cabecerasolicitud.porciento_asistencia(),"porcientorequerido":x.cabecerasolicitud.porciento_requerido_asistencia()} for x in asistencia.capdetalleasistencia_set.filter(status=True)]}
                return JsonResponse(data)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addasistenciaindividual':
            try:
                asistencia=CapCabeceraAsistencia.objects.get(pk=int(request.POST["id"]))
                if asistencia.capdetalleasistencia_set.values('id').filter(cabecerasolicitud_id=int(request.POST['idi']),status=True).exists():
                    resultadovalores =asistencia.capdetalleasistencia_set.get(cabecerasolicitud_id=int(request.POST['idi']),status=True)
                    resultadovalores.asistio = True if request.POST['valor']=="y" else False
                    resultadovalores.save(request)
                else:
                    resultadovalores = CapDetalleAsistencia(cabecerasolicitud_id=int(request.POST['idi']),cabeceraasistencia=asistencia,asistio=True if request.POST['valor']=="y" else False)
                    resultadovalores.save(request)
                datos={}
                datos['id'] = resultadovalores.cabecerasolicitud.id
                datos['porcientoasist'] = resultadovalores.cabecerasolicitud.porciento_asistencia()
                datos['porcientorequerido'] = resultadovalores.cabecerasolicitud.porciento_requerido_asistencia()
                datos['result']='ok'
                log(u'Edito Asistencia de Evento: %s [%s]' % (asistencia,asistencia.id), request, "edit")
                return JsonResponse(datos)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addasistenciacontenido':
            try:
                asistencia=CapCabeceraAsistencia.objects.get(pk=int(request.POST["id"]))
                asistencia.contenido=request.POST["valor"]
                asistencia.save(request)
                log(u'Edito Contenido de Asistencia de Evento: %s [%s]' % (asistencia,asistencia.id), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addasistenciaobservacion':
            try:
                asistencia=CapCabeceraAsistencia.objects.get(pk=int(request.POST["id"]))
                asistencia.observaciones=request.POST["valor"]
                asistencia.save(request)
                log(u'Edito Observacion de Asistencia de Evento: %s [%s]' % (asistencia,asistencia.id), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delasistencia':
            try:
                asistencia = CapCabeceraAsistencia.objects.get(pk=int(request.POST["id"]))
                asistencia.delete()
                log(u'Elimino asistencia: %s [%s]' % (asistencia,asistencia.id), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'adicionarpersonafirma':
            try:
                form = CapEventoPeriodoFirmasForm(request.POST)
                if form.is_valid():
                    # if CapEventoPeriodoFirmas.objects.filter(capeventoperiodo=form.cleaned_data['id'], firmapersona_id=form.cleaned_data['personafirma'], tipofirmaevento=form.cleaned_data['tipofirmaevento']):
                    #     firma = CapEventoPeriodoFirmas.objects.get(capeventoperiodo=form.cleaned_data['id'], firmapersona_id=form.cleaned_data['personafirma'], tipofirmaevento=form.cleaned_data['tipofirmaevento'])
                    #     firma
                    evento = CapEventoPeriodoFirmas(capeventoperiodo_id=int(request.POST['id']),
                                                    firmapersona_id=form.cleaned_data['personafirma'],
                                                    tipofirmaevento=form.cleaned_data['tipofirmaevento'],
                                                    cargo=form.cleaned_data['cargo'])
                    evento.save(request)
                    log(u'Adiciono firma evento periodo: %s [%s]' % (evento, evento.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletefirma':
            try:
                itemfirma = CapEventoPeriodoFirmas.objects.get(pk=int(request.POST['id']))
                itemfirma.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar la firma."})

        return HttpResponseRedirect(request.path)

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            #PERIODO
            if action == 'addperiodo':
                try:
                    data['title'] = u'Adicionar Período de Evento'
                    data['form'] = CapPeriodoForm()
                    return render(request, "adm_capacitacioneventoperiodo/addperiodo.html", data)
                except Exception as ex:
                    pass

            elif action == 'delperiodo':
                try:
                    data['title'] = u'Eliminar Período de Evento'
                    data['periodo'] = CapPeriodo.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitacioneventoperiodo/delperiodo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editperiodo':
                try:
                    data['title'] = u'Editar Período de Evento'
                    data['periodo'] = periodo=CapPeriodo.objects.get(pk=int(request.GET['id']))
                    form = CapPeriodoForm(initial={'nombre':periodo.nombre,'descripcion':periodo.descripcion,'abreviatura':periodo.abreviatura,'fechainicio':periodo.fechainicio,'fechafin':periodo.fechafin})
                    if periodo.esta_cap_evento_periodo_activo():
                        form.editar_grupo()
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodo/editperiodo.html", data)
                except Exception as ex:
                    pass

            #EVENTO
            elif action == 'addevento':
                try:
                    data['title'] = u'Adicionar Evento'
                    data['form'] = CapEventoForm()
                    return render(request, "adm_capacitacioneventoperiodo/addevento.html", data)
                except Exception as ex:
                    pass

            elif action == 'delevento':
                try:
                    data['title'] = u'Eliminar Evento'
                    data['evento'] = CapEvento.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitacioneventoperiodo/delevento.html", data)
                except Exception as ex:
                    pass

            elif action == 'editevento':
                try:
                    data['title'] = u'Editar Evento'
                    data['evento'] = evento = CapEvento.objects.get(pk=int(request.GET['id']))
                    form = CapEventoForm(initial={'nombre': evento.nombre,
                                                  'tipocurso': evento.tipocurso})
                    if evento.esta_cap_evento_activo():
                        form.editar_grupo()
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodo/editevento.html", data)
                except Exception as ex:
                    pass

            elif action == 'eventos':
                try:
                    data['title'] = u'Evento'
                    search = None
                    ids = None
                    evento = None
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        evento = CapEvento.objects.filter(pk=ids, status=True)
                    elif 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            evento = CapEvento.objects.filter(pk=search, status=True)
                        else:
                            if search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    evento = CapEvento.objects.filter(Q(nombre__icontains=s[0]),Q(status=True))
                                elif len(s) == 2:
                                    evento = CapEvento.objects.filter(Q(nombre__icontains=s[0]),Q(nombre__icontains=s[1]),Q(status=True))
                                elif len(s) == 3:
                                    evento = CapEvento.objects.filter(Q(nombre__icontains=s[0]),Q(nombre__icontains=s[1]), Q(nombre__icontains=s[2]),Q(status=True))
                                elif len(s) == 4:
                                    evento = CapEvento.objects.filter(Q(nombre__icontains=s[0]),Q(nombre__icontains=s[1]), Q(nombre__icontains=s[2]), Q(nombre__icontains=s[3]),Q(status=True))
                            else:
                                evento = CapEvento.objects.filter(status=True)
                    else:
                        evento = CapEvento.objects.filter(status=True)
                    paging = MiPaginador(evento, 25)
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
                    data['evento'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_capacitacioneventoperiodo/viewevento.html", data)
                except Exception as ex:
                    pass

            #ENFOQUE
            elif action == 'addenfoque':
                try:
                    data['title'] = u'Adicionar Capacitación Enfoque'
                    data['form'] = CapEnfocadaForm()
                    return render(request, "adm_capacitacioneventoperiodo/addenfoque.html", data)
                except Exception as ex:
                    pass

            elif action == 'delenfoque':
                try:
                    data['title'] = u'Eliminar Capacitación Enfoque'
                    data['enfocada'] = CapEnfocada.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitacioneventoperiodo/delenfoque.html", data)
                except Exception as ex:
                    pass

            elif action == 'editenfoque':
                try:
                    data['title'] = u'Editar Capacitación Enfoque'
                    data['enfocada'] = enfo=CapEnfocada.objects.get(pk=int(request.GET['id']))
                    form = CapEnfocadaForm(initial={'nombre':enfo.nombre})
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodo/editenfoque.html", data)
                except Exception as ex:
                    pass

            elif action == 'enfoques':
                try:
                    data['title'] = u'Capacitación Enfoque'
                    data['enfocada'] = CapEnfocada.objects.filter(status=True)
                    return render(request, "adm_capacitacioneventoperiodo/viewenfoque.html", data)
                except Exception as ex:
                    pass

            #TURNO
            elif action == 'addturno':
                try:
                    data['title'] = u'Adicionar Turno'
                    form= CapTurnoForm(initial={'turno':int((CapTurno.objects.filter(status=True).aggregate(Max('turno'))['turno__max'])+1) if CapTurno.objects.values('id').filter(status=True).exists() else 1})
                    form.editar_grupo()
                    data['form'] =form
                    return render(request, "adm_capacitacioneventoperiodo/addturno.html", data)
                except Exception as ex:
                    pass

            elif action == 'delturno':
                try:
                    data['title'] = u'Eliminar Turno'
                    data['turno'] = CapTurno.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitacioneventoperiodo/delturno.html", data)
                except Exception as ex:
                    pass

            elif action == 'editturno':
                try:
                    data['title'] = u'Editar Turno'
                    data['turno'] = turno=CapTurno.objects.get(pk=int(request.GET['id']))
                    form = CapTurnoForm(initial={'turno': turno.turno,
                                                 'horainicio': str(turno.horainicio),
                                                 'horafin': str(turno.horafin),
                                                 'horas': str(turno.horas)})
                    form.editar_grupo()
                    form.editar_turno()
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodo/editturno.html", data)
                except Exception as ex:
                    pass

            elif action == 'turnos':
                try:
                    data['title'] = u'Turnos'
                    data['turno'] = CapTurno.objects.filter(status=True)
                    return render(request, "adm_capacitacioneventoperiodo/viewturno.html", data)
                except Exception as ex:
                    pass

            #CONFIGURACION
            elif action == 'configuracion':
                try:
                    data['title'] = u'Configuración'
                    configuracion = CapConfiguracion.objects.filter()
                    if configuracion.values('id').exists():
                        try:
                            revisado = DistributivoPersona.objects.filter(persona=configuracion[0].revisado,denominacionpuesto=configuracion[0].denominacionrevisado)
                            aprobado1 = DistributivoPersona.objects.filter(persona=configuracion[0].aprobado1,denominacionpuesto=configuracion[0].denominacionaprobado1)
                            aprobado2 = DistributivoPersona.objects.filter(persona=configuracion[0].aprobado2,denominacionpuesto=configuracion[0].denominacionaprobado2)
                            aprobado3 = DistributivoPersona.objects.filter(persona=configuracion[0].aprobado3,denominacionpuesto=configuracion[0].denominacionaprobado3)
                            form = CapConfiguracionForm(initial={'minasistencia': configuracion[0].minasistencia,
                                                                 'minnota': configuracion[0].minnota,
                                                                 'abreviaturadepartamento': configuracion[0].abreviaturadepartamento,
                                                                 'revisado': revisado[0].id if revisado.values('id').exists() else 0,
                                                                 'aprobado1': aprobado1[0].id if aprobado1.values('id').exists() else 0,
                                                                 'aprobado2': aprobado2[0].id if aprobado2.values('id').exists() else 0,
                                                                 'aprobado3': aprobado3[0].id if aprobado3.values('id').exists() else 0 })
                            form.editar(revisado,aprobado1,aprobado2,aprobado3)
                        except Exception as ex:
                            form = CapConfiguracionForm(initial={'minasistencia': configuracion[0].minasistencia,
                                                                 'minnota': configuracion[0].minnota})
                    else:
                        form = CapConfiguracionForm()
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodo/configuracion.html", data)
                except Exception as ex:
                    pass

            elif action == 'busquedaconcargo':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__()==2:
                        distributivo = DistributivoPersona.objects.filter(Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1]),estadopuesto__id=PUESTO_ACTIVO_ID, status=True).distinct()[:20]
                    else:
                        distributivo = DistributivoPersona.objects.filter(Q(persona__nombres__contains=q) | Q(persona__apellido1__contains=q) | Q(persona__apellido2__contains=q) | Q(persona__cedula__contains=q)).filter(estadopuesto__id=PUESTO_ACTIVO_ID, status=True)[:20]
                    data = {"result": "ok", "results": [{"id": x.id, "name": (u'%s - %s - %s'%(x.persona.cedula , x.persona.nombre_completo_inverso(),x.denominacionpuesto)) } for x in distributivo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            #EVENTO PERIODO
            elif action == 'addperiodoevento':
                try:
                    data['title'] = u'Adicionar Evento'
                    periodo=CapPeriodo.objects.get(pk=int(request.GET['id']))
                    data['periodo'] = periodo.id
                    pais=Pais.objects.get(pk=1)
                    provincia = Provincia.objects.get(pk=10)
                    canton=Canton.objects.get(pk=2)
                    parroquia = Parroquia.objects.get(pk=4)
                    configuracion=CapConfiguracion.objects.all()
                    form=CapEventoPeriodoForm(initial={'periodo':periodo,
                                                       'pais': pais,
                                                       'provincia': provincia,
                                                       'canton': canton,
                                                       'parroquia': parroquia,
                                                       'minasistencia': configuracion[0].minasistencia if configuracion.values('id').exists() else 0,
                                                       'minnota': configuracion[0].minnota if configuracion.values('id').exists() else 0,
                                                       'revisado': configuracion[0].revisado_f() if configuracion.values('id').exists() else '',
                                                       'aprobado1':(u'%s - %s - %s'%(configuracion[0].aprobado1.cedula,configuracion[0].aprobado1.nombre_completo_inverso(),configuracion[0].denominacionaprobado1)) if configuracion.values('id').exists() else '',
                                                       'aprobado2':(u'%s - %s - %s'%(configuracion[0].aprobado2.cedula,configuracion[0].aprobado2.nombre_completo_inverso(),configuracion[0].denominacionaprobado2)) if configuracion.values('id').exists() else '',
                                                       'aprobado3': (u'%s - %s - %s' % (configuracion[0].aprobado3.cedula,configuracion[0].aprobado3.nombre_completo_inverso(),configuracion[0].denominacionaprobado3)) if configuracion.values('id').exists() else '',
                                                       'abreviaturadepartamento': (u'%s' % configuracion[0].abreviaturadepartamento if configuracion.values('id').exists() else ''),
                                                       'codigo':int((CapEventoPeriodo.objects.filter(status=True,periodo=periodo).aggregate(Max('codigo'))['codigo__max'])+1 if CapEventoPeriodo.objects.values('id').filter(status=True,periodo=periodo).exists() else 1)
                                                       })
                    form.editar_grupo()
                    form.adicionar(pais,provincia,canton)
                    data['form'] =form
                    return render(request, "adm_capacitacioneventoperiodo/addperiodoevento.html", data)
                except Exception as ex:
                    pass

            elif action == 'delperiodoevento':
                try:
                    data['title'] = u'Eliminar Evento'
                    data['evento'] = CapEventoPeriodo.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitacioneventoperiodo/delperiodoevento.html", data)
                except Exception as ex:
                    pass

            elif action == 'editperiodoevento':
                try:
                    data['title'] = u'Editar Evento'
                    data['evento'] = evento=CapEventoPeriodo.objects.get(pk=int(request.GET['id']))
                    responsable= Administrativo.objects.get(persona=evento.responsable)
                    form = CapEventoPeriodoForm(initial={'periodo':evento.periodo,
                                                         'capevento':evento.capevento,
                                                         'horas': evento.horas,
                                                         'departamento': evento.departamento,
                                                         'horaspropedeutica': evento.horaspropedeutica,
                                                         'horasautonoma': evento.horasautonoma,
                                                         'horastotal': evento.horasautonoma+ evento.horas+evento.horaspropedeutica,
                                                         'folder': evento.folder,
                                                         'objetivo': evento.objetivo,
                                                         'observacion': evento.observacion,
                                                         'minasistencia': evento.minasistencia,
                                                         'minnota': evento.minnota,
                                                         'fechainicio': evento.fechainicio,
                                                         'fechafin': evento.fechafin,
                                                         'regimenlaboral': evento.regimenlaboral,
                                                         'tipoparticipacion': evento.tipoparticipacion,
                                                         'contextocapacitacion': evento.contextocapacitacion,
                                                         'modalidad' : evento.modalidad,
                                                         'tipocertificacion': evento.tipocertificacion,
                                                         'tipocapacitacion': evento.tipocapacitacion,
                                                         'pais':  evento.pais,
                                                         'provincia': evento.provincia,
                                                         'canton': evento.canton,
                                                         'parroquia': evento.parroquia,
                                                         'visualizar': evento.visualizar,
                                                         'enfoque': evento.enfoque,
                                                         'contenido': evento.contenido,
                                                         'cupo': evento.cupo,
                                                         'responsable': responsable.id,
                                                         'areaconocimiento': evento.areaconocimiento,
                                                         'subareaconocimiento': evento.subareaconocimiento,
                                                         'subareaespecificaconocimiento': evento.subareaespecificaconocimiento,
                                                         'revisado':(u'%s - %s - %s'%(evento.revisado.cedula,evento.revisado.nombre_completo_inverso(),evento.denominacionrevisado)) if evento.revisado else '',
                                                         'aprobado1':(u'%s - %s - %s'%(evento.aprobado1.cedula,evento.aprobado1.nombre_completo_inverso(),evento.denominacionaprobado1)) if evento.aprobado1 else '',
                                                         'aprobado2':(u'%s - %s - %s'%(evento.aprobado2.cedula,evento.aprobado2.nombre_completo_inverso(),evento.denominacionaprobado2)) if evento.aprobado2 else '',
                                                         'aprobado3': (u'%s - %s - %s' % (evento.aprobado3.cedula,evento.aprobado3.nombre_completo_inverso(),evento.denominacionaprobado3)) if evento.aprobado3 else '',
                                                         'abreviaturadepartamento': (u'%s' % evento.abreviaturadepartamento if evento.abreviaturadepartamento else ''),
                                                         'codigo':evento.codigo,
                                                         'observacionreporte': evento.observacionreporte,
                                                         'aula': evento.aula })
                    form.editar_grupo()
                    if evento.exiten_inscritos():
                        form.editar_regimenlaboral()
                    form.editar_responsable(responsable)
                    if not evento.periodo.esta_activo_periodo:
                        data['permite_modificar'] = False
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodo/editperiodoevento.html", data)
                except Exception as ex:
                    pass

            elif action == 'busqueda':
                try:
                    q = request.GET['q'].upper().strip()
                    if ' ' in q:
                        s = q.split(" ")
                        distributivo=DistributivoPersona.objects.filter(Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1]),estadopuesto__id=PUESTO_ACTIVO_ID,status=True).distinct()[:20]
                    distributivo=DistributivoPersona.objects.filter(Q(persona__nombres__contains=q) | Q(persona__apellido1__contains=q) | Q(persona__apellido2__contains=q) | Q(persona__cedula__contains=q)).filter(estadopuesto__id=PUESTO_ACTIVO_ID,status=True)[:20]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr()}for x in distributivo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'busquedaregistro':
                try:
                    eventoperiodo= CapEventoPeriodo.objects.get(pk=int(request.GET['id']))
                    data = {"result": "ok", "results": [{"id": eventoperiodo.id,"horas":str(eventoperiodo.horas),"evento":str(eventoperiodo.capevento), "inicio":str(eventoperiodo.fechainicio.strftime('%d-%m-%Y')),"fin":str(eventoperiodo.fechafin.strftime('%d-%m-%Y')),"enfoque":str(eventoperiodo.enfoque)}if eventoperiodo else ""]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'listadoinscripcion':
                try:
                    participante= DistributivoPersona.objects.get(pk=int(request.GET['idp']))
                    tieneeventos = CapCabeceraSolicitud.objects.values_list("capeventoperiodo_id").filter(participante=participante.persona)
                    excluir = CapEventoPeriodo.objects.values_list("id").filter(capevento__nombre__in=[datos['evento'] for datos in json.loads(request.GET['listado'])]) if request.GET['listado'] else []
                    eventoperiodolista =CapEventoPeriodo.objects.filter(Q(status=True)&Q(visualizar=True)&Q(regimenlaboral=participante.regimenlaboral)).exclude(Q(pk__in=excluir)|Q(pk__in=tieneeventos))
                    if eventoperiodolista:
                        data = {"result": "ok", "results": [{"id": str(eventoperiodo.id),"horas":str(eventoperiodo.horas),"evento":str(eventoperiodo.capevento),"inicio":str(eventoperiodo.fechainicio.strftime('%d-%m-%Y')),"fin":str(eventoperiodo.fechafin.strftime('%d-%m-%Y')),"enfoque":str(eventoperiodo.enfoque),"inscrito":str(eventoperiodo.contar_inscripcion_evento_periodo()),"modalidad":str(eventoperiodo.get_modalidad_display())}for eventoperiodo in eventoperiodolista]}
                    else:
                        data = {"result": "no"}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'addinscribir':
                try:
                    data['title'] = u'Inscribir'
                    data['form'] = CapInscribirForm()
                    data['eventoperiodo'] = int(request.GET['id'])
                    return render(request, "adm_capacitacioneventoperiodo/addinscribir.html", data)
                except Exception as ex:
                    pass

            elif action == 'inscritos':
                try:
                    data['title'] = u'Inscritos'
                    search = None
                    ids = None
                    eventoperiodo=CapEventoPeriodo.objects.get(pk=int(request.GET['id']))
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            cabecera = CapCabeceraSolicitud.objects.filter((Q(participante__nombres__icontains=search) |
                                                                            Q(participante__apellido1__icontains=search) |
                                                                            Q(participante__apellido2__icontains=search) |
                                                                            Q(participante__cedula__icontains=search) |
                                                                            Q(participante__pasaporte__icontains=search)) &
                                                                           Q(capeventoperiodo=eventoperiodo)&
                                                                           Q(estadosolicitud=variable_valor('APROBADO_CAPACITACION'))&Q(status=True)). \
                                distinct()
                        else:
                            cabecera = CapCabeceraSolicitud.objects.filter(Q(participante__apellido1__icontains=ss[0]) & Q(solicita__apellido2__icontains=ss[1]) &
                                                                           Q(capeventoperiodo=eventoperiodo)&Q(estadosolicitud=variable_valor('APROBADO_CAPACITACION'))&Q(status=True)).distinct()
                    else:
                        cabecera = CapCabeceraSolicitud.objects.filter(capeventoperiodo=eventoperiodo, status=True, estadosolicitud=variable_valor('APROBADO_CAPACITACION'))
                    paging = MiPaginador(cabecera, 20)
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
                    data['cabecera'] = page.object_list
                    data['eventoperiodo'] = eventoperiodo
                    return render(request, "adm_capacitacioneventoperiodo/inscritos.html", data)
                except Exception as ex:
                    pass

            elif action == 'listafirmas':
                try:
                    data['title'] = u'Listado de firmas'
                    eventoperiodo = CapEventoPeriodo.objects.get(pk=int(request.GET['id']))
                    data['listadofirmas'] = listadofirmas = eventoperiodo.capeventoperiodofirmas_set.filter(status=True)
                    firma1 = None
                    firma2 = None
                    firma3 = None
                    if listadofirmas.filter(tipofirmaevento=1):
                        firma1 = listadofirmas.filter(tipofirmaevento=1)[0]
                    if listadofirmas.filter(tipofirmaevento=2):
                        firma2 = listadofirmas.filter(tipofirmaevento=2)[0]
                    if listadofirmas.filter(tipofirmaevento=3):
                        firma3 = listadofirmas.filter(tipofirmaevento=3)[0]
                    data['firma1'] = firma1
                    data['firma2'] = firma2
                    data['firma3'] = firma3
                    data['eventoperiodo'] = eventoperiodo
                    return render(request, "adm_capacitacioneventoperiodo/listafirmas.html", data)
                except Exception as ex:
                    pass

            elif action == 'adicionarpersonafirma':
                try:
                    data['title'] = u'Adicionar firma'
                    data['capeventoperiodo'] = capeventoperiodo = CapEventoPeriodo.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['listafirmas'] = listafirmas = capeventoperiodo.capeventoperiodofirmas_set.values_list('tipofirmaevento',flat=True).filter(status=True)
                    form = CapEventoPeriodoFirmasForm()
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodo/adicionarpersonafirma.html", data)
                except Exception as ex:
                    pass

            elif action == 'delinscrito':
                try:
                    data['title'] = u'Eliminar Inscrito'
                    data['cabecera'] = CapCabeceraSolicitud.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitacioneventoperiodo/delinscrito.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadodistributivo':
                try:
                    id = int (request.GET['id'])
                    listado_participante=CapCabeceraSolicitud.objects.values_list("participante_id").filter(capeventoperiodo_id=int(request.GET['ide']), estadosolicitud=variable_valor('APROBADO_CAPACITACION'))
                    distributivo=DistributivoPersona.objects.filter(unidadorganica_id=id,estadopuesto__id=PUESTO_ACTIVO_ID,status=True).exclude(persona_id__in=listado_participante).distinct()[:20]
                    if distributivo:
                        data = {"result": "ok", "results": [{"id": str(x.id),"cedula":str(x.persona.cedula), "apellidos": x.persona.nombre_completo_inverso(), "cargo": str(x.denominacionpuesto)}for x in distributivo]}
                    else:
                        data = {"result": "no"}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'verdetalle':
                try:
                    data = {}
                    cabecera = CapCabeceraSolicitud.objects.get(pk=int(request.GET['id']))
                    data['cabecerasolicitud'] = cabecera
                    data['detallesolicitud'] = cabecera.capdetallesolicitud_set.all()
                    data['solicitud_capacitacion'] = variable_valor('SOLICITUD_CAPACITACION')
                    data['pendiente_capacitacion'] = variable_valor('PENDIENTE_CAPACITACION')
                    data['aprobado_capacitacion'] = variable_valor('APROBADO_CAPACITACION')
                    template = get_template("adm_capacitacioneventoperiodo/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'verdetalleevento':
                try:
                    data = {}
                    data['evento'] =CapEventoPeriodo.objects.get(pk=int(request.GET['id']))
                    template = get_template("adm_capacitacioneventoperiodo/detalleevento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'planificacion':
                try:
                    data['title'] = u'Planificación de Eventos'
                    search = None
                    ids = None
                    data['periodo'] = periodo = CapPeriodo.objects.get(pk=int(request.GET['id']))
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            evento = CapEventoPeriodo.objects.filter((Q(capevento__nombre__icontains=search)|
                                                                      Q(enfoque__nombre__icontains=search)) &
                                                                     Q(periodo=periodo) &
                                                                     Q(status=True)).distinct().order_by('capevento','enfoque', 'fechainicio')
                        else:
                            evento = CapEventoPeriodo.objects.filter(Q(capevento__nombre__icontains=ss[0]) & Q(enfoque__nombre__icontains=ss[1]) &
                                                                     Q(periodo=periodo) &
                                                                     Q(status=True)).distinct().order_by('capevento','enfoque','fechainicio')
                    else:
                        evento = CapEventoPeriodo.objects.filter(periodo=periodo, status=True).order_by('fechainicio')
                    paging = MiPaginador(evento, 20)
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
                    data['evento'] = page.object_list
                    data['reporte_0'] = obtener_reporte('inscritos_capacitacion_auth')
                    data['aprobado_capacitacion'] = variable_valor('APROBADO_CAPACITACION')
                    return render(request, "adm_capacitacioneventoperiodo/viewperiodoevento.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'excelasistencia':
                try:
                    # bordes
                    borders = Borders()
                    borders.left = 1
                    borders.right = 1
                    borders.top = 1
                    borders.bottom = 1
                    # estilos para los reportes
                    title = easyxf('font: name Arial, bold on , height 235; alignment: horiz centre')
                    subtitle1 = easyxf('font: name Arial, height 200; alignment: horiz centre')
                    subtitle2 = easyxf('font: name Arial, height 180; alignment: horiz centre')
                    nnormal = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
                    nnormal1 = easyxf('font: name Arial, bold on , height 150; alignment: horiz left')
                    nnormal2 = easyxf('font: name Arial, bold on , height 150; alignment: horiz right')
                    normal = easyxf('font: name Arial , height 150; alignment: horiz left')
                    normal2 = easyxf('font: name Arial, bold on , height 170; alignment: horiz left')
                    normal3 = easyxf('font: name Arial, bold on , height 150; alignment: horiz left')
                    stylenotas = easyxf('font: name Arial , height 150; alignment: horiz centre')
                    stylebnotas = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
                    stylebnotas1 = easyxf('font: name Arial, bold on , height 140; align:wrap on, horiz centre')
                    stylebfirmas = easyxf('font: name Arial, bold on , height 120; align:wrap on, horiz left,vert top')
                    stylebnombre = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
                    stylevacio = easyxf('font: name Arial , height 600; alignment: horiz centre')
                    normal.borders = borders
                    stylebnotas.borders = borders
                    stylebnotas1.borders = borders
                    stylenotas.borders = borders
                    stylebnombre.borders = borders
                    stylevacio.borders = borders
                    #consulta
                    evento = CapEventoPeriodo.objects.get(status=True, id=int(request.GET['id']))

                    __author__ = 'Unemi'
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('reporte1')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename =CONTROL DE ASISTENCIA ' + '.xls'

                    ws.col(0).width = 1000
                    ws.col(1).width = 5000
                    ws.col(2).width = 4000
                    encabezado = 13

                    ws.write_merge(encabezado,encabezado+1, 0,0, 'Nº', stylebnotas)
                    ws.write_merge(encabezado, encabezado+1, 1, 2, 'APELLIDOS Y NOMBRES', stylebnombre)
                    fechas=CapCabeceraAsistencia.objects.filter(clase__capeventoperiodo=evento).distinct('fecha').order_by('fecha')
                    meses = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP","OCT", "NOV", "DIC"]
                    fila=3
                    for fecha in fechas:
                        turno_fecha=CapCabeceraAsistencia.objects.filter(clase__capeventoperiodo=evento,fecha=fecha.fecha).order_by('clase__turno')
                        contar_turnos=turno_fecha.count()
                        nombre_concatenado=""
                        nombre_concatenado=str(fecha.fecha.day)+" "+meses[fecha.fecha.month-1]
                        if contar_turnos>1:
                            ws.write_merge(encabezado, encabezado, fila , fila+contar_turnos-1, nombre_concatenado , stylebnotas)
                            cada_uno=fila
                            for turno in turno_fecha:
                                ws.write(encabezado+1, cada_uno, str(turno.clase.turno.horainicio.strftime("%H:%M")), stylenotas)
                                cada_uno+=1
                            fila += contar_turnos
                        else:
                            ws.write(encabezado, fila, nombre_concatenado,stylebnotas)
                            ws.write(encabezado+1, fila, str(turno_fecha[0].clase.turno.horainicio.strftime("%H:%M")), stylenotas)
                            fila += 1
                    ws.col(fila).width = 2000
                    ws.col(fila+1).width = 2000
                    ws.col(fila + 2).width = 2550
                    ws.write_merge(encabezado, encabezado+1, fila,fila, '% HORAS ASISTIDA', stylebnotas1)
                    ws.write_merge(encabezado, encabezado+1, fila+1,fila+1, '% HORAS ASISTIDA', stylebnotas1)
                    ws.write_merge(encabezado, encabezado+1, fila+2, fila + 2, 'ESTADO', stylebnombre)
                    ws.write_merge(encabezado, encabezado+1, fila+3, fila + 3, 'OBSERVACIÓN', stylebnotas)

                    listainscritos = evento.inscritos_aprobado()
                    colum = 3
                    sumar_promedio_asistencia=0
                    contar_promedio_asistencia = 0
                    ultima_fecha = 0
                    if listainscritos.exists():
                        i = 0
                        for inscrito in listainscritos:
                            fil = i + 15
                            ws.write(fil, 0, str(i + 1), stylenotas)
                            ws.write(fil, 1, (u'%s'%inscrito.participante), normal)
                            ws.merge(fil, fil, 1, 2, normal)
                            colum=3
                            asistencia_asistida=0
                            for fecha in fechas:
                                turno_fecha = CapCabeceraAsistencia.objects.filter(clase__capeventoperiodo=evento,fecha=fecha.fecha).order_by('clase__turno')
                                for turno in turno_fecha:
                                    ws.col(colum).width = 1425
                                    asistio=CapDetalleAsistencia.objects.filter(cabeceraasistencia=turno,cabecerasolicitud=inscrito)
                                    if asistio.exists():
                                        ws.write(fil, colum, str('A'if asistio[0].asistio else 'F'), stylenotas)
                                        if asistio[0].asistio:
                                            asistencia_asistida+=1
                                    else:
                                        ws.write(fil, colum, str('N'), stylenotas)
                                    colum+=1
                                ultima_fecha = fecha.fecha
                            ws.write(fil, colum, str(asistencia_asistida), stylenotas)
                            promedio=inscrito.porciento_asistencia()
                            sumar_promedio_asistencia+=promedio
                            contar_promedio_asistencia+=1
                            ws.write(fil, colum+1, str(promedio)+'%', stylenotas)
                            if inscrito.porciento_requerido_asistencia():
                                ws.write(fil, colum + 2, str('APROBADO'), normal)
                            else:
                                ws.write(fil, colum + 2, str('REPROBADO'), normal)
                            ws.write(fil, colum + 3, str(''), stylenotas)
                            i = i + 1
                    ws.write_merge(fil + 1,fil + 1,colum-1, colum, 'PROMEDIO:', nnormal2)
                    ws.write(fil + 1,colum+1, str(round((sumar_promedio_asistencia/contar_promedio_asistencia),2) if contar_promedio_asistencia>0 else 0)+'%', stylenotas)
                    # hoja
                    ws.write_merge(1, 1, 0, colum+3, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(2, 2, 0, colum+3, 'INSTITUTO DE POSTGRADO Y EDUCACIÓN CONTINUA', subtitle1)
                    ws.write_merge(3, 3, 0, colum+3, 'UNIDAD DE TALENTO HUMANO', subtitle2)
                    ws.write_merge(4, 4, 0, colum+3, 'ÁREA DE FORMACIÓN Y DESARROLLO DE TALENTO HUMANO', subtitle2)
                    ws.write_merge(5, 5, 0, colum+3, 'RESUMEN CONTROL DE ASISTENCIA', title)
                    ws.write(7, 1, 'CÓDIGO: ', normal3)
                    ws.write(7, 2, evento.concatenar_codigo(), normal2)
                    ws.merge(7, 7, 2, colum)
                    ws.write(8, 1, 'CURSO: ', normal3)
                    ws.merge(8, 8, 1, 1)
                    ws.write(8, 2, (u'%s'% evento.capevento.nombre), normal2)
                    ws.merge(8, 8, 2, colum+3)
                    ws.write(9, 1, 'FACILITADORES:', normal3)
                    ws.merge(9, 9, 1, 1)
                    ws.write(9, 2, evento.concatenar_facilitadores(), normal3)
                    ws.merge(9, 9, 2, colum+3)
                    ws.write(10, 4, 'LUGAR:', normal3)
                    ws.merge(10, 10, 4, 5)
                    ws.write(10, 6, (u'%s'%evento.aula.nombre) + ' - ' + str(evento.aula.sede), normal3)
                    ws.merge(10, 10, 6, colum+3)
                    ws.write(10, 1, 'FECHA INICIO: ', normal3)
                    ws.merge(10, 10, 1, 1)
                    ws.write(10, 2, str(evento.fechainicio.strftime('%d-%m-%Y')), normal3)
                    ws.merge(10, 10, 2, 2)
                    ws.write(11, 1, 'FECHA FIN: ', normal3)
                    ws.merge(11, 11, 1, 1)
                    ws.write(11, 2, str(evento.fechafin.strftime('%d-%m-%Y')), normal3)
                    ws.merge(11, 11, 2, 2)
                    ws.write(11, 4, 'HORAS:', normal3)
                    ws.merge(11, 11, 4, 5)
                    ws.write(11, 6, str(evento.horas), normal3)
                    ws.merge(11, 11, 6, 9)
                    fecha_corte=0
                    if ultima_fecha.weekday()>=0 and ultima_fecha.weekday()<=3 or ultima_fecha.weekday()==6 :
                        dias = timedelta(days=1)
                    else:
                        dias = timedelta(days=2)
                    fecha_corte = ultima_fecha + dias
                    ws.write_merge(fil + 3, fil + 3, colum-2, colum-1, 'FECHA CORTE:', nnormal)
                    ws.write_merge(fil + 3, fil + 3, colum,colum, 'DIA', stylebnotas)
                    ws.write_merge(fil + 3, fil + 3, colum+1, colum+1, 'MES', stylebnotas)
                    ws.write_merge(fil + 3, fil + 3, colum+2, colum+2, 'AÑO', stylebnotas)
                    ws.write_merge(fil + 3, fil + 3, colum+3, colum+3, 'HORA', stylebnotas)
                    ws.write_merge(fil + 4, fil + 4, colum, colum,str(fecha_corte.day), stylenotas)
                    ws.write_merge(fil + 4, fil + 4, colum+1, colum+1, str(fecha_corte.month), stylenotas)
                    ws.write_merge(fil + 4, fil + 4, colum+2, colum+2, str(fecha_corte.year), stylenotas)
                    ws.write_merge(fil + 4, fil + 4, colum + 3, colum + 3, str(''), stylenotas)
                    ws.write_merge(fil + 5, fil + 5, colum , colum + 3,evento.concatenar_codigo(), stylebnotas)

                    ws.write_merge(fil + 2, fil + 2, 1, 1, 'OBSERVACIÓN:', nnormal1)
                    ws.write_merge(fil + 3, fil + 4, 1, 2, (evento.observacionreporte if evento.observacionreporte else ""), stylebnotas1)

                    ws.write_merge(fil + 6, fil + 6, 1, 8, 'RESUMEN GENERAL DE ASISTENCIA', nnormal)
                    ws.write_merge(fil + 7, fil + 8, 1, 1, 'SESIÓN', stylebnotas)
                    ws.write_merge(fil + 7, fil + 8, 2, 2, 'FECHA EJECUCIÓN DEL EVENTO', stylebnotas1)
                    ws.write_merge(fil + 7, fil + 8, 3, 4, '% ASISTENCIA', stylebnotas1)
                    fil=fil + 8
                    c = 0
                    suma_promedio=0
                    for fecha in fechas:
                        c += 1
                        fil += 1
                        fecha_asistencia = CapDetalleAsistencia.objects.filter(cabeceraasistencia__clase__capeventoperiodo=evento,cabeceraasistencia__fecha=fecha.fecha)
                        asistencia=fecha_asistencia.filter(asistio=True, status=True).count()
                        promedio=round((asistencia*100)/float(fecha_asistencia.count()),2)
                        suma_promedio+=promedio
                        ws.write_merge(fil, fil, 1, 1,str(c), stylebnotas)
                        ws.write_merge(fil, fil, 2, 2, str(fecha.fecha.strftime('%d-%m-%Y')), stylenotas)
                        ws.write_merge(fil, fil, 3, 4, str(promedio)+'%', stylenotas)

                    ws.write_merge(fil+1, fil+1, 1, 2, str('%PROMEDIO DE ASISTENCIA:'),nnormal2)
                    ws.write_merge(fil+1, fil+1, 3, 4,str(round((float(suma_promedio/c) if c>0 else 0),2)) + '%',stylenotas)
                    fil += 2
                    ws.write(fil + 1, 1, str('ELABORADO POR:'), nnormal1)
                    ws.write_merge(fil + 1, fil + 1, 3, 5, str('REVISADO POR:'), nnormal1)
                    ws.write_merge(fil + 1, fil + 1, 9, 10, str('APROBADO POR:'), nnormal1)
                    ws.write_merge(fil + 1, fil + 1, 13, 15, str('APROBADO POR:'), nnormal1)
                    fil += 3
                    cargo=DistributivoPersona.objects.filter(persona_id=persona,estadopuesto__id=PUESTO_ACTIVO_ID, status=True)
                    titulacion = persona.titulacion_principal_senescyt_registro()
                    ws.write_merge(fil, fil, 1, 2, '_________________________', nnormal1)
                    ws.write_merge(fil + 1,fil + 3, 1,2, (titulacion.titulo.abreviatura if not titulacion=='' else "")+""+str(persona)+ '\n' + str(cargo[0].denominacionpuesto if cargo.exists()else''), stylebfirmas)

                    ws.write_merge(fil, fil, 3, 7, '_________________________', nnormal1)
                    titulacionrevisado=evento.revisado.titulacion_principal_senescyt_registro()
                    ws.write_merge(fil + 1, fil + 3,3, 7, (titulacionrevisado.titulo.abreviatura if not titulacionrevisado=='' else "")+""+(evento.revisado.nombre_completo_inverso()if evento.revisado else '') + '\n' + str(evento.denominacionrevisado if evento.denominacionrevisado else ''),stylebfirmas)

                    ws.write_merge(fil, fil, 9, 11, '_________________________', nnormal1)
                    titulacionaprobado1 = evento.aprobado1.titulacion_principal_senescyt_registro()
                    ws.write_merge(fil + 1, fil + 3, 9, 11, (titulacionaprobado1.titulo.abreviatura if not titulacionaprobado1 == '' else "") + "" + (evento.aprobado1.nombre_completo_inverso() if evento.aprobado1 else '') + '\n' + str(evento.denominacionaprobado1 if evento.denominacionaprobado1 else ''), stylebfirmas)

                    ws.write_merge(fil, fil, 13, 16, '_________________________', nnormal1)
                    titulacionaprobado2 = evento.aprobado2.titulacion_principal_senescyt_registro()
                    ws.write_merge(fil + 1, fil + 3, 13, 15, (titulacionaprobado2.titulo.abreviatura if not titulacionaprobado2 == '' else "") + "" + (evento.aprobado2.nombre_completo_inverso() if evento.aprobado2 else '') + '\n' + str(evento.denominacionaprobado2 if evento.denominacionaprobado2 else ''), stylebfirmas)
                    wb.save(response)
                    return response
                except Exception as es:
                    pass

            #INSTRUCTOR
            if action == 'busquedainstructor':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 2:
                        persona = Persona.objects.filter(apellido1__icontains=s[0],apellido2__icontains=s[1],real=True).exclude(pk__in=lista).distinct()[:15]
                    else:
                        persona =Persona.objects.filter(Q(real=True) & (Q(nombres__contains=s[0]) | Q(apellido1__contains=s[0]) | Q(apellido2__contains=s[0]) | Q(cedula__contains=s[0]))).exclude(pk__in=lista).distinct()[:15]
                    data = {"result": True, "aData": [{"id": x.id, "name": x.flexbox_repr()}for x in persona]}
                    return JsonResponse(data)
                except Exception as ex:
                    data = {"result": False, "mensaje": f"{ex.__str__()}", "aData": []}
                    return JsonResponse(data)

            if action == 'addinstructor':
                try:
                    data['title'] = u'Adicionar Instructor'
                    data['form'] = CapInstructorForm()
                    lista = CapInstructor.objects.values_list('instructor_id').filter(capeventoperiodo_id=int(request.GET['id']), status=True)
                    data['eventoperiodo']=request.GET['id']
                    return render(request, "adm_capacitacioneventoperiodo/addinstructor.html", data)
                except Exception as ex:
                    pass

            if action == 'delinstructor':
                try:
                    data['title'] = u'Eliminar Instructor'
                    data['instructor'] = CapInstructor.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitacioneventoperiodo/delinstructor.html", data)
                except Exception as ex:
                    pass

            if action == 'editinstructor':
                try:
                    data['title'] = u'Editar Instructor'
                    data['instructor'] = instructor=CapInstructor.objects.get(pk=int(request.GET['id']))
                    lista = CapInstructor.objects.values_list('instructor_id').filter(capeventoperiodo=instructor.capeventoperiodo, status=True).exclude(pk=instructor.id)
                    form = CapInstructorForm(initial={'instructor':instructor.instructor_id,
                                                      'tipo': instructor.tipo,
                                                      'instructorprincipal': instructor.instructorprincipal})
                    data['periodo']= instructor.capeventoperiodo.periodo_id
                    form.editar(instructor)
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodo/editinstructor.html", data)
                except Exception as ex:
                    pass

            if action == 'instructor':
                try:
                    data['title'] = u'Instructor'
                    data['instructor'] = CapInstructor.objects.filter(capeventoperiodo=int(request.GET['id']), status=True)
                    data['eventoperiodo'] = CapEventoPeriodo.objects.get(pk=int(request.GET['id']), status=True)
                    return render(request, "adm_capacitacioneventoperiodo/viewinstructor.html", data)
                except Exception as ex:
                    pass

            #HORARIOS
            if action == 'addclase':
                try:
                    data['title'] = u'Adicionar horario'
                    evento = CapEventoPeriodo.objects.get(pk=int(request.GET['cepid']))
                    form = CapClaseForm(initial={'capeventoperiodo': evento,
                                                 'turno': CapTurno.objects.get(pk=request.GET['turno']),
                                                 'dia': request.GET['dia'],
                                                 'fechainicio': evento.fechainicio,
                                                 'fechafin': evento.fechafin})
                    data['cepid'] = evento.id
                    form.editar_grupo()
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodo/addclase.html", data)
                except Exception as ex:
                    pass

            if action == 'delclase':
                try:
                    data['title'] = u'Eliminar horario'
                    data['clase'] =clase= CapClase.objects.get(pk=int(request.GET['cid']))
                    data['eventoperiodo'] = clase.capeventoperiodo.id
                    return render(request, "adm_capacitacioneventoperiodo/delclase.html", data)
                except Exception as ex:
                    pass

            if action == 'editclase':
                try:
                    data['title'] = u'Editar horario'
                    clase = CapClase.objects.get(pk=int(request.GET['cid']))
                    form = CapClaseForm(initial={'capeventoperiodo': clase.capeventoperiodo,
                                                 'turno': clase.turno,
                                                 'fechainicio': clase.fechainicio,
                                                 'fechafin': clase.fechafin,
                                                 'dia': clase.dia})
                    data['cepid'] = clase.capeventoperiodo.id
                    data['claseid'] = clase.id
                    form.editar_grupo()
                    form.editar_turno()
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodo/editclase.html", data)
                except Exception as ex:
                    pass

            if action == 'horario':
                try:
                    data['title'] = u'Horarios'
                    data['capeventoperiodo'] = None
                    data['eventoperiodoid'] = None
                    data['semana'] = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
                    evento = CapEventoPeriodo.objects.get(pk=int(request.GET['id']))
                    data['activo'] = datetime.now().date() <= evento.fechafin
                    data['turnos'] = CapTurno.objects.filter(status=True)
                    data['capeventoperiodo'] = evento
                    data['eventoperiodoid'] = evento.id
                    return render(request, "adm_capacitacioneventoperiodo/horario.html", data)
                except Exception as ex:
                    pass

            #ASISTENCIA
            if action == 'asistencia':
                try:
                    data['title'] = u'Horarios'
                    dia = 0
                    clase_activa = False
                    capeventoperiodo = CapEventoPeriodo.objects.get(pk=int(request.GET['id']))
                    semana = [[0, 'Hoy'], [1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'],[4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo'], [8, 'Todos']]
                    if 'd' in request.GET:
                        dia = int(request.GET['d'])
                        if dia == 8 :
                            data['dias'] = {1:'Lunes', 2: 'Martes', 3:'Miercoles',4:'Jueves', 5:'Viernes', 6:'Sabado', 7: 'Domingo'}
                        elif dia > 0 and dia < 8:
                            data['dias'] = {DIAS_CHOICES[dia-1][0]:  DIAS_CHOICES[dia-1][1]}
                    else:
                        clase_activa = True
                        data['fecha_hoy'] = datetime.now().date()
                        data['clases_hoy'] = capeventoperiodo.clases_activas()
                        data['dias'] = {DIAS_CHOICES[date.today().weekday()][0]: DIAS_CHOICES[date.today().weekday()][1]}
                    data['select_dia'] = dia
                    data['capeventoperiodo'] = capeventoperiodo
                    data['clase_activa'] = clase_activa
                    data['dia_list'] = semana
                    form = CapAsistenciaForm()
                    form.adicionar(capeventoperiodo)
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodo/asistencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'addasistencia':
                try:
                    revisar=False
                    data['title'] = u'Asistencia'
                    data['cabeceraasistencia'] = asistencia = CapCabeceraAsistencia.objects.get(pk=int(request.GET['id']))
                    data['clase']= asistencia.clase
                    data['listadoinscritos'] = asistencia.clase.capeventoperiodo.inscritos_aprobado()
                    if 'm' in request.GET:
                        revisar=True
                    data['revisar'] = revisar
                    return render(request, "adm_capacitacioneventoperiodo/addasistencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'delasistencia':
                try:
                    data['title'] = u'Eliminar asistencia'
                    data['cabeceraasistencia'] = CapCabeceraAsistencia.objects.get(pk=int(request.GET['id']))
                    data['dia'] = int(request.GET['d'])
                    return render(request, "adm_capacitacioneventoperiodo/delasistencia.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Periodo de Evento'
            data['periodo'] = CapPeriodo.objects.filter(status=True).order_by('fechainicio')
            return render(request, "adm_capacitacioneventoperiodo/viewperiodo.html", data)