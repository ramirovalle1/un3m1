# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from mobi.decorators import detect_mobile
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.models import  Sesion, ComplexivoClase, AlternativaTitulacion, PeriodoGrupoTitulacion

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
@detect_mobile
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    # if not ABRIR_CLASES_DISPOSITIVO_MOVIL and request.mobile:
    #     return HttpResponseRedirect("/?info=No se puede abrir clases desde un dispositivo movil.")
    # if not perfilprincipal.es_profesor():
    #     return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    profesor = perfilprincipal.profesor

    if request.method == 'POST':

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        # data['title'] = u'Horario de profesor UNEMI'
        # clasesabiertas = LeccionGrupo.objects.filter(profesor=profesor, abierta=True).order_by('-fecha', '-horaentrada')
        # data['disponible'] = clasesabiertas.count() == 0
        # if clasesabiertas:
        #     data['claseabierta'] = clasesabiertas[0]
        # if not data['disponible']:
        #     if clasesabiertas.count() > 1:
        #         for clase in clasesabiertas[1:]:
        #             clase.abierta = False
        #             clase.save()
        #     data['lecciongrupo'] = LeccionGrupo.objects.filter(profesor=profesor, abierta=True)[0]
        data['profesor'] = profesor
        data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
        hoy = datetime.now().date()
        # data['materiasnoprogramadas'] = ProfesorMateria.objects.filter(profesor=profesor, tipoprofesor_id=TIPO_DOCENTE_TEORIA, hasta__gt=hoy, activo=True, principal=True).exclude(materia__clase__id__isnull=False)
        data['misclases'] = clases = ComplexivoClase.objects.filter(activo=True, materia__profesor=profesor)
        data['sesiones'] = Sesion.objects.filter(turno__clase__in=clases).distinct()
        data['periodo'] = request.session['periodo']

        data['misclasescomplexivo'] = ComplexivoClase.objects.filter(activo=True, fechafin__gte=hoy, materia__profesor__profesorTitulacion=profesor).order_by(
            'fechainicio')
        data['periodotitulacion'] = PeriodoGrupoTitulacion.objects.filter(status=True).order_by('-id')
        periodo = int(request.GET['per']) if 'per' in request.GET  else 0
        cursos = AlternativaTitulacion.objects.filter(status=True, tipotitulacion__tipo=2)
        if periodo > 0:
            cursos = cursos.filter(grupotitulacion__periodogrupo=periodo)
            data['per_id'] = PeriodoGrupoTitulacion.objects.get(pk=periodo)
        return render(request, "pro_complexivohorarios/view.html", data)




        # clasesabiertas = LeccionGrupo.objects.filter(profesor=profesor, abierta=True).order_by('-fecha', '-horaentrada')
        # data['disponible'] = clasesabiertas.count() == 0
        # if clasesabiertas:
        #     data['claseabierta'] = clasesabiertas[0]
        # if not data['disponible']:
        #     if clasesabiertas.count() > 1:
        #         for clase in clasesabiertas[1:]:
        #             clase.abierta = False
        #             clase.save()
        #     data['lecciongrupo'] = LeccionGrupo.objects.filter(profesor=profesor, abierta=True)[0]
        # data['profesor'] = profesor
        # data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
        # hoy = datetime.now().date()
        # data['materiasnoprogramadas'] = ProfesorMateria.objects.filter(profesor=profesor, tipoprofesor_id=TIPO_DOCENTE_TEORIA, hasta__gt=hoy, activo=True, principal=True).exclude(materia__clase__id__isnull=False)
        # data['misclases'] = clases = Clase.objects.filter(activo=True, fin__gte=hoy, materia__profesormateria__profesor=profesor, materia__profesormateria__principal=True, materia__profesormateria__tipoprofesor_id=TIPO_DOCENTE_TEORIA, tipoprofesor_id=TIPO_DOCENTE_TEORIA).order_by('inicio')
        # data['sesiones'] = Sesion.objects.filter(turno__clase__in=clases).distinct()
        # data['periodo'] = request.session['periodo']
        # data['misclasescomplexivo'] = ComplexivoClase.objects.filter(activo=True, fechafin__gte=hoy, materia__profesor__profesorTitulacion=profesor).order_by(
        #     'fechainicio')
