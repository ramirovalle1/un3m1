# -*- coding: UTF-8 -*-
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from decorators import last_access, secure_module
from sga.commonviews import adduserdata
from sga.forms import ConfiguracionTitulacionPosgradoForm, NuevaTutoriaForm
from sga.funciones import log, variable_valor, generar_nombre, MiPaginador
from sga.models import TemaTitulacionPosgradoProfesor, TemaTitulacionPosgradoMatricula, \
    TutoriasTemaTitulacionPosgradoProfesor, TemaTitulacionPosgradoMatriculaCabecera


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
# @secure_module
@last_access
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    data['profesor'] = profesor = perfilprincipal.profesor
    if not perfilprincipal.es_profesor():
        #     if not persona.mis_coordinaciones().filter(id=7):
        #         return HttpResponseRedirect("/?info=Solo los perfiles de profesores de posgrado pueden ingresar al modulo.")
        # else:
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores de posgrado pueden ingresar al modulo.")
    hoy = datetime.now().date()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                tema = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'])
                temaprofesor = TemaTitulacionPosgradoProfesor(tematitulacionposgradomatricula=tema,
                                                              profesor=profesor,
                                                              fecharegistro=hoy)
                temaprofesor.save(request)
                # # Guaddar Historial
                # tematitulacionposgradomatriculahistorial = TemaTitulacionPosgradoProfesorHistorial(tematitulacionposgradoprofesor=temaprofesor,
                #                                                                                    observacion='NINGUNA',
                #                                                                                    estado=1)
                # tematitulacionposgradomatriculahistorial.save(request)
                log(u'Ingreso solicitud tema posgrado: %s' % temaprofesor, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass
                return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar los datos."})

        if action == 'addpareja':
            try:
                tema = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.POST['id'])
                temaprofesor = TemaTitulacionPosgradoProfesor(tematitulacionposgradomatriculacabecera=tema,
                                                              tematitulacionposgradomatricula=None,
                                                              profesor=profesor,
                                                              fecharegistro=hoy)
                temaprofesor.save(request)
                # # Guaddar Historial
                # tematitulacionposgradomatriculahistorial = TemaTitulacionPosgradoProfesorHistorial(tematitulacionposgradoprofesor=temaprofesor,
                #                                                                                    observacion='NINGUNA',
                #                                                                                    estado=1)
                # tematitulacionposgradomatriculahistorial.save(request)
                log(u'Ingreso solicitud tema posgrado: %s' % temaprofesor, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass
                return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar los datos."})

        if action == 'addtutoria':
            try:
                tema = TemaTitulacionPosgradoProfesor.objects.get(pk=request.POST['idtema'])
                form = NuevaTutoriaForm(request.POST, request.FILES)
                if form.is_valid():
                    if 'archivo' in request.FILES:
                        arch = request.FILES['archivo']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 10485760:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                    tutoria = TutoriasTemaTitulacionPosgradoProfesor(tematitulacionposgradoprofesor=tema,
                                                                     tutor=profesor,
                                                                     fecharegistro=form.cleaned_data['fecharegistro'],
                                                                     observacion=form.cleaned_data['observacion'])
                    tutoria.save(request)
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("tutoria_", newfile._name)
                    tutoria.archivo = newfile
                    tutoria.save()

                    log(u'Ingreso tutoria tema posgrado: %s' % tutoria, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass
                return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar los datos."})

        if action == 'delete':
            try:
                solicitud = TemaTitulacionPosgradoProfesor.objects.get(pk=request.POST['id'])
                log(u'Eliminó solicitud tema titulacion posgrado: %s' % solicitud, request, "del")
                solicitud.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'edittutoria':
            try:
                tutoria = TutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=request.POST['id'])
                f = NuevaTutoriaForm(request.POST)
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 10485760:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                if f.is_valid():
                    tutoria.observacion = f.cleaned_data['observacion']
                    tutoria.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("tutoria_", newfile._name)
                        tutoria.archivo = newfile
                        tutoria.save()

                    log(u'Modifico tutoria Titulacion posgrado: %s' % tutoria, request, "edit")
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

            if action == 'add':
                try:
                    data['title'] = u'Solicitar tema titulación'
                    data['tema'] = TemaTitulacionPosgradoMatricula.objects.get(pk=request.GET['id'])
                    return render(request, "pro_titulacionposgrado/add.html", data)
                except Exception as ex:
                    pass

            if action == 'addpareja':
                try:
                    data['title'] = u'Solicitar tema titulación'
                    data['tema'] = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.GET['id'])
                    return render(request, "pro_titulacionposgrado/addpareja.html", data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar solicitud de tema titulación'
                    data['solicitud'] = TemaTitulacionPosgradoProfesor.objects.get(pk=request.GET['id'])
                    return render(request, 'pro_titulacionposgrado/delete.html', data)
                except Exception as ex:
                    pass

            elif action == 'registrartutorias':
                try:
                    data['title'] = u'Registrar tutorias'
                    data['temaprofesor'] = temaprofesor = TemaTitulacionPosgradoProfesor.objects.get(pk=int(request.GET['id']))
                    data['tutorias'] = tutorias = temaprofesor.tutoriastematitulacionposgradoprofesor_set.filter(status=True).order_by('fecharegistro')
                    return render(request, "pro_titulacionposgrado/registrartutorias.html", data)
                except Exception as ex:
                    pass

            elif action == 'edittutoria':
                try:
                    data['title'] = u'Editar tutoria'
                    tutoria = TutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=int(request.GET['id']))
                    form = NuevaTutoriaForm(initial={'fecharegistro': tutoria.fecharegistro,
                                                     'observacion': tutoria.observacion})
                    data['tutoria'] = tutoria
                    form.editar()
                    data['form'] = form
                    data['idtema'] = request.GET['idtema']
                    return render(request, "pro_titulacionposgrado/edittutoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'addtutoria':
                try:
                    data['title'] = u'Registrar nueva Tutoria'
                    form = NuevaTutoriaForm(initial={'fecharegistro': datetime.now().date()} )
                    data['form'] = form
                    data['persona'] = persona
                    data['idtema'] = request.GET['idtema']
                    return render(request, "pro_titulacionposgrado/addtutoria.html", data)
                except Exception as ex:
                    pass
            elif action == 'masinformacion':
                try:
                    if 'id' in request.GET:
                        data['solicitud'] = solicitures = TemaTitulacionPosgradoProfesor.objects.get(pk=request.GET['id'])
                        template = get_template("pro_titulacionposgrado/masinformacion.html")
                        return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'masinformacionpareja':
                try:
                    if 'id' in request.GET:
                        data['solicitud'] = solicitures = TemaTitulacionPosgradoProfesor.objects.get(pk=request.GET['id'])
                        template = get_template("pro_titulacionposgrado/masinformacionpareja.html")
                        return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            elif action == 'masinformacionaperturado':
                try:
                    if 'id' in request.GET:
                        data['temaindividualapertura'] = temas = TemaTitulacionPosgradoMatricula.objects.get(pk=request.GET['id'])
                        template = get_template("pro_titulacionposgrado/masinformacionaperturado.html")
                        return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'masinformacionaperturadopareja':
                try:
                    if 'id' in request.GET:
                        data['pareja'] = parejaaperturado = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.GET['id'])
                        template = get_template("pro_titulacionposgrado/masinformacionaperturadopareja.html")
                        return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'postulatedocente':
                try:
                    data['title'] = u'Postúlate'

                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    temasperiodo=None
                    idexcluir = TemaTitulacionPosgradoProfesor.objects.values_list( 'tematitulacionposgradomatricula__id', flat=True).filter(status=True,  profesor=profesor).exclude(
                        tematitulacionposgradomatricula__isnull=True)
                    idexcluir_pareja = TemaTitulacionPosgradoProfesor.objects.values_list('tematitulacionposgradomatriculacabecera__id', flat=True).filter(status=True, profesor=profesor).exclude(
                        tematitulacionposgradomatriculacabecera__isnull=True)
                    temas = TemaTitulacionPosgradoMatricula.objects.filter(tutor__isnull=True, aprobado=True,
                                                                           matricula__nivel__periodo__configuraciontitulacionposgrado__fechainiciopostulacion__lte=hoy,
                                                                           matricula__nivel__periodo__configuraciontitulacionposgrado__fechafinpostulacion__gte=hoy,
                                                                           status=True).exclude(mecanismotitulacionposgrado__nombre__icontains='COMPLEXIVO').distinct().order_by('-id')
                    temasperiodo = temas.filter(cabeceratitulacionposgrado__isnull=True).exclude( id__in=idexcluir)
                    temas_pareja_id = temas.filter(cabeceratitulacionposgrado__isnull=False).values_list('cabeceratitulacionposgrado', flat=True).order_by('cabeceratitulacionposgrado').distinct().exclude(cabeceratitulacionposgrado_id__in=idexcluir_pareja)
                    temasperiodogrupo = TemaTitulacionPosgradoMatriculaCabecera.objects.filter(pk__in=temas_pareja_id)

                    paging = MiPaginador(temasperiodo, 25)
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
                    data['temasperiodo'] = page.object_list

                    paging2 = MiPaginador(temasperiodogrupo, 25)

                    p2 = 1
                    try:
                        paginasesion2 = 1
                        if 'paginador2' in request.session:
                            paginasesion2 = int(request.session['paginador2'])
                        if 'page2' in request.GET:
                            p2 = int(request.GET['page2'])
                        else:
                            p2 = paginasesion2
                        try:
                            page2 = paging2.page(p2)
                        except:
                            p2 = 1
                        page2 = paging2.page(p2)
                    except:
                        page2 = paging2.page(p2)
                    request.session['paginador2'] = p2
                    data['paging2'] = paging2
                    data['rangospaging2'] = paging2.rangos_paginado(p2)
                    data['page2'] = page2
                    data['temasperiodogrupo'] = page2.object_list



                    return render(request, "pro_titulacionposgrado/postulardocente.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Solicitud de temas titulación'
            data['aprobar'] = variable_valor('APROBAR_SILABO')
            data['rechazar'] = variable_valor('RECHAZAR_SILABO')
            data['pendiente'] = variable_valor('PENDIENTE_SILABO')
            idexcluir = TemaTitulacionPosgradoProfesor.objects.values_list('tematitulacionposgradomatricula__id', flat=True).filter(status=True,profesor=profesor).exclude(tematitulacionposgradomatricula__isnull=True)
            idexcluir_pareja = TemaTitulacionPosgradoProfesor.objects.values_list('tematitulacionposgradomatriculacabecera__id', flat=True).filter(status=True, profesor=profesor).exclude(tematitulacionposgradomatriculacabecera__isnull=True)
            solicitures = TemaTitulacionPosgradoProfesor.objects.filter(profesor=profesor,status=True)
            solicitudindividual = solicitures.filter(tematitulacionposgradomatriculacabecera__isnull=True)
            solicitudpareja = solicitures.filter(tematitulacionposgradomatricula__isnull=True)

            paging = MiPaginador(solicitudindividual, 25)
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
            data['solicitudes'] = page.object_list

            paging2 = MiPaginador(solicitudpareja, 25)

            p2 = 1
            try:
                paginasesion2 = 1
                if 'paginador2' in request.session:
                    paginasesion2 = int(request.session['paginador2'])
                if 'page2' in request.GET:
                    p2 = int(request.GET['page2'])
                else:
                    p2 = paginasesion2
                try:
                    page2 = paging2.page(p2)
                except:
                    p2 = 1
                page2 = paging2.page(p2)
            except:
                page2 = paging2.page(p2)
            request.session['paginador2'] = p2
            data['paging2'] = paging2
            data['rangospaging2'] = paging2.rangos_paginado(p2)
            data['page2'] = page2
            data['solicitudespareja'] = page2.object_list


            return render(request, "pro_titulacionposgrado/view.html", data)