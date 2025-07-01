# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import PreProyectoGradoForm, SubirAvanceProyectoForm, AvanceTutoriaForm, \
    SubirProyectoCompletoForm
from sga.funciones import generar_nombre, log
from sga.models import PreProyectoGrado, Tutoria, ProyectosGrado, TutoriaProyecto, TutoriaArchivo


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addavance':
            try:
                form = SubirAvanceProyectoForm(request.FILES)
                if form.is_valid():
                    vali=TutoriaProyecto.objects.get(pk=int(request.POST['id']))
                    if vali.puede_registrar():
                        newfile = None
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("avance_", newfile._name)
                            if not vali.tiene_archivo():
                                tutoriaarchivo = TutoriaArchivo(tutoria=vali,archivo=newfile)
                                tutoriaarchivo.save(request)

                            else:
                                tutoriaarchivo=TutoriaArchivo.objects.get(tutoria=vali)
                                tutoriaarchivo.archivo=newfile
                                tutoriaarchivo.save(request)
                            return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"N."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addproyectocompleto':
            try:
                form = SubirProyectoCompletoForm(request.FILES)
                if form.is_valid():

                    if 'archivo' in request.FILES:
                        proyecto = ProyectosGrado.objects.get(pk=int(request.POST['id']))
                        proyecto.fechaentregaprocompleto=datetime.now().date()
                        newfile = None
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("proyectocompleto_", newfile._name)
                        if not proyecto.tiene_archivo():
                            proyecto.proyectocompleto=newfile
                            proyecto.save(request)
                        log(u'subir proyecto Completo: %s' % proyecto, request, "add")
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

            if action == 'subiravance':
                try:
                    data['title'] = u'Subir Avance de Proyecto'
                    data['form'] = SubirAvanceProyectoForm()
                    data['proyecto']= request.GET['id']
                    return render(request, "alu_tutoriasproyecto/subiravance.html", data)
                except Exception as ex:
                    pass
            if action == 'subirproyectocompleto':
                try:
                    data['title'] = u'Subir Proyecto Completo'
                    data['form'] = SubirProyectoCompletoForm()
                    data['proyecto']= ProyectosGrado.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_tutoriasproyecto/subirproyectocompleto.html", data)
                except Exception as ex:
                    pass


            if action == 'informacion':
                try:
                    data['title'] = u'Información del proyecto'
                    data['permite_modificar'] = False
                    proyecto = PreProyectoGrado.objects.get(pk=request.GET['id'])
                    data['form'] = PreProyectoGradoForm(initial={'titulo': proyecto.titulo,
                                                                 'fecha': proyecto.fecha,
                                                                 'tipogrado': proyecto.tipogrado,
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
                    return render(request, "alu_tutorias/informacion.html", data)
                except Exception as ex:
                    pass

            if action=='verobservacion':
                try:
                    data['title'] = u'Observacion de Proyecto'
                    data['permite_modificar'] = False
                    tutoria = TutoriaProyecto.objects.get(pk=request.GET['id'])
                    archivo = TutoriaArchivo.objects.get(tutoria=request.GET['id'])
                    form= AvanceTutoriaForm(initial={'proyecto': tutoria.proyectogrado,
                                                     'fechaentrega': archivo.fecha_creacion.strftime("%d/%m/%Y %H:%M:%S "),
                                                     'fecharevision': tutoria.fecha_modificacion.strftime("%d/%m/%Y %H:%M:%S "),
                                                     'observacion': tutoria.observacion
                                                     })
                    form.editar()
                    data['form'] = form
                    return render(request, "alu_tutoriasproyecto/observacion.html", data)
                except Exception as ex:
                    pass

            if action == 'tutorias':
                try:
                    data['title'] = u'Seguimiento a tutorias'
                    preproyecto = PreProyectoGrado.objects.get(pk=request.GET['id'])
                    data['proyecto'] = proyecto = preproyecto.proyecto_grado()
                    data['tutorias'] = proyecto.tutoria_set.all()
                    data['inscripcion'] = inscripcion
                    return render(request, "alu_tutorias/tutorias.html", data)
                except Exception as ex:
                    pass

            if action == 'confirmar':
                try:
                    data['title'] = u'Confirmar tutorias'
                    data['tutoria'] = Tutoria.objects.get(pk=request.GET['id'])
                    return render(request, "alu_tutorias/confirmar.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Gestion de Tutorias de Proyectos'
            data['misproyectos'] =ProyectosGrado.objects.get(proyecto__inscripciones=inscripcion)

            return render(request, "alu_tutoriasproyecto/view1.html", data)