from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from bd.forms import EstandaresDesarrolloForm, ContenidoIndiceForm, ContenidoDocumentoForm
from bd.models import CategoriaIndice, ContenidoIndice, ContenidoDocumento

from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.funciones import log


@login_required(redirect_field_name='ret', login_url='/loginsagest')
# @secure_module
# @last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['currenttime'] = datetime.now()
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'addcategoria':
            try:
                f = EstandaresDesarrolloForm(request.POST)
                if f.is_valid():
                    if CategoriaIndice.objects.filter(status=True, descripcion=f.cleaned_data['descripcion']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una categoria con esa descripcion."})
                    categoria = CategoriaIndice(descripcion=f.cleaned_data['descripcion'])
                    categoria.save(request)
                    log(u'Adiciono nueva categoria de estandar de desarrollo: %s' % categoria, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
        elif action == 'editcategoria':
            try:
                cat = CategoriaIndice.objects.get(id=request.POST['id'])
                f = EstandaresDesarrolloForm(request.POST)
                if f.is_valid():
                    if CategoriaIndice.objects.filter(status=True, descripcion=f.cleaned_data['descripcion']).exclude(id=cat.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una categoria con esa descripcion."})
                    cat.descripcion = f.cleaned_data['descripcion']
                    cat.save(request)
                    log(u'Edito categoria de estandar de desarrollo: %s' % cat, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)

        elif action == 'delcategoria':
            try:
                cat = CategoriaIndice.objects.get(id=request.POST['id'])
                log(u'Eliminar categoría de Estandares: %s' % cat, request, "del")
                cat.status=False
                cat.save(request)
                return JsonResponse({"result": "ok", "mensaje": u"Eliminó la categoría de Estandares."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'editcontenido':
            try:
                cont = ContenidoIndice.objects.get(id=request.POST['id'])
                form = ContenidoIndiceForm(request.POST)
                if form.is_valid():
                    if ContenidoIndice.objects.filter(status=True, descripcion=form.cleaned_data['descripcion']).exclude(id=cont.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una categoria con esa descripcion."})
                    cont.descripcion = form.cleaned_data['descripcion']
                    cont.save(request)
                    log(u'Edito categoria de estandar de desarrollo: %s' % cont, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)

        elif action == 'addcontenidoindice':
            try:
                form = ContenidoIndiceForm(request.POST)
                if form.is_valid():
                    if ContenidoIndice.objects.filter(status=True, descripcion=form.cleaned_data['descripcion'], categoriaindice=form.cleaned_data['categoriaindice']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una categoria con esa descripcion."})
                    contenido = ContenidoIndice(descripcion=form.cleaned_data['descripcion'], categoriaindice=form.cleaned_data['categoriaindice'])
                    contenido.save(request)
                    log(u'Adiciono nueva subcategoria de Contenido de Documento: %s' % contenido, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)

        elif action == 'delcontenido':
            try:
                contenido = ContenidoIndice.objects.get(id=request.POST['id'])
                log(u'Eliminar Contendo Indice: %s' % contenido, request, "del")
                contenido.status=False
                contenido.save(request)
                return JsonResponse({"result": "ok", "mensaje": u"Eliminó el Contendo de Indice."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addcontenidodocumento':
            try:
                doc = ContenidoDocumentoForm(request.POST)
                if doc.is_valid():
                    if ContenidoDocumento.objects.filter(status=True, texto=doc.cleaned_data['texto'], contenidoindice=doc.cleaned_data['contenidoindice']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una categoria con esa descripcion."})
                    contdoc = ContenidoDocumento(titulo=doc.cleaned_data['titulo'], texto=doc.cleaned_data['texto'], contenidoindice=doc.cleaned_data['contenidoindice'])
                    contdoc.save(request)
                    log(u'Adiciono nueva subcategoria de Contenido de Indice: %s' % contdoc, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)

        elif action == 'editcontenidodocumento':
            try:
                contdoc = ContenidoDocumento.objects.get(id=request.POST['id'])
                doc = ContenidoDocumentoForm(request.POST)
                if doc.is_valid():
                    if ContenidoDocumento.objects.filter(status=True, texto=doc.cleaned_data['texto']).exclude(id=contdoc.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un documento con esa descripcion."})
                    contdoc.titulo = doc.cleaned_data['titulo']
                    contdoc.texto = doc.cleaned_data['texto']
                    contdoc.contenidoindice = doc.cleaned_data['contenidoindice']
                    contdoc.save(request)
                    log(u'Edito categoria de estandar de desarrollo: %s' % contdoc, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)

        elif action == 'delcontenidodocumento':
            try:
                contdoc = ContenidoDocumento.objects.get(id=request.POST['id'])
                log(u'Eliminar Contendo Indice: %s' % contdoc, request, "del")
                contdoc.status=False
                contdoc.save(request)
                return JsonResponse({"result": "ok", "mensaje": u"Eliminó el Contendo de Documento."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            if action == 'addcategoria':
                try:
                    data['title'] = u'Adicionar Estandares de Desarrollo'
                    form = EstandaresDesarrolloForm()
                    data['form'] = form
                    data['permite_modificar'] = True
                    return render(request, "estandares/addcategoria.html", data)
                except Exception as ex:
                    print(ex)
            elif action == 'editcategoria':
                try:
                    data['title'] = u'Editar categoria de Estandares de Desarrollo'
                    cat = CategoriaIndice.objects.get(id=request.GET['id'])
                    form = EstandaresDesarrolloForm(initial={'descripcion': cat.descripcion})
                    data['id'] = cat.id
                    data['form'] = form
                    data['permite_modificar'] = True
                    return render(request, "estandares/editcategoria.html.", data)
                except Exception as ex:
                    print(ex)
            elif action == 'listacontenidoindice':
                try:
                    data['title'] = u'Contenido Indice'
                    search = request.GET.get('search', '')
                    if search:
                        lista = ContenidoIndice.objects.filter(status=True, descripcion__icontains=search)
                    else:
                        lista = ContenidoIndice.objects.filter(status=True)
                    data['lista'] = lista
                    data['search'] = search
                    data['permite_modificar'] = True
                    return render(request, "estandares/lista_contenido.html", data)
                except Exception as ex:
                    print(ex)
            elif action == 'addcontenidoindice':
                try:
                    data['title'] = u'Adicionar Subcategoría'
                    form = ContenidoIndiceForm()
                    data['form'] = form
                    data['permite_modificar'] = True
                    return render(request, "estandares/addcontenidoindice.html.", data)
                except Exception as ex:
                    print(ex)
            elif action == 'editcontenido':
                try:
                    data['title'] = u'Editar contenido'
                    id = request.GET['id']
                    filtro = ContenidoIndice.objects.get(id=id)
                    form = ContenidoIndiceForm(initial={'descripcion': filtro.descripcion, 'categoriaindice': filtro.categoriaindice})
                    data['form'] = form
                    data['id'] = id
                    data['permite_modificar'] = True
                    return render(request, "estandares/editarcontenido.html.", data)
                except Exception as ex:
                    pass
            elif action == 'listacontenidodocumentos':
                try:
                    data['title'] = u'Contenido de Documentos'
                    search = request.GET.get('search', '')
                    if search:
                        lista = ContenidoDocumento.objects.filter(status=True, titulo__icontains=search)
                    else:
                        lista = ContenidoDocumento.objects.filter(status=True)
                    data['lista'] = lista
                    data['search'] = search
                    data['permite_modificar'] = True
                    return render(request, "estandares/lista_contenidodocumentos.html", data)
                except Exception as ex:
                    print(ex)
            elif action == 'addcontenidodocumento':
                try:
                    data['title'] = u'Adicionar Contenido de Documento'
                    form = ContenidoDocumentoForm()
                    data['form'] = form
                    data['permite_modificar'] = True
                    return render(request, "estandares/addcontenidodocumento.html.", data)
                except Exception as ex:
                    print(ex)
            elif action == 'editcontenidodocumento':
                try:
                    data['title'] = u'Editar Contenido de Documento'
                    id = request.GET['id']
                    doc = ContenidoDocumento.objects.get(id=id)
                    form = ContenidoDocumentoForm(initial={'titulo': doc.titulo, 'texto': doc.texto, 'contenidoindice': doc.contenidoindice})
                    data['form'] = form
                    data['id'] = id
                    data['permite_modificar'] = True
                    return render(request, "estandares/editarcontenidodocumento.html.", data)
                except Exception as ex:
                    pass
        else:
            try:
                data['title'] = u'Estandares de Desarrollo'
                search = request.GET.get('search', '')
                if search:
                    lista = CategoriaIndice.objects.filter(status=True, descripcion__icontains=search)
                else:
                    lista = CategoriaIndice.objects.filter(status=True)
                data['lista'] = lista.order_by('descripcion')
                data['search'] = search
                data['permite_modificar'] = True
                return render(request, "estandares/lista.html", data)
            except Exception as ex:
                print(ex)
