# -*- coding: UTF-8 -*-
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template

from decorators import secure_module
from sagest.forms import PacForm,  EjecucionPacForm
from sagest.models import PeriodoPac, Pac, ObjetivoOperativo, AccionDocumento, IndicadorPoa, \
    Departamento, null_to_numeric,  EjecucionPac
from sga.commonviews import adduserdata
from sga.funciones import log, MiPaginador,  generar_nombre


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    # departamento = persona.mi_departamento()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'ejecucion':
            try:
                form = EjecucionPacForm(request.POST, request.FILES)
                if form.is_valid():
                    pac = Pac.objects.get(pk=int(request.POST['id']), status=True)
                    if pac.saldo < Decimal(form.cleaned_data['total']).quantize(Decimal('.01')):
                        return JsonResponse({"result": "bad", "mensaje": "Saldo menor al valor ejecultado."})
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("ejecucionpac_", newfile._name)
                    ejecucionpac = EjecucionPac(pac=pac,
                                                fecha=form.cleaned_data['fecha'],
                                                cantidad=form.cleaned_data['cantidad'],
                                                costounitario=form.cleaned_data['costounitario'],
                                                total=form.cleaned_data['total'],
                                                observacion=form.cleaned_data['observacion'],
                                                archivo=newfile)
                    ejecucionpac.save(request)
                    # pac.valorejecutado = form.cleaned_data['total']
                    # pac.total = Decimal((pac.cantidad-pac.cantidadejecutada())*pac.costounitario).quantize(Decimal('.01'))
                    # pac.save(request)
                    log(u'Registro nuevo Ejecución PAC: %s' % ejecucionpac, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'editejecucion':
            try:
                form = EjecucionPacForm(request.POST, request.FILES)
                if form.is_valid():
                    ejecucionpac = EjecucionPac.objects.filter(pk=request.POST['id'], status=True)[0]
                    if ejecucionpac.pac.saldo < Decimal(form.cleaned_data['total']).quantize(Decimal('.01')):
                        return JsonResponse({"result": "bad", "mensaje": "Saldo menor al valor ejecultado."})
                    if request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("ejecucionpac_", newfile._name)
                        ejecucionpac.archivo = newfile

                    ejecucionpac.fecha=form.cleaned_data['fecha']
                    ejecucionpac.cantidad=form.cleaned_data['cantidad']
                    ejecucionpac.costounitario=form.cleaned_data['costounitario']
                    ejecucionpac.total=form.cleaned_data['total']
                    ejecucionpac.observacion=form.cleaned_data['observacion']
                    ejecucionpac.save(request)
                    # ejecucionpac.pac.valorejecutado = form.cleaned_data['total']
                    # ejecucionpac.pac.total = Decimal((ejecucionpac.pac.cantidad-ejecucionpac.pac.cantidadejecutada())*ejecucionpac.pac.costounitario).quantize(Decimal('.01'))
                    # ejecucionpac.pac.save(request)
                    log(u'Registro modificado Ejecución PAC: %s' % ejecucionpac, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'deleteejecucion':
            try:
                ejecucionpac = EjecucionPac.objects.get(pk=request.POST['id'], status=True)
                ejecucionpac.status=False
                ejecucionpac.save(request)
                # ejecucionpac.pac.save(request)
                log(u'Elimino caracteristicas productos PAC: %s' % ejecucionpac, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'segmento':
            try:
                data['acciondocumento'] = acciondocumento = AccionDocumento.objects.get(pk=int(request.POST['acciondocumento']), status=True)
                data['pac'] = Pac.objects.filter(departamento_id=int(request.POST['departamento']), acciondocumento=acciondocumento, status=True).order_by('fechaejecucion')
                data['periodopac'] = periodopac = PeriodoPac.objects.filter(pk=request.POST['periodo'], status=True)[0]
                data['total_pac'] = null_to_numeric(Pac.objects.filter(departamento_id=int(request.POST['departamento']), status=True).aggregate(total=Sum('total'))['total'])
                data['aprobado'] = periodopac.aprobado
                template = get_template("pac_pacejecucion/segmento.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'ejecucionpac':
                try:
                    data['title'] = u'EJECUCIÓN PAC UNIVERSIDAD ESTATAL DE MILAGRO '
                    data['periodopac'] = periodopac = PeriodoPac.objects.filter(pk=request.GET['id'], status=True)[0]
                    data['departamentos'] = departamentos = Departamento.objects.filter(status=True, objetivoestrategico__isnull=False, objetivoestrategico__periodopoa__anio=periodopac.anio).distinct()

                    search = None
                    idobjetivooperativo = 0
                    idindicadorpoa = 0
                    idacciondocumento = 0
                    iddepartamento = 0

                    # departamento
                    if 'iddepartamento' in request.GET:
                        iddepartamento = request.GET['iddepartamento']
                        departamento = Departamento.objects.filter(pk=int(iddepartamento), status=True)[0]
                    else:
                        departamento = departamentos[0]
                        iddepartamento = departamento.id

                    # objetivo opertaivo
                    data['objetivosoperativos'] = objetivosoperativos1 = departamento.objetivos_operativos(periodopac.anio)
                    if 'idobjetivooperativo' in request.GET:
                        idobjetivooperativo = request.GET['idobjetivooperativo']
                        # data['objetivosoperativos'] = objetivosoperativos1 = ObjetivoOperativo.objects.filter(pk=int(idobjetivooperativo))
                        objetivosoperativos = ObjetivoOperativo.objects.filter(pk=int(idobjetivooperativo), status=True)[0]
                    else:
                        objetivosoperativos = objetivosoperativos1[0]
                        idobjetivooperativo = objetivosoperativos.id

                    # indicador poa
                    if 'idindicadorpoa' in request.GET:
                        idindicadorpoa = request.GET['idindicadorpoa']
                        indicadorpoa = IndicadorPoa.objects.filter(pk=int(idindicadorpoa), status=True)[0]
                    else:
                        indicadorpoa = objetivosoperativos.indicadorpoa_set.filter(status=True)[0]
                        idindicadorpoa = indicadorpoa.id

                    # accion documento
                    if 'idacciondocumento' in request.GET:
                        idacciondocumento = request.GET['idacciondocumento']
                        acciondocumento = AccionDocumento.objects.filter(pk=int(idacciondocumento), status=True)[0]
                    else:
                        acciondocumento = indicadorpoa.acciondocumento_set.filter(status=True)[0]
                        idacciondocumento =  acciondocumento.id

                    data['idobjetivooperativo'] = idobjetivooperativo
                    data['idindicadorpoa'] = idindicadorpoa
                    data['idacciondocumento'] = idacciondocumento
                    data['iddepartamento'] = iddepartamento

                    # acciondocumento = AccionDocumento.objects.filter(indicadorpoa__objetivooperativo=objetivosoperativo)[0]
                    if 'acciondocumento' in request.GET:
                        search = request.GET['acciondocumento']
                    if search:
                        acciondocumento = AccionDocumento.objects.filter(pk=search, status=True)[0]
                        pac = Pac.objects.filter(departamento=departamento,acciondocumento=acciondocumento , status=True)
                        data['idacciondocumento'] = acciondocumento.id
                    else:
                        acciondocumento1 = acciondocumento
                        # pac = Pac.objects.filter(departamento=departamento,acciondocumento=acciondocumento1 , status=True)
                    data['aprobado'] = periodopac.aprobado
                    data['form2'] = PacForm()
                    return render(request, "pac_pacejecucion/ejecucionpac.html", data)
                except Exception as ex:
                    pass

            if action == 'ejecucion':
                try:
                    data['pac'] = pac = Pac.objects.filter(pk=request.GET['id'], status=True)[0]
                    data['periodopac'] = pac.periodo
                    data['title'] = u'Ejecutar Pac: ' + pac.caracteristicas.descripcion
                    data['form'] = EjecucionPacForm(initial={'costounitario': pac.costounitario})
                    return render(request, "pac_pacejecucion/ejecucion.html", data)
                except Exception as ex:
                    pass

            if action == 'editejecucion':
                try:
                    data['ejecucionpac'] = ejecucionpac = EjecucionPac.objects.filter(pk=request.GET['id'], status=True)[0]
                    data['title'] = u'Editar Ejecución Pac: ' + ejecucionpac.pac.caracteristicas.descripcion
                    data['form'] = EjecucionPacForm(initial={'fecha': ejecucionpac.fecha,
                                                             'cantidad': ejecucionpac.cantidad,
                                                             'costounitario': ejecucionpac.costounitario,
                                                             'total': ejecucionpac.total,
                                                             'observacion': ejecucionpac.observacion})
                    return render(request, "pac_pacejecucion/editejecucion.html", data)
                except Exception as ex:
                    pass

            if action == 'verejecucion':
                try:
                    data['pac'] = pac = Pac.objects.filter(pk=request.GET['id'], status=True)[0]
                    data['title'] = u'Ejecución Pac: ' + pac.caracteristicas.descripcion
                    data['ejecucionpacs'] = EjecucionPac.objects.filter(status=True, pac=pac)
                    return render(request, "pac_pacejecucion/verejecucion.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteejecucion':
                try:
                    data['title'] = u'Eliminar Ejecución PAC'
                    data['ejecucionpac'] = EjecucionPac.objects.get(pk=request.GET['id'], status=True)
                    return render(request, 'pac_pacejecucion/deleteejecucion.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Ejecución PAC UNEMI'
            search = None
            tipo = None

            if 's' in request.GET:
                search = request.GET['s']
            if search:
                periodopac = PeriodoPac.objects.filter(Q(descripcion__icontains=search) |
                                                       Q(anio__icontains=search), status=True).order_by('-id')
            else:
                periodopac = PeriodoPac.objects.filter(status=True).order_by('-id')
            paging = MiPaginador(periodopac, 25)
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
            data['periodopacs'] = page.object_list
            return render(request, 'pac_pacejecucion/view.html', data)