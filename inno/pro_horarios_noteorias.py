# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from mobi.decorators import detect_mobile
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.models import Clase, Sesion, DetalleDistributivo, ClaseActividadEstado
from sga.funcionesxhtml2pdf import conviert_html_to_pdf


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
@detect_mobile
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['periodo'] = periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    # if not ABRIR_CLASES_DISPOSITIVO_MOVIL and request.mobile:
    #     return HttpResponseRedirect("/?info=No se puede abrir clases desde un dispositivo movil.")
    if not perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    profesor = perfilprincipal.profesor
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'horarioactividadespdf':
            try:
                data['title'] = u'Horarios de las Actividades del Profesor'
                data['profesor'] = profesor
                data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                clases_turnos = profesor.extraer_clases_y_turnos_practica(datetime.now().date(), periodo)
                data['misclases'] = clases_turnos[0]
                data['sesiones'] = Sesion.objects.filter(turno__clase__in=clases_turnos[1]).distinct()
                return conviert_html_to_pdf('pro_horarios/actividades_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        data = {}
        adduserdata(request, data)
        if 'action' in request.GET:
            action = request.GET['action']
            data['periodo'] = request.session['periodo']
            if 'listactividades' == action:
                try:
                    actidocencia = DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                                                                      distributivo__periodo=periodo,
                                                                      criteriodocenciaperiodo_id__isnull=False).exclude(criteriodocenciaperiodo__criterio_id__in=['15','16','17','18','20','21','27','28','19'])
                    actiinvestigacion = DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                                                                           distributivo__periodo=periodo,
                                                                           criterioinvestigacionperiodo_id__isnull=False)
                    actigestion = DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                                                                     distributivo__periodo=periodo,
                                                                     criteriogestionperiodo_id__isnull=False)
                    data['actividades'] = actidocencia | actiinvestigacion | actigestion
                    # return render(request, "pro_horarios/actividadesdocentes.html", data)
                except Exception as ex:
                    pass
        else:
            data['title'] = u'Horarios del Profesor'
            if not request.session['periodo'].visible:
                return HttpResponseRedirect("/?info=Periodo Inactivo.")
            data['profesor'] = profesor
            data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
            data['mostrar'] = 0
            if ClaseActividadEstado.objects.values('id').filter(profesor=profesor, periodo=periodo, status=True).exists():
                data['mostrar'] = 1
                data['detalleestados'] = estadoactividad = ClaseActividadEstado.objects.filter(profesor=profesor, periodo=periodo, status=True)
                data['estadoactividad'] = estadoactividad.all().order_by('-id')[0]
            clases_turnos = profesor.extraer_clases_y_turnos_practica(datetime.now().date(), periodo)
            data['misclases'] = clases_turnos[0]
            data['sesiones'] = sesiones = Sesion.objects.filter(turno__in=clases_turnos[1]).distinct()
            if not sesiones:
                return HttpResponseRedirect(u"/?info=No tiene asignaturas Téorico-Prácticas.")
            return render(request, "pro_horarios/horarios_noteorias.html", data)