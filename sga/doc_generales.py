# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import ARCHIVO_TIPO_MANUALES
from sga.commonviews import adduserdata
from sga.forms import ArchivoGeneralForm
from sga.funciones import generar_nombre, log, MiPaginador
from sga.models import Archivo


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'add':
                try:
                    form = ArchivoGeneralForm(request.POST, request.FILES)
                    if form.is_valid():
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("documentogeneral_", newfile._name)
                        archivo = Archivo(nombre=form.cleaned_data['nombre'],
                                          fecha=datetime.now().date(),
                                          tipo_id=ARCHIVO_TIPO_MANUALES,
                                          grupo=form.cleaned_data['grupo'],
                                          archivo=newfile,
                                          sga=form.cleaned_data['sga'],
                                          sagest=form.cleaned_data['sagest'],
                                          api=form.cleaned_data['api'],
                                          visible=form.cleaned_data['visible'])
                        archivo.save(request)
                        log(u'Adiciono archivo general: %s' % archivo, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

            if action == 'edit':
                try:
                    form = ArchivoGeneralForm(request.POST)
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            if newfile.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                            elif newfile.size <= 0:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, el archivo Propuesta Práctica esta vacío."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == ".doc" or ext == ".docx" or ext == ".xls" or ext == ".xlsx" or ext == ".pdf" or ext == ".DOC" or ext == ".DOCX" or ext == ".XLS" or ext == ".XLSX" or ext == ".PDF" or ext == ".png" or ext == ".jpeg" or ext == ".jpg" or ext == ".html":
                                    newfile._name = generar_nombre("documentogeneral_", newfile._name)
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo de Propuesta Práctica solo en .doc, docx."})
                    if form.is_valid():
                        archivo = Archivo.objects.get(pk=int(request.POST['id']))
                        archivo.nombre = form.cleaned_data['nombre']
                        archivo.grupo=form.cleaned_data['grupo']
                        archivo.visible=form.cleaned_data['visible']
                        archivo.sga=form.cleaned_data['sga']
                        archivo.sagest=form.cleaned_data['sagest']
                        archivo.api=form.cleaned_data['api']
                        if newfile:
                            archivo.archivo=newfile
                        archivo.save(request)
                        log(u'Adiciono archivo general: %s' % archivo, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

            if action == 'del':
                try:
                    archivo = Archivo.objects.get(pk=request.POST['id'])
                    log(u'Elimino archivo general: %s' % archivo, request, "del")
                    archivo.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {}
        adduserdata(request, data)
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar documento'
                    data['form'] = ArchivoGeneralForm()
                    return render(request, "doc_generales/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar documento'
                    data['archivo'] = archivo = Archivo.objects.get(pk=int(request.GET['id']))
                    data['form'] = ArchivoGeneralForm(initial={'nombre':archivo.nombre, 'grupo':archivo.grupo, 'visible': archivo.visible, 'sga': archivo.sga, 'sagest': archivo.sagest, 'api': archivo.api})
                    return render(request, "doc_generales/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'del':
                try:
                    data['title'] = u'Eliminar documento'
                    archivo = Archivo.objects.get(pk=request.GET['id'])
                    data['archivo'] = archivo
                    return render(request, "doc_generales/del.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Subir documentos'
            search = None
            ids = None
            archivos = Archivo.objects.filter(tipo_id=ARCHIVO_TIPO_MANUALES).order_by('nombre')
            data['grupos'] = Group.objects.filter(id__in=archivos.values_list('grupo__id', flat=False).filter(grupo__isnull=False))
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss)==1:
                    archivos = archivos.filter(nombre__icontains=search)
                elif len(ss) == 2:
                    archivos = archivos.filter(Q(nombre__icontains=ss[0]), Q(nombre__icontains=ss[1]))
                else:
                    archivos = archivos.filter(Q(nombre__icontains=ss[0]), Q(nombre__icontains=ss[1]))
            if 'gid' in request.GET:
                archivos = archivos.filter(grupo_id=int(request.GET['gid']))
                data['idg'] = int(request.GET['gid'])
            app = 0
            if 'app' in request.GET and int(request.GET['app']) > 0:
                app = int(request.GET['app'])
                if app == 1:
                    archivos = archivos.filter(sga=True)
                elif app == 2:
                    archivos = archivos.filter(sagest=True)
                elif app == 3:
                    archivos = archivos.filter(api=True)
            data['app_filter'] = app
            paging = MiPaginador(archivos, 20)
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
            data['archivos'] = page.object_list
            return render(request, "doc_generales/view.html", data)
