# -*- coding: latin-1 -*-

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template

from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import ArchivoPdfForm
from sga.funciones import MiPaginador, log, variable_valor, generar_nombre
from sga.models import TemaTitulacionPosgradoMatricula, \
    TemaTitulacionPosgradoMatriculaHistorial


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    # miscarreras = Carrera.objects.filter(coordinadorcarrera__in=persona.gruposcarrera(periodo)).distinct()
    miscoordinaciones = persona.mis_coordinaciones()
    # Carrera.objects.filter(grupocoordinadorcarrera__group__in=persona.grupos()).distinct()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            # if action == ' ':
            #     try:
            #         form = ArchivoForm(request.POST)
            #         if form.is_valid():
            #             materia = Archivo.objects.filter(pk=request.POST['id'])[0].materia
            #             profesor = materia.profesormateria_set.filter(status=True, principal=True)[0].profesor
            #             Archivo.objects.filter(materia=materia).update(aprobado=False)
            #             archivopdf = Archivo.objects.filter(materia=materia, tipo_id=ARCHIVO_TIPO_SYLLABUS, profesor=profesor, archivo__contains='.pdf').order_by('-id')[0]
            #             archivopdf.aprobado = form.cleaned_data['aprobado']
            #             archivopdf.observacion = form.cleaned_data['observacion']
            #             archivopdf.save(request)
            #             archivoword = Archivo.objects.filter(materia=materia, tipo_id=ARCHIVO_TIPO_SYLLABUS, profesor=profesor, archivo__contains='.doc').order_by('-id')[0]
            #             archivoword.aprobado = form.cleaned_data['aprobado']
            #             archivoword.observacion = form.cleaned_data['observacion']
            #             archivoword.save(request)
            #             log(u'Aprobo silabo: %s' % materia, request, "edit")
            #             return JsonResponse({"result": "ok"})
            #         else:
            #              raise NameError('Error')
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            #
            if action == 'aprobar_tema':
                try:
                    form = ArchivoPdfForm(request.POST, request.FILES)
                    if form.is_valid():
                        if 'archivo' in request.FILES:
                            arch = request.FILES['archivo']
                            extension = arch._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if arch.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                            if not exte.lower() == 'pdf':
                                return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})


                        if 'id' in request.POST and 'st' in request.POST and 'obs' in request.POST:
                            tema = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.POST['id']))
                            historial = TemaTitulacionPosgradoMatriculaHistorial(tematitulacionposgradomatricula=tema,
                                                                                 observacion=request.POST['obs'],
                                                                                 estado=request.POST['st'])
                            historial.save(request)
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("archivorevisionsolicitudtemapropuesto_", newfile._name)
                            historial.archivo = newfile
                            historial.save()

                            if variable_valor('APROBAR_SILABO') == int(request.POST['st']):
                                tema.aprobado = True
                                tema.save(request)
                                log(u'Aprobó el tema titulacion %s' % (tema), request, "add")
                                #silabo.materia.crear_actualizar_silabo_curso()
                            else:
                                log(u'Rechazó el tema titulacion %s' % (tema), request, "add")
                            return JsonResponse({"result": "ok","idm":tema.id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'detalleaprobacion':
                try:
                    data['tema'] = tema = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.POST['id']))
                    data['historialaprobacion'] = tema.tematitulacionposgradomatriculahistorial_set.filter(status=True).order_by('-id')
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    template = get_template("adm_aprobartematitulacion/detalleaprobacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            # elif action == 'detallerevicion':
            #     try:
            #         data['title'] = u'Detalle de revisión de guías de práctica'
            #         practica = GPGuiaPracticaSemanal.objects.get(pk=request.POST['id'])
            #         data['revisiones'] = practica.estadoguiapractica_set.filter(status=True).order_by('-fecha')
            #         template = get_template("aprobar_silabo_decano/detallerevision.html")
            #         json_content = template.render(data)
            #         return JsonResponse({"result": "ok", 'data': json_content})
            #     except Exception as ex:
            #         pass
            #
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            # if action == 'aprobarsilabo':
            #     try:
            #         data['title'] = u'Aprobar Silabo'
            #         data['archivo'] = archivo = Archivo.objects.filter(pk=request.GET['id'])[0]
            #         form = ArchivoForm(initial={'observacion': archivo.observacion,
            #                                     'aprobado': archivo.aprobado})
            #         data['form'] = form
            #         return render(request, "aprobar_silabo_decano/aprobarsilabo.html", data)
            #     except Exception as ex:
            #         pass
            #
            if action == 'listar_temas':
                try:
                    # data['materia'] = materia = Materia.objects.get(pk=pm.materia.id)
                    data['temas'] = tema = TemaTitulacionPosgradoMatricula.objects.filter(pk=int(request.GET['id']))
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    form = ArchivoPdfForm()
                    data['form'] = form
                    template = get_template("adm_aprobartematitulacion/listatema.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Aprobar tema titulación'
                if not request.session['periodo'].visible:
                    return HttpResponseRedirect("/?info=Periodo Inactivo.")
                search = None
                mallaid = None
                nivelmallaid = None
                ids = None
                temas = TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula__nivel__periodo=periodo).order_by('-id')
                if 'id' in request.GET:
                    ids = int(request.GET['id'])
                    temas = TemaTitulacionPosgradoMatricula.filter(matricula__nivel__periodo=periodo,status=True, id=int(request.GET['id']))

                if 's' in request.GET:
                    search = request.GET['s']
                    # s = search.split(" ")
                    temas = TemaTitulacionPosgradoMatricula.filter(matricula__nivel__periodo=periodo,status=True, propuestatema__icontains=search)

                paging = MiPaginador(temas, 25)
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
                data['temas'] = page.object_list
                data['search'] = search if search else ""
                data['periodo'] = periodo
                return render(request, "adm_aprobartematitulacion/view.html", data)
            except Exception as ex:
                pass
