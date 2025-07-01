# -*- coding: latin-1 -*-
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.shortcuts import render

from openpyxl import workbook as openxl
from openpyxl.styles import Font as openxlFont
from openpyxl.styles.alignment import Alignment as alin
from urllib.request import urlopen, Request
import json
from inno.models import *
import random
from decorators import secure_module, last_access
from idioma.forms import PeriodoForm, GrupoForm, PeriodoAsignaturaForm
from idioma.models import Periodo, Grupo, GrupoInscripcion, PeriodoAsignatura
from postulaciondip.forms import PrerevisionActaParaleloPosgradoForm
from postulaciondip.models import ActaSeleccionDocente, Convocatoria, ActaParalelo, PersonalAContratar, ESTADO_ACTA, \
    PersonalApoyoMaestria, InscripcionConvocatoria
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, puede_realizar_accion, log, convertir_lista
from sga.models import Empleador, Persona, CUENTAS_CORREOS, RecordAcademico, HistoricoRecordAcademico, NivelTitulacion
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from django.template.loader import get_template
from sagest.models import Pago

@login_required(redirect_field_name='ret', login_url='/loginsga')
#@secure_module
#@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['url_'] = request.path
    persona = request.session['persona']
    periodo = request.session['periodo']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'iniciar_proceso_persona':
            try:
                id = int(request.POST.get('id',0))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")
                INICIAR_PROCESO = 3
                ePersonalAContratar = PersonalAContratar.objects.get(pk=id)
                ePersonalAContratar.estado = INICIAR_PROCESO
                ePersonalAContratar.save(request)
                log(u'Confirmo el inicio de proceso: %s' % ePersonalAContratar, request, "edit")
                return JsonResponse({"result": True, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        if action == 'iniciar_proceso_todos':
            try:
                INICIAR_PROCESO = 3
                id = int(request.POST.get('id',0))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")

                eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=id)
                for ePersonalAContratar in eActaSeleccionDocente.get_ganador():
                    ePersonalAContratar.estado = INICIAR_PROCESO
                    ePersonalAContratar.save(request)
                    log(u'Confirmo el inicio de proceso: %s' % ePersonalAContratar, request, "edit")
                eActaSeleccionDocente.iniciar_proceso_legalizar_acta(request)
                log(u'Inicio legalizar acta: %s' % eActaSeleccionDocente, request, "edit")
                return JsonResponse({"result": True, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        if action == 'reprogramacion_academica_persona':
            try:
                id = int(request.POST.get('id',0))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")
                REPROGRAMACION = 2
                ePersonalAContratar = PersonalAContratar.objects.get(pk=id)
                ePersonalAContratar.estado = REPROGRAMACION
                ePersonalAContratar.save(request)
                log(u'Confirmo la reprogramacion de proceso: %s' % ePersonalAContratar, request, "edit")
                return JsonResponse({"result": True, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        if action == 'confirmar_acta_revision':
            try:
                LEGALIZAR = 3
                REPROGRAMACION = 5
                id = int(request.POST.get('id',0))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")
                eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=id)

                if not eActaSeleccionDocente.get_existen_paralelos_rechazados_prerevision():
                    eActaSeleccionDocente.estado = LEGALIZAR
                    eActaSeleccionDocente.save(request)
                    ePersonalApoyoMaestrias = None
                    eActaParalelo = ActaParalelo.objects.filter(status=True, acta=eActaSeleccionDocente)
                    if eActaParalelo.exists():
                        carrera = eActaParalelo.first().convocatoria.carrera
                        periodo = eActaParalelo.first().convocatoria.periodo
                        ePersonalApoyoMaestrias = PersonalApoyoMaestria.objects.filter(status=True, carrera=carrera,periodo=periodo)
                    eActaSeleccionDocente.notificar_acta_revisada_a_la_gestion_de_posgrado(request,ePersonalApoyoMaestrias)
                    eActaSeleccionDocente.guardar_recorrido_acta_seleccion_docente(request,
                                                                                   actaparalelo=None,
                                                                                   persona=persona,
                                                                                   observacion=f"Acta de selección docente enviada a ser legalizada por parte de los miembros del comité académico.",
                                                                                   archivo=None)
                else:
                    #existen rechazados
                    eActaSeleccionDocente.estado = REPROGRAMACION
                    eActaSeleccionDocente.save(request)
                    ePersonalApoyoMaestrias = None
                    eActaParalelo = ActaParalelo.objects.filter(status=True, acta=eActaSeleccionDocente)
                    if eActaParalelo.exists():
                        carrera = eActaParalelo.first().convocatoria.carrera
                        periodo = eActaParalelo.first().convocatoria.periodo
                        ePersonalApoyoMaestrias = PersonalApoyoMaestria.objects.filter(status=True, carrera=carrera,  periodo=periodo)
                        #notifico comite
                    eActaSeleccionDocente.notificar_acta_reprogramacion_gestion_posgrado_comite(request,ePersonalApoyoMaestrias)
                    eActaSeleccionDocente.guardar_recorrido_acta_seleccion_docente(request,
                                                                           actaparalelo=None,
                                                                           persona=persona,
                                                                           observacion=f"Acta de selección docente enviada a reprogramación por vicerrectorado acadèmico de posgrado.",
                                                                           archivo=None)

                eActaSeleccionDocente.notificar_a_la_persona_que_le_toca_firmar(request)
                log(u'Realizo la revision del acta: %s' % eActaSeleccionDocente, request, "edit")
                return JsonResponse({"result": True, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        if action == 'actualizar_principal':
            try:
                id = int(request.POST.get('id',0))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")
                ePersonalAContratarAlterno = PersonalAContratar.objects.get(pk=id)
                ePersonalAContratarAlterno.hacer_principal_y_actualizar_al_principal_anterior(request)
                ePersonalAContratarAlterno.actaparalelo.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                            actaparalelo=ePersonalAContratarAlterno.actaparalelo,
                                                                            persona=persona,
                                                                            observacion=f"Vicerrectorado académico de posgrado actualizó al profesional: {ePersonalAContratarAlterno} como {ePersonalAContratarAlterno.tipo}",
                                                                            archivo=None)
                log(u'Actualizo al nuevo principal: %s' % ePersonalAContratarAlterno, request, "edit")
                return JsonResponse({"result": True, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        if action == 'prerevision_paralelo':
            try:
                eActaParalelo = ActaParalelo.objects.get(pk=request.POST.get('id'))
                f = PrerevisionActaParaleloPosgradoForm(request.POST)

                if f.is_valid():
                    eActaParalelo.estadoprerevision = f.cleaned_data['estado']
                    eActaParalelo.save(request)
                    eActaParalelo.guardar_historial_acta_paralelo(request,persona, f.cleaned_data['estado'], f.cleaned_data['observacion'])


                    log(f"Pre revision {eActaParalelo}", request, 'edit')
                    eActaParalelo.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                                actaparalelo=eActaParalelo,
                                                                                persona=persona,
                                                                                observacion=f"Revisión realizada por vicerrectorado académico de posgrado: estado: {eActaParalelo.get_estadoprerevision_display()};",
                                                                                archivo=None)
                    return JsonResponse({'result': True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                pass


        return JsonResponse({"result": False, "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'loadViewRevisar':
                id = request.GET.get('id',0)
                eActaParalelo = ActaParalelo.objects.get(pk=id)
                data['eActaParalelo']  = eActaParalelo
                data['Principales']  = principales = eActaParalelo.get_personal_principal()
                data['Alternos']  = alternos = eActaParalelo.get_personal_alterno()
                data['elegibles']  = elegibles = eActaParalelo.convocatoria.get_postulantes_banco_elegible()

                template = get_template('seleccionposgrado/modal/revisar_view.html')
                return JsonResponse({"result": True, 'data': template.render(data)})

            if action == 'historial_reprogramacion':
                id = request.GET.get('id',0)
                eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=id)
                data['reprogramaciones']= eActaSeleccionDocente.get_historial_reprogramacion()
                template = get_template('seleccionposgrado/modal/historial_reprogramacion.html')
                return JsonResponse({"result": True, 'data': template.render(data)})

            if action == 'historial_acta_paralelo':
                id = request.GET.get('id',0)
                eActaParalelo = ActaParalelo.objects.get(pk=id)
                data['eActaParalelo']= eActaParalelo
                data['historial']= eActaParalelo.get_historial_acta_paralelo()
                template = get_template('seleccionposgrado/modal/historial_reprogramacion.html')
                return JsonResponse({"result": True, 'data': template.render(data)})

            elif action == 'modulos':
                try:
                    id = request.GET.get('id',0)
                    eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=id)
                    data['title'] = eActaSeleccionDocente
                    eActaParalelos = ActaParalelo.objects.filter(acta=eActaSeleccionDocente, status = True)
                    data["eActaParalelos"] = eActaParalelos
                    data["eActaSeleccionDocente"] = eActaSeleccionDocente
                    data["total"] = eActaParalelos.count()
                    data["rechazados"] = eActaParalelos.filter(estadoprerevision = 3).count()
                    data["aprobados"] = eActaParalelos.filter(estadoprerevision = 2).count()
                    data["pendientes"] = eActaParalelos.filter(estadoprerevision = 1).count()

                    return render(request, "seleccionposgrado/modulos.html", data)
                except Exception as ex:
                    pass

            elif action == 'baremodetallado':
                try:
                    data['title'] = 'Detalle del baremo'
                    id_acta_paralelo = int(request.GET.get('id', '0'))
                    if id_acta_paralelo == 0:
                        raise NameError("Parametro no encontrado")
                    eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=id_acta_paralelo)

                    data["eActaSeleccionDocente"] = eActaSeleccionDocente
                    return render(request, "seleccionposgrado/baremodetallado.html", data)
                except Exception as ex:
                    pass

            elif action == 'prerevision_paralelo':
                try:
                    data['action'] = action
                    data['id'] = request.GET.get('id')
                    data['form'] = form = PrerevisionActaParaleloPosgradoForm()
                    template = get_template('seleccionposgrado/modal/formModal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'ver_votaciones_por_acta':
                try:
                    with transaction.atomic():
                        pk = int(request.GET.get('id', '0'))
                        if pk == 0:
                            raise NameError("Parametro no encontrado")
                        eActaSeleccionDocente = ActaSeleccionDocente.objects.get(pk=pk)
                        data['eActaSeleccionDocente'] = eActaSeleccionDocente
                        template = get_template('adm_postulacion/modal/ver_votaciones_acta.html')
                        return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": f"{ex.__str__()}"})

            elif action == 'verdatospersonalescomite':
                try:
                    ic = None
                    eInscripcionConvocatoria = InscripcionConvocatoria.objects.filter(pk=int(encrypt(request.GET['id'])))
                    if eInscripcionConvocatoria.exists():
                        ic = eInscripcionConvocatoria.first()

                    data['eInscripcionConvocatoria'] = ic
                    data['inscripcion'] = ic.postulante
                    data['niveltituloposgrado'] = NivelTitulacion.objects.filter(pk__in=[3, 4], status=True).order_by('-rango')
                    template = get_template('adm_postulacion/modal/verdatospersonales.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'SELECCIÓN DEL PERSONAL ACÁDEMICO'
                url_vars = ' '
                pk = request.GET.get('pk', 0)
                search = None
                PENDIENTE= 1
                REVISION = 2
                LEGALIZAR =3
                LEGALIZADA =4
                filtro = Q(status=True)
                id_estado_acta = request.GET.get('id_estado_acta', 0)
                search = request.GET.get('searchinput', '')
                if int(pk) != 0:
                    filtro &= Q(pk=pk)
                    data['pk'] = int(pk)
                    url_vars += "&pk={}".format(pk)

                if id_estado_acta != 0:
                    filtro &= Q(estado=id_estado_acta)
                    data['id_estado_seleccionado'] = int(id_estado_acta)
                    url_vars += "&id_estado_acta={}".format(id_estado_acta)
                else:
                    filtro &= Q(estado__in=[REVISION, LEGALIZAR, LEGALIZADA])

                if search.isdigit():
                    filtro &= Q(numero__contains=search)
                elif search != '':
                    filtro &= Q(comite__nombre__icontains=search)
                    url_vars += "&searchinput={}".format(search)

                eActaSeleccionDocentes = ActaSeleccionDocente.objects.filter(filtro).order_by('estado','-pk')
                eActaParalelo = ActaParalelo.objects.filter(acta__in= eActaSeleccionDocentes, status = True)
                ePersonalAContratar = PersonalAContratar.objects.filter(status=True,actaparalelo__in = eActaParalelo)
                data["pendientes_de_revisar"] = ActaSeleccionDocente.objects.filter(status=True,estado__in =[REVISION]).count()
                data["por_legalizar"] = ActaSeleccionDocente.objects.filter(status=True,estado__in =[LEGALIZAR]).count()
                data["personal_pendiente"] = ePersonalAContratar.filter(status=True,estado__in =[PENDIENTE]).exclude(actaparalelo__acta__estado=4).exclude(actaparalelo__acta__estado = LEGALIZAR).count()
                data["total_personal_contratar"] = ePersonalAContratar.filter(status=True,actaparalelo__acta__estado = LEGALIZAR).count()
                data['estados_acta'] = estados_deseados = [(estado[0], estado[1]) for estado in ESTADO_ACTA if estado[0] in (REVISION,LEGALIZAR,LEGALIZADA)]

                paging = MiPaginador(eActaSeleccionDocentes, 10)
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
                data['eActaSeleccionDocentes'] = page.object_list
                data['searchinput'] = search if search else ""
                data['url_vars'] = url_vars

                return render(request, "seleccionposgrado/view.html", data)
            except Exception as ex:
                pass
