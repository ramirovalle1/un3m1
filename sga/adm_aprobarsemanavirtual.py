# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
import random
import xlwt
from django.template.context import Context
from django.template.loader import get_template
from xlwt import *
from decorators import secure_module, last_access
from settings import ARCHIVO_TIPO_SYLLABUS
from sga.commonviews import adduserdata
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.forms import ArchivoForm
from sga.funciones import MiPaginador, log, variable_valor
from sga.models import Archivo, ProfesorMateria, Carrera, Materia, \
    Malla, NivelMalla, ESTADO_APROBACION_VIRTUAL, TIPO_RECURSOS, TIPO_LINK, TIPO_ACTIVIDAD, SilaboSemanal, \
    AprobacionSemanalVirtual, VirtualLecturasSilabo, VirtualMasRecursoSilabo, VirtualPresencialSilabo


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    miscarreras = Carrera.objects.filter(coordinadorcarrera__in=persona.gruposcarrera(periodo)).distinct()
    miscoordinaciones = Carrera.objects.filter(grupocoordinadorcarrera__group__in=persona.grupos()).distinct()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'semanas':
                try:
                    data['materia'] = materia = Materia.objects.get(status=True, id=int(request.POST['id']))
                    data['semanas'] = materia.silabo_actual().silabosemanal_set.filter(status=True).order_by('numsemana')
                    data['tiporecurso'] = TIPO_RECURSOS
                    data['tipolink'] = TIPO_LINK
                    data['tipoactividad'] = TIPO_ACTIVIDAD
                    template = get_template("adm_aprobarsemanavirtual/semanas.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'aprobarsemana':
                try:
                    if 'id' in request.POST:
                        semana = SilaboSemanal.objects.get(status=True, pk=int(request.POST['id']))
                        semana.estado=1
                        semana.save(request)
                        aprob = AprobacionSemanalVirtual(silabosemanal=semana, estado=1, observacion='Ok')
                        aprob.save(request)
                        return JsonResponse({"result": "ok", 'idestado': semana.estado, 'estado':semana.get_estado_display()})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar la semana de planificacion."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'rechazarsemana':
                try:
                    if 'id' in request.POST and 'observacion' in request.POST:
                        semana = SilaboSemanal.objects.get(status=True, pk=int(request.POST['id']))
                        semana.estado=2
                        semana.save(request)
                        aprob = AprobacionSemanalVirtual(silabosemanal=semana, estado=2, observacion=request.POST['observacion'])
                        aprob.save(request)
                        return JsonResponse({"result": "ok", 'idestado': semana.estado, 'estado':semana.get_estado_display()})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar la semana de planificacion."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'detalle_lectura':
                try:
                    if 'id' in request.POST:
                        data['item'] = VirtualLecturasSilabo.objects.get(pk=int(request.POST['id']))
                        template = get_template("adm_aprobarsemanavirtual/detallelectura.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'detalle_recurso':
                try:
                    if 'id' in request.POST:
                        data['item'] = VirtualMasRecursoSilabo.objects.get(pk=int(request.POST['id']))
                        template = get_template("adm_aprobarsemanavirtual/detallerecurso.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'detalle_presencialv':
                try:
                    if 'id' in request.POST:
                        data['item'] = VirtualPresencialSilabo.objects.get(pk=int(request.POST['id']))
                        template = get_template("adm_aprobarsemanavirtual/detallepresncialvirtual.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
                action = request.GET['action']
        else:
            try:
                data['title'] = u'Aprobar planificacion semanal modalidad virtual'
                if not request.session['periodo'].visible:
                    return HttpResponseRedirect("/?info=Periodo Inactivo.")
                # data['mallas'] = malla = Malla.objects.filter(carrera__in=persona.mis_carreras()).distinct()
                # data['mallas'] = malla = Malla.objects.filter(status=True, carrera__modalidad=3).distinct()
                data['mallas'] = malla = Malla.objects.filter(status=True).distinct()
                data['nivelmalla'] = NivelMalla.objects.filter(status=True)
                search = None
                mallaid = None
                nivelmallaid = None
                ids = None
                # if miscarreras:
                #     materias = Materia.filter(asignaturamalla__malla__carrera__in=miscarreras)
                # else:
                #     materias = Materia.filter(asignaturamalla__malla__carrera__in=persona.mis_carreras())
                materias = Materia.objects.filter(status=True, asignaturamalla__malla__in=malla, nivel__periodo=periodo)
                if 'nid' in request.GET:
                    if int(request.GET['nid']) > 0:
                        nivelmallaid = int(request.GET['nid'])
                        materias = materias.filter(asignaturamalla__nivelmalla__id=nivelmallaid)
                    else:
                        nivelmallaid = 0
                if 'mid' in request.GET:
                    if int(request.GET['mid']) > 0:
                        mallaid = int(request.GET['mid'])
                        materias = materias.filter(asignaturamalla__malla__id=mallaid)
                    else:
                        mallaid = 0
                if 'id' in request.GET:
                    ids = int(request.GET['id'])
                    materias = materias.filter(materia__id=int(request.GET['id']))
                if 's' in request.GET:
                    search = request.GET['s']
                    s = search.split(" ")
                    if len(s) == 2:
                        materias = materias.filter((Q(asignatura__nombre__icontains=s[0]) & Q(asignatura__nombre__icontains=s[1])))
                    else:
                        materias = materias.filter(Q(asignatura__nombre__icontains=search))

                paging = MiPaginador(materias, 20)
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
                data['materias'] = page.object_list
                data['search'] = search if search else ""
                data['mid'] = mallaid if mallaid else 0
                data['nid'] = nivelmallaid if nivelmallaid else 0
                data['ids'] = ids
                data['periodo'] = periodo
                data['estados'] = ESTADO_APROBACION_VIRTUAL
                return render(request, "adm_aprobarsemanavirtual/view.html", data)
            except Exception as ex:
                pass
