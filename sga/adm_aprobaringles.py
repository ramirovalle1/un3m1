# -*- coding: UTF-8 -*-
import io
import random
import sys

import xlsxwriter
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
import xlwt
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Context
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt
from xlwt import *
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import EMAIL_DOMAIN

from sga.commonviews import adduserdata

from sga.funciones import MiPaginador, log, generar_nombre
from sga.models import Persona
from .forms import AprobarCertificadoIdiomaForm
from .models import *
from django.db.models import Value, Count, Sum, F, FloatField
from django.db.models import Count, Case, When, CharField, F
from django.db.models.functions import Coalesce

# @csrf_exempt
@login_required(redirect_field_name='ret', login_url='/loginsagest')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    persona = request.session['persona']
    periodo = request.session['periodo']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'aprobar':
            try:
                with transaction.atomic():
                    form = AprobarCertificadoIdiomaForm(request.POST)
                    if form.is_valid():
                        certificado = CertificadoIdioma.objects.get(pk=request.POST['id'])
                        inscripcion = Inscripcion.objects.get(pk=request.POST['idextra'])
                        perfilusu = inscripcion.perfil_usuario()
                        if not HistorialCertificacionPersona.objects.filter(certificado=certificado, aprueba=persona,
                                                                            estado=form.cleaned_data['estado'],
                                                                            perfilusuario=perfilusu,
                                                                            observacion=form.cleaned_data['observacion']).exists():
                            historial = HistorialCertificacionPersona(
                                certificado=certificado,
                                aprueba=persona,
                                estado=form.cleaned_data['estado'],
                                fecha=datetime.now(),
                                perfilusuario=perfilusu,
                                observacion=form.cleaned_data['observacion']
                            )
                            historial.save(request)
                            certificado.estado = historial.estado
                            log(u'Aprobó certificación de inglés: %s' % certificado, request, "add")

                        return JsonResponse({"result": False}, safe=False)
                    else:
                        raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'aprobar':
                try:
                    form = AprobarCertificadoIdiomaForm()
                    data['form2'] = form
                    data['id'] = request.GET['id']
                    data['idextra'] = request.GET['idextra']
                    template = get_template("adm_aprobaringles/modal/formaprobar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verhistorial':
                try:
                    data['title'] = u'Ver Historial'
                    data['id'] = id = request.GET['id']
                    data['idextra'] = idextra = request.GET['idextra']
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=int(idextra))
                    data['certificacion'] = certificacion = CertificadoIdioma.objects.get(pk=id)
                    data['detalle'] = certificacion.historial(inscripcion.perfil_usuario())
                    template = get_template("adm_aprobaringles/modal/historial.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'certificado':
                try:
                    data['title'] = u'Ver certificado'
                    data['id'] = id = request.GET['id']
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=int(id))
                    data['certificaciones'] = certificaciones = CertificadoIdioma.objects.filter(persona=inscripcion.persona,status=True)
                    template = get_template("adm_aprobaringles/modal/certificados.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Aprobar suficiencia en Inglés'
            carrera_id = CoordinadorCarrera.objects.values_list('carrera_id').filter(persona=persona, periodo=periodo, status=True)
            certi_id = CertificadoIdioma.objects.values_list('persona_id').filter(status=True)
            url_vars = ''
            filtro = Q(status=True, aplica_b2=True, carrera_id__in=carrera_id, persona_id__in=certi_id, coordinacion_id__in=[1, 2, 3, 4, 5])
            if persona.usuario.is_superuser:
                filtro = Q(status=True, aplica_b2=True, persona_id__in=certi_id, coordinacion_id__in=[1, 2, 3, 4, 5])
            search = None
            ids = None
            tipo = None

            if 't' in request.GET:
                if request.GET['t'] != '0':
                    tipo = request.GET['t']
            if 's' in request.GET:
                if request.GET['s'] != '':
                    search = request.GET['s']

            # inscritos = Inscripcion.objects.filter(filtro).exclude(graduado__status=True)
            inscritos = Inscripcion.objects.annotate(totalgraduado=Count('graduado', distinct=True)).filter(filtro)

            if search:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    filtro = filtro & (Q(persona__nombres__icontains=search) |
                                       Q(persona__apellido1__icontains=search) |
                                       Q(persona__apellido2__icontains=search) |
                                       Q(persona__cedula__icontains=search) |
                                       Q(persona__pasaporte__icontains=search))
                else:
                    filtro = filtro & (Q(persona__apellido1__icontains=ss[0]) &
                                       Q(persona__apellido2__icontains=ss[1]))
                url_vars += '&s=' + search
                # inscritos=Inscripcion.objects.filter(filtro).exclude(graduado__status=True)
                inscritos=Inscripcion.objects.annotate(totalgraduado=Count('graduado', distinct=True)).filter(filtro, aplica_b2=True)


            paging = MiPaginador(inscritos, 20)
            p = 1
            try:
                paginasesion = 1
                if 'paginador' in request.session:
                    paginasesion = int(request.session['paginador'])
                if 'page' in request.GET:
                    p = int(request.GET['page'])
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
            data['t'] = int(tipo) if tipo else ''
            data["url_vars"] = url_vars
            data['ids'] = ids if ids else ""
            data['inscritos'] = page.object_list
            data['email_domain'] = EMAIL_DOMAIN
            return render(request, 'adm_aprobaringles/view.html', data)