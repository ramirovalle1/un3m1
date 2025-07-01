# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from matricula.models import PeriodoMatricula
from settings import MATRICULACION_LIBRE
from sga.commonviews import adduserdata, obtener_reporte
from sga.models import Materia, HorarioVirtual, DetalleHorarioVirtual
from django.db import transaction

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    periodo = request.session['periodo']

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
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:

            action = request.GET['action']
            if action == 'fechasexamenes':
                try:
                    data['title'] = u'Planificacion de la materia'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['planificaciones'] = materia.planificacionmateria_set.all()
                    return render(request, "alu_cronograma/fechasexamenes.html", data)
                except Exception as ex:
                    pass

            if action == 'horarioexamen':
                try:
                    data['title'] = u'Horario Examen'
                    matricula = inscripcion.matricula()
                    data['horariovirtual'] = None
                    data['horariovirtualrecu'] = None
                    # periodo = request.session['periodo']
                    if not matricula:
                        return HttpResponseRedirect("/?info=Ud. aun no ha sido matriculado")
                    if HorarioVirtual.objects.filter(participanteshorariovirtual__matricula=matricula, tipo=1, status=True):
                        data['horariovirtual'] = horariovirtual = HorarioVirtual.objects.filter(participanteshorariovirtual__matricula=matricula,tipo=1, status=True)
                        # data['horarioasignaturas'] = horariovirtual.detallehorariovirtual_set.filter(status=True).order_by('fecha')
                        # tienehorario = True
                    if HorarioVirtual.objects.filter(participanteshorariovirtual__matricula=matricula, tipo=2, status=True):
                        data['horariovirtualrecu'] = horariovirtualrecu = HorarioVirtual.objects.filter(participanteshorariovirtual__matricula=matricula,tipo=2, status=True)
                        # data['horarioasignaturasrecu'] = DetalleHorarioVirtual.objects.filter(horariovirtual__in=horariovirtualrecu ,status=True).order_by('fecha')
                    #     tienehorariorecu = True
                    # data['tienehorario'] = tienehorario
                    # data['tienehorariorecu'] = tienehorariorecu
                    data['periodo'] = request.session['periodo']
                    return render(request, "alu_cronograma/horarioexamen.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Cronograma de materias del estudiante'
            matricula = inscripcion.matricula()
            if not matricula:
                return HttpResponseRedirect("/?info=Ud. aun no ha sido matriculado")
            materiasasignadas = matricula.materiaasignada_set.all().order_by('materia__inicio')
            data['matricula'] = matricula
            data['materiasasignadas'] = materiasasignadas
            data['reporte_0'] = obtener_reporte('mate_cronogramaalumno')
            data['hoy'] = datetime.now().date()
            data['matriculacion_libre'] = MATRICULACION_LIBRE
            data['modalidadcarrera'] = inscripcion.modalidad_id
            return render(request, "alu_cronograma/view.html", data)
