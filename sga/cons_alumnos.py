# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata, obtener_reporte
from sga.models import Inscripcion, Periodo
from django.db import transaction

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    if request.method == 'POST':

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {}
        adduserdata(request, data)
        data['title'] = u'Consulta de alumnos'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'segmento':
                try:
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    if 'p' in request.GET:
                        try:
                            matriculas = inscripcion.matricula_set.filter(nivel__periodo__id=int(request.GET['p']))
                        except Exception as ex:
                            matriculas = inscripcion.matricula_set.all()
                    else:
                        matriculas = inscripcion.matricula_set.all()
                    data['matriculas'] = matriculas
                    data['reporte_0'] = obtener_reporte("certificado_notas_completos")
                    return render(request, "cons_alumnos/segmento.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['periodos'] = Periodo.objects.filter(visible=True)
            if 'id' in request.GET:
                data['id'] = request.GET['id']
            return render(request, "cons_alumnos/view.html", data)