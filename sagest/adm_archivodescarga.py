# -*- coding: UTF-8 -*-
import random

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
import xlwt
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from xlwt import *
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import ArchivoDescargaForm
from sagest.models import ArchivoDescarga
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addarchivo':
            try:
                f = ArchivoDescargaForm(request.POST, request.FILES)
                newfile = None
                if f.is_valid():
                    if 'imagen' in request.FILES:
                        newfile = request.FILES['imagen']
                        newfile._name = generar_nombre("archivodescarga_", newfile._name)
                    archivo = ArchivoDescarga(nombreprograma=f.cleaned_data['nombreprograma'].upper(),
                                                version=f.cleaned_data['version'],
                                                estadoacceso=f.cleaned_data['estadoacceso'],
                                                enlacedescarga=f.cleaned_data['enlacedescarga'],
                                                imagen=newfile,
                                                estado=f.cleaned_data['estado'])
                    archivo.save(request)
                    log(u'Adiciono nuevo archivo de descarga en el balcon: %s' % archivo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        if action == 'editarchivo':
            try:
                archivo = ArchivoDescarga.objects.get(pk=request.POST['id'])
                f = ArchivoDescargaForm(request.POST, request.FILES)
                if f.is_valid():
                    if 'imagen' in request.FILES:
                        newfile = request.FILES['imagen']
                        newfile._name = generar_nombre("archivodescarga_", newfile._name)
                        archivo.imagen = newfile
                    archivo.nombreprograma = f.cleaned_data['nombreprograma'].upper()
                    archivo.version = f.cleaned_data['version']
                    archivo.estadoacceso = f.cleaned_data['estadoacceso']
                    archivo.enlacedescarga = f.cleaned_data['enlacedescarga']
                    archivo.estado = f.cleaned_data['estado']
                    archivo.save(request)
                    log(u'Modificó un archivo de descarga: %s' % archivo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'bloqueopublicacion':
            try:
                evento = ArchivoDescarga.objects.get(pk=request.POST['id'])
                evento.estado = True if request.POST['val'] == 'y' else False
                evento.save(request)
                log(u'Visualiza o no un enlace para descarga de archivo : %s (%s)' % (evento, evento.estado),
                    request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        if action == 'delarchivo':
            try:
                archivo = ArchivoDescarga.objects.get(pk=request.POST['id'])
                archivo.status = False
                archivo.save(request)
                log(u'Elimino un archivo de descarga: %s' % archivo, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addarchivo':
                try:
                    data['title'] = u'Adicionar nuevo enlace'
                    data['form'] = ArchivoDescargaForm()
                    return render(request, "adm_archivodescarga/addarchivodescarga.html", data)
                except Exception as ex:
                    pass

            if action == 'editarchivo':
                try:
                    data['title'] = u'Editar Enlace'
                    data['archivo'] = archivo = ArchivoDescarga.objects.get(pk=request.GET['id'])
                    data['form'] = ArchivoDescargaForm(
                        initial={'nombreprograma': archivo.nombreprograma, 'version': archivo.version, 'estado': archivo.estado, 'estadoacceso' : archivo.estadoacceso,'enlacedescarga': archivo.enlacedescarga})
                    return render(request, "adm_archivodescarga/editarchivodescarga.html", data)
                except Exception as ex:
                    pass

            if action == 'delarchivo':
                try:
                    data['title'] = u'ELIMINAR ENLACE DE DESCARGA'
                    data['archivo'] = ArchivoDescarga.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_archivodescarga/delarchivodescarga.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Lista de enlaces a programas'
            url_vars = ''
            filtro = Q(status=True)
            search = None
            ids = None

            if 's' in request.GET:
                if request.GET['s'] != '':
                    search = request.GET['s']

            if search:
                filtro = filtro & (Q(nombreprograma__icontains=search))
                url_vars += '&s=' + search

            procesos = ArchivoDescarga.objects.filter(filtro).order_by('id')

            paging = MiPaginador(procesos, 20)
            p = 1
            try:
                paginasesion = 1
                if 'paginador' in request.session:
                    paginasesion = int(request.session['paginador'])
                if 'page' in request.GET:
                    p = int(request.GET['page'])
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
            data["url_vars"] = url_vars
            data['ids'] = ids if ids else ""
            data['proceso'] = page.object_list
            data['email_domain'] = EMAIL_DOMAIN
            data['categorias'] = ArchivoDescarga.objects.filter(status=True).order_by('nombreprograma')
            return render(request, 'adm_archivodescarga/view.html', data)