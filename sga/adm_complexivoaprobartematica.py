# -*- coding: UTF-8 -*-
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.funciones import log, generar_nombre, MiPaginador
from sga.models import Tematica, ComplexivoTematica, Carrera, ParticipanteTematica, PeriodoGrupoTitulacion

@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
@last_access

def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    miscarreras = persona.mis_carreras()
    periodo = request.session['periodo']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'aprobartematica':
                try:
                    tematica = Tematica.objects.get(pk=request.POST['id'])
                    lista = json.loads(request.POST['lista'])
                    lista = map(int, lista)
                    participantes = tematica.participantetematica_set.filter(pk__in = lista)
                    carrera = Carrera.objects.get(pk=request.POST['carid'])
                    profesor = None
                    if carrera.coordinadores(periodo):
                        cordinador= carrera.coordinadores(periodo)[0]
                        perfil = cordinador.persona.perfilusuario_profesor()
                    else:
                        return JsonResponse({'result': 'bad', 'mensaje': u'La carrera no tiene asignado un coordinador'})

                    for participante in participantes:
                        complexivotematica = ComplexivoTematica(periodo_id=request.POST['per'] ,tematica= tematica, director=perfil.profesor, tutor= participante, carrera=carrera, cantidadgrupo=0)
                        complexivotematica.save(request)
                        log(u"Aprobo línea de investigación  %s con tutor %s" % (tematica,participante), request, "delete")
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al eliminar participante'})
            elif action == 'deletetematica':
                try:
                    tematica = Tematica.objects.get(pk=request.POST['id'])
                    carrera= Carrera.objects.get(pk=request.POST['carid'])
                    periodo = PeriodoGrupoTitulacion.objects.get(pk=request.POST['perid'])
                    if ComplexivoTematica.objects.filter(tematica=tematica, carrera=carrera, periodo = periodo).exists():
                        comtematica = ComplexivoTematica.objects.filter(tematica=tematica, carrera=carrera, periodo = periodo)
                        for com in comtematica:
                            if com.tiene_grupos():
                                return JsonResponse({'result': 'bad', 'mensaje': u'La tematica ya se encuentra en uso.'})
                        ComplexivoTematica.objects.filter(tematica=tematica, carrera=carrera, periodo = periodo).delete()
                        log(u"Elimino línea de investigación : %s" % tematica, request, "delete")
                        # tematica.participantetematica_set.all().update(estutor=False)
                        return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al eliminar tematica'})
            elif action == 'deletetutor':
                try:
                    participante = ParticipanteTematica.objects.get(pk=request.POST['id'])
                    carrera = Carrera.objects.get(pk=request.POST['carid'])
                    periodo = PeriodoGrupoTitulacion.objects.get(pk=request.POST['perid'])
                    if ComplexivoTematica.objects.filter(status=True, tematica=participante.tematica, tutor= participante, carrera=carrera, periodo=periodo).exists():
                        comtematica = ComplexivoTematica.objects.get(status=True,tematica=participante.tematica, tutor=participante,carrera=carrera, periodo=periodo)
                        if comtematica.tiene_grupos():
                            return JsonResponse({'result': 'bad','mensaje': u'Ya se encuentra como acompañante de un grupo de estudiantes'})
                        comtematica.delete()
                        log(u"Elimino tutor de línea de investigación : %s" % participante, request, "delete")
                        return JsonResponse({'result': 'ok'})
                    else:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al eliminar tutor'})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al eliminar tutor'})
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'acompanates':
                try:
                    data['tematica'] = tematica = Tematica.objects.get(pk=request.GET['id'])
                    data['grupo'] = tematica.grupo
                    data['participantes'] = tematica.participantetematica_set.filter(status=True, participante__persona__profesor__isnull=False).order_by('id')
                    template = get_template("adm_complexivoaprobartematica/acompanantes.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
            elif action == 'deletetematica':
                try:
                    data['title'] = u"Eliminar línea de investigación"
                    data['tematica'] = Tematica.objects.get(pk=request.GET['id'])
                    data['periodo'] = PeriodoGrupoTitulacion.objects.get(pk=request.GET['per'])
                    data['carrera'] = Carrera.objects.get(pk=request.GET['car'])
                    data['vigente'] = request.GET['vigente']
                    return render(request, "adm_complexivoaprobartematica/deletetematica.html", data)
                except Exception as ex:
                    pass
            elif action == 'tutores':
                try:
                    data['title'] = u"Acompañantes"
                    data['tematica'] = tematica = Tematica.objects.get(pk=request.GET['id'])
                    data['grupo'] = tematica.grupo
                    data['perid']=request.GET['per']
                    data['carid']=request.GET['car']
                    data['participantes'] = tematica.participantetematica_set.filter(status=True, participante__persona__profesor__isnull=False).order_by('id')
                    return render(request, "adm_complexivoaprobartematica/tutortematica.html", data)
                except Exception as ex:
                    pass
            elif action == 'deletetutor':
                try:
                    data['title'] = u"Eliminar Acompañante"
                    data['participante'] = participante = ParticipanteTematica.objects.get(pk=request.GET['id'])
                    data['perid'] = request.GET['perid']
                    data['carid'] = request.GET['carid']
                    data['tematica'] = participante.tematica
                    return render(request, "adm_complexivoaprobartematica/deletetutor.html", data)
                except Exception as ex:
                    pass
            elif action =='asignartutor':
                try:
                    participante = ParticipanteTematica.objects.get(pk=request.GET['id'])

                    if ComplexivoTematica.objects.filter(status=True, periodo_id=request.GET['perid'], tematica=participante.tematica).exists():
                        comtematica = ComplexivoTematica(periodo_id=request.GET['perid'], tematica = participante.tematica, tutor= participante, carrera_id=request.GET['carid'])
                        comtematica.save(request)
                    data['tematica'] = tematica = participante.tematica
                    data['grupo'] = tematica.grupo
                    return HttpResponseRedirect("/adm_aprobartematica?action=tutores&id="+str(tematica.id)+"&per="+str(request.GET['perid'])+"&car="+str(request.GET['carid']))
                except Exception as ex:
                    pass
        else:
            try:
                data['title'] = u'Línea de investigación y tutores'
                search = None
                ids = None
                periodo = request.session['periodo']
                if Carrera.objects.filter(coordinadorcarrera__in=persona.gruposcarrera(periodo)).exists():
                    miscarreras = Carrera.objects.filter(coordinadorcarrera__in=persona.gruposcarrera(periodo)).distinct()
                miscarreras = miscarreras.filter(propuestalineainvestigacion_carrera__isnull=False).distinct()
                data['miscarreras'] = miscarreras
                periodotitulacion = int(request.GET['per']) if 'per' in request.GET else 0
                carreraselecionada = int(request.GET['car']) if 'car' in request.GET else 0
                tematicas = Tematica.objects.filter(status=True).order_by('id')
                list = []
                carrera = 0
                if carreraselecionada > 0:
                    data['carid'] = carrera = miscarreras.get(pk=carreraselecionada)
                else:
                    if miscarreras:
                        data['carid'] = carrera = miscarreras[0]
                for tema in tematicas:
                    if tema.pertenece_carrera(carrera):
                        list.append(tema.id)
                list_tematicas = Tematica.objects.filter(status=True, pk__in=list).order_by('tipopublicacion__id').distinct()
                vigente = 1
                if 'vigente' in request.GET:
                    vigente = int(request.GET['vigente'])
                data['vigente'] = vigente
                if vigente == 1:
                    list_tematicas = list_tematicas.filter(vigente=True, grupo__vigente=True).order_by('tipopublicacion__id').distinct()
                elif vigente == 2:
                    list_tematicas = list_tematicas.filter(vigente=False).order_by('tipopublicacion__id').distinct()
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        list_tematicas = list_tematicas.filter(tema__icontains=search).order_by('tipopublicacion__id').distinct()
                    elif len(ss) == 2:
                        list_tematicas = list_tematicas.filter(Q(tema__icontains=ss[0]), Q(tema__icontains=ss[1])).order_by('tipopublicacion__id').distinct()
                    else:
                        list_tematicas = list_tematicas.filter(Q(tema__icontains=ss[0]), Q(tema__icontains=ss[1]),  Q(tema__icontains=ss[2])).order_by('tipopublicacion__id').distinct()
                paging = MiPaginador(list_tematicas, 10)
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
                data['tematicas'] = page.object_list
                data['titperiodos'] = periodos = PeriodoGrupoTitulacion.objects.filter(status=True).order_by('-id')
                if periodotitulacion > 0:
                    data['perid'] = PeriodoGrupoTitulacion.objects.get(pk=periodotitulacion)
                else:
                    data['perid'] = periodos[0]
                return render(request, "adm_complexivoaprobartematica/listtematica.html", data)
            except Exception as ex:
                pass