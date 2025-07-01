# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import TribunalProyectoGradoForm, \
    CalificarProyectoGradoForm, InformacionProyectoGradoForm, CambiarTutoresProyectoGradoForm, \
    CambiarEstadoProyectoGradoForm
from sga.funciones import MiPaginador, log
from sga.models import ProyectoGrado, ProyectosGrado


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'tribunal':
            try:
                form = TribunalProyectoGradoForm(request.POST)
                proyecto = ProyectoGrado.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    proyecto.presidentepredefensa = form.cleaned_data['presidente']
                    proyecto.secretariopredefensa = form.cleaned_data['secretario']
                    proyecto.delegadopredefensa = form.cleaned_data['delegado']
                    proyecto.fechapredefensa = form.cleaned_data['fechasustentacion']
                    proyecto.horapredefensa = form.cleaned_data['horasustentacion']
                    proyecto.lugarpredefensa = form.cleaned_data['lugar']
                    proyecto.save(request)
                    log(u'Asignacion tribunal predefensa: %s' % proyecto, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'tribunaldefensa':
            try:
                form = TribunalProyectoGradoForm(request.POST)
                proyecto = ProyectoGrado.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    proyecto.presidentedefensa = form.cleaned_data['presidente']
                    proyecto.secretariodefensa = form.cleaned_data['secretario']
                    proyecto.delegadodefensa = form.cleaned_data['delegado']
                    proyecto.fechadefensa = form.cleaned_data['fechasustentacion']
                    proyecto.horadefensa = form.cleaned_data['horasustentacion']
                    proyecto.lugardefensa = form.cleaned_data['lugar']
                    proyecto.save(request)
                    log(u'Asignacion tribunal defensa: %s' % proyecto, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'prorrogar':
            try:
                form = TribunalProyectoGradoForm(request.POST)
                proyecto = ProyectoGrado.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    proyecto.presidenteprorroga = form.cleaned_data['presidente']
                    proyecto.secretarioprorroga = form.cleaned_data['secretario']
                    proyecto.delegadoprorroga = form.cleaned_data['delegado']
                    proyecto.fechanuevasustentacion = form.cleaned_data['fechasustentacion']
                    proyecto.horanuevasustentacion = form.cleaned_data['horasustentacion']
                    proyecto.motivo = form.cleaned_data['motivo']
                    proyecto.fechapostergacion = datetime.now().date()
                    proyecto.prorrogado = True
                    proyecto.estado = 4
                    proyecto.save(request)
                    log(u'Prorroga proyecto: %s' % proyecto, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'calificar':
            try:
                form = CalificarProyectoGradoForm(request.POST)
                proyecto = ProyectoGrado.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    proyecto.calificacion = form.cleaned_data['calificacion']
                    proyecto.estadosustentacion = form.cleaned_data['estadosustentacion']
                    proyecto.estado = 3
                    proyecto.save(request)
                    log(u'Calificacion proyecto: %s' % proyecto, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cambioestado':
            try:
                form = CambiarEstadoProyectoGradoForm(request.POST)
                proyecto = ProyectoGrado.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    proyecto.estado = form.cleaned_data['estado']
                    proyecto.save(request)
                    log(u'Cambio estado de proyecto: %s' % proyecto, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cambiartutores':
            try:
                form = CambiarTutoresProyectoGradoForm(request.POST)
                proyecto = ProyectoGrado.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    proyecto.preproyecto.tutortitular = form.cleaned_data['tutortitular']
                    proyecto.preproyecto.tutorsecundario = form.cleaned_data['tutorsecundario']
                    proyecto.save(request)
                    log(u'Cambio tutores proyecto: %s' % proyecto, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'tribunal':
                try:
                    data['title'] = u'Establecer tribunal predefensa'
                    data['proyecto'] = proyecto = ProyectoGrado.objects.get(pk=request.GET['id'])
                    form = TribunalProyectoGradoForm(initial={'presidente': proyecto.presidentepredefensa,
                                                              'secretario': proyecto.secretariopredefensa,
                                                              'delegado': proyecto.delegadopredefensa,
                                                              'lugar': proyecto.lugarpredefensa,
                                                              'fechasustentacion': proyecto.fechapredefensa if proyecto.fechapredefensa else proyecto.fechalimite,
                                                              'horasustentacion': str(proyecto.horapredefensa) if proyecto.horapredefensa else '13:00'})
                    data['form'] = form
                    return render(request, "adm_proyectosgrado/tribunal.html", data)
                except Exception as ex:
                    pass

            if action == 'tribunaldefensa':
                try:
                    data['title'] = u'Establecer tribunal defensa'
                    data['proyecto'] = proyecto = ProyectoGrado.objects.get(pk=request.GET['id'])
                    form = TribunalProyectoGradoForm(initial={'presidente': proyecto.presidentedefensa,
                                                              'secretario': proyecto.secretariodefensa,
                                                              'delegado': proyecto.delegadodefensa,
                                                              'lugar': proyecto.lugardefensa,
                                                              'fechasustentacion': proyecto.fechadefensa if proyecto.fechadefensa else proyecto.fechalimite,
                                                              'horasustentacion': str(proyecto.horadefensa) if proyecto.horadefensa else '13:00'})
                    data['form'] = form
                    return render(request, "adm_proyectosgrado/tribunaldefensa.html", data)
                except Exception as ex:
                    pass

            if action == 'vertutorias':
                try:
                    data['title'] = u'Seguimiento a tutorias'
                    data['proyecto'] = proyecto = ProyectoGrado.objects.get(pk=request.GET['id'])
                    data['tutorias'] = proyecto.tutoria_set.all()
                    return render(request, "adm_proyectosgrado/tutorias.html", data)
                except Exception as ex:
                    pass

            if action == 'calificar':
                try:
                    data['title'] = u'Calificacion del proyecto grado'
                    data['proyecto'] = ProyectoGrado.objects.get(pk=request.GET['id'])
                    data['form'] = CalificarProyectoGradoForm()
                    return render(request, "adm_proyectosgrado/calificar.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiartutores':
                try:
                    data['title'] = u'Cambiar tutores del proyecto grado'
                    data['proyecto'] = proyecto = ProyectoGrado.objects.get(pk=request.GET['id'])
                    data['form'] = CambiarTutoresProyectoGradoForm(initial={'tutortitular': proyecto.preproyecto.tutortitular,
                                                                            'tutorsecundario': proyecto.preproyecto.tutorsecundario})
                    return render(request, "adm_proyectosgrado/cambiartutores.html", data)
                except Exception as ex:
                    pass

            if action == 'cambioestado':
                try:
                    data['title'] = u'Cambiar estado del proyecto grado'
                    data['proyecto'] = proyecto = ProyectoGrado.objects.get(pk=request.GET['id'])
                    data['form'] = CambiarEstadoProyectoGradoForm(initial={'estado': proyecto.estado})
                    return render(request, "adm_proyectosgrado/cambioestado.html", data)
                except Exception as ex:
                    pass

            if action == 'informacion':
                try:
                    data['title'] = u'Información del proyecto grado'
                    data['permite_modificar'] = False
                    data['proyecto'] = proyecto = ProyectoGrado.objects.get(pk=request.GET['id'])
                    form = InformacionProyectoGradoForm(initial={'estado': proyecto.estado,
                                                                 'fechaaprobacion': proyecto.fechaaprobacion,
                                                                 'fechaconsejo': proyecto.fechaconsejo,
                                                                 'fechalimite': proyecto.fechalimite,
                                                                 'porcientoavance': proyecto.porcientoavance,
                                                                 'presidentepredefensa': proyecto.presidentepredefensa,
                                                                 'secretariopredefensa': proyecto.secretariopredefensa,
                                                                 'delegadopredefensa': proyecto.delegadopredefensa,
                                                                 'fechapredefensa': proyecto.fechapredefensa,
                                                                 'horapredefensa': str(proyecto.horapredefensa),
                                                                 'lugarpredefensa': proyecto.lugarpredefensa,
                                                                 'presidentedefensa': proyecto.presidentedefensa,
                                                                 'secretariodefensa': proyecto.secretariodefensa,
                                                                 'delegadodefensa': proyecto.delegadodefensa,
                                                                 'fechadefensa': proyecto.fechadefensa,
                                                                 'horadefensa': str(proyecto.horadefensa),
                                                                 'lugardefensa': proyecto.lugardefensa,
                                                                 'estadosustentacion': proyecto.estadosustentacion})
                    data['form'] = form
                    return render(request, "adm_proyectosgrado/informacion.html", data)
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Gestion de Proyectos de Grado'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                proyectos = ProyectoGrado.objects.filter(Q(preproyecto__titulo__icontains=search) |
                                                         Q(preproyecto__tutortitular__nombres__icontains=search) |
                                                         Q(preproyecto__tutortitular__apellido1__icontains=search) |
                                                         Q(preproyecto__tutortitular__apellido2__icontains=search) |
                                                         Q(preproyecto__referencias__icontains=search) |
                                                         Q(preproyecto__resultadoesperado__icontains=search) |
                                                         Q(preproyecto__descripcionpropuesta__icontains=search) |
                                                         Q(preproyecto__objetivogeneral__icontains=search) |
                                                         Q(preproyecto__objetivoespecifico__icontains=search) |
                                                         Q(preproyecto__problema__icontains=search) |
                                                         Q(preproyecto__palabrasclaves__icontains=search)).order_by(
                    '-fechaaprobacion', 'preproyecto__titulo').distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                proyectos = ProyectosGrado.objects.filter(id=ids)
            else:
                proyectos = ProyectosGrado.objects.all().order_by('-fechaaprobacion', 'proyecto__titulo').distinct()
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
            return render(request, "adm_proyectosgrados/view.html", data)
