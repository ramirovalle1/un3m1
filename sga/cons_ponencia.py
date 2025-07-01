# -*- coding: UTF-8 -*-
import json
from googletrans import Translator
from datetime import datetime, date, timedelta, time
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sagest.models import  DistributivoPersona
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, convertir_fecha
from sga.models import ProfesorDistributivoHoras, PlanificarPonencias
from django.db.models import Q
from sga.funcionesxhtml2pdf import conviert_html_to_pdf


@login_required(redirect_field_name='ret',login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    lista = []
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    periodo = request.session['periodo']

    if persona.es_responsablecoordinacion(periodo):
        # DECANO DE FACULTAD
        responsablecoordinacion = persona.responsablecoordinacion(periodo)
        numerocoordinaciones = persona.numero_coordinaciones_asignadas(periodo)
        coordinacion = responsablecoordinacion.coordinacion
        coordinacion2 = None

        if numerocoordinaciones > 1:
            coordinacion2 = persona.coordinacion2(periodo)
            coordinacion2 = coordinacion2.coordinacion

        tipoautoridad = responsablecoordinacion.tipo
    elif persona.es_coordinadorcarrera(periodo):
        # DIRECTOR DE CARRERA
        responsablecarrera = persona.coordinadorcarreras(periodo)
        codigoscarrera = responsablecarrera.values_list('carrera__id', flat=True).filter(status=True)
        coordinacion = responsablecarrera[0].coordinacion()
        tipoautoridad = responsablecarrera[0].tipo
    else:
        return HttpResponseRedirect("/?info=Este modulo solo es para uso de los responsables de carreras, de coordinacion y tesorero general.")

    if request.method == 'POST':
        action = request.POST['action']
        if action == 'verificalistadosolicitud_pdf':
            try:
                if datetime.strptime(request.POST['desde'], '%d-%m-%Y') <= datetime.strptime(request.POST['hasta'], '%d-%m-%Y'):
                    if tipoautoridad == 3:
                        codigosprofesores = ProfesorDistributivoHoras.objects.values_list('profesor__id', flat=True).filter(carrera__id__in=codigoscarrera, periodo=periodo, status=True)
                    else:
                        codigosprofesores1 = coordinacion.profesordistributivohoras_set.values_list('profesor__id', flat=True).filter(periodo=periodo, status=True)

                        codigosprofesores = codigosprofesores1

                        if coordinacion2:
                            codigosprofesores2 = coordinacion2.profesordistributivohoras_set.values_list('profesor__id', flat=True).filter(periodo=periodo, status=True)
                            codigosprofesores = codigosprofesores | codigosprofesores2

                    desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)


                    if PlanificarPonencias.objects.filter(status=True, profesor__id__in=codigosprofesores,
                                                    fecha_creacion__range=(desde, hasta)).order_by('-fecha_creacion').exists():
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse(
                            {"result": "bad", "mensaje": "No existen registros para generar el reporte"})

                else:
                    return JsonResponse({"result": "bad", "mensaje": "La fecha desde debe ser menor o igual a la fecha hasta"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Formatos de fechas incorrectas."})

        elif action == 'listadosolicitud_pdf':
            try:
                data = {}

                if tipoautoridad == 3:
                    codigosprofesores = ProfesorDistributivoHoras.objects.values_list('profesor__id', flat=True).filter(
                        carrera__id__in=codigoscarrera, periodo=periodo, status=True)
                else:
                    codigosprofesores1 = coordinacion.profesordistributivohoras_set.values_list('profesor__id',
                                                                                                flat=True).filter(
                        periodo=periodo, status=True)

                    codigosprofesores = codigosprofesores1

                    if coordinacion2:
                        codigosprofesores2 = coordinacion2.profesordistributivohoras_set.values_list('profesor__id',
                                                                                                     flat=True).filter(
                            periodo=periodo, status=True)
                        codigosprofesores = codigosprofesores | codigosprofesores2

                desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)

                participantes = PlanificarPonencias.objects.filter(status=True, profesor__id__in=codigosprofesores, fecha_creacion__range=(desde, hasta)).order_by('-fecha_creacion', 'profesor__persona__apellido1')

                cargo = DistributivoPersona.objects.filter(persona=persona, status=True).order_by('estadopuesto_id')[0]

                tit1 = tit2 = ""
                tit1dec = None
                dec = persona.titulacion_principal_senescyt_registro()
                if dec != '':
                    tit1dec = persona.titulacion_set.filter(titulo__nivel_id=3).order_by('-fechaobtencion')[0]
                    tit1 = tit1dec.titulo.abreviatura
                    tit1 = tit1 + "." if tit1.find(".") < 0 else tit1

                tit2dec = persona.titulacion_principal_senescyt_registro()
                if tit2dec:
                    tit2 = tit2dec.titulo.abreviatura if tit2dec.titulo.nivel_id == 4 else ''
                    if tit2 != '':
                        tit2 = tit2 + "." if tit2.find(".") < 0 else tit2

                if tit1 != "":
                    if tit2 != "":
                        tit2 = ", " + tit2
                else:
                    if tit2 != "":
                        tit1 = tit2
                        tit2 = ""

                data['desde'] = request.POST['desde']
                data['hasta'] = request.POST['hasta']
                data['titulo1dec'] = tit1
                data['titulo2dec'] = tit2
                data['facultad'] = coordinacion
                data['denominacionpuesto'] = cargo.denominacionpuesto  #"DECANA" if persona.sexo.id == 1 else "DECANO"
                data['participantes'] = participantes
                data['decano'] = persona

                return conviert_html_to_pdf(
                    'cons_ponencia/listadosolicitudgeneral_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )

            except Exception as ex:
                pass

        return HttpResponseRedirect(request.path)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'participantes':
                try:
                    data['title'] = u'Registro de solicitudes para presentar ponencias'

                    if tipoautoridad == 3:
                        codigosprofesores = ProfesorDistributivoHoras.objects.values_list('profesor__id', flat=True).filter(carrera__id__in=codigoscarrera, periodo=periodo, status=True)
                    else:
                        codigosprofesores1 = coordinacion.profesordistributivohoras_set.values_list('profesor__id', flat=True).filter(periodo=periodo, status=True)

                        codigosprofesores = codigosprofesores1

                        if coordinacion2:
                            codigosprofesores2 = coordinacion2.profesordistributivohoras_set.values_list('profesor__id', flat=True).filter(periodo=periodo, status=True)
                            codigosprofesores = codigosprofesores | codigosprofesores2


                    estadosol = int(request.GET['eSol']) if 'eSol' in request.GET else 0
                    fecharep = request.GET['fecharep'] if 'fecharep' in request.GET else ''
                    search = None

                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            if estadosol == 0:
                                participantes = PlanificarPonencias.objects.filter(
                                    Q(profesor__persona__apellido1__icontains=search) | Q(
                                        profesor__persona__apellido2__icontains=search) | Q(
                                        profesor__persona__nombres__icontains=search),
                                    profesor__id__in=codigosprofesores, status=True
                                    ).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                            else:
                                participantes = PlanificarPonencias.objects.filter(
                                    Q(profesor__persona__apellido1__icontains=search) | Q(
                                        profesor__persona__apellido2__icontains=search) | Q(
                                        profesor__persona__nombres__icontains=search),
                                    profesor__id__in=codigosprofesores, status=True, estado=estadosol
                                ).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                        else:
                            if estadosol == 0:
                                participantes = PlanificarPonencias.objects.filter(
                                    Q(profesor__persona__apellido1__icontains=ss[0]) & Q(
                                        profesor__persona__apellido2__icontains=ss[1]),
                                    profesor__id__in=codigosprofesores, status=True
                                    ).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                            else:
                                participantes = PlanificarPonencias.objects.filter(
                                    Q(profesor__persona__apellido1__icontains=ss[0]) & Q(
                                        profesor__persona__apellido2__icontains=ss[1]),
                                    profesor__id__in=codigosprofesores, status=True, estado=estadosol
                                ).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                    else:
                        participantes = PlanificarPonencias.objects.filter(status=True, profesor__id__in=codigosprofesores).order_by(
                            '-fecha_creacion', 'profesor__persona__apellido1')

                    data['totalreg'] = participantes.count()

                    paging = MiPaginador(participantes, 15)
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
                    data['participantes'] = page.object_list
                    data['estadosol'] = estadosol
                    data['fecharep'] = fecharep

                    return render(request, "cons_ponencia/view.html", data)
                except Exception as ex:
                    pass
        else:
            try:
                data['title'] = u'Registro de solicitudes para presentar ponencias'

                if tipoautoridad == 3:
                    codigosprofesores = ProfesorDistributivoHoras.objects.values_list('profesor__id', flat=True).filter(carrera__id__in=codigoscarrera, periodo=periodo, status=True)
                else:
                    codigosprofesores1 = coordinacion.profesordistributivohoras_set.values_list('profesor__id', flat=True).filter(periodo=periodo, status=True)

                    codigosprofesores = codigosprofesores1

                    if coordinacion2:
                        codigosprofesores2 = coordinacion2.profesordistributivohoras_set.values_list('profesor__id', flat=True).filter(periodo=periodo, status=True)
                        codigosprofesores = codigosprofesores | codigosprofesores2

                participantes = PlanificarPonencias.objects.filter(status=True, profesor__id__in=codigosprofesores).order_by('-fecha_creacion', 'profesor__persona__apellido1')

                search = None

                paging = MiPaginador(participantes, 15)
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
                data['participantes'] = page.object_list
                data['fecharep'] = datetime.now().strftime('%d-%m-%Y')

                return render(request, "cons_ponencia/view.html", data)
            except Exception as ex:
                pass