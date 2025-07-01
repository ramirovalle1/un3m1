# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, variable_valor
from sga.models import OfertaLaboral, AplicanteOferta, miinstitucion, Empleador, CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'verdescripcion':
                try:
                    oferta = OfertaLaboral.objects.get(pk=request.POST['id'])
                    return JsonResponse({'result': 'ok', 'area': oferta.area, 'cargo': oferta.cargo, 'descripcion': oferta.descripcion})
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u'Error al obtener los datos'})

            if action == 'confirmar':
                try:
                    aplicante = AplicanteOferta.objects.get(pk=request.POST['id'])
                    aplicante.citaconfirmada = True
                    aplicante.save(request)
                    empresaempleadora = aplicante.oferta.empresa
                    empleador = Empleador.objects.get(empresa=empresaempleadora)
                    log(u'Confirma aplica oferta en alumno oferta laboral: %s [%s] - empresa empleadora: %s - empleador: %s' % (aplicante,aplicante.id,empresaempleadora, empleador), request, "edit")
                    send_html_mail("Cita confirmada por candidato", "emails/citaconfirmada.html", {'sistema': request.session['nombresistema'], 'registro': aplicante, 't': miinstitucion(), 'dominio': EMAIL_DOMAIN}, empleador.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[4][1])
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

            if action == "registar":
                try:
                    solicitud = OfertaLaboral.objects.get(pk=request.POST['id'])
                    if AplicanteOferta.objects.filter(oferta=solicitud, inscripcion=inscripcion).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra registrado"})
                    aplicante = AplicanteOferta(oferta=solicitud,
                                                inscripcion=inscripcion,
                                                aprobada=False,
                                                entrevistado=False)
                    aplicante.save(request)
                    log(u'Registro aplicante oferta en alumno oferta laboral: %s [%s]' % (aplicante, aplicante.id), request, "edit")
                    #lista = ['empleo@unemi.edu.ec']
                    lista = ['empleo@unemi.edu.ec']
                    if persona.emailinst:
                        lista.append(aplicante.inscripcion.persona.lista_emails_envio())
                    send_html_mail("Registrar Oferta", "emails/registraroferta.html",
                                   {'sistema': request.session['nombresistema'], 'registro': aplicante,
                                    't': miinstitucion(), 'dominio': EMAIL_DOMAIN}, lista, [],
                                   cuenta=CUENTAS_CORREOS[17][1])
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar datos"})

            if action == "cancelar":
                try:
                    oferta = OfertaLaboral.objects.get(pk=request.POST['id'])
                    if not AplicanteOferta.objects.filter(oferta=oferta, inscripcion=inscripcion).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"No se encuentra registrado"})
                    aplicante = AplicanteOferta.objects.filter(oferta=oferta, inscripcion=inscripcion)[0]
                    log(u'Elimino aplicacion a solicitud: %s' % aplicante, request, "del")
                    aplicante.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar datos"})

            if action == 'deletefertalaboral':
                try:
                    oferta = AplicanteOferta.objects.get(pk=request.POST['id'])
                    log(u'Elimino oferta laboral en alumno oferta laboral: %s' % oferta, request, "del")
                    oferta.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'registarestado':
                try:
                    aplicante = AplicanteOferta.objects.get(pk=request.POST['id'])
                    aplicante.estado=True
                    aplicante.save(request)
                    log(u'Registro aplicante oferta en alumno oferta laboral: %s [%s]' % (aplicante, aplicante.id), request, "edit")
                    send_html_mail("Registrar Oferta", "emails/registraroferta.html", {'sistema': request.session['nombresistema'], 'registro': aplicante, 't': miinstitucion(), 'dominio': EMAIL_DOMAIN}, aplicante.inscripcion.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[17][1])
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'deletefertalaboral':
                try:
                    data['title'] = u'Eliminar Oferta Laboral'
                    data['oferta'] = AplicanteOferta.objects.get(pk=request.GET['idofertalaboral'])
                    return render(request, "alu_ofertalaboral/deleteofertalaboral.html", data)
                except Exception as ex:
                    pass

            if action == 'registar':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_periodo')
                    data['title'] = u'Solicitar Oferta Laboral'
                    data['solicitud'] = OfertaLaboral.objects.get(pk=request.GET['id'])
                    return render(request, 'alu_ofertalaboral/registrar.html', data)
                except Exception as ex:
                    pass

            if action == 'registarestado':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_periodo')
                    data['title'] = u'Solicitar Oferta Laboral'
                    data['aplicanteoferta'] = AplicanteOferta.objects.get(pk=request.GET['id'])
                    return render(request, 'alu_ofertalaboral/registrarestado.html', data)
                except Exception as ex:
                    pass

            if action == 'detalle':
                try:
                    data = {}
                    data['ofertalaboral'] = ofertalaboral = OfertaLaboral.objects.get(pk=int(request.GET['id']))
                    data['carreras'] = ofertalaboral.vercarreras()
                    template = get_template("alu_ofertalaboral/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Listado de ofertas laborales'
            search = None
            ids = None
            if inscripcion.usado_graduados():
                if 'id' in request.GET:
                    ids = request.GET['id']
                    ofertas = OfertaLaboral.objects.filter(id=ids, cerrada=False, fin__gte=datetime.now().date())
                elif 's' in request.GET:
                    search = request.GET['s']
                    ofertas = OfertaLaboral.objects.filter((Q(cargo__icontains=search) |
                                                            Q(area__icontains=search) |
                                                            Q(descripcion__icontains=search)), cerrada=False, fin__gte=datetime.now().date())
                else:
                    ofertas = OfertaLaboral.objects.filter(cerrada=False, fin__gte=datetime.now().date())
            else:
                if 'id' in request.GET:
                    ids = request.GET['id']
                    ofertas = OfertaLaboral.objects.filter(id=ids, cerrada=False, graduado=False ,fin__gte=datetime.now().date())
                elif 's' in request.GET:
                    search = request.GET['s']
                    ofertas = OfertaLaboral.objects.filter((Q(cargo__icontains=search) |
                                                            Q(area__icontains=search) |
                                                            Q(descripcion__icontains=search)),graduado=False , cerrada=False,
                                                           fin__gte=datetime.now().date())
                else:
                    ofertas = OfertaLaboral.objects.filter(cerrada=False,graduado=False , fin__gte=datetime.now().date())
            # data['datoinscripcion'] = Inscripcion.
            paging = MiPaginador(ofertas, 25)
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
            data['ofertas'] = page.object_list
            data['inscripcion'] = inscripcion
            return render(request, 'alu_ofertalaboral/view.html', data)