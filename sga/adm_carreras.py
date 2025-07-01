# -*- coding: latin-1 -*-
from django.template.context import Context
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import CarreraForm, CostoInscripcionCarrera, CarreraPrincipalForm, TipoFormacionCarreraForm, \
    EnteAprobadorCarreraForm
from sga.funciones import MiPaginador, log, puede_realizar_accion, generar_nombre
from sga.models import Carrera, CarreraGrupo, TipoFormacionCarrera, TituloInstitucion, EnteAprobadorCarrera
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                newfile = None
                resolucionies = None
                proyecto = None
                f = CarreraForm(request.POST)

                if 'resolucion' in request.FILES:
                    arch = request.FILES['resolucion']
                    extencion = arch._name.split('.')
                    exte = extencion[extencion.__len__()-1]
                    if arch.size > 153600000:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 150Mb."})
                    if not exte == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})

                if 'resolucionies' in request.FILES:
                    arch = request.FILES['resolucionies']
                    extencion = arch._name.split('.')
                    exte = extencion[extencion.__len__()-1]
                    if arch.size > 153600000:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 150Mb."})
                    if not exte == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})

                if 'archivoproyecto' in request.FILES:
                    arch = request.FILES['archivoproyecto']
                    extencion = arch._name.split('.')
                    exte = extencion[extencion.__len__() - 1]
                    if arch.size > 153600000:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 150Mb."})
                    if not exte == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})

                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if 'resolucion' in request.FILES:
                    newfile = request.FILES['resolucion']
                    newfile._name = generar_nombre("resolucion_", newfile._name)
                if 'resolucionies' in request.FILES:
                    resolucionies = request.FILES['resolucionies']
                    resolucionies._name = generar_nombre("resolucionIES_", resolucionies._name)
                if 'archivoproyecto' in request.FILES:
                    proyecto = request.FILES['archivoproyecto']
                    proyecto._name = generar_nombre("proyecto", proyecto._name)
                carrera = Carrera(nombre=f.cleaned_data['nombre'],
                                  nombrevisualizar=f.cleaned_data['nombre'],
                                  mencion=f.cleaned_data['mencion'],
                                  alias=f.cleaned_data['alias'],
                                  activa=f.cleaned_data['activa'],
                                  niveltitulacion=f.cleaned_data['niveltitulacion'],
                                  tituloobtenidohombre=f.cleaned_data['tituloobtenidohombre'],
                                  tituloobtenidomujer=f.cleaned_data['tituloobtenidomujer'],
                                  carreragrupo_id=int(request.POST['carreragrupo']) if request.POST['carreragrupo'] else None,
                                  titulootorga=f.cleaned_data['titulootorga'],
                                  modalidad=f.cleaned_data['modalidad'],
                                  numeroresolucion=f.cleaned_data['numeroresolucion'],
                                  resolucion=newfile,
                                  resolucionies=resolucionies,
                                  fechaaprobacion=f.cleaned_data['fechaaprobacion'],
                                  anovigencia=f.cleaned_data['anovigencia'],
                                  misioncarrera=f.cleaned_data['misioncarrera'],
                                  objetivocarrera=f.cleaned_data['objetivocarrera'],
                                  perfilprofesional=f.cleaned_data['perfilprofesional'],
                                  perfilegreso=f.cleaned_data['perfilegreso'],
                                  campoocupacional=f.cleaned_data['campoocupacional'],
                                  camporotacion=f.cleaned_data['camporotacion'],
                                  tipo=f.cleaned_data['tipo'],
                                  codigo=f.cleaned_data['codigo'],
                                  fechacreacioncarrera=f.cleaned_data['fechacreacioncarrera'],
                                  codigoresolucionies=f.cleaned_data['codigoresolucionies'],
                                  archivoproyecto=proyecto,
                                  enteaprobadorcarrera=f.cleaned_data['enteaprobadorcarrera'])
                carrera.save(request)
                f.cleaned_data['coordinacion'].carrera.add(carrera)
                log(u'Adiciono carrera: %s' % carrera, request, "add")
                return JsonResponse({"result": "ok", "id": encrypt(carrera.id)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        elif action == 'edit':
            try:
                carrera = Carrera.objects.get(pk=request.POST['id'], status=True)
                f = CarreraForm(request.POST)
                newfile = None
                resolucionies = None
                proyecto = None
                if 'resolucion' in request.FILES:
                    arch = request.FILES['resolucion']
                    extencion = arch._name.split('.')
                    exte = extencion[extencion.__len__()-1]
                    if arch.size > 153600000:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 150Mb."})
                    if not exte == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                    newfile = request.FILES['resolucion']
                    newfile._name = generar_nombre("resolucion_", newfile._name)
                if 'resolucionies' in request.FILES:
                    arch = request.FILES['resolucionies']
                    extencion = arch._name.split('.')
                    exte = extencion[extencion.__len__()-1]
                    if arch.size > 153600000:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 150Mb."})
                    if not exte == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                    resolucionies = request.FILES['resolucionies']
                    resolucionies._name = generar_nombre("resolucionIES_", resolucionies._name)
                if 'archivoproyecto' in request.FILES:
                    arch = request.FILES['archivoproyecto']
                    extencion = arch._name.split('.')
                    exte = extencion[extencion.__len__() - 1]
                    if arch.size > 153600000:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 150Mb."})
                    if not exte == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                    proyecto = request.FILES['archivoproyecto']
                    proyecto._name = generar_nombre("proyecto", proyecto._name)
                if f.is_valid():
                    carrera.nombre = f.cleaned_data['nombre']
                    carrera.nombrevisualizar = f.cleaned_data['nombre']
                    carrera.mencion = f.cleaned_data['mencion']
                    carrera.alias = f.cleaned_data['alias']
                    carrera.activa = f.cleaned_data['activa']
                    carrera.niveltitulacion = f.cleaned_data['niveltitulacion']
                    carrera.tituloobtenidohombre = f.cleaned_data['tituloobtenidohombre']
                    carrera.tituloobtenidomujer = f.cleaned_data['tituloobtenidomujer']
                    carrera.carreragrupo_id = f.cleaned_data['carreragrupo']
                    carrera.titulootorga = f.cleaned_data['titulootorga']
                    carrera.modalidad = f.cleaned_data['modalidad']
                    carrera.numeroresolucion = f.cleaned_data['numeroresolucion']
                    carrera.resolucion = f.cleaned_data['resolucion']
                    carrera.fechaaprobacion = f.cleaned_data['fechaaprobacion']
                    carrera.fechacreacioncarrera = f.cleaned_data['fechacreacioncarrera']
                    carrera.anovigencia = f.cleaned_data['anovigencia']
                    carrera.misioncarrera = f.cleaned_data['misioncarrera']
                    carrera.objetivocarrera = f.cleaned_data['objetivocarrera']
                    carrera.perfilprofesional = f.cleaned_data['perfilprofesional']
                    carrera.perfilegreso = f.cleaned_data['perfilegreso']
                    carrera.campoocupacional = f.cleaned_data['campoocupacional']
                    carrera.camporotacion = f.cleaned_data['camporotacion']
                    carrera.tipo = f.cleaned_data['tipo']
                    carrera.codigo = f.cleaned_data['codigo']
                    carrera.codigoresolucionies = f.cleaned_data['codigoresolucionies']
                    carrera.enteaprobadorcarrera = f.cleaned_data['enteaprobadorcarrera']
                    carrera.abrsustentacion = f.cleaned_data['abrsustentacion']
                    if newfile:
                        carrera.resolucion = newfile
                    if resolucionies:
                        carrera.resolucionies = resolucionies
                    if proyecto:
                        carrera.archivoproyecto = proyecto
                    carrera.save(request)
                    if not f.cleaned_data['coordinacion'].carrera.filter(id=carrera.id):
                        f.cleaned_data['coordinacion'].carrera.add(carrera)
                    log(u'Modifico carrera: %s' % carrera, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'costoinscripcion':
            try:
                carrera = Carrera.objects.get(pk=request.POST['id'], status=True)
                f = CostoInscripcionCarrera(request.POST)
                if f.is_valid():
                    carrera.costoinscripcion = f.cleaned_data['costoinscripcion']
                    carrera.save(request)
                    log(u'Modifico costo de inscripcion carrera: %s' % carrera, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addcarrerap':
            try:
                f = CarreraPrincipalForm(request.POST)
                if f.is_valid():
                    if CarreraGrupo.objects.filter(nombre=f.cleaned_data['nombre']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El grupo de carrera ya se encuentra registrado."})
                    carrera = CarreraGrupo(nombre=f.cleaned_data['nombre'], activa=f.cleaned_data['activa'])
                    carrera.save(request)
                    log(u'Adiciono una carrera principal: %s' % carrera, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcarrerap':
            try:
                f = CarreraPrincipalForm(request.POST)
                if f.is_valid():
                    grupo = CarreraGrupo.objects.get(pk=int(request.POST['id']))
                    if CarreraGrupo.objects.filter(nombre=f.cleaned_data['nombre']).exclude(id=grupo.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El grupo de carrera ya se encuentra registrado."})
                    grupo.nombre=f.cleaned_data['nombre']
                    grupo.activa=f.cleaned_data['activa']
                    grupo.save(request)
                    log(u'Editó una carrera principal: %s' % grupo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delcarrerap':
            try:
                grupo = CarreraGrupo.objects.get(pk=int(request.POST['id']), status=True)
                if not grupo.carrera_set.all().exists():
                    log(u'Eliminó un grupo de carrera principal: %s' % grupo, request, "del")
                    grupo.delete()
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar ya se encuentra en uso."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addenteaprobador':
            try:
                f = EnteAprobadorCarreraForm(request.POST)
                if f.is_valid():
                    if EnteAprobadorCarrera.objects.filter(nombre=f.cleaned_data['nombre']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El registro ya se encuentra registrado."})
                    ente = EnteAprobadorCarrera(nombre=f.cleaned_data['nombre'])
                    ente.save(request)
                    log(u'Adiciono un ente aprobador de carrera: %s' % ente, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editenteaprobador':
            try:
                f = EnteAprobadorCarreraForm(request.POST)
                if f.is_valid():
                    ente = EnteAprobadorCarrera.objects.get(pk=request.POST['id'])
                    if EnteAprobadorCarrera.objects.filter(nombre=f.cleaned_data['nombre']).exclude(id=ente.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El registro ya se encuentra registrado."})
                    ente.nombre=f.cleaned_data['nombre']
                    ente.save(request)
                    log(u'Adiciono ente aprobador de carrera: %s' % ente, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deltipoformacion':
            try:
                ente = EnteAprobadorCarrera.objects.get(pk=int(request.POST['id']), status=True)
                if not ente.en_uso():
                    log(u'Eliminó ente aprobador de carrera principal: %s' % ente, request, "del")
                    ente.delete()
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar ya se encuentra en uso."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'detallecarrera':
            try:
                data['carrera'] = carrera = Carrera.objects.get(pk=request.POST['id'], status=True)
                # data['facultad'] = carrera.coordinacion_set.filter(status=True)[0]
                # data['institucion'] = TituloInstitucion.objects.filter(status=True)[0]
                template = get_template("carreras/detallecarrera.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                pass

        elif action == 'informacioncarrera_pdf':
            try:
                if 'id' in request.POST:
                    data['carrera'] = carrera = Carrera.objects.get(status=True, id=int(request.POST['id']))
                    facultad = []
                    if carrera.coordinacion_set.filter(status=True).exists():
                        facultad = carrera.coordinacion_set.filter(status=True)[0]
                    data['facultad'] = facultad
                    data['institucion'] = TituloInstitucion.objects.filter(status=True)[0]
                    return conviert_html_to_pdf('carreras/informacioncarrera_pdf.html', {'pagesize': 'A4','data': data,})
            except Exception as ex:
                pass

        elif action == 'delcarrera':
            try:
                carrera = Carrera.objects.get(pk=int(request.POST['id']), status=True)
                if not carrera.en_uso():
                    log(u'Eliminó la carrera: %s' % carrera, request, "del")
                    carrera.status = False
                    carrera.save()
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar ya se encuentra en uso."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Carreras'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_carreras')
                    data['title'] = u'Nueva carrera'
                    form = CarreraForm()
                    data['form'] = form
                    return render(request, "carreras/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_carreras')
                    data['title'] = u'Editar carrera'
                    carrera = Carrera.objects.get(pk=int(request.GET['id']), status=True)
                    form = CarreraForm(initial={'nombre': carrera.nombre if not carrera.nombrevisualizar else carrera.nombrevisualizar,
                                                'mencion': carrera.mencion,
                                                'alias': carrera.alias,
                                                'activa': carrera.activa,
                                                'costoinscripcion': carrera.costoinscripcion,
                                                'tipoformacion' : carrera.tipoformacion,
                                                'niveltitulacion' : carrera.niveltitulacion,
                                                'tituloobtenidohombre' : carrera.tituloobtenidohombre,
                                                'tituloobtenidomujer' :carrera.tituloobtenidomujer,
                                                'carreragrupo' :carrera.carreragrupo,
                                                'tipo':carrera.tipo,
                                                'titulootorga' :carrera.titulootorga,
                                                'modalidad' :carrera.modalidad,
                                                'numeroresolucion' :carrera.numeroresolucion,
                                                'enteaprobadorcarrera' :carrera.enteaprobadorcarrera,
                                                'fechaaprobacion' :carrera.fechaaprobacion,
                                                'fechacreacioncarrera' :carrera.fechacreacioncarrera,
                                                'anovigencia' :carrera.anovigencia,
                                                'misioncarrera' :carrera.misioncarrera,
                                                'perfilprofesional' :carrera.perfilprofesional,
                                                'perfilegreso' :carrera.perfilegreso,
                                                'objetivocarrera' :carrera.objetivocarrera,
                                                'campoocupacional' :carrera.campoocupacional,
                                                'camporotacion' :carrera.camporotacion,
                                                'codigo' :carrera.codigo,
                                                'codigoresolucionies': carrera.codigoresolucionies,
                                                'abrsustentacion': carrera.abrsustentacion
                                                })
                    data['carrera'] = carrera
                    data['form'] = form
                    return render(request, "carreras/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'costoinscripcion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_rubros')
                    data['title'] = u'Costo de inscripción'
                    data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['id'], status=True)
                    data['form'] = CostoInscripcionCarrera(initial={'costoinscripcion': carrera.costoinscripcion})
                    return render(request, "carreras/costoinscripcion.html", data)
                except Exception as ex:
                    pass

            elif action == 'delcarrera':
                try:
                    data['title'] = u'Eliminar Carrera'
                    data['carrera'] = Carrera.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    return render(request, "carreras/delcarrera.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcarrerap':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_carreras')
                    data['title'] = u'Nueva carrera'
                    data['form'] = CarreraPrincipalForm()
                    return render(request, "carreras/addcarrerap.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcarrerap':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_carreras')
                    data['title'] = u'Editar carrera'
                    data['carrera'] = carrera = CarreraGrupo.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    data['form'] = CarreraPrincipalForm(initial={'nombre':carrera.nombre, 'activa':carrera.activa})
                    return render(request, "carreras/editcarrerap.html", data)
                except Exception as ex:
                    pass

            elif action == 'delcarrerap':
                try:
                    data['title'] = u'Eliminar grupo de carrera'
                    data['carrera'] = CarreraGrupo.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    return render(request, "carreras/delcarrerap.html", data)
                except Exception as ex:
                    pass

            elif action == 'addenteaprobador':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_carreras')
                    data['title'] = u'Nueva ente aprobador de carrera'
                    data['form'] = EnteAprobadorCarreraForm()
                    return render(request, "carreras/addenteaprobador.html", data)
                except Exception as ex:
                    pass

            elif action == 'editenteaprobador':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_carreras')
                    data['title'] = u'Editar tipo formación de carrera'
                    data['ente'] = ente = EnteAprobadorCarrera.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = EnteAprobadorCarreraForm(initial={'nombre':ente.nombre})
                    return render(request, "carreras/editenteaprobador.html", data)
                except Exception as ex:
                    pass

            elif action == 'delenteaprobador':
                try:
                    data['title'] = u'Eliminar ente aprobador de carrera'
                    data['tipo'] = TipoFormacionCarrera.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    return render(request, "carreras/deltipoformacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'enteaprobador':
                try:
                    search = None
                    ids = None
                    data['title'] = u'Ente aprobador de carrera'
                    tipos = EnteAprobadorCarrera.objects.filter(status=True).order_by('nombre')
                    if 'id' in request.GET:
                        ids = int(encrypt(request.GET['id']))
                        tipos = tipos.filter(id=ids)
                    elif 's' in request.GET:
                        search = request.GET['s']
                        tipos = tipos.filter(Q(nombre__icontains=search)).distinct()
                    paging = MiPaginador(tipos, 25)
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
                    data['tipos'] = page.object_list
                    return render(request, "carreras/enteaprobador.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s"%ex})
                    pass

            elif action == 'carreragrupo':
                try:
                    search = None
                    ids = None
                    carreras = CarreraGrupo.objects.filter(status=True).order_by('nombre')
                    if 'id' in request.GET:
                        ids = int(encrypt(request.GET['id']))
                        carreras = carreras.filter(id=ids)
                    elif 's' in request.GET:
                        search = request.GET['s']
                        carreras = carreras.filter(Q(nombre__icontains=search)).distinct()
                    paging = MiPaginador(carreras, 25)
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
                    data['carreras'] = page.object_list
                    return render(request, "carreras/carreragrupo.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                search = None
                ids = None
                if 'id' in request.GET:
                    ids = request.GET['id']
                    carreras = Carrera.objects.filter(id=int(encrypt(ids)), status = True)
                elif 's' in request.GET:
                    search = request.GET['s']
                    carreras = Carrera.objects.filter((Q(nombre__icontains=search) | Q(coordinacion__alias__icontains=search)) & Q(status=True)).distinct()
                else:
                    carreras = Carrera.objects.filter(status=True)
                paging = MiPaginador(carreras, 25)
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
                data['carreras'] = page.object_list
                return render(request, "carreras/view.html", data)
            except Exception as ex:
                pass
