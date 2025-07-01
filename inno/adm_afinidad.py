# -*- coding: latin-1 -*-
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template
from django.contrib import messages
from sga.templatetags.sga_extras import encrypt
from django.forms import model_to_dict

from decorators import last_access, secure_module
from inno.funciones import enviar_notificacion_aceptar_rechazar_solicitud_asistencia_pro
from secretaria.models import Solicitud, Servicio
from settings import SOLICITUD_PREPROYECTO_ESTADO_APROBADO_ID, \
    SOLICITUD_PREPROYECTO_ESTADO_RECHAZADO_ID
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log
from sga.models import Profesor, Periodo, Nivel, Malla, AsignaturaMalla
from poli.models import PoliticaPolideportivo
from inno.models import ResultadoAfinidad, DetalleAfinidad, ConfiguracionAfinidad
from inno.forms import ConfiguracionAfinidadForm, DetalleAfinidadForm, ResultadoAfinidadForm, MasivoAsignaturaResultadoForm


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    hoy = datetime.now().date()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addafinidad':
            try:
                with transaction.atomic():
                    form = ConfiguracionAfinidadForm(request.POST)
                    if form.is_valid():
                        if not ConfiguracionAfinidad.objects.values('id').filter(periodo=form.cleaned_data['periodo']).exists():
                            instance = ConfiguracionAfinidad(periodo=form.cleaned_data['periodo'])
                            instance.save(request)
                            log(u'Adicionó Afinidad: %s' % instance, request, "add")
                            messages.success(request, 'Registro guardado con éxito.')
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            raise NameError(u'El registro ya existe.')
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'importarmallas':
            try:
                configafinidad = int(request.POST['idconfigafinidad'])
                afinidad = ConfiguracionAfinidad.objects.get(pk=configafinidad)
                lista = request.POST['lista'].split(',')
                for elemento in lista:
                    if not DetalleAfinidad.objects.filter(configafinidad=afinidad, malla_id=elemento, status=True):
                        detalle = DetalleAfinidad(configafinidad=afinidad,
                                                  malla_id=elemento)
                        detalle.save(request)
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'adddetalleafinidad':
            try:
                with transaction.atomic():
                    form = DetalleAfinidadForm(request.POST)
                    if form.is_valid():
                        if not DetalleAfinidad.objects.values('id').filter(configafinidad_id=int(encrypt(request.POST['id'])), periodo=form.cleaned_data['periodo']).exists():
                            instance = DetalleAfinidad(configafinidad_id=int(encrypt(request.POST['id'])),
                                                       periodo=form.cleaned_data['periodo'])
                            instance.save(request)
                            log(u'Adicionó Detalle Afinidad: %s' % instance, request, "add")
                            messages.success(request, 'Registro guardado con éxito.')
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            raise NameError(u'El registro ya existe.')
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'addresultado':
            try:
                with transaction.atomic():
                    form = ResultadoAfinidadForm(request.POST)
                    if form.is_valid():
                        if int(form.cleaned_data['orden']) < 1:
                            raise NameError(u'El orden debe ser mayor a cero.')
                        if (int(form.cleaned_data['orden']),) in ResultadoAfinidad.objects.values_list('orden').filter(status=True, detafinidad_id=int(encrypt(request.POST['detalle']))):
                            raise NameError(u'El orden ya se encuentra registrado. Debe ser único.')
                        if not ResultadoAfinidad.objects.values('id').filter(detafinidad_id=int(encrypt(request.POST['detalle'])), docente=form.cleaned_data['profesor'], asignaturamalla=form.cleaned_data['asignaturamalla']).exists():
                            instance = ResultadoAfinidad(detafinidad_id=int(encrypt(request.POST['detalle'])),
                                                       docente=form.cleaned_data['profesor'],
                                                       asignaturamalla=form.cleaned_data['asignaturamalla'],
                                                       orden=form.cleaned_data['orden'],
                                                       cumplecampoamplio=form.cleaned_data['campoamplio'],
                                                       cumplecampoespecifico=form.cleaned_data['campoespecifico'],
                                                       cumplecampodetallado=form.cleaned_data['campodetallado'],
                                                       fecha=hoy)
                            instance.save(request)
                            log(u'Adicionó Resultado Afinidad: %s' % instance, request, "add")
                            messages.success(request, 'Registro guardado con éxito.')
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            raise NameError(u'El registro ya existe.')
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'editresultado':
            try:
                with transaction.atomic():
                    filtro = ResultadoAfinidad.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = ResultadoAfinidadForm(request.POST)
                    if f.is_valid():
                        if int(f.cleaned_data['orden']) < 1:
                            raise NameError(u'El docente debe cumplir con un campo.')
                        if (int(f.cleaned_data['orden']),) in ResultadoAfinidad.objects.values_list('orden').filter(detafinidad_id=filtro.detafinidad.id, status=True).exclude(pk=filtro.id):
                            raise NameError(u'El orden ya se encuentra registrado. Debe ser único.')
                        filtro.docente = f.cleaned_data['profesor']
                        filtro.asignaturamalla = f.cleaned_data['asignaturamalla']
                        filtro.orden = f.cleaned_data['orden']
                        filtro.cumplecampoamplio = f.cleaned_data['campoamplio']
                        filtro.cumplecampoespecifico = f.cleaned_data['campoespecifico']
                        filtro.cumplecampodetallado = f.cleaned_data['campodetallado']
                        filtro.save(request)
                        log(u'Editó Resultado Afinidad: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'delafinidad':
            try:
                with transaction.atomic():
                    instancia = ConfiguracionAfinidad.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó Configuración Afinidad: %s' % instancia, request, "delete")
                    messages.success(request, 'Registro eliminado con éxito.')
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'deldetalleafinidad':
            try:
                with transaction.atomic():
                    instancia = DetalleAfinidad.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó Detalle Afinidad: %s' % instancia, request, "delete")
                    messages.success(request, 'Registro eliminado con éxito.')
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'delresultado':
            try:
                with transaction.atomic():
                    instancia = ResultadoAfinidad.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó Resultado Afinidad: %s' % instancia, request, "delete")
                    messages.success(request, 'Registro eliminado con éxito.')
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'generarresultadosmalla':
            try:
                with transaction.atomic():
                    if 'id' in request.POST and int(request.POST['id']) > 0:
                        id = int(request.POST['id'])
                    if 'idmalla' in request.POST and int(request.POST['idmalla']) > 0:
                        idmalla = int(request.POST['idmalla'])
                    if 'idasignatura' in request.POST and int(request.POST['idasignatura']) > 0:
                        idasignatura = int(request.POST['idasignatura'])
                    if 'idperiodo' in request.POST and int(request.POST['idperiodo']) > 0:
                        idperiodo = int(request.POST['idperiodo'])
                    docente = None
                    asignaturamalla = None
                    orden = 0
                    c_amplio = False
                    c_especifico = False
                    c_detallado = False
                    # if id and idperiodo and Malla.objects.values('id').filter(pk=idmalla, status=True):
                    #     eMalla = Malla.objects.get(pk=idmalla, status=True)
                    if idasignatura:
                        # asignaturamalla = eMalla.asignaturamalla_set.filter(status=True)
                        # data['asigcount'] = asignaturamalla.values('id').count()
                        asignatura = AsignaturaMalla.objects.get(pk=int(idasignatura))
                        profesores = Profesor.objects.select_related().filter(status=True, profesordistributivohoras__periodo__id=idperiodo).order_by('id', '-persona__usuario__is_active', 'persona__apellido1', 'persona__apellido2', 'persona__nombres')
                        data['profcount'] = profesores.values('id').count()
                        # for asignatura in asignaturamalla:
                        docente = ''

                        ca_asignatura = asignatura.areaconocimientotitulacion
                        ce_asignatura = asignatura.subareaconocimiento
                        cd_asignatura = asignatura.subareaespecificaconocimiento

                        listadocentescumple = []
                        for pro in profesores:
                            afinidad, ca, ce, cd = pro.persona.mis_titulaciones_afinidad(ca_asignatura, ce_asignatura, cd_asignatura)
                            if afinidad:
                                listadocentescumple.append(pro)
                                    # guarda -- falta fecha
                            # profesor.cantidad_materias2(periodo)
                            # profesor.cantidad_asignaturas(periodo)
                            # profesor.mis_materiastodas(periodo)
                            # persona.mis_titulacionesxgrupo(3)
                            # nivelmalla = NivelMalla.objects.get(pk=int(request.GET['nivelmallaid']))

                            # malla__asignaturamalla__materia__nivel__periodo = periodo

                            # asignatura.es_afin(ca,ce,cd)

                        # if not ResultadoAfinidad.objects.values('id').filter(detafinidad_id=id, docente=docente, asignaturamalla=asignaturamalla).exists():
                        #     instance = ResultadoAfinidad(detafinidad_id=id,
                        #                                docente=docente,
                        #                                asignaturamalla=asignaturamalla,
                        #                                orden=orden,
                        #                                cumplecampoamplio=c_amplio,
                        #                                cumplecampoespecifico=c_especifico,
                        #                                cumplecampodetallado=c_detallado,
                        #                                fecha=hoy)
                        #     instance.save(request)

                        #     return JsonResponse({"result": True, 'msg': 'Convocatoria Duplicada!'})
                        # else:
                        #     raise NameError(u'El registro ya existe.')
                        messages.success(request, 'Proceso ejecutado con éxito. (%s)'%len(listadocentescumple))
                        return JsonResponse({"result": True, 'msg': 'Proceso ejecutado con éxito.'})
                    else:
                        raise NameError(u'No se encontró la malla.')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'msg': '%s'%ex})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'verlistadomalllas':
                try:
                    lista = []
                    afinidad = ConfiguracionAfinidad.objects.get(pk=int(request.GET['idconfigafinidad']))
                    mallasexcluir = DetalleAfinidad.objects.values('malla_id').filter(configafinidad=afinidad, status=True)
                    listadomallas = Malla.objects.filter(vigente=True, status=True).distinct().order_by('-inicio').exclude(
                        pk__in=mallasexcluir)
                    for lis in listadomallas:
                        lista.append([lis.id, str(lis.carrera), lis.inicio])
                    data = {"results": "ok", 'listadomallas': lista}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'addafinidad':
                try:
                    form = ConfiguracionAfinidadForm()
                    periodosexcluir = ConfiguracionAfinidad.objects.values('periodo_id').filter(status=True)
                    form.iniciar(periodosexcluir)
                    data['action'] = 'addafinidad'
                    data['form'] = form
                    template = get_template("adm_afinidaddocente/modal/formconfigafinidad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'adddetalleafinidad':
                try:
                    form = DetalleAfinidadForm()
                    data['action'] = 'adddetalleafinidad'
                    data['id'] = request.GET['id']
                    data['form'] = form
                    template = get_template("adm_afinidaddocente/modal/formconfigafinidad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addresultado':
                try:
                    form = ResultadoAfinidadForm()
                    if 'id' in request.GET and int(request.GET['id']) > 0:
                        data['detalle'] = iddetalle = int(request.GET['id'])
                        detalle = DetalleAfinidad.objects.get(pk=iddetalle)
                        form.iniciar(detalle.malla)
                    data['action'] = 'addresultado'
                    data['form'] = form
                    template = get_template("adm_afinidaddocente/modal/formresultados.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editresultado':
                try:
                    data['id'] = request.GET['id']
                    data['action'] = 'editresultado'
                    data['filtro'] = filtro = ResultadoAfinidad.objects.get(pk=request.GET['id'])
                    form = ResultadoAfinidadForm(initial={'asignaturamalla':filtro.asignaturamalla,
                                                               'profesor':filtro.docente,
                                                               'campoamplio': filtro.cumplecampoamplio,
                                                               'campoespecifico': filtro.cumplecampoespecifico,
                                                               'campodetallado': filtro.cumplecampodetallado,
                                                               'orden': filtro.orden})
                    form.editar(filtro)
                    data['form'] = form
                    template = get_template("adm_afinidaddocente/modal/formresultados.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'viewresultado':
                try:
                    data['title'] = 'Afinidad'
                    data['title1'] = 'Resultado de Afinidad - Docentes '
                    filtro, search, url_vars = Q(status=True), request.GET.get('s', ''), f'&action={action}'

                    periodo = malla = None
                    id = detperiodo = 0
                    asignaturasmalla = []

                    if 'id' in request.GET and request.GET['id']:
                        id = int(request.GET['id'])
                        afinidad = ConfiguracionAfinidad.objects.get(pk=id)
                        url_vars += f'&id={id}'
                        data['idcombom'] = id
                        data['periodoa'] = afinidad.periodo

                    if 'detperiodo' in request.GET:
                        detperiodo = int(request.GET['detperiodo'])
                        url_vars += f'&detperiodo={detperiodo}'
                        data['detperiodo'] = detalle = DetalleAfinidad.objects.get(pk=detperiodo)

                        data['malla'] = malla = Malla.objects.get(pk=detalle.malla.id)
                        asignaturas = malla.asignaturamalla_set.values('id').filter(filtro)
                        data['count'] = asignaturas.count()

                    if id > 0:
                        mallas = DetalleAfinidad.objects.filter(status=True, configafinidad=id)
                        data['listmallasperiodo'] = mallas

                    if search:
                        data['search'] = search
                        filtro = filtro & (Q(asignatura__nombre__icontains=search))
                        url_vars += '&s={}'.format(search)

                    if malla:
                        asignaturasmalla = malla.asignaturamalla_set.filter(filtro)

                    paging = MiPaginador(asignaturasmalla.order_by('asignatura__nombre'), 10)
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
                    data['url_vars'] = url_vars
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['listado'] = page.object_list
                    data['periodolist'] = ConfiguracionAfinidad.objects.filter(status=True).order_by('-periodo').distinct()
                    return render(request, 'adm_afinidaddocente/viewresultados.html', data)
                except Exception as ex:
                    pass

            elif action == 'viewdocentesafines':
                try:
                    if 'idasignaturamalla' in request.GET and 'detperiodo' in request.GET:
                        data['detperiodo'] = det = DetalleAfinidad.objects.get(pk=int(request.GET['detperiodo']))
                        data['asignaturamalla'] = asigm = AsignaturaMalla.objects.get(pk=int(request.GET['idasignaturamalla']))
                        data['docentes'] = datos =ResultadoAfinidad.objects.filter(
                                                    detafinidad=int(request.GET['detperiodo']),
                                                    asignaturamalla=int(request.GET['idasignaturamalla']),
                                                    status=True).order_by("orden", '-cumplecampoamplio', '-cumplecampoespecifico', '-cumplecampodetallado', 'docente')
                    template = get_template("adm_afinidaddocente/modal/viewdocentesafin.html")
                    return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'configuracion':
                try:
                    data['title'] = 'Configuración de Afinidad'
                    filtros, s, url_vars = Q(status=True), request.GET.get('s', ''), f'&action={action}'
                    data['count'] = ConfiguracionAfinidad.objects.values("id").filter(filtros).count()
                    if s:
                        filtros = filtros & (
                                             Q(periodo__nombre__icontains=s)
                                             # Q(malla__carrera__nombre__icontains=s)
                                             )
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"
                    listado = ConfiguracionAfinidad.objects.filter(filtros).order_by('id')
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "adm_afinidaddocente/configurarafinidad.html", data)
                except Exception as ex:
                    pass

            elif action == 'configresultados':
                try:
                    data['title'] = 'Resultados de Afinidad'
                    subtitle1 = subtitle2 = ''
                    filtros, s, m, url_vars = Q(status=True), request.GET.get('s', ''), request.GET.get('m', '0'), f'&action={action}'

                    listado = ResultadoAfinidad.objects.filter(filtros)
                    if 'detalle' in request.GET and int(request.GET['detalle']) > 0:
                        data['detalle'] = iddetalle = int(request.GET['detalle'])
                        listado = listado.filter(detafinidad_id=iddetalle)
                        data['count'] = listado.count()
                        detalle = DetalleAfinidad.objects.get(pk=iddetalle)
                        subtitle1 = str(detalle.configafinidad.periodo)
                        subtitle2 = str(detalle.malla)
                        data['periodo'] = periodo = detalle.configafinidad.periodo
                        data['malla'] = malla = detalle.malla
                        url_vars += f"&detalle={iddetalle}"

                    if s:
                        filtros = filtros & (
                                             Q(asignaturamalla__asignatura__nombre__icontains=s) |
                                             Q(docente__persona__nombres__icontains=s) |
                                             Q(docente__persona__apellido1__icontains=s) |
                                             Q(docente__persona__apellido2__icontains=s) |
                                             Q(docente__persona__cedula__icontains=s)
                                             )
                        ss = s.split(' ')
                        if len(ss) > 1:
                            filtros = filtros & (Q(docente__persona__apellido1__icontains=ss[0]) & Q(docente__persona__apellido2__icontains=ss[1]))
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"

                    listado = listado.filter(filtros)
                    paging = MiPaginador(listado.order_by("orden", '-cumplecampoamplio', '-cumplecampoespecifico', '-cumplecampodetallado', 'docente'), 10)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    data['subtitle1'] = subtitle1
                    data['subtitle2'] = subtitle2
                    return render(request, "adm_afinidaddocente/configresultadosafinidad.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscadocente':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    personas = Profesor.objects.filter(status=True).order_by('persona_id').distinct('persona_id')
                    if len(s) == 1:
                        per = personas.filter((Q(persona__nombres__icontains=q) | Q(persona__apellido1__icontains=q) | Q(
                                                         persona__apellido2__icontains=q) | Q(persona__cedula__contains=q))).distinct()[:15]
                    elif len(s) == 2:
                        per = personas.filter((Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1])) | (
                                                             Q(nombres__icontains=s[0]) & Q(
                                                         persona__nombres__icontains=s[1])) | (
                                                             Q(persona__nombres__icontains=s[0]) & Q(
                                                         persona__apellido1__contains=s[1]))).distinct()[:15]
                    else:
                        per = personas.filter((Q(persona__nombres__contains=s[0]) & Q(persona__apellido1__contains=s[1]) & Q(
                                                         persona__apellido2__contains=s[2])) | (Q(persona__nombres__contains=s[0]) & Q(
                                                         persona__nombres__contains=s[1]) & Q(persona__apellido1__contains=s[2]))).distinct()[:15]

                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": str(x.persona.nombre_completo())}
                                        for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'generarresultadosasignaturamalla':
                try:
                    data['title'] = u'Generar Resultados por Asignatura'
                    form = MasivoAsignaturaResultadoForm()
                    data['form'] = form
                    if 'iddetalle' in request.GET and int(request.GET['iddetalle']) > 0:
                        data['iddetalle'] = iddetalle = int(request.GET['iddetalle'])
                    if 'idperiodo' in request.GET and int(request.GET['idperiodo']) > 0:
                        data['idperiodo'] = idperiodo = int(request.GET['idperiodo'])
                    if 'idmalla' in request.GET and int(request.GET['idmalla']) > 0:
                        data['idmalla'] = idmalla = int(request.GET['idmalla'])
                        form.iniciar(idmalla)
                        template = get_template("adm_afinidaddocente/modal/formgenerarmasivoresultados.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Afinidad'
                periodosesion = periodo
                filtros, s, url_vars = Q(status=True), request.GET.get('s', ''), ''

                id = 0
                if 'id' in request.GET:
                    id = int(request.GET['id'])
                    afinidad = ConfiguracionAfinidad.objects.get(pk=id)
                    data['idcombom'] = afinidad.id
                    data['periodoa'] = afinidad.periodo
                else:
                    data['idcombom'] = periodosesion.id
                    afinidad = ConfiguracionAfinidad.objects.filter(periodo=periodosesion).first()
                    if afinidad:
                        data['periodoa'] = afinidad.periodo
                        id = afinidad.id

                detperiodo = 0
                if 'detperiodo' in request.GET:
                    detperiodo = int(request.GET['detperiodo'])
                    data['detperiodo'] = DetalleAfinidad.objects.get(pk=detperiodo)

                mallas = None
                if id > 0:
                    mallas = DetalleAfinidad.objects.filter(status=True, configafinidad=id)
                data['listmallasperiodo'] = mallas

                data['url_vars'] = url_vars
                data['periodolist'] = ConfiguracionAfinidad.objects.filter(status=True).order_by('-periodo').distinct()
                return render(request, "adm_afinidaddocente/view.html", data)
            except Exception as ex:
                HttpResponseRedirect(f"/?info={ex.__str__()}")
