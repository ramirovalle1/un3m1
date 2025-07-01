# -*- coding: latin-1 -*-
import sys

from django.template.loader import get_template
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.forms import model_to_dict
from decorators import secure_module, last_access
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import log, variable_valor, MiPaginador, generar_nombre, remover_caracteres_especiales_unicode
from sga.templatetags.sga_extras import encrypt
from laboratorio.models import Perfil, DetallePerfil, UsuarioPerfil, Test, DetalleTest, ProcesoOpcionSistema, LaboratorioOpcionSistema
from laboratorio.forms import PerfilForm, DetallePerfilForm, UsuarioPerfilForm, TestForm, DetalleTestForm, ProcesoOpcionSistemaForm, LaboratorioOpcionSistemaForm

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    persona = request.session['persona']
    usuario = request.user
    hoy = datetime.now().date()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addperfil':
            try:
                form = PerfilForm(request.POST)
                if form.is_valid():
                    registro = Perfil(nombre=form.cleaned_data['nombre'], descripcion=form.cleaned_data['descripcion'])
                    registro.save(request)
                    log(u'Adicionó Perfil: %s' % (registro), request, "add")
                    messages.success(request, 'Registro guardado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'editperfil':
            try:
                registro = Perfil.objects.get(pk=request.POST['id'])
                form = PerfilForm(request.POST)
                if form.is_valid():
                    registro.nombre = form.cleaned_data['nombre']
                    registro.descripcion = form.cleaned_data['descripcion']
                    registro.save(request)
                    log(u'Editó Perfil: %s' % registro, request, "edit")
                    messages.success(request, 'Registro editado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'delperfil':
            try:
                registro = Perfil.objects.get(pk=int(encrypt(request.POST['id'])))
                registro.status = False
                registro.save(request)
                log(u'Elimino perfil: %s' % registro, request, "del")
                messages.success(request, 'Registro eliminado con éxito.')
                res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addporcentajeperfil':
            try:
                form = DetallePerfilForm(request.POST)
                if form.is_valid():
                    registro = DetallePerfil(perfil=form.cleaned_data['perfil'],
                                             porcentajeacierto=form.cleaned_data['porcentajeacierto'],
                                             niveldificultad=form.cleaned_data['niveldificultad'],
                                             segundosinteraccion=form.cleaned_data['segundosinteraccion'],
                                             zurdo=form.cleaned_data['zurdo'],
                                             contraste=form.cleaned_data['contraste']
                                             )
                    registro.save(request)
                    log(u'Adicionó detalle perfil: %s' % (registro), request, "add")
                    messages.success(request, 'Registro guardado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'editporcentajeperfil':
            try:
                registro = DetallePerfil.objects.get(pk=request.POST['id'])
                form = DetallePerfilForm(request.POST)
                if form.is_valid():
                    registro.perfil = form.cleaned_data['perfil']
                    registro.porcentajeacierto = form.cleaned_data['porcentajeacierto']
                    registro.niveldificultad = form.cleaned_data['niveldificultad']
                    registro.segundosinteraccion = form.cleaned_data['segundosinteraccion']
                    registro.zurdo = form.cleaned_data['zurdo']
                    registro.contraste = form.cleaned_data['contraste']
                    registro.save(request)
                    log(u'Editó detalle perfil: %s' % registro, request, "edit")
                    messages.success(request, 'Registro editado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'delporcentajeperfil':
            try:
                registro = DetallePerfil.objects.get(pk=int(encrypt(request.POST['id'])))
                registro.status = False
                registro.save(request)
                log(u'Elimino detalle perfil: %s' % registro, request, "del")
                messages.success(request, 'Registro eliminado con éxito.')
                res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addusuarioperfil':
            try:
                form = UsuarioPerfilForm(request.POST)
                usuario = int(request.POST['usuario']) if ('usuario' in request.POST and request.POST['usuario'] != '' and int(request.POST['usuario']) > 0) else None
                if form.is_valid():
                    registro = UsuarioPerfil(usuario_id=usuario,
                                             perfil=form.cleaned_data['perfil'],
                                             tourguiado=form.cleaned_data['tourguiado'],
                                             fechainicio=form.cleaned_data['fechainicio'],
                                             fechafin=form.cleaned_data['fechafin'],
                                             activo=form.cleaned_data['activo']
                                             )
                    registro.save(request)
                    log(u'Adicionó usuario perfil: %s' % (registro), request, "add")
                    messages.success(request, 'Registro guardado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'editusuarioperfil':
            try:
                registro = UsuarioPerfil.objects.get(pk=request.POST['id'])
                form = UsuarioPerfilForm(request.POST)
                usuario = int(request.POST['usuario']) if ('usuario' in request.POST and request.POST['usuario'] != '' and int(request.POST['usuario']) > 0) else None
                if form.is_valid():
                    registro.usuario_id = usuario
                    registro.perfil = form.cleaned_data['perfil']
                    registro.tourguiado = form.cleaned_data['tourguiado']
                    registro.fechainicio = form.cleaned_data['fechainicio']
                    registro.fechafin = form.cleaned_data['fechafin']
                    registro.activo = form.cleaned_data['activo']
                    registro.save(request)
                    log(u'Editó usuario perfil: %s' % registro, request, "edit")
                    messages.success(request, 'Registro editado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'delusuarioperfil':
            try:
                registro = UsuarioPerfil.objects.get(pk=int(encrypt(request.POST['id'])))
                registro.status = False
                registro.save(request)
                log(u'Elimino usuario perfil: %s' % registro, request, "del")
                messages.success(request, 'Registro eliminado con éxito.')
                res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addtest':
            try:
                form = TestForm(request.POST)
                if form.is_valid():
                    registro = Test(nombre=form.cleaned_data['nombre'], descripcion=form.cleaned_data['descripcion'], fecha=form.cleaned_data['fecha'])
                    registro.save(request)
                    log(u'Adicionó Test: %s' % (registro), request, "add")
                    messages.success(request, 'Registro guardado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'edittest':
            try:
                registro = Test.objects.get(pk=request.POST['id'])
                form = TestForm(request.POST)
                if form.is_valid():
                    registro.nombre = form.cleaned_data['nombre']
                    registro.descripcion = form.cleaned_data['descripcion']
                    registro.fecha = form.cleaned_data['fecha']
                    registro.save(request)
                    log(u'Editó Test: %s' % registro, request, "edit")
                    messages.success(request, 'Registro editado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deltest':
            try:
                registro = Test.objects.get(pk=int(encrypt(request.POST['id'])))
                registro.status = False
                registro.save(request)
                log(u'Elimino Test: %s' % registro, request, "del")
                messages.success(request, 'Registro eliminado con éxito.')
                res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'adddetalletest':
            try:
                form = DetalleTestForm(request.POST)
                if form.is_valid():
                    registro = DetalleTest(test_id=int(request.POST['idp']), descripcion=form.cleaned_data['descripcion'], respuesta=form.cleaned_data['respuesta'], valor=form.cleaned_data['valor'],
                                           rgb=form.cleaned_data['rgb'], rotacion=form.cleaned_data['rotacion'], orden=form.cleaned_data['orden'])
                    registro.save(request)
                    log(u'Adicionó Detalle Test: %s' % (registro), request, "add")
                    messages.success(request, 'Registro guardado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'editdetalletest':
            try:
                registro = DetalleTest.objects.get(pk=request.POST['id'])
                form = DetalleTestForm(request.POST)
                if form.is_valid():
                    registro.descripcion = form.cleaned_data['descripcion']
                    registro.respuesta = form.cleaned_data['respuesta']
                    registro.valor = form.cleaned_data['valor']
                    registro.rgb = form.cleaned_data['rgb']
                    registro.rotacion = form.cleaned_data['rotacion']
                    registro.orden = form.cleaned_data['orden']
                    registro.save(request)
                    log(u'Editó Detalle Test: %s' % registro, request, "edit")
                    messages.success(request, 'Registro editado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deldetalletest':
            try:
                registro = DetalleTest.objects.get(pk=int(encrypt(request.POST['id'])))
                registro.status = False
                registro.save(request)
                log(u'Elimino detalle Test: %s' % registro, request, "del")
                messages.success(request, 'Registro eliminado con éxito.')
                res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addopcion':
            try:
                form = ProcesoOpcionSistemaForm(request.POST)
                if form.is_valid():
                    registro = ProcesoOpcionSistema(descripcion=form.cleaned_data['descripcion'])
                    registro.save(request)
                    log(u'Adicionó Proceso Opcion Sistema: %s' % (registro), request, "add")
                    messages.success(request, 'Registro guardado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'editopcion':
            try:
                registro = ProcesoOpcionSistema.objects.get(pk=request.POST['id'])
                form = ProcesoOpcionSistemaForm(request.POST)
                if form.is_valid():
                    registro.descripcion = form.cleaned_data['descripcion']
                    registro.save(request)
                    log(u'Editó Proceso Opcion Sistema: %s' % registro, request, "edit")
                    messages.success(request, 'Registro editado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'delopcion':
            try:
                registro = ProcesoOpcionSistema.objects.get(pk=int(encrypt(request.POST['id'])))
                registro.status = False
                registro.save(request)
                log(u'Elimino Proceso Opcion Sistema: %s' % registro, request, "del")
                messages.success(request, 'Registro eliminado con éxito.')
                res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addlaboratorioopcion':
            try:
                form = LaboratorioOpcionSistemaForm(request.POST)
                if form.is_valid():
                    registro = LaboratorioOpcionSistema(
                        modulo=form.cleaned_data['modulo'],
                        nombre=form.cleaned_data['nombre'],
                        proceso=form.cleaned_data['proceso'],
                        url=form.cleaned_data['url'],
                        descripcion=form.cleaned_data['descripcion'],
                        pregunta=form.cleaned_data['pregunta'],
                        activo=form.cleaned_data['activo']
                    )
                    registro.save(request)
                    if 'imagen' in request.FILES:
                        newfile = request.FILES['imagen']
                        newfile._name = generar_nombre('imagen_{}'.format(remover_caracteres_especiales_unicode(registro.nombre)), newfile._name)
                        registro.archivo = newfile
                        registro.save(request)
                    log(u'Adicionó Laboratorio Opcion Sistema: %s' % (registro), request, "add")
                    messages.success(request, 'Registro guardado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'editlaboratorioopcion':
            try:
                registro = LaboratorioOpcionSistema.objects.get(pk=request.POST['id'])
                form = LaboratorioOpcionSistemaForm(request.POST)
                if form.is_valid():
                    registro.modulo = form.cleaned_data['modulo']
                    registro.nombre = form.cleaned_data['nombre']
                    registro.url = form.cleaned_data['url']
                    registro.descripcion = form.cleaned_data['descripcion']
                    registro.proceso = form.cleaned_data['proceso']
                    # registro.tipo = form.cleaned_data['tipo']
                    # registro.preguntauxplora = form.cleaned_data['preguntauxplora']
                    registro.activo = form.cleaned_data['activo']
                    if 'imagen' in request.FILES:
                        newfile = request.FILES['imagen']
                        newfile._name = generar_nombre(
                            'imagen_{}'.format(remover_caracteres_especiales_unicode(registro.nombre)),
                            newfile._name)
                        registro.imagen = newfile
                    registro.save(request)
                    log(u'Editó Laboratorio Opcion Sistema: %s' % registro, request, "edit")
                    messages.success(request, 'Registro editado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'dellaboratorioopcion':
            try:
                registro = LaboratorioOpcionSistema.objects.get(pk=int(encrypt(request.POST['id'])))
                registro.status = False
                registro.save(request)
                log(u'Elimino Laboratorio Opcion Sistema: %s' % registro, request, "del")
                messages.success(request, 'Registro eliminado con éxito.')
                res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:

        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addperfil':
                try:
                    data['action'] = request.GET['action']
                    data['title'] = u'Adicionar perfil'
                    form = PerfilForm()
                    data['form'] = form
                    template = get_template("adm_perfillaboratorio/modal/formperfil.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'editperfil':
                try:
                    data['title'] = u'Editar perfil'
                    data['action'] = request.GET['action']
                    data['id'] = id = int(encrypt(request.GET['id']))
                    if id > 0:
                        data['registro'] = registro = Perfil.objects.get(pk=id)
                        form = PerfilForm(initial=model_to_dict(registro))
                        data['form'] = form
                        template = get_template("adm_perfillaboratorio/modal/formperfil.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": u"Problemas al obtener los datos. Intente nuevamente más tarde."})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'viewporcentaje':
                try:
                    data['title'] = u'Laboratorio Perfiles'
                    data['subtitle'] = u'Listado de perfiles de laboratorio'
                    data['action'] = action
                    ids = None
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), f'?action={action}'

                    if search:
                        data['s'] = search = request.GET['s'].strip()
                        ss = search.split(' ')
                        url_vars += f"&s={search}"
                        if search:
                            filtro = filtro & (Q(perfil__descripcion__icontains=search) | Q(perfil__nombre__icontains=search))

                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        filtro = filtro & (Q(status=True))

                    registros = DetallePerfil.objects.filter(filtro)
                    paging = MiPaginador(registros, 10)

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
                    data['usuario'] = usuario
                    data['page'] = page
                    data['ids'] = ids if ids else ""
                    data['listado'] = page.object_list
                    data['totalregistros'] = registros.count()
                    data['url_vars'] = url_vars
                    request.session['viewactivo'] = 2
                    return render(request, "adm_perfillaboratorio/viewporcentaje.html", data)
                except Exception as ex:
                    pass

            elif action == 'addporcentajeperfil':
                try:
                    data['action'] = request.GET['action']
                    data['title'] = u'Adicionar porcentaje perfil'
                    form = DetallePerfilForm()
                    data['form'] = form
                    template = get_template("adm_perfillaboratorio/modal/formperfil.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'editporcentajeperfil':
                try:
                    data['title'] = u'Editar porcentaje perfil'
                    data['action'] = request.GET['action']
                    data['id'] = id = int(encrypt(request.GET['id']))
                    if id > 0:
                        data['registro'] = registro = DetallePerfil.objects.get(pk=id)
                        form = DetallePerfilForm(initial=model_to_dict(registro))
                        data['form'] = form
                        template = get_template("adm_perfillaboratorio/modal/formperfil.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": u"Problemas al obtener los datos. Intente nuevamente más tarde."})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'viewusuario':
                try:
                    data['title'] = u'Laboratorio Perfiles'
                    data['subtitle'] = u'Listado de perfiles de laboratorio'
                    data['action'] = action
                    ids = None
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), f'?action={action}'

                    if search:
                        data['s'] = search = request.GET['s'].strip()
                        ss = search.split(' ')
                        url_vars += f"&s={search}"
                        if len(ss) == 1 or len(ss) > 3:
                            filtro = filtro & (
                                Q(usuario__persona__cedula__icontains=search) | Q(usuario__persona__pasaporte__icontains=search) |
                                Q(usuario__persona__nombres__icontains=search) |
                                Q(usuario__persona__apellido1__icontains=search) | Q(usuario__persona__apellido2__icontains=search) |
                                Q(perfil__descripcion__icontains=search) | Q(perfil__nombre__icontains=search)
                            )
                        elif len(ss) == 2:
                            filtro = filtro & (
                                (Q(usuario__persona__nombres__icontains=ss[0]) & Q(usuario__persona__nombres__icontains=ss[1]))|
                                (Q(usuario__persona__nombres__icontains=ss[0]) & Q(usuario__persona__apellido1__icontains=ss[1]))|
                                (Q(usuario__persona__apellido1__icontains=ss[0]) & Q(usuario__persona__nombres__icontains=ss[1]))|
                                (Q(usuario__persona__apellido1__icontains=ss[0]) & Q(usuario__persona__apellido2__icontains=ss[1])) |
                                (Q(perfil__descripcion__icontains=ss[0]) & Q(perfil__descripcion__icontains=ss[1])) |
                                (Q(perfil__nombre__icontains=ss[0]) & Q(perfil__nombre__icontains=ss[1]))
                            )
                        elif len(ss) == 3:
                            filtro = filtro & (
                                    (Q(perfil__descripcion__icontains=ss[0]) & Q(perfil__descripcion__icontains=ss[1]) & Q(perfil__descripcion__icontains=ss[2])) |
                                    (Q(perfil__nombre__icontains=ss[0]) & Q(perfil__nombre__icontains=ss[1]) & Q(perfil__nombre__icontains=ss[2]))
                            )

                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        filtro = filtro & (Q(status=True))

                    registros = UsuarioPerfil.objects.filter(filtro)
                    paging = MiPaginador(registros, 10)

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
                    data['usuario'] = usuario
                    data['page'] = page
                    data['ids'] = ids if ids else ""
                    data['listado'] = page.object_list
                    data['totalregistros'] = registros.count()
                    data['url_vars'] = url_vars
                    request.session['viewactivo'] = 3
                    return render(request, "adm_perfillaboratorio/viewusuario.html", data)
                except Exception as ex:
                    pass

            elif action == 'addusuarioperfil':
                try:
                    data['action'] = request.GET['action']
                    data['title'] = u'Adicionar usuario perfil'
                    form = UsuarioPerfilForm()
                    data['usuario_id'] = 0
                    data['form'] = form
                    template = get_template("adm_perfillaboratorio/modal/formperfil.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'editusuarioperfil':
                try:
                    data['title'] = u'Editar usuario perfil'
                    data['action'] = request.GET['action']
                    data['id'] = id = int(encrypt(request.GET['id']))
                    if id > 0:
                        data['registro'] = registro = UsuarioPerfil.objects.get(pk=id)
                        data['usuario_id'] = registro.usuario.id if registro.usuario else 0
                        form = UsuarioPerfilForm(initial=model_to_dict(registro))
                        data['form'] = form
                        template = get_template("adm_perfillaboratorio/modal/formperfil.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": u"Problemas al obtener los datos. Intente nuevamente más tarde."})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'viewtest':
                try:
                    data['title'] = u'Laboratorio test'
                    data['subtitle'] = u'Listado de test docentes'
                    data['action'] = action
                    ids = None
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), f'?action={action}'

                    if search:
                        data['s'] = search = request.GET['s'].strip()
                        ss = search.split(' ')
                        url_vars += f"&s={search}"
                        if search:
                            filtro = filtro & (Q(descripcion__icontains=search) | Q(nombre__icontains=search))

                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        filtro = filtro & (Q(status=True))

                    registros = Test.objects.filter(filtro)
                    paging = MiPaginador(registros, 10)

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
                    data['usuario'] = usuario
                    data['page'] = page
                    data['ids'] = ids if ids else ""
                    data['listado'] = page.object_list
                    data['tableIds'] = page.object_list.values_list('id', flat=True)
                    data['totalregistros'] = registros.count()
                    data['url_vars'] = url_vars
                    request.session['viewactivo'] = 4
                    return render(request, "adm_perfillaboratorio/viewtest.html", data)
                except Exception as ex:
                    pass

            elif action == 'addtest':
                try:
                    data['action'] = request.GET['action']
                    data['title'] = u'Adicionar registro'
                    form = TestForm()
                    data['form'] = form
                    template = get_template("adm_perfillaboratorio/modal/formperfil.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'edittest':
                try:
                    data['title'] = u'Editar registro'
                    data['action'] = request.GET['action']
                    data['id'] = id = int(encrypt(request.GET['id']))
                    if id > 0:
                        data['registro'] = registro = Test.objects.get(pk=id)
                        form = TestForm(initial=model_to_dict(registro))
                        data['form'] = form
                        template = get_template("adm_perfillaboratorio/modal/formperfil.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": u"Problemas al obtener los datos. Intente nuevamente más tarde."})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'adddetalletest':
                try:
                    data['action'] = request.GET['action']
                    data['idp'] = request.GET['idp']
                    data['title'] = u'Adicionar registro'
                    form = DetalleTestForm()
                    data['form'] = form
                    template = get_template("adm_perfillaboratorio/modal/formperfil.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'editdetalletest':
                try:
                    data['title'] = u'Editar registro'
                    data['action'] = request.GET['action']
                    data['id'] = id = int(encrypt(request.GET['id']))
                    if id > 0:
                        data['registro'] = registro = DetalleTest.objects.get(pk=id)
                        form = DetalleTestForm(initial=model_to_dict(registro))
                        data['form'] = form
                        template = get_template("adm_perfillaboratorio/modal/formperfil.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": u"Problemas al obtener los datos. Intente nuevamente más tarde."})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'viewopcion':
                try:
                    data['title'] = u'Opción sistema'
                    data['subtitle'] = u'Listado de opciones sistema'
                    data['action'] = action
                    ids = None
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), f'?action={action}'

                    if search:
                        data['s'] = search = request.GET['s'].strip()
                        ss = search.split(' ')
                        url_vars += f"&s={search}"
                        if search:
                            filtro = filtro & (Q(descripcion__icontains=search))

                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        filtro = filtro & (Q(status=True))

                    registros = ProcesoOpcionSistema.objects.filter(filtro).order_by('descripcion')
                    paging = MiPaginador(registros, 10)

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
                    data['usuario'] = usuario
                    data['page'] = page
                    data['ids'] = ids if ids else ""
                    data['listado'] = page.object_list
                    data['totalregistros'] = registros.count()
                    data['url_vars'] = url_vars
                    request.session['viewactivo'] = 5
                    return render(request, "adm_perfillaboratorio/viewopcion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addopcion':
                try:
                    data['action'] = request.GET['action']
                    data['title'] = u'Adicionar registro'
                    form = ProcesoOpcionSistemaForm()
                    data['form'] = form
                    template = get_template("adm_perfillaboratorio/modal/formperfil.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'editopcion':
                try:
                    data['title'] = u'Editar registro'
                    data['action'] = request.GET['action']
                    data['id'] = id = int(encrypt(request.GET['id']))
                    if id > 0:
                        data['registro'] = registro = ProcesoOpcionSistema.objects.get(pk=id)
                        form = ProcesoOpcionSistemaForm(initial=model_to_dict(registro))
                        data['form'] = form
                        template = get_template("adm_perfillaboratorio/modal/formperfil.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": u"Problemas al obtener los datos. Intente nuevamente más tarde."})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'viewlaboratorioopcion':
                try:
                    data['title'] = u'Laboratorio Opción sistema'
                    data['subtitle'] = u'Listado de laboratorio opciones del sistema'
                    data['action'] = action
                    ids = None
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), f'?action={action}'

                    if search:
                        data['s'] = search = request.GET['s'].strip()
                        ss = search.split(' ')
                        url_vars += f"&s={search}"
                        if search:
                            filtro = filtro & (Q(descripcion__icontains=search) | Q(nombre__icontains=search) |
                                               Q(proceso__descripcion__icontains=search) | Q(pregunta__icontains=search) |
                                               Q(modulo__descripcion__icontains=search) | Q(modulo__nombre__icontains=search))

                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        filtro = filtro & (Q(status=True))

                    registros = LaboratorioOpcionSistema.objects.filter(filtro).order_by('nombre')
                    paging = MiPaginador(registros, 10)

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
                    data['usuario'] = usuario
                    data['page'] = page
                    data['ids'] = ids if ids else ""
                    data['listado'] = page.object_list
                    data['totalregistros'] = registros.count()
                    data['url_vars'] = url_vars
                    request.session['viewactivo'] = 6
                    return render(request, "adm_perfillaboratorio/viewlaboratorioopcion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addlaboratorioopcion':
                try:
                    data['action'] = request.GET['action']
                    data['title'] = u'Adicionar registro'
                    form = LaboratorioOpcionSistemaForm()
                    data['form'] = form
                    template = get_template("adm_perfillaboratorio/modal/formperfil.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'editlaboratorioopcion':
                try:
                    data['title'] = u'Editar registro'
                    data['action'] = request.GET['action']
                    data['id'] = id = int(encrypt(request.GET['id']))
                    if id > 0:
                        data['registro'] = registro = LaboratorioOpcionSistema.objects.get(pk=id)
                        form = LaboratorioOpcionSistemaForm(initial=model_to_dict(registro))
                        data['form'] = form
                        template = get_template("adm_perfillaboratorio/modal/formperfil.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": u"Problemas al obtener los datos. Intente nuevamente más tarde."})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Laboratorio Perfiles'
                data['subtitle'] = u'Listado de perfiles de laboratorio'
                ids = None
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''

                if search:
                    data['s'] = search = request.GET['s'].strip()
                    ss = search.split(' ')
                    url_vars += f"&s={search}"
                    if search:
                        filtro = filtro & (Q(descripcion__icontains=search) | Q(nombre__icontains=search))

                if 'id' in request.GET:
                    ids = int(request.GET['id'])
                    filtro = filtro & (Q(status=True))

                registros = Perfil.objects.filter(filtro).order_by('nombre')
                paging = MiPaginador(registros, 10)

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
                data['usuario'] = usuario
                data['page'] = page
                data['ids'] = ids if ids else ""
                data['listado'] = page.object_list
                data['totalregistros'] = registros.count()
                data['url_vars'] = url_vars
                request.session['viewactivo'] = 1
                return render(request, "adm_perfillaboratorio/view.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                return render(request, "adm_horarios/error.html", data)
