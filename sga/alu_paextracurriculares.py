# -*- coding: UTF-8 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import PaeInscripcionActividadesArchivoForm
from sga.funciones import log, generar_nombre
from django.db.models.query_utils import Q
from sga.models import PaeActividadesPeriodoAreas, PaeInscripcionActividades, Inscripcion, \
    InscripcionActividadesSolicitud


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al módulo.")
    inscripcion = perfilprincipal.inscripcion
    validaadmision = Inscripcion.objects.filter(pk=inscripcion.id, carrera__coordinacion__id=9)
    if validaadmision:
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes que no pertenezcan admisión pueden ingresar al módulo.")
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addinscripcion':
            try:
                matricula = inscripcion.matricula_periodo(periodo)
                actividad = PaeActividadesPeriodoAreas.objects.get(pk=request.POST['idactividad'],status=True)
                # if not PaeInscripcionActividades.objects.values("id").filter(matricula=matricula, status=True, actividades__grupo=actividad.grupo).exists():
                # if not PaeInscripcionActividades.objects.values("id").filter(matricula=matricula, status=True).exists():
                if not actividad.paeinscripcionactividades_set.values("id").filter(matricula=matricula, status=True).exists():
                        totalinscritos = actividad.paeinscripcionactividades_set.values("id").filter(status=True).count()
                        if totalinscritos >= actividad.cupo:
                            return JsonResponse({"result": "bad", "mensaje": u"Lo sentimos, no hay cupo disponible."})
                        inscripcionactividad = PaeInscripcionActividades(matricula=matricula, actividades_id=request.POST['idactividad'])
                        inscripcionactividad.save(request)
                        log(u'Adiciono actividad complementaria: %s' % inscripcionactividad, request, "add")
                        return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Lo sentimos, ya esta inscrito en esta actividad."})
                # else:
                #     return JsonResponse( {"result": "bad", "mensaje": u"Lo sentimos, ya esta inscrito en un grupo de esta actividad."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'deleteinscripcion':
            try:
                participante = PaeInscripcionActividades.objects.get(pk=request.POST['id'])
                participante.status = False
                participante.save(request)
                log(u'elimino actividad complementaria: %s' % participante, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'enviareliminacion':
            try:
                inscripcion=PaeInscripcionActividades.objects.get(status=True,pk=request.POST['id'])
                if not InscripcionActividadesSolicitud.objects.filter(status=True, matricula=inscripcion.matricula,actividades=inscripcion.actividades).exists():
                    solicitud=InscripcionActividadesSolicitud(matricula=inscripcion.matricula,
                                                              actividades=inscripcion.actividades,
                                                              observacion=str(request.POST['observacion']))
                    solicitud.save(request)
                    log(u'Envio solicitud actividad complementaria: %s' % solicitud, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Ya envió solicitud."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addarchivoinscripcion':
            try:
                f = PaeInscripcionActividadesArchivoForm(request.POST, request.FILES)
                # 2.5MB - 2621440
                # 5MB - 5242880
                # 10MB - 10485760
                # 20MB - 20971520
                # 50MB - 5242880
                # 100MB 104857600
                # 250MB - 214958080
                # 500MB - 429916160
                d = request.FILES['archivo']
                if d.size > 10485760:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("codigoQR_", newfile._name)
                        participante = PaeInscripcionActividades.objects.get(pk=request.POST['id'])
                        participante.archivo=newfile
                        participante.save(request)
                        log(u'elimino actividad complementaria: %s' % participante, request, "del")
                        return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'deleteinscripcion':
                try:
                    data['title'] = u'Eliminar Actividad'
                    data['inscripcionextracurricular'] = PaeInscripcionActividades.objects.get(pk=request.GET['idinscripcion'], status=True)
                    return render(request, "alu_paextracurricular/deleteinscripcion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addarchivoinscripcion':
                try:
                    data['inscripcion'] = inscripcion = PaeInscripcionActividades.objects.get(pk=request.GET['id'])
                    data['title'] = u'AÑADIR ARCHIVO INSCRIPCIÓN ' + inscripcion.matricula.inscripcion.persona.nombre_completo_inverso()
                    form = PaeInscripcionActividadesArchivoForm()
                    data['form'] = form
                    return render(request, "alu_paextracurricular/addarchivoinscripcion.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Actividades programadas '
            data['periodo'] = periodo
            data['matricula'] = matricula = inscripcion.matricula_periodo(periodo)
            data['inscrito'] = actividadesinscritas = PaeInscripcionActividades.objects.select_related().filter(matricula__inscripcion=inscripcion, status=True, matricula__status=True).order_by('matricula__nivel__periodo__id')
            inscripciones = actividadesinscritas.filter(matricula=matricula, status=True)
            data['totalinscrito'] = totalinscrito = inscripciones.count()
            totalinscritosalu = inscripciones.filter(actividades__general=False,matricula=matricula, status=True)
            data['totalinscritosalu'] = totalinscritosalu.count()
            data['induccionesabiertas'] = ''
            data['inscripcion'] = inscripcion
            if PaeActividadesPeriodoAreas.objects.filter(coordinacion=inscripcion.coordinacion,general=True ,periodoarea__periodo=periodo, status=True).exists():
                data['induccionesabiertas'] = PaeActividadesPeriodoAreas.objects.values_list('periodoarea__areas__id', flat=True).filter(coordinacion=inscripcion.coordinacion,
                                                                                                                                         general=True, periodoarea__periodo=periodo,
                                                                                                                                         status=True).distinct()

            # if inscripciones.filter(actividades__general=True,matricula=matricula, status=True).exists():
            #     data['actividadesgenerales'] = f =  inscripciones.filter(actividades__general=True,matricula=matricula, status=True)
            #     data['actividadesgeneralesd'] = h = f.values_list('actividades__periodoarea__areas__id')
            data['fechaactual'] = datetime.now().date()
            # idarea = 0
            # if inscripciones:
            #     idarea = inscripciones[0].actividades.periodoarea.areas.id
            # data['idarea'] = idarea
            hoy = datetime.now().date()
            mi_nivel = matricula.nivelmalla
            jornada = None
            if matricula:
                jornada = matricula.nivel
            # actividades = PaeActividadesPeriodoAreas.objects.select_related().filter(((Q(
            #     nivelminimo__id__lte=mi_nivel.nivel.id) & Q(nivelmaximo__id__gte=mi_nivel.nivel.id)) | (Q(
            #     nivelminimo__isnull=True) & Q(nivelmaximo__isnull=True))) & Q(fechafin__gte=hoy) & Q(
            #     coordinacion=inscripcion.coordinacion), Q(periodoarea__periodo=periodo) & Q(status=True) & (Q(
            #     nivel__isnull=True) | Q(nivel=jornada))).order_by('periodoarea__areas__nombre', 'coordinacion', 'nombre')
            actividades = PaeActividadesPeriodoAreas.objects.select_related().filter(((Q(
                 nivelminimo__id__lte=mi_nivel.id) & Q(nivelmaximo__id__gte=mi_nivel.id)) | (Q(
                 nivelminimo__isnull=True) & Q(nivelmaximo__isnull=True))) & Q(fechafin__gte=hoy) & Q(
                 coordinacion=inscripcion.coordinacion), Q(periodoarea__periodo=periodo) & Q(status=True) & (Q(
                 nivel__isnull=True) | Q(nivel=jornada)) & (Q(carrera__isnull=True) | Q(
                 carrera=inscripcion.carrera))).order_by('periodoarea__areas__nombre', 'coordinacion', 'nombre')
            if totalinscrito:
                # fechainicio__lte = hoy, fechafin__gte = hoy,
                # data['actividades'] = PaeActividadesPeriodoAreas.objects.select_related().filter(periodoarea__periodo=periodo, status=True).exclude(pk__in=inscripciones.values('actividades_id')).exclude(periodoarea__areas__id=idarea).order_by('periodoarea__areas__nombre','coordinacion','nombre')
                # data['actividades'] = PaeActividadesPeriodoAreas.objects.select_related().filter(periodoarea__periodo=periodo,periodoarea__areas__id=idarea, status=True).exclude(pk__in=inscripciones.values('actividades_id')).order_by('periodoarea__areas__nombre','coordinacion','nombre')
                # actividades = PaeActividadesPeriodoAreas.objects.select_related().filter(((Q(nivelminimo__id__lte=mi_nivel.nivel.id) &
                #                                                                            Q(nivelmaximo__id__gte=mi_nivel.nivel.id)) |
                #                                                                           (Q(nivelminimo__isnull=True) &
                #                                                                            Q(nivelmaximo__isnull=True))) &
                #                                                                          Q(fechafin__gte=hoy) &
                #                                                                          Q(coordinacion=inscripcion.coordinacion),
                #                                                                          Q(periodoarea__periodo=periodo) &
                #                                                                          Q(status=True) &
                #                                                                          (Q(nivel__isnull=True) |
                #                                                                                            Q(nivel=jornada)) &
                #                                                                          (Q(carrera__isnull=True) |
                #                                                                           Q(carrera=inscripcion.carrera))).exclude(pk__in=inscripciones.values('actividades_id')).order_by('periodoarea__areas__nombre','coordinacion','nombre')
                actividades = actividades.exclude(pk__in=inscripciones.values('actividades_id'))
            # if inscripcion.coordinacion.id == 4:
            #     if inscripcion.carrera.id in [76]:
            #         actividades = actividades.filter(Q(carrera__id=22) & Q(grupo__in=[2, 3, 4]))
            #     elif inscripcion.carrera.id in [77]:
            #         actividades = actividades.filter(Q(carrera__id=22) & Q(grupo__in=[2]))
            #     else:
            #         actividades = actividades.filter(Q(carrera=inscripcion.carrera))
            # else:
            #actividades = PaeActividadesPeriodoAreas.objects.select_related().filter(((Q(nivelminimo__id__lte=mi_nivel.nivel.id) & Q(nivelmaximo__id__gte=mi_nivel.nivel.id)) | (Q(nivelminimo__isnull=True) & Q(nivelmaximo__isnull=True))) &  Q(fechafin__gte=hoy) &  Q(coordinacion=inscripcion.coordinacion), Q(periodoarea__periodo=periodo) &  Q(status=True) & (Q(nivel__isnull=True) | Q(nivel=jornada)) & (Q(carrera__isnull=True) | Q(carrera=inscripcion.carrera))).order_by('periodoarea__areas__nombre','coordinacion','nombre')
            #actividades = actividades.filter(Q(carrera=inscripcion.carrera))
            data['actividades'] = actividades
            return render(request, "alu_paextracurricular/view.html", data)