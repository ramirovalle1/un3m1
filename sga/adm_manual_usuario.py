# -*- coding: UTF-8 -*-
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sagest.forms import ProveedorForm, ManualUsuarioForm
from sagest.models import Proveedor
from sga.models import ManualUsuario, TipoNoticias
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, puede_realizar_accion, generar_nombre


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'add':
            try:
                f = ManualUsuarioForm(request.POST,request.FILES)
                if not f.is_valid():
                    # [(k, v[0]) for k, v in f.errors.items()]
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                manualusuario = ManualUsuario(
                                      nombre=f.cleaned_data['nombre'],
                                      version=f.cleaned_data['version'],
                                      fecha=f.cleaned_data['fecha'],
                                      observacion=f.cleaned_data['observacion'],
                                      visible=f.cleaned_data['visible']
                                      )
                manualusuario.save(request)

                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("manual_usuario_", newfile._name)

                    manualusuario.archivo = newfile
                    manualusuario.save(request)

                if 'archivofuente' in request.FILES:
                    newfile = request.FILES['archivofuente']
                    newfile._name = generar_nombre("manual_usuario_", newfile._name)

                    manualusuario.archivofuente = newfile
                    manualusuario.save(request)
                for tipo in f.cleaned_data['tipos']:
                    manualusuario.tipos.add(tipo)
                for modulo in f.cleaned_data['modulos']:
                    manualusuario.modulos.add(modulo)
                log(u'Adiciono nuevo Manual de Usuario: %s' % manualusuario, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        if action == 'edit':
            try:
                manualusuario = ManualUsuario.objects.get(pk=request.POST['id'])
                f = ManualUsuarioForm(request.POST)
                if not f.is_valid():
                    # [(k, v[0]) for k, v in f.errors.items()]
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                manualusuario.nombre = f.cleaned_data['nombre']
                manualusuario.version = f.cleaned_data['version']
                manualusuario.fecha = f.cleaned_data['fecha']
                manualusuario.observacion = f.cleaned_data['observacion']
                manualusuario.visible = f.cleaned_data['visible']
                manualusuario.save(request)
                manualusuario.tipos.clear()
                # for data in f.cleaned_data['tipos']:
                #     manualusuario.modulos.add(data)
                # manualusuario.modulos.clear()
                # for r in f.cleaned_data['modulos']:
                #     manualusuario.modulos.add(r)
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("manual_usuario_", newfile._name)

                    manualusuario.archivo = newfile

                if 'archivofuente' in request.FILES:
                    newfile = request.FILES['archivofuente']
                    newfile._name = generar_nombre("manual_usuario_", newfile._name)

                    manualusuario.archivofuente = newfile
                manualusuario.save(request)
                log(u'Modificó Manual Usuario: %s' % manualusuario, request, "edit")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        if action == 'delete':
            try:
                manualusuario = ManualUsuario.objects.get(pk=request.POST['id'])
                manualusuario.delete()
                #manualusuario.save(request)
                log(u'Eliminó Manual de Usuario: %s' % manualusuario, request, "del")
                return JsonResponse({"result": "ok", 'mensaje': u'Registro eliminado correctamente.'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'cambiarestado':
            try:
                manualusuario = ManualUsuario.objects.get(pk=request.POST['id'])
                estado = request.POST['estado']
                manualusuario.visible = not eval(estado)
                manualusuario.save(request)
                log(u'Cambio Estado Manual de Usuario: %s' % manualusuario, request, "del")
                return JsonResponse({"result": "ok", 'mensaje': u'Se cambio estado correctamente'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al Cambiar Estado Visible."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    #puede_realizar_accion(request, 'sagest.puede_modificar_proveedor')
                    data['title'] = u'Adicionar Manual De Usuario'
                    data['form'] = ManualUsuarioForm()
                    return render(request, "adm_manual_usuario/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    #puede_realizar_accion(request, 'sagest.puede_modificar_proveedor')
                    data['title'] = u'Editar Manual de Usuario'
                    data['manualusuario'] = manualusuario = ManualUsuario.objects.get(pk=request.GET['id'])
                    form = ManualUsuarioForm(initial={
                                                  'nombre': manualusuario.nombre,
                                                  'observacion': manualusuario.observacion,
                                                  'version': manualusuario.version,
                                                  'fecha': manualusuario.fecha,
                                                  'visible': manualusuario.visible,
                                                  'tipos': manualusuario.tipos.all(),
                                                  'modulos': manualusuario.modulos.all(),
                                            })
                    #form.editar()
                    data['form'] = form
                    return render(request, "adm_manual_usuario/edit.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = 'Administración Manuales de usuarios'
                search = None
                ids = None
                manuales = None
                data['tipos'] = tipos = TipoNoticias.objects.filter(status=True)
                # if perfilprincipal.es_estudiante():
                #     manuales = ManualUsuario.objects.filter(status=True, tipos__id__in=[4,1], visible=True).order_by('nombre')
                # elif perfilprincipal.es_profesor():
                #     manuales = ManualUsuario.objects.filter(status=True, tipos__id__in=[5,1], visible=True).order_by('nombre')
                # elif perfilprincipal.es_administrativo():
                #     manuales = ManualUsuario.objects.filter(status=True, tipos__id__in=[3,1], visible=True).order_by('nombre')
                # else:
                #     manuales = ManualUsuario.objects.filter(status=True, visible=True).order_by('nombre')
                manuales = ManualUsuario.objects.filter(status=True)
                if 's' in request.GET:
                    search = request.GET['s']
                if search:
                    manuales =manuales.filter(Q(nombre__icontains=search))
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    manuales = manuales.objects.filter(id=ids)


                visible = 0
                if 'v' in request.GET and int(request.GET['v']) > 0:
                    visible = int(request.GET['v'])
                    manuales = manuales.filter(visible=int(request.GET['v']) == 1)

                tipo = 0
                if 't' in request.GET and int(request.GET['t']) > 0:
                    tipo = int(request.GET['t'])
                    manuales = manuales.filter(tipos__id=int(request.GET['t']))

                paging = MiPaginador(manuales, 20)
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
                data['visible'] = visible
                data['tipo'] = tipo
                data['manuales'] = page.object_list
                return render(request, "adm_manual_usuario/view.html", data)
            except Exception as ex:
                pass
