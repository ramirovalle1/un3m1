# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador
from sga.models import Profesor, AsignaturaMallaPreferencia
from sga.funcionesxhtml2pdf import conviert_html_to_pdf


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    persona = request.session['persona']

    if 'action' in request.POST:
        action = request.POST['action']

        if action == 'pdfmateriaspreferencias':
            try:
                data = {}
                data['periodo'] = periodo
                data['profesor'] = profesor = Profesor.objects.select_related().get(pk=request.POST['id'])
                data['materiaspreferencias'] = AsignaturaMallaPreferencia.objects.filter(profesor=profesor, periodo=periodo, status=True).order_by('id')
                return conviert_html_to_pdf(
                    'adm_promateriaspreferencias/materiaspreferencias_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Docentes asignaturas de preferencias'
        if 'action' in request.GET:
            action = request.GET['action']

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            idc = None
            periodo = request.session['periodo']
            data['coordinaciones'] = coordinaciones = persona.mis_coordinaciones()
            if 'idc' in request.GET:
                data['idc'] = idc = int(request.GET['idc'])
            else:
                data['idc'] = None
            if 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                if len(ss) == 2:
                    if idc:
                        profesores = AsignaturaMallaPreferencia.objects.filter(Q(profesor__persona__apellido1__icontains=ss[0]) &
                                                                                                Q(profesor__persona__apellido2__icontains=ss[1])).distinct()
                    else:
                        profesores = AsignaturaMallaPreferencia.objects.filter(Q(profesor__persona__apellido1__icontains=ss[0]) &
                                                                                                         Q(profesor__persona__apellido2__icontains=ss[1])).order_by('profesor').distinct()

                else:
                    if idc:
                        profesores = AsignaturaMallaPreferencia.objects.filter(Q(profesor__persona__nombres__icontains=search) |
                                                                                                Q(profesor__persona__apellido1__icontains=search) |
                                                                                                Q(profesor__persona__apellido2__icontains=search) |
                                                                                                Q(profesor__persona__cedula__icontains=search)).order_by('profesor').distinct()
                    else:
                        profesores = AsignaturaMallaPreferencia.objects.filter(Q(profesor__persona__nombres__icontains=search) |
                                                                                                         Q(profesor__persona__apellido1__icontains=search) |
                                                                                                         Q(profesor__persona__apellido2__icontains=search) |
                                                                                                         Q(profesor__persona__cedula__icontains=search)).order_by('profesor').distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                if idc:
                    profesores = AsignaturaMallaPreferencia.objects.filter(pk=[idc])
                else:
                    profesores = AsignaturaMallaPreferencia.objects.filter(pk=coordinaciones)
            else:
                if idc:
                    profesores = AsignaturaMallaPreferencia.objects.all().order_by('profesor').distinct()
                else:
                    profesores = AsignaturaMallaPreferencia.objects.values_list('profesor__id').filter(periodo=periodo, status=True).distinct()
                    profesores = Profesor.objects.filter(pk__in=profesores).order_by('persona')
            paging = MiPaginador(profesores, 25)
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
            # data['reporte_1'] = obtener_reporte('hoja_vida_sagest')
            # data['reporte_2'] = obtener_reporte('actividades_horas_docente_facu')
            # data['reporte_3'] = obtener_reporte('actividades_horas_docente_facu_profesor')
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['idc'] = idc if idc else ""
            data['profesores'] = page.object_list
            return render(request, "adm_promateriaspreferencias/view.html", data)