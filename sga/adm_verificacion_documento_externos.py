# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import json
from django.forms import model_to_dict
from django.template import Context
from django.template.loader import get_template
from datetime import datetime
from decorators import secure_module, last_access
from matricula.funciones import valid_intro_module_estudiante
from sagest.forms import BecaValidacionForm, BecaPersonaForm, InstitucionForm
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import SolicitudForm
from django.db.models.aggregates import Avg
from sga.funciones import MiPaginador, generar_nombre, log
from sga.models import RecordAcademico, SolicitudMatricula, SolicitudDetalle, Matricula, MateriaAsignada, TipoSolicitud, \
    ConfiguracionTerceraMatricula, Inscripcion, BecaPersona, Carrera, CampoArtistico, InstitucionBeca
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
                form = BecaValidacionForm(request.POST)
                if form.is_valid():
                    becado = BecaPersona.objects.get(pk=int(request.POST['id']))
                    becado.estadoarchivo = form.cleaned_data['estadobecado']
                    becado.observacion = form.cleaned_data['observacionbecado'].strip().upper()
                    becado.verificado = True if int(form.cleaned_data['estadobecado']) == 2 else False
                    becado.save(request)
                    log(u'Actualizó registro de becado: %s' % becado, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        elif action == 'add':
            try:
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                form = BecaPersonaForm(request.POST, request.FILES)
                if not form.is_valid():
                    # [(k, v[0]) for k, v in f.errors.items()]
                    for k, v in form.errors.items():
                        raise NameError(f'{k}:{v[0]}')
                personabeca = BecaPersona(
                    persona_id=form.cleaned_data['persona'],
                    tipoinstitucion=form.cleaned_data['tipoinstitucion'],
                    institucion=form.cleaned_data['institucion'],
                    archivo=form.cleaned_data['archivo'],
                    fechainicio=form.cleaned_data['fechainicio'],
                    fechafin=form.cleaned_data['fechafin'])
                personabeca.save(request)
                log(u'Agregar  Registro de Becario Externo: %s' % personabeca, request, "add")
                return JsonResponse({"result": True, "mensaje": u"Adiciono Solicitud de Beca correctamente a %s" % (personabeca)}, safe=False)
            except Exception as ex:
                msg = str(ex)
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'edit':
            try:
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                    arch._name = generar_nombre("archivobeca", arch._name)

                form = BecaPersonaForm(request.POST, request.FILES)
                personabeca = BecaPersona.objects.get(pk=int(encrypt(request.POST['id'])))
                if not form.is_valid():
                    # [(k, v[0]) for k, v in f.errors.items()]
                    for k, v in form.errors.items():
                        raise NameError(f'{k}:{v[0]}')

                if 'archivo' in request.FILES:
                    personabeca.archivo = arch

                personabeca.persona_id = form.cleaned_data['persona']
                personabeca.tipoinstitucion = form.cleaned_data['tipoinstitucion']
                personabeca.institucion = form.cleaned_data['institucion']
                personabeca.archivo = form.cleaned_data['archivo']
                personabeca.fechainicio = form.cleaned_data['fechainicio']
                personabeca.fechafin = form.cleaned_data['fechafin']
                personabeca.save(request)
                log(u'Edito  registro de Becario Externo: %s' % personabeca, request, "edit")
                return JsonResponse({"result": True, "mensaje": u"Edito Solicitud de Beca correctamente a %s" % (personabeca)}, safe=False)
            except Exception as ex:
                msg = str(ex)
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'delete':
            try:
                registro = BecaPersona.objects.get(pk=int(encrypt(request.POST['id'])))
                registro.status = False
                registro.save(request)
                log(u'Elimino registro de Becario Externo: %s' % registro, request, "del")
                return JsonResponse({"result": True, "mensaje": u"Registro Eliminado Correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al eliminar los datos."})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'datos':
                try:
                    becado = BecaPersona.objects.get(pk=int(request.GET['id']))
                    data['becado'] = becado
                    form = BecaValidacionForm(initial={'estadobecado':becado.estadoarchivo, 'observacionbecado':becado.observacion})
                    form.editar()
                    form.fields['estadobecado'].choices = (
                                ('', u'--Seleccione--'),
                                (2, u'VALIDADO'),
                                (3, u'RECHAZADO'),
                                (5, u'REVISIÓN'),
                                (6, u'RECHAZADO IO')
                    )
                    data['form'] = form
                    template = get_template("adm_verificacion_documento/externos/datos.html")
                    return JsonResponse({"result": True, 'datos': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': u'Error al obtener los datos'})

            elif action == 'add':
                try:
                    data['title'] = u'Adicionar Becario Externo'
                    data['form'] = BecaPersonaForm()
                    data['action'] = action
                    template = get_template("adm_verificacion_documento/externos/form.html")
                    return JsonResponse({"result": True, 'data': template.render(data), 'title': data['title']})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al editar los datos."})

            elif action == 'edit':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['becado'] = becado = BecaPersona.objects.get(pk=id)
                    data['title'] = u'Editar Becario Externo'
                    data['form'] = BecaPersonaForm(initial=model_to_dict(becado))
                    data['action'] = action
                    template = get_template("adm_verificacion_documento/externos/form.html")
                    return JsonResponse({"result": True, 'data': template.render(data), 'title': data['title']})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al editar los datos."})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Verificación de Documentos'
                search = None
                ids = None
                inscripcionid = None
                # cursor = connection.cursor()
                inscripciones = Inscripcion.objects.filter(matricula__status=True,
                                                           matricula__nivel__periodo=periodo,
                                                            persona__becapersona__isnull=False,
                                                            persona__becapersona__status=True)

                externos = BecaPersona.objects.filter(
                    pk__in=inscripciones.values_list('persona__becapersona__id', flat=True).distinct(),
                    persona__inscripcion__matricula__nivel__periodo=periodo
                )

                carreras = Carrera.objects.filter(id__in=inscripciones.values_list('carrera_id', flat=True).distinct())
                instituciones = InstitucionBeca.objects.filter(
                    id__in=externos.values_list('institucion_id', flat=True).distinct())

                if 's' in request.GET:
                    search = request.GET['s']
                    externos = externos.filter(Q(persona__nombres__icontains=search) |
                                               Q(persona__cedula__icontains=search) |
                                               Q(persona__apellido1__icontains=search) |
                                               Q(persona__apellido2__icontains=search)
                                               )
                verificacion = 0
                if 'veri' in request.GET:
                    verificacion = int(request.GET['veri'])
                    if verificacion > 0:
                        externos = externos.filter(verificado=int(request.GET['veri']) == 1)

                carreraselect = 0
                if 'c' in request.GET:
                    carreraselect = int(request.GET['c'])
                    if carreraselect > 0:
                        externos = externos.filter(persona__inscripcion__carrera_id=carreraselect)

                modalidadselect = 0
                if 'm' in request.GET:
                    modalidadselect = int(request.GET['m'])
                    if modalidadselect > 0:
                        externos = externos.filter(persona__inscripcion__modalidad_id=modalidadselect)

                institucionselect = 0
                if 'inst' in request.GET:
                    institucionselect = int(request.GET['inst'])
                    if institucionselect > 0:
                        externos = externos.filter(institucion_id=institucionselect)

                externos = externos.order_by("persona")

                paging = MiPaginador(externos, 25)

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
                data['externos'] = page.object_list
                data['carreras'] = carreras
                data['carreraselect'] = carreraselect
                data['instituciones'] = instituciones
                data['institucionselect'] = institucionselect
                data['form2'] = InstitucionForm()
                data['modalidadselect'] = modalidadselect
                data['verificacion'] = verificacion
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['reporte_1'] = obtener_reporte('hoja_vida_sagest')
                data['reporte_2'] = obtener_reporte('discapacitados')

                return render(request, "adm_verificacion_documento/externos/view.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                pass