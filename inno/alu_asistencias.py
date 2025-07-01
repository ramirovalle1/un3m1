# -*- coding: latin-1 -*-
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template

from decorators import secure_module, last_access
from matricula.models import PeriodoMatricula
from sga.commonviews import adduserdata, obtener_reporte
from sga.models import Matricula, SesionZoom, AsistenciaLeccion
from sga.templatetags.sga_extras import encrypt_alu


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    matricula = inscripcion.mi_matricula_periodo(periodo.id)
    if not matricula:
        return HttpResponseRedirect("/?info=Ud. no se encuentra matriculado")

    # automatricula de pregrado
    confirmar_automatricula_pregrado = inscripcion.tiene_automatriculapregrado_por_confirmar(periodo)
    if confirmar_automatricula_pregrado:
        mat = inscripcion.mi_matricula_periodo(periodo.id)
        if mat.nivel.fechainicioagregacion > datetime.now().date():
            return HttpResponseRedirect("/?info=Estimado estudiante, se informa que el proceso de aceptación de matrícula empieza %s" % mat.nivel.fechainicioagregacion.__str__())
        if mat.nivel.fechafinagregacion < datetime.now().date():
            return HttpResponseRedirect("/?info=Estimado estudiante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado")
        if PeriodoMatricula.objects.values("id").filter(periodo=periodo, status=True).exists():
            ePeriodoMatricula = PeriodoMatricula.objects.filter(periodo=periodo, status=True)[0]
            if not ePeriodoMatricula.activo:
                return HttpResponseRedirect("/?info=Estimado aspirante, se informa que el proceso de matrícula se encuentra inactivo")
        return HttpResponseRedirect("/alu_matricula/pregrado")

    # automatricula de admisión
    confirmar_automatricula_admision = inscripcion.tiene_automatriculaadmision_por_confirmar(periodo)
    if confirmar_automatricula_admision:
        mat = inscripcion.mi_matricula_periodo(periodo.id)
        if mat.nivel.fechainicioagregacion > datetime.now().date():
            return HttpResponseRedirect("/?info=Estimado aspirante, se informa que el proceso de aceptación de matrícula empieza %s" % mat.nivel.fechainicioagregacion.__str__())
        if mat.nivel.fechafinagregacion < datetime.now().date():
            return HttpResponseRedirect("/?info=Estimado aspirante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado")
        if PeriodoMatricula.objects.values("id").filter(periodo=periodo, status=True).exists():
            ePeriodoMatricula = PeriodoMatricula.objects.filter(periodo=periodo, status=True)[0]
            if not ePeriodoMatricula.activo:
                return HttpResponseRedirect("/?info=Estimado estudiante, se informa que el proceso de matrícula se encuentra inactivo")
        return HttpResponseRedirect("/alu_matricula/admision")

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'viewAsistencia':
                try:
                    if not 'ida' in request.POST:
                        raise NameError(u"Parametro de asistencia no encontrado")

                    if not AsistenciaLeccion.objects.values("id").filter(pk=int(request.POST['ida'])).exists():
                        raise NameError(u"Asistencia no encontrada")
                    asistencia = AsistenciaLeccion.objects.get(pk=int(request.POST['ida']))
                    data['asistencia'] = asistencia
                    template = get_template("alu_asistencias/view_asistencia.html")
                    json_content = template.render(data)
                    return JsonResponse( {"result": "ok",  "html": json_content, "fecha": asistencia.fecha_creacion.strftime("%d-%m-%Y")})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el dato. %s" % ex.__str__()})

            return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            HttpResponseRedirect("/")
        else:
            try:
                data['title'] = u'Consulta de asistencias'
                if not periodo:
                    raise NameError(u"No tiene periodo asignado.")
                data['inscripcion'] = inscripcion
                data['matricula'] = matricula
                data['mi_malla'] = inscripcion.mi_malla()
                data['minivel'] = inscripcion.mi_nivel().nivel
                cantidadmaxima = 0
                mismaterias = matricula.materiaasignada_set.all().order_by('materia__asignatura')
                for materia in mismaterias:
                    cantidad_asistencias_lecciones = materia.cantidad_asistencias_lecciones()
                    if cantidad_asistencias_lecciones > cantidadmaxima:
                        cantidadmaxima = cantidad_asistencias_lecciones
                materiaasignadas = []
                for materia in mismaterias:
                    cantidad_asistencias_lecciones = materia.cantidad_asistencias_lecciones()
                    asistencia_real = materia.asistencia_real()
                    real_dias_asistencia = materia.real_dias_asistencia()
                    materiaasignadas.append([materia, materia.asistencias_lecciones(), cantidadmaxima, cantidad_asistencias_lecciones, cantidadmaxima - cantidad_asistencias_lecciones, asistencia_real, real_dias_asistencia, real_dias_asistencia - asistencia_real])
                data['materiasasiganadas'] = materiaasignadas
                data['cantidad'] = cantidadmaxima
                data['modalidadcarrera'] = inscripcion.modalidad_id
                data['reporte_0'] = obtener_reporte('clases_consolidado_alumno')
                return render(request, "alu_asistencias/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect("/?info=%s" % ex.__str__())
