# -*- coding: latin-1 -*-
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db.models.functions import Coalesce
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata, obtener_reporte
from sga.models import Inscripcion, PracticasPreprofesionalesInscripcion
from sga.templatetags.sga_extras import encrypt

from django.db.models import F, Sum
from django.db.models import FloatField
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
    data['periodo'] = request.session['periodo']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    data['inscripcion'] = inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'extracurricular':
                try:
                    data['title'] = u'Actividades extracurriculares'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['pasantias'] = inscripcion.pasantias()
                    data['talleres'] = inscripcion.talleres()
                    data['practicas'] = inscripcion.practicas()
                    data['vccs'] = inscripcion.vcc()
                    return render(request, "alu_notas/extracurricular.html", data)
                except Exception as ex:
                    pass

            if action == 'detalle':
                try:
                    data['title'] = u'Historico de notas'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['record'] = record = inscripcion.recordacademico_set.get(pk=int(encrypt(request.GET['rec'])))
                    data['historicos'] = record.historicorecordacademico_set.all().order_by('-fecha')
                    return render(request, "alu_notas/detalle.html", data)
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Registro academico'
            data['records'] = inscripcion.recordacademico_set.all().order_by('asignaturamalla__nivelmalla', 'asignatura', 'fecha')
            data['total_creditos'] = inscripcion.total_creditos()
            if not inscripcion.inscripcionmalla_set.filter(status=True):
                return HttpResponseRedirect("/?info=No tiene malla asignada.")
            data['modalidadcarrera'] = inscripcion.modalidad_id
            data['total_creditos_malla'] = inscripcion.total_creditos_malla()
            data['total_creditos_modulos'] = inscripcion.total_creditos_modulos()
            data['total_creditos_otros'] = inscripcion.total_creditos_otros()
            data['total_horas'] = inscripcion.total_horas()
            data['promedio'] = inscripcion.promedio_record()
            data['aprobadas'] = inscripcion.recordacademico_set.values('id').filter(aprobada=True, valida=True).count()
            data['reprobadas'] = inscripcion.recordacademico_set.values('id').filter(aprobada=False, valida=True).count()
            data['reporte_0'] = obtener_reporte("record_alumno")
            data['admision'] = not inscripcion.mi_coordinacion().id == 9
            if inscripcion.inscripcionmalla_set.filter(status=True):
                data['horas_total_practicas'] = inscripcion.inscripcionmalla_set.filter(status=True).first().malla.horas_practicas
                data['horas_total_vinculacion'] = inscripcion.inscripcionmalla_set.filter(status=True).first().malla.horas_vinculacion
            data['mishoraspracticas'] = inscripcion.numero_horas_practicas_pre_profesionales()
            data['miishorasvinculacion'] = inscripcion.numero_horas_proyectos_vinculacion()
            data['numero_horas_vinculacion'] = inscripcion.numero_horas_vinculacion()

            fechainicioprimernivel = inscripcion.fechainicioprimernivel if inscripcion.fechainicioprimernivel else datetime.now().date()
            excluiralumnos = datetime(2009, 1, 21, 23, 59, 59).date()
            data['esexonerado'] = fechainicioprimernivel <= excluiralumnos

            return render(request, "alu_notas/view.html", data)
