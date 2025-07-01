# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template
from django.contrib.admin.models import LogEntry
from decorators import secure_module, last_access
from settings import CANTIDAD_HORAS_JUSTIFICACION_ASISTENCIAS, LIMITE_HORAS_JUSTIFICAR
from sga.commonviews import adduserdata, justificar_asistencia
from sga.models import Matricula, Profesor, AsistenciaLeccion, MateriaAsignada
from sga.templatetags.sga_extras import encrypt


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
    if request.method == 'POST':
        action = request.POST['action']

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

        if action == 'actualizar_asistencia':
            try:
                materiaasignada = MateriaAsignada.objects.get(pk=encrypt(request.POST['id']))
                materiaasignada.save(actualiza=True)
                materiaasignada.actualiza_estado()
                return JsonResponse({"result": "ok","mensaje": u"Se actualizo correctamente la asistencia",
                                     "porcentaje_asistencia": materiaasignada.asistenciafinal,
                                     "estado_asistencia": materiaasignada.porciento_requerido(),
                                     "total_general": materiaasignada.real_dias_asistencia(),
                                    "total_presentes": materiaasignada.asistencia_real(),
                                    "total_faltas": materiaasignada.real_dias_asistencia() - materiaasignada.asistencia_real(),
                                     "materiaasignada_id":materiaasignada.id
                                     })
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'viewAsistencia':
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
                #print(data['logs'].count())
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
                template = get_template("adm_asistencias/view_asistencia.html")
                json_content = template.render(data)
                return JsonResponse(
                    {"result": "ok", "html": json_content, "fecha": asistencia.fecha_creacion.strftime("%d-%m-%Y")})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Consulta de asistencias.'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'asistencia':
                try:
                    data['title'] = u'Consulta de asistencias de alumnos'
                    profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['profesor'] = profesor
                    data['periodo'] = request.session['periodo']
                    data['materias'] = profesor.materias_imparte_periodo(data['periodo'])
                    return render(request, "adm_asistencias/view.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            if 'id' not in request.GET:
                return HttpResponseRedirect('/?info=Debe de seleccionar un estudiante matriculado desde el modulo de inscripciones')
            matricula = Matricula.objects.get(pk=request.GET['id'])
            data['matricula'] = matricula
            cantidadmaxima = 0
            for materia in matricula.materiaasignada_set.all():
                if materia.cantidad_asistencias_lecciones() > cantidadmaxima:
                    cantidadmaxima = materia.cantidad_asistencias_lecciones()
            materiaasignadas = []
            for materia in matricula.materiaasignada_set.filter(retiramateria=False).order_by('materia__asignatura'):
                materiaasignadas.append([materia, materia.asistencias_lecciones(), cantidadmaxima, materia.asistencia_plan(), cantidadmaxima - materia.cantidad_asistencias_lecciones(), materia.asistencia_real(), materia.real_dias_asistencia(), materia.real_dias_asistencia() - materia.asistencia_real()])
            data['materiasasiganadas'] = materiaasignadas
            data['cantidad'] = cantidadmaxima
            data['puede_modificar_asistencia'] = True if not periodo.tipo_id==2 or matricula.carrera_es_admision() else False
            data['puede_modificar_asistencia_por_perfilusuario'] =  persona.mis_carreras().values('id').filter(pk=matricula.inscripcion.carrera.id).exists()
            return render(request, "adm_asistencias/view.html", data)