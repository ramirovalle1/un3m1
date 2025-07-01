# -*- coding: latin-1 -*-
from datetime import datetime
from django.db import transaction
from django.db.models import Q
from decorators import secure_module, last_access
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from settings import PREPROYECTO_ESTADO_PENDIENTE_ID, MIN_PROMEDIO_APROBACION
from sga.commonviews import adduserdata
from sga.forms import AnteproyectoForm
from sga.funciones import variable_valor
from sga.models import Anteproyecto, Inscripcion, miinstitucion, \
    CalificacionProyecto, Profesor, CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    lista=""
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'add':
            try:
                form = AnteproyectoForm(request.POST)
                if form.is_valid():
                    if Anteproyecto.objects.filter(Q(titulo=form.cleaned_data['titulo']) & Q(estado=1)| Q( estado=2)).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un proyecto con este titulo registrado."})
                    listado = request.POST['otrosintegrantes']
                    integrantes = Inscripcion.objects.filter(id__in=[int(x) for x in listado.split(',')]) if listado else []
                    # if integrantes.count()<3:
                    #     if integrantes.count() == 2:
                    #         for inte in integrantes:
                    #             for integ in integrantes:
                    #                 if not integ.id == inte.id:
                    #                   if not integ.carrera_id==inte.carrera_id:
                    #                       return JsonResponse({"result": "bad","mensaje": u" El Estudiante integrante debe ser de la misma carrera."})
                    #     elif integrantes.count() == 3:
                    #         ban=0
                    #         for inte in integrantes:
                    #             for integ in integrantes:
                    #                 if not integ.id == inte.id:
                    #                     if integ.carrera_id == inte.carrera_id:
                    #                         ban=inte.carrera_id
                    #         if ban ==0 :
                    #             return JsonResponse({"result": "bad","mensaje": u" No puede ver estudiante de varias carreras."})

                    # else:
                    #     return JsonResponse({"result": "bad","mensaje": u"La cantidad de estudiante sobrepasa lo permitido."})
                    for integrante in integrantes:
                        if integrante.tiene_proyecto_pendiente_activo():
                            return JsonResponse({"result": "bad", "mensaje": u"El estudiante " + integrante.persona.nombre_completo() + " ya se encuentra registrado en un proyecto."})
                        if not integrante.tiene_porciento_cumplimiento_malla():
                            return JsonResponse({"result": "bad", "mensaje": u"Debe de cumplir con el 80% el "+integrante.persona.nombre_completo()+" requerido de su malla para presentar un anteproyecto."})

                    antepro = Anteproyecto(titulo=form.cleaned_data['titulo'],
                                           tipotrabajotitulacion=form.cleaned_data['tipotrabajotitulacion'],
                                           tutorsugerido=form.cleaned_data['tutorsugerido'],
                                           fecha=datetime.now().date(),
                                           estado=PREPROYECTO_ESTADO_PENDIENTE_ID,
                                           referencias=form.cleaned_data['referencias'],
                                           resultadoesperado=form.cleaned_data['resultadoesperado'],
                                           descripcionpropuesta=form.cleaned_data['descripcionpropuesta'],
                                           objetivogeneral=form.cleaned_data['objetivogeneral'],
                                           objetivoespecifico=form.cleaned_data['objetivoespecifico'],
                                           problema=form.cleaned_data['problema'],
                                           metodo=form.cleaned_data['metodo'],
                                           palabrasclaves=form.cleaned_data['palabrasclaves'],
                                           sublineainvestigacion=form.cleaned_data['sublineainvestigacion'])
                    antepro.save()
                    for integrante in integrantes:
                        antepro.inscripciones.add(integrante)
                    send_html_mail("Registro anteproyecto", "emails/nuevoanteproyecto.html", {'sistema': request.session['nombresistema'], 'anteproyecto': antepro, 't': miinstitucion()}, inscripcion.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[4][1])
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            list={}
            if action == 'busqueda':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 2:
                        inscripcionl = Inscripcion.objects.filter(persona__apellido1__icontains=s[0],persona__apellido2__icontains=s[1],carrera=inscripcion.carrera).exclude(pk__in=lista).distinct()[:20]
                    else:
                        inscripcionl =Inscripcion.objects.filter(Q(persona__nombres__contains=s[0]) | Q(persona__apellido1__contains=s[0]) | Q(persona__apellido2__contains=s[0]) | Q(persona__cedula__contains=s[0])).filter(carrera=inscripcion.carrera).exclude(pk__in=lista).distinct()[:20]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr()}for x in inscripcionl]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'verificarcumplimiento':
                try:
                    q = request.GET['fila'].upper().strip()
                    s = q.split("-")
                    cedula=s[0].strip()
                    estudiante=Inscripcion.objects.get(persona__cedula=cedula)
                    if estudiante.tiene_porciento_cumplimiento_malla1():
                        if estudiante.tiene_proyecto_pendiente_activo():
                            data = {"mensaje": "Tiene Proyecto Activo"}
                        else:
                            data = {"results": "ok"}
                    else:
                        data = {"mensaje": "No cumple con los requisitos"}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    data['title'] = u'Adicionar AnteProyecto'
                    data['inscripcion'] = inscripcion
                    forapro = AnteproyectoForm()
                    forapro.fields['tutorsugerido'].queryset = Profesor.objects.filter(coordinacion=inscripcion.coordinacion_id, activo=True)
                    data['form'] = forapro
                    return render(request, "alu_anteproyecto/alu_addanteproyecto.html", data)
                except Exception as ex:
                    pass

            if action == 'informacion':
                try:
                    data['title'] = u'Información del proyecto'
                    data['permite_modificar'] = False
                    proyecto = Anteproyecto.objects.get(pk=request.GET['id'])
                    form= AnteproyectoForm(initial={'titulo': proyecto.titulo,
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
                    form.editar()
                    data['form'] = form
                    return render(request, "alu_anteproyecto/informacion.html", data)
                except Exception as ex:
                    pass

            if action == 'observacion':
                try:
                    data['title'] = u'Observacion del Anteproyecto'
                    data['permite_modificar'] = False
                    data['calificadores'] = CalificacionProyecto.objects.filter(anteproyecto=request.GET['id'])
                    return render(request, "alu_anteproyecto/observacion.html", data)
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Gestion de Anteproyectos y Proyectos de Grado'
            if not inscripcion.tiene_porciento_cumplimiento_malla():
                return HttpResponseRedirect("/?info=Debe de cumplir con el % requerido de su malla para presentar un anteproyecto.")
            anteproyect=Anteproyecto.objects.filter(inscripciones=inscripcion)
            data['misproyectos'] = anteproyect
            ban=True
            if anteproyect:
                for ante in anteproyect:
                    if ante.esta_aprobado() or ante.esta_pendiente():
                        ban=False
            data['adicionar']=ban
            data['MIN_PROMEDIO_APROBACION'] = MIN_PROMEDIO_APROBACION
            return render(request, "alu_anteproyecto/view.html", data)
