# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from mobi.decorators import detect_mobile
from decorators import secure_module, last_access
from settings import ABRIR_CLASES_DISPOSITIVO_MOVIL
from sga.commonviews import adduserdata
from sga.models import Clase, Sesion, LeccionGrupo, ProfesorMateria, ProfesorReemplazo, Materia


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
@detect_mobile
def view(request):
    data = {}
    adduserdata(request, data)
    hoy = datetime.now().date()
    data['reemplazos'] = reemplazos = ProfesorReemplazo.objects.filter(desde__lte=hoy, hasta__gte=hoy, reemplaza__persona=request.session['persona'])
    if reemplazos:
        profesor_principal = reemplazos[0].reemplaza
    else:
        return HttpResponseRedirect("/?info=No tiene asignado reemplazar a otro docente, en esta fecha.")
    data['materias_profesor_principal_reemplado'] = materias_profesor_principal_reemplado = Materia.objects.filter(profesormateria__profesor=profesor_principal, profesormateria__tipoprofesor__id=6)
    if not reemplazos.exists():
        return HttpResponseRedirect("/?info=No tiene asignado reemplazar a otro docente.")
    data['reemplazoid'] = reemplazo_id = int(request.GET['reemplazoid']) if 'reemplazoid' in request.GET else reemplazos[0].reemplaza.persona.id
    perfiles = profesor_principal.persona.mis_perfilesusuarios_app('sga')
    perfilprincipal = profesor_principal.persona.perfilusuario_principal(perfiles, 'sga')
    if not ABRIR_CLASES_DISPOSITIVO_MOVIL and request.mobile:
        return HttpResponseRedirect("/?info=No se puede abrir clases desde un dispositivo movil.")
    if not perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    profesor = perfilprincipal.profesor
    if request.method == 'POST':
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Horario de profesor'
        LeccionGrupo.objects.filter(profesor=profesor, abierta=True).exists()
        clasesabiertas = LeccionGrupo.objects.filter(profesor=profesor, abierta=True).order_by('-fecha', '-horaentrada')
        data['disponible'] = clasesabiertas.count() == 0
        if clasesabiertas:
            data['claseabierta'] = clasesabiertas[0]
        if not data['disponible']:
            if clasesabiertas.count() > 1:
                for clase in clasesabiertas[1:]:
                    clase.abierta = False
                    clase.save(request)
            data['lecciongrupo'] = LeccionGrupo.objects.filter(profesor=profesor, abierta=True)[0]
        data['profesor'] = profesor
        data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
        data['materiasnoprogramadas'] = ProfesorMateria.objects.filter(profesor=profesor, hasta__gt=hoy, activo=True, principal=True).exclude(materia__clase__id__isnull=False)
        data['misclases'] = clases = Clase.objects.filter(activo=True, fin__gte=hoy, profesor=profesor, materia__in=materias_profesor_principal_reemplado).order_by('inicio')
        data['sesiones'] = Sesion.objects.filter(turno__clase__in=clases).distinct()
        data['periodo'] = request.session['periodo']
        data['reemplazo'] = reemplazos.get(reemplaza__persona_id=reemplazo_id)
        data['parametros'] = True
        return render(request, "pro_horarios_reemplazo/view.html", data)