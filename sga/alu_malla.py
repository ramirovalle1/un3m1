# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.models import NivelMalla, EjeFormativo, AsignaturaMalla
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
    data['periodo'] = periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    data['inscripcion']= inscripcion = perfilprincipal.inscripcion
    confirmar_automatricula_admision = inscripcion.tiene_automatriculaadmision_por_confirmar(periodo)
    # if datetime(2021, 5, 28, 0, 0, 0).date() == datetime.now().date():
    if confirmar_automatricula_admision and periodo.limite_agregacion < datetime.now().date():
        cordinacionid = inscripcion.carrera.coordinacion_carrera().id
        if cordinacionid in [9]:
            return HttpResponseRedirect("/?info=Estimado aspirante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado")
    inscripcionmalla = inscripcion.malla_inscripcion()
    if not inscripcionmalla:
        return HttpResponseRedirect("/?info=Este estudiante no tiene ninguna malla asociada")
    if request.method == 'POST':

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'predecesora':
                try:
                    asignaturamalla = AsignaturaMalla.objects.get(pk=request.GET['id'])
                    lista = []
                    for predecesora in asignaturamalla.asignaturamallapredecesora_set.all():
                            lista.append([predecesora.predecesora.asignatura.nombre, predecesora.predecesora.nivelmalla.nombre])
                    return JsonResponse({"result": "ok", "lista": lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Malla del alumno'
            data['malla'] = malla = inscripcionmalla.malla
            data['nivelesdemallas'] = NivelMalla.objects.all().order_by('orden')
            asignaturamalla=AsignaturaMalla.objects.filter(malla=malla, status=True, vigente=True).exclude(tipomateria_id=3)
            xyz = [1,2,3]
            if inscripcion.itinerario and inscripcion.itinerario > 0:
                xyz.remove(inscripcion.itinerario)
                asignaturamalla = asignaturamalla.exclude(itinerario__in=xyz)
            data['ejesformativos'] = EjeFormativo.objects.filter(status=True,id__in=AsignaturaMalla.objects.values_list('ejeformativo_id',flat=True).filter(malla=malla, status=True, vigente=True).distinct()).order_by('nombre')
            data['asignaturasmallas'] = asignaturasmallas = [(x, inscripcion.aprobadaasignatura(x)) for x in asignaturamalla]
            data['resumenes'] = [{'id': x.id, 'horas': x.total_horas(malla), 'creditos': x.total_creditos(malla)} for x in NivelMalla.objects.all().order_by('nombre')]
            return render(request, "alu_malla/view.html", data)
