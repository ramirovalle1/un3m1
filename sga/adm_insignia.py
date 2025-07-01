from decorators import secure_module, last_access
from datetime import datetime
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection, connections
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from sga.commonviews import adduserdata
from sga.forms import InsigniaForm, CategoriaInsigniaForm, InsigniaPersonaForm
from sga.models import Insignia, InsigniaPersona, CategoriaInsignia, TIPO_INSIGNIA, Persona
from django.template.loader import get_template
from sga.funciones import log, MiPaginador
from sga.templatetags.sga_extras import encrypt
from django.forms import model_to_dict

@login_required()
# @secure_module()
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema = request.build_absolute_uri('/')[:-1].strip("/")
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addinsignia':
            try:
                f = InsigniaForm(request.POST, request.FILES)
                if not 'modelo' in request.FILES:
                    raise NameError('Suba una imagen de la insignia')
                new_file = request.FILES['modelo']
                ext_file = new_file.name.split('.')[-1]
                if not ext_file in ['jpg','png','jpeg']:
                    raise NameError('Formate de imagen incorrecta. Tipo de archivo valido .jpg, .png, .jpeg')
                if new_file.size >4194304:
                    raise  NameError(u'Tamaño máximo permitido es de 4MB')
                if not f.is_valid():
                    raise NameError(f.errors)
                insignia = Insignia(
                    categoria = f.cleaned_data['categoria'],
                    titulo = f.cleaned_data['titulo'],
                    descripcion = f.cleaned_data['descripcion'],
                    modelo = new_file,
                    vigente = f.cleaned_data['vigente'],
                    tipoinsignia = f.cleaned_data['tipoinsignia'],
                    nombrecorto = f.cleaned_data['nombrecorto']
                )
                insignia.save(request)
                log(u'Agregó una nueva insignia %s -%s'%(insignia,insignia.pk),request,'add')
                return JsonResponse({'result':False,'mensaje': u'Registro guardado con éxito!'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result':True,'mensaje':u'Error al procesar los datos! Detalle: %s'%(ex.__str__())})

        if action == 'editinsignia':
            try:
                id = encrypt(request.POST['id'])
                data['filtro'] = insignia = Insignia.objects.filter(pk=int(id), status=True).order_by('-id').first()
                f = InsigniaForm(request.POST, request.FILES)
                new_file = None
                if 'modelo' in request.FILES:
                    new_file = request.FILES['modelo']
                    ext_file = new_file.name.split('.')[-1]
                    if not ext_file in ['jpg','png','jpeg']:
                        raise NameError('Formate de imagen incorrecta. Tipo de archivo valido .jpg, .png, .jpeg')
                    if new_file.size >4194304:
                        raise  NameError(u'Tamaño máximo permitido es de 4MB')
                if not f.is_valid():
                    raise NameError(f.errors)
                insignia.categoria = f.cleaned_data['categoria']
                insignia.titulo = f.cleaned_data['titulo']
                insignia.descripcion = f.cleaned_data['descripcion']
                if new_file:
                    insignia.modelo = new_file
                insignia.vigente = f.cleaned_data['vigente']
                insignia.tipoinsignia = f.cleaned_data['tipoinsignia']
                insignia.nombrecorto = f.cleaned_data['nombrecorto']
                insignia.save(request)
                log(u'Editó una insignia %s -%s'%(insignia,insignia.pk),request,'edit')
                return JsonResponse({'result':False,'mensaje': u'Registro guardado con éxito!'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result':True,'mensaje':u'Error al procesar los datos! Detalle: %s'%(ex.__str__())})

        if action == 'deleteinsignia':
            try:
                id = encrypt(request.POST['id'])
                insignia = Insignia.objects.filter(pk=int(id), status=True).order_by('-id').first()
                insignia.status = False
                insignia.save(request)
                log(u'Eliminó una insignia %s -%s'%(insignia,insignia.pk),request,'del')
                return JsonResponse({'error':False,'mensaje': u'Registro eliminado!'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'error':True,'mensaje':u'Error al procesar los datos! Detalle: %s'%(ex.__str__())})

        if action == 'addcategoria':
            try:
                f = CategoriaInsigniaForm(request.POST)
                if not f.is_valid():
                    raise NameError([{k: v[0]} for k, v in f.errors.items()])
                cateref = f.cleaned_data['categoriaref']
                categoriainsignia = CategoriaInsignia(
                    descripcion = f.cleaned_data['descripcion'],
                )
                if cateref:
                    categoriainsignia.parent = cateref.next()
                    categoriainsignia.categoriaref = cateref
                categoriainsignia.save(request)
                log(u'Agrego una categoria de insignia %s - %s'%(categoriainsignia.pk,categoriainsignia),request,'add')
                return JsonResponse({'result':False,'mensaje': u'Registro guardado con éxito!'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result':True,'mensaje':u'Error al procesar los datos! Detalle: %s'%(ex.__str__())})

        if action == 'addinsigper':
            try:
                f = InsigniaPersonaForm(request.POST)
                if not f.is_valid():
                    raise NameError([{k: v[0]} for k, v in f.errors.items()])
                insigper = InsigniaPersona(
                    insignia = f.cleaned_data['insignia'],
                    fechaobtencion = f.cleaned_data['fechaobtencion'],
                    persona = f.cleaned_data['persona'],
                )
                insigper.save(request)
                log(u'Agrego a una persona una insignia %s - %s'%(insigper.pk,insigper),request,'add')
                return JsonResponse({'result':False,'mensaje': u'Registro guardado con éxito!'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result':True,'mensaje':u'Error al procesar los datos! Detalle: %s'%(ex.__str__())})

        if action == 'editinsigper':
            try:
                id = encrypt(request.POST['id'])
                insigpersona = InsigniaPersona.objects.get(id=int(id),status=True)
                f = InsigniaPersonaForm(request.POST)
                if not f.is_valid():
                    raise NameError([{k: v[0]} for k, v in f.errors.items()])
                insigpersona.insignia = f.cleaned_data['insignia']
                insigpersona.fechaobtencion = f.cleaned_data['fechaobtencion']
                insigpersona.persona = f.cleaned_data['persona']
                insigpersona.save(request)
                log(u'Edito a una persona una insignia %s - %s'%(insigpersona.pk,insigpersona),request,'edit')
                return JsonResponse({'result':False,'mensaje': u'Registro guardado con éxito!'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result':True,'mensaje':u'Error al procesar los datos! Detalle: %s'%(ex.__str__())})

        if action == 'deleteinsigper':
            try:
                id = encrypt(request.POST['id'])
                insignia = InsigniaPersona.objects.filter(pk=int(id), status=True).order_by('-id').first()
                insignia.status = False
                insignia.save(request)
                log(u'Eliminó a una persona una insignias %s -%s'%(insignia,insignia.pk),request,'del')
                return JsonResponse({'error':False,'mensaje': u'Registro eliminado!'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'error':True,'mensaje':u'Error al procesar los datos! Detalle: %s'%(ex.__str__())})

        if action == 'editcategoria':
            try:
                id = encrypt(request.POST['id'])
                data['filtro'] = filtro = CategoriaInsignia.objects.filter(pk=int(id), status=True).order_by('-id').first()
                f = CategoriaInsigniaForm(request.POST)
                if not f.is_valid():
                    raise NameError([{k: v[0]} for k, v in f.errors.items()])
                filtro.categoriaref = f.cleaned_data['categoriaref']
                filtro.parent = f.cleaned_data['parent']
                filtro.descripcion = f.cleaned_data['descripcion']
                filtro.save(request)
                log(u'Editó una categoria %s -%s'%(filtro,filtro.pk),request,'edit')
                return JsonResponse({'result':False,'mensaje': u'Registro guardado con éxito!'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result':True,'mensaje':u'Error al procesar los datos! Detalle: %s'%(ex.__str__())})

        if action == 'deletecategoria':
            try:
                id = encrypt(request.POST['id'])
                catinsignia = CategoriaInsignia.objects.filter(pk=int(id), status=True).order_by('-id').first()
                catinsignia.status = False
                catinsignia.save(request)
                log(u'Eliminó una categoria %s -%s'%(catinsignia,catinsignia.pk),request,'del')
                return JsonResponse({'error':False,'mensaje': u'Registro eliminado!'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'error':True,'mensaje':u'Error al procesar los datos! Detalle: %s'%(ex.__str__())})

        if action == 'actualizarvisto':
            try:
                id = encrypt(request.POST['id'])
                valor = request.POST['valor']
                insigniaper = InsigniaPersona.objects.filter(id=int(id), status=True).order_by('-id').first()
                insigniaper.visto = json.loads(valor)
                insigniaper.save(request)
                log(u'Editó el estado de visto de la insignia de una persona %s -%s'%(insigniaper,insigniaper.pk),request,'edit')
                return JsonResponse({'result': True, 'mensaje': u'Registro editado!'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': False, 'mensaje': u'Error al procesar los datos! Detalle: %s' % (ex.__str__())})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addinsignia':
                try:
                    data['titulo'] = u'Agregar insignia'
                    id = None
                    categoria = None
                    if 'id' in request.GET:
                        id = request.GET['id']
                    if id:
                        if not CategoriaInsignia.objects.values('id').filter(status=True, id=encrypt(id)).exists():
                            raise NameError("No existe categoria")
                        categoria = CategoriaInsignia.objects.get(status=True, id=encrypt(id))

                    form = InsigniaForm(initial={
                        'categoria': categoria
                    })
                    if categoria:
                        form.addarbol()
                    data['form'] = form
                    template = get_template('adm_insignias/modal/forminsignia.html')
                    return JsonResponse({'result':True,'data':template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addcategoria':
                try:
                    data['titulo'] = u'Agregar categoría'
                    data['form'] = CategoriaInsigniaForm()
                    template = get_template('adm_insignias/modal/forminsignia.html')
                    return JsonResponse({'result':True,'data':template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addinsigper':
                try:
                    data['titulo'] = u'Agregar insignia persona'
                    form = InsigniaPersonaForm()
                    form.fields['persona'].queryset = Persona.objects.none()
                    data['form'] = form
                    template = get_template('adm_insignias/modal/forminsignia.html')
                    return JsonResponse({'result':True,'data':template.render(data)})
                except Exception as ex:
                    pass
            if action == 'editinsigper':
                try:
                    id = encrypt(request.GET['id'])
                    data['filtro'] = filtro = InsigniaPersona.objects.get(id=int(id), status=True)
                    data['titulo'] = u'Agregar insignia persona'
                    form = InsigniaPersonaForm(initial=model_to_dict(filtro))
                    if filtro.persona:
                        form.fields['persona'].queryset = Persona.objects.filter(id=filtro.persona.id)
                    else:
                        form.fields['persona'].queryset = Persona.objects.none()
                    data['form'] = form
                    template = get_template('adm_insignias/modal/forminsignia.html')
                    return JsonResponse({'result':True,'data':template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editinsignia':
                try:
                    id = encrypt(request.GET['id'])
                    data['filtro'] = insignia = Insignia.objects.filter(pk=int(id), status=True).order_by('-id').first()

                    data['titulo'] = u'Editar insignia'
                    data['form'] = InsigniaForm(initial={
                        'titulo':insignia.titulo,
                        'descripcion':insignia.descripcion,
                        'categoria':insignia.categoria,
                        'tipoinsignia':insignia.tipoinsignia,
                        'modelo':insignia.modelo.url,
                        'vigente':insignia.vigente,
                        'nombrecorto':insignia.nombrecorto
                    })
                    template = get_template('adm_insignias/modal/forminsignia.html')
                    return JsonResponse({'result':True,'data':template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editcategoria':
                try:
                    id = encrypt(request.GET['id'])
                    data['filtro'] = filtro = CategoriaInsignia.objects.filter(pk=int(id), status=True).order_by('-id').first()
                    data['titulo'] = u'Editar categoría'
                    form = CategoriaInsigniaForm(model_to_dict(filtro))
                    data['form'] = form
                    template = get_template('adm_insignias/modal/forminsignia.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'viewcategoria':
                try:
                    url_vars = f'&action={action}'
                    data['title'] = u'Categoría de insignias'
                    categoria = CategoriaInsignia.objects.filter(status=True)
                    request.session['viewactivo'] = 2
                    if 's' in request.GET:
                        data['s'] = search = request.GET['s']
                        categoria = categoria.filter(Q(descripcion__icontains=search)).distinct()
                        url_vars += f"&s={search}"
                    paging = MiPaginador(categoria, 25)
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
                    paging.rangos_paginado(p)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, 'adm_insignias/viewcategoria.html', data)
                except Exception as ex:
                    pass

            if action == 'viewpersonainsi':
                try:
                    url_vars = f'&action={action}'
                    data['title'] = u'Categoría de insignias'
                    insigniaper = InsigniaPersona.objects.filter(status=True)
                    request.session['viewactivo'] = 3
                    if 's' in request.GET:
                        data['s'] = q = search = request.GET['s']
                        s = search.split(' ')
                        if len(s) == 1:
                            insigniaper = insigniaper.filter((Q(persona__nombres__icontains=q) | Q(persona__apellido1__icontains=q) | Q(
                                persona__cedula__icontains=q) | Q(persona__apellido2__icontains=q) | Q(persona__cedula__contains=q)),
                                                   Q(status=True)).distinct()[:15]
                        elif len(s) == 2:
                            insigniaper = insigniaper.filter((Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1])) |
                                                   (Q(persona__nombres__icontains=s[0]) & Q(persona__nombres__icontains=s[1])) |
                                                   (Q(persona__nombres__icontains=s[0]) & Q(persona__apellido1__contains=s[1]))).filter(
                                status=True).distinct()[:15]
                        else:
                            insigniaper = insigniaper.filter(Q(insignia__descripcion__icontains=search)).distinct()
                        url_vars += f"&s={search}"
                    paging = MiPaginador(insigniaper, 25)
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
                    paging.rangos_paginado(p)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, 'adm_insignias/viewinsigpersona.html', data)
                except Exception as ex:
                    pass

            if action == 'viewarbolcategoria':
                try:
                    request.session['viewactivo'] = 2
                    data['title'] = u'Arbol categoría de insignias'
                    categoria = CategoriaInsignia.objects.filter(status=True, parent=0, categoriaref__isnull=True).order_by('descripcion')
                    data['categoria'] = categoria
                    return render(request,'adm_insignias/viewtreecat.html', data)
                except Exception as ex:
                    pass

            if action == 'buscarpersonas':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    querybase = Persona.objects.filter(status=True,).order_by('apellido1')
                    if len(s) == 1:
                        per = querybase.filter((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(cedula__icontains=q) |  Q(apellido2__icontains=q) | Q(cedula__contains=q)), Q(status=True)).distinct()[:15]
                    elif len(s) == 2:
                        per = querybase.filter((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                                                       (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                                                       (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1]))).filter(status=True).distinct()[:15]
                    else:
                        per = querybase.filter((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) |
                                                       (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2]))).filter(status=True).distinct()[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.cedula, x.nombre_completo())} for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
        else:
            url_vars = ''
            data['title'] = u'Insignias conseguidas'
            insignia = Insignia.objects.filter(status=True)
            request.session['viewactivo'] = 1
            if 's' in request.GET:
                data['s'] = search = request.GET['s']
                insignia = insignia.filter(Q(id__icontains=search) | Q(titulo__icontains=search) | Q(descripcion__icontains=search)).distinct()
                url_vars += f"&s={search}"
            if 'tipo' in request.GET:
                data['tipo'] = estado = int(request.GET['tipo'])
                insignia = insignia.filter(tipoinsignia=estado)
                url_vars += f"&tipo={estado}"
            paging = MiPaginador(insignia, 25)
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
            paging.rangos_paginado(p)
            data['paging'] = paging
            data['rangospaging'] = paging.rangos_paginado(p)
            data['page'] = page
            data['listado'] = page.object_list
            data['url_vars'] = url_vars
            return render(request,'adm_insignias/view.html',data)