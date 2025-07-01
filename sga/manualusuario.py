# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sagest.forms import ProveedorForm
from sagest.models import Proveedor
from sga.models import ManualUsuario
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, puede_realizar_accion


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
                f = ProveedorForm(request.POST)
                if f.is_valid():
                    if Proveedor.objects.filter(identificacion=f.cleaned_data['identificacion'].strip()).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un proveedor registrado con ese número de identificacion."})
                    proveedor = Proveedor(identificacion=f.cleaned_data['identificacion'],
                                          nombre=f.cleaned_data['nombre'],
                                          alias=f.cleaned_data['alias'],
                                          pais=f.cleaned_data['pais'],
                                          direccion=f.cleaned_data['direccion'],
                                          telefono=f.cleaned_data['telefono'],
                                          celular=f.cleaned_data['celular'],
                                          email=f.cleaned_data['email'],
                                          fax=f.cleaned_data['fax'])
                    proveedor.save(request)
                    log(u'Adiciono nuevo proveedor: %s' % proveedor, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                proveedor = Proveedor.objects.get(pk=request.POST['id'])
                f = ProveedorForm(request.POST)
                if f.is_valid():
                    proveedor.alias = f.cleaned_data['alias']
                    proveedor.direccion = f.cleaned_data['direccion']
                    proveedor.pais = f.cleaned_data['pais']
                    proveedor.telefono = f.cleaned_data['telefono']
                    proveedor.celular = f.cleaned_data['celular']
                    proveedor.email = f.cleaned_data['email']
                    proveedor.fax = f.cleaned_data['fax']
                    proveedor.save(request)
                    log(u'Modificó proveedor: %s' % proveedor, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                proveedor = Proveedor.objects.get(pk=request.POST['id'])
                if proveedor.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"El proveedor se encuentra en uso, no es posible eliminar."})
                log(u'Eliminó proveedor: %s' % proveedor, request, "del")
                proveedor.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_proveedor')
                    data['title'] = u'Adicionar Proveedor'
                    data['form'] = ProveedorForm()
                    return render(request, "adm_proveedores/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_proveedor')
                    data['title'] = u'Editar Proveedor'
                    data['proveedor'] = proveedor = Proveedor.objects.get(pk=request.GET['id'])
                    form = ProveedorForm(initial={'identificacion': proveedor.identificacion,
                                                  'nombre': proveedor.nombre,
                                                  'alias': proveedor.alias,
                                                  'direccion': proveedor.direccion,
                                                  'pais': proveedor.pais,
                                                  'telefono': proveedor.telefono,
                                                  'celular': proveedor.celular,
                                                  'email': proveedor.email,
                                                  'fax': proveedor.fax})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_proveedores/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_proveedor')
                    data['title'] = u'Borrar Proveedor'
                    data['proveedor'] = Proveedor.objects.get(pk=request.GET['id'])
                    return render(request, "adm_proveedores/delete.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Manuales de usuarios'
                search = None
                ids = None
                manuales = None
                if perfilprincipal.es_estudiante():
                    manuales = ManualUsuario.objects.filter(status=True, tipos__id__in=[4,1], visible=True).order_by('nombre')
                elif perfilprincipal.es_profesor():
                    manuales = ManualUsuario.objects.filter(status=True, tipos__id__in=[5,1], visible=True).order_by('nombre')
                elif perfilprincipal.es_administrativo():
                    manuales = ManualUsuario.objects.filter(status=True, tipos__id__in=[3,1], visible=True).order_by('nombre')
                elif perfilprincipal.es_postulanteempleo():
                    manuales = ManualUsuario.objects.filter(status=True, tipos__id__in=[6], visible=True).order_by('nombre')
                elif perfilprincipal.es_empleador():
                    manuales = ManualUsuario.objects.filter(status=True, tipos__id__in=[7], visible=True).order_by('nombre')
                else:
                    manuales = ManualUsuario.objects.filter(status=True, visible=True).order_by('nombre')

                url_vars = ''
                if 's' in request.GET:
                    search = request.GET['s']
                    url_vars += "&s={}".format(search)
                if search:
                    manuales =manuales.filter(Q(nombre__icontains=search))
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    manuales = manuales.objects.filter(id=ids)
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
                data["url_vars"] = url_vars
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['manuales'] = page.object_list
                if request.session['tiposistema'] in ['empleo', 'empresa']:
                    return render(request, "manualusuario/unemiempleoview.html", data)
                else:
                    return render(request, "manualusuario/view.html", data)
            except Exception as ex:
                pass
