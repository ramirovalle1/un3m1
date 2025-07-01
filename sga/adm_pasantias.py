# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import PasantiaForm, PasantiaAprobarForm
from sga.funciones import MiPaginador, log, formato24h, formato12h
from sga.models import Inscripcion, Pasantia


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                f = PasantiaForm(request.POST)
                if f.is_valid():
                    comienza = formato24h(f.cleaned_data['comienza'])
                    termina = formato24h(f.cleaned_data['termina'])
                    pasantia = Pasantia(inscripcion=inscripcion,
                                        institucion=f.cleaned_data['institucion'],
                                        direccion=f.cleaned_data['direccion'],
                                        telefono=f.cleaned_data['telefono'],
                                        correo=f.cleaned_data['correo'],
                                        departamento=f.cleaned_data['departamento'],
                                        jefeinmediato=f.cleaned_data['jefeinmediato'],
                                        cargo=f.cleaned_data['cargo'],
                                        cargoadesempenar=f.cleaned_data['cargoadesempenar'],
                                        fecha=datetime.now().date(),
                                        inicio=f.cleaned_data['inicio'],
                                        fin=f.cleaned_data['fin'],
                                        comienza=comienza,
                                        termina=termina,
                                        aprobador=request.session['persona'],
                                        horas=f.cleaned_data['horas'],
                                        faltas=f.cleaned_data['faltas'],
                                        atrasos=f.cleaned_data['atrasos'],
                                        calificacion=f.cleaned_data['calificacion'])
                    pasantia.save(request)
                    log(u'Adicionada pasantia: %s' % pasantia, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                pasantia = Pasantia.objects.get(pk=request.POST['id'])
                f = PasantiaForm(request.POST)
                if f.is_valid():
                    comienza = formato24h(f.cleaned_data['comienza'])
                    termina = formato24h(f.cleaned_data['termina'])
                    pasantia.institucion = f.cleaned_data['institucion']
                    pasantia.direccion = f.cleaned_data['direccion']
                    pasantia.telefono = f.cleaned_data['telefono']
                    pasantia.correo = f.cleaned_data['correo']
                    pasantia.departamento = f.cleaned_data['departamento']
                    pasantia.jefeinmediato = f.cleaned_data['jefeinmediato']
                    pasantia.cargo = f.cleaned_data['cargo']
                    pasantia.cargoadesempenar = f.cleaned_data['cargoadesempenar']
                    pasantia.inicio = f.cleaned_data['inicio']
                    pasantia.fin = f.cleaned_data['fin']
                    pasantia.comienza = comienza
                    pasantia.termina = termina
                    pasantia.horas = f.cleaned_data['horas']
                    pasantia.faltas = f.cleaned_data['faltas']
                    pasantia.atrasos = f.cleaned_data['atrasos']
                    pasantia.calificacion = f.cleaned_data['calificacion']
                    pasantia.save(request)
                    log(u'Modifico pasantia: %s' % pasantia, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'reprobar':
            try:
                pasantia = Pasantia.objects.get(pk=request.POST['id'])
                f = PasantiaAprobarForm(request.POST)
                if f.is_valid():
                    pasantia.aprobador = request.session['persona']
                    pasantia.aprobado = False
                    pasantia.fecha_aprobacion = datetime.now().date()
                    pasantia.comentarios_aprobador = f.cleaned_data['comentarios_aprobador']
                    pasantia.save(request)
                    log(u'Rechazo pasantia: %s' % pasantia, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'del':
            try:
                pasantia = Pasantia.objects.get(pk=request.POST['id'])
                log(u'Elimino pasantia: %s' % pasantia, request, "del")
                pasantia.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {}
        adduserdata(request, data)
        data['title'] = u'Listado de pasantes'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar pasantia'
                    inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    if 'origen' in request.GET:
                        data['origen'] = request.GET['origen']
                    data['inscripcion'] = inscripcion
                    data['form'] = PasantiaForm(initial={'inicio': datetime.now().strftime("%d-%m-%Y"),
                                                         'fin': datetime.now().strftime("%d-%m-%Y"),
                                                         'comienza': '9:00 AM',
                                                         'termina': '6:00 PM',
                                                         'horas': '0',
                                                         'faltas': '0',
                                                         'atrasos': '0',
                                                         'calificacion': '0'})
                    return render(request, "adm_pasantias/add.html", data)
                except Exception as ex:
                    pass

            if action == 'listapasantias':
                try:
                    data['title'] = u'Listado de pasantias'
                    inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    pasantias = Pasantia.objects.filter(inscripcion=inscripcion).order_by('-inicio')
                    data['inscripcion'] = inscripcion
                    data['pasantias'] = pasantias
                    data['reporte_0'] = obtener_reporte('formulario_pasantia')
                    data['reporte_1'] = obtener_reporte('carta_pasantia')
                    return render(request, "adm_pasantias/listapasantias.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Actualizar pasantia'
                    pasantia = Pasantia.objects.get(pk=request.GET['id'])
                    data['pasantia'] = pasantia
                    data['form'] = PasantiaForm(initial={'institucion': pasantia.institucion,
                                                         'direccion': pasantia.direccion,
                                                         'telefono': pasantia.telefono,
                                                         'correo': pasantia.correo,
                                                         'departamento': pasantia.departamento,
                                                         'jefeinmediato': pasantia.jefeinmediato,
                                                         'cargo': pasantia.cargo,
                                                         'cargoadesempenar': pasantia.cargoadesempenar,
                                                         'inicio': pasantia.inicio,
                                                         'fin': pasantia.fin,
                                                         'comienza': formato12h(str(pasantia.comienza)),
                                                         'termina': formato12h(str(pasantia.termina)),
                                                         'horas': pasantia.horas,
                                                         'faltas': pasantia.faltas,
                                                         'atrasos': pasantia.atrasos,
                                                         'calificacion': pasantia.calificacion})
                    return render(request, "adm_pasantias/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'del':
                try:
                    data['title'] = u'Borrar pasantia'
                    data['pasantia'] = Pasantia.objects.get(pk=request.GET['id'])
                    return render(request, "adm_pasantias/del.html", data)
                except Exception as ex:
                    pass

            elif action == 'aprobar':
                try:
                    pasantia = Pasantia.objects.get(pk=request.GET['id'])
                    pasantia.aprobado = True
                    pasantia.fecha_aprobacion = datetime.now().date()
                    pasantia.aprobador = request.session['persona']
                    pasantia.save(request)
                    log(u'Aprobo pasantia: %s' % pasantia, request, "edit")
                    return HttpResponseRedirect("/adm_pasantias?action=ver&id=" + str(pasantia.inscripcion.id))
                except Exception as ex:
                    pass

            elif action == 'reprobar':
                try:
                    data['title'] = u'Reprobar pasantia'
                    data['pasantia'] = Pasantia.objects.get(pk=request.GET['id'])
                    f = PasantiaAprobarForm()
                    data['form'] = f
                    return render(request, "adm_pasantias/reprobar.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            pasantes = Inscripcion.objects.annotate(pasantias=Count('pasantia__id')).filter(pasantias__gt=0)
            if 'id' in request.GET:
                ids = request.GET['id']
                pasantes = Inscripcion.objects.annotate(pasantias=Count('pasantia__id')).filter(id=ids, pasantias__gt=0)
            elif 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                while '' in ss:
                    ss.remove('')
                if len(ss) == 1:
                    pasantes = Inscripcion.objects.annotate(pasantias=Count('pasantia__id')).filter(Q(persona__nombres__icontains=search) |
                                                                                                    Q(persona__apellido1__icontains=search) |
                                                                                                    Q(persona__apellido2__icontains=search) |
                                                                                                    Q(persona__cedula__icontains=search) |
                                                                                                    Q(persona__pasaporte__icontains=search)).filter(pasantias__gt=0)
                else:
                    pasantes = Inscripcion.objects.annotate(pasantias=Count('pasantia__id')).filter(Q(persona__apellido1__icontains=ss[0]) &
                                                                                                    Q(persona__apellido2__icontains=ss[1])).filter(pasantias__gt=0)
            paging = MiPaginador(pasantes, 25)
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
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['pasantes'] = page.object_list
            return render(request, "adm_pasantias/view.html", data)