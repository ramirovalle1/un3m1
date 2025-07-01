# -*- coding: latin-1 -*-
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from datetime import datetime, timedelta
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import SolicitudJustificacionAsistenciaForm
from sga.funciones import variable_valor, generar_nombre, log
from django.db.models import Q
from django.template.context import Context
from django.template.loader import get_template
from django.forms.models import model_to_dict
from sga.tasks import send_html_mail
from sga.models import SolicitudJustificacionAsistencia, MateriaJustificacionAsistencia, MateriaAsignada, \
    AsistenciaLeccion, DetalleMateriaJustificacionAsistencia, DetalleSolicitudJustificacionAsistencia, \
    CasosJustificacion, AutorizarAlumnoSolicitud, DiasNoLaborable, CUENTAS_CORREOS, miinstitucion, \
    Matricula, JustificacionAsistencia


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    data['inscripcion'] = inscripcion = perfilprincipal.inscripcion
    periodosesion=request.session['periodo']
    data['matricula'] = matricula = inscripcion.mi_matricula_periodo(periodosesion.id)
    if not matricula:
        return HttpResponseRedirect("/?info=Ud. aun no ha sido matriculado")
    if matricula.inscripcion.coordinacion.excluir or matricula.inscripcion.coordinacion.id == 7:
        return HttpResponseRedirect("/?info=Solo los alumnos de las carreras de PREGRADO pueden ingresar al módulo.")

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'add':
                mensaje_error = u"Error al guardar los datos."
                try:
                    form = SolicitudJustificacionAsistenciaForm(request.POST, request.FILES)
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        extencion = newfile._name.split('.')
                        exte = extencion[1]
                        if newfile.size > 50485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                        if not exte == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                        newfile._name = generar_nombre("evidencia_", newfile._name)

                    if form.is_valid():
                        casojustificativo = form.cleaned_data['casojustificacion']
                        # if casojustificativo:
                        #     if request.POST['numdiassolicitud']:
                        #         if int(request.POST['numdiassolicitud']) > 5:
                        #             return JsonResponse({"result": "bad", "mensaje": u"Imposible generar solicitud: Según instructivo de justificación de faltas en Art. 6"})
                        if casojustificativo.id == 8 or casojustificativo.id == 9:
                            if request.POST['numerodiasreposo']:
                                if int(request.POST['numerodiasreposo']) < 30:
                                    return JsonResponse({"result": "bad", "mensaje": u"Imposible generar solicitud: El caso seleccionado no cumple con el criterio de dias de reposo (más de 30 dias), por favor cambie las fechas de inicio y fin de reposo."})

                        if not newfile:
                            return JsonResponse({"result": "bad", "mensaje": u"Debe subir un archivo de evidencia"})
                        autorizados = matricula.autorizaralumnosolicitud_set.filter(activo=True)

                        extendida = False
                        extendida = form.cleaned_data['extendida']
                        if not extendida:
                            extendida = False

                        for autorizado in autorizados:
                            autorizado.activo = False
                            autorizado.save(request)
                            log(u'Se desactivo la autorizacion de justificación por que ya solicito el alumno: %s - [%s]' % (matricula, matricula.id), request, "add")
                        asignatura_horario = json.loads(request.POST['lista_items1'])
                        solicitud = SolicitudJustificacionAsistencia(matricula=matricula,
                                                                     fechasolicitud=datetime.now(),
                                                                     casojustificacion_id=casojustificativo.id,
                                                                     justificativo=form.cleaned_data['justificativo'],
                                                                     estadosolicitud=variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA'),
                                                                     archivo=newfile,
                                                                     fechainicioreposo=form.cleaned_data['fechainicioreposo'],
                                                                     fechafinreposo=form.cleaned_data['fechafinreposo'],
                                                                     numerodiasreposo=form.cleaned_data['numerodiasreposo'],
                                                                     diagnostico=form.cleaned_data['diagnostico'],
                                                                     nombredoctor=form.cleaned_data['nombredoctor'],
                                                                     codigoafiliacionmsp=form.cleaned_data['codigoafiliacionmsp'],
                                                                     extendida=extendida
                                                                     )
                        solicitud.save(request)
                        fecha_inicio_justificacion = datetime.now().date()
                        for asig in asignatura_horario:
                            materiaasignada = MateriaAsignada.objects.get(pk=int(asig['idasig']))
                            asistencialeccion = AsistenciaLeccion.objects.get(pk=int(asig['idlecc']))
                            registradomateria = MateriaJustificacionAsistencia.objects.filter(solicitudjustificacion=solicitud, materiaasignada=materiaasignada)
                            if registradomateria.exists():
                                materia = registradomateria[0]
                            else:
                                materia = MateriaJustificacionAsistencia(solicitudjustificacion=solicitud, materiaasignada=materiaasignada)
                                materia.save(request)
                                log(u'Adiciono una materia asignada en materia justificacion asistencia: %s - [%s]' % (materia, materia.id), request, "add")
                            detalle = DetalleMateriaJustificacionAsistencia(materiajustificacion=materia, asistencialeccion=asistencialeccion)
                            detalle.save(request)
                            log(u'Adiciono horario en detalle de materia de justificacion: materia %s[%s] - horario %s[%s] - solicitud justificacion asistencia - %s[%s]' %
                                (materiaasignada.materia.nombre_completo(), materiaasignada.id, asistencialeccion.leccion.fecha, asistencialeccion.id, solicitud.casojustificacion, solicitud.id), request, "add")
                            # PROCESO PARA SACAR EL DIA DE INICIO DE JUSTIFICACION DE FALTA
                            if fecha_inicio_justificacion > asistencialeccion.leccion.fecha:
                                fecha_inicio_justificacion = asistencialeccion.leccion.fecha
                        solicitud.fechainiciojustificacion = fecha_inicio_justificacion
                        solicitud.save(request)
                        detalle = DetalleSolicitudJustificacionAsistencia(solicitud=solicitud,
                                                                          fechaaprobacion=datetime.now(),
                                                                          observacion="Solicito Justificación de Asistencia",
                                                                          aprueba_id=persona.id,
                                                                          estado=1)
                        detalle.save(request)
                        detalle.mail_notificar_justificacion_asistencia(request.session['nombresistema'])
                        # aprobación de solicitud automática
                        habilita_aprobacion_automatica = variable_valor('HABILITA_APROBACION_AUTOMATICA')
                        if habilita_aprobacion_automatica:
                            aprueba_solicitud_justificacion(request, solicitud)

                        log(u'Adiciono una solicitud de justificacion de asistencia: %s - [%s]' % (solicitud, solicitud.id), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": mensaje_error})

            elif action == 'numero_dias_laborales':
                try:
                    fecha_inicio = datetime.strptime(request.POST['finicio'], '%d-%m-%Y')
                    fecha_fin = datetime.strptime(request.POST['ffin'], '%d-%m-%Y')
                    if fecha_fin > fecha_inicio:
                        numerodias = contar_dias_sin_finsemana(fecha_inicio, fecha_fin, periodo)
                        data = {"result": "ok", "numerodias": (numerodias-1)}
                        return JsonResponse(data)
                    else:
                        return JsonResponse({'result': 'bad', "mensaje": u"Fechas ingresadas incorrectamente."})
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al contar dias laborales."})

            elif action == 'edit':
                try:
                    form = SolicitudJustificacionAsistenciaForm(request.POST, request.FILES)
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        extencion = newfile._name.split('.')
                        exte = extencion[1]
                        if newfile.size > 50485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                        if not exte == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                        newfile._name = generar_nombre("evidencia_", newfile._name)

                    if form.is_valid():
                        solicitud = SolicitudJustificacionAsistencia.objects.get(pk=int(request.POST['id']))
                        asignatura_horario = json.loads(request.POST['lista_items1'])
                        if not solicitud.extendida:
                            if not asignatura_horario:
                                return JsonResponse({"result": "bad", "mensaje": u"Debe contener al menos un registro de asignatura y horario para su justificación"})

                        casojustificativo = form.cleaned_data['casojustificacion']
                        # if casojustificativo:
                        #     if request.POST['numdiassolicitud']:
                        #         if int(request.POST['numdiassolicitud']) > 5:
                        #             return JsonResponse({"result": "bad", "mensaje": u"Imposible modificar solicitud: Según instructivo de justificación de faltas en Art. 6"})
                        if casojustificativo.id == 8 or casojustificativo.id == 9:
                            if request.POST['numerodiasreposo']:
                                if int(request.POST['numerodiasreposo']) < 30:
                                    return JsonResponse({"result": "bad", "mensaje": u"Imposible modificar solicitud: El caso seleccionado no cumple con el criterio de dias de reposo (más de 30 dias)."})

                        solicitud.casojustificacion = form.cleaned_data['casojustificacion']
                        solicitud.justificativo = form.cleaned_data['justificativo']
                        solicitud.estadosolicitud = 1
                        solicitud.fechainicioreposo = form.cleaned_data['fechainicioreposo']
                        solicitud.fechafinreposo = form.cleaned_data['fechafinreposo']
                        solicitud.numerodiasreposo = form.cleaned_data['numerodiasreposo']
                        solicitud.diagnostico = form.cleaned_data['diagnostico']
                        solicitud.nombredoctor = form.cleaned_data['nombredoctor']
                        solicitud.codigoafiliacionmsp = form.cleaned_data['codigoafiliacionmsp']

                        solicitud.save(request)
                        if newfile:
                            solicitud.archivo = newfile
                            solicitud.save(request)
                        for asig in asignatura_horario:
                            materiaasignada = MateriaAsignada.objects.get(pk=int(asig['idasig']))
                            asistencialeccion = AsistenciaLeccion.objects.get(pk=int(asig['idlecc']))
                            registradomateria = solicitud.materiajustificacionasistencia_set.filter(materiaasignada=materiaasignada)
                            if registradomateria.exists():
                                registradomateria = registradomateria[0]
                            else:
                                registradomateria = MateriaJustificacionAsistencia(solicitudjustificacion=solicitud, materiaasignada=materiaasignada)
                                registradomateria.save(request)
                                log(u'Adiciono una materia asignada en materia justificación asistencia: %s - [%s]' % (registradomateria, registradomateria.id), request, "add")
                            if not registradomateria.detallemateriajustificacionasistencia_set.filter(asistencialeccion=asistencialeccion).exists():
                                detalle = DetalleMateriaJustificacionAsistencia(materiajustificacion=registradomateria, asistencialeccion=asistencialeccion)
                                detalle.save(request)
                                log(u'Adiciono horario en detalle de materia de justificación: materia %s[%s] - horario %s[%s] - solicitud justificacion asistencia - %s[%s]' %
                                    (materiaasignada.materia.nombre_completo(), materiaasignada.id, asistencialeccion.leccion.fecha, asistencialeccion.id, solicitud.casojustificacion, solicitud.id), request, "add")
                        matariajustificacion = solicitud.materiajustificacionasistencia_set.filter().exclude(materiaasignada_id__in=[int(asignatura['idasig']) for asignatura in asignatura_horario])
                        detalles = DetalleMateriaJustificacionAsistencia.objects.filter(materiajustificacion__solicitudjustificacion=solicitud).exclude(asistencialeccion_id__in=[int(x['idlecc']) for x in asignatura_horario])
                        for detalle in detalles:
                            log(u'Elimino un horario de justificación de asistencia: %s - [%s]' % (detalle, detalle.id), request, "del")
                        for materia in matariajustificacion:
                            log(u'Se elimina una materia de justificación de asistencia porque esta sin utilizar no tiene detalle: %s - [%s]' % (materia, materia.id), request, "del")
                        detalles.delete()
                        matariajustificacion.delete()
                        log(u'Edito una solicitud de justificación de asistencia: %s - [%s]' % (solicitud, solicitud.id), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'mensajeevidencia':
                try:
                    caso = CasosJustificacion.objects.get(pk=int(request.POST['id']))
                    data = {"result": "ok", "mensajeevidencia": caso.descripcion}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al eliminar los datos."})

            elif action == 'puedeadicionar':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=int(request.POST['id']))
                    puedeseguir = materiaasignada.cuanto_queda_justificar_asis(matricula) - int(request.POST['c'])
                    data = {"result": "ok", "puede": True if puedeseguir > 1 else False, "porciento": variable_valor('PORCENTAJE_JUSTIFICACION_ASISTENCIA')}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al eliminar los datos."})

            elif action == 'editcarga':
                try:
                    materias_horario = json.loads(request.POST['lista'])
                    lista = []
                    for matehor in materias_horario:
                        detalle = DetalleMateriaJustificacionAsistencia.objects.get(materiajustificacion__solicitudjustificacion__id=int(request.POST['id']), materiajustificacion__materiaasignada__id=int(matehor['idasig']), asistencialeccion_id=int(matehor['idlecc']))
                        horario = u'%s [%s a %s]' % (detalle.asistencialeccion.leccion.fecha, detalle.asistencialeccion.leccion.horaentrada.strftime("%H:%M"), detalle.asistencialeccion.leccion.horasalida.strftime("%H:%M"))
                        lista.append([detalle.materiajustificacion.materiaasignada_id, detalle.asistencialeccion_id, detalle.materiajustificacion.materiaasignada.materia.nombre_completo(), horario])
                    data = {"result": "ok", "results": lista}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al eliminar los datos."})

            elif action == 'horario_asignatura':
                try:
                    materia = matricula.materiaasignada_set.get(pk=int(request.POST['id']))
                    autorizacionjustificar = matricula.extraer_fechas_autorizacion_justificar()
                    if autorizacionjustificar:
                        lecciones = materia.asistencialeccion_set.filter(Q(asistio=False) & Q(status=True) & Q(leccion__fecha__in=autorizacionjustificar)).exclude(pk__in=materia.listaidleccion_detalle_aun_falta_justificar(matricula)).order_by('leccion__fecha', 'leccion__horaentrada')
                    else:
                        lecciones = materia.asistencialeccion_set.filter(Q(asistio=False) & Q(status=True) & (Q(leccion__fecha__lte=datetime.now().date()) & Q(leccion__fecha__gte=fecha_anterior_justificar()))).exclude(pk__in=materia.listaidleccion_detalle_aun_falta_justificar(matricula)).order_by('leccion__fecha', 'leccion__horaentrada')
                        # lecciones = materia.asistencialeccion_set.filter(Q(asistio=False) & (Q(leccion__fecha__lte=datetime.now().date()) & Q(leccion__fecha__gte=fecha_anterior_justificar()))).exclude(pk__in=[detalle.asistencialeccion.id for detalle in materia.detalle_aun_falta_justificar(matricula)]).order_by('leccion__fecha', 'leccion__horaentrada')
                    if lecciones:
                        data = {"result": "ok", "results": [{"id": leccion.id, "fechahora": (u'%s [%s a %s]' % (leccion.leccion.fecha.strftime('%d-%m-%Y'), leccion.leccion.horaentrada.strftime("%H:%M"), leccion.leccion.horasalida.strftime("%H:%M")))} for leccion in lecciones]}
                    else:
                        data = {"result": 'bad', "mensaje": u"No tiene asignaturas asignadas."}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al eliminar los datos."})

            elif action == 'del':
                try:
                    solicitud = SolicitudJustificacionAsistencia.objects.get(pk=int(request.POST['id']))
                    if not solicitud.estadosolicitud == variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA'):
                        return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, ya tiene aprobacion/rechazo."})
                    log(u'Elimino un Caso de Justificacion de Asistencia para el alumno : %s [%s]' % (solicitud, solicitud.id), request, "del")
                    solicitud.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'detalle':
                try:
                    data['solicitud'] = SolicitudJustificacionAsistencia.objects.get(pk=int(request.POST['id']))
                    data['solicitado'] = variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA')
                    data['aprobado'] = variable_valor('APROBADO_JUSTIFICACION_ASISTENCIA')
                    data['rechazado'] = variable_valor('RECHAZADO_JUSTIFICACION_ASISTENCIA')

                    if inscripcion.carrera.id == 7 or inscripcion.carrera.id == 138 or inscripcion.carrera.id == 134:
                        materias = matricula.materiaasignada_set.filter(status=True)
                    else:
                        materias = matricula.mis_materias_sin_ingles()
                    data['materias'] = materias
                    data['no_atendido'] = variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA_NO_ATENDIDA')
                    template = get_template("alu_solicitudjustificacionasistencia/detallesolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'detalleaprobar':
                try:
                    data = {}
                    solicitud = SolicitudJustificacionAsistencia.objects.get(pk=int(request.POST['id']))
                    data['solicitud'] = solicitud
                    data['detallesolicitud'] = solicitud.detallesolicitudjustificacionasistencia_set.all()
                    data['aprobador'] = persona
                    data['fecha'] = datetime.now()
                    data['solicitado'] = variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA')
                    data['aprobado'] = variable_valor('APROBADO_JUSTIFICACION_ASISTENCIA')
                    data['rechazado'] = variable_valor('RECHAZADO_JUSTIFICACION_ASISTENCIA')
                    data['no_atendido'] = variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA_NO_ATENDIDA')
                    data['puede_aprobar'] = False
                    data['es_alumno'] = True
                    template = get_template("adm_justificacionasistencia/detalle_aprobar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar justificación de asistencia'
                    form = SolicitudJustificacionAsistenciaForm()
                    form.deshabilitar_fecha()
                    data['form'] = form
                    data['matricula'] = matricula
                    autorizacionjustificar = matricula.extraer_fechas_autorizacion_justificar()
                    if autorizacionjustificar:
                        data['asignaturas'] = AsistenciaLeccion.objects.filter(Q(materiaasignada__in=matricula.materiaasignada_set.values_list('id').all()) & Q(asistio=False) & Q(status=True) & Q(leccion__fecha__in=autorizacionjustificar)).distinct('materiaasignada')
                    else:
                        data['asignaturas'] = AsistenciaLeccion.objects.filter(Q(materiaasignada__in=matricula.materiaasignada_set.values_list('id').all()) & Q(asistio=False) & Q(status=True) & (Q(leccion__fecha__lte=datetime.now().date()) & Q(leccion__fecha__gte=fecha_anterior_justificar()))).distinct('materiaasignada')
                    if inscripcion.carrera.id == 7 or inscripcion.carrera.id == 138 or inscripcion.carrera.id == 134:
                        materias = matricula.materiaasignada_set.filter(status=True)
                    else:
                        materias = matricula.mis_materias_sin_ingles()
                    data['materias'] = materias
                    data['dias_anterior'] = variable_valor('DIAS_ANTERIOR_JUSTIFICAR_ESTUDIANTE')
                    data['mensaje'] = "Según instructivo de justificación de faltas en Art. 6 indica: Las y los estudiantes deberán presentar las respectivas justificaciones en el término de (%s) días laborales, luego de ocurrido el suceso y lo podrá realizar de manera personal o intermedio persona." % variable_valor('DIAS_ANTERIOR_JUSTIFICAR_ESTUDIANTE')
                    data['mensaje2'] = "En caso de que el certificado no posea la codificación CIE10, no se procederá con la validación ya que el documento no cumple con lo establecido en la normativa legal vigente."
                    data['mensaje3'] = "En caso de no evidenciar el código de afiliación del médico al MSP, no se procederá con la validación del certificado."
                    data['mensaje4'] = "En caso de constatarse que el documento enviado carece de legalidad o que es falso, se procederá con el inicio de las investigaciones respectivas para aplicar las sanciones que correspondan conforme a la normativa legal vigente"
                    return render(request, "alu_solicitudjustificacionasistencia/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar justificación de asistencia'
                    data['solicitud'] = justificacion = SolicitudJustificacionAsistencia.objects.get(pk=int(request.GET['id']))

                    initial = model_to_dict(justificacion)
                    form = SolicitudJustificacionAsistenciaForm(initial=initial)
                    # form = SolicitudJustificacionAsistenciaForm(initial={'fecha': justificacion.fechasolicitud,
                    #                                                      'casojustificacion': justificacion.casojustificacion,
                    #                                                      'justificativo': justificacion.justificativo})
                    form.deshabilitar_fecha()
                    data['form'] = form
                    materias = matricula.materiaasignada_set.all()
                    data['materias_2'] = justificacion.materiajustificacionasistencia_set.filter(status=True)
                    data['asignaturas'] = AsistenciaLeccion.objects.filter(Q(materiaasignada__in=matricula.materiaasignada_set.all()) & Q(asistio=False) & Q(status=True) & (Q(leccion__fecha__lte=datetime.now().date()) & Q(leccion__fecha__gte=fecha_anterior_justificar()))).distinct('materiaasignada')
                    data['mensaje'] = "Según instructivo de justificación de faltas en Art. 6 indica: Las y los estudiantes deberán presentar las respectivas justificaciones en el término de (%s) días laborales, luego de ocurrido el suceso y lo podrá realizar de manera personal o intermedio persona." % variable_valor('DIAS_ANTERIOR_JUSTIFICAR_ESTUDIANTE')
                    data['mensaje2'] = "En caso de que el certificado no posea la codificación CIE10, no se procederá con la validación ya que el documento no cumple con lo establecido en la normativa legal vigente."
                    data['mensaje3'] = "En caso de no evidenciar el código de afiliación del médico al MSP, no se procederá con la validación del certificado."
                    data['mensaje4'] = "En caso de constatarse que el documento enviado carece de legalidad o que es falso, se procederá con el inicio de las investigaciones respectivas para aplicar las sanciones que correspondan conforme a la normativa legal vigente"
                    return render(request, "alu_solicitudjustificacionasistencia/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'del':
                try:
                    data['title'] = u'Eliminar solicitud de justificación'
                    data['solicitud'] = SolicitudJustificacionAsistencia.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_solicitudjustificacionasistencia/del.html", data)
                except Exception as ex:
                    pass
        else:
            data['title'] = u'Solicitud de justificación de asistencia'
            data['justificaciones'] = SolicitudJustificacionAsistencia.objects.filter(matricula=matricula).order_by('-fechasolicitud')
            data['solicitado'] = variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA')
            data['aprobado'] = variable_valor('APROBADO_JUSTIFICACION_ASISTENCIA')
            data['no_atendido'] = variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA_NO_ATENDIDA')
            return render(request, "alu_solicitudjustificacionasistencia/view.html", data)


def fecha_anterior_justificar():
    fecha = datetime.now().date()
    aumento = 1
    while aumento <= variable_valor('DIAS_ANTERIOR_JUSTIFICAR_ESTUDIANTE'):
        if datetime.isoweekday(fecha) == 6:
            dias = timedelta(days=-1)
        elif datetime.isoweekday(fecha) == 7:
            dias = timedelta(days=-2)
        elif datetime.isoweekday(fecha) == 1:
            dias = timedelta(days=-3)
        else:
            dias = timedelta(days=-1)
        fecha = fecha + dias
        aumento += 1
    return fecha

def contar_dias_sin_finsemana(fechainicio, fechafin, periodo):
    contador = 0
    fechaini = fechainicio
    while fechaini <= fechafin:
        if fechaini.weekday() == 5:
            dias = timedelta(days=3)
        else:
            dias = timedelta(days=1)
        fechaini = fechaini + dias
        if not DiasNoLaborable.objects.values('id').filter(fecha=fechaini, periodo=periodo, activo=True).exclude(motivo__in=[2, 3]).exists():
            contador += 1
    return contador

def aprueba_solicitud_justificacion(request, solicitud):
    try:
        solicitud.estadosolicitud = variable_valor('APROBADO_JUSTIFICACION_ASISTENCIA')
        solicitud.save(request)
        detallesolicitud = DetalleSolicitudJustificacionAsistencia(solicitud=solicitud,
                                                                   fechaaprobacion=datetime.now(),
                                                                   observacion='Validado por el Sistema de Gestión Académica',
                                                                   aprueba_id=1,
                                                                   estado=2)
        detallesolicitud.save(request)
        log(u'Aprobar solicitud de justificacion de asistencia(Director): %s - %s [%s]' % (
        detallesolicitud.aprueba, detallesolicitud.get_estado_display(), detallesolicitud.id), request, "add")
        if not solicitud.extendida:
            # JUSTIFICAR ASISTENCIAS
            justificar_asistencias(request, solicitud)
        else:
            #SE CREA REGISTRO DE MATERIA Y ASISTENCIA A JUSTIFICAR POR CADA FALTA ENCONTRADA EN LAS MATERIAS
            if solicitud.matricula.inscripcion.carrera.id == 7 or solicitud.matricula.inscripcion.carrera.id == 138 or solicitud.matricula.inscripcion.carrera.id == 134:
                materias = solicitud.matricula.materiaasignada_set.filter(status=True)
            else:
                materias = solicitud.matricula.mis_materias_sin_ingles()
            for materiaasignada in materias:
                cantidadjustificar = materiaasignada.cuanto_queda_justificar_asis(solicitud.matricula)

                #VALIDACIÓN DE JUSTIFICAR POR FECHAS AUTORIZADAS O LOS 5 DIAS HABILES (VARIABLE GLOBAL)
                autorizacionjustificar = solicitud.matricula.extraer_fechas_autorizacion_justificar()
                if autorizacionjustificar:
                    listaasistencialeccion = materiaasignada.asistencialeccion_set.filter(Q(asistio=False) & Q(status=True) &
                        Q(leccion__fecha__in=autorizacionjustificar)).exclude(pk__in=materiaasignada.listaidleccion_detalle_aun_falta_justificar(
                            solicitud.matricula)).order_by('leccion__fecha', 'leccion__horaentrada')[:cantidadjustificar]
                else:
                    fechainiciojus = fecha_anterior_justificar() if fecha_anterior_justificar() >= solicitud.fechainicioreposo else solicitud.fechainicioreposo
                    fechafinjus = solicitud.fechafinreposo if solicitud.fechafinreposo <= datetime.now().date() else datetime.now().date()
                    listaasistencialeccion = materiaasignada.asistencialeccion_set.filter(Q(asistio=False) & Q(status=True) &
                        (Q(leccion__fecha__lte=fechafinjus) & Q(leccion__fecha__gte=fechainiciojus))).exclude(
                        pk__in=materiaasignada.listaidleccion_detalle_aun_falta_justificar(solicitud.matricula)).order_by(
                        'leccion__fecha', 'leccion__horaentrada')[:cantidadjustificar]

                # Faltas con fechas de inicio y fin de reposo (para prueba)
                # listaasistencialeccion = materiaasignada.asistencialeccion_set.filter(
                #     Q(asistio=False) & (Q(leccion__fecha__gte=solicitud.fechainicioreposo) & Q(leccion__fecha__lte=solicitud.fechafinreposo))).exclude(
                #     pk__in=materiaasignada.listaidleccion_detalle_aun_falta_justificar(solicitud.matricula)).order_by(
                #     'leccion__fecha', 'leccion__horaentrada')[:cantidadjustificar]

                if listaasistencialeccion:
                    registradomateria = MateriaJustificacionAsistencia.objects.filter(solicitudjustificacion=solicitud, materiaasignada=materiaasignada)
                    if registradomateria.exists():
                        materia = registradomateria[0]
                    else:
                        materia = MateriaJustificacionAsistencia(solicitudjustificacion=solicitud, materiaasignada=materiaasignada)
                        materia.save(request)
                        log(u'Adiciono una materia asignada en materia justificacion asistencia: %s - [%s]' % (
                        materia, materia.id), request, "add")
                    for asistencialeccion in listaasistencialeccion:
                        detalle = DetalleMateriaJustificacionAsistencia(materiajustificacion=materia,
                                                                        asistencialeccion=asistencialeccion)
                        detalle.save(request)
                        log(u'Adiciono horario en detalle de materia de justificacion: materia %s[%s] - horario %s[%s] - solicitud justificacion asistencia - %s[%s]' %
                            (materiaasignada.materia.nombre_completo(), materiaasignada.id,
                             asistencialeccion.leccion.fecha, asistencialeccion.id, solicitud.casojustificacion,
                             solicitud.id), request, "add")
            # JUSTIFICAR ASISTENCIAS
            justificar_asistencias(request, solicitud, materias)
    except Exception as ex:
        transaction.set_rollback(True)
        raise NameError('Error al generar la solicitud')

def justificar_asistencias(request, solicitud, materias=None):
    try:
        detallesmateriajustificacion = DetalleMateriaJustificacionAsistencia.objects.filter(materiajustificacion__solicitudjustificacion=solicitud).order_by('materiajustificacion')
        if detallesmateriajustificacion:
            for materiajustificacion in solicitud.justificacion_materias():
                justifico_materia = False
                for detalle_materia in materiajustificacion.detalle_materia():
                    justifico_hora = False
                    if detalle_materia in detallesmateriajustificacion:
                        asistencialeccion = detalle_materia.asistencialeccion
                        asistencialeccion.asistenciajustificada = True
                        asistencialeccion.asistio = True
                        asistencialeccion.save(request)
                        justifico_hora = True
                        justifico_materia = True
                    detalle = JustificacionAsistencia(detallemateriajustificacion=detalle_materia,
                                                      fechaajustificacion=datetime.now(),
                                                      estadojustificado=justifico_hora)
                    detalle.save(request)
                    log(u'Justifico asistencia: id_solicitud[%s] id_justificacionasistencia[%s] - materia: [%s] - horario: [%s] - estadojustificado:[%s]' % (
                        solicitud.id, detalle.id, materiajustificacion.materiaasignada.materia.asignatura,
                        detalle_materia.__str__(), justifico_hora), request, "add")
                if justifico_materia:
                    materiajustificacion.materiaasignada.save(actualiza=True)
            solicitud.mail_notificar_justificacion_asistencia(request.session['nombresistema'])

        # ENVIO DE CORREO A DOCENTES DE MATERIAS EN SOLICITUD
        titulo = 'faltas'
        if solicitud.casojustificacion.id == 10:
            titulo = 'actividadess'
        artsexoest = 'La'
        if solicitud.matricula.inscripcion.persona.sexo.id == 2:
            artsexoest = 'El'

        if solicitud.extendida and materias:
            listamaterias = materias
            for mat in listamaterias:
                artdocente = 'Estimada'
                if mat.materia.profesor_principal():
                    if mat.materia.profesor_principal().persona.sexo.id == 2:
                        artdocente = 'Estimado'
                    correoinstitucional = mat.materia.profesor_principal().persona.lista_emails_interno()
                    send_html_mail("Solicitud de Justificación de %s : %s" % (
                        titulo, solicitud.matricula.inscripcion.persona.nombre_completo_inverso()),
                                   "emails/notificacion_docente_materia_justificacion_asistencia_extendida.html",
                                   {'sistema': request.session['nombresistema'],
                                    'materia': mat,
                                    'solicitud': solicitud,
                                    'artdocente': artdocente,
                                    'artsexoest': artsexoest,
                                    'tipo': 'Solicitud',
                                    'titulo': titulo,
                                    't': miinstitucion()},
                                   correoinstitucional, [], cuenta=CUENTAS_CORREOS[1][1])
        else:
            listamaterias = MateriaJustificacionAsistencia.objects.filter(solicitudjustificacion=solicitud)
            for materia in listamaterias:
                artdocente = 'Estimada'
                if materia.materiaasignada.materia.profesor_principal().persona.sexo.id == 2:
                    artdocente = 'Estimado'
                correoinstitucional = materia.materiaasignada.materia.profesor_principal().persona.lista_emails_interno()
                send_html_mail("Solicitud de Justificación de %s : %s" % (
                    titulo, solicitud.matricula.inscripcion.persona.nombre_completo_inverso()),
                               "emails/notificacion_docente_materia_justificacion_asistencia.html",
                               {'sistema': request.session['nombresistema'],
                                'materia': materia,
                                'solicitud': solicitud,
                                'artdocente': artdocente,
                                'artsexoest': artsexoest,
                                'tipo': 'Solicitud',
                                'titulo': titulo,
                                't': miinstitucion()},
                               correoinstitucional, [], cuenta=CUENTAS_CORREOS[1][1])
    except Exception as ex:
        transaction.set_rollback(True)
        raise NameError('Error al generar la solicitud')