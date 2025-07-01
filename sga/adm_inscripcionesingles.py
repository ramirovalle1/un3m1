# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import AprendizajePracticoInglesForm
from sga.funciones import log, MiPaginador, variable_valor
from sga.models import Inscripcion, Malla, MateriaAsignada, AprendizajePracticoIngles
from datetime import datetime
from sga.templatetags.sga_extras import encrypt

unicode =str


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    personasesion = request.session['persona']
    periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'addhoras':
            try:
                observacion = request.POST['observacion']
                fecha = request.POST['fecha']
                horainicio = request.POST['horainicio']
                horafin = request.POST['horafin']
                materiaasignada = request.POST['materiaasignada']
                if AprendizajePracticoIngles.objects.values('id').filter(materiaasignada_id=materiaasignada, fecha=fecha, status=True).count() > 1:
                    return JsonResponse({"result": "bad", "mensaje": u"Solo se puede registrar dos horas al dia."})
                aprendizajepractico = AprendizajePracticoIngles(materiaasignada_id=materiaasignada,
                                                                observaciones=observacion,
                                                                fecha=fecha,
                                                                horainicio=horainicio,
                                                                horafin=horafin)
                aprendizajepractico.save(request)
                # log(u'Modifico malla de inscripcion: %s - %s' % (inscripcion.persona, im.malla), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editaprendizaje':
            try:
                f = AprendizajePracticoInglesForm(request.POST)
                aprendizajepractico = AprendizajePracticoIngles.objects.get(pk=int(encrypt(request.POST['id'])))
                if f.is_valid():
                    aprendizajepractico.fecha = f.cleaned_data['fechainicio']
                    aprendizajepractico.horainicio = f.cleaned_data['horainicio']
                    aprendizajepractico.horafin = f.cleaned_data['horafin']
                    aprendizajepractico.observaciones = f.cleaned_data['observaciones']
                    aprendizajepractico.save(request)
                    log(u'Modifico aprendizaje ingles: %s - %s' % (aprendizajepractico.materiaasignada.matricula, aprendizajepractico.materiaasignada.materia), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delaprendizaje':
            try:
                aprendizajepractico = AprendizajePracticoIngles.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'elimino aprendizaje ingles: %s - %s - %s - %s - %s' % (aprendizajepractico.fecha, aprendizajepractico.horainicio, aprendizajepractico.horafin, aprendizajepractico.materiaasignada.matricula, aprendizajepractico.materiaasignada.materia), request, "del")
                aprendizajepractico.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Listado de inscripciones'
        persona = request.session['persona']
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'listadohorasaprendizaje':
                try:
                    data['title'] = u'Horas de aprendizaje práctico'
                    idmallamoduloingles = variable_valor('ID_MALLAINGLES')
                    data['form2'] = AprendizajePracticoInglesForm()
                    data['fecha'] = str(datetime.now().date())[:4] + '-' + str(datetime.now().date())[5:7] + '-' + str(datetime.now().date())[8:10]
                    data['hora'] = str(datetime.now())[11:16]
                    data['inscripcion'] = inscripcion = Inscripcion.objects.select_related().get(pk=int(encrypt(request.GET['id'])))
                    data['materiaasignada'] = materiaasignada = inscripcion.matricula_set.filter(nivel__periodo=periodo,estado_matricula__in=[2,3])[0].materiaasignada_set.filter(materia__asignaturamalla__malla__id=idmallamoduloingles,retiramateria=False)[0]
                    data['horasaprendizaje'] = materiaasignada.aprendizajepracticoingles_set.filter(status=True).order_by('fecha')
                    return render(request, "adm_inscripcionesingles/listadohorasaprendizaje.html", data)
                except Exception as ex:
                    pass

            if action == 'editaprendizaje':
                try:
                    data['title'] = u'Editar aprendizaje práctico'
                    data['aprendizajepractico'] = aprendizajepractico = AprendizajePracticoIngles.objects.get(pk=int(encrypt(request.GET['idhoraaprendizaje'])))
                    form = AprendizajePracticoInglesForm(initial={'observaciones': aprendizajepractico.observaciones,
                                                                  'fechainicio': aprendizajepractico.fecha,
                                                                  'horainicio': aprendizajepractico.horainicio,
                                                                  'horafin': aprendizajepractico.horafin
                                                                  })
                    data['form'] = form
                    return render(request, "adm_inscripcionesingles/editaprendizaje.html", data)
                except Exception as ex:
                    pass

            if action == 'delaprendizaje':
                try:
                    data['title'] = u'Eliminar aprendizaje práctico'
                    data['aprendizajepractico'] = AprendizajePracticoIngles.objects.get(pk=int(encrypt(request.GET['idhoraaprendizaje'])))
                    return render(request, "adm_inscripcionesingles/delaprendizaje.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Listado de inscripciones módulos de inglés'
                persona = request.session['persona']
                periodo = request.session['periodo']
                malla = Malla.objects.get(pk=variable_valor('ID_MALLAINGLES'))
                search = None
                carreraselect = 0
                listacarreras = []
                estado_todos = False
                ids = None
                if 's' in request.GET:
                    listaestudiantesmoduloingles = MateriaAsignada.objects.values_list('matricula__inscripcion__id', flat=True).filter(matricula__estado_matricula__in=[2,3], materia__asignaturamalla__malla=malla, matricula__nivel__periodo=periodo,retiramateria=False).distinct()
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        inscripciones = Inscripcion.objects.filter(Q(persona__nombres__icontains=search) |
                                                                   Q(persona__apellido1__icontains=search) |
                                                                   Q(persona__apellido2__icontains=search) |
                                                                   Q(persona__cedula__icontains=search) |
                                                                   Q(persona__pasaporte__icontains=search) |
                                                                   Q(identificador__icontains=search) |
                                                                   Q(inscripciongrupo__grupo__nombre__icontains=search) |
                                                                   Q(persona__usuario__username__icontains=search), pk__in=listaestudiantesmoduloingles).distinct()
                    else:
                        inscripciones = Inscripcion.objects.filter(Q(persona__apellido1__icontains=ss[0]) &
                                                                   Q(persona__apellido2__icontains=ss[1]), pk__in=listaestudiantesmoduloingles).distinct()
                else:
                    listaestudiantesmoduloingles = MateriaAsignada.objects.values_list('matricula__inscripcion__id',flat=True).filter(matricula__estado_matricula__in=[2,3], materia__asignaturamalla__malla=malla, matricula__nivel__periodo=periodo,retiramateria=False).distinct()
                    inscripciones = Inscripcion.objects.filter(pk__in=listaestudiantesmoduloingles)
                paging = MiPaginador(inscripciones, 15)
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
                data['inscripciones'] = page.object_list
                data['periodo'] = request.session['periodo']
                data['carreraselect'] = carreraselect
                data['carreras'] = 0
                return render(request, "adm_inscripcionesingles/view.html", data)
            except Exception as ex:
                pass
