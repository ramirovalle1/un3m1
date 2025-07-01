# -*- coding: UTF-8 -*-
from datetime import datetime
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata, nivel_matriculacion
from sga.forms import ExamenComplexivoForm, ExamenComplexivoAyudantiaForm
from sga.funciones import log, generar_nombre, variable_valor
from sga.models import ExamenComplexivo, ComplexivoPeriodo, Inscripcion, AsignaturaAyudantiaComplexivo, \
    CUENTAS_CORREOS, AsignaturaMalla, Graduado
from sga.tasks import conectar_cuenta, send_html_mail


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
@last_access
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    data['inscripcion'] = inscripcion = perfilprincipal.inscripcion
    hoy = datetime.now().date()
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = ExamenComplexivoForm(request.POST, request.FILES)
                if f.is_valid():
                    periodocomplexivo = ComplexivoPeriodo.objects.get(pk=request.POST['id'])
                    if (periodocomplexivo.cupo - periodocomplexivo.inscritos()) <= 0:
                        return JsonResponse({"result": "bad", "mensaje": u"No hay cupo disponible."})
                    if ExamenComplexivo.objects.values('id').filter(inscripcion__persona=persona, inscripcion__carrera_id=f.cleaned_data['carrera'].id, complexivoperiodo=periodocomplexivo).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El registro ya existe."})
                    inscripcion = Inscripcion.objects.get(carrera=f.cleaned_data['carrera'], persona=persona)
                    #nivel = inscripcion.mi_nivel().nivel
                    if periodocomplexivo.nivel:
                        if not periodocomplexivo.nivel.id <= inscripcion.mi_nivel().nivel.id:
                            return JsonResponse({"result": "bad", "mensaje": u"Solo pueden inscribirse desde "+ periodocomplexivo.nivel})
                    # if periodocomplexivo.tipocomplexivo:
                    #     if periodocomplexivo.modulo != 0:
                    #         if ExamenComplexivo.objects.filter(inscripcion=inscripcion, complexivoperiodo__tipocomplexivo=periodocomplexivo.tipocomplexivo, complexivoperiodo__modulo=periodocomplexivo.modulo, status=True).exists():
                    #             return JsonResponse({"result": "bad", "mensaje": u"Ya tiene una Solicitud del mismo tipo y modulo."})
                    # newfile = None
                    # if 'solicituddecano' in request.FILES:
                    #     newfile = request.FILES['solicituddecano']
                    #     newfile._name = generar_nombre("solicitud_decano_", newfile._name)
                    id_asignaturas = AsignaturaMalla.objects.values_list('asignatura_id').filter(status=True, malla_id=22).exclude(asignatura_id=782)
                    #totalingles = inscripcion.recordacademico_set.filter(status=True, noaplica=False, asignatura_id__in=id_asignaturas, aprobada=True).count()
                    totalingles = inscripcion.recordacademico_set.filter(status=True, noaplica=False,
                                                                         asignatura_id__in=id_asignaturas,
                                                                         aprobada=True).exclude(inscripcion_id__in=Graduado.objects.values_list('inscripcion_id').filter(status=True, estadograduado=True)).count()

                    if periodocomplexivo.id == 233 or periodocomplexivo.id == 234 or periodocomplexivo.id == 235 or periodocomplexivo.id == 236 or periodocomplexivo.id == 237:
                        if totalingles > 0:
                            examencomplexivo = ExamenComplexivo(inscripcion=inscripcion,
                                                                complexivoperiodo=periodocomplexivo,
                                                                nivel=inscripcion.mi_nivel().nivel
                                                                # ultimosemestre=f.cleaned_data['ultimosemestre'],
                                                                # egresado=f.cleaned_data['egresado'],
                                                                # solicituddecano=newfile
                                                                )
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Registra un total de (%s) módulos de ingles" % totalingles})
                    else:
                        examencomplexivo = ExamenComplexivo(inscripcion=inscripcion,
                                                            complexivoperiodo=periodocomplexivo,
                                                            # ultimosemestre=f.cleaned_data['ultimosemestre'],
                                                            # egresado=f.cleaned_data['egresado'],
                                                            # solicituddecano=newfile
                                                            )
                    examencomplexivo.save(request)
                    # persona.telefono = f.cleaned_data['telefono']
                    # persona.telefono_conv = f.cleaned_data['telefono_conv']
                    # persona.email = f.cleaned_data['email']
                    persona.save(request)
                    # send_html_mail("PreInscripción", "emails/prematricula.html", {'sistema': request.session['nombresistema'], 'examencomplexivo': examencomplexivo}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[4][1])

                    log(u'Adiciono una PreInscripción: %s' % examencomplexivo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.(%s)" % ex})

        if action == 'addcomasignatura':
            try:
                f = ExamenComplexivoAyudantiaForm(request.POST, request.FILES)
                if f.is_valid():
                    periodocomplexivo = ComplexivoPeriodo.objects.get(pk=request.POST['id'])
                    if ExamenComplexivo.objects.values('id').filter(inscripcion__persona=persona, inscripcion__carrera_id=f.cleaned_data['carrera'].id, complexivoperiodo=periodocomplexivo).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El registro ya existe."})
                    inscripcion = Inscripcion.objects.get(carrera=f.cleaned_data['carrera'], persona=persona)
                    newfile = None
                    if 'solicituddecano' in request.FILES:
                        newfile = request.FILES['solicituddecano']
                        newfile._name = generar_nombre("solicitud_decano_", newfile._name)
                    examencomplexivo = ExamenComplexivo(inscripcion=inscripcion,
                                                        complexivoperiodo=periodocomplexivo,
                                                        ultimosemestre=f.cleaned_data['ultimosemestre'],
                                                        egresado=f.cleaned_data['egresado'],
                                                        solicituddecano=newfile)
                    examencomplexivo.save(request)
                    examencomplexivoasignatura = AsignaturaAyudantiaComplexivo(examencomplexivo=examencomplexivo,
                                                                               asignatura=f.cleaned_data['asignatura'])
                    examencomplexivoasignatura.save(request)
                    persona.telefono = f.cleaned_data['telefono']
                    persona.telefono_conv = f.cleaned_data['telefono_conv']
                    persona.email = f.cleaned_data['email']
                    persona.save(request)
                    log(u'Adicionó una PreInscripción: %s' % examencomplexivo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.(%s)" % ex})

        if action == 'edit':
            try:
                f = ExamenComplexivoForm(request.POST, request.FILES)
                if f.is_valid():
                    examencomplexivo = ExamenComplexivo.objects.get(pk=request.POST['id'])
                    if examencomplexivo.estadosolicitud != 1:
                        return JsonResponse({"result": "bad", "mensaje": u"El registro esta en uso."})
                    # examencomplexivo.egresado = f.cleaned_data['egresado']
                    # examencomplexivo.ultimosemestre = f.cleaned_data['ultimosemestre']
                    newfile = None
                    # if 'solicituddecano' in request.FILES:
                    #     newfile = request.FILES['solicituddecano']
                    #     newfile._name = generar_nombre("solicitud_decano_", newfile._name)
                    #     examencomplexivo.solicituddecano = newfile
                    examencomplexivo.save(request)
                    # persona.telefono = f.cleaned_data['telefono']
                    # persona.telefono_conv = f.cleaned_data['telefono_conv']
                    # persona.email = f.cleaned_data['email']
                    persona.save(request)
                    log(u'Modificó una PreInscripción: %s' % examencomplexivo, request, "edit")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editcomasignatura':
            try:
                f = ExamenComplexivoAyudantiaForm(request.POST, request.FILES)
                if f.is_valid():
                    examencomplexivo = ExamenComplexivo.objects.get(pk=request.POST['id'])
                    if examencomplexivo.estadosolicitud != 1:
                        return JsonResponse({"result": "bad", "mensaje": u"El registro esta en uso."})
                    examencomplexivo.egresado = f.cleaned_data['egresado']
                    examencomplexivo.ultimosemestre = f.cleaned_data['ultimosemestre']
                    newfile = None
                    if 'solicituddecano' in request.FILES:
                        newfile = request.FILES['solicituddecano']
                        newfile._name = generar_nombre("solicitud_decano_", newfile._name)
                        examencomplexivo.solicituddecano = newfile
                    examencomplexivo.save(request)
                    persona.telefono = f.cleaned_data['telefono']
                    persona.telefono_conv = f.cleaned_data['telefono_conv']
                    persona.email = f.cleaned_data['email']
                    persona.save(request)
                    if AsignaturaAyudantiaComplexivo.objects.values('id').filter(examencomplexivo=examencomplexivo).exists():
                        complexivoasignatura = AsignaturaAyudantiaComplexivo.objects.get(examencomplexivo=examencomplexivo)
                        complexivoasignatura.asignatura=f.cleaned_data['asignatura']
                        complexivoasignatura.save(request)
                    else:
                        examencom = AsignaturaAyudantiaComplexivo(examencomplexivo=examencomplexivo,
                                                                  asignatura=f.cleaned_data['asignatura'])
                        examencom.save(request)
                    log(u'Modifico PreInscripción: %s' % examencomplexivo, request, "edit")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                examencomplexivo = ExamenComplexivo.objects.get(pk=request.POST['id'])
                if examencomplexivo.estadosolicitud != 1:
                    return JsonResponse({"result": "bad", "mensaje": u"El registro esta en uso."})
                log(u'Eliminó PreInscripción: %s' % examencomplexivo, request, "del")
                examencomplexivo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'deletecomasignatura':
            try:
                examencomplexivo = ExamenComplexivo.objects.get(pk=request.POST['id'])
                if examencomplexivo.estadosolicitud != 1:
                    return JsonResponse({"result": "bad", "mensaje": u"El registro esta en uso."})
                log(u'Elimino PreInscripción: %s' % examencomplexivo, request, "del")
                complexivoasignatura = AsignaturaAyudantiaComplexivo.objects.get(examencomplexivo=examencomplexivo)
                complexivoasignatura.delete()
                examencomplexivo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    complexivoperiodo = ComplexivoPeriodo.objects.filter(pk=request.GET['id'])[0]
                    if complexivoperiodo.ayudantia: #codigos para que muestren solo los de ayudantias
                        data['complexivoperiodo'] = complexivoperiodo
                        data['title'] = complexivoperiodo.nombre
                        # data['observacion'] = complexivoperiodo.observacion
                        form = ExamenComplexivoAyudantiaForm(
                                                                # initial={'telefono': persona.telefono,
                                                                #       'telefono_conv': persona.telefono_conv,
                                                                #       'email': persona.email}
                                                            )
                        form.mis_carrera(persona=persona)
                        form.mis_asignaturasaprobadas(inscripcion=inscripcion)
                        data['form'] = form
                        return render(request, 'alu_complexivo/addcomasignatura.html', data)
                    else:
                        data['complexivoperiodo'] = complexivoperiodo
                        data['title'] = complexivoperiodo.nombre
                        # data['observacion'] = complexivoperiodo.observacion
                        form = ExamenComplexivoForm(
                            # initial={'telefono': persona.telefono,
                            #                                  'telefono_conv': persona.telefono_conv,
                            #                                  'email': persona.email}
                        )
                        form.mis_carrera(persona=persona)
                        form.adicionar(perfilprincipal.inscripcion)
                        data['form'] = form
                        return render(request, 'alu_complexivo/add.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar solicitud'
                    data['solicitud'] = solicitud = ExamenComplexivo.objects.get(pk=request.GET['id'])
                    if solicitud.complexivoperiodo.id in [49, 50]:  # codigos para que muestren solo los de ayudantias
                        if AsignaturaAyudantiaComplexivo.objects.values('id').filter(examencomplexivo=solicitud.id).exists():
                            nomasignatura = AsignaturaAyudantiaComplexivo.objects.get(examencomplexivo=solicitud.id)
                            nombremateria = nomasignatura.asignatura
                        else:
                            nombremateria = None
                        form = ExamenComplexivoAyudantiaForm(initial={'carrera': solicitud.inscripcion.carrera,
                                                                      # 'egresado': solicitud.egresado,
                                                                      'asignatura': nombremateria
                                                                      # 'ultimosemestre': solicitud.ultimosemestre,
                                                                      # 'telefono': persona.telefono,
                                                                      # 'telefono_conv': persona.telefono_conv,
                                                                      # 'email': persona.email
                                                                      })
                        form.mis_carrera(persona=persona)
                        form.mis_asignaturasaprobadas(inscripcion=inscripcion)
                        form.editar()
                        data['form'] = form
                        return render(request, 'alu_complexivo/editcomasignatura.html', data)
                    else:
                        form = ExamenComplexivoForm(initial={'carrera': solicitud.inscripcion.carrera,
                                                             # 'egresado': solicitud.egresado,
                                                             # 'ultimosemestre': solicitud.ultimosemestre,
                                                             # 'telefono': persona.telefono,
                                                             # 'telefono_conv': persona.telefono_conv,
                                                             # 'email': persona.email
                                                             })
                        form.mis_carrera(persona=persona)
                        form.editar()
                        data['form'] = form
                        return render(request, 'alu_complexivo/edit.html', data)
                except Exception as ex:
                    pass

            if action == 'resultado':
                try:
                    data['title'] = u'Resultado de la solicitud'
                    data['solicitud'] = ExamenComplexivo.objects.get(pk=request.GET['id'])
                    return render(request, 'alu_complexivo/mostrar_resultado.html', data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar solicitud de examen complexivo'
                    data['solicitud'] = excomplexivo = ExamenComplexivo.objects.get(pk=request.GET['id'])
                    if excomplexivo.complexivoperiodo.id in [49, 50]:  # codigos para que muestren solo los de ayudantias
                        return render(request, 'alu_complexivo/deletecomasignatura.html', data)
                    else:
                        return render(request, 'alu_complexivo/delete.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Solicitud de Inscripción'
            search = None
            tipo = None
            complexivos=None
            if inscripcion.coordinacion.id == 9:
                return HttpResponseRedirect("/?info=Estimado aspirante su coordinación de Admisión, no permite acceder a este módulo de PRE-INSCRIPCIONES.")


            if 's' in request.GET:
                search = request.GET['s']
            if search:
                solicitudes = ExamenComplexivo.objects.filter(inscripcion__persona=persona).filter(Q(inscripcion__carrera__nombre__icontains=search) |
                                                                                                   Q(inscripcion__persona__nombres__icontains=search) |
                                                                                                   Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                                   Q(inscripcion__persona__apellido2__icontains=search))
            else:
                solicitudes = ExamenComplexivo.objects.filter(inscripcion__persona=persona)
            # paging = MiPaginador(solicitudes, 25)
            # p = 1
            # try:
            #     paginasesion = 1
            #     if 'paginador' in request.session:
            #         paginasesion = int(request.session['paginador'])
            #     if 'page' in request.GET:
            #         p = int(request.GET['page'])
            #     else:
            #         p = paginasesion
            #     try:
            #         page = paging.page(p)
            #     except:
            #         p = 1
            #     page = paging.page(p)
            # except:
            #     page = paging.page(p)
            # request.session['paginador'] = p
            # data['paging'] = paging
            # data['rangospaging'] = paging.rangos_paginado(p)
            # data['page'] = page
            data['solicitudes'] = solicitudes
            data['search'] = search if search else ""
            # data['solicitudes'] = page.object_list
            # data['habilitado'] = ComplexivoPeriodo.objects.filter(fecha_inicio__lte=hoy, fecha_fin__gte=hoy).exists()
            # data['periodocomple'] = ComplexivoPeriodo.objects.get(fecha_inicio__lte=hoy, fecha_fin__gte=hoy) if data['habilitado'] else None
            # complexivos = ComplexivoPeriodo.objects.filter(Q(fecha_inicio__lte=hoy),
            #                                                Q(fecha_fin__gte=hoy),
            #                                                (Q(coordinacion__isnull=True) |
            #                                                 Q(coordinacion=inscripcion.coordinacion)),
            #                                                nivel__id__lte=inscripcion.mi_nivel().nivel.id,
            #                                                nivel__isnull=False).order_by('-id')

            complexivos = ComplexivoPeriodo.objects.filter(Q(fecha_inicio__lte=hoy),
                                                           Q(fecha_fin__gte=hoy),
                                                           (Q(coordinacion__isnull=True) |
                                                            Q(coordinacion=inscripcion.coordinacion)),
                                                            (Q(carreras__isnull=True) |
                                                             Q(carreras=inscripcion.carrera)),
                                                           (Q(nivel__isnull=True) |
                                                            Q(nivel__id__lte=inscripcion.mi_nivel().nivel.id)),
                                                           complexivoperiodo_modalidades__modalidad=inscripcion.modalidad,
                                                            status=True
                                                           ).order_by('-id')
            # complexivos2=ComplexivoPeriodo.objects.filter(Q(fecha_inicio__lte=hoy),
            #                                                Q(fecha_fin__gte=hoy),
            #                                               (Q(coordinacion__isnull=True) |
            #                                                Q(coordinacion=inscripcion.coordinacion)),
            #
            #                                               status=True
            #                                                ).order_by('-id')
            # if complexivos1 and complexivos2:
            #     complexivos=complexivos1|complexivos2
            # elif complexivos1:
            #     complexivos = complexivos1
            # elif complexivos2:
            #     complexivos = complexivos2
            data['complexivoperiodo'] = complexivos
            id_asignaturas = AsignaturaMalla.objects.values_list('asignatura_id').filter(status=True, malla_id=22).exclude(asignatura_id=782)
            data['totalingles'] = inscripcion.recordacademico_set.filter(status=True, noaplica=False,
                                                                         asignatura_id__in=id_asignaturas,
                                                                         aprobada=True).exclude(inscripcion_id__in=Graduado.objects.values_list('inscripcion_id').filter(status=True, estadograduado=True)).count()

            iscurso = False
            examenes = ExamenComplexivo.objects.filter(inscripcion=inscripcion, status=True).exclude(estadosolicitud=3)
            listcursoingles = [242,243,245,246,247,248,249,250,251,252,253,254,255,256,257,258,259,260,261,262,263,264,265]


            if examenes.filter(complexivoperiodo_id__in=listcursoingles).exists():
                iscurso = True

            data['iscurso'] = iscurso
            return render(request, "alu_complexivo/view.html", data)