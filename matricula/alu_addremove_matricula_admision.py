# -*- coding: latin-1 -*-
import os
from datetime import datetime
import code128
import pyqrcode
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from matricula.funciones import valid_intro_module_estudiante
from matricula.models import PeriodoMatricula
from settings import SITE_STORAGE
from sga.commonviews import adduserdata, obtener_reporte
from sga.models import Matricula, Inscripcion
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavecertificados
from django.db import connections

from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
def view(request):
    data = {}
    adduserdata(request, data)
    valid, msg_error = valid_intro_module_estudiante(request, 'admision')
    if not valid:
        return HttpResponseRedirect(f"/?info={msg_error}")
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    inscripcion = perfilprincipal.inscripcion
    hoy = datetime.now().date()

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
        else:
            try:
                data['title'] = u'Matriculación Online'
                periodomatricula = None
                matricula = None
                if not PeriodoMatricula.objects.values_list('id').filter(status=True, activo=True, periodo=periodo).exists():
                    raise NameError(u"Estimado/a aspirante, el periodo de matriculación se encuentra inactivo")
                periodomatricula = PeriodoMatricula.objects.filter(status=True, activo=True, periodo=periodo)
                if periodomatricula.count() > 1:
                    raise NameError(u"Estimado/a aspirante, proceso de matriculación no se encuentra activo")
                periodomatricula = periodomatricula[0]
                if not periodomatricula.esta_periodoactivomatricula():
                    raise NameError(u"Estimado/a aspirante, el periodo de matriculación se encuentra inactivo")
                if inscripcion.tiene_perdida_carrera(periodomatricula.num_matriculas):
                    raise NameError(u"ATENCIÓN: Su limite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria para mas informacion.")
                if periodomatricula.periodo and inscripcion.tiene_automatriculaadmision_por_confirmar(periodomatricula.periodo):
                    return HttpResponseRedirect("/alu_matricula")
                raise NameError(u"Funcionalidad no se encuentra activa para aspirantes")
                return render(request, "matricula_addremove/admision/view.html", data)
            except Exception as ex:
                data['msg_matricula'] = ex.__str__()
                return render(request, "matricula_addremove/view.html", data)
