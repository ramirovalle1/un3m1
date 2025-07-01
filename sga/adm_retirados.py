# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.funciones import log
from sga.models import RetiroMatricula, Matricula, MateriaAsignadaRetiro, Carrera


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    miscarreras = Carrera.objects.filter(grupocoordinadorcarrera__group__in=persona.grupos()).distinct()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'continua':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    if matricula.nivel.cerrado:
                        return JsonResponse({"result": "bad", "mensaje": u"El nivel se encuentra cerrado."})
                    log(u'Elimino retiro de matricula: %s' % matricula, request, "del")
                    retiro = matricula.retiromatricula_set.all()
                    retiro.delete()
                    matricula.retiradomatricula = False
                    matricula.save(request)
                    retirnomaterias = MateriaAsignadaRetiro.objects.filter(materiaasignada__matricula=matricula)
                    for rm in retirnomaterias:
                        rm.materiaasignada.retiramateria = False
                        rm.materiaasignada.save(request)
                    retirnomaterias.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'continua':
                try:
                    data['title'] = u'Continuar matricula'
                    data['matricula'] = Matricula.objects.filter(inscripcion__carrera__in=miscarreras).get(pk=request.GET['id'])
                    return render(request, "adm_retirados/continua.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Retiros de matriculas'
            periodo = request.session['periodo']
            search = None
            if 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                if len(ss) == 1:
                    retirados = RetiroMatricula.objects.filter(matricula__inscripcion__carrera__in=miscarreras).filter(Q(matricula__nivel__periodo=periodo) & (Q(matricula__inscripcion__persona__nombres__icontains=search) | Q(matricula__inscripcion__persona__apellido1__icontains=search) | Q(matricula__inscripcion__persona__apellido2__icontains=search) | Q(matricula__inscripcion__persona__cedula__icontains=search) | Q(matricula__inscripcion__persona__pasaporte__icontains=search)))
                else:
                    retirados = RetiroMatricula.objects.filter(matricula__inscripcion__carrera__in=miscarreras).filter(Q(matricula__nivel__periodo=periodo) & Q(matricula__inscripcion__persona__apellido1__icontains=ss[0]) & Q(matricula__inscripcion__persona__apellido2__icontains=ss[1]))
            else:
                retirados = RetiroMatricula.objects.filter(matricula__inscripcion__carrera__in=miscarreras).filter(matricula__nivel__periodo=periodo)
            paging = Paginator(retirados, 30)
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
            data['retirados'] = page.object_list
            return render(request, "adm_retirados/view.html", data)