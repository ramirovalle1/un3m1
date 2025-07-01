# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import last_access
from settings import ALUMNOS_GROUP_ID
from sga.commonviews import adduserdata
from sga.forms import SeguimientoEstudianteForm, EstudioInscripcionBasicoForm, IdiomaDominaForm, EstudioInscripcionSuperiorForm
from sga.funciones import log, MiPaginador
from sga.models import SeguimientoEstudiante, EstudioInscripcion, IdiomaDomina, Persona


@login_required(redirect_field_name='ret', login_url='/loginsga')
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addtrabajo':
            try:
                persona = Persona.objects.get(pk=request.POST['id'])
                form = SeguimientoEstudianteForm(request.POST)
                if form.is_valid():
                    if not form.cleaned_data['labora']:
                        if form.cleaned_data['fecha'] >= form.cleaned_data['fechafin']:
                            return JsonResponse({'result': 'bad', 'mensaje': u'Error: La fecha fin es menor o igual a la fecha de inicio'})
                    seguimiento = SeguimientoEstudiante(persona=persona,
                                                        empresa=form.cleaned_data['empresa'],
                                                        industria=form.cleaned_data['industria'],
                                                        cargo=form.cleaned_data['cargo'],
                                                        ocupacion=form.cleaned_data['ocupacion'],
                                                        responsabilidades=form.cleaned_data['responsabilidades'],
                                                        telefono=form.cleaned_data['telefono'],
                                                        email=form.cleaned_data['email'],
                                                        sueldo=form.cleaned_data['sueldo'],
                                                        ejerce=form.cleaned_data['ejerce'],
                                                        fecha=form.cleaned_data['fecha'])
                    if not form.cleaned_data['labora']:
                        seguimiento.fechafin = form.cleaned_data['fechafin']
                    seguimiento.save(request)
                    log(u"Adiciono seguimiento estudiante: %s" % persona, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar datos'})

        elif action == 'editidioma':
            try:
                idioma = IdiomaDomina.objects.get(pk=request.POST['id'])
                form = IdiomaDominaForm(request.POST)
                if form.is_valid():
                    idioma.idioma = form.cleaned_data['idioma']
                    idioma.lectura = form.cleaned_data['lectura']
                    idioma.escritura = form.cleaned_data['escritura']
                    idioma.save(request)
                    log(u"Editó idioma del estudiante: %s" % idioma, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos datos'})

        elif action == 'editestudiosuperior':
            try:
                estudio = EstudioInscripcion.objects.get(pk=request.POST['id'])
                form = EstudioInscripcionSuperiorForm(request.POST)
                if form.is_valid():
                    estudio.universidad = form.cleaned_data['superiores']
                    estudio.carrera = form.cleaned_data['carrera']
                    estudio.titulo = form.cleaned_data['titulo']
                    estudio.anoestudio = form.cleaned_data['anoestudio']
                    estudio.graduado = form.cleaned_data['graduado']
                    estudio.registro = form.cleaned_data['registro']
                    estudio.estudiosposteriores = form.cleaned_data['posteriores']
                    estudio.incorporacion = form.cleaned_data['incorporacion']
                    estudio.save(request)
                    log(u"Editó estudio superior del estudiante: %s" % estudio, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'editestudio':
            try:
                estudio = EstudioInscripcion.objects.get(pk=request.POST['id'])
                form = EstudioInscripcionBasicoForm(request.POST)
                if form.is_valid():
                    estudio.colegio = form.cleaned_data['colegio']
                    estudio.incorporacion = form.cleaned_data['incorporacion']
                    estudio.especialidad = form.cleaned_data['especialidad']
                    estudio.graduado = True
                    estudio.save(request)
                    log(u"Editó estudio del estudiante: %s" % estudio, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'delidioma':
            try:
                idioma = IdiomaDomina.objects.get(pk=request.POST['id'])
                log(u"Elimino idioma que domina: %s" % idioma, request, "del")
                idioma.delete()
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al eliminar los datos'})

        elif action == 'delestudio':
            try:
                estudio = EstudioInscripcion.objects.get(pk=request.POST['id'])
                log(u'Elimino estudio: %s' % estudio, request, "del")
                estudio.delete()
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al eliminar los datos'})

        if action == 'edittrabajo':
            try:
                trabajo = SeguimientoEstudiante.objects.get(pk=request.POST['id'])
                form = SeguimientoEstudianteForm(request.POST)
                if form.is_valid():
                    if not form.cleaned_data['labora']:
                        if form.cleaned_data['fecha'] >= form.cleaned_data['fechafin']:
                            return JsonResponse({'result': 'bad', 'mensaje': u'Error: La fecha fin es menor o igual a la fecha de inicio'})
                    trabajo.empresa = form.cleaned_data['empresa']
                    trabajo.industria = form.cleaned_data['industria']
                    trabajo.cargo = form.cleaned_data['cargo']
                    trabajo.ocupacion = form.cleaned_data['ocupacion']
                    trabajo.responsabilidades = form.cleaned_data['responsabilidades']
                    trabajo.telefono = form.cleaned_data['telefono']
                    trabajo.email = form.cleaned_data['email']
                    trabajo.sueldo = form.cleaned_data['sueldo']
                    trabajo.ejerce = form.cleaned_data['ejerce']
                    trabajo.fecha = form.cleaned_data['fecha']
                    if not form.cleaned_data['labora']:
                        trabajo.fechafin = form.cleaned_data['fechafin']
                    else:
                        trabajo.fechafin = None
                    trabajo.save(request)
                    log(u'Modifico seguimiento laboral de estudiante: %s' % trabajo, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'deltrabajo':
            try:
                trabajo = SeguimientoEstudiante.objects.get(pk=request.POST['id'])
                log(u'Elimino seguimiento laboral estudiante: %s' % trabajo, request, "del")
                trabajo.delete()
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al eliminar los datos'})

        elif action == 'addidioma':
            try:
                persona = Persona.objects.get(pk=request.POST['id'])
                form = IdiomaDominaForm(request.POST)
                if form.is_valid():
                    idioma = IdiomaDomina(persona=persona,
                                          idioma=form.cleaned_data['idioma'],
                                          lectura=form.cleaned_data['lectura'],
                                          escritura=form.cleaned_data['escritura'])
                    idioma.save(request)
                    log(u'Adiciono idioma que domina: %s' % idioma, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'addestudiosuperior':
            try:
                persona = Persona.objects.get(pk=request.POST['id'])
                form = EstudioInscripcionSuperiorForm(request.POST)
                if form.is_valid():
                    estudio = EstudioInscripcion(persona=persona,
                                                 universidad=form.cleaned_data['superiores'],
                                                 carrera=form.cleaned_data['carrera'],
                                                 titulo=form.cleaned_data['titulo'],
                                                 anoestudio=form.cleaned_data['anoestudio'],
                                                 graduado=form.cleaned_data['graduado'],
                                                 estudiosposteriores=form.cleaned_data['posteriores'],
                                                 registro=form.cleaned_data['registro'],
                                                 incorporacion=form.cleaned_data['incorporacion'])
                    estudio.save(request)
                    log(u'Adiciono estudio superior de inscripcion: %s' % estudio, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'addestudio':
            try:
                persona = Persona.objects.get(pk=request.POST['id'])
                form = EstudioInscripcionBasicoForm(request.POST)
                if form.is_valid():
                    estudio = EstudioInscripcion(persona=persona,
                                                 colegio=form.cleaned_data['colegio'],
                                                 incorporacion=form.cleaned_data['incorporacion'],
                                                 especialidad=form.cleaned_data['especialidad'],
                                                 graduado=True)
                    estudio.save(request)
                    log(u'Adiciono estudio basicos de inscripcion: %s' % estudio, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Listado de egresados'
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'edittrabajo':
                try:
                    data['title'] = u'Editar seguimiento laboral del estudiante'
                    data['trabajo'] = trabajo = SeguimientoEstudiante.objects.get(pk=request.GET['id'])
                    data['form'] = SeguimientoEstudianteForm(initial={'empresa': trabajo.empresa,
                                                                      'industria': trabajo.industria,
                                                                      'cargo': trabajo.cargo,
                                                                      'ocupacion': trabajo.ocupacion,
                                                                      'responsabilidades': trabajo.responsabilidades,
                                                                      'telefono': trabajo.telefono,
                                                                      'email': trabajo.email,
                                                                      'sueldo': trabajo.sueldo,
                                                                      'ejerce': trabajo.ejerce,
                                                                      'labora': False if trabajo.fechafin else True,
                                                                      'fecha': trabajo.fecha,
                                                                      'fechafin': trabajo.fechafin})
                    return render(request, "seguimiento/edittrabajo.html", data)
                except Exception as ex:
                    pass

            elif action == 'deltrabajo':
                try:
                    data['title'] = u'Borrar seguimiento laboral del estudiante'
                    data['trabajo'] = SeguimientoEstudiante.objects.get(pk=request.GET['id'])
                    return render(request, "seguimiento/deltrabajo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addtrabajo':
                try:
                    data['title'] = u'Adicionar seguimiento laboral'
                    data['seguimiento'] = Persona.objects.get(pk=request.GET['id'])
                    data['form'] = SeguimientoEstudianteForm(initial={'fecha': datetime.now().date(),
                                                                      'labora': True})
                    return render(request, "seguimiento/addtrabajo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addestudio':
                try:
                    data['title'] = u'Adicionar estudios básicos'
                    data['seguimiento'] = Persona.objects.get(pk=request.GET['id'])
                    data['form'] = EstudioInscripcionBasicoForm(initial={'incorporacion': datetime.now().date().year})
                    return render(request, "seguimiento/addestudio.html", data)
                except Exception as ex:
                    pass

            elif action == 'addestudiosuperior':
                try:
                    data['title'] = u'Adicionar estudios superiores'
                    data['seguimiento'] = Persona.objects.get(pk=request.GET['id'])
                    data['form'] = EstudioInscripcionSuperiorForm(initial={'incorporacion': datetime.now().date().year,
                                                                           'anoestudio': 0,
                                                                           'posteriores': True,
                                                                           'graduado': True})

                    return render(request, "seguimiento/addestudiosuperior.html", data)
                except Exception as ex:
                    pass

            elif action == 'addidioma':
                try:
                    data['title'] = u'Adicionar estudios de idiomas realizados'
                    data['seguimiento'] = Persona.objects.get(pk=request.GET['id'])
                    data['form'] = IdiomaDominaForm()
                    return render(request, "seguimiento/addidioma.html", data)
                except Exception as ex:
                    pass

            elif action == 'editidioma':
                try:
                    data['title'] = u'Editar Idioma'
                    idioma = IdiomaDomina.objects.get(pk=request.GET['id'])
                    data['form'] = IdiomaDominaForm(initial={'idioma': idioma.idioma,
                                                             'escritura': idioma.escritura,
                                                             'lectura': idioma.lectura})
                    data['idioma'] = idioma
                    return render(request, "seguimiento/editidioma.html", data)
                except Exception as ex:
                    pass

            elif action == 'editestudiosuperior':
                try:
                    data['title'] = u'Editar estudios superiores realizados'
                    data['estudio'] = estudio = EstudioInscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = EstudioInscripcionSuperiorForm(initial={'incorporacion': estudio.incorporacion,
                                                                           'superiores': estudio.universidad,
                                                                           'carrera': estudio.carrera,
                                                                           'titulo': estudio.titulo,
                                                                           'anoestudio': estudio.anoestudio,
                                                                           'registro': estudio.registro,
                                                                           'posteriores': estudio.estudiosposteriores,
                                                                           'graduado': estudio.graduado})
                    data['seguimiento'] = estudio.persona
                    return render(request, "seguimiento/editestudiosuperior.html", data)
                except Exception as ex:
                    pass

            elif action == 'editestudio':
                try:
                    data['title'] = u'Editar Estudios Básicos Realizados'
                    data['estudio'] = estudio = EstudioInscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = EstudioInscripcionBasicoForm(initial={'colegio': estudio.colegio,
                                                                         'incorporacion': estudio.incorporacion,
                                                                         'especialidad': estudio.especialidad})
                    data['seguimiento'] = estudio.persona
                    return render(request, "seguimiento/editestudio.html", data)
                except Exception as ex:
                    pass

            elif action == 'delidioma':
                try:
                    data['title'] = u'Eliminar idioma'
                    data['idioma'] = idioma = IdiomaDomina.objects.get(pk=request.GET['id'])
                    data['seguimiento'] = idioma.persona
                    return render(request, "seguimiento/delidioma.html", data)
                except Exception as ex:
                    pass

            elif action == 'delestudio':
                try:
                    data['title'] = u'Eliminar estudios realizados'
                    data['estudio'] = estudio = EstudioInscripcion.objects.get(pk=request.GET['id'])
                    data['seguimiento'] = estudio.persona
                    return render(request, "seguimiento/delestudio.html", data)
                except Exception as ex:
                    pass

            elif action == 'estudio':
                try:
                    data['title'] = u'Estudios realizados por el alumno'
                    data['seguimiento'] = persona = Persona.objects.get(pk=request.GET['id'])
                    data['estudios'] = persona.estudioinscripcion_set.all().order_by('-incorporacion')
                    data['idiomas'] = persona.idiomadomina_set.all().order_by('idioma')
                    return render(request, "seguimiento/estudio.html", data)
                except Exception as ex:
                    pass

            elif action == 'trabajo':
                try:
                    data['title'] = u'Actividad Laboral del alumno'
                    data['seguimiento'] = persona = Persona.objects.get(pk=request.GET['id'])
                    data['trabajos'] = persona.seguimientoestudiante_set.all().order_by('-fecha')
                    return render(request, "seguimiento/trabajo.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Seguimiento de estudiantes'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                if len(ss) == 1:
                    personal = Persona.objects.filter(Q(nombres__icontains=search) |
                                                      Q(apellido1__icontains=search) |
                                                      Q(apellido2__icontains=search) |
                                                      Q(cedula__icontains=search) |
                                                      Q(pasaporte__icontains=search) |
                                                      Q(inscripcion__identificador__icontains=search) |
                                                      Q(inscripcion__inscripciongrupo__grupo__nombre__icontains=search) |
                                                      Q(inscripcion__carrera__nombre__icontains=search), usuario__groups__id__in=[ALUMNOS_GROUP_ID]).distinct()
                else:
                    personal = Persona.objects.filter(Q(apellido1__icontains=ss[0]) &
                                                      Q(apellido2__icontains=ss[1]), usuario__groups__id__in=[ALUMNOS_GROUP_ID]).distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                personal = Persona.objects.filter(id=ids, usuario__groups__id__in=[ALUMNOS_GROUP_ID]).distinct()
            else:
                personal = Persona.objects.filter(usuario__groups__id__in=[ALUMNOS_GROUP_ID]).distinct()
            paging = MiPaginador(personal, 25)
            p = 1
            try:
                paginasesion = 1
                if 'paginador' in request.session:
                    paginasesion = int(request.session['paginador'])
                if 'page' in request.GET:
                    p = int(request.GET['page'])
                else:
                    p = paginasesion
                try:
                    page = paging.page(p)
                except:
                    p = 1
                page = paging.page(p)
            except:
                page = paging.page(p)
            request.session['paginador'] = p
            data['paging'] = paging
            data['rangospaging'] = paging.rangos_paginado(p)
            data['page'] = page
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['personal'] = page.object_list
            return render(request, "seguimiento/view.html", data)