# -*- coding: UTF-8 -*-
import random
from datetime import datetime
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse, request
from django.http.response import HttpResponse, HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from django.template.context import Context
from django.template.loader import get_template
import xlwt
from xlwt import *
from sga.commonviews import adduserdata
from sga.forms import VirtualIncidenteForm, VirtualIncidenteAsignadoForm, VirtualCausaIncidenteForm, \
    ReporteSoporteUsuarioForm, DetalleReporteSoporteUsuarioForm, DocumentoEntregadoForm, \
    AnexosReporteUsuarioVirtualForm, TipoActividadVirtualForm, EditDetalleReporteSoporteUsuarioForm, \
    AsignarSoporteEstudiante
from sga.funciones import log, generar_nombre, MiPaginador
from sga.models import VirtualSoporteUsuario, VirtualSoporteUsuarioIncidentes, VirtualSoporteUsuarioInscripcion, \
    VirtualCausaIncidente, VirtualIncidenteAsignado, VirtualSoporteAsignado, ReporteSoporteVirtual, \
    DetalleReporteSoporteVirtual, DocumentoEntregado, AnexosReporteUsuarioVirtual, TipoActividadVirtual, Carrera, \
    Materia, Silabo, PlanificacionClaseSilabo, Matricula, Profesor, VirtualSoporteUsuarioProfesor, \
    ProfesorDistributivoHoras

from sga.templatetags.sga_extras import encrypt
from sga.funcionesxhtml2pdf import conviert_html_to_pdf


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['periodo'] = periodo = request.session['periodo']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'virtual_incidenteasignado':
                try:
                    if 'archivo' in request.FILES:
                        d = request.FILES['archivo']
                        if d.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                    form = VirtualIncidenteAsignadoForm(request.POST)
                    if form.is_valid():
                        incidenteasignado = VirtualIncidenteAsignado.objects.get(pk=int(encrypt(request.POST['id'])))
                        if form.cleaned_data['estado'] == '2':
                            incidente = incidenteasignado.incidente
                            incidente.fecha_finalizaticket = datetime.now()
                            incidente.estado = form.cleaned_data['estado']
                            incidente.save(request)
                            incidenteasignado.planaccion = form.cleaned_data['planaccion']
                            incidenteasignado.estado = 3
                            incidenteasignado.finalizado = True
                            incidenteasignado.fecha_finalizaasignacion = datetime.now()
                            incidenteasignado.save(request)
                            incidente.envio_correo_incidente(20, request)
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("evidenciaincidente", newfile._name)
                                incidenteasignado.archivo = newfile
                                incidenteasignado.save(request)
                        if form.cleaned_data['estado'] == '3':
                            incidenteasignado.planaccion = form.cleaned_data['planaccion']
                            incidenteasignado.fecha_finalizaasignacion = datetime.now()
                            incidenteasignado.save(request)
                            incidenteasignadoadd = VirtualIncidenteAsignado(incidente=incidenteasignado.incidente,
                                                                            soporteusuarioasignado=form.cleaned_data['personaasignar'],
                                                                            fecha_creaasignacion=datetime.now(),
                                                                            estado=3
                                                                            )
                            incidenteasignadoadd.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'addcausa':
                try:
                    form = VirtualCausaIncidenteForm(request.POST)
                    if form.is_valid():
                        if not VirtualCausaIncidente.objects.filter(status=True, descripcion=form.cleaned_data['descripcion']).exists():
                            causa = VirtualCausaIncidente(descripcion=form.cleaned_data['descripcion'],
                                                          prioridad=form.cleaned_data['prioridad'])
                            causa.save(request)
                            log(u'Agrego una nueva Causa incidente virtual: %s' % causa, request, "add")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"El registro ya existe."})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

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
                    form = DetalleReporteSoporteUsuarioForm(request.POST)
                    tipo = int(request.POST['tipoactividad'])
                    reporte = ReporteSoporteVirtual.objects.get(pk=int(request.POST['id_reporte']))
                    tipoactividad = TipoActividadVirtual.objects.get(pk=tipo)
                    if not tipo==1 and not tipo==2 and not tipo==3:
                        if form.is_valid():
                            detalle = DetalleReporteSoporteVirtual(reporte=reporte,
                                fechaactividad=form.cleaned_data['fechaactividad'],
                                tipoactividad=tipoactividad,
                                tiposistema=form.cleaned_data['tiposistema'],
                                nombreactividad=form.cleaned_data['nombreactividad']
                            )
                            detalle.save(request)
                            log(u'Agrego una nueva actividad virtual: %s' % detalle, request, "add")
                            return JsonResponse({"result": "ok"})
                        else:
                            raise NameError('Error')
                    else :
                        return JsonResponse({"result": "bad", "mensaje": u"Este tipo de actividad, requiere de actividades adicionales"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'actividades_extraidas_sga':
                try:
                    reporte = ReporteSoporteVirtual.objects.get(pk=int(request.POST['id']))
                    carrera = Carrera.objects.get(pk=int(request.POST['idcarrera']))
                    materia = Materia.objects.get(pk=int(request.POST['idmateria']))
                    actividad = TipoActividadVirtual.objects.get(pk=int(request.POST['idactividad']))
                    fini=request.POST['fini']
                    ffin=request.POST['ffin']
                    fechaactividad=request.POST['fecha']
                    accion=request.POST['accion']
                    observaciones=request.POST['observacion']
                    titulo=request.POST['titulo']
                    silabocab = Silabo.objects.get(materia__codigosakai=materia.codigosakai,status=True)
                    if not PlanificacionClaseSilabo.objects.filter(tipoplanificacion__planificacionclasesilabo_materia__materia=silabocab.materia,status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Noo tiene cronograma académico."})
                    DetalleReporteSoporteVirtual.objects.filter(reporte=reporte, tipoactividad_id=actividad.id,accion=accion,carrera=carrera,materia=materia).delete()

                    for p in PlanificacionClaseSilabo.objects.filter(tipoplanificacion__planificacionclasesilabo_materia__materia=silabocab.materia,status=True,fechainicio__gte=fini,fechafin__lte=ffin).exclude(semana=0).order_by('orden'):
                        semana = None
                        idcodigo = 0
                        if silabocab.silabosemanal_set.filter(fechainiciosemana__gte=p.fechainicio,fechafinciosemana__lte=p.fechafin).exists():
                            lissemana = silabocab.silabosemanal_set.filter(fechainiciosemana__gte=p.fechainicio, fechafinciosemana__lte=p.fechafin)[0]
                            idcodigo = lissemana.id
                            semana = lissemana
                        modelosilabo = semana
                        for uni in modelosilabo.unidades_silabosemanal():
                            for temassel in modelosilabo.temas_silabosemanal(uni.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.id):
                                if not actividad.id == 3:
                                    nombre_actividad =accion +" "+actividad.titulo+" de la carrera "+carrera.nombre+" de la asignatura "+materia.asignatura.nombre+" de la semana "+str(p.semana)+" con el tema: "+temassel.temaunidadresultadoprogramaanalitico.descripcion+"."
                                else:
                                    nombre_actividad=accion+" en el Campus Virtual las tareas, foros y lecciones de la carrera "+carrera.nombre+" de la asignatura "+materia.asignatura.nombre+" de la semana "+str(p.semana)+" con el tema: "+temassel.temaunidadresultadoprogramaanalitico.descripcion+"."

                                if actividad.id==3 or actividad.id==2 or actividad.id==1:
                                    detalle = DetalleReporteSoporteVirtual(reporte=reporte,
                                                                           observacion = observaciones if observaciones else '',
                                                                           fechaactividad=p.fechainicio,
                                                                           tipoactividad=actividad,
                                                                           tiposistema='SGA' if not actividad.id == 3 else 'SAKAI',
                                                                           nombreactividad=nombre_actividad,
                                                                           accion=accion,
                                                                           carrera=carrera,
                                                                           materia=materia
                                                                           )
                                    detalle.save()
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'plan_semanal_clase_virtual':
                try:
                    data['title'] = u'PLANIFICACIÓN SEMANAL DE SÍLABO'
                    panalitico = 0
                    materia = Materia.objects.get(pk=int(request.POST['idmateria']))
                    fini=request.POST['fini']
                    ffin=request.POST['ffin']
                    data['silabocab'] = silabocab = Silabo.objects.get(materia__codigosakai=materia.codigosakai,status=True)
                    if not PlanificacionClaseSilabo.objects.filter(tipoplanificacion__planificacionclasesilabo_materia__materia=silabocab.materia,status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Noo tiene cronograma académico."})
                    data['planificacion'] = PlanificacionClaseSilabo.objects.filter( tipoplanificacion__planificacionclasesilabo_materia__materia=silabocab.materia,status=True,fechainicio__gte=fini,fechafin__lte=ffin).exclude(semana=0).order_by('orden')
                    lista = []
                    if PlanificacionClaseSilabo.objects.filter( tipoplanificacion__planificacionclasesilabo_materia__materia=silabocab.materia, status=True,fechainicio__gte=fini, fechafin__lte=ffin).exclude(semana=0).exists():
                        for p in PlanificacionClaseSilabo.objects.filter(tipoplanificacion__planificacionclasesilabo_materia__materia=silabocab.materia,status=True,fechainicio__gte=fini,fechafin__lte=ffin).exclude(semana=0).order_by('orden'):
                            semana = None
                            idcodigo = 0
                            if silabocab:
                                if silabocab.silabosemanal_set.filter(fechainiciosemana__gte=p.fechainicio,fechafinciosemana__lte=p.fechafin).exists():
                                    lissemana = silabocab.silabosemanal_set.filter(fechainiciosemana__gte=p.fechainicio, fechafinciosemana__lte=p.fechafin)[0]
                                    idcodigo = lissemana.id
                                    semana = lissemana
                                    idcodigo = idcodigo
                                    modelosilabo = semana
                                    lista.append([p.fechainicio.isocalendar()[1], p.fechainicio, p.fechafin, idcodigo, modelosilabo,p.semana])
                        data['fechas'] = lista
                        template = get_template("virtual_admsoporte_online/planificacionsemanal.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"No existen planificaciones para la fecha ingresada"})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


            if action == 'actividades_extraidas':
                try:
                    reporte = ReporteSoporteVirtual.objects.get(pk=int(request.POST['id_reporte']))
                    soporteusuario = VirtualSoporteUsuario.objects.get(persona=persona, activo=True)
                    if not TipoActividadVirtual.objects.filter(titulo='ATENCIÓN A LOS TICKET DE SOPORTE USUARIO').exists():
                        tipoactividad = TipoActividadVirtual(titulo='ATENCIÓN A LOS TICKET DE SOPORTE USUARIO')
                        tipoactividad.save(request)
                    else:
                        tipoactividad=TipoActividadVirtual.objects.filter(titulo='ATENCIÓN A LOS TICKET DE SOPORTE USUARIO')[0]

                    if soporteusuario.actividades_realizadas(request.POST['fini'],request.POST['ffin']):
                        DetalleReporteSoporteVirtual.objects.filter(reporte=reporte,tipoactividad=tipoactividad).delete()
                        for actividad in soporteusuario.actividades_realizadas(request.POST['fini'],request.POST['ffin']):
                            detalle = DetalleReporteSoporteVirtual(reporte=reporte,
                                                                   fechaactividad=actividad.fecha_creaasignacion,
                                                                   tipoactividad=tipoactividad,
                                                                   tiposistema='SGA',
                                                                   nombreactividad = tipoactividad.titulo,
                                                                   accion=''
                                                                   )
                            detalle.save()

                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"No tiene tickets asignados en esa fecha"})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

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
                        if not TipoActividadVirtual.objects.filter(titulo=form.cleaned_data['titulo'].upper()).exists():
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

            if action == 'editcausa':
                try:
                    causa = VirtualCausaIncidente.objects.get(pk=int(request.POST['id']))
                    form = VirtualCausaIncidenteForm(request.POST)
                    if form.is_valid():
                        if not VirtualCausaIncidente.objects.filter(status=True, prioridad=form.cleaned_data['prioridad'], descripcion=form.cleaned_data['descripcion'].upper()).exclude(pk=causa.id).exists():
                            causa.descripcion = form.cleaned_data['descripcion']
                            causa.prioridad = form.cleaned_data['prioridad']
                            causa.save(request)
                            log(u'Editar causa incidente virtual: %s' % causa, request, "edit")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"El nombre de causa ya existe."})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

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
                    form = EditDetalleReporteSoporteUsuarioForm(request.POST)
                    if form.is_valid():
                            actividad.tipoactividad = form.cleaned_data['tipoactividad']
                            actividad.tiposistema = form.cleaned_data['tiposistema'].upper()
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

            if action == 'delcausa':
                try:
                    causa = VirtualCausaIncidente.objects.get(pk=int(request.POST['id']))
                    causa.delete()
                    log(u'Elimino causa incidente virtual: %s' % causa, request, "del")
                    return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente.."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

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

            elif action == 'asignarestudiantescarrera':
                try:
                    form = AsignarSoporteEstudiante(request.POST)
                    if form.is_valid():
                        soportes = VirtualSoporteUsuario.objects.get(id=request.POST['soporte'])
                        carrera = form.cleaned_data['carrera']
                        matriculas = Matricula.objects.filter(status=True, nivel__periodo=periodo,
                                                              inscripcion__carrera__id__in=carrera).distinct().order_by(
                            'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                            'inscripcion__persona__nombres')
                        for matricula in matriculas:
                            if VirtualSoporteUsuarioInscripcion.objects.filter(status=True, matricula=matricula,
                                                                               soporteusuario=soportes).exists():
                                soporte = \
                                VirtualSoporteUsuarioInscripcion.objects.filter(status=True, matricula=matricula,
                                                                                soporteusuario=soportes)[0]
                                if soporte.activo == False:
                                    soporte.activo = True
                            else:
                                soporte = VirtualSoporteUsuarioInscripcion(matricula=matricula, soporteusuario=soportes,
                                                                           activo=True)
                            if soporte:
                                soporte.save(request)
                        for eliminar in VirtualSoporteUsuarioInscripcion.objects.filter(status=True,
                                                                                        soporteusuario=soportes,
                                                                                        matricula__nivel__periodo=periodo).exclude(
                                matricula__inscripcion__carrera__id__in=carrera):
                            eliminar.status = False
                            eliminar.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

            elif action == 'desactivarsoporte':
                try:
                    if request.POST['tipo'] == 'inscripcion':
                        if VirtualSoporteUsuarioInscripcion.objects.filter(id=request.POST['id'], status=True).exists():
                            soporte = VirtualSoporteUsuarioInscripcion.objects.get(id=request.POST['id'], status=True)
                            soporte.activo = False
                            soporte.save(request)
                    elif request.POST['tipo'] == 'tutor':
                        if VirtualSoporteUsuarioProfesor.objects.filter(id=request.POST['id'], activo=True).exists():
                            soporte = VirtualSoporteUsuarioProfesor.objects.get(id=request.POST['id'], activo=True)
                            soporte.activo = False
                            soporte.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'activarsoporte':
                try:
                    soporte = VirtualSoporteUsuario.objects.get(id=request.POST['soporte'])
                    if 'matricula' in request.POST:
                        matricula = Matricula.objects.get(id=request.POST['matricula'])
                        if VirtualSoporteUsuarioInscripcion.objects.filter(status=True, matricula=matricula,
                                                                           soporteusuario=soporte).exists():
                            soporte = VirtualSoporteUsuarioInscripcion.objects.filter(status=True, matricula=matricula,
                                                                                      soporteusuario=soporte)[0]
                            if soporte.activo == False:
                                soporte.activo = True
                            else:
                                soporte.activo = False
                        else:
                            soporte = VirtualSoporteUsuarioInscripcion(matricula=matricula, soporteusuario=soporte,
                                                                       activo=True)
                        if soporte:
                            soporte.save(request)
                        return JsonResponse({"result": "ok"})

                    elif 'tutor' in request.POST:
                        profesor = Profesor.objects.get(id=request.POST['tutor'])
                        if VirtualSoporteUsuarioProfesor.objects.filter(activo=True, profesor=profesor,
                                                                        soporteusuario=soporte).exists():
                            soporte = VirtualSoporteUsuarioProfesor.objects.filter(activo=True, profesor=profesor,
                                                                                   soporteusuario=soporte)[0]
                            if soporte.activo == False:
                                soporte.activo = True
                            else:
                                soporte.activo = False
                        else:
                            soporte = VirtualSoporteUsuarioProfesor(profesor=profesor, soporteusuario=soporte,
                                                                    activo=True)
                        if soporte:
                            soporte.save(request)
                        return JsonResponse({"result": "ok"})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

            elif action == 'asignartutorescarrera':
                try:
                    form = AsignarSoporteEstudiante(request.POST)
                    if form.is_valid():
                        soportes = VirtualSoporteUsuario.objects.get(id=request.POST['soporte'])
                        carrera = form.cleaned_data['carrera']
                        profesordistributivohoras = ProfesorDistributivoHoras.objects.filter(periodo=periodo, carrera__id__in=carrera, profesor__profesormateria__tipoprofesor__id__in=[7,8]).distinct('profesor')
                        for profesordistributivo in profesordistributivohoras:
                            if VirtualSoporteUsuarioProfesor.objects.filter(status=True, profesor=profesordistributivo.profesor,
                                                                               soporteusuario=soportes).exists():
                                soporte = VirtualSoporteUsuarioProfesor.objects.filter(status=True, profesor=profesordistributivo.profesor,
                                                                                soporteusuario=soportes)[0]
                                if soporte.activo == False:
                                    soporte.activo = True
                            else:
                                soporte = VirtualSoporteUsuarioProfesor(soporteusuario=soportes,profesor=profesordistributivo.profesor,activo=True)
                            if soporte:
                                soporte.save(request)
                        for eliminar in VirtualSoporteUsuarioProfesor.objects.filter(status=True,
                                                                                        soporteusuario=soportes,
                                                                                        profesor__profesordistributivohoras__periodo=periodo).exclude(
                                profesor__profesordistributivohoras__carrera__id__in=carrera):
                            eliminar.status = False
                            eliminar.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

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
                        (u"CEDULA", 4000),
                        (u"NOMBRE", 10000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listadoinscripcion = VirtualSoporteUsuarioInscripcion.objects.filter(soporteusuario__persona=persona, status=True).order_by('matricula__inscripcion__persona__apellido1')
                    row_num = 4
                    for listado in listadoinscripcion:
                        i = 0
                        campo1 = listado.matricula.inscripcion.persona.cedula
                        campo2 = listado.matricula.inscripcion.persona

                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2.__str__(), font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'reporteincidentesexcell':
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

                    listadoincidentesdetalle = VirtualIncidenteAsignado.objects.filter(incidente__soporteiniscripcion__soporteusuario__persona=persona,incidente__fecha_creaticket__gte=fech_ini, incidente__fecha_creaticket__lte=fech_fin, incidente__status=True,status=True).order_by('id')
                    row_num = 4
                    i = 0
                    for listado in listadoincidentesdetalle:
                        i += 1
                        campo1 = listado.incidente.soporteiniscripcion.matricula.inscripcion.persona.cedula
                        campo2 = listado.incidente.soporteiniscripcion.matricula.inscripcion.persona.apellido1 + ' ' + listado.incidente.soporteiniscripcion.matricula.inscripcion.persona.apellido2 + ' ' + listado.incidente.soporteiniscripcion.matricula.inscripcion.persona.nombres
                        campo3 = listado.incidente.soporteiniscripcion.matricula.inscripcion.persona.email
                        campo4 = listado.incidente.soporteiniscripcion.matricula.inscripcion.persona.telefono
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

                        ws.write(row_num, 0, campo14, font_style2)
                        ws.write(row_num, 1, campo1, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, campo3, font_style2)
                        ws.write(row_num, 4, campo4, font_style2)
                        ws.write(row_num, 5, campo5, date_format)
                        ws.write(row_num, 6, campo6, date_format)
                        ws.write(row_num, 7, campo9, font_style2)
                        ws.write(row_num, 8, campo12, font_style2)
                        ws.write(row_num, 9, campo10, font_style2)
                        ws.write(row_num, 10, campo11, font_style2)
                        ws.write(row_num, 11, campo13, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'virtual_incidenteasignado':
                try:
                    data['title'] = u'Incidente'
                    data['incidente'] = incidente = VirtualSoporteUsuarioIncidentes.objects.get(pk=request.GET['idincidente'], status=True)
                    data['listaasignado'] = asignado = incidente.virtualincidenteasignado_set.filter(status=True).order_by('id')
                    data['usuarioasignado'] = asignado.filter(status=True).order_by('-id')[0]
                    userasignado = None
                    if incidente.virtualincidenteasignado_set.filter(status=True):
                        asignado = incidente.virtualincidenteasignado_set.filter(status=True)[0]
                        userasignado = asignado.soporteusuarioasignado
                    data['form'] = VirtualIncidenteAsignadoForm(initial={'causaincidente': incidente.causaincidente,
                                                                         'telefono': incidente.soporteiniscripcion.matricula.inscripcion.persona.telefono,
                                                                         'estado': incidente.estado,
                                                                         'personaasignar': userasignado,
                                                                         'email': incidente.soporteiniscripcion.matricula.inscripcion.persona.email
                                                                         })
                    return render(request, "virtual_admsoporte_online/virtual_incidenteasignado.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadocausas':
                try:
                    data['title'] = u'Causas de Incidentes'
                    data['listadocausas'] = VirtualCausaIncidente.objects.filter(status=True).order_by('id')
                    return render(request, "virtual_admsoporte_online/listadocausas.html", data)
                except Exception as ex:
                    pass

            elif action == 'lista_reportes':
                try:
                    soporteusuario = VirtualSoporteUsuario.objects.get(persona=persona, activo=True)
                    data['title'] = u'Reportes Generados'
                    data['reportes'] = soporteusuario.reportesoportevirtual_set.all()
                    return render(request, "virtual_admsoporte_online/lista_reportes.html", data)
                except Exception as ex:
                    pass

            elif action == 'listado_tipoactividad':
                try:
                    data['title'] = u'Listado de Tipos de Actividades'
                    data['listadoactividades'] = TipoActividadVirtual.objects.all().order_by('id')
                    return render(request, "virtual_admsoporte_online/listado_actividades.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcausa':
                try:
                    data['title'] = u'Adicionar Causa'
                    data['form'] = VirtualCausaIncidenteForm()
                    return render(request, 'virtual_admsoporte_online/addcausa.html', data)
                except Exception as ex:
                    pass

            elif action == 'addreporte':
                try:
                    data['title'] = u'Adicionar Reporte'
                    data['form'] = ReporteSoporteUsuarioForm(initial={'semestre':'IISEM2018','objetivo':'Informar Actividades que se han realizado en el perfil designado como Personal de Apoyo Académico durante el mes de abril del 2019.'})
                    data['soporteusuario'] = soporteusuario = VirtualSoporteUsuario.objects.get(persona=persona, activo=True)
                    return render(request, 'virtual_admsoporte_online/addreporte.html', data)
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
                    return render(request, 'virtual_admsoporte_online/editreporte.html', data)
                except Exception as ex:
                    pass

            elif action == 'addactividad':
                try:
                    data['title'] = u'Adicionar Actividades'
                    data['form'] = DetalleReporteSoporteUsuarioForm()
                    data['reporte'] = reporte = ReporteSoporteVirtual.objects.get(pk=int(request.GET['idreporte']))
                    data['carreras'] = carreras = Carrera.objects.filter(modalidad=3)
                    return render(request, 'virtual_admsoporte_online/addactividad.html', data)
                except Exception as ex:
                    pass

            elif action == 'editactividad':
                try:
                    data['title'] = u'Editar Actividades'
                    data['actividad'] = actividad = DetalleReporteSoporteVirtual.objects.get(pk=int(request.GET['id']))
                    form = EditDetalleReporteSoporteUsuarioForm(initial={'fechaactividad': actividad.fechaactividad,'tipoactividad':actividad.tipoactividad, 'nombreactividad': actividad.nombreactividad,'tiposistema':actividad.tiposistema})
                    form.editar(actividad)
                    data['form'] = form
                    return render(request, 'virtual_admsoporte_online/editactividad.html', data)
                except Exception as ex:
                    pass

            elif action == 'adddocumento':
                try:
                    data['title'] = u'Adicionar Documento'
                    data['form'] = DocumentoEntregadoForm()
                    data['reporte'] = reporte = ReporteSoporteVirtual.objects.get(pk=int(request.GET['idreporte']))
                    return render(request, 'virtual_admsoporte_online/adddocumento.html', data)
                except Exception as ex:
                    pass

            elif action == 'addtipoactividad':
                try:
                    data['title'] = u'Adicionar Tipo de Actividad'
                    data['form'] = TipoActividadVirtualForm()
                    if 'idreporte' in request.GET:
                        data['reporte'] = reporte = ReporteSoporteVirtual.objects.get(pk=int(request.GET['idreporte']))
                    return render(request, 'virtual_admsoporte_online/addtipoactividad.html', data)
                except Exception as ex:
                    pass

            elif action == 'edittipoactividad':
                try:
                    data['title'] = u'Editar Tipo de Actividad'
                    data['actividad'] = actividad = TipoActividadVirtual.objects.get(pk=int(request.GET['id']))
                    data['form'] = TipoActividadVirtualForm(initial={'titulo':actividad.titulo})
                    return render(request, 'virtual_admsoporte_online/edittipoactividad.html', data)
                except Exception as ex:
                    pass

            elif action == 'editdocumento':
                try:
                    data['title'] = u'Editar Documento'
                    data['documento'] = documento = DocumentoEntregado.objects.get(pk=int(request.GET['id']))
                    form = DocumentoEntregadoForm(initial={'nombredocumento':documento.nombredocumento})
                    data['form'] = form
                    return render(request, 'virtual_admsoporte_online/editdocumento.html', data)
                except Exception as ex:
                    pass

            elif action == 'addanexo':
                try:
                    data['title'] = u'Adicionar Anexo'
                    data['form'] = AnexosReporteUsuarioVirtualForm()
                    data['documento'] = documento = DocumentoEntregado.objects.get(pk=int(request.GET['id_documento']))
                    return render(request, 'virtual_admsoporte_online/addanexo.html', data)
                except Exception as ex:
                    pass

            elif action == 'listar_actividades_soporte':
                try:
                    data['title'] = u'Actividades y Documentos Realizados'
                    data['form'] = DetalleReporteSoporteUsuarioForm()
                    data['reporte'] = reporte = ReporteSoporteVirtual.objects.get(pk=int(request.GET['idreporte']))
                    data['listadoactividades'] = reporte.detallereportesoportevirtual_set.all().order_by('fechaactividad')
                    data['documentos'] = reporte.documentoentregado_set.all().order_by('id')
                    return render(request, 'virtual_admsoporte_online/listadoactividades.html', data)
                except Exception as ex:
                    pass

            elif action == 'listar_anexos':
                try:
                    data['title'] = u'Listado de Anexos'
                    data['documento'] = documento = DocumentoEntregado.objects.get(pk=int(request.GET['id']))
                    return render(request, 'virtual_admsoporte_online/listado_anexos.html', data)
                except Exception as ex:
                    pass

            elif action == 'editcausa':
                try:
                    data['title'] = u'Editar Causa'
                    data['causa'] = causa = VirtualCausaIncidente.objects.get(pk=int(request.GET['id']))
                    form = VirtualCausaIncidenteForm(initial={'descripcion':causa.descripcion,'prioridad':causa.prioridad })
                    data['form'] = form
                    return render(request, "virtual_admsoporte_online/editcausa.html", data)
                except Exception as ex:
                    pass

            elif action == 'delcausa':
                try:
                    data['title'] = u'Eliminar Causa'
                    data['causa'] = VirtualCausaIncidente.objects.get(pk=int(request.GET['id']))
                    return render(request, "virtual_admsoporte_online/delcausa.html", data)
                except Exception as ex:
                    pass

            elif action == 'delactividad':
                try:
                    data['title'] = u'Eliminar Actividad'
                    data['actividad'] = actividad = DetalleReporteSoporteVirtual.objects.get(pk=int(request.GET['id']))
                    data['idreporte'] = actividad.reporte.id
                    return render(request, "virtual_admsoporte_online/delactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'deltipoactividad':
                try:
                    data['title'] = u'Eliminar Actividad'
                    data['actividad'] = actividad = TipoActividadVirtual.objects.get(pk=int(request.GET['id']))
                    return render(request, "virtual_admsoporte_online/deltipoactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'deldocumento':
                try:
                    data['title'] = u'Eliminar Documento'
                    data['documento'] = documento = DocumentoEntregado.objects.get(pk=int(request.GET['id']))
                    return render(request, "virtual_admsoporte_online/deldocumento.html", data)
                except Exception as ex:
                    pass

            elif action == 'delanexo':
                try:
                    data['title'] = u'Eliminar Anexo'
                    data['anexo'] = anexo = AnexosReporteUsuarioVirtual.objects.get(pk=int(request.GET['id']))
                    return render(request, "virtual_admsoporte_online/delanexo.html", data)
                except Exception as ex:
                    pass

            elif action == 'generar_reporte_soporte':
                try:
                    data['title'] = u'Eliminar Causa'
                    data['reporte'] = reporte = ReporteSoporteVirtual.objects.get(pk=int(request.GET['id']))
                    return conviert_html_to_pdf('virtual_admsoporte_online/imprimir_reporte_soporte.html',
                                                {'pagesize': 'A4',
                                                 'data': data,
                                                 'reporte': reporte,
                                                 })
                except Exception as ex:
                    pass

            elif action == 'generar_anexo_soporte':
                try:
                    data['title'] = u'Eliminar Causa'
                    data['reporte'] = reporte = ReporteSoporteVirtual.objects.get(pk=int(request.GET['id']))
                    return conviert_html_to_pdf('virtual_admsoporte_online/imprimir_anexo_soporte.html',
                                                {'pagesize': 'A4',
                                                 'data': data,
                                                 'reporte': reporte,
                                                 })
                except Exception as ex:
                    pass

            elif action == 'listaasignatura':
                try:
                    if 'idcarrera' in request.GET:
                        data['idcarrera'] = idcarrera = request.GET['idcarrera']
                        carrera = Carrera.objects.get(id=idcarrera)
                        lista=[]
                        materias = Materia.objects.filter(status=True,asignaturamalla__malla__carrera=carrera,nivel__periodo=periodo).order_by('asignatura')
                        for x in materias:
                            lista.append([x.id, x.flexbox_repr()])
                        data = {"result": "ok", "lista": lista}
                        return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'soportes_activos':
                try:
                    data['title'] = u'Listado de Soportes'
                    data['soportes'] = VirtualSoporteUsuario.objects.filter(activo=True)
                    return render(request, "virtual_admsoporte_online/soporte_activo.html", data)
                except Exception as ex:
                    pass

            elif action == 'ver_asigandos':
                try:
                    data['title'] = u'Estudiantes Asignados'
                    data['soporte'] = soporte = VirtualSoporteUsuario.objects.get(pk=request.GET['id'])
                    data['asignados'] = soporte.asignados(periodo)
                    return render(request, "virtual_admsoporte_online/asignar_usuarios.html", data)
                except Exception as ex:
                    pass

            elif action == 'asignarestudiantescarrera':
                try:
                    from itertools import chain
                    data['title'] = u'Asignar Estudiantes'
                    data['soporte'] = soporte = VirtualSoporteUsuario.objects.get(id=request.GET['ids'])
                    carreras = soporte.virtualsoporteusuarioinscripcion_set.values_list('matricula__inscripcion__carrera__id',flat=True).filter(status=True, matricula__nivel__periodo=periodo).distinct()
                    carreras2id = Matricula.objects.values_list('inscripcion__carrera__id',flat=True).filter(status=True, nivel__periodo=periodo).distinct()
                    ids = list(chain(carreras, carreras2id))
                    form = AsignarSoporteEstudiante(initial={'carrera': Carrera.objects.filter(status=True, pk__in=carreras)})
                    form.cargar_carreras(ids)
                    data['form'] = form
                    return render(request, "virtual_admsoporte_online/asignar_estudiantes_carrera.html", data)
                except Exception as ex:
                    pass

            elif action == 'ver_tutores':
                try:
                    data['title'] = u'Listado de tutores online'
                    search = None
                    ids = None
                    inscripcionid = None
                    data['soporte'] = soporteusuario = VirtualSoporteUsuario.objects.get(pk=request.GET['id'])
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
                    return render(request, "virtual_admsoporte_online/ver_tutores.html", data)
                except Exception as ex:
                    pass

            elif action == 'asignartutorescarrera':
                try:
                    from itertools import chain
                    data['title'] = u'Asignar Turores'
                    data['soporte'] = soporte = VirtualSoporteUsuario.objects.get(id=request.GET['ids'])
                    idprofesor = VirtualSoporteUsuarioProfesor.objects.values_list('profesor__id',flat=True).filter(status=True,soporteusuario=soporte).distinct('profesor__id')
                    carreras = ProfesorDistributivoHoras.objects.values_list('carrera__id',flat=True).filter(profesor__id__in=idprofesor).distinct('carrera__id')
                    carreras2id = ProfesorDistributivoHoras.objects.values_list('carrera__id',flat=True).filter(periodo=periodo, profesor__profesormateria__tipoprofesor__id__in=[7,8]).distinct()
                    ids = list(chain(carreras, carreras2id))
                    form = AsignarSoporteEstudiante(initial={'carrera': Carrera.objects.filter(status=True, pk__in=carreras)})
                    form.cargar_carreras(ids)
                    data['form'] = form
                    return render(request, "virtual_admsoporte_online/asignar_tutores_carrera.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Listado de asignaciones online'
            searchasig = None
            idsasig = None
            inscripcionidasig = None
            if VirtualSoporteUsuario.objects.filter(persona=persona, activo=True, status=True).exists():
                soporteusuario = VirtualSoporteUsuario.objects.get(persona=persona, activo=True)
            else:
                return HttpResponseRedirect("/?info=No tiene asignado usuarios soporte online.")
            if 'sasig' in request.GET:
                searchasig = request.GET['sasig'].strip()
                ssasig = searchasig.split(' ')
                if len(ssasig) == 1:
                    usuariosonlineasig = VirtualSoporteUsuarioIncidentes.objects.filter(
                        Q(soporteiniscripcion__matricula__inscripcion__persona__nombres__icontains=searchasig) |
                        Q(soporteiniscripcion__matricula__inscripcion__persona__apellido1__icontains=searchasig) |
                        Q(soporteiniscripcion__matricula__inscripcion__persona__apellido2__icontains=searchasig) |
                        Q(soporteiniscripcion__matricula__inscripcion__persona__cedula__icontains=searchasig) |
                        Q(soporteiniscripcion__matricula__inscripcion__persona__pasaporte__icontains=searchasig) |
                        Q(soporteiniscripcion__matricula__inscripcion__persona__telefono__icontains=searchasig) |
                        Q(soporteiniscripcion__matricula__inscripcion__persona__email__icontains=searchasig),
                        pk__in=soporteusuario.virtualincidenteasignado_set.values_list('incidente_id').filter(estado=3, status=True).distinct(),
                        # soporteiniscripcion__matricula__inscripcion__carrera__modalidad=3,soporteiniscripcion__matricula__nivel__periodo=periodo,
                        soporteiniscripcion__matricula__nivel__periodo=periodo,
                        status=True)
                else:
                    usuariosonlineasig = VirtualSoporteUsuarioIncidentes.objects.filter(
                        Q(soporteiniscripcion__matricula__inscripcion__persona__apellido1__icontains=ssasig[0]) &
                        Q(soporteiniscripcion__matricula__inscripcion__persona__apellido2__icontains=ssasig[1]),
                        # pk__in=soporteusuario.virtualincidenteasignado_set.values_list('incidente_id').filter(estado=3, status=True).distinct(), soporteiniscripcion__matricula__inscripcion__carrera__modalidad=3,soporteiniscripcion__matricula__nivel__periodo=periodo,
                        pk__in=soporteusuario.virtualincidenteasignado_set.values_list('incidente_id').filter(estado=3, status=True).distinct(), soporteiniscripcion__matricula__nivel__periodo=periodo,
                        status=True)
            else:
                usuariosonlineasig = VirtualSoporteUsuarioIncidentes.objects.filter(pk__in=soporteusuario.virtualincidenteasignado_set.values_list('incidente_id').filter(estado=3, status=True).distinct(),soporteiniscripcion__matricula__nivel__periodo=periodo, status=True).order_by('-id')
            data['totalasignados'] = usuariosonlineasig.filter(estado=3, status=True).count()
            pagingasig = MiPaginador(usuariosonlineasig, 10)
            pasig = 1
            try:
                paginasesionasig = 1
                if 'paginadorasig' in request.session:
                    paginasesionasig = int(request.session['paginadorasig'])
                if 'pageasig' in request.GET:
                    pasig = int(request.GET['pageasig'])
                else:
                    pasig = paginasesionasig
                try:
                    pageasig = pagingasig.page(pasig)
                except:
                    pasig = 1
                pageasig = pagingasig.page(pasig)
            except:
                pageasig = pagingasig.page(pasig)
            request.session['paginadorasig'] = pasig
            data['pagingasig'] = pagingasig
            data['pageasig'] = pageasig
            data['rangospagingasig'] = pagingasig.rangos_paginado(pasig)
            data['usuariosasignados'] = pageasig.object_list
            data['searchasig'] = searchasig if searchasig else ""
            data['idsasig'] = idsasig if idsasig else ""
            data['inscripcionid'] = inscripcionidasig if inscripcionidasig else ""
            return render(request, "virtual_admsoporte_online/view.html", data)
