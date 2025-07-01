# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from settings import USA_PLANIFICACION
from sga.commonviews import adduserdata
from sga.forms import ArchivoPlanificacionForm
from sga.funciones import generar_nombre, log
from sga.models import Materia, Leccion, MateriaAsignada, MateriaAsignadaPlanificacion


@login_required(redirect_field_name='ret', login_url='/loginsga')
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
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'subirdeberplanificacion':
                try:
                    miplanificacion = MateriaAsignadaPlanificacion.objects.get(pk=request.POST['id'])
                    form = ArchivoPlanificacionForm(request.POST, request.FILES)
                    if form.is_valid():
                        tarea = request.FILES['archivo']
                        nameoriginal = tarea._name
                        tarea._name = generar_nombre("tarea_", tarea._name)
                        miplanificacion.archivo = tarea
                        miplanificacion.fechaentrega = miplanificacion.planificacion.hasta
                        miplanificacion.horaentrega = miplanificacion.planificacion.horahasta
                        miplanificacion.save(request)
                        log(u'Alumno sube tarea de planificación:%s [%s] - archivo: %s [%s]' % (miplanificacion, miplanificacion.id, miplanificacion.archivo, miplanificacion.horaentrega), request,"add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'deldeberplanificacion':
                try:
                    miplanificacion = MateriaAsignadaPlanificacion.objects.get(pk=request.POST['id'])
                    if not miplanificacion.calificacion:
                        log(u'Alumno elimina tarea de planificación:%s [%s] - archivo: %s [%s]' % (miplanificacion, miplanificacion.id, miplanificacion.archivo, miplanificacion.horaentrega),request, "del")
                        miplanificacion.archivo = None
                        miplanificacion.fechaentrega = None
                        miplanificacion.horaentrega = None
                        miplanificacion.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'planificacion':
                try:
                    data['title'] = u'Planificacion de la materia'
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    data['materia'] = materiaasignada.materia
                    data['materiaasignada'] = materiaasignada
                    data['planificaciones'] = materiaasignada.materia.planificacionmateria_set.filter(desde__lte=datetime.now().date())
                    return render(request, "alu_documentos/planificacionall.html", data)
                except Exception as ex:
                    pass

            if action == 'deberes':
                try:
                    data['title'] = u'Deberes por clases'
                    materia = Materia.objects.get(pk=request.GET['id'])
                    lecciones = Leccion.objects.filter(clase__materia=materia).order_by('-fecha', '-horaentrada')
                    data['lecciones'] = lecciones
                    data['materia'] = materia
                    return render(request, "alu_documentos/deberes.html", data)
                except Exception as ex:
                    pass

            if action == 'subirdeberplanificacion':
                try:
                    data['title'] = u'Subir archivo de tarea de planificación'
                    data['miplanificacion'] = MateriaAsignadaPlanificacion.objects.get(pk=request.GET['id'])
                    data['form'] = ArchivoPlanificacionForm()
                    return render(request, "alu_documentos/subirdeberplanificacionall.html", data)
                except Exception as ex:
                    pass

            if action == 'deldeberplanificacion':
                try:
                    data['title'] = u'Eliminar deber de planificación'
                    data['miplanificacion'] = MateriaAsignadaPlanificacion.objects.get(pk=request.GET['id'])
                    return render(request, "alu_documentos/deldeberplanificacion.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Descarga de documentos'
            data['matricula'] = matricula = inscripcion.ultima_matricula()
            if not matricula:
                return HttpResponseRedirect("/?info=Ud. no se encuentra matriculado")
            data['materiasasignadas'] = matricula.materiaasignada_set.all()
            data['usa_planificacion'] = USA_PLANIFICACION
            return render(request, "alu_documentos/viewall.html", data)