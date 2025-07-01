# -*- coding: latin-1 -*-
#decoradores
import json
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from django.forms import model_to_dict
from decorators import last_access, secure_module
from inno.models import CampoAmplioPac, CampoEspecificoPac, CampoDetalladoPac
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre, log, email_valido, MiPaginador
from sga.models import CamposTitulosPostulacion, Titulo, AreaConocimientoTitulacion, SubAreaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacion
from postulate.forms import CamposTitulosPostulacionForm


@login_required(redirect_field_name='ret', login_url='/loginpostulate')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['url_'] = request.path
    persona = request.session['persona']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addtitulo':
            try:
                with transaction.atomic():
                    form = CamposTitulosPostulacionForm(request.POST)
                    if form.is_valid():
                        if CamposTitulosPostulacion.objects.filter(titulo=form.cleaned_data['titulo'], status=True).exists():
                            return JsonResponse({"result": True, "mensaje": "Ya existe una configuración con este título."}, safe=False)
                        instance = CamposTitulosPostulacion(titulo=form.cleaned_data['titulo'])
                        instance.save(request)
                        for ca in form.cleaned_data['campoamplio']:
                            instance.campoamplio.add(ca)
                        for ce in form.cleaned_data['campoespecifico']:
                            instance.campoespecifico.add(ce)
                        for cd in form.cleaned_data['campodetallado']:
                            instance.campodetallado.add(cd)
                        log(u'Adicionó Configuracion Titulo Postulate: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. {}".format(ex)}, safe=False)

        if action == 'edittitulo':
            try:
                with transaction.atomic():
                    instance = CamposTitulosPostulacion.objects.get(pk=request.POST['id'])
                    form = CamposTitulosPostulacionForm(request.POST)
                    if form.is_valid():
                        instance.campoamplio.clear()
                        for ca in form.cleaned_data['campoamplio']:
                            instance.campoamplio.add(ca)
                        instance.campoespecifico.clear()
                        for ce in form.cleaned_data['campoespecifico']:
                            instance.campoespecifico.add(ce)
                        instance.campodetallado.clear()
                        for cd in form.cleaned_data['campodetallado']:
                            instance.campodetallado.add(cd)
                        instance.save(request)
                        log(u'Edito Configuracion Titulo Postulate: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. {}".format(ex)}, safe=False)

        if action == 'deltitulo':
            try:
                with transaction.atomic():
                    instancia = CamposTitulosPostulacion.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Configuración Título: %s' % instancia, request, "delete")
                    return JsonResponse({'error': False}, safe=False)
            except Exception as ex:
                return JsonResponse({'error': True, "message": "Error: {}".format(ex)}, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addtitulo':
                try:
                    form = CamposTitulosPostulacionForm()
                    excluirids = CamposTitulosPostulacion.objects.values('titulo__id').filter(status=True).values_list('titulo__id', flat=True)
                    form.fields['titulo'].queryset = Titulo.objects.none()
                    # form.fields['campoamplio'].queryset = AreaConocimientoTitulacion.objects.none()
                    form.fields['campoespecifico'].queryset = SubAreaConocimientoTitulacion.objects.none()
                    form.fields['campodetallado'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.none()
                    data['form'] = form
                    template = get_template("postulate/adm_configuraciontitulos/formtitulos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'edittitulo':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = CamposTitulosPostulacion.objects.get(pk=request.GET['id'])
                    form = CamposTitulosPostulacionForm(initial=model_to_dict(filtro))
                    form.fields['titulo'].queryset = Titulo.objects.filter(status=True, usoseleccion=True, pk=filtro.titulo.pk)
                    # form.fields['campoamplio'].queryset = listamplios = AreaConocimientoTitulacion.objects.filter(status=True, id__in=filtro.campoamplio.all().values_list('id',flat=True))
                    form.fields['campoespecifico'].queryset = listespecifico = SubAreaConocimientoTitulacion.objects.filter(status=True, id__in=filtro.campoespecifico.all().values_list('id',flat=True))
                    form.fields['campodetallado'].queryset = listdetallado = SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, id__in=filtro.campodetallado.all().values_list('id',flat=True))
                    data['form'] = form
                    template = get_template("postulate/adm_configuraciontitulos/formtitulos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'buscartitulos':
                try:
                    q = request.GET['q'].upper().strip()
                    querybase = Titulo.objects.filter(nivel_id__in=[3, 4, 21, 22, 23], status=True)
                    per = querybase.filter((Q(nombre__icontains=q) | Q(abreviatura__icontains=q)), Q(status=True)).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.abreviatura, x.nombre)} for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'listcampoespecifico':
                try:
                    campoamplio = request.GET.get('campoamplio')
                    listcampoamplio=campoamplio
                    if len(campoamplio) > 1:
                        listcampoamplio = campoamplio.split(',')
                    querybase = SubAreaConocimientoTitulacion.objects.filter(status=True, areaconocimiento__in=listcampoamplio).order_by('codigo')
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id,"idca":x.areaconocimiento.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'listcampodetallado':
                try:
                    campoespecifico = request.GET.get('campoespecifico')
                    listcampoespecifico = campoespecifico
                    if len(campoespecifico) > 1:
                        listcampoespecifico = campoespecifico.split(',')
                    querybase = SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, areaconocimiento__in=listcampoespecifico).order_by('codigo')
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Configuración Armonización de Títulos'

                search, filtro, url_vars = request.GET.get('s', ''), (Q(status=True)), ''

                if search:
                    data['search'] = search
                    url_vars += "&s={}".format(search)
                    filtro = filtro & (Q(titulo__nombre__icontains=search) | Q(titulo__abreviatura__icontains=search))

                listado = CamposTitulosPostulacion.objects.filter(filtro).order_by('titulo__nombre')
                paging = MiPaginador(listado, 20)
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
                data['listado'] = page.object_list
                data['list_count'] = len(listado)
                return render(request, "postulate/adm_configuraciontitulos/view.html", data)
            except Exception as ex:
                pass

