# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from sga.templatetags.sga_extras import encrypt

from decorators import secure_module, last_access
from posgrado.forms import CoordinacionImagenesForm
from sga.commonviews import adduserdata
from sga.forms import CoordinacionForm, ResponsableCoordinacionForm, ResponsableCarreraForm, RepresentanteForm, \
    ResponsableCarrera2Form
from sga.funciones import log, puede_realizar_accion, generar_nombre
from sga.models import Sede, Coordinacion, CoordinacionImagenes, ResponsableCoordinacion, CoordinadorCarrera, Carrera, RepresentantesFacultad, Profesor, Administrativo, ActividadConvalidacionPPV


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    data['periodo'] = periodo = request.session['periodo']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'add':
                try:
                    f = CoordinacionForm(request.POST)
                    if f.is_valid():
                        if not f.cleaned_data['carrera']:
                            return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar al menos una carrera"})
                        coordinacion = Coordinacion(nombre=f.cleaned_data['nombre'],
                                                    sede=f.cleaned_data['sede'],
                                                    alias=f.cleaned_data['alias'])
                        coordinacion.save(request)
                        for carr in f.cleaned_data['carrera']:
                            coordinacion.carrera.add(carr)
                        lista = [x.id for x in coordinacion.carrera.all()]
                        for coord in coordinacion.sede.coordinacion_set.exclude(id=coordinacion.id):
                            if coord.carrera.filter(id__in=lista).exists():
                                transaction.set_rollback(True)
                                return JsonResponse({"result": "bad", "mensaje": u"Su sede ya posee una coordinacion con esta carrera"})
                        log(u'Adicionada coordinacion: %s' % coordinacion, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editar':
                try:
                    f = CoordinacionForm(request.POST)
                    if f.is_valid():
                        if not f.cleaned_data['carrera']:
                            return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar al menos una carrera"})
                        coordinacion = Coordinacion.objects.get(pk=request.POST['id'])
                        coordinacion.nombre = f.cleaned_data['nombre']
                        coordinacion.nombreantiguo = f.cleaned_data['nombreantiguo']
                        coordinacion.alias = f.cleaned_data['alias']
                        coordinacion.save(request)
                        for carrera in  f.cleaned_data['carrera']:
                            coordinacion.carrera.add(carrera)

                        lista = [x.id for x in coordinacion.carrera.all()]
                        for coord in coordinacion.sede.coordinacion_set.exclude(id=coordinacion.id):
                            if coord.carrera.filter(id__in=lista).exists():
                                transaction.set_rollback(True)
                                return JsonResponse({"result": "bad", "mensaje": u"Su sede ya posee una coordinacion con esta carrera"})
                        log(u'Modifico coordinacion: %s' % coordinacion, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'eliminar':
                try:
                    coordinacion = Coordinacion.objects.get(pk=request.POST['id'])
                    if coordinacion.cantidad_niveles():
                        return JsonResponse({"result": "bad", "mensaje": u"Existen niveles registrados."})
                    log(u'Elimino coordinacion: %s' % coordinacion, request, "del")
                    coordinacion.delete()
                    return JsonResponse({"result": "ok", "id": coordinacion.id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'responsable':
                try:
                    coordinacion = Coordinacion.objects.get(pk=request.POST['id'])
                    form = ResponsableCoordinacionForm(request.POST)
                    if form.is_valid():
                        coordinador = coordinacion.responsable_periododos(periodo, request.POST['tipo'])
                        if coordinador:
                            coordinador.persona = form.cleaned_data['responsable']
                            coordinador.save(request)
                            coordinador.tipo = form.cleaned_data['tipo']
                            coordinador.save(request)
                        else:
                            coordinador = ResponsableCoordinacion(coordinacion=coordinacion,
                                                                  periodo=periodo,
                                                                  persona=form.cleaned_data['responsable'],
                                                                  tipo=form.cleaned_data['tipo'])
                            coordinador.save(request)
                        log(u'Modifico responsable de coordinacion: %s' % coordinacion, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'addresponsablecarrera':
                try:
                    coordinacion = Coordinacion.objects.get(pk=request.POST['idc'])
                    carrera = Carrera.objects.get(pk=request.POST['id'])
                    periodo = request.session['periodo']
                    f = ResponsableCarreraForm(request.POST)
                    if f.is_valid():
                        if CoordinadorCarrera.objects.filter(persona=f.cleaned_data['responsable'], carrera=carrera, periodo=periodo, sede=coordinacion.sede).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Responsable duplicado."})
                        responsable = CoordinadorCarrera(persona=f.cleaned_data['responsable'],
                                                         carrera=carrera,
                                                         periodo=periodo,
                                                         sede=coordinacion.sede)
                        responsable.save(request)
                        log(u'Adicionado responsable de carrera: %s' % responsable, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            if action == 'addresponsablecarrera2':
                try:
                    coordinacion = Coordinacion.objects.get(pk=request.POST['idc'])
                    carrera = Carrera.objects.get(pk=request.POST['id'])
                    periodo = request.session['periodo']
                    f = ResponsableCarrera2Form(request.POST)
                    if f.is_valid():
                        # if CoordinadorCarrera.objects.filter(persona=f.cleaned_data['responsable'], carrera=carrera, periodo=periodo, sede=coordinacion.sede).exists():
                        #     return JsonResponse({"result": "bad", "mensaje": u"Responsable duplicado."})
                        responsable = CoordinadorCarrera(persona=f.cleaned_data['responsable'],
                                                         carrera=carrera,
                                                         periodo=periodo,
                                                         sede=coordinacion.sede,
                                                         tipo=f.cleaned_data['tipo'])
                        responsable.save(request)
                        log(u'Adicionado responsable de carrera: %s' % responsable, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'delresponsablecarrera':
                try:
                    coordinador = CoordinadorCarrera.objects.get(pk=request.POST['id'])
                    log(u'Elimino responsable de carrera: %s' % coordinador, request, "del")
                    coordinador.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'editresponsablecarrera_2':
                try:
                    responsable = CoordinadorCarrera.objects.get(pk=request.POST['id'])
                    f = ResponsableCarreraForm(request.POST)
                    if f.is_valid():
                        if CoordinadorCarrera.objects.filter(persona=f.cleaned_data['responsable'], carrera=responsable.carrera, periodo=responsable.periodo, sede=responsable.sede).exclude(id=responsable.id).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Responsable duplicado."})

                        responsable.persona = f.cleaned_data['responsable']
                        responsable.save(request)
                        log(u'Modifico responsable de carrera: %s' % responsable, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editresponsablecarrera':
                try:
                    responsable = CoordinadorCarrera.objects.get(pk=request.POST['id'])
                    f = ResponsableCarreraForm(request.POST)
                    if f.is_valid():
                        if CoordinadorCarrera.objects.filter(persona=f.cleaned_data['responsable'], carrera=responsable.carrera, periodo=responsable.periodo, sede=responsable.sede).exclude(id=responsable.id).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Responsable duplicado."})


                        if ActividadConvalidacionPPV.objects.values('id').filter(status=True, estado__in=[1, 2, 3, 4, 5, 7, 8], director=responsable.persona).exists():
                            actividadextra = ActividadConvalidacionPPV.objects.filter(status=True, estado__in=[1, 2, 3, 4, 5, 7, 8], director=responsable.persona)
                            for act in actividadextra:
                                carr = act.carrera.all()
                                for c in carr:
                                    if c == responsable.carrera:
                                        act.director = f.cleaned_data['responsable']
                                        act.save(request)

                        responsable.persona = f.cleaned_data['responsable']
                        responsable.save(request)
                        log(u'Modifico responsable de carrera: %s' % responsable, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'addrepresentante':
                try:
                    form = RepresentanteForm(request.POST)
                    if form.is_valid():
                        coor = Coordinacion.objects.get(pk=request.POST['id'], status=True)
                        representantesuplentedocente = None
                        representantedocente = None
                        representanteservidores = None
                        if int(request.POST['representantedocente']) > 0:
                            representantedocente = Profesor.objects.get(pk=int(request.POST['representantedocente']))
                        else:
                            if int(request.POST['representantesuplentedocente']) > 0:
                                representantesuplentedocente = Profesor.objects.get(pk=int(request.POST['representantesuplentedocente']))
                        if int(request.POST['representanteservidores']) > 0:
                            representanteservidores = Administrativo.objects.get(pk=int(request.POST['representanteservidores']))
                        responsable = RepresentantesFacultad(facultad=coor,
                                                             representanteestudiantil_id=request.POST['representanteestudiantil'] if int(request.POST['representanteestudiantil']) > 0 else None,
                                                             representantedocente_id=representantedocente.persona.id if representantedocente else None,
                                                             representantesuplentedocente_id=representantesuplentedocente.persona.id if representantesuplentedocente else None,
                                                             representanteservidores_id=representanteservidores.persona.id if representanteservidores else None
                                                             )
                        responsable.save(request)
                        log(u'Adiciono representantes ha la facultad: %s' % responsable, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'addlistadoimagenes':
                try:
                    form = CoordinacionImagenesForm(request.POST)
                    coor = Coordinacion.objects.get(pk=request.POST['id'], status=True)
                    if form.is_valid():
                        coordinacionimg = CoordinacionImagenes(coordinacion=coor,
                                                               tipoimagen=form.cleaned_data['tipoimagen'],
                                                               tipoimagennombre=form.cleaned_data['tipoimagennombre'],
                                                               imagen=request.FILES['imagen'])
                        coordinacionimg.save(request)
                        log(u'Adiciono nuevo Imagen: %s' % coordinacionimg, request, "addlistadoimagenes")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editlistadoimagenes':
                try:
                    form = CoordinacionImagenesForm(request.POST)
                    coordi = CoordinacionImagenes.objects.get(pk=request.POST['id'])
                    newfile = None
                    if 'imagen' in request.FILES:
                        newfile = request.FILES['imagen']
                        if newfile:
                            if newfile.size > 5242880:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 5Mb."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.png' or ext == '.PNG' or ext == '.jpg' or ext == '.JPG' or ext == '.jpeg' or ext == '.JPEG':
                                    newfile._name = generar_nombre("coordinacionimagen_", newfile._name)
                                else:
                                    return JsonResponse(
                                        {"result": "bad", "mensaje": u"Error, Solo archivo con extención: PNG, JPG y JPEG "})
                    if form.is_valid():
                        coordi.tipoimagen = form.cleaned_data['tipoimagen']
                        coordi.tipoimagennombre = form.cleaned_data['tipoimagennombre']
                        coordi.imagen = form.cleaned_data['imagen']
                        if newfile:
                            coordi.imagen = newfile
                        coordi.save(request)
                        log(u'Editó la Imagen: %s' % coordi, request, "editlistadoimagenes")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editrepresentante':
                try:
                    form = RepresentanteForm(request.POST)
                    if form.is_valid():
                        repre = RepresentantesFacultad.objects.get(pk=request.POST['id'], status=True)
                        representantesuplentedocente = None
                        representantedocente = None
                        representanteservidores = None
                        if int(request.POST['representantedocente']) > 0:
                            representantedocente = Profesor.objects.get(pk=int(request.POST['representantedocente']))
                        else:
                            if int(request.POST['representantesuplentedocente']) > 0:
                                representantesuplentedocente = Profesor.objects.get(pk=int(request.POST['representantesuplentedocente']))
                        if int(request.POST['representanteservidores']) > 0:
                            representanteservidores = Administrativo.objects.get(pk=int(request.POST['representanteservidores']))
                        repre.representanteestudiantil_id = request.POST['representanteestudiantil'] if int(request.POST['representanteestudiantil']) > 0 else None
                        repre.representantedocente_id = representantedocente.persona.id if representantedocente else None
                        repre.representantesuplentedocente_id = representantesuplentedocente.persona.id if representantesuplentedocente else None
                        repre.representanteservidores_id = representanteservidores.persona.id if representanteservidores else None
                        repre.save(request)
                        log(u'Editó representantes de la facultad: %s' % repre, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Coordinaciones de la Institución'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_coordinaciones')
                    data['title'] = u'Adicionar de coordinación'
                    data['form'] = CoordinacionForm()
                    return render(request, "adm_coordinaciones/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'editar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_coordinaciones')
                    data['title'] = u'Editar de coordinación'
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['id'])
                    form = CoordinacionForm(initial={'nombre': coordinacion.nombre,
                                                     'sede': coordinacion.sede,
                                                     'nombreantiguo': coordinacion.nombreantiguo,
                                                     'carrera': coordinacion.carrera.all(),
                                                     'alias': coordinacion.alias})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_coordinaciones/editar.html", data)
                except Exception as ex:
                    pass

            if action == 'eliminar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_coordinaciones')
                    data['title'] = u'Eliminar de coordinación'
                    data['coordinacion'] = Coordinacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_coordinaciones/eliminar.html", data)
                except Exception as ex:
                    pass

            if action == 'responsable':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_coordinaciones')
                    if request.GET['tipo'] == '1':
                        data['title'] = u'Responsable de coordinación'
                    if request.GET['tipo'] == '2':
                        data['title'] = u'Responsable de subcoordinación'
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['id'])
                    responsable = coordinacion.responsable_periododos(periodo, request.GET['tipo'])
                    if responsable:
                        form = ResponsableCoordinacionForm(initial={'responsable': responsable.persona,
                                                                    'tipo': responsable.tipo})
                    else:
                        form = ResponsableCoordinacionForm(initial={'tipo': request.GET['tipo']})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_coordinaciones/responsable.html", data)
                except Exception as ex:
                    pass

            if action == 'addresponsablecarrera':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_coordinaciones')
                    data['title'] = u'Establecer responsable de carrera'
                    data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['id'])
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['idc'])
                    form = ResponsableCarreraForm()
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_coordinaciones/addresponsablecarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'addresponsablecarrera2':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_coordinaciones')
                    data['title'] = u'Establecer responsable de carrera'
                    data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['id'])
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['idc'])
                    form = ResponsableCarrera2Form()
                    data['form'] = form
                    return render(request, "adm_coordinaciones/addresponsablecarrera2.html", data)
                except Exception as ex:
                    pass

            if action == 'delresponsablecarrera':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_coordinaciones')
                    data['responsable'] = CoordinadorCarrera.objects.get(pk=request.GET['id'])
                    return render(request, "adm_coordinaciones/delresponsablecarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'editresponsablecarrera':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_coordinaciones')
                    data['title'] = u'Editar responsable de carrera'
                    data['responsable'] = responsable = CoordinadorCarrera.objects.get(pk=request.GET['id'])
                    form = ResponsableCarreraForm(initial={'responsable': responsable.persona})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_coordinaciones/editresponsablecarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'representantes':
                try:
                    data['title'] = u'Representantes de facultad'
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['id'])
                    data['representantes'] = coordinacion.representantesfacultad_set.filter(status=True)
                    return render(request, "adm_coordinaciones/representantes.html", data)
                except Exception as ex:
                    pass

            if action == 'listadoimagenes':
                try:
                    data['title'] = u'Listado de Imagenes'
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['id'])
                    data['listadoimagenes'] = coordinacion.coordinacionimagenes_set.filter(status=True)
                    return render(request, "adm_coordinaciones/listadoimagenes.html", data)
                except Exception as ex:
                    pass

            if action == 'deletelistadoimagenes':
                try:
                    with transaction.atomic():
                        id = request.POST['id']
                        coordinacionimagenes = CoordinacionImagenes.objects.get(pk=id)
                        coordinacionimagenes.delete()
                        log(u'Elimino Imagen: %s' % coordinacionimagenes, request, "deletelistadoimagenes")
                        res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            if action == 'addrepresentante':
                try:
                    data['title'] = u'Adicionar representantes'
                    data['coordinacion'] = Coordinacion.objects.get(pk=request.GET['id'])
                    data['form'] = RepresentanteForm()
                    return render(request, "adm_coordinaciones/addrepresentante.html", data)
                except Exception as ex:
                    pass

            if action == 'addlistadoimagenes':
                try:
                    data['coordinacion'] = Coordinacion.objects.get(pk=request.GET['id'])
                    form = CoordinacionImagenesForm()
                    data['form'] = form
                    template = get_template("adm_coordinaciones/addlistadoimagenes.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            # GET
            if action == 'editlistadoimagenes':
                try:
                    data['title'] = u'Editar Requisito'
                    data['coordimagen'] = coordi = CoordinacionImagenes.objects.get(pk=request.GET['id'], status=True)
                    data['id'] = request.GET['id']
                    data['form'] = CoordinacionImagenesForm(initial={'tipoimagen': coordi.tipoimagen,
                                                          'tipoimagennombre': coordi.tipoimagennombre,
                                                          'imagen': coordi.imagen})
                    template = get_template("adm_coordinaciones/editlistadoimagenes.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editrepresentante':
                try:
                    data['title'] = u'Editar representantes'
                    data['representante'] = repre = RepresentantesFacultad.objects.get(pk=request.GET['id'])
                    if repre.representanteestudiantil_id in [None, '', 0]:
                        data['idrepresentanteestudiantil'] = idrepresentanteestudiantil = 0
                    else:
                        data['idrepresentanteestudiantil'] = idrepresentanteestudiantil = repre.representanteestudiantil.id
                    if repre.representantedocente_id in [None, '', 0]:
                        data['idrepresentantedocente'] = idrepresentantedocente = 0
                    else:
                        data['idrepresentantedocente'] = idrepresentantedocente = repre.representantedocente.profesor().id if repre.representantedocente.profesor() else 0
                    if repre.representantesuplentedocente_id in [None, '', 0]:
                        data['idrepresentantesuplentedocente'] = idrepresentantesuplentedocente = 0
                    else:
                        data['idrepresentantesuplentedocente'] = idrepresentantesuplentedocente = repre.representantesuplentedocente.profesor().id
                    if repre.representanteservidores_id in [None, '', 0]:
                        data['idrepresentanteservidores'] = idrepresentanteservidores = 0
                    else:
                        data['idrepresentanteservidores'] = idrepresentanteservidores = repre.representanteservidores.administrativo().id
                    data['form'] = RepresentanteForm({'representanteestudiantil': idrepresentanteestudiantil,
                                                      'representantedocente': idrepresentantedocente,
                                                      'representantesuplentedocente': idrepresentantesuplentedocente,
                                                      'representanteservidores': idrepresentanteservidores
                                                      })
                    return render(request, "adm_coordinaciones/editrepresentante.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['sedes'] = Sede.objects.all()
            coordinaciones = periodo.nivel_set.values_list('nivellibrecoordinacion__coordinacion_id').filter(status=True)
            coordina1 = Coordinacion.objects.filter(pk__in=coordinaciones).order_by('nombre')
            coordina2 = Coordinacion.objects.filter(pk=11).order_by('nombre')
            data['listadocoordinaciones'] = coordina1 | coordina2
            return render(request, "adm_coordinaciones/view.html", data)
