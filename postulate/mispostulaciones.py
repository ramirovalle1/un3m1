# -*- coding: latin-1 -*-
#decoradores

from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from django.forms import model_to_dict
from decorators import last_access, secure_module
from postulate.forms import SolicitudApelacionForm, AceptarDesistirForm
from postulate.models import Convocatoria, Partida, PersonaAplicarPartida, PersonaIdiomaPartida, \
    PersonaFormacionAcademicoPartida, PersonaExperienciaPartida, PersonaCapacitacionesPartida, \
    PersonaPublicacionesPartida, CriterioApelacion, FactorApelacion, PersonaApelacion, TurnoConvocatoria, \
    HorarioConvocatoria, HorarioPersonaPartida
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime

from postulate.postular import validar_campos
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre, log, email_valido, MiPaginador
from sga.models import miinstitucion, CUENTAS_CORREOS
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginpostulate')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['url_'] = request.path
    perfilprincipal = request.session['perfilprincipal']
    persona = request.session['persona']
    periodo = request.session['periodo']
    data['hoy'] = hoy = datetime.now().date()
    data['currenttime'] = datetime.now()
    data['perfil'] = persona.mi_perfil()
    data['periodo'] = periodo

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'delpartida':
            try:
                with transaction.atomic():
                    instancia = PersonaAplicarPartida.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    PersonaIdiomaPartida.objects.filter(personapartida=instancia).update(status=False)
                    PersonaFormacionAcademicoPartida.objects.filter(personapartida=instancia).update(status=False)
                    PersonaExperienciaPartida.objects.filter(personapartida=instancia).update(status=False)
                    PersonaCapacitacionesPartida.objects.filter(personapartida=instancia).update(status=False)
                    PersonaPublicacionesPartida.objects.filter(personapartida=instancia).update(status=False)
                    instancia.save(request)
                    send_html_mail(u"Postulación eliminada, Postúlate-UNEMI.", "emails/postulate_eliminar_partida.html",
                                   {'sistema': u'Postúlate-UNEMI', 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'persona': persona,
                                    'partida': instancia, 't': miinstitucion(), 'tit': 'Postulate - Unemi'}, persona.lista_emails_envio(), [], [], cuenta=CUENTAS_CORREOS[30][1])
                    log(u'Elimino Postulación Partida: %s' % instancia, request, "delete")
                    return JsonResponse({"error": False}, safe=False)
            except Exception as ex:
                return JsonResponse({'error': True, "message": "Error: {}".format(ex)}, safe=False)

        if action == 'apelar':
            try:
                with transaction.atomic():
                    instance = PersonaAplicarPartida.objects.get(pk=request.POST['id'])
                    form = SolicitudApelacionForm(request.POST, request.FILES)
                    if 'archivo' in request.FILES:
                        archivo_ = request.FILES['archivo']
                    newfilesd = archivo_._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if not ext == '.pdf':
                        return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf."})
                    if archivo_.size > 80485760:
                        return JsonResponse({"result": True, "mensaje": u"Error, archivo mayor a 20 Mb."})
                    if form.is_valid():
                        factoresid = request.POST.getlist('factor')
                        if len(factoresid) == 0:
                            return JsonResponse({"result": True, "mensaje": "Debe seleccionar factores para continuar con su solicitud."}, safe=False)
                        instance.solapelacion = True
                        instance.save(request)
                        apelacion = PersonaApelacion(personapartida=instance)
                        apelacion.observacion = request.POST['observacion']
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile:
                                newfile._name = generar_nombre("evidencia_apelacion_", newfile._name)
                                apelacion.archivo = newfile
                        apelacion.save(request)
                        for fact in factoresid:
                            apelacion.factores.add(fact)
                        apelacion.save(request)
                        log(u'Registro Solicitud de Apelación: %s' % apelacion, request, "add")
                        return JsonResponse({"result": False, "form": [{k: v[0]} for k, v in form.errors.items()], "modalsuccess": True, "mensaje": "Solicitud registrada con exito, será validada en un lapso de 24 horas desde la emisión de la solicitud."}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. {}".format(ex)}, safe=False)

        if action == 'confirmarpostulacion':
            try:
                with transaction.atomic():
                    instance = PersonaAplicarPartida.objects.get(pk=request.POST['id'])
                    notificacionganador = instance.notificacion_ganador()
                    form = AceptarDesistirForm(request.POST, request.FILES)
                    if 'archivo' in request.FILES:
                        archivo_ = request.FILES['archivo']
                    newfilesd = archivo_._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if not ext == '.pdf':
                        return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf."})
                    if archivo_.size > 80485760:
                        return JsonResponse({"result": True, "mensaje": u"Error, archivo mayor a 20 Mb."})
                    if form.is_valid():
                        notificacionganador.observacion = request.POST['observacion']
                        notificacionganador.estado = request.POST['estado']
                        notificacionganador.fecharespuesta=datetime.now().date()
                        notificacionganador.respondioganador=True
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile:
                                newfile._name = generar_nombre("evidencia_apelacion_", newfile._name)
                                notificacionganador.archivo = newfile
                        notificacionganador.save(request)

                        log(u'Respondió aceptación/rechazo de ganador postulate: %s' % notificacionganador, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. {}".format(ex)}, safe=False)

        if action == 'seleccionahorario':
                try:
                    horario = HorarioConvocatoria.objects.get(pk=int(encrypt(request.POST['horario'])))
                    partida = PersonaAplicarPartida.objects.get(pk=int(encrypt(request.POST['partida'])))
                    if horario.tiene_cupo():
                        seleccion = HorarioPersonaPartida(partida=partida, horario=horario)
                        seleccion.save()
                        asunto = u"AGENDAMIENTO DE TURNO "

                        send_html_mail(asunto, "postulate/mispostulaciones/mails/notifica_horarios.html",
                                       {'sistema': u'Postúlate-UNEMI', 'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(), 'persona': partida.persona,
                                        'horario': horario, 't': miinstitucion(), 'tit': 'Postulate - Unemi'}
                                       , partida.persona.lista_emails_envio(), [], [], cuenta=CUENTAS_CORREOS[30][1])

                        log(u'Seleccionó horario : %s' % (seleccion), request, "add")
                        return JsonResponse({"error": False, 'mensaje': 'Cambios guardados'})
                    else:
                        return JsonResponse({"error": True,'mensaje': 'Horario no tiene cupo'})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': False, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'delseleccionhorario':
            try:
                with transaction.atomic():
                    horario = HorarioConvocatoria.objects.get(pk=int(encrypt(request.POST['horario'])))
                    partida = PersonaAplicarPartida.objects.get(pk=int(encrypt(request.POST['partida'])))
                    HorarioPersonaPartida.objects.filter(status=True,horario=horario,partida=partida).update(status=False)
                    log(u'Elimino horario seleccionado: %s - partida: %s' % (horario,partida), request, "del")
                    return JsonResponse({"error": False}, safe=False)
            except Exception as ex:
                return JsonResponse({'error': True, "message": "Error: {}".format(ex)}, safe=False)


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'verdetalle':
                try:
                    data['id'] = id = encrypt(request.GET['id'])
                    data['filtro'] = filtro = Partida.objects.get(pk=id)
                    data['resp_campos'] = validar_campos(request, persona, filtro)
                    template = get_template("postulate/postular/verdetalle.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'verapelacion':
                try:
                    data['id'] = id = encrypt(request.GET['id'])
                    data['filtro'] = filtro = PersonaApelacion.objects.get(pk=id)
                    template = get_template("postulate/mispostulaciones/verapelacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'apelar':
                try:
                    data['id'] = id = encrypt(request.GET['id'])
                    data['filtro'] = filtro = PersonaAplicarPartida.objects.get(pk=id)
                    form = SolicitudApelacionForm()
                    form.fields['factor'].queryset = FactorApelacion.objects.none()
                    data['form'] = form
                    template = get_template("postulate/mispostulaciones/formapelacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'buscarfactores':
                try:
                    idscriterios = request.GET.getlist('criterio[]')
                    data['listcriterios'] = criterio = CriterioApelacion.objects.filter(id__in=list(idscriterios))
                    data['listado'] = FactorApelacion.objects.filter(criterio__in=criterio.values_list('id', flat=True), status=True).order_by('descripcion')


                    template = get_template("postulate/mispostulaciones/cbfactores.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': str(ex)})

            if action == 'vercalificar':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['postulante'] = postulante = PersonaAplicarPartida.objects.get(pk=id)
                    data['partida'] = partida = Partida.objects.get(pk=postulante.partida.pk)
                    data['resp_campos'] = validar_campos(request, persona, partida)
                    data['persona'] = postulante.persona
                    data['posidiomas'] = posidiomas = PersonaIdiomaPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['postitulacion'] = postitulacion = PersonaFormacionAcademicoPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['posexperiencia'] = posexperiencia = PersonaExperienciaPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['poscapacitacion'] = poscapacitacion = PersonaCapacitacionesPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    data['pospublicacion'] = pospublicacion = PersonaPublicacionesPartida.objects.filter(status=True, personapartida=postulante).order_by('id')
                    template = get_template("postulate/mispostulaciones/vercalificacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'confirmarpostulacion':
                try:
                    data['id'] = request.GET['id']
                    data['form'] = form = AceptarDesistirForm()
                    template = get_template("ajaxformmodalpos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'horarios':
                try:
                    id = int(encrypt(request.GET['id']))
                    data['postulante'] = postulante = PersonaAplicarPartida.objects.get(id=int(encrypt(request.GET['id'])))
                    data['convocatoria'] = convocatoria = postulante.partida.convocatoria
                    data['title'] = u'Horarios de %s' % (postulante.partida)
                    data['semana'] = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
                    horarios = HorarioConvocatoria.objects.values("turno_id").filter(convocatoria=convocatoria,status=True,mostrar=True,fecha__gte=hoy)
                    data['turnos'] = TurnoConvocatoria.objects.filter(id__in=horarios, mostrar=True).order_by('comienza')
                    return render(request, "postulate/mispostulaciones/viewhorarios.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Mis Postulaciones'
                search, filtro, url_vars = request.GET.get('s', ''), (Q(status=True) & Q(persona=persona)), ''

                if search:
                    data['search'] = search
                    url_vars += "&s={}".format(search)
                    filtro = filtro & (Q(partida__titulo__icontains=search) | Q(partida__codpartida__icontains=search))

                listado = PersonaAplicarPartida.objects.filter(filtro).order_by('-id')
                paging = MiPaginador(listado, 20)
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
                data["url_vars"] = url_vars
                data['listado'] = page.object_list
                data['list_count'] = len(listado)
                data['convocatorias_vigente'] = convocatorias = Convocatoria.objects.values('id').filter(status=True, finicio__lte=hoy, ffin__gte=hoy, vigente=True).exists()
                data['segunda_etapa_vigente'] = segunda_etapa_vigente = Convocatoria.objects.values('id').filter(id__in=listado.values_list('partida__convocatoria__id', flat=True), status=True, finicio__lte=hoy, ffin__gte=hoy, vigente=True, segundaetapa=True).exists()
                data['numpartidas'] = Partida.objects.values('id').filter(status=True, convocatoria__vigente=True, convocatoria__finicio__lte=hoy, convocatoria__ffin__gte=hoy, vigente=True).count()
                return render(request, "postulate/mispostulaciones/view.html", data)
            except Exception as ex:
                pass

