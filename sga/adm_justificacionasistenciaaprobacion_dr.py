# -*- coding: latin-1 -*-
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import SolicitudJustificacionAsistenciaBienestarForm, CorregirSolicitudForm
from sga.funciones import variable_valor, log, MiPaginador, convertir_fecha, generar_nombre
from django.db.models import Q
from datetime import datetime, timedelta
from django.template.context import Context
from django.template.loader import get_template
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.tasks import send_html_mail
from sga.models import SolicitudJustificacionAsistencia, DetalleSolicitudJustificacionAsistencia, \
    MateriaJustificacionAsistencia, JustificacionAsistencia, ESTADO_SOLICITUD_JUSTIFICACION_ASISTENCIA, Coordinacion, \
    DetalleMateriaJustificacionAsistencia, Matricula, CasosJustificacion, MateriaAsignada, AsistenciaLeccion, CUENTAS_CORREOS, miinstitucion, Notificacion
from sga.templatetags.sga_extras import encrypt
from django.contrib.contenttypes.models import ContentType


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addaprobacion':
            mensaje = u"Llene todos los campos"
            try:
                # APROBAR ASISTENCIAS
                solicitud = SolicitudJustificacionAsistencia.objects.get(pk=int(request.POST['id']))
                solicitud.estadosolicitud = variable_valor('APROBADO_JUSTIFICACION_ASISTENCIA') if int(request.POST['estado']) == variable_valor('APROBADO_JUSTIFICACION_ASISTENCIA') else variable_valor('RECHAZADO_JUSTIFICACION_ASISTENCIA')
                solicitud.save(request)
                detallesolicitud = DetalleSolicitudJustificacionAsistencia(solicitud=solicitud,
                                              fechaaprobacion=datetime.now(),
                                              observacion=request.POST['observacion'],
                                              aprueba=persona,
                                              estado=2 if int(request.POST['estado']) == variable_valor('APROBADO_JUSTIFICACION_ASISTENCIA') else 3)
                detallesolicitud.save(request)
                log(u'Aprobar solicitud de justificacion de asistencia(Director): %s - %s [%s]' % (detallesolicitud.aprueba, detallesolicitud.get_estado_display(), detallesolicitud.id), request, "add")
                #JUSTIFICAR ASISTENCIAS
                if int(request.POST['estado']) == variable_valor('APROBADO_JUSTIFICACION_ASISTENCIA'):
                    datos = json.loads(request.POST['lista_items1'])
                    if datos:
                        detallesmateriajustificacion = DetalleMateriaJustificacionAsistencia.objects.filter(materiajustificacion__solicitudjustificacion = solicitud, id__in=[iddetalle['idmas'] for iddetalle in datos]).order_by('materiajustificacion')
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
                                detalle = JustificacionAsistencia(detallemateriajustificacion=detalle_materia, fechaajustificacion=datetime.now(), estadojustificado=justifico_hora)
                                detalle.save(request)
                                log(u'Justifico asistencia: id_solicitud[%s] id_justificacionasistencia[%s] - materia: [%s] - horario: [%s] - estadojustificado:[%s]' % (solicitud.id, detalle.id, materiajustificacion.materiaasignada.materia.asignatura, detalle_materia.__str__(), justifico_hora), request, "add")
                            if justifico_materia:
                                materiajustificacion.materiaasignada.save(actualiza=True)
                        solicitud.mail_notificar_justificacion_asistencia(request.session['nombresistema'])

                        # ENVIO DE CORREO A DOCENTES DE MATERIAS EN SOLICITUD
                        listamaterias = MateriaJustificacionAsistencia.objects.filter(solicitudjustificacion=solicitud)
                        titulo = 'faltas'
                        if solicitud.casojustificacion.id == 10:
                            titulo = 'actividadess'
                        artsexoest = 'La'
                        if solicitud.matricula.inscripcion.persona.sexo.id == 2:
                            artsexoest = 'El'
                        for materia in listamaterias:
                            artdocente = 'Estimada'
                            if materia.materiaasignada.materia.profesor_principal().persona.sexo.id == 2:
                                artdocente = 'Estimado'
                            # correos = materia.materiaasignada.materia.profesor_principal().persona.lista_emails_envio()
                            correoinstitucional = materia.materiaasignada.materia.profesor_principal().persona.lista_emails_interno()
                            # correoinstitucional = ['jnavarretej@unemi.edu.ec', ]
                            send_html_mail("Solicitud de Justificación de %s : %s" % (titulo, solicitud.matricula.inscripcion.persona.nombre_completo_inverso()),
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

                    else:
                        if solicitud.extendida:
                            # ENVIO DE CORREO A DOCENTES DE MATERIAS EN SOLICITUD
                            if solicitud.matricula.inscripcion.carrera.id == 7 or solicitud.matricula.inscripcion.carrera.id == 138 or solicitud.matricula.inscripcion.carrera.id == 134:
                                listamaterias = solicitud.matricula.materiaasignada_set.filter(status=True)
                            else:
                                listamaterias = solicitud.matricula.mis_materias_sin_ingles()
                            titulo = 'faltas'
                            if solicitud.casojustificacion.id == 10:
                                titulo = 'actividadess'
                            artsexoest = 'La'
                            if solicitud.matricula.inscripcion.persona.sexo.id == 2:
                                artsexoest = 'El'
                            for mat in listamaterias:
                                artdocente = 'Estimada'
                            if mat.materia.profesor_principal():
                                if mat.materia.profesor_principal().persona.sexo.id == 2:
                                    artdocente = 'Estimado'
                                # correos = materia.materiaasignada.materia.profesor_principal().persona.lista_emails_envio()
                                correoinstitucional = mat.materia.profesor_principal().persona.lista_emails_interno()
                                #correoinstitucional = ['rviterib1@unemi.edu.ec', ]
                                send_html_mail("Solicitud de Justificación de %s : %s" % (titulo, solicitud.matricula.inscripcion.persona.nombre_completo_inverso()),
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
                            mensaje = u"Seleccione al menos un horario a justificar"
                            raise NameError('Error')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": mensaje})

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
                data['puede_aprobar'] = True
                data['es_alumno'] = False
                template = get_template("adm_justificacionasistencia/detalle_aprobar.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content, 'titulo':"Aprobación de la solicitud"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'corregirsolicitud':
            try:
                with transaction.atomic():
                    persona = request.session['persona']
                    solicitud = SolicitudJustificacionAsistencia.objects.get(pk=int(request.POST['id']))
                    f = CorregirSolicitudForm(request.POST, request.FILES)
                    if f.is_valid():
                        solicitud.estadosolicitud = 5
                        solicitud.observacion = f.cleaned_data['observaciones']
                        solicitud.save(request)

                        notificacion = Notificacion(titulo='Se envió a corregir su solicitud de justificación de falta sobre el caso %s' % solicitud.casojustificacion,
                                                    cuerpo='Realice las siguiente correciones: %s' % f.cleaned_data['observaciones'],
                                                    destinatario=solicitud.matricula.inscripcion.persona,
                                                    url=f"/alu_justificacion_asis",
                                                    content_type=ContentType.objects.get_for_model(solicitud),
                                                    object_id=solicitud.pk,
                                                    prioridad=2,
                                                    fecha_hora_visible=datetime.now() + timedelta(days=30),
                                                    app_label='sga',
                                                    )
                        notificacion.save(request)
                        log(u'Envió a corregir la solicitud: %s' % persona, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'aprobarjustificar':
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
                data['materias'] = MateriaJustificacionAsistencia.objects.filter(solicitudjustificacion_id=int(request.POST['id']))
                template = get_template("adm_justificacionasistencia/aprobarjustificar.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content, 'titulo':"Aprobar solicitud"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'aprobarjustificacioncorregida':
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
                if solicitud.matricula.inscripcion.carrera.id == 7 or solicitud.matricula.inscripcion.carrera.id == 138 or solicitud.matricula.inscripcion.carrera.id == 134:
                    materias = solicitud.matricula.materiaasignada_set.filter(status=True)
                else:
                    materias = solicitud.matricula.mis_materias_sin_ingles()
                data['materias2'] = materias
                data['no_atendido'] = variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA_NO_ATENDIDA')
                data['materias'] = MateriaJustificacionAsistencia.objects.filter(solicitudjustificacion_id=int(request.POST['id']))
                template = get_template("adm_justificacionasistencia/aprobarsolicitudjustificacion.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content, 'titulo':"Aprobar solicitud"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'editdetalleaprobar':
            try:
                data = {}
                solicitud = SolicitudJustificacionAsistencia.objects.get(pk=int(request.POST['id']))
                data['solicitud'] = solicitud
                data['detallesolicitud'] = solicitud.detallesolicitudjustificacionasistencia_set.all().exclude(pk=solicitud.fecha_aprobacion().id)
                data['aprobador'] = persona
                data['fecha'] = datetime.now()
                data['solicitado'] = variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA')
                data['aprobado'] = variable_valor('APROBADO_JUSTIFICACION_ASISTENCIA')
                data['rechazado'] = variable_valor('RECHAZADO_JUSTIFICACION_ASISTENCIA')
                data['no_atendido'] = variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA_NO_ATENDIDA')
                template = get_template("adm_justificacionasistencia/editdetalle_aprobar.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content, 'titulo':"Editar aprobación de la solicitud"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'editaprobacion':
            try:
                detalle = DetalleSolicitudJustificacionAsistencia.objects.get(pk=int(request.POST['id']))
                detalle.fechaaprobacion = datetime.now()
                detalle.observacion = request.POST['observacion']
                detalle.aprueba = persona
                detalle.estado = 2 if int(request.POST['estado']) == variable_valor('APROBADO_JUSTIFICACION_ASISTENCIA') else 3
                detalle.save(request)
                solicitud = detalle.solicitud
                solicitud.estadosolicitud = variable_valor('APROBADO_JUSTIFICACION_ASISTENCIA') if int(request.POST['estado']) == variable_valor('APROBADO_JUSTIFICACION_ASISTENCIA') else variable_valor('RECHAZADO_JUSTIFICACION_ASISTENCIA')
                solicitud.save(request)
                log(u'Edito cambio de estado a una solicitud de justificacion de asistencia: %s - %s [%s]' % (detalle.aprueba,detalle.get_estado_display(), detalle.id), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Llene todos los campos"})

        elif action == 'detallesolicitud':
            try:
                data['solicitud'] = soli = SolicitudJustificacionAsistencia.objects.get(pk=int(request.POST['id']))
                data['solicitado'] = variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA')
                data['aprobado'] = variable_valor('APROBADO_JUSTIFICACION_ASISTENCIA')
                data['rechazado'] = variable_valor('RECHAZADO_JUSTIFICACION_ASISTENCIA')
                if soli.matricula.inscripcion.carrera.id == 7 or soli.matricula.inscripcion.carrera.id == 138 or soli.matricula.inscripcion.carrera.id == 134:
                    materias = soli.matricula.materiaasignada_set.filter(status=True)
                else:
                    materias = soli.matricula.mis_materias_sin_ingles()
                data['materias'] = materias
                data['no_atendido'] = variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA_NO_ATENDIDA')
                template = get_template("alu_solicitudjustificacionasistencia/detallesolicitud.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'reporte_pdf':
            try:
                data['fechainicio'] = fechainicio = datetime.strptime(request.POST['ini'],'%d-%m-%Y').date()
                data['fechafin'] = fechafin = datetime.strptime(request.POST['fin'], '%d-%m-%Y').date()
                data['periodo'] = periodo
                data['aprobado'] = variable_valor('APROBADO_JUSTIFICACION_ASISTENCIA')
                data['reprobado'] = variable_valor('RECHAZADO_JUSTIFICACION_ASISTENCIA')
                data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=int(request.POST['c']), excluir=False)
                data['solicitudes'] = SolicitudJustificacionAsistencia.objects.filter(fechasolicitud__range=(fechainicio, fechafin),
                                                                                      matricula__inscripcion__coordinacion=coordinacion,
                                                                                      matricula__nivel__periodo=periodo,
                                                                                      estadosolicitud__in=[variable_valor('APROBADO_JUSTIFICACION_ASISTENCIA'), variable_valor('RECHAZADO_JUSTIFICACION_ASISTENCIA')]).\
                                                                                      distinct().order_by('-fechasolicitud','matricula__inscripcion__persona__apellido2','matricula__inscripcion__persona__apellido1','matricula__inscripcion__persona__nombres')
                return conviert_html_to_pdf('adm_justificacionasistencia/reporte_justificacion_pdf.html',{'pagesize': 'A4', 'data': data})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        elif action == 'actualizarjustificacion':
            try:
                justificacion = JustificacionAsistencia.objects.all().exclude(materiajustificacion=None)
                lista_id_solicitudes = justificacion.distinct('materiajustificacion__solicitudjustificacion__id').order_by('materiajustificacion__solicitudjustificacion__id')
                contador_horario=0
                contador_asignatura = 0
                for solicitud in SolicitudJustificacionAsistencia.objects.filter(pk__in=lista_id_solicitudes.values_list('materiajustificacion__solicitudjustificacion__id')):
                    for materiajustificacion in solicitud.justificacion_materias():
                        for detalle_materia in materiajustificacion.detalle_materia():
                            fechajustificacion = JustificacionAsistencia.objects.get(materiajustificacion = materiajustificacion).fechaajustificacion
                            detalle = JustificacionAsistencia(detallemateriajustificacion=detalle_materia, fechaajustificacion=fechajustificacion, estadojustificado=True)
                            detalle.save(request)
                            contador_horario += 1
                        contador_asignatura += 1
                justificacion.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos."})

        elif action == 'extraerasignaturashorarios':
            try:
                fechai = convertir_fecha(request.POST['fi'])
                fechaf = convertir_fecha(request.POST['ff'])
                idmatricula = int(request.POST['mat'])
                listalecciones = []
                if fechai < fechaf:
                    matricula = Matricula.objects.get(pk=idmatricula)
                    materiasasignadas = matricula.materiaasignada_set.filter(asistencialeccion__asistio=False, asistencialeccion__leccion__fecha__range=(fechai, fechaf), status=True).distinct().order_by('materia')
                    for materiaasignada in materiasasignadas:
                        cantidadjustificar = materiaasignada.cuanto_queda_justificar_asis(matricula)
                        if cantidadjustificar > 0:
                            for leccion in materiaasignada.asistencialeccion_set.filter(Q(asistio=False) & (Q(leccion__fecha__lte=fechaf) & Q(leccion__fecha__gte=fechai))).exclude(pk__in=materiaasignada.listaidleccion_detalle_aun_falta_justificar(matricula)).order_by('leccion__fecha', 'leccion__horaentrada')[:cantidadjustificar]:
                                listalecciones.append([materiaasignada.id, materiaasignada.materia.nombre_mostrar_solo(), leccion.id,  (u'%s [%s a %s]' % (leccion.leccion.fecha.strftime('%d-%m-%Y'), leccion.leccion.clase.turno.comienza.strftime("%H:%M"),leccion.leccion.clase.turno.termina.strftime("%H:%M")))])
                if listalecciones:
                    data = {"result": "ok", "lista": listalecciones}
                else:
                    data = {"result": 'bad', "mensaje": u"No tiene horario para justificar en las inidicación de fechas."}
                return JsonResponse(data)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos."})

        elif action == 'mensajeevidencia':
            try:
                caso = CasosJustificacion.objects.get(pk=int(request.POST['id']))
                data = {"result": "ok", "mensajeevidencia": caso.descripcion if caso.descripcion else ""}
                return JsonResponse(data)
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al eliminar los datos."})

        elif action == 'addsolicitud':
            mensaje_error = u"Error al guardar los datos."
            try:
                form = SolicitudJustificacionAsistenciaBienestarForm(request.POST, request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    extencion = newfile._name.split('.')
                    exte = extencion[1]
                    if newfile.size > 12582912:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                    if not exte == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                    newfile._name = generar_nombre("evidencia_", newfile._name)

                if form.is_valid():
                    if not newfile:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe subir un archivo de evidencia"})
                    if not form.cleaned_data['matricula']>0:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar un estudiante matriculado"})
                    asignatura_horario = json.loads(request.POST['lista_items1'])
                    matricula = Matricula.objects.get(pk=form.cleaned_data['matricula'])
                    solicitud = SolicitudJustificacionAsistencia(matricula=matricula,
                                                                 fechasolicitud=datetime.now(),
                                                                 fechainicio=form.cleaned_data['fechainicio'],
                                                                 fechafin=form.cleaned_data['fechafin'],
                                                                 casojustificacion=form.cleaned_data[ 'casojustificacion'],
                                                                 justificativo=form.cleaned_data['justificativo'],
                                                                 estadosolicitud=variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA'),
                                                                 archivo=newfile)
                    solicitud.save(request)
                    fecha_inicio_justificacion = datetime.now().date()
                    for asig in asignatura_horario:
                        materiaasignada = MateriaAsignada.objects.get(pk=int(asig['idasig']))
                        asistencialeccion = AsistenciaLeccion.objects.get(pk=int(asig['idlecc']))
                        registradomateria = MateriaJustificacionAsistencia.objects.filter(solicitudjustificacion=solicitud, materiaasignada=materiaasignada)
                        if registradomateria.exists():
                            materia = registradomateria[0]
                        else:
                            materia = MateriaJustificacionAsistencia(solicitudjustificacion=solicitud,materiaasignada=materiaasignada)
                            materia.save(request)
                            log(u'Adiciono una materia asignada en materia justificacion asistencia: %s - [%s]' % (
                            materia, materia.id), request, "add")
                        detalle = DetalleMateriaJustificacionAsistencia(materiajustificacion=materia,asistencialeccion=asistencialeccion)
                        detalle.save(request)
                        log(u'Adiciono horario en detalle de materia de justificacion: materia %s[%s] - horario %s[%s] - solicitud justificacion asistencia - %s[%s]' % (materiaasignada.materia.nombre_completo(), materiaasignada.id,asistencialeccion.leccion.fecha, asistencialeccion.id, solicitud.casojustificacion,solicitud.id), request, "add")
                        # PROCESO PARA SACAR EL DIA DE INICIO DE JUSTIFICACION DE FALTA
                        if fecha_inicio_justificacion > asistencialeccion.leccion.fecha:
                            fecha_inicio_justificacion = asistencialeccion.leccion.fecha
                    solicitud.fechainiciojustificacion = fecha_inicio_justificacion
                    solicitud.save(request)
                    detalle = DetalleSolicitudJustificacionAsistencia(solicitud=solicitud,
                                                                      fechaaprobacion=datetime.now(),
                                                                      observacion="Solicito Justificación de Asistencia",
                                                                      aprueba=persona,
                                                                      estado=1)
                    detalle.save(request)
                    detalle.mail_notificar_justificacion_asistencia(request.session['nombresistema'])
                    log(u'Adiciono una solicitud de justificacion de asistencia: %s - [%s]' % (solicitud, solicitud.id),request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": mensaje_error})

        elif action == 'delsolicitud':
            try:
                solicitud = SolicitudJustificacionAsistencia.objects.get(pk=int(encrypt(request.POST['id'])))
                if not solicitud.estadosolicitud == variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA'):
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, ya tiene aprobacion/rechazo."})
                log(u'Elimino un Caso de Justificacion de Asistencia para el alumno : %s [%s]' % (solicitud, solicitud.id), request, "del")
                solicitud.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            # SOLICITAR JUSTIFICACION DE ASISTENCIA
            if action == 'addsolicitud':
                try:
                    data['title'] = u'Adicionar justificación de asistencia'
                    data['form'] = SolicitudJustificacionAsistenciaBienestarForm()
                    return render(request, "alu_solicitudjustificacionasistencia/addsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscarmatriculados':
                try:
                    q = request.GET['q'].upper().strip()
                    if ' ' in q:
                        s = q.split(" ")
                        if len(s) == 2:
                            matriculas = Matricula.objects.filter(Q(nivel__periodo=periodo) & (Q(inscripcion__persona__apellido1__contains=s[0]) & Q(inscripcion__persona__apellido2__contains=s[1])) | (Q(inscripcion__persona__nombres__contains=s[0]) & Q(inscripcion__persona__nombres__contains=s[1]))).exclude(inscripcion__coordinacion__excluir=True, inscripcion__coordinacion__id=7).distinct()[:25]
                        if len(s) == 3:
                            matriculas = Matricula.objects.filter(Q(nivel__periodo=periodo) & Q(inscripcion__persona__apellido1__contains=s[0]) & Q(inscripcion__persona__apellido2__contains=s[1]) & Q(inscripcion__persona__nombres__contains=s[2])).exclude(inscripcion__coordinacion__excluir=True, inscripcion__coordinacion__id=7).distinct()[:25]
                        if len(s) == 4:
                            matriculas = Matricula.objects.filter(Q(nivel__periodo=periodo) & Q(inscripcion__persona__apellido1__contains=s[0]) & Q(inscripcion__persona__apellido2__contains=s[1]) & Q(inscripcion__persona__nombres__contains=s[2]) & Q( inscripcion__persona__nombres__contains=s[3])).exclude(inscripcion__coordinacion__excluir=True, inscripcion__coordinacion__id=7).distinct()[:25]
                    else:
                        matriculas = Matricula.objects.filter(Q(nivel__periodo=periodo) & Q(inscripcion__persona__nombres__contains=q) | Q(inscripcion__persona__apellido1__contains=q) | Q(inscripcion__persona__apellido2__contains=q) | Q(inscripcion__persona__cedula__contains=q)).exclude(inscripcion__coordinacion__excluir=True, inscripcion__coordinacion__id=7).distinct()[:25]
                    data = {"result": "ok","results": [{"id": x.id, "name": x.flexbox_repr()} for x in matriculas]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'corregirsolicitud':
                try:
                    data['filtro'] = filtro = SolicitudJustificacionAsistencia.objects.get(pk=int(request.GET['id']))
                    form = CorregirSolicitudForm()
                    data['action'] = 'corregirsolicitud'
                    data['form2'] = form
                    template = get_template("adm_justificacionasistencia/modal/corregirsolicitud.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar solicitud de justificación'
                    data['solicitud'] = SolicitudJustificacionAsistencia.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request,"adm_justificacionasistencia/delsolicitud.html", data)
                except Exception as ex:
                    pass

        else:
            data['title'] = u'Aprobar / Justificar Asistencia'
            search = None
            ids = None
            fecha = datetime.now().date()
            aumento = 1
            while aumento <= variable_valor('DIAS_ANTERIOR_REVISAR_DIRECTOR'):
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
            #A TODAS LAS SOLICITUDES PASADA YA DE LAS FECHA DE REVISION SE LES CAMBIA EL ESTADO A "NO ATENDIDA"
            # for verificar_tiempo in SolicitudJustificacionAsistencia.objects.filter(estadosolicitud=variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA'),fechainiciojustificacion__lte=fecha, matricula__inscripcion__carrera=coordinador.carrera):
            #     verificar_tiempo.estadosolicitud=variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA_NO_ATENDIDA')
            #     verificar_tiempo.save(request)
            estadoselect=0
            estado_todos=False
            listaestado = []
            if 'e' in request.GET:
                estadoselect = int(request.GET['e'])
                if estadoselect>0:
                    listaestado.append(estadoselect)
                else:
                    estado_todos = True
            else:
                estado_todos = True
            if estado_todos:
                for estado in ESTADO_SOLICITUD_JUSTIFICACION_ASISTENCIA:
                    listaestado.append(estado[0])
            coordinaciones = persona.mis_coordinaciones()
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    solicitudes = SolicitudJustificacionAsistencia.objects.filter((Q(matricula__inscripcion__persona__nombres__icontains=search) |
                                                                                  Q(matricula__inscripcion__persona__apellido1__icontains=search) |
                                                                                  Q(matricula__inscripcion__persona__apellido2__icontains=search) |
                                                                                  Q(matricula__inscripcion__persona__cedula__icontains=search) |
                                                                                  Q(matricula__inscripcion__persona__pasaporte__icontains=search)|
                                                                                  Q(matricula__inscripcion__carrera__nombre__icontains=search) |
                                                                                  Q(casojustificacion__nombre__icontains=search)|
                                                                                  Q(materiajustificacionasistencia__materiaasignada__materia__asignatura__nombre__icontains=search)) &
                                                                                  Q(estadosolicitud__in=listaestado) &
                                                                                  Q(matricula__inscripcion__coordinacion__in=coordinaciones) &
                                                                                  Q(matricula__nivel__periodo=periodo)). \
                                                                                  distinct().order_by('-fechasolicitud', 'matricula__inscripcion__persona__apellido2','matricula__inscripcion__persona__apellido1','matricula__inscripcion__persona__nombres')
                else:
                    solicitudes = SolicitudJustificacionAsistencia.objects.filter((Q(matricula__inscripcion__persona__apellido1__icontains=ss[0]) &
                                                                                   Q(matricula__inscripcion__persona__apellido2__icontains=ss[1]))|
                                                                                  (Q(casojustificacion__nombre__icontains=ss[0]) &
                                                                                   Q(casojustificacion__nombre__icontains=ss[1]))|
                                                                                  (Q(materiajustificacionasistencia__materiaasignada__materia__asignatura__nombre__icontains=ss[0])&
                                                                                   Q(materiajustificacionasistencia__materiaasignada__materia__asignatura__nombre__icontains=ss[1]))|
                                                                                  (Q(matricula__inscripcion__carrera__nombre__icontains=ss[0]) &
                                                                                   Q(matricula__inscripcion__carrera__nombre__icontains=ss[1]))&
                                                                                   Q(estadosolicitud__in=listaestado) &
                                                                                  Q(matricula__inscripcion__coordinacion__in=coordinaciones) &
                                                                                   Q(matricula__nivel__periodo=periodo)).\
                                                                                    distinct().order_by('-fechasolicitud', 'matricula__inscripcion__persona__apellido2', 'matricula__inscripcion__persona__apellido1','matricula__inscripcion__persona__nombres')
            elif estadoselect > 0:
                    solicitudes = SolicitudJustificacionAsistencia.objects.filter(matricula__nivel__periodo=periodo, matricula__inscripcion__coordinacion__in=coordinaciones,
                                                                                  estadosolicitud=estadoselect).distinct().order_by('-fechasolicitud', 'matricula__inscripcion__persona__apellido2','matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__nombres')
            else:
                solicitudes = SolicitudJustificacionAsistencia.objects.filter(matricula__nivel__periodo=periodo, matricula__inscripcion__coordinacion__in=coordinaciones).distinct().order_by('-fechasolicitud','matricula__inscripcion__persona__apellido2', 'matricula__inscripcion__persona__apellido1','matricula__inscripcion__persona__nombres')

            paging = MiPaginador(solicitudes, 30)
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
            data['solicitudes'] = page.object_list
            data['solicitado'] = variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA')
            data['aprobado'] = variable_valor('APROBADO_JUSTIFICACION_ASISTENCIA')
            data['reprobado'] = variable_valor('RECHAZADO_JUSTIFICACION_ASISTENCIA')
            data['no_atendido'] = variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA_NO_ATENDIDA')
            data['estadoselect'] = estadoselect
            data['estados'] = ESTADO_SOLICITUD_JUSTIFICACION_ASISTENCIA
            data['coordinaciones_dr'] = coordinaciones.filter(excluir=False).exclude(id=7)
            data['hoy'] = datetime.now().date()
            return render(request, 'adm_justificacionasistencia/aprobar_director.html', data)
