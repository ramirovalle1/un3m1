# -*- coding: UTF-8 -*-
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template

from decorators import secure_module
from sagest.forms import SolicitudCajaChicaForm
from sagest.models import SolicitudCajaChica, Departamento, \
    SolicitudCajaChicaAprobacion, SolicitudReposicionCajaChica, SolicitudReposicionCajaChicaAprobacion
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log


@login_required(redirect_field_name='ret', login_url='/loginsagest')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if not Departamento.objects.values_list('id', flat=True).filter(responsable=persona).exists():
        return HttpResponseRedirect("/?info=Ud. no esta designado para aprobar cajas chica.")
    data['departamento']= Departamento.objects.filter(responsable=persona)[0]
    departamento = Departamento.objects.values_list('id', flat=True).filter(responsable=persona)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addaprobacion':
            try:
                solicitud = SolicitudCajaChica.objects.get(pk=request.POST['id'])
                esta =int(request.POST['esta'])
                if solicitud.partidacajachica.valorsaldo<=0:
                    return JsonResponse({"result": "bad", "mensaje": u"Lo sentimos ya no tiene saldo"})
                aprobar = SolicitudCajaChicaAprobacion(solicitud=solicitud,
                                            fechaaprobacion=datetime.now().date(),
                                            observacion=request.POST['obse'],
                                            aprueba=persona,
                                            estadosolicitud=esta)
                aprobar.save(request)
                solicitud.actulizar_estado(request)
                # if esta == 1:
                #     solicitud.partidacajachica.valorcomprometido=solicitud.partidacajachica.valorcomprometido+ solicitud.valor if solicitud.partidacajachica.valorcomprometido else solicitud.valor
                #     solicitud.partidacajachica.save()
                # aprobar.mail_notificar_jefe_departamento(request.session['nombresistema'])
                log(u'Aprobar solicitud(Director): %s' % aprobar, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        # if action == 'addaprobacioncomprobante':
        #     try:
        #         comprobante = ComprobanteCajaChica.objects.get(pk=request.POST['id'])
        #         esta =int(request.POST['esta'])
        #         # if comprobante.cajachica.valormaximo<=0:
        #         #     return JsonResponse({"result": "bad", "mensaje": u"Lo sentimos ya no tiene saldo"})
        #         aprobar = ComprobanteCajaChicaAprobacion(solicitud=comprobante,
        #                                     fechaaprobacion=datetime.now().date(),
        #                                     observacion=request.POST['obse'],
        #                                     aprueba=persona,
        #                                     estadosolicitud=esta)
        #         aprobar.save(request)
        #         comprobante.actulizar_estado(request)
        #         # if esta == 1:
        #         #     solicitud.partidacajachica.valorcomprometido=solicitud.partidacajachica.valorcomprometido+ solicitud.valor if solicitud.partidacajachica.valorcomprometido else solicitud.valor
        #         #     solicitud.partidacajachica.save()
        #         # aprobar.mail_notificar_jefe_departamento(request.session['nombresistema'])
        #         log(u'Aprobar solicitud(Director): %s' % aprobar, request, "add")
        #         return JsonResponse({"result": "ok"})
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addaprobacion_reposicion':
            try:
                solicitud = SolicitudReposicionCajaChica.objects.get(pk=request.POST['id'])
                esta = int(request.POST['esta'])
                aprobar = SolicitudReposicionCajaChicaAprobacion(solicitud=solicitud,
                                                       fechaaprobacion=datetime.now().date(),
                                                       observacion=request.POST['obse'],
                                                       aprueba=persona,
                                                       estadosolicitud=esta)
                aprobar.save(request)
                solicitud.actualizar_estado(request)
                log(u'Aprobar solicitud(Director): %s' % aprobar, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addsolicitud':
                try:
                    data['title'] = u'Solicitar'
                    form = SolicitudCajaChicaForm()
                    form.addcustodio(persona)
                    data['form'] = form
                    return render(request, "custodio_cajachica/addsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalle':
                try:
                    data = {}
                    data['solicitud'] = solicitud = SolicitudCajaChica.objects.get(pk=int(request.GET['id']))
                    data['aprobador'] = persona
                    data['fecha'] = datetime.now().date()
                    data['aprobadores'] = solicitud.solicitudcajachicaaprobacion_set.filter(status=True)
                    template = get_template("aprobar_cajachica/detalle_aprobar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'verdetalle':
                try:
                    data = {}
                    data['solicitud'] = solicitud = SolicitudCajaChica.objects.get(pk=int(request.GET['id']))
                    data['aprobadores'] = solicitud.solicitudcajachicaaprobacion_set.filter(status=True)
                    template = get_template("aprobar_cajachica/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            # elif action == 'comprobantes':
            #     try:
            #         data['title'] = u'Comprobantes de caja chica'
            #         search = None
            #         ids = None
            #         departamento = Departamento.objects.values_list('id', flat=True).filter(responsable=persona)
            #         comprobante = ComprobanteCajaChica.objects.filter(status=True,cajachica__departamento__id__in=departamento).exclude(solicita=persona).order_by('-fechasolicitud', '-secuencia')
            #         if 's' in request.GET:
            #             search = request.GET['s']
            #         if search:
            #             comprobante = comprobante.filter(status=True, solicita=persona).filter(
            #                 Q(concepto__contains=search) |
            #                 Q(solicita__cedula__icontains=search) |
            #                 Q(solicita__pasaporte__icontains=search)|
            #                 Q(solicita__nombres__icontains=search) |
            #                 Q(solicita__apellido1__icontains=search) |
            #                 Q(solicita__apellido2__icontains=search)
            #             ).distinct()
            #         elif 'id' in request.GET:
            #             ids = request.GET['id']
            #             comprobante = comprobante.filter(id=ids)
            #         paging = MiPaginador(comprobante, 20)
            #         p = 1
            #         try:
            #             paginasesion = 1
            #             if 'paginador' in request.session:
            #                 paginasesion = int(request.session['paginador'])
            #             if 'page' in request.GET:
            #                 p = int(request.GET['page'])
            #             else:
            #                 p = paginasesion
            #             try:
            #                 page = paging.page(p)
            #             except:
            #                 p = 1
            #             page = paging.page(p)
            #         except:
            #             page = paging.page(p)
            #         request.session['paginador'] = p
            #         data['paging'] = paging
            #         data['rangospaging'] = paging.rangos_paginado(p)
            #         data['page'] = page
            #         data['search'] = search if search else ""
            #         data['ids'] = ids if ids else ""
            #         data['comprobantes'] = page.object_list
            #         return render(request, 'aprobar_cajachica/comprobantes.html', data)
            #     except Exception as ex:
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
            #
            # elif action == 'verdetallecomprobanteaprobar':
            #     try:
            #         data = {}
            #         data['comprobante'] = comprobante = ComprobanteCajaChica.objects.get(pk=int(request.GET['id']))
            #         data['aprobadores'] = comprobante.comprobantecajachicaaprobacion_set.filter(status=True)
            #         template = get_template("aprobar_cajachica/detallecomprobanteaprobar.html")
            #         json_content = template.render(data)
            #         return JsonResponse({"result": "ok", 'data': json_content})
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
            #
            # elif action == 'verdetallecomprobante':
            #     try:
            #         data = {}
            #         data['comprobante'] = comprobante = ComprobanteCajaChica.objects.get(pk=int(request.GET['id']))
            #         data['aprobadores'] = comprobante.comprobantecajachicaaprobacion_set.filter(status=True)
            #         template = get_template("custodio_cajachica/detallecomprobante.html")
            #         json_content = template.render(data)
            #         return JsonResponse({"result": "ok", 'data': json_content})
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'solicitudesreposicion':
                try:
                    data['title'] = u'Solicitudes de Consumo'
                    search = None
                    ids = None
                    solicitudes = SolicitudReposicionCajaChica.objects.filter(status=True, cajachica__departamento__id__in=departamento).order_by('-fechasolicitud', '-secuencia')
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        solicitudes = solicitudes.filter(status=True).filter(
                            Q(secuencia__contains=search) |
                            Q(cajachica_custodio__cedula__icontains=search) |
                            Q(cajachica_custodio__pasaporte__icontains=search)|
                            Q(cajachica_custodio__nombres__icontains=search) |
                            Q(cajachica_custodio__apellido1__icontains=search) |
                            Q(cajachica_custodio__apellido2__icontains=search)
                        ).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        solicitudes = solicitudes.filter(id=ids)
                    else:
                        solicitudes = solicitudes.filter(status=True)
                    paging = MiPaginador(solicitudes, 20)
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
                    data['solicitudes'] = page.object_list
                    return render(request, 'aprobar_cajachica/solicitudesreposicion.html', data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'detalleregistro':
                try:
                    data = {}
                    data['solicitud'] = solicitud = SolicitudReposicionCajaChica.objects.get(pk=int(request.GET['id']))
                    data['comprobantes'] = solicitud.detallecomprobantes()
                    template = get_template("aprobar_cajachica/detalleregistro.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'detallesolicitud1':
                try:
                    data = {}
                    data['solicitud'] = solicitud = SolicitudReposicionCajaChica.objects.get(pk=int(request.GET['id']))
                    data['aprobador'] = persona
                    data['fecha'] = datetime.now().date()
                    data['aprobadores'] = solicitud.solicitudreposicioncajachicaaprobacion_set.filter(status=True)
                    template = get_template("aprobar_cajachica/detalle_aprobarsolicitud1.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'verdetallesolicitud1':
                try:
                    data = {}
                    data['solicitud'] = solicitud = SolicitudReposicionCajaChica.objects.get(pk=int(request.GET['id']))
                    data['aprobadores'] = solicitud.solicitudreposicioncajachicaaprobacion_set.filter(status=True)
                    template = get_template("aprobar_cajachica/detalle_aprobarsolicitud2.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Aprobación de solicitudes de fondo.'
            search = None
            ids = None
            solicitudes=SolicitudCajaChica.objects.filter(status=True,partidacajachica__cajachica__departamento__id__in=departamento).exclude(solicita=persona).order_by('-fechasolicitud', '-secuencia')
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                solicitudes = solicitudes.filter(Q(concepto__contains=search) | Q(solicita__cedula__icontains=search) | Q(solicita__pasaporte__icontains=search)).distinct().order_by('-fechasolicitud', '-secuencia')
            elif 'id' in request.GET:
                ids = request.GET['id']
                solicitudes = solicitudes.filter(id=ids)
            paging = MiPaginador(solicitudes, 20)
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
            data['solicitudescaja'] = page.object_list
            return render(request, 'aprobar_cajachica/view.html', data)

