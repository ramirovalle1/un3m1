# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import json
from django.template import Context
from django.template.loader import get_template
from datetime import datetime
from decorators import secure_module, last_access
from matricula.funciones import valid_intro_module_estudiante
from sagest.forms import DeportistaValidacionForm, DiscapacidadValidacionForm, EtniaValidacionForm
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import SolicitudForm
from django.db.models.aggregates import Avg
from sga.funciones import MiPaginador, generar_nombre, log
from sga.models import RecordAcademico, SolicitudMatricula, SolicitudDetalle, Matricula, MateriaAsignada, TipoSolicitud, \
    ConfiguracionTerceraMatricula, Inscripcion, DeportistaPersona, Carrera, DisciplinaDeportiva, PerfilInscripcion
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    data['periodo'] = periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'validar':
            try:
                form = EtniaValidacionForm(request.POST)
                if form.is_valid():
                    etnia = PerfilInscripcion.objects.get(pk=int(request.POST['id']))
                    etnia.estadoarchivoraza = form.cleaned_data['estadoetnia']
                    etnia.observacionarchraza = form.cleaned_data['observacionetnia'].strip().upper()
                    etnia.verificaraza = True if int(form.cleaned_data['estadoetnia']) == 2 else False
                    etnia.save(request)
                    log(u'Actualizó registro de etnia: %s' % etnia, request, "edit")
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
            if action == 'datos':
                try:
                    etnia = PerfilInscripcion.objects.get(pk=int(request.GET['id']))
                    data['etnia'] = etnia
                    form = EtniaValidacionForm(initial={
                        'estadoetnia': etnia.estadoarchivoraza,
                        'observacionetnia': etnia.observacionarchraza,
                        'raza': etnia.raza,
                    })
                    form.editar()
                    form.fields['estadoetnia'].choices = (
                                ('', u'--Seleccione--'),
                                (2, u'VALIDADO'),
                                (3, u'RECHAZADO'),
                                (5, u'REVISIÓN'),
                                (6, u'RECHAZADO IO')
                    )

                    data['form'] = form
                    template = get_template("adm_verificacion_documento/etnias/datos.html")
                    return JsonResponse({"result": True, 'datos': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': u'Error al obtener los datos'})
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Verificación de Documentos'
                search = None
                ids = None
                inscripcionid = None
                # cursor = connection.cursor()
                etnias = Inscripcion.objects.filter(matricula__status=True,
                                                            matricula__nivel__periodo=periodo,
                                                            persona__perfilinscripcion__raza__id__in=[1, 2, 4, 5]
                                                           )
                carreras = Carrera.objects.filter(id__in=etnias.values_list('carrera_id', flat=True).distinct())
                if 's' in request.GET:
                    search = request.GET['s']
                    etnias = etnias.filter(Q(persona__nombres__icontains=search) |
                                               Q(persona__cedula__icontains=search) |
                                               Q(persona__apellido1__icontains=search) |
                                               Q(persona__apellido2__icontains=search)
                                               )
                verificacion = 0
                if 'veri' in request.GET:
                    verificacion = int(request.GET['veri'])
                    if verificacion > 0:
                        etnias = etnias.filter(persona__perfilinscripcion__verificaraza=int(request.GET['veri']) == 1)

                carreraselect = 0
                if 'c' in request.GET:
                    carreraselect = int(request.GET['c'])
                    if carreraselect > 0:
                        etnias = etnias.filter(carrera_id=carreraselect)

                modalidadselect = 0
                if 'm' in request.GET:
                    modalidadselect = int(request.GET['m'])
                    if modalidadselect > 0:
                        etnias = etnias.filter(modalidad_id=modalidadselect)

                etnias = etnias.order_by("persona")

                paging = MiPaginador(etnias, 25)

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
                data['rangospaging'] = paging.rangos_paginado(p)
                data['etnias'] = page.object_list
                data['carreras'] = carreras
                data['carreraselect'] = carreraselect
                data['modalidadselect'] = modalidadselect
                data['verificacion'] = verificacion
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['reporte_1'] = obtener_reporte('hoja_vida_sagest')
                data['reporte_2'] = obtener_reporte('discapacitados')
                return render(request, "adm_verificacion_documento/etnias/view.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                pass #return render(request, "alu_solicitudmatricula/error.html", data)
