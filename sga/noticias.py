# -*- coding: latin-1 -*-
import json
import sys
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from decorators import secure_module, last_access
from settings import ARCHIVO_TIPO_GENERAL
from sga.commonviews import adduserdata
from sga.forms import NoticiaForm, CargarMuestraForm
from sga.funciones import MiPaginador, generar_nombre, log
from sga.models import Noticia, Archivo, Coordinacion, Carrera, TIPOS_NOTICIAS, TipoNoticias, Persona, NoticiaMuestra
import xlrd

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = NoticiaForm(request.POST, request.FILES)
                if f.is_valid():
                    noticia = Noticia(titular=f.cleaned_data['titular'],
                                      cuerpo=f.cleaned_data['cuerpo'],
                                      desde=f.cleaned_data['desde'],
                                      hasta=f.cleaned_data['hasta'],
                                      banerderecho=f.cleaned_data['banerderecho'],
                                      publica=request.session['persona'],
                                      tiene_muestra=f.cleaned_data['tiene_muestra'],
                                      publicacion=f.cleaned_data['publicacion'])
                    noticia.save(request)
                    tipos = json.loads(request.POST['lista_items2'])[0]
                    for t in tipos:
                        if t:
                            noticia.tipos.add(TipoNoticias.objects.get(pk=t))
                    if 'lista_items1' in request.POST:
                        for carrera in json.loads(request.POST['lista_items1']):
                            noticia.carreras.add(Carrera.objects.get(pk=carrera["id"]))
                    if 'imagen' in request.FILES:
                        newfile = request.FILES['imagen']
                        newfile._name = generar_nombre("foto_", newfile._name)
                        archivo = Archivo(nombre='NOTICIA GRAFICA',
                                          fecha=datetime.now().date(),
                                          archivo=newfile,
                                          tipo_id=ARCHIVO_TIPO_GENERAL)
                        archivo.save(request)
                        noticia.imagen = archivo
                        noticia.save(request)
                    log(u'Adiciono noticia: %s' % noticia, request, "add")
                    return JsonResponse({"result": "ok", "id": noticia.id})
                else:
                    raise NameError(f.errors)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        elif action == 'edit':
            try:
                noticia = Noticia.objects.get(pk=request.POST['id'])
                f = NoticiaForm(request.POST)
                if f.is_valid():
                    noticia.titular = f.cleaned_data['titular']
                    noticia.cuerpo = f.cleaned_data['cuerpo']
                    noticia.desde = f.cleaned_data['desde']
                    noticia.hasta = f.cleaned_data['hasta']
                    noticia.banerderecho = f.cleaned_data['banerderecho']
                    noticia.publica = request.session['persona']
                    noticia.publicacion = f.cleaned_data['publicacion']
                    noticia.tiene_muestra = f.cleaned_data['tiene_muestra']
                    tipos = json.loads(request.POST['lista_items2'])[0]
                    noticia.tipos.clear()
                    for t in tipos:
                        if t:
                            noticia.tipos.add(TipoNoticias.objects.get(pk=int(t)))
                    if 'lista_items1' in request.POST:
                        noticia.carreras.clear()
                        for carrera in json.loads(request.POST['lista_items1']):
                            noticia.carreras.add(Carrera.objects.get(pk=carrera["id"]))
                    if 'imagen' in request.FILES:
                        newfile = request.FILES['imagen']
                        newfile._name = generar_nombre("foto_", newfile._name)
                        archivo = Archivo(nombre='NOTICIA GRAFICA',
                                          fecha=datetime.now().date(),
                                          archivo=newfile,
                                          tipo_id=ARCHIVO_TIPO_GENERAL)
                        archivo.save(request)
                        noticia.imagen = archivo
                        noticia.save(request)
                    noticia.save(request)
                    log(u'Editó noticia: %s' % noticia, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delete':
            try:
                noticia = Noticia.objects.get(pk=request.POST['id'])
                log(u'Elimino noticia: %s' % noticia, request, "del")
                noticia.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'cargarmuestra':
            try:
                with transaction.atomic():
                    import openpyxl
                    if not 'archivo' in request.FILES:
                        return JsonResponse({"result": True, "mensaje": "Debe cargar un archivo con muestra."}, safe=False)
                    excel = request.FILES['archivo']
                    id = request.POST['id']
                    noti = Noticia.objects.get(pk=id)
                    wb = openpyxl.load_workbook(excel)
                    worksheet = wb.worksheets[0]
                    linea, excluido, cargados = 1, 0, 0
                    lista_excluidos = []
                    for row in worksheet.iter_rows():
                        currentValues = [str(cell.value) for cell in row]
                        if linea > 1:
                            if not currentValues[0] == 'None':
                                if Persona.objects.filter(status=True, cedula=currentValues[0]).exists():
                                    pers = Persona.objects.filter(status=True, cedula=currentValues[0]).first()
                                    if not NoticiaMuestra.objects.filter(status=True, persona=pers, noticia=noti).exists():
                                        notimuestra = NoticiaMuestra(persona=pers, noticia=noti)
                                        notimuestra.save(request)
                                        cargados += 1
                                    else:
                                        lista_excluidos.append(currentValues[0])
                                        excluido += 1
                                else:
                                    lista_excluidos.append(currentValues[0])
                                    excluido += 1
                            else:
                                excluido += 1
                        linea += 1
                    messages.success(request, 'Registro Guardado, se cargaron un total {} y se excluyeron un total de {}'.format(cargados, excluido))
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                print(ex)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deletemuestra':
            try:
                with transaction.atomic():
                    instancia = NoticiaMuestra.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Muestra de Noticia: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'add':
                try:
                    # 'tipo': 1,
                    data['title'] = u'Nueva noticia'
                    data['coordinaciones'] = Coordinacion.objects.filter(status=True).exclude(pk__in=[6, 8])
                    data['form'] = NoticiaForm(initial={'publicacion': 1,
                                                        'desde': datetime.now().date(),
                                                        'hasta': (datetime.now() + timedelta(days=30)).date()})
                    return render(request, "noticias/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar noticia'
                    noticia = Noticia.objects.get(pk=request.GET['id'])
                    data['coordinaciones'] = Coordinacion.objects.filter(status=True).exclude(pk__in=[6, 8])
                    data['form'] = NoticiaForm(initial={'titular': noticia.titular,
                                                        'cuerpo': noticia.cuerpo,
                                                        'desde': noticia.desde,
                                                        'hasta': noticia.hasta,
                                                        'tiene_muestra': noticia.tiene_muestra,
                                                        'banerderecho': noticia.banerderecho,
                                                        'publicacion': noticia.publicacion})
                    data['noticia'] = noticia
                    data['tipo'] = [ x.id for x in noticia.tipos.all()]
                    data['carreras'] = [ x.id for x in noticia.carreras.all()]
                    return render(request, "noticias/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    data['title'] = u'Eliminar noticia'
                    data['noticia'] = Noticia.objects.get(pk=request.GET['id'])
                    return render(request, "noticias/delete.html", data)
                except Exception as ex:
                    pass

            elif action == 'cargarmuestra':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = Noticia.objects.get(pk=request.GET['id'])
                    data['form2'] = CargarMuestraForm()
                    template = get_template("noticias/cargarmuestra.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'muestrapersona':
                try:
                    data['title'] = u'Muestra Noticia'
                    data['noticia'] = noti = Noticia.objects.get(pk=request.GET['id'])
                    data['muestra'] = muestra = noti.noticiamuestra_set.filter(status=True).order_by('persona__apellido1')
                    return render(request, "noticias/muestra.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Noticias publicadas'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                noticias = Noticia.objects.filter(titular__icontains=search)
            elif 'id' in request.GET:
                ids = int(request.GET['id'])
                noticias = Noticia.objects.filter(id=ids)
            else:
                noticias = Noticia.objects.all()
            paging = MiPaginador(noticias, 25)
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
            data['page'] = page
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['rangospaging'] = paging.rangos_paginado(p)
            data['paging'] = paging
            data['page'] = page
            data['noticias'] = page.object_list
            return render(request, "noticias/view.html", data)