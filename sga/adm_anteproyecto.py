# -*- coding: latin-1 -*-
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import PREPROYECTO_ESTADO_APROBADO_ID, MAX_CALIFICADORES, \
    TITULAR_ID, PROYECTO_EN_TUTORIA, DIAS_LIMITES_PROYECTO_GRADO
from sga.commonviews import adduserdata
from sga.forms import AnteproyectoForm, AsignarCalificadorProyectoForm, AprobarAnteproyectoForm
from sga.funciones import MiPaginador, log
from sga.models import Anteproyecto, CalificacionProyecto,Coordinacion, Profesor, AprobacionAnteproyecto, ProyectosGrado


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'aprobacion':
            try:
                form = AprobarAnteproyectoForm(request.POST)
                anteproyecto = Anteproyecto.objects.get(pk=request.POST['id'])
                if form.is_valid():
                        proyecto = AprobacionAnteproyecto(anteproyecto=anteproyecto,
                                                 fechaaprobacion=datetime.now(),
                                                 aprobacionpersona=persona,
                                                 observacion=form.cleaned_data['observacion'])
                        proyecto.save(request)
                        anteproyecto.estado= form.cleaned_data['estado']
                        anteproyecto.save(request)
                        id_profesor=int(form.cleaned_data['tutor'].id)
                        if int(form.cleaned_data['estado']) == PREPROYECTO_ESTADO_APROBADO_ID:
                            fecha =datetime.now()
                            proyectogrado = ProyectosGrado(proyecto=anteproyecto,
                                                     fechaaprobacion=datetime.now(),
                                                     tutor=form.cleaned_data['tutor'],
                                                     estado=PROYECTO_EN_TUTORIA,
                                                     fechalimite=(datetime(fecha.year, fecha.month, fecha.day, 0, 0,0) + timedelta(days=DIAS_LIMITES_PROYECTO_GRADO)).date())
                            proyectogrado.save(request)
                        #log(u'Aprobacion proyecto: %s' % anteproyecto, request, "edit")
                        return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'asignarcalificador':
            try:
                form = AsignarCalificadorProyectoForm(request.POST)
                antepro = Anteproyecto.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    if form.cleaned_data['fecha'] >datetime.now().date():
                        if antepro.calificacionproyecto_set.filter(profesor=form.cleaned_data['calificador']).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya esta asignado el docente."})
                        calificador = CalificacionProyecto(anteproyecto=antepro,
                                                            profesor=form.cleaned_data['calificador'],
                                                            fechaasignacion=form.cleaned_data['fecha'])
                        calificador.save(request)
                    else:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u" La fecha de asignacion debe ser mayor a la actual."})
                    log(u'Asigno calificador de anteproyecto: %s' % calificador, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'eliminarcalificador':
            try:
                calificador = CalificacionProyecto.objects.get(pk=request.POST['id'])
                log(u'Elimino calificador de anteproyecto: %s' % calificador, request, "del")
                calificador.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})


    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'aprobacion':
                try:
                    data['title'] = u'Aprobar Anteproyecto'
                    proyecto = Anteproyecto.objects.get(pk=request.GET['id'])
                    ins = proyecto.inscripciones.all()
                    ban = 0
                    for inte in ins:
                        for integ in ins:
                            if not integ.id == inte.id:
                                if integ.carrera_id == inte.carrera_id:
                                    ban = inte.carrera_id
                    var = Coordinacion.objects.get(carrera=ban)
                    forapro=AprobarAnteproyectoForm()
                    forapro.fields['tutor'].queryset=Profesor.objects.filter(coordinacion=var, activo=True,  nivelcategoria=TITULAR_ID)
                    forapro.fields['tutor'].initial=proyecto.tutorsugerido.id

                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['distributivo'] = profesor.distributivohoraseval(periodo)

                    data['form'] =  forapro
                    data['proyecto']=proyecto
                    return render(request, "adm_anteproyecto/aprobacion.html", data)
                except Exception as ex:
                    pass

            if action == 'eliminarcalificador':
                try:
                    data['title'] = u'Eliminar calificador'
                    data['calificador'] = CalificacionProyecto.objects.get(pk=request.GET['id'])
                    return render(request, "adm_anteproyecto/eliminarcalificador.html", data)
                except Exception as ex:
                    pass

            if action == 'informacion':
                try:
                    data['title'] = u'Información del proyecto'
                    data['permite_modificar'] = False
                    proyecto = Anteproyecto.objects.get(pk=request.GET['id'])
                    data['form'] = AnteproyectoForm(initial={'titulo': proyecto.titulo,
                                                                 'tipotrabajotitulacion': proyecto.tipotrabajotitulacion,
                                                                 'tutorsugerido': proyecto.tutor_principal(),
                                                                 'referencias': proyecto.referencias,
                                                                 'resultadoesperado': proyecto.resultadoesperado,
                                                                 'descripcionpropuesta': proyecto.descripcionpropuesta,
                                                                 'objetivogeneral': proyecto.objetivogeneral,
                                                                 'objetivoespecifico': proyecto.objetivoespecifico,
                                                                 'problema': proyecto.problema,
                                                                 'metodo': proyecto.metodo,
                                                                 'palabrasclaves': proyecto.palabrasclaves,
                                                                 'sublineainvestigacion': proyecto.sublineainvestigacion})
                    return render(request, "adm_anteproyecto/informacion.html", data)
                except Exception as ex:
                    pass

            if action == 'asignarcalificador':
                try:
                    data['title'] = u'Asignar Docente para Calificación'
                    antepro=Anteproyecto.objects.get(pk=request.GET['id'])
                    ins=antepro.inscripciones.all()
                    ban=0
                    for inte in ins:
                        for integ in ins:
                            if not integ.id == inte.id:
                                if integ.carrera_id == inte.carrera_id:
                                    ban = inte.carrera_id
                    var=Coordinacion.objects.get(carrera=ban)
                    data['preproyecto'] = antepro
                    form = AsignarCalificadorProyectoForm(initial={'fecha': datetime.now().date()})
                    profesor= Profesor.objects.filter(coordinacion=var, activo=True, nivelcategoria=TITULAR_ID)
                    form.fields['calificador'].queryset = Profesor.objects.filter(coordinacion=var, activo=True,  nivelcategoria=TITULAR_ID, )
                    data['form'] = form
                    return render(request, "adm_anteproyecto/asignarcalificador.html", data)
                except Exception as ex:
                    pass

            if action == 'calificadores':

                try:
                    data['title'] = u'Docentes Asignados a Calificar el Anteproyecto'
                    ante =Anteproyecto.objects.get(pk=request.GET['id'])
                    data['preproyecto'] =ante
                    valor = True
                    if CalificacionProyecto.objects.filter(anteproyecto=ante).count()>=MAX_CALIFICADORES or ante.esta_rechazado() or ante.esta_aprobado() :
                        valor=False
                    data['adicionar']= valor
                    return render(request, "adm_anteproyecto/calificadores.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Gestion de Anteproyectos de Grado'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                proyectos = Anteproyecto.objects.filter(Q(titulo__icontains=search) |
                                                            Q(tutortitular__nombres__icontains=search) |
                                                            Q(tutortitular__apellido1__icontains=search) |
                                                            Q(tutortitular__apellido2__icontains=search) |
                                                            Q(referencias__icontains=search) |
                                                            Q(resultadoesperado__icontains=search) |
                                                            Q(descripcionpropuesta__icontains=search) |
                                                            Q(objetivogeneral__icontains=search) |
                                                            Q(objetivoespecifico__icontains=search) |
                                                            Q(problema__icontains=search) |
                                                            Q(palabrasclaves__icontains=search)).order_by('estado', 'titulo').distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                proyectos = Anteproyecto.objects.filter(id=ids)
            else:
                proyectos = Anteproyecto.objects.all().order_by('estado', 'titulo').distinct()
            paging = MiPaginador(proyectos, 25)
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
            data['proyectos'] = page.object_list
            return render(request, "adm_anteproyecto/view.html", data)