# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponseRedirect, JsonResponse
from django.db import transaction
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import ProgramaVinculacionForm, ProyectoVinculacionForm, ProfesorVinculacionForm
from sga.funciones import MiPaginador, log, puede_realizar_accion
from sga.models import Programa, ProyectosVinculacion, ParticipanteProyectoVinculacion, ProfesorProyectoVinculacion, LimiteProyectoVinculacion, \
    Inscripcion, null_to_numeric


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'edit':
                try:
                    f = ProgramaVinculacionForm(request.POST)
                    if f.is_valid():
                        programa = Programa.objects.get(pk=request.POST['id'])
                        programa.nombre = f.cleaned_data['nombre']
                        programa.inicio = f.cleaned_data['inicio']
                        programa.fin = f.cleaned_data['fin']
                        programa.objetivo = f.cleaned_data['objetivo']
                        programa.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'del':
                try:
                    programa = Programa.objects.get(pk=request.POST['id'])
                    if programa.proyectosvinculacion_set.exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Existen proyectos dentro del programa."})
                    log(u"Elimino programa: %s" % programa, request, "del")
                    programa.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'delproyecto':
                try:
                    proyecto = ProyectosVinculacion.objects.get(pk=request.POST['id'])
                    if proyecto.participanteproyectovinculacion_set.exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Existen participantes resgistrados."})
                    log(u"Elimino proyecto: %s" % proyecto, request, "del")
                    proyecto.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'retirar':
                try:
                    participante = ParticipanteProyectoVinculacion.objects.get(pk=request.POST['id'])
                    log(u"Elimino participante de proyecto: %s" % participante, request, "del")
                    participante.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'delprofesor':
                try:
                    profesor = ProfesorProyectoVinculacion.objects.get(pk=request.POST['id'])
                    log(u"Elimino profesor de proyecto: %s" % profesor, request, "del")
                    profesor.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'add':
                try:
                    f = ProgramaVinculacionForm(request.POST)
                    if f.is_valid():
                        programa = Programa(nombre=f.cleaned_data['nombre'],
                                            inicio=f.cleaned_data['inicio'],
                                            coordinacion=f.cleaned_data['coordinacion'],
                                            fin=f.cleaned_data['fin'],
                                            objetivo=f.cleaned_data['objetivo'])
                        programa.save(request)
                        log(u'Adiciono programa vinculacion: %s' % programa, request, "add")
                        return JsonResponse({"result": "ok", "id": programa.id})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addprofesor':
                try:
                    f = ProfesorVinculacionForm(request.POST)
                    if f.is_valid():
                        proyecto = ProyectosVinculacion.objects.get(pk=request.POST['id'])
                        profesor = ProfesorProyectoVinculacion(proyecto=proyecto,
                                                               profesor=f.cleaned_data['profesor'],
                                                               responsable=False)
                        profesor.save(request)
                        if not proyecto.profesorproyectovinculacion_set.filter(responsable=True).exists():
                            profesor.responsable = True
                            profesor.save(request)
                        log(u'Adiciono profesor a proyecto de vinculacion: %s' % profesor, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'limites':
                try:
                    limitecarrera = LimiteProyectoVinculacion.objects.get(pk=request.POST['cid'])
                    proyecto = limitecarrera.proyecto
                    valor = int(request.POST['valor'])
                    limiteproyecto = proyecto.limiteparticipantes
                    limitesactuales = null_to_numeric(proyecto.limiteproyectovinculacion_set.exclude(id=limitecarrera.id).aggregate(suma=Sum('limite'))['suma'])
                    if limitesactuales + valor <= limiteproyecto:
                        limitecarrera.limite = valor
                        limitecarrera.save(request)
                        log(u'edito el limite de proyecto de vinculacion: %s' % limitecarrera, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad"})

            elif action == 'addproyecto':
                try:
                    programa = Programa.objects.get(pk=request.POST['id'])
                    f = ProyectoVinculacionForm(request.POST)
                    if f.is_valid():
                        if f.cleaned_data['inicio'] < programa.inicio:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio es menor a la del programa."})
                        if f.cleaned_data['fin'] > programa.fin:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha fin es mayor a la del programa."})
                        proyecto = ProyectosVinculacion(nombre=f.cleaned_data['nombre'],
                                                        inicio=f.cleaned_data['inicio'],
                                                        fin=f.cleaned_data['fin'],
                                                        programa=programa,
                                                        institucion=f.cleaned_data['institucion'],
                                                        reponsableinst=f.cleaned_data['reponsableinst'],
                                                        correoinst=f.cleaned_data['correoinst'],
                                                        direccion=f.cleaned_data['direccion'],
                                                        telefono=f.cleaned_data['telefono'],
                                                        celular=f.cleaned_data['celular'],
                                                        institucionasoc=f.cleaned_data['institucionasoc'],
                                                        reponsableinstasoc=f.cleaned_data['reponsableinstasoc'],
                                                        correoinstasoc=f.cleaned_data['correoinstasoc'],
                                                        telefonoinstasoc=f.cleaned_data['telefonoinstasoc'],
                                                        objetivo=f.cleaned_data['objetivo'],
                                                        condiciones=f.cleaned_data['condiciones'],
                                                        horas=f.cleaned_data['horas'],
                                                        beneficiariosdirectos=f.cleaned_data['beneficiariosdirectos'],
                                                        beneficiariosindirectos=f.cleaned_data['beneficiariosindirectos'],
                                                        limiteparticipantes=f.cleaned_data['limiteparticipantes'],
                                                        lugar=f.cleaned_data['lugar'],
                                                        calfmaxima=f.cleaned_data['califmaxima'] if f.cleaned_data['calificar'] else 0,
                                                        calfminima=f.cleaned_data['califminima'] if f.cleaned_data['calificar'] else 0,
                                                        calificar=f.cleaned_data['calificar'],
                                                        asistminima=f.cleaned_data['asistminima'])
                        proyecto.save(request)
                        proyecto.tipo = f.cleaned_data['tipo']
                        proyecto.carreras = f.cleaned_data['carreras']
                        proyecto.materias.clear()
                        for r in f.cleaned_data['materias']:
                            proyecto.materias.add(r) #= f.cleaned_data['materias']
                        log(u'Adiciono proyecto de vinculacion: %s' % proyecto, request, "add")
                        return JsonResponse({"result": "ok", 'id': proyecto.id})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editproyecto':
                try:
                    proyecto = ProyectosVinculacion.objects.get(pk=request.POST['id'])
                    f = ProyectoVinculacionForm(request.POST)
                    if f.is_valid():
                        if f.cleaned_data['inicio'] < proyecto.programa.inicio:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio es menor a la del programa."})
                        if f.cleaned_data['fin'] > proyecto.programa.fin:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha fin es mayor a la del programa."})
                        proyecto.nombre = f.cleaned_data['nombre']
                        proyecto.inicio = f.cleaned_data['inicio']
                        proyecto.fin = f.cleaned_data['fin']
                        proyecto.materias = f.cleaned_data['materias']
                        proyecto.institucion = f.cleaned_data['institucion']
                        proyecto.reponsableinst = f.cleaned_data['reponsableinst']
                        proyecto.correoinst = f.cleaned_data['correoinst']
                        proyecto.direccion = f.cleaned_data['direccion']
                        proyecto.telefono = f.cleaned_data['telefono']
                        proyecto.celular = f.cleaned_data['celular']
                        proyecto.institucionasoc = f.cleaned_data['institucionasoc']
                        proyecto.reponsableinstasoc = f.cleaned_data['reponsableinstasoc']
                        proyecto.correoinstasoc = f.cleaned_data['correoinstasoc']
                        proyecto.telefonoinstasoc = f.cleaned_data['telefonoinstasoc']
                        proyecto.objetivo = f.cleaned_data['objetivo']
                        proyecto.condiciones = f.cleaned_data['condiciones']
                        proyecto.horas = f.cleaned_data['horas']
                        proyecto.beneficiariosdirectos = f.cleaned_data['beneficiariosdirectos']
                        proyecto.beneficiariosindirectos = f.cleaned_data['beneficiariosindirectos']
                        proyecto.limiteparticipantes = f.cleaned_data['limiteparticipantes']
                        proyecto.lugar = f.cleaned_data['lugar']
                        proyecto.tipo = f.cleaned_data['tipo']
                        proyecto.carreras = f.cleaned_data['carreras']
                        proyecto.calificar = f.cleaned_data['calificar']
                        proyecto.asistminima = f.cleaned_data['asistminima']
                        if f.cleaned_data['calificar']:
                            proyecto.calfmaxima = f.cleaned_data['califmaxima']
                            proyecto.calfminima = f.cleaned_data['califminima']
                        else:
                            proyecto.calfmaxima = 0
                            proyecto.calfminima = 0
                        proyecto.save(request)
                        log(u'Edito proyecto de vinculacion: %s' % proyecto, request, "edit")
                        for participante in proyecto.participanteproyectovinculacion_set.all():
                            participante.actualiza_estado()
                        return JsonResponse({"result": "ok", 'id': proyecto.id})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'registrar':
                try:
                    inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                    proyecto = ProyectosVinculacion.objects.get(pk=request.POST['idp'])
                    if proyecto.tiene_cupo():
                        registro = ParticipanteProyectoVinculacion(proyecto=proyecto,
                                                                   inscripcion=inscripcion,
                                                                   nota=0,
                                                                   asistencia=0,
                                                                   lider_grupo=False)
                        registro.save(request)
                        log(u"Registro alumno a proyecto: %s" % registro, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'cerrarparticipante':
                try:
                    participante = ParticipanteProyectoVinculacion.objects.get(pk=request.POST['id'])
                    participante.cerrado = True
                    participante.save(request)
                    participante.actualiza_estado()
                    return JsonResponse({"result": "ok", "estado": participante.estado})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Programas de vinculación con la comunidad'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_vinculacion')
                    data['title'] = u'Nuevo programa de vinculación'
                    data['form'] = ProgramaVinculacionForm(initial={'inicio': datetime.now().date(),
                                                                    'fin': datetime.now().date()})
                    return render(request, "adm_vinculacion/add.html", data)
                except Exception as ex:
                    pass

            if action == 'addprofesor':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_vinculacion')
                    data['title'] = u'Profesor del proyecto de vinculación'
                    data['proyecto'] = proyecto = ProyectosVinculacion.objects.get(pk=request.GET['id'])
                    data['form'] = ProfesorVinculacionForm()
                    return render(request, "adm_vinculacion/addprofesor.html", data)
                except Exception as ex:
                    pass

            if action == 'responsable':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_vinculacion')
                    profesor = ProfesorProyectoVinculacion.objects.get(pk=request.GET['id'])
                    for profe in profesor.proyecto.profesores():
                        profe.responsable = False
                        profe.save(request)
                    profesor.responsable = True
                    profesor.save(request)
                    log(u'Modifico profesor a proyecto de vinculacion: %s' % profesor, request, "add")
                    return HttpResponseRedirect("/adm_vinculacion?action=proyectos&id=" + str(profesor.proyecto.programa.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'delprofesor':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_vinculacion')
                    data['profesor'] = ProfesorProyectoVinculacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_vinculacion/delprofesor.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_vinculacion')
                    data['title'] = u'Editar programa de vinculación'
                    data['programa'] = programa = Programa.objects.get(pk=request.GET['id'])
                    data['form'] = ProgramaVinculacionForm(initial={'inicio': programa.inicio,
                                                                    'fin': programa.fin,
                                                                    'objetivo': programa.objetivo,
                                                                    'nombre': programa.nombre})
                    return render(request, "adm_vinculacion/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'del':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_vinculacion')
                    data['title'] = u'Eliminar programa de vinculación'
                    data['programa'] = Programa.objects.get(pk=request.GET['id'])
                    return render(request, "adm_vinculacion/del.html", data)
                except Exception as ex:
                    pass

            if action == 'delproyecto':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_vinculacion')
                    data['title'] = u'Eliminar proyecto de vinculación'
                    data['proyecto'] = proyecto = ProyectosVinculacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_vinculacion/delproyecto.html", data)
                except Exception as ex:
                    pass

            if action == 'proyectos':
                try:
                    data['title'] = u'Proyectos del programa de vinculación'
                    programa = Programa.objects.get(pk=request.GET['id'])
                    search = None
                    ids = None
                    if 'ps' in request.GET:
                        search = request.GET['ps']
                        proyectos = programa.proyectosvinculacion_set.filter(nombre__icontains=search).order_by('-inicio')
                    elif 'pid' in request.GET:
                        ids = request.GET['pid']
                        proyectos = programa.proyectosvinculacion_set.filter(id=ids)
                    else:
                        proyectos = programa.proyectosvinculacion_set.all().order_by('-inicio')
                    paging = MiPaginador(proyectos, 25)
                    p = 1
                    try:
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        page = paging.page(p)
                    except Exception as ex:
                        page = paging.page(p)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['proyectos'] = page.object_list
                    data['programa'] = programa
                    data['reporte_0'] = obtener_reporte('acta_calificacion_proyecto')
                    data['reporte_1'] = obtener_reporte('listado_estudiantes_inscritos_vcc')
                    data['reporte_2'] = obtener_reporte('informe_proyecto')
                    data['reporte_3'] = obtener_reporte('impresion_control_vinculacion_general')
                    return render(request, "adm_vinculacion/proyectos.html", data)
                except Exception as ex:
                    pass

            elif action == 'registroproyectos':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_vinculacion')
                    data['title'] = u'Registrar en proyecto de vinculacion'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    data['proyectos'] = ProyectosVinculacion.objects.all().order_by('-fin')
                    return render(request, "adm_vinculacion/registroproyectos.html", data)
                except Exception as ex:
                    pass

            elif action == 'registrar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_vinculacion')
                    data['title'] = u'Registrar en proyecto'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    data['proyecto'] = ProyectosVinculacion.objects.get(pk=request.GET['idp'])
                    return render(request, "adm_vinculacion/registrar.html", data)
                except Exception as ex:
                    pass

            if action == 'registrados':
                try:
                    data['title'] = u'Registrados en el proyecto de vinculación'
                    data['proyecto'] = proyecto = ProyectosVinculacion.objects.get(pk=request.GET['id'])
                    data['registrados'] = proyecto.participanteproyectovinculacion_set.all().order_by('inscripcion__persona')
                    return render(request, "adm_vinculacion/registrados.html", data)
                except Exception as ex:
                    pass

            elif action == 'limites':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_vinculacion')
                    data['title'] = u'Limite de estudiantes por carrera'
                    data['proyecto'] = proyecto = ProyectosVinculacion.objects.get(pk=request.GET['id'])
                    carreraslimite = proyecto.limiteproyectovinculacion_set.all()
                    lista = [x.carrera.id for x in carreraslimite]
                    for carrera in proyecto.carreras.all():
                        if carrera.id not in lista:
                            ncarrera = LimiteProyectoVinculacion(proyecto=proyecto,
                                                                 carrera=carrera,
                                                                 limite=0)
                            ncarrera.save()
                    carreraslimite = proyecto.limiteproyectovinculacion_set.all()
                    lista = [x.id for x in proyecto.carreras.all()]
                    for limite in carreraslimite:
                        if limite.carrera.id not in lista:
                            limite.delete()
                    data['limites'] = proyecto.limiteproyectovinculacion_set.all()
                    lista = [x.id for x in proyecto.carreras.all()]
                    data['registradosotros'] = proyecto.participanteproyectovinculacion_set.count() - proyecto.participanteproyectovinculacion_set.filter(inscripcion__carrera__id__in=lista).count()
                    return render(request, "adm_vinculacion/limites.html", data)
                except Exception as ex:
                    pass

            elif action == 'addproyecto':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_vinculacion')
                    data['title'] = u'Adicionar nuevo proyecto'
                    data['programa'] = programa = Programa.objects.get(pk=request.GET['id'])
                    data['form'] = ProyectoVinculacionForm(initial={'inicio': programa.inicio,
                                                                    'fin': programa.fin,
                                                                    'horas': 0,
                                                                    'beneficiariosdirectos': 0,
                                                                    'beneficiariosindirectos': 0,
                                                                    'limiteparticipantes': 0})
                    return render(request, "adm_vinculacion/addproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'retirar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_vinculacion')
                    data['title'] = u'Retirar estudiante de proyecto'
                    data['participante'] = ParticipanteProyectoVinculacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_vinculacion/retirar.html", data)
                except Exception as ex:
                    pass

            elif action == 'lider':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_vinculacion')
                    participante = ParticipanteProyectoVinculacion.objects.get(pk=request.GET['id'])
                    participante.lider_grupo = request.GET['val'] == 'y'
                    participante.save()
                    return HttpResponseRedirect("/adm_vinculacion?action=registrados&id=" + str(participante.proyecto.id))
                except Exception as ex:
                    pass

            elif action == 'editproyecto':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_vinculacion')
                    data['title'] = u'Editar proyecto'
                    data['proyecto'] = proyecto = ProyectosVinculacion.objects.get(pk=request.GET['id'])
                    data['form'] = ProyectoVinculacionForm(initial={'nombre': proyecto.nombre,
                                                                    'inicio': proyecto.inicio,
                                                                    'fin': proyecto.fin,
                                                                    'materias': proyecto.materias.all(),
                                                                    'institucion': proyecto.institucion,
                                                                    'reponsableinst': proyecto.reponsableinst,
                                                                    'correoinst': proyecto.correoinst,
                                                                    'direccion': proyecto.direccion,
                                                                    'telefono': proyecto.telefono,
                                                                    'celular': proyecto.celular,
                                                                    'institucionasoc': proyecto.institucionasoc,
                                                                    'reponsableinstasoc': proyecto.reponsableinstasoc,
                                                                    'correoinstasoc': proyecto.correoinstasoc,
                                                                    'telefonoinstasoc': proyecto.telefonoinstasoc,
                                                                    'objetivo': proyecto.objetivo,
                                                                    'condiciones': proyecto.condiciones,
                                                                    'horas': proyecto.horas,
                                                                    'beneficiariosdirectos': proyecto.beneficiariosdirectos,
                                                                    'beneficiariosindirectos': proyecto.beneficiariosindirectos,
                                                                    'limiteparticipantes': proyecto.limiteparticipantes,
                                                                    'lugar': proyecto.lugar,
                                                                    'calificar': proyecto.calificar,
                                                                    'califmaxima': proyecto.calfmaxima,
                                                                    'califminima': proyecto.calfminima,
                                                                    'asistminima': proyecto.asistminima,
                                                                    'carreras': proyecto.carreras.all(),
                                                                    'tipo': proyecto.tipo.all()})
                    return render(request, "adm_vinculacion/editproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'abrirproyecto':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_vinculacion')
                    proyecto = ProyectosVinculacion.objects.get(pk=request.GET['id'])
                    proyecto.cerrado = False
                    proyecto.save()
                    for participante in proyecto.participanteproyectovinculacion_set.all():
                        participante.cerrado = False
                        participante.save()
                        participante.actualiza_estado()
                    return HttpResponseRedirect("/adm_vinculacion?action=proyectos&id=" + str(proyecto.programa.id))
                except Exception as ex:
                    pass

            elif action == 'cerrarproyecto':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_vinculacion')
                    proyecto = ProyectosVinculacion.objects.get(pk=request.GET['id'])
                    proyecto.cerrado = True
                    proyecto.save()
                    for participante in proyecto.participanteproyectovinculacion_set.all():
                        participante.cerrado = True
                        participante.save()
                        participante.actualiza_estado()
                    return HttpResponseRedirect("/adm_vinculacion?action=proyectos&id=" + str(proyecto.programa.id))
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                programas = Programa.objects.filter(nombre__icontains=search).order_by('-inicio')
            elif 'id' in request.GET:
                ids = request.GET['id']
                programas = Programa.objects.filter(id=ids).order_by('-inicio')
            else:
                programas = Programa.objects.all().order_by('-inicio')
        paging = MiPaginador(programas, 25)
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
        data['programas'] = page.object_list
        data['reporte_0'] = obtener_reporte('proyectos_de_programa')
        return render(request, "adm_vinculacion/view.html", data)