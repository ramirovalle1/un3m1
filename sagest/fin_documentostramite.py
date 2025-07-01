# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from sagest.commonviews import anio_ejercicio
from sagest.models import PuntoVenta, DocumentosTramitePago
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    lugarrecaudacion = PuntoVenta.objects.all()[0]
    perfilprincipal = request.session['perfilprincipal']
    if 'aniofiscalpresupuesto' in request.session:
        anio = request.session['aniofiscalpresupuesto']
    else:
        anio = anio_ejercicio().anioejercicio
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'detalle_revisiones':
            try:
                data['documento'] = documento = DocumentosTramitePago.objects.get(pk=int(request.POST['id']))
                data['detalles'] = documento.detalledocumentopago_set.all().exclude(recorrido=persona.mi_departamento())
                template = get_template("fin_documentostramite/detallerevisiones.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Documentos de trámites de pago'
            ids = None
            search = None
            if 's' in request.GET:
                search = request.GET['s']
                documentos = DocumentosTramitePago.objects.filter(Q(numero__icontains=search) |
                                                                  Q(departamento__nombre__icontains=search) |
                                                                  Q(beneficiario__beneficiario__apellido1__icontains=search)).distinct().order_by('-id')
            elif 'id' in request.GET:
                ids = request.GET['id']
                documentos = DocumentosTramitePago.objects.filter(id=ids).order_by('-id')
            else:
                documentos = DocumentosTramitePago.objects.all().order_by('-id')
            paging = MiPaginador(documentos, 25)
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
            data['ids'] = ids if ids else None
            data['page'] = page
            data['documentos'] = page.object_list
            data['reporte_0'] = obtener_reporte('resumen_comprobante_egreso')
            data['search'] = search if search else ""
            try:
                return render(request, "fin_documentostramite/view.html", data)
            except Exception as ex:
                pass