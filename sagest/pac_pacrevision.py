# -*- coding: UTF-8 -*-
import json

from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template

from decorators import secure_module
from sagest.forms import PacForm, ReformaForm, PacReformaForm
from sagest.models import PeriodoPac, Pac, ObjetivoOperativo, AccionDocumento, IndicadorPoa, \
    Departamento, null_to_numeric, CatalogoBien, Reforma, ReformaPac
from sga.commonviews import adduserdata
from sga.funciones import log, MiPaginador, convertir_fecha


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

        if action == 'addpacdepartamento':
            try:
                # , acciondocumento_id = int(request.POST['acciondocumento'])
                if Pac.objects.filter(periodo_id=int(request.POST['idperiodo']), departamento_id=int(request.POST['departamento']), acciondocumento=None, caracteristicas_id=int(request.POST['caracteristicas']), status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                catalogobien = CatalogoBien.objects.filter(pk=int(request.POST['caracteristicas']), status=True)[0]
                pac = Pac(periodo_id=int(request.POST['idperiodo']),
                          departamento_id=int(request.POST['departamento']),
                          # acciondocumento_id=int(request.POST['acciondocumento']),
                          caracteristicas_id=int(request.POST['caracteristicas']),
                          cantidad=int(request.POST['cantidad']),
                          unidadmedida_id=int(request.POST['unidadmedida']),
                          costounitario=request.POST['costounitario'],
                          total=request.POST['total'],
                          saldo=request.POST['total'],
                          item=catalogobien.item,
                          fechaejecucion=convertir_fecha(request.POST['fechaejecucion']))
                pac.save(request)
                log(u'Registro nuevo caracteristicas productos PAC: %s' % pac, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'editpacdepartamento':
            try:
                pac = Pac.objects.get(pk=int(request.POST['idpac']), status=True)
                pac.cantidad=int(request.POST['cantidad'])
                pac.cantidad=int(request.POST['cantidad'])
                pac.unidadmedida_id=int(request.POST['unidadmedida'])
                pac.costounitario=request.POST['costounitario']
                pac.total=request.POST['total']
                pac.saldo=request.POST['total']
                pac.fechaejecucion = convertir_fecha(request.POST['fechaejecucion'])
                pac.save(request)
                log(u'Registro modificado caracteristicas productos PAC: %s' % pac, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al editar los datos."})

        if action == 'deletepac':
            try:
                pac = Pac.objects.get(pk=request.POST['id'], status=True)
                pac.status=False
                pac.save(request)
                log(u'Elimino caracteristicas productos PAC: %s' % pac, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'segmento':
            try:
                # data['acciondocumento'] = acciondocumento = AccionDocumento.objects.get(pk=int(request.POST['acciondocumento']), status=True)
                data['acciondocumento'] = acciondocumento = None
                data['pac'] = Pac.objects.filter(departamento_id=int(request.POST['departamento']), acciondocumento=acciondocumento, status=True).order_by('id')
                data['periodopac'] = periodopac = PeriodoPac.objects.filter(pk=request.POST['periodo'], status=True)[0]
                data['total_pac'] = null_to_numeric(Pac.objects.filter(departamento_id=int(request.POST['departamento']), status=True).aggregate(total=Sum('total'))['total'])
                data['aprobado'] = periodopac.aprobado
                template = get_template("pac_pacrevision/segmento.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'addreforma':
            try:
                form = ReformaForm(request.POST)
                if form.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    if len(datos) == 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Seleccione al menos un campo del Contrato."})

                    reforma = Reforma(descripcion=form.cleaned_data['descripcion'],
                                      memorando=form.cleaned_data['memorando'],
                                      informe=form.cleaned_data['informe'],
                                      estadoreforma=form.cleaned_data['estadoreforma'],
                                      departamento=form.cleaned_data['departamento'],
                                      fecha=form.cleaned_data['fecha'])
                    reforma.save(request)
                    for elemento in datos:
                        if elemento['tipo'] == 'DISMINUCION':
                            pac = Pac.objects.filter(pk=int(elemento['id']), status=True)[0]
                            reformapac = ReformaPac(periodo_id=int(request.POST['id']),
                                                    departamento=pac.departamento,
                                                    acciondocumento=pac.acciondocumento,
                                                    caracteristicas=pac.caracteristicas,
                                                    cantidad=pac.cantidad,
                                                    unidadmedida=pac.unidadmedida,
                                                    costounitario=pac.costounitario,
                                                    total=elemento['valor'],
                                                    item=pac.item,
                                                    fechaejecucion=pac.fechaejecucion,
                                                    programa=pac.programa,
                                                    actividad=pac.actividad,
                                                    fuente=pac.fuente,
                                                    tiporeforma=2)
                            reformapac.save(request)
                            # pac.saldo=pac.saldo - Decimal(elemento['valor']).quantize(Decimal('.01'))
                            # pac.save(request)
                        else:
                            catalogobien = CatalogoBien.objects.filter(pk=int(elemento['caracteristica']), status=True)[0]
                            reformapac = ReformaPac(periodo_id=int(request.POST['id']),
                                                    departamento=form.cleaned_data['departamento'],
                                                    acciondocumento_id=int(elemento['actividadproyecto']),
                                                    caracteristicas_id=int(elemento['caracteristica']),
                                                    cantidad=int(elemento['cantidad']),
                                                    unidadmedida_id=int(elemento['unidadmedida']),
                                                    costounitario=Decimal(elemento['costounitario']).quantize(Decimal('.01')),
                                                    total=Decimal(elemento['total']).quantize(Decimal('.01')),
                                                    item=catalogobien.item,
                                                    fechaejecucion=convertir_fecha(elemento['fechaejecucion']),
                                                    programa_id=int(elemento['programa']),
                                                    actividad_id=int(elemento['actividad']),
                                                    fuente_id=int(elemento['fuente']),
                                                    tiporeforma=1)
                            reformapac.save(request)
                            if Pac.objects.filter(periodo_id=int(request.POST['id']), departamento=form.cleaned_data['departamento'], acciondocumento_id=int(elemento['actividadproyecto']), caracteristicas_id=int(elemento['caracteristica']),unidadmedida_id=int(elemento['unidadmedida']), costounitario=Decimal(elemento['costounitario']).quantize(Decimal('.01')), item=catalogobien.item, fechaejecucion=convertir_fecha(elemento['fechaejecucion']), programa_id=int(elemento['programa']), actividad_id=int(elemento['actividad']), fuente_id=int(elemento['fuente']), status=True).exists():
                                pac = Pac.objects.filter(periodo_id=int(request.POST['id']), departamento=form.cleaned_data['departamento'], acciondocumento_id=int(elemento['actividadproyecto']), caracteristicas_id=int(elemento['caracteristica']),unidadmedida_id=int(elemento['unidadmedida']), costounitario=Decimal(elemento['costounitario']).quantize(Decimal('.01')), item=catalogobien.item, fechaejecucion=convertir_fecha(elemento['fechaejecucion']), programa_id=int(elemento['programa']), actividad_id=int(elemento['actividad']), fuente_id=int(elemento['fuente']), status=True)[0]
                                pac.cantidad = pac.cantidad + int(elemento['cantidad'])
                                pac.total = pac.total + Decimal(elemento['total']).quantize(Decimal('.01'))
                                # pac.saldo = pac.saldo + float(elemento['total'])
                                pac.save(request)
                            else:
                                pac = Pac(periodo_id=int(request.POST['id']),
                                          departamento=form.cleaned_data['departamento'],
                                          acciondocumento_id=int(elemento['actividadproyecto']),
                                          caracteristicas_id=int(elemento['caracteristica']),
                                          cantidad=int(elemento['cantidad']),
                                          unidadmedida_id=int(elemento['unidadmedida']),
                                          costounitario=Decimal(elemento['costounitario']).quantize(Decimal('.01')),
                                          total=Decimal(elemento['total']).quantize(Decimal('.01')),
                                          saldo=Decimal(elemento['total']).quantize(Decimal('.01')),
                                          item=catalogobien.item,
                                          fechaejecucion=convertir_fecha(elemento['fechaejecucion']),
                                          programa_id=int(elemento['programa']),
                                          actividad_id=int(elemento['actividad']),
                                          fuente_id=int(elemento['fuente']),
                                          estadoitem=2,
                                          tipo=2)
                                pac.save(request)
                    log(u'Registro nuevo Reforma: %s' % reforma, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'revisionpac':
                try:
                    data['title'] = u'PAC UNIVERSIDAD ESTATAL DE MILAGRO '
                    data['periodopac'] = periodopac = PeriodoPac.objects.filter(pk=request.GET['id'], status=True)[0]
                    # data['departamentos'] = departamentos = Departamento.objects.filter(status=True, objetivoestrategico__isnull=False, objetivoestrategico__periodopoa__anio=periodopac.anio).distinct()
                    data['departamentos'] = departamentos = Departamento.objects.filter(status=True, pac__isnull=False).distinct()

                    search = None
                    idobjetivooperativo = 0
                    idindicadorpoa = 0
                    idacciondocumento = 0
                    iddepartamento = 0
                    objetivosoperativos = None
                    indicadorpoa = None
                    acciondocumento = None
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
                        if objetivosoperativos1:
                            objetivosoperativos = objetivosoperativos1[0]
                            idobjetivooperativo = objetivosoperativos.id

                    # indicador poa
                    if 'idindicadorpoa' in request.GET:
                        idindicadorpoa = request.GET['idindicadorpoa']
                        indicadorpoa = IndicadorPoa.objects.filter(pk=int(idindicadorpoa), status=True)[0]
                    else:
                        if objetivosoperativos:
                            indicadorpoa = objetivosoperativos.indicadorpoa_set.filter(status=True)[0]
                            idindicadorpoa = indicadorpoa.id

                    # accion documento
                    if 'idacciondocumento' in request.GET:
                        idacciondocumento = request.GET['idacciondocumento']
                        acciondocumento = AccionDocumento.objects.filter(pk=int(idacciondocumento), status=True)[0]
                    else:
                        if indicadorpoa:
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
                        acciondocumento = AccionDocumento.objects.filter(pk=search)[0]
                        pac = Pac.objects.filter(departamento=departamento,acciondocumento=acciondocumento , status=True)
                        data['idacciondocumento'] = acciondocumento.id
                    else:
                        acciondocumento1 = acciondocumento
                        # pac = Pac.objects.filter(departamento=departamento,acciondocumento=acciondocumento1 , status=True)
                    data['aprobado'] = periodopac.aprobado
                    data['form2'] = PacForm()
                    return render(request, "pac_pacrevision/revisionpac.html", data)
                except Exception as ex:
                    pass

            if action == 'deletepac':
                try:
                    data['title'] = u'Eliminar Caracteristica Producto PAC'
                    data['pac'] = Pac.objects.get(pk=request.GET['id'], status=True)
                    return render(request, 'pac_pacrevision/deletepac.html', data)
                except Exception as ex:
                    pass

            if action == 'addreforma':
                try:
                    data['title'] = u'Nuevo Reforma'
                    data['periodopac'] = periodopac = PeriodoPac.objects.get(pk=request.GET['idperiodo'], status=True)
                    data['pacs'] = Pac.objects.filter(periodo=periodopac, status=True).order_by('-id')
                    data['departamentos'] = departamentos = Departamento.objects.filter(status=True, objetivoestrategico__isnull=False, objetivoestrategico__periodopoa__anio=periodopac.anio).distinct()
                    form = ReformaForm()
                    form.adicionar(departamentos)
                    data['form'] = form
                    form2 = PacReformaForm()
                    form2.adicionar()
                    data['form2'] = form2

                    search = None
                    idobjetivooperativo = 0
                    idindicadorpoa = 0
                    idacciondocumento = 0
                    iddepartamento = 0

                    # departamento
                    departamento = departamentos[0]
                    iddepartamento = departamento.id

                    # objetivo opertaivo
                    data['objetivosoperativos'] = objetivosoperativos1 = departamento.objetivos_operativos(periodopac.anio)
                    objetivosoperativos = objetivosoperativos1[0]
                    idobjetivooperativo = objetivosoperativos.id

                    # indicador poa
                    indicadorpoa = objetivosoperativos.indicadorpoa_set.filter(status=True)[0]
                    idindicadorpoa = indicadorpoa.id

                    # accion documento
                    acciondocumento = indicadorpoa.acciondocumento_set.filter(status=True)[0]
                    idacciondocumento = acciondocumento.id

                    data['idobjetivooperativo'] = idobjetivooperativo
                    data['idindicadorpoa'] = idindicadorpoa
                    data['idacciondocumento'] = idacciondocumento
                    data['iddepartamento'] = iddepartamento

                    return render(request, "pac_pacrevision/addreforma.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Revisión PAC Departamental'
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
                # data['departamento'] = departamento

                return render(request, 'pac_pacrevision/view.html', data)
            except Exception as ex:
                pass