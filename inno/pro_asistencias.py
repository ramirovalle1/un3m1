# -*- coding: latin-1 -*-
from django.contrib.admin.models import LogEntry
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.models import Materia, PermisoPeriodo, MateriaAsignada, AsistenciaLeccion, GruposProfesorMateria
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.templatetags.sga_extras import encrypt

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    data['profesor'] = profesor = perfilprincipal.profesor
    data['periodo'] = periodo = request.session['periodo']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'segmento':
                try:
                    data['materia'] = materia = Materia.objects.get(pk=request.POST['id'])
                    data['profesoresmaterias'] = materia.profesormateria_set.filter(status=True, profesor=profesor)
                    # data['gruposprofesor'] = gruposprofesor = GruposProfesorMateria.objects.filter(profesormateria__materia=materia, profesormateria__profesor=profesor, status=True)
                    data['asistenciaaprobar'] = materia.modeloevaluativo.asistenciaaprobar
                    # asistodo = []
                    # for asignadomateria in materia.asignados_a_est+a_materia_por_profesor(profesor):
                    #     asis = []
                    #     for asistencia in asignadomateria.asistencias():
                    #         asis.append(asistencia)
                    #     asistodo.append([asignadomateria,asis])
                    # data['asistodo'] = asistodo
                    template = get_template("pro_asistencias/segmento.html")
                    json_content = template.render(data)
                    # plantilla = render(request, "pro_asistencias/segmento.html", {'materia': materia})
                    return JsonResponse({"result": "ok", "data":json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informeasistencia':
                try:
                    data['materia'] = materia = Materia.objects.get(pk=int(request.POST['id']))
                    data['asistenciaaprobar'] = materia.modeloevaluativo.asistenciaaprobar
                    asistodo = []
                    for asignadomateria in materia.asignados_a_esta_materia():
                        asis = []
                        for asistencia in asignadomateria.asistencias_leccion_total():
                            asis.append(asistencia)
                        asistodo.append([asignadomateria, asis])
                    data['asistodo'] = asistodo
                    data['vertical_horizontal'] = True if materia.total_lecciones_individuales() <= 35 else False
                    return conviert_html_to_pdf('pro_asistencias/informe_asistencia_docente.html',{'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    pass

            elif action == 'viewAsistencia':
                try:
                    asistencia = AsistenciaLeccion.objects.get(pk=int(request.POST['ida']))
                    data['asistencia'] = asistencia

                    data['solicitud_justificacion'] = None
                    data['justificacion_manual'] = None

                    palabra_buscar = u'Asistencia en clase: %s - %s - %s,' % (
                        asistencia.materiaasignada.materia.asignatura.nombre,
                        asistencia.materiaasignada.matricula.inscripcion.persona.nombre_completo_inverso(),
                        asistencia.leccion.fecha.strftime("%Y-%m-%d"))

                    data['logs'] = LogEntry.objects.filter(change_message__contains=palabra_buscar,
                                                           action_time__date=asistencia.leccion.fecha).order_by(
                        'action_time')
                    justificaciones = asistencia.detallemateriajustificacionasistencia_set.filter(status=True)
                    if justificaciones.exists():
                        data[
                            'solicitud_justificacion'] = justificaciones.first().materiajustificacion.solicitudjustificacion
                    justificacion = asistencia.justificacionausenciaasistencialeccion_set.filter(status=True)
                    if justificacion.exists():
                        data['justificacion_manual'] = justificacion

                    matricula = asistencia.materiaasignada.matricula
                    data[
                        'puede_modificar_asistencia'] = True if not periodo.tipo_id == 2 or matricula.carrera_es_admision() else False
                    data['sga_puede_modificar_asistencia'] = request.user.has_perm('sga.puede_modificar_asistencia')
                    data['puede_modificar_asistencia_por_perfilusuario'] = persona.mis_carreras().values('id').filter(
                        pk=matricula.inscripcion.carrera.id).exists()
                    data['is_superuser'] = request.user.is_superuser
                    if matricula.inscripcion.coordinacion in persona.mis_coordinaciones() or request.user.is_superuser:
                        data['puede_justificar_asistencia'] = request.user.has_perm('sga.puede_justificar_asistencia')
                    template = get_template("pro_asistencias/view_asistencia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok",  "html": json_content, "fecha": asistencia.fecha_creacion.strftime("%d-%m-%Y")})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'detalleasistencia':
                try:
                    data['title'] = u'Adicionar estudiante'
                    data['estudiante'] = estudiante = MateriaAsignada.objects.get(pk=int(encrypt(request.GET['idmateriaasignada'])))
                    data['detalle'] = estudiante.asistenciamoodle_set.filter(status=True)
                    return render(request, "pro_planificacion/detalleasistencia.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            try:
                # if not PermisoPeriodo.objects.filter(periodo=periodo).exists():
                #     return HttpResponseRedirect("/?info=No tiene materias en el periodo seleccionado.")
                data['title'] = u'Asistencias de alumnos'
                if periodo.ocultarmateria:
                    data['materias'] = materias = False
                else:
                    data['materias'] = materias = Materia.objects.filter(nivel__periodo=periodo, profesormateria__profesor=profesor).distinct()
                if not materias.exists():
                    raise NameError(u"No tiene materias en el periodo seleccionado")
                if periodo.versionasistencia == 2:
                    if 'codigomat' in request.GET:
                        primeramateria = materias.get(pk=request.GET['codigomat'])
                    else:
                        primeramateria = materias[0]
                    data['primeramateria'] = primeramateria
                    data['unidadesperiodo'] = periodo.unidadesperiodo_set.values_list('orden').filter(status=True).order_by('orden').distinct()
                    return render(request, "pro_asistencias/view_asistenciamoodle.html", data)
                if periodo.versionasistencia == 1:
                    return render(request, "pro_asistencias/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f"/?info=No puede acceder al módulo")
