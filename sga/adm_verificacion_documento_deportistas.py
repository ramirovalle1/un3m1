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
from sagest.forms import DeportistaValidacionForm
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import SolicitudForm
from django.db.models.aggregates import Avg
from sga.funciones import MiPaginador, generar_nombre, log
from sga.models import RecordAcademico, SolicitudMatricula, SolicitudDetalle, Matricula, MateriaAsignada, TipoSolicitud, \
    ConfiguracionTerceraMatricula, Inscripcion, DeportistaPersona, Carrera, DisciplinaDeportiva
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
                form = DeportistaValidacionForm(request.POST)
                if form.is_valid():
                    deportista = DeportistaPersona.objects.get(pk=int(request.POST['id']))
                    deportista.estadoarchivoevento = form.cleaned_data['estadoarchivoevento']
                    deportista.observacionarchevento = form.cleaned_data['observacionarchevento'].strip().upper()
                    deportista.estadoarchivoentrena = form.cleaned_data['estadoarchivoentrena']
                    deportista.observacionarchentrena = form.cleaned_data['observacionarchentrena'].strip().upper()
                    deportista.verificado = True if int(form.cleaned_data['estadoarchivoevento']) == 2 and int(form.cleaned_data['estadoarchivoentrena']) == 2 else False
                    deportista.save(request)
                    log(u'Actualizó registro de deportista: %s' % deportista, request, "edit")
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
                    deportista = DeportistaPersona.objects.get(pk=int(request.GET['id']))
                    data['deportista'] = deportista
                    form = DeportistaValidacionForm(initial={
                        'estadoarchivoevento':deportista.estadoarchivoevento,
                        'observacionarchevento':deportista.observacionarchevento,
                        'estadoarchivoentrena':deportista.estadoarchivoentrena,
                        'observacionarchentrena':deportista.observacionarchentrena,
                    })
                    form.editar()
                    form.fields['estadoarchivoevento'].choices= (
                                ('', u'--Seleccione--'),
                                (2, u'VALIDADO'),
                                (3, u'RECHAZADO'),
                                (5, u'REVISIÓN'),
                                (6, u'RECHAZADO IO')
                    )
                    form.fields['estadoarchivoentrena'].choices= (
                                ('', u'--Seleccione--'),
                                (2, u'VALIDADO'),
                                (3, u'RECHAZADO'),
                                (5, u'REVISIÓN'),
                                (6, u'RECHAZADO IO')
                    )

                    data['form'] = form
                    template = get_template("adm_verificacion_documento/deportistas/datos.html")
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
                inscripciones = Inscripcion.objects.filter(matricula__status=True, matricula__nivel__periodo=periodo,
                                persona__deportistapersona__isnull=False, persona__deportistapersona__status=True,
                                                         persona__deportistapersona__vigente=1).order_by("persona")
                deportistas = DeportistaPersona.objects.filter(
                    pk__in=inscripciones.values_list('persona__deportistapersona__id', flat=True).distinct(),
                    persona__inscripcion__matricula__nivel__periodo=periodo
                )
                carreras = Carrera.objects.filter(id__in=inscripciones.values_list('carrera_id', flat=True).distinct())
                disciplinas = DisciplinaDeportiva.objects.filter(
                    id__in=deportistas.values_list('disciplina__id', flat=True).distinct(),
                )

                if 's' in request.GET:
                    search = request.GET['s']
                    deportistas = deportistas.filter(Q(persona__nombres__icontains=search) |
                                               Q(persona__cedula__icontains=search) |
                                               Q(persona__apellido1__icontains=search) |
                                               Q(persona__apellido2__icontains=search)
                                               )
                verificacion = 0
                if 'veri' in request.GET:
                    verificacion = int(request.GET['veri'])
                    if verificacion > 0:
                        deportistas = deportistas.filter(verificado=int(request.GET['veri']) == 1)

                carreraselect = 0
                if 'c' in request.GET:
                    carreraselect = int(request.GET['c'])
                    if carreraselect > 0:
                        deportistas = deportistas.filter(persona__inscripcion__carrera_id=carreraselect)

                modalidadselect = 0
                if 'm' in request.GET:
                    modalidadselect = int(request.GET['m'])
                    if modalidadselect > 0:
                        deportistas = deportistas.filter(persona__inscripcion__modalidad_id=modalidadselect)
                
                disciplinaselect = 0
                if 'dis' in request.GET:
                    disciplinaselect = int(request.GET['dis'])
                    if disciplinaselect > 0:
                        deportistas = deportistas.filter(disciplina__id=disciplinaselect)

                deportistas = deportistas.order_by("persona")

                paging = MiPaginador(deportistas, 25)

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
                data['deportistas'] = page.object_list
                data['carreras'] = carreras
                data['carreraselect'] = carreraselect
                data['disciplinas'] = disciplinas
                data['disciplinaselect'] = disciplinaselect
                data['modalidadselect'] = modalidadselect
                data['verificacion'] = verificacion
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['reporte_1'] = obtener_reporte('hoja_vida_sagest')
                data['reporte_2'] = obtener_reporte('discapacitados')
                return render(request, "adm_verificacion_documento/deportistas/view.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                pass #return render(request, "alu_solicitudmatricula/error.html", data)
