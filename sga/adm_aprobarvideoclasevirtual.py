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
    AprobacionSemanalVirtual, VirtualLecturasSilabo, VirtualMasRecursoSilabo, VirtualPresencialSilabo, \
    DetalleSilaboSemanalTema, VideoTemaTutor, AprobacionVideoTutor

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
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'ir_temas':
                try:
                    data['materia'] = materia = Materia.objects.get(status=True, id=int(request.POST['id']))
                    detallesemanal = []
                    if materia.silabo_actual() and materia.tiene_silabo_semanal():
                        detallesemanal = DetalleSilaboSemanalTema.objects.filter(silabosemanal__silabo=materia.silabo_actual()).order_by('temaunidadresultadoprogramaanalitico__orden')
                    data['detallesemanal'] = detallesemanal
                    template = get_template("adm_aprobarvideoclasevirtual/temas.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'aprobar':
                try:
                    if 'id' in request.POST:
                        video = VideoTemaTutor.objects.get(status=True, pk=int(request.POST['id']))
                        video.estado = 1
                        video.save(request)
                        aprob = AprobacionVideoTutor(videotutor=video, estado=1, observacion='Ok')
                        aprob.save(request)
                        return JsonResponse({"result": "ok", 'idestado': video.estado, 'estado':video.get_estado_display()})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar el video."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'rechazar':
                try:
                    if 'id' in request.POST and 'observacion' in request.POST:
                        video = VideoTemaTutor.objects.get(status=True, pk=int(request.POST['id']))
                        video.estado=2
                        video.save(request)
                        aprob = AprobacionVideoTutor(videotutor=video, estado=2, observacion=request.POST['observacion'])
                        aprob.save(request)
                        return JsonResponse({"result": "ok", 'idestado': video.estado, 'estado':video.get_estado_display()})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar la semana de planificacion."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'play_video':
                try:
                    if 'id' in request.POST:
                        data['item'] = VideoTemaTutor.objects.get(pk=int(request.POST['id']))
                        template = get_template("adm_aprobarvideoclasevirtual/playvideo.html")
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
                data['title'] = u'Aprobar videos de clases virtuales'
                if not request.session['periodo'].visible:
                    return HttpResponseRedirect("/?info=Periodo Inactivo.")
                profesormaterias = ProfesorMateria.objects.filter(status=True, materia__nivel__periodo=periodo, tipoprofesor_id=7, materia__asignaturamalla__malla__carrera__modalidad=3)
                listaniv = profesormaterias.values_list('materia__asignaturamalla__nivelmalla__id').distinct('materia__asignaturamalla__nivelmalla__id')
                data['mallas'] = malla = Malla.objects.filter(status=True, carrera__modalidad=3).distinct()
                data['nivelmalla'] = NivelMalla.objects.filter(status=True, id__in=listaniv)
                search = None
                mallaid = None
                nivelmallaid = None
                ids = None
                if 'nid' in request.GET:
                    if int(request.GET['nid']) > 0:
                        nivelmallaid = int(request.GET['nid'])
                        profesormaterias = profesormaterias.filter(materia__asignaturamalla__nivelmalla__id=nivelmallaid)
                    else:
                        nivelmallaid = 0
                if 'mid' in request.GET:
                    if int(request.GET['mid']) > 0:
                        mallaid = int(request.GET['mid'])
                        profesormaterias = profesormaterias.filter(materia__asignaturamalla__malla__id=mallaid)
                    else:
                        mallaid = 0
                if 'id' in request.GET:
                    ids = int(request.GET['id'])
                    profesormaterias = profesormaterias.filter(id=int(request.GET['id']))
                if 's' in request.GET:
                    search = request.GET['s']
                    s = search.split(" ")
                    if len(s) == 2:
                        profesormaterias = profesormaterias.filter((Q(materia__asignatura__nombre__icontains=s[0]) & Q(materia__asignatura__nombre__icontains=s[1])) | (Q(profesor__persona__nombres__icontains=s[0]) & Q(profesor__persona__nombres__icontains=s[0])) | (Q(profesor__persona__apellido1__icontains=s[0]) & Q(profesor__persona__apellido2__icontains=s[1])))
                    else:
                        profesormaterias = profesormaterias.filter(Q(materia__asignatura__nombre__icontains=search) | Q(profesor__persona__nombres__icontains=search) | Q(profesor__persona__apellido1__icontains=search)| Q(profesor__persona__apellido2__icontains=search))

                paging = MiPaginador(profesormaterias, 20)
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
                data['profesormaterias'] = page.object_list
                data['search'] = search if search else ""
                data['mid'] = mallaid if mallaid else 0
                data['nid'] = nivelmallaid if nivelmallaid else 0
                data['ids'] = ids
                data['periodo'] = periodo
                data['estados'] = ESTADO_APROBACION_VIRTUAL
                return render(request, "adm_aprobarvideoclasevirtual/view.html", data)
            except Exception as ex:
                pass
