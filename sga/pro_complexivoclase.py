# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.core.paginator import Paginator
from sga.commonviews import adduserdata
from sga.forms import ContenidoAcademicoForm
from decorators import secure_module, last_access
from sga.funciones import log
from sga.models import ComplexivoLeccion, ComplexivoClase, ComplexivoParticipanteClase, ComplexivoMateria, \
    PeriodoGrupoTitulacion, ComplexivoAsignatura, ComplexivoMateriaAsignada


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    perfilprincipal = request.session['perfilprincipal']
    profesor = perfilprincipal.profesor
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'nuevaleccion':
                try:
                    # clase = ComplexivoClase.objects.get(pk=request.POST['clase'])
                    # if ComplexivoLeccion.objects.filter(clase=clase, abierta=True).exists():
                    # clase = ComplexivoClase.objects.get(pk=request.POST['clase'])
                    if ComplexivoLeccion.objects.filter(clase__materia__profesor__profesorTitulacion=profesor, abierta=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Existe una clase abierta, verificar en el módulo Mis Horarios -> botón Continuar y proceda a cerrar la clase."})
                    fecha = datetime.now().date()
                    # enviar automaticamente el pk
                    listaleccion = []
                    if not ComplexivoLeccion.objects.filter(clase__in=[int(x) for x in request.POST['clases'].split(',')], fecha=fecha).exists():
                        clases = ComplexivoClase.objects.filter(id__in=[int(x) for x in request.POST['clases'].split(',')])
                        for clase in clases:
                            leccion = ComplexivoLeccion(clase=clase,
                                              fecha=fecha,
                                              horaentrada=datetime.now().time(),
                                              abierta=True,
                                              contenido='SIN CONTENIDO',
                                              estrategiasmetodologicas='SIN CONTENIDO',
                                              observaciones='SIN CONTENIDO')
                            leccion.save(request)
                            listaleccion.append(leccion.id)
                            log(u"Adiciono leccion: %s" % leccion, request, "add")
                            # materia = ComplexivoMateria.objects.get(pk=clase.materia_id)
                            # asignados = materia.complexivomateriaasignada_set.filter(matricula__estado=1)
                            inscritos = clase.materia.complexivomateriaasignada_set.filter(status=True, matricula__estado=1)
                            for materiaasignada in inscritos:
                                participanteclase = ComplexivoParticipanteClase(leccion=leccion,
                                                                                materiaasignada=materiaasignada,
                                                                                asistencia=True
                                                                            )
                                participanteclase.save(request)
                                log(u"Adiciono estudiante a la clase: %s" % participanteclase, request, "add")
                            # for materiaasignada in asignados:
                            #     participanteclase = ComplexivoParticipanteClase(leccion=leccion,
                            #                                                     materiaasignada=materiaasignada,
                            #                                                     asistencia=True
                            #                                                 )
                            #     participanteclase.save(request)
                            #     log(u"Adiciono estudiante a la clase: %s" % participanteclase, request, "add")
                        return JsonResponse({"result": "ok", "lec": listaleccion})
                    else:
                        # return JsonResponse({"result": "bad","mensaje": u"Existe una clase registrada en esa fecha en el turno seleccionado."})
                        lecciones = ComplexivoLeccion.objects.filter(clase__in=[int(x) for x in request.POST['clases'].split(',')], fecha=fecha)
                        for leccion in lecciones:
                            leccion.abierta = True
                            leccion.save(request)
                            listaleccion.append(leccion.id)
                            log(u"Abrio leccion : %s" % leccion, request, "open")
                        return JsonResponse({"result": "ok", "lec": listaleccion})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al abrir la clase."})

            if action == 'asistencia':
                try:
                    lecciones = ComplexivoLeccion.objects.filter(id__in=[int(x) for x in request.POST['leccionesid'].split(',')])
                    if puede_cerrar_clases(lecciones):
                        lecciones.update(abierta=False)
                        return JsonResponse({"result": "close"})
                    else:
                        asistencia = ComplexivoParticipanteClase.objects.get(pk=request.POST['id'])
                        asistencia.asistencia = request.POST['val'] == 'y'
                        asistencia.save(request)
                        log(u"Adiciono asistencia: %s" % asistencia, request, "add")
                        materiaasignada = asistencia.materiaasignada
                        materiaasignada.save(actualiza=True)
                        presentes = ComplexivoParticipanteClase.objects.filter(leccion=asistencia.leccion, asistencia=True, materiaasignada__matricula__estado=1).distinct().count()
                        ausentes=ComplexivoParticipanteClase.objects.filter(leccion=asistencia.leccion, asistencia=False, materiaasignada__matricula__estado=1).distinct().count()
                        totalasistencias=ComplexivoParticipanteClase.objects.filter(leccion=asistencia.leccion, materiaasignada__matricula__estado=1).distinct().count()
                        return JsonResponse({"result": "ok", "porcientoasist":materiaasignada.asistenciafinal,"presentes":presentes,"ausentes":ausentes, "totalasistencias":totalasistencias})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al abrir la clase."})

            if action == 'asistenciagrupo':
                try:
                    lecciones = ComplexivoLeccion.objects.filter(id__in=[int(x) for x in request.POST['leccionesid'].split(',')])
                    if puede_cerrar_clases(lecciones):
                        lecciones.update(abierta=False)
                    else:
                        participantes = ComplexivoParticipanteClase.objects.filter(leccion__id__in=lecciones.values_list("id", flat=False).all())
                        porasignarasistencias = participantes.filter(asistencia=False)
                        for parct in porasignarasistencias:
                            parct.asistencia = True
                            parct.save(request)
                            parct.materiaasignada.save(actualiza=True)
                            log(u"Adicionó la asistencia a : %s" % parct.materiaasignada.matricula.inscripcion.persona, request, "add")

                    # leccion = ComplexivoLeccion.objects.get(pk=request.POST['id'])
                    # grupo = ComplexivoParticipanteClase.objects.filter(leccion = leccion)
                    # for asistencia in grupo:
                    #     asistencia.asistencia = True
                    #     asistencia.save(request)
                    #     materiaasignada = asistencia.materiaasignada
                    #     materiaasignada.save(actualiza=True)
                    #     log(u"Adiciono asistencia: %s" % asistencia, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al abrir la clase."})

            if action == 'observaciones':
                try:
                    lecciones = ComplexivoLeccion.objects.filter(id__in=[int(x) for x in request.POST['id'].split(',')])
                    if puede_cerrar_clases(lecciones):
                        lecciones.update(abierta=False)
                    else:
                        for leccion in lecciones:
                            leccion.observaciones = request.POST['val']
                            leccion.save(request)
                            log(u"Adiciono observacion: %s" % leccion, request, "add")
                    return JsonResponse({"result": "ok"})
                    # leccion = ComplexivoLeccion.objects.get(pk=request.POST['id'])
                    # leccion.observaciones = request.POST['val']
                    # leccion.save(request)
                    # log(u"Adiciono observacion: %s" % leccion, request, "add")
                    # return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar datos."})
            if action == 'contenido':
                try:
                    lecciones = ComplexivoLeccion.objects.filter(id__in=[int(x) for x in request.POST['id'].split(',')])
                    if puede_cerrar_clases(lecciones):
                        lecciones.update(abierta=False)
                    else:
                        for leccion in lecciones:
                            leccion.contenido = request.POST['val']
                            leccion.save(request)
                            log(u"Adiciono contenido: %s" % leccion, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar datos."})

            if action == 'estrategiasmetodologicas':
                try:
                    lecciones = ComplexivoLeccion.objects.filter(id__in=[int(x) for x in request.POST['id'].split(',')])
                    if puede_cerrar_clases(lecciones):
                        lecciones.update(abierta=False)
                    else:
                        for leccion in lecciones:
                            leccion.estrategiasmetodologicas = request.POST['val']
                            leccion.save(request)
                            log(u"Adiciono estrategia metodologica: %s" % leccion, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar datos."})

            if action == 'cerrar':
                try:
                    lecciones = ComplexivoLeccion.objects.filter(id__in=[int(x) for x in request.POST['leccionesid'].split(',')])
                    for leccion in lecciones:
                        leccion.abierta= False
                        leccion.horasalida = datetime.now().time()
                        leccion.save(request)
                        log(u"Cerro leccion: %s" % leccion, request, "add")
                    # leccion = ComplexivoLeccion.objects.get(pk=request.POST['id'])
                    # if not leccion.contenido:
                    #     return JsonResponse({"result": "bad", "motivo": "contenido"})
                    # if leccion.abierta:
                    #     leccion.abierta = False
                    #     leccion.horasalida = datetime.now().time()
                    #     leccion.save(request)
                    #     log(u"Cerro leccion: %s" % leccion, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad"})

            elif action == 'contenidoacademico':
                try:
                    form = ContenidoAcademicoForm(request.POST)
                    if form.is_valid():
                        leccion = ComplexivoLeccion.objects.get(pk=request.POST['id'])
                        leccion.contenido = form.cleaned_data['contenido']
                        leccion.estrategiasmetodologicas = form.cleaned_data['estrategiasmetodologicas']
                        leccion.observaciones = form.cleaned_data['observaciones']
                        leccion.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'deleteleccion':
                try:
                    lecciones = ComplexivoLeccion.objects.filter(id__in=[int(x) for x in request.POST['id'].split(',')])
                    participantes = ComplexivoParticipanteClase.objects.filter(leccion_id__in=lecciones.values_list("id", flat=False))
                    for part in participantes:
                        log(u'Eliminó la asistencia del complexivo, del estudiante: %s, materia: %s fecha de la asistencia: %s' % (part.materiaasignada.matricula.inscripcion,part.materiaasignada.materia.asignatura.nombre,part.leccion.fecha), request, "del")
                    # participantes.delete()
                    materiasid =[int(x.clase.materia.id) for x in lecciones]
                    for leccion in lecciones:
                        log(u'Eliminó lección: %s' % leccion, request, "del")
                    # lecciones.delete()
                    for materiaasignada in ComplexivoMateriaAsignada.objects.filter(materia_id__in=[int(x.clase.materia.id) for x in lecciones], materia__status=True):
                        materiaasignada.save(actualiza=True)
                    # leccion = ComplexivoLeccion.objects.get(pk=request.POST['id'])
                    # leccion.complexivoparticipanteclase_set.all().delete()
                    # materia = leccion.clase.materia
                    # leccion.delete(request)
                    # for materiaasignada in materia.complexivomateriaasignada_set.filter(matricula__estado=1):
                    #     materiaasignada.save(actualiza=True)
                    # log(u'Elimino leccion: %s' % leccion, request, "delete")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Listado de clases impartidas'
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'view':
                try:
                    data['title'] = u'Lección'
                    # leccion = ComplexivoLeccion.objects.get(pk=request.GET['id'])
                    leccion = ComplexivoLeccion.objects.filter(id__in=[int(x) for x in request.GET['listaleccionid'].split(',')])
                    data['leccionagrupada'] = ComplexivoLeccion.objects.filter(id__in=[int(x) for x in request.GET['listaleccionid'].split(',')]).distinct('clase__aula')[0]
                    data['lecciones'] = leccion
                    data['presentes'] = ComplexivoParticipanteClase.objects.filter(leccion_id__in=leccion.values_list("id",flat=False),asistencia=True,materiaasignada__matricula__estado=1).distinct().count()
                    data['ausentes'] = ComplexivoParticipanteClase.objects.filter(leccion_id__in=leccion.values_list("id",flat=False),asistencia=False,materiaasignada__matricula__estado=1).distinct().count()
                    data['totalasistencias'] = ComplexivoParticipanteClase.objects.filter(leccion_id__in=leccion.values_list("id",flat=False),materiaasignada__matricula__estado=1).distinct().count()
                    data['leccionesabiertas'] = leccion.values("id").filter(abierta=True).count() == leccion.values("id").count()
                    return render(request, "pro_complexivoclase/leccioncomplexivo1.html", data)
                except Exception as ex:
                    pass
            elif action == 'contenidoacademico':
                try:
                    data['title'] = u'Contenido academico'
                    data['leccion'] = leccion = ComplexivoLeccion.objects.get(pk=request.GET['id'])
                    data['form'] = ContenidoAcademicoForm(initial={'contenido': leccion.contenido,
                                                                   'estrategiasmetodologicas': leccion.estrategiasmetodologicas,
                                                                   'observaciones': leccion.observaciones})
                    return render(request, "pro_complexivoclase/contenidoacademico.html", data)
                except Exception as ex:
                    pass
            elif action == 'deleteleccion':
                try:
                    data['title'] = u'Eliminar la asistencia de clases'
                    data['lecciones'] = ComplexivoLeccion.objects.filter(id__in=[int(x) for x in request.GET['listaleccionid'].split(',')])
                    data['listaleccionid'] = request.GET['listaleccionid']
                    return render(request, "pro_complexivoclase/deleteleccion.html", data)
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u"Listado de clases impartidas complexivo"
            # data['materias'] = ComplexivoAsignatura.objects.filter(status=True)
            data['periodotitulacion'] = PeriodoGrupoTitulacion.objects.filter(status=True).order_by('-id')
            data['materias'] = ComplexivoMateria.objects.filter(status=True, profesor__profesorTitulacion=profesor, alternativa__grupotitulacion__periodogrupo__fechafin__gt=datetime.now().date()).order_by('id')
            periodo = int(request.GET['per']) if 'per' in request.GET  else 0
            materia = int(request.GET['mat']) if 'mat' in request.GET else 0
            lecciones = ComplexivoLeccion.objects.filter(clase__materia__profesor__profesorTitulacion=profesor, clase__materia__alternativa__grupotitulacion__periodogrupo__fechafin__gt=datetime.now().date()).distinct('clase__aula','clase__materia__asignatura', 'clase__turno', 'horaentrada')
            if periodo > 0:
                lecciones = lecciones.filter(clase__materia__alternativa__grupotitulacion__periodogrupo=periodo)
                data['materias'] = ComplexivoMateria.objects.filter(status=True, profesor__profesorTitulacion=profesor, alternativa__grupotitulacion__periodogrupo=periodo).order_by('id')
                data['per_id'] = PeriodoGrupoTitulacion.objects.get(pk=periodo)
            if materia > 0:
                lecciones= lecciones.filter(clase__materia__id=materia)
                # data ['mat_id']= ComplexivoAsignatura.objects.get(pk=materia)
                data['mat_id'] = ComplexivoMateria.objects.get(pk=materia)
            paging = Paginator(lecciones, 30)
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
            data['lecciones'] = page.object_list
            data['profesor']= profesor
            return render(request, "pro_complexivoclase/listar.html", data)

def puede_cerrar_clases(lecciones):
    cerrar=0
    for clase in ComplexivoClase.objects.filter(id__in=lecciones.values_list("clase_id", flat=False)):
        if not (datetime.now().time() >= clase.turno.comienza and datetime.now().time() <= clase.turno.comienza):
            cerrar = 1
            break
    if cerrar == 0:
        return  True
    else:
        return False
