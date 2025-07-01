# -*- coding: UTF-8 -*-
import sys
from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template

from decorators import secure_module
from sga.templatetags.sga_extras import encrypt
from voto.forms import EvidenciaActaForm
from voto.models import *
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, puede_realizar_accion, generar_nombre, puede_realizar_accion_afirmativo
from django.db.models import Sum, Q, F, FloatField
from django.db.models.functions import Coalesce


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona_sesion=request.session['persona']
    if not request.user.is_superuser:
        if not persona_sesion.es_profesor():
            return redirect('/?info=Solo docentes pueden acceder al modulo')
    # puedeingresar = puede_realizar_accion_afirmativo(request, 'sga.puede_ingresar_acta_mesa')
    if request.method == 'POST':
        action = request.POST['action']
        valoranterior = 0

        if action == 'actualiza_totalempadronados':
            try:
                det=ConfiguracionMesaResponsable.objects.get(id=request.POST['id'])
                valoranterior = det.totalempadronados
                valor=int(request.POST['valor'])
                if valoranterior != valor:
                    log(u'Edita valor de empadronado en mesa valor ant (%s) valor nuevo (%s) de autoridad %s ' % (det.__str__(), str(valoranterior), str(valor)), request, "edit")
                    det.totalempadronados=valor
                    det.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "valoranterior":valoranterior, "mensaje": u"Error al guardar los datos."})

        elif action == 'actualiza_valores':
            try:
                det=DetalleMesa.objects.get(id=request.POST['iddet'])
                campo=request.POST['campo']
                valor=int(request.POST['valor'])
                if campo == 'empadronado':
                    if det.empadronado != valor:
                        log(u'Edita valor de empadronado valor ant (%s) valor nuevo (%s) de autoridad %s ' % (det.empadronado, str(valor), det.gremio_periodo), request, "edit")
                        det.empadronado=valor
                elif campo == 'ausentismo':
                    if det.ausentismo != valor:
                        det.ausentismo=valor
                        log(u'Edita valor de ausentismo valor ant (%s) valor nuevo (%s) de autoridad %s ' % (det.ausentismo, str(valor), det.gremio_periodo), request, "edit")

                elif campo == 'votovalido':
                    if det.votovalido != valor:
                        det.votovalido=valor
                        log(u'Edita valor de votovalido valor ant (%s) valor nuevo (%s) de autoridad %s ' % (det.votovalido, str(valor),det.gremio_periodo), request, "edit")

                elif campo == 'votonulo':
                    if det.votonulo != valor:
                        det.votonulo=valor
                        log(u'Edita valor de votonulo valor ant (%s) valor nuevo (%s) de autoridad %s ' % (det.votonulo, str(valor), det.gremio_periodo), request, "edit")

                elif campo == 'votoblanco':
                    if det.votoblanco != valor:
                        det.votoblanco=valor
                        log(u'Edita valor de votonulo valor ant (%s) valor nuevo (%s) de autoridad %s ' % (det.votonulo, str(valor), det.gremio_periodo), request, "edit")
                det.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "valoranterior":valoranterior, "mensaje": u"Error al guardar los datos."})

        elif action == 'actualiza_valores_subdet':
            try:
                subdet=SubDetalleMesa.objects.get(id=request.POST['iddet'])
                valor=int(request.POST['valor'])
                if subdet.totalvoto != valor:
                    log(u'Edita valor lista %s valor ant (%s) valor nuevo (%s) de autoridad %s ' % (subdet.lista.nombre, subdet.totalvoto, str(valor), subdet.detallemesa.gremio_periodo), request, "edit")
                    subdet.totalvoto=valor
                    subdet.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "valoranterior":valoranterior, "mensaje": u"Error al guardar los datos."})

        elif action == 'cerraracta':
            try:
                with transaction.atomic():
                    newfile = None
                    id = int(request.POST['id'])
                    filtro = ConfiguracionMesaResponsable.objects.get(pk=id)
                    form = EvidenciaActaForm(request.POST, request.FILES)
                    if form.is_valid():
                        detallemesas = DetalleMesa.objects.filter(status=True, mesa_responsable=filtro).order_by('pk')
                        for d in detallemesas:
                            totalvotos = Decimal(d.empadronado)
                            totalesregistrados = Decimal(d.ausentismo) + Decimal(d.votovalido) + Decimal(d.votonulo) + Decimal(d.votoblanco)
                            if totalvotos != totalesregistrados:
                                return JsonResponse({"result": True, "mensaje": u"Los votos registrados en {} no concuerdan con la cantidad de personas empadronadas. {} / {}".format(d.gremio_periodo, totalvotos, totalesregistrados)})
                            totalvotos = SubDetalleMesa.objects.filter(status=True, detallemesa=d).aggregate(total=Coalesce(Sum(F('totalvoto'), output_field=IntegerField()), 0)).get('total')
                            if d.votovalido != totalvotos:
                                return JsonResponse({"result": False, "mensaje": u"Los votos registrados por listas en {} no concuerdan con la cantidad de votos validos. {} / {}".format(d.gremio_periodo, d.votovalido, totalvotos)})
                        if 'acta_evidencia' in request.FILES:
                            newfile = request.FILES['acta_evidencia']
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 4194304:
                                return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                            if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                newfile._name = generar_nombre("actaelecciones_", newfile._name)
                            else:
                                return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                            filtro.acta_evidencia = newfile
                            filtro.abierta = False
                            filtro.persona_cierre = persona_sesion
                            filtro.fecha_cierre = datetime.now()
                            filtro.hora_cierre = datetime.now().time()
                            filtro.save(request)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "FALTA SUBIR EVIDENCIA"}, safe=False)
                        log(u'Cierre de Acta: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False, 'to': "{}".format(request.path)}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": f"Intentelo más tarde. {ex} - Linea {sys.exc_info()[-1].tb_lineno}"}, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'cerraracta':
                try:
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = ConfiguracionMesaResponsable.objects.get(pk=id)
                    data['form2'] = EvidenciaActaForm()
                    detallemesas = DetalleMesa.objects.filter(status=True, mesa_responsable=filtro).order_by('pk')
                    for d in detallemesas:
                        totalvotos = Decimal(d.empadronado)
                        totalesregistrados = Decimal(d.ausentismo) + Decimal(d.votovalido) + Decimal(d.votonulo) + Decimal(d.votoblanco)
                        if totalvotos != totalesregistrados:
                            return JsonResponse({"result": False, "mensaje": u"Los votos registrados en {} no concuerdan con la cantidad de personas empadronadas. {} / {}".format(d.gremio_periodo, totalvotos, totalesregistrados)})
                        totalvotos = SubDetalleMesa.objects.filter(status=True, detallemesa=d).aggregate(total=Coalesce(Sum(F('totalvoto'), output_field=IntegerField()), 0)).get('total')
                        if d.votovalido != totalvotos:
                            return JsonResponse({"result": False, "mensaje": u"Los votos registrados por listas en {} no concuerdan con la cantidad de votos validos. {} / {}".format(d.gremio_periodo, d.votovalido, totalvotos)})
                    template = get_template("adm_ingresoacta/cierreacta.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Intentelo más tarde. {ex} - Linea {sys.exc_info()[-1].tb_lineno}"}, safe=False)

            if action == 'validadormesas':
                try:
                    id = request.GET['id']
                    d = DetalleMesa.objects.get(pk=id)
                    totalvotos = Decimal(d.empadronado)
                    totalesregistrados = Decimal(d.ausentismo) + Decimal(d.votovalido) + Decimal(d.votonulo) + Decimal(d.votoblanco)
                    if totalvotos != d.mesa_responsable.totalempadronados:
                        return JsonResponse({"result": False, "mensaje": u"Campo empadronados {} no concuerdan con la cantidad de personas empadronadas en la mesa. {} / {}".format(d.gremio_periodo, totalvotos, d.mesa_responsable.totalempadronados)})
                    if totalvotos != totalesregistrados:
                        return JsonResponse({"result": False, "mensaje": u"Los votos registrados en {} no concuerdan con la cantidad de personas empadronadas. {} / {}".format(d.gremio_periodo, totalvotos, totalesregistrados)})
                    totalvotos = SubDetalleMesa.objects.filter(status=True, detallemesa=d).aggregate(total=Coalesce(Sum(F('totalvoto'), output_field=IntegerField()), 0)).get('total')
                    if d.votovalido != totalvotos:
                        return JsonResponse({"result": False, "mensaje": u"Los votos registrados por listas en {} no concuerdan con la cantidad de votos validos. {} / {}".format(d.gremio_periodo, d.votovalido, totalvotos)})
                    return JsonResponse({"result": True})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Intentelo más tarde. {ex} - Linea {sys.exc_info()[-1].tb_lineno}"}, safe=False)

            if action == 'ingresoacta':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    if not request.user.is_superuser and not ConfiguracionMesaResponsable.objects.filter(status=True, presidente__persona=persona_sesion, pk=id).exists():
                        return redirect('/')

                    data['filtro'] = filtro = ConfiguracionMesaResponsable.objects.get(status=True, pk=id)
                    # if not filtro.periodo.activo_ingreso_acta:
                    #     messages.error(request, 'PERIODO DE ACTAS SE ENCUENTRA CERRADO')
                    # if not filtro.abierta:
                    #     messages.error(request, 'ACTA CERRADA')
                    #     return redirect(request.path)
                    data['title'] = u'INGRESO DE ACTA {}'.format(filtro.periodo.nombre)
                    mesa_responsable = filtro
                    data['mesa_responsable'] = mesa_responsable
                    data['det_dignidades'] = detallemesas = DetalleMesa.objects.filter(status=True, mesa_responsable=mesa_responsable).order_by('pk')
                    for detalle in detallemesas:
                        for lista_gremio in detalle.gremio_periodo.listagremio_set.filter(status=True):
                            if not SubDetalleMesa.objects.filter(detallemesa=detalle, status=True, lista=lista_gremio.lista).exists():
                                sub = SubDetalleMesa(detallemesa=detalle, lista=lista_gremio.lista)
                                sub.save(request)
                    return render(request, "adm_ingresoacta/ingresoacta.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Ingreso de Actas Elecciones.'
                data['eventos'] = even = CabPadronElectoral.objects.filter(status=True).order_by('-pk')
                primerevento = even.first().pk if even.exists() else ''
                url_vars, filtros, evento = '', Q(status=True), request.GET.get('evento', primerevento)
                listado = ConfiguracionMesaResponsable.objects.none()
                # if puedeingresar:
                #     listado = ConfiguracionMesaResponsable.objects.filter(status=True).order_by('tipo', 'mesa__orden')
                # else:
                if request.user.is_superuser:
                    listado = ConfiguracionMesaResponsable.objects.filter(status=True, periodo__activo_ingreso_acta=True).order_by('tipo', 'mesa__orden')
                else:
                    listado = ConfiguracionMesaResponsable.objects.filter(status=True, periodo__activo_ingreso_acta=True, presidente__persona=persona_sesion).order_by('tipo', 'mesa__orden')
                if evento:
                    listado = listado.filter(periodo__id=evento)
                data['listado'] = listado.order_by('tipo', 'mesa__orden')
                data['evento'] = int(evento)
                # data['listado']= DetPersonaPadronElectoral.objects.filter(status=True, persona=persona_sesion, tipo=2, enmesa=True)
                return render(request, "adm_ingresoacta/view.html", data)
            except Exception as ex:
                pass
