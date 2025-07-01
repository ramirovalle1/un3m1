# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import AulaMantForm, TipoUbicacionAulaForm
from sga.funciones import MiPaginador, log, convertir_fecha, convertir_hora
from sga.models import AulaCoordinacion, Aula, Coordinacion, TipoUbicacionAula, Turno, Sesion
from datetime import datetime, timedelta, date


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
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'desaprobar':
            try:
                aulacoordinacion = AulaCoordinacion.objects.filter(coordinacion_id = int(request.POST['coordinacion']), aula_id = int(request.POST['aula']))[0]
                log(u'Quito Aula Coordinacion: %s' % aulacoordinacion, request, "del")
                aulacoordinacion.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'aprobar':
            try:
                aulacoordinacion = AulaCoordinacion(coordinacion_id = int(request.POST['coordinacion']),
                                                    aula_id = int(request.POST['aula']))
                aulacoordinacion.save(request)
                log(u'Inserto Aula Coordinacion: %s' % aulacoordinacion, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addaula':
            try:
                form = AulaMantForm(request.POST)
                if form.is_valid():
                        if Aula.objects.filter(nombre=form.cleaned_data['nombre'], status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                        aula=Aula(sede=form.cleaned_data['sede'],
                                  nombre=form.cleaned_data['nombre'],
                                  tipo=form.cleaned_data['tipo'],
                                  tipoubicacion=form.cleaned_data['tipoubicacion'],
                                  capacidad=form.cleaned_data['capacidad'],
                                  bloque=form.cleaned_data['bloque'])
                        aula.save(request)
                        log(u'Adiciono aula desde aula coordinacion : %s - [%s]' % (aula,aula.id), request, "add")
                        return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editaula':
            try:
                form = AulaMantForm(request.POST)
                if form.is_valid():
                    aula = Aula.objects.get(pk=int(request.POST['id']))
                    if not aula.claseaula():
                        aula.sede = form.cleaned_data['sede']
                        aula.tipo = form.cleaned_data['tipo']
                    aula.capacidad = form.cleaned_data['capacidad']
                    aula.nombre = form.cleaned_data['nombre']
                    aula.tipoubicacion = form.cleaned_data['tipoubicacion']
                    aula.bloque = form.cleaned_data['bloque']
                    aula.save(request)
                    log(u'Edito aula desde aula coordinacion: %s - [%s]' % (aula,aula.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delaula':
            try:
                aula = Aula.objects.get(pk=int(request.POST['id']))
                if aula.claseaula():
                    return JsonResponse({"result": "bad","mensaje": u"No puede Eliminar, tiene horario de clase.."})
                log(u'Elimino aula desde aula coodinacion: %s - [%s]' % (aula,aula.id), request, "del")
                aula.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addtipoubicacion':
            try:
                form = TipoUbicacionAulaForm(request.POST)
                if form.is_valid():
                        if TipoUbicacionAula.objects.filter(nombre=form.cleaned_data['nombre'], status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                        tipo=TipoUbicacionAula(nombre=form.cleaned_data['nombre'])
                        tipo.save(request)
                        log(u'Adiciono tipo de ubicacion de aula desde aula coordinacion : %s - [%s]' % (tipo,tipo.id), request, "add")
                        return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edittipoubicacion':
            try:
                form = TipoUbicacionAulaForm(request.POST)
                if form.is_valid():
                    tipo = TipoUbicacionAula.objects.get(pk=int(request.POST['id']))
                    tipo.nombre = form.cleaned_data['nombre']
                    tipo.save(request)
                    log(u'Edito tipo de ubicacion de aula desde aula coordinacion: %s - [%s]' % (tipo,tipo.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deltipoubicacion':
            try:
                tipo = TipoUbicacionAula.objects.get(pk=int(request.POST['id']))
                if tipo.aula_set.all().exists():
                    return JsonResponse({"result": "bad","mensaje": u"No puede Eliminar, esta utilizado en aula.."})
                log(u'Elimino tipo de ubicacion de aula desde aula coordinacion: %s - [%s]' % (tipo,tipo.id), request, "del")
                tipo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Error Aula Coordinacion."})
    else:
        data['title'] = u'Coordinación Aulas'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'desaprobar':
                try:
                    data['title'] = u'Quitar Coordinación Aulas'
                    aulaid = request.GET['idaula']
                    data['coordinacion'] = request.GET['idcoordinacion']
                    data['aula'] = request.GET['idaula']
                    return render(request, "adm_aulas/desaprobar.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobar':
                try:
                    data['title'] = u'Insertar Coordinación Aulas'
                    aulaid = request.GET['idaula']
                    data['coordinacion'] = request.GET['idcoordinacion']
                    data['aula'] = request.GET['idaula']
                    return render(request, "adm_aulas/aprobar.html", data)
                except Exception as ex:
                    pass

            if action == 'addaula':
                try:
                    data['title'] = u'Adicionar aula'
                    data['form'] = AulaMantForm()
                    return render(request, "adm_aulas/addaula.html", data)
                except Exception as ex:
                    pass

            elif action == 'editaula':
                try:
                    data['title'] = u'Editar aula'
                    data['aula'] = aula = Aula.objects.get(pk=int(request.GET['id']))
                    form = AulaMantForm(initial={'sede':aula.sede,
                                                 'nombre':aula.nombre,
                                                 'tipo':aula.tipo,
                                                 'tipoubicacion': aula.tipoubicacion,
                                                 'capacidad':aula.capacidad,
                                                 'bloque':aula.bloque})

                    if aula.claseaula():
                        form.editar()
                    data['form'] = form
                    if 's' in request.GET:
                        data['search'] = request.GET['s']
                    else:
                        data['search'] = None
                    return render(request, "adm_aulas/editaula.html", data)
                except Exception as ex:
                    pass

            elif action == 'delaula':
                try:
                    data['title'] = u'Eliminar aula'
                    data['aula'] = Aula.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_aulas/delaula.html", data)
                except Exception as ex:
                    pass

            # elif action == 'aulas':
            #     try:
            #         data['title'] = u'Aulas'
            #         search = None
            #         ids = None
            #         if 's' in request.GET:
            #             search = request.GET['s'].strip()
            #             ss = search.split(' ')
            #             if len(ss) == 1:
            #                 aula = Aula.objects.filter(Q(nombre__icontains=search)|Q(tipo__nombre__icontains=search)|Q(capacidad__icontains=search)|Q(tipoubicacion__nombre__icontains=search)).distinct().order_by('nombre')
            #             elif len(ss) == 2:
            #                 aula = Aula.objects.filter(Q(nombre__icontains=ss[0]) & Q(nombre__icontains=ss[1])).distinct().order_by('nombre')
            #             else:
            #                 aula = Aula.objects.filter(Q(nombre__icontains=ss[0]) & Q(nombre__icontains=ss[1]) & Q(nombre__icontains=ss[2])).distinct().order_by('nombre')
            #         else:
            #             aula = Aula.objects.all().order_by('nombre')
            #         paging = MiPaginador(aula, 30)
            #         p = 1
            #         try:
            #             paginasesion = 1
            #             if 'paginador' in request.session:
            #                 paginasesion = int(request.session['paginador'])
            #             if 'page' in request.GET:
            #                 p = int(request.GET['page'])
            #             else:
            #                 p = paginasesion
            #             try:
            #                 page = paging.page(p)
            #             except:
            #                 p = 1
            #             page = paging.page(p)
            #         except:
            #             page = paging.page(p)
            #         request.session['paginador'] = p
            #         data['paging'] = paging
            #         data['rangospaging'] = paging.rangos_paginado(p)
            #         data['page'] = page
            #         data['search'] = search if search else ""
            #         data['ids'] = ids if ids else ""
            #         data['aulas'] = page.object_list
            #         return render(request, "adm_aulas/viewaula.html", data)
            #     except Exception as ex:
            #         pass

            if action == 'addtipoubicacion':
                try:
                    data['title'] = u'Adicionar tipo de ubicación'
                    data['form'] = TipoUbicacionAulaForm()
                    return render(request, "adm_aulas/addtipoubicacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'edittipoubicacion':
                try:
                    data['title'] = u'Editar tipo de ubicación'
                    data['tipoubicacion'] = tipo = TipoUbicacionAula.objects.get(pk=int(request.GET['id']))
                    form = TipoUbicacionAulaForm(initial={'nombre':tipo.nombre})
                    data['form'] = form
                    if 's' in request.GET:
                        data['search'] = request.GET['s']
                    else:
                        data['search'] = None
                    return render(request, "adm_aulas/edittipoubicacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'deltipoubicacion':
                try:
                    data['title'] = u'Eliminar tipo de ubicación'
                    data['tipoubicacion'] = TipoUbicacionAula.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_aulas/deltipoubicacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'tipoubicacion':
                try:
                    data['title'] = u'Tipos de ubicación'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            tipo = TipoUbicacionAula.objects.filter(Q(nombre__icontains=search)).distinct().order_by('nombre')
                        else:
                            tipo = TipoUbicacionAula.objects.filter(Q(nombre__icontains=ss[0]) & Q(nombre__icontains=ss[1])).distinct().order_by('nombre')
                    else:
                        tipo = TipoUbicacionAula.objects.all().order_by('nombre')
                    paging = MiPaginador(tipo, 30)
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
                    data['tipoubicacion'] = page.object_list
                    return render(request, "adm_aulas/viewtipoubicacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'disponibilidadaula':
                try:
                    data['title'] = u'Disponibilidad de aula'
                    inicio = None
                    fin = None
                    horainicio = None
                    horafin = None
                    aulaselect = None
                    seccionselect = None
                    lista_fechas = []
                    aulas = Aula.objects.filter(status=True).order_by('nombre')
                    if 'ida' in request.GET:
                        aulaselect = int(request.GET['ida'])
                        if aulaselect>0:
                            aulas = aulas.filter(pk=aulaselect)
                    turnos = Turno.objects.filter(status=True, mostrar=True).order_by('comienza')
                    if 'fi' and 'ff' in request.GET:
                        inicio = convertir_fecha(request.GET['fi'])
                        fin = convertir_fecha(request.GET['ff'])
                        if inicio > fin:
                            return HttpResponseRedirect("/adm_aulas?action=disponibilidadaula&info=No puede ser mayor la fecha de inicio que la fecha fin.")
                        for dia in daterange(inicio, (fin + timedelta(days=1))):
                            lista_fechas.append(dia)
                    if 'ids' in request.GET:
                        seccionselect = int(request.GET['ids'])
                        if seccionselect > 0:
                            turnos = turnos.filter(sesion_id=seccionselect).order_by('comienza')
                    if 'hi' in request.GET and 'hf' in request.GET:
                        horainicio = convertir_hora(request.GET['hi'])
                        horafin = convertir_hora(request.GET['hf'])
                        if horainicio > horafin:
                            return HttpResponseRedirect("/dm_aulas?action=disponibilidadaula&info=No puede ser mayor la hora de inicio que la hora fin.")
                        turnos = turnos.filter(comienza__gte=horainicio, termina__lte=horafin).order_by('comienza')
                    data['turnos'] = turnos
                    data['lista_fechas'] = lista_fechas
                    data['aulas'] = aulas
                    data['listaaulas'] = Aula.objects.filter(status=True).order_by('nombre')
                    data['listasesion'] = Sesion.objects.filter(status=True).order_by('nombre')
                    data['horasinicio'] = Turno.objects.values_list('comienza', flat=True).filter(status=True).distinct('comienza').order_by('comienza')
                    data['horasfin'] = Turno.objects.values_list('termina', flat=True).filter(status=True).distinct('termina').order_by('termina')
                    data['inicio'] = inicio
                    data['fin'] = fin
                    data['horainicioselect'] = horainicio
                    data['horafinselect'] = horafin
                    data['aulaselect'] = aulaselect
                    data['seccionselect'] = seccionselect
                    return render(request, "adm_aulas/viewdisponibilidad.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Aulas'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    aula = Aula.objects.filter(Q(nombre__icontains=search) | Q(tipo__nombre__icontains=search) | Q(capacidad__icontains=search) | Q(tipoubicacion__nombre__icontains=search)).distinct().order_by('nombre')
                elif len(ss) == 2:
                    aula = Aula.objects.filter(Q(nombre__icontains=ss[0]) & Q(nombre__icontains=ss[1])).distinct().order_by('nombre')
                else:
                    aula = Aula.objects.filter(Q(nombre__icontains=ss[0]) & Q(nombre__icontains=ss[1]) & Q(nombre__icontains=ss[2])).distinct().order_by('nombre')
            else:
                aula = Aula.objects.all().order_by('nombre')
            paging = MiPaginador(aula, 30)
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
            data['aulas'] = page.object_list
            return render(request, "adm_aulas/viewaula.html", data)
            # search = None
            # ids = None
            # if 'id' in request.GET:
            #     ids = request.GET['id']
            #     aulas = Aula.objects.filter(id=ids).order_by('nombre').distinct()
            # elif 's' in request.GET:
            #     search = request.GET['s']
            #     aulas = Aula.objects.filter(nombre__icontains=search).order_by('nombre').distinct()
            # else:
            #     aulas = Aula.objects.all().order_by('nombre').distinct()
            # paging = MiPaginador(aulas, 25)
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
            # data['coordinaciones'] = coordinacion = Coordinacion.objects.all().order_by('nombre').distinct()
            # if 'coordinacion' in request.GET:
            #     request.session['coordinacionselect'] = Coordinacion.objects.filter(pk=int(request.GET['coordinacion']))[0]
            # else:
            #     request.session['coordinacionselect'] = coordinacion[0]
            #
            # data['paging'] = paging
            # data['rangospaging'] = paging.rangos_paginado(p)
            # data['page'] = page
            # data['search'] = search if search else ""
            # data['ids'] = ids if ids else ""
            # data['aulas'] = page.object_list
            # data['coordinacionselect'] = request.session['coordinacionselect']
            #
            # return render(request, "aulacoordinacion/view.html", data)


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)