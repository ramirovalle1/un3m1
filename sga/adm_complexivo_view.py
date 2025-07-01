# -*- coding: UTF-8 -*-
from django.db.models import Q
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sga.commonviews import adduserdata
from sga.forms import ApNeExamenComplexivoForm
from sga.funciones import MiPaginador, generar_nombre, log
from sga.models import ComplexivoPeriodo, ExamenComplexivo

@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    hoy = datetime.now().date()
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'edit_estado':
            try:
                f = ApNeExamenComplexivoForm(request.POST, request.FILES)
                if f.is_valid():
                    examencomplexivo = ExamenComplexivo.objects.get(pk=request.POST['id'])
                    if examencomplexivo.estadosolicitud != 1:
                        return JsonResponse({"result": "bad", "mensaje": u"El registro esta en uso."})
                    examencomplexivo.estadosolicitud = f.cleaned_data['estadosolicitud']
                    examencomplexivo.observacion = f.cleaned_data['observacion']
                    newfile = None
                    if 'informe' in request.FILES:
                        newfile = request.FILES['informe']
                        newfile._name = generar_nombre("informe_decano_", newfile._name)
                        examencomplexivo.informe = newfile
                    examencomplexivo.save(request)
                    log(u'Aprobo o nego solicitud complexivo: %s' % examencomplexivo, request, "edit")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'edit_estado':
                try:
                    data['title'] = u'Aprobar o Negar solicitud'
                    data['periodo'] = periodo = ExamenComplexivo.objects.get(pk=request.GET['id'])
                    form = ApNeExamenComplexivoForm()
                    form.aprobar_rechazar()
                    data['form'] = form
                    return render(request, 'adm_complexivo_view/edit_estado.html', data)
                except Exception as ex:
                    pass

            if action == 'inscritos':
                try:
                    data['title'] = u'Inscritos en examen Complexivo'
                    miscarreras = persona.mis_carreras()
                    search = None
                    tipo = None
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        solicitudes = ExamenComplexivo.objects.filter(Q(inscripcion__carrera__in=miscarreras,
                                                                        inscripcion__carrera__nombre__icontains=search) |
                                                                      Q(inscripcion__coordinacion__nombre__icontains=search) |
                                                                      Q(inscripcion__persona__nombres__icontains=search) |
                                                                      Q(inscripcion__persona__apellido1__icontains=search) |
                                                                      Q(inscripcion__persona__apellido2__icontains=search)).order_by("estadosolicitud", "inscripcion__coordinacion__nombre", "inscripcion__carrera__nombre", "inscripcion__persona")
                    else:
                        solicitudes = ExamenComplexivo.objects.filter(inscripcion__carrera__in=miscarreras).order_by("estadosolicitud", "inscripcion__coordinacion__nombre", "inscripcion__carrera__nombre", "inscripcion__persona")
                    paging = MiPaginador(solicitudes, 25)
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
                    data['solicitudes'] = page.object_list
                    data['habilitado'] = ComplexivoPeriodo.objects.filter(fecha_inicio__lte=hoy, fecha_fin__gte=hoy).exists()
                    data['periodo'] = ComplexivoPeriodo.objects.get(fecha_inicio__lte=hoy, fecha_fin__gte=hoy) if data[
                        'habilitado'] else None
                    return render(request, "adm_complexivo_view/view_inscritos.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Examen complexivo'
            search = None
            tipo = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                periodos = ComplexivoPeriodo.objects.filter(nombre__icontains=search)
            else:
                periodos = ComplexivoPeriodo.objects.all()
            paging = MiPaginador(periodos, 25)
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
            data['periodoscomplexivo'] = page.object_list
            return render(request, "adm_complexivo_view/view.html", data)
