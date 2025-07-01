# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from admision.forms import RubricaForm, RubricaCriterioForm, RubricaNivelForm
from admision.models import Rubrica, RubricaCriterio, RubricaNivel, RubricaRelleno
from decorators import secure_module
from sagest.forms import ProveedorForm
from sagest.models import Proveedor
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, puede_realizar_accion
from sga.models import Inscripcion, Carrera, Matricula, Coordinacion
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
#@secure_module
@transaction.atomic()
def view(request):
    data = {}
    data['personasesion'] = personasesion = request.session['persona']
    lista_carreras = Inscripcion.objects.values_list('carrera__id').filter(status=True, carrera__status=True,
                                                                           carrera__modalidad=3,
                                                                           coordinacion__excluir=True).distinct()
    data['lista_carreras'] = lista_carreras = Carrera.objects.filter(status=True, pk__in=lista_carreras)
    data['periodo'] = periodo = request.session['periodo']
    data['cantidad_graduados_online'] = cantidad_graduados_online = Matricula.objects.values("id").filter(
        inscripcion__carrera__modalidad=3, nivel__periodo=periodo).distinct().count()
    data['coordinacion'] = coordinacion = Coordinacion.objects.get(status=True, id=9)
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        # Rubrica
        if action == 'addrubrica':
            try:
                f = RubricaForm(request.POST)
                if f.is_valid():
                    rubrica = Rubrica(nombre=f.cleaned_data['nombre'])
                    rubrica.save(request)
                    log(u'Adiciono nuevo rubrica entrevista admisión: %s' % rubrica, request, "addrubrica")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editrubrica':
            try:
                f = RubricaForm(request.POST)
                if f.is_valid():
                    rubrica = Rubrica.objects.get(id=int(request.POST['id']))
                    rubrica.nombre = f.cleaned_data['nombre']
                    rubrica.save(request)
                    log(u'Editó rubrica entrevista admisión: %s' % rubrica, request, "editrubrica")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delrubrica':
            try:
                rubrica = Rubrica.objects.get(pk=int(request.POST['id']))
                rubrica.delete()
                log(u'Eliminó Rúbrica: %s' % rubrica, request, "delrubrica")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        # Criterio
        elif action == 'addcriteriorubrica':
            try:
                f = RubricaCriterioForm(request.POST)
                if f.is_valid():
                    criterio = RubricaCriterio(descripcion=f.cleaned_data['descripcion'], orden=f.cleaned_data['orden'])
                    criterio.save(request)
                    log(u'Adiciono nuevo criterio de rubrica admisión: %s' % criterio, request, "addcriteriorubrica")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcriteriorubrica':
            try:
                f = RubricaCriterioForm(request.POST)
                if f.is_valid():
                    criterio = RubricaCriterio.objects.get(id=int(request.POST['id']))
                    criterio.descripcion = f.cleaned_data['descripcion']
                    criterio.orden = f.cleaned_data['orden']
                    criterio.save(request)
                    log(u'Editó criterio de rúbrica admisión: %s' % criterio, request, "editcriteriorubrica")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delcriteriorubrica':
            try:
                criterio = RubricaCriterio.objects.get(pk=int(request.POST['id']))
                criterio.delete()
                log(u'Eliminó Criterio: %s' % criterio, request, "delcriteriorubrica")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        # Nivel
        elif action == 'addnivelrubrica':
            try:
                f = RubricaNivelForm(request.POST)
                if f.is_valid():
                    nivel = RubricaNivel(descripcion=f.cleaned_data['descripcion'], calificacion=f.cleaned_data['calificacion'])
                    nivel.save(request)
                    log(u'Adiciono nuevo nivel de rubrica admisión: %s' % nivel, request, "addnivelubrica")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editnivelrubrica':
            try:
                f = RubricaNivelForm(request.POST)
                if f.is_valid():
                    nivel = RubricaNivel.objects.get(id=int(request.POST['id']))
                    nivel.descripcion = f.cleaned_data['descripcion']
                    nivel.calificacion = f.cleaned_data['calificacion']
                    nivel.save(request)
                    log(u'Editó nivel de rúbrica admisión: %s' % nivel, request, "editnivelrubrica")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delnivelrubrica':
            try:
                nivel = RubricaNivel.objects.get(pk=int(request.POST['id']))
                nivel.delete()
                log(u'Eliminó Nivel: %s' % nivel, request, "delnivelrubrica")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'add':
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

        elif action == 'edit':
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

        elif action == 'delete':
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
        search = None
        ids = None
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

            #Rubrica
            if action == 'addrubrica':
                try:
                    #puede_realizar_accion(request, 'sagest.puede_modificar_proveedor')
                    data['title'] = u'Adicionar Rúbrica Entrevista'
                    data['form'] = RubricaForm()
                    return render(request, "adm_entrevista/addrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'editrubrica':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_proveedor')
                    data['rubrica'] = rubrica = Rubrica.objects.get(id=int(encrypt(request.GET['id'])))
                    data['title'] = u'Modificar Rúbrica Entrevista'
                    data['form'] = RubricaForm(initial={"nombre": rubrica.nombre})
                    return render(request, "adm_entrevista/editrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'delrubrica':
                try:
                    #puede_realizar_accion(request, 'sagest.puede_modificar_proveedor')
                    data['title'] = u'Borrar Rubrica Entrevista'
                    data['rubrica'] = Rubrica.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_entrevista/delrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'gestionrubrica':
                try:
                    #puede_realizar_accion(request, 'sagest.puede_modificar_proveedor')
                    data['title'] = u'Gestión Rúbrica Entrevista'
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        rubricas = Rubrica.objects.filter(nombre__icontains=search, status=True)
                    else:
                        rubricas = Rubrica.objects.filter(status=True)
                    page = paginacion(request, rubricas, data)
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['rubricas'] = page.object_list
                    return render(request, "adm_entrevista/gestionrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'rubricarelleno':
                try:
                    #puede_realizar_accion(request, 'sagest.puede_modificar_proveedor')
                    data['rubrica'] = rubrica = Rubrica.objects.get(id=int(encrypt(request.GET['rubrica_id'])))
                    data['title'] = u'Llenar matriz de rúbrica %s' % rubrica.nombre
                    data['rubricarelleno'] = rubricarelleno = RubricaRelleno.objects.filter(rubrica_id=rubrica.id).order_by('criterio__orden')
                    cant_niveles = [i for i in range(2)]
                    json_rubrica = []
                    for r in rubricarelleno:
                        json_rubrica.append({"orden": r.criterio.orden,
                                             "criterio": r.criterio.descripcion,
                                             "niveles": [{"nivel": n.descripcion, "calificacion": str(n.calificacion)} for n in r.niveles]})
                    if rubricarelleno.exists():
                        cant_niveles = [i for i in range(rubricarelleno[0].niveles.count())]
                    data['cant_niveles'] = cant_niveles
                    data['cant_registros'] = rubricarelleno.count() + 1
                    data['json_rubrica'] = json_rubrica
                    return render(request, "adm_entrevista/rubricarelleno.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Listado de inscripciones Admisión'
                carreraselect = 0
                inscripciones = Inscripcion.objects.filter(carrera__coordinacion__id=9).order_by('persona__apellido1',
                                                                                                 'persona__apellido2')
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        inscripciones = inscripciones.filter(Q(persona__nombres__icontains=search) |
                                                             Q(persona__apellido1__icontains=search) |
                                                             Q(persona__apellido2__icontains=search) |
                                                             Q(persona__cedula__icontains=search) |
                                                             Q(persona__pasaporte__icontains=search) |
                                                             Q(identificador__icontains=search) |
                                                             Q(inscripciongrupo__grupo__nombre__icontains=search) |
                                                             Q(persona__usuario__username__icontains=search)).distinct()
                    else:
                        inscripciones = inscripciones.filter(
                            Q(persona__apellido1__icontains=ss[0]) &
                            Q(persona__apellido2__icontains=ss[1])).distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    inscripciones = Inscripcion.objects.filter(id=ids)
                if 'c' in request.GET:
                    carreraselect = int(request.GET['c'])
                    if carreraselect > 0:
                        inscripciones = inscripciones.filter(carrera__id=carreraselect)
                page=paginacion(request, inscripciones, data)
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['inscripciones'] = page.object_list
                data['carreras'] = carreras = Carrera.objects.filter(
                    id__in=Matricula.objects.values_list('inscripcion__carrera__id', flat=True).filter(
                        nivel__periodo=periodo, inscripcion__carrera__coordinacion__id=9)).order_by('modalidad')
                data['carreraselect'] = carreraselect if carreraselect else ""
                return render(request, "adm_entrevista/view.html", data)
            except Exception as ex:
                pass

def paginacion(request, queryset, data):
    paging = MiPaginador(queryset, 15)
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
    return page