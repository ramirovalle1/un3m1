# -*- coding: latin-1 -*-
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect,JsonResponse
from django.shortcuts import render
from sga.commonviews import adduserdata
from decorators import secure_module
from sga.funciones import log
from sga.models import ComplexivoExamen, AlternativaTitulacion, ComplexivoExamenDetalle


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module

def view(request):
    data = {}
    adduserdata(request, data)
    perfilprincipal = request.session['perfilprincipal']
    data['profesor']=profesor = perfilprincipal.profesor
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'notas':
                try:
                    datos = json.loads(request.POST['datos'])
                    for d in datos:
                        detalle = ComplexivoExamenDetalle.objects.get(pk=d['id'])
                        detalle.calificacion = float(d['exa'])
                        detalle.calificacionrecuperacion = float(d['rec'])
                        detalle.save(True)
                        log(u"Adiciono calificacion: %s" % detalle, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(
                        json.dumps({"result": "bad", "mensaje": u"Error al eliminar los datos.(%s)" % ex}),
                        content_type="application/json")
            if action == 'observaciones':
                try:
                    detalle = ComplexivoExamenDetalle.objects.get(pk=request.POST['id'])
                    detalle.observacion = request.POST['observacion']
                    detalle.save(request)
                    log(u"Adiciono observacion a calificacion: %s" % detalle, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.(%s)" % ex})

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'calificaciones':
                try:
                    data['title'] = u'Examen complexivo'
                    examen = ComplexivoExamen.objects.get(pk=request.GET['id'])
                    data['alternativa'] = AlternativaTitulacion.objects.get(pk=examen.alternativa_id)
                    data['examen'] = examen
                    matriculados = examen.alternativa.matriculatitulacion_set.filter(estado=1)
                    for matriculado in matriculados:
                        if not ComplexivoExamenDetalle.objects.values('id').filter(examen= examen, matricula=matriculado).exists():
                            detalle = ComplexivoExamenDetalle()
                            detalle.examen = examen
                            detalle.matricula = matriculado
                            detalle.save(request)
                    data['estudiantes'] = examen.complexivoexamendetalle_set.all().order_by('matricula__inscripcion')
                    return render(request, "pro_complexivoexamen/calificaciones.html", data)
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Listado de Examen complexivo'
            data['examenes'] = ComplexivoExamen.objects.filter(docente=profesor).order_by('alternativa__carrera')
            return render(request, "pro_complexivoexamen/views.html", data)