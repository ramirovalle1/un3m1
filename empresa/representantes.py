# -*- coding: latin-1 -*-
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from empresa.forms import RepresentanteForm
from empresa.models import RepresentantesEmpresa
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, puede_realizar_accion, log
from sga.models import Empleador, Persona, CUENTAS_CORREOS
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='empresa/loginempresa')
# @secure_module
# @last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['url_'] = request.path
    perfilprincipal = request.session['perfilprincipal']
    persona = request.session['persona']
    data['hoy'] = hoy = datetime.now().date()
    data['currenttime'] = datetime.now()
    data['perfil'] = persona.mi_perfil()
    data['empresa'] = empresa = Empleador.objects.get(persona=persona)

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = RepresentanteForm(request.POST)
                filter = Q(status=True)
                if f.is_valid():
                    if not f.cleaned_data['cedula'] and not f.cleaned_data['pasaporte']:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe especificar un numero de identificación."})
                    if f.cleaned_data['cedula'] and not f.cleaned_data['cedula'] == '':
                        filter = filter & Q(cedula=f.cleaned_data['cedula'])
                    if f.cleaned_data['pasaporte'] and not f.cleaned_data['pasaporte'] == '':
                        filter = filter | Q(pasaporte=f.cleaned_data['pasaporte'])
                    if not Persona.objects.filter(filter).exists():
                        persona = Persona(nombres=f.cleaned_data['nombres'],
                                               apellido1=f.cleaned_data['apellido1'],
                                               apellido2=f.cleaned_data['apellido2'],
                                               cedula=f.cleaned_data['cedula'],
                                               pasaporte=f.cleaned_data['pasaporte'],
                                               nacimiento=f.cleaned_data['nacimiento'],
                                               sexo=f.cleaned_data['sexo'],
                                               paisnacimiento=f.cleaned_data['paisnacimiento'],
                                               provincianacimiento=f.cleaned_data['provincianacimiento'],
                                               cantonnacimiento=f.cleaned_data['cantonnacimiento'],
                                               parroquianacimiento=f.cleaned_data['parroquianacimiento'],
                                               nacionalidad=f.cleaned_data['nacionalidad'],
                                               pais=f.cleaned_data['pais'],
                                               provincia=f.cleaned_data['provincia'],
                                               canton=f.cleaned_data['canton'],
                                               parroquia=f.cleaned_data['parroquia'],
                                               sector=f.cleaned_data['sector'],
                                               direccion=f.cleaned_data['direccion'],
                                               direccion2=f.cleaned_data['direccion2'],
                                               num_direccion=f.cleaned_data['num_direccion'],
                                               telefono=f.cleaned_data['telefono'],
                                               telefono_conv=f.cleaned_data['telefono_conv'],
                                               sangre=f.cleaned_data['sangre'],
                                               email=f.cleaned_data['email'])
                        persona.save(request)
                    if Persona.objects.filter(filter).exists():
                        cedula = f.cleaned_data['cedula']
                        pasaporte = f.cleaned_data['pasaporte']
                        if cedula:
                            persona = Persona.objects.filter(cedula=cedula, status=True).first()
                        elif pasaporte:
                            persona = Persona.objects.filter(pasaporte=pasaporte, status=True).first()
                    if RepresentantesEmpresa.objects.filter(persona=persona, empresa=empresa, status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Esta persona ya se encuentra registrada como representate."})
                    administrativo = RepresentantesEmpresa(persona=persona, cargo=f.cleaned_data['cargo'], empresa=empresa)
                    administrativo.save(request)

                    if f.cleaned_data['email']:
                        send_html_mail("Asignacion como representante", "emails/registrorepresentanteempresa.html",
                                       {'sistema': u'Unemi Empleo', 'fecha': datetime.now(), 'administrativo': administrativo, 'tit': 'Unemi - Empleo'},
                                       [f.cleaned_data['email']],
                                       [], cuenta=CUENTAS_CORREOS[17][1])

                    log(u'Adiciono representante de empresa: %s - %s' % (persona, empresa.nombrecorto), request, "add")
                    return JsonResponse({"result": "ok", "id": administrativo.id})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': "bad", "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        elif action == 'edit':
            try:
                f = RepresentanteForm(request.POST)
                f.fields['cedula'].required = False
                if f.is_valid():
                    representante = RepresentantesEmpresa.objects.get(pk=request.POST['id'])
                    personaadmin = representante.persona
                    representante.cargo = f.cleaned_data['cargo']
                    personaadmin.nombres = f.cleaned_data['nombres']
                    personaadmin.apellido1 = f.cleaned_data['apellido1']
                    personaadmin.apellido2 = f.cleaned_data['apellido2']
                    personaadmin.nacimiento = f.cleaned_data['nacimiento']
                    personaadmin.sexo = f.cleaned_data['sexo']
                    personaadmin.paisnacimiento = f.cleaned_data['paisnacimiento']
                    personaadmin.provincianacimiento = f.cleaned_data['provincianacimiento']
                    personaadmin.cantonnacimiento = f.cleaned_data['cantonnacimiento']
                    personaadmin.parroquianacimiento = f.cleaned_data['parroquianacimiento']
                    personaadmin.nacionalidad = f.cleaned_data['nacionalidad']
                    personaadmin.pais = f.cleaned_data['pais']
                    personaadmin.provincia = f.cleaned_data['provincia']
                    personaadmin.canton = f.cleaned_data['canton']
                    personaadmin.parroquia = f.cleaned_data['parroquia']
                    personaadmin.sector = f.cleaned_data['sector']
                    personaadmin.direccion = f.cleaned_data['direccion']
                    personaadmin.direccion2 = f.cleaned_data['direccion2']
                    personaadmin.num_direccion = f.cleaned_data['num_direccion']
                    personaadmin.telefono = f.cleaned_data['telefono']
                    personaadmin.telefono_conv = f.cleaned_data['telefono_conv']
                    personaadmin.email = f.cleaned_data['email']
                    personaadmin.sangre = f.cleaned_data['sangre']
                    personaadmin.save(request)
                    representante.save(request)
                    log(u'Modifico representante de empresa: %s' % representante, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'error', "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        elif action == 'delete':
            try:
                representante = RepresentantesEmpresa.objects.get(pk=int(encrypt(request.POST['id'])))
                if representante.ofertalaboralempresa_set.filter(status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar este representante."})
                representante.status = False
                representante.save(request)
                log(u'Eliminó representante de empresa: %s - %s' % (representante, empresa.nombrecorto), request, "del")
                return JsonResponse({"error": False})
            except Exception as e:
                print(e)
                pass

        return JsonResponse({"result": False, "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            if action == 'add':
                try:
                    # puede_realizar_accion(request, 'empresa.puede_modificar_representantes')
                    data['title'] = u'Adicionar representante de la Empresa'
                    form = RepresentanteForm()
                    form.adicionar()
                    data['email_domain'] = EMAIL_DOMAIN
                    data['form'] = form

                    return render(request, "empresa/addrepresentante.html", data)
                except Exception as ex:
                    pass
            elif action == 'edit':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Editar representante de empresa'
                    data['representante'] = representante = RepresentantesEmpresa.objects.get(pk=int(encrypt(request.GET['id'])))
                    personaadmin = representante.persona
                    form = RepresentanteForm(initial={'nombres': personaadmin.nombres,
                                                        'apellido1': personaadmin.apellido1,
                                                        'apellido2': personaadmin.apellido2,
                                                        'cedula': personaadmin.cedula,
                                                        'sexo': personaadmin.sexo,
                                                        'pasaporte': personaadmin.pasaporte,
                                                        'nacimiento': personaadmin.nacimiento,
                                                        'paisnacimiento': personaadmin.paisnacimiento,
                                                        'provincianacimiento': personaadmin.provincianacimiento,
                                                        'cantonnacimiento': personaadmin.cantonnacimiento,
                                                        'parroquianacimiento': personaadmin.parroquianacimiento,
                                                        'nacionalidad': personaadmin.nacionalidad,
                                                        'pais': personaadmin.pais,
                                                        'provincia': personaadmin.provincia,
                                                        'canton': personaadmin.canton,
                                                        'parroquia': personaadmin.parroquia,
                                                        'sector': personaadmin.sector,
                                                        'direccion': personaadmin.direccion,
                                                        'direccion2': personaadmin.direccion2,
                                                        'num_direccion': personaadmin.num_direccion,
                                                        'telefono': personaadmin.telefono,
                                                        'telefono_conv': personaadmin.telefono_conv,
                                                        'email': personaadmin.email,
                                                        'emailinst': personaadmin.emailinst,
                                                        'sangre': personaadmin.sangre,
                                                      'cargo': representante.cargo})
                    form.editar(personaadmin)
                    data['form'] = form
                    data['email_domain'] = EMAIL_DOMAIN
                    return render(request, "empresa/editrepresentante.html", data)
                except Exception as ex:
                    pass
            elif action == 'searchpersona':
                try:
                    representante = Persona.objects.filter(Q(status=True), Q(cedula=request.GET['dato']) | Q(pasaporte=request.GET['dato']))
                    if representante.exists():
                        representante = representante.first()
                        if RepresentantesEmpresa.objects.filter(persona=representante, empresa=empresa, status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Esta persona ya se encuentra registrada como representante."})
                        objeto = {'nombres': representante.nombres, 'apellido1': representante.apellido1,
                                  'apellido2': representante.apellido2,
                                  'pasaporte': representante.pasaporte, 'nacimiento': representante.nacimiento,
                                  'sector': representante.sector, 'direccion': representante.direccion,
                                  'direccion2': representante.direccion2,
                                  'num_direccion': representante.num_direccion, 'referencia': representante.referencia,
                                  'telefono': representante.telefono,
                                  'telefono_conv': representante.telefono_conv, 'email': representante.email}
                        if representante.sexo:
                            objeto['sexo'] = representante.sexo_id
                        if representante.pais:
                            objeto['pais'] = representante.pais_id
                            objeto['nacionalidad'] = representante.pais.nacionalidad,
                        if representante.provincia:
                            objeto['provincia'] = {'id': representante.provincia_id, 'text': representante.provincia.nombre}
                        if representante.canton:
                            objeto['canton'] = {'id': representante.canton_id, 'text': representante.canton.nombre}
                        if representante.parroquia:
                            objeto['parroquia'] = {'id': representante.parroquia_id, 'text': representante.parroquia.nombre}
                        if representante.paisnacimiento:
                            objeto['paisnacimiento'] = representante.paisnacimiento_id
                        if representante.provincianacimiento:
                            objeto['provincianacimiento'] = {'id': representante.provincianacimiento_id, 'text': representante.provincianacimiento.nombre}
                        if representante.cantonnacimiento:
                            objeto['cantonnacimiento'] = {'id': representante.cantonnacimiento_id, 'text': representante.cantonnacimiento.nombre}
                        if representante.parroquianacimiento:
                            objeto['parroquianacimiento'] = {'id': representante.parroquianacimiento_id, 'text': representante.parroquianacimiento.nombre}
                        if representante.sangre:
                            objeto['sangre'] = representante.sangre_id

                        return JsonResponse({"result": 'ok', 'lista': objeto})
                    return JsonResponse({"result": 'badexist'})
                except Exception as e:
                    print(e)
                    pass
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Representantes de la Empresa'
                representantes = RepresentantesEmpresa.objects.filter(status=True, empresa=empresa)
                search, filtro, url_vars = request.GET.get('search', ''), (Q(status=True)), ''
                if search:
                    data['search'] = search = request.GET['search'].strip()
                    ss = search.split(' ')
                    url_vars += "&search={}".format(search)
                    if len(ss) == 1:
                        representantes = representantes.filter(Q(persona__nombres__icontains=search) |
                                                                 Q(persona__apellido1__icontains=search) |
                                                                 Q(persona__apellido2__icontains=search) |
                                                                 Q(persona__cedula__icontains=search) |
                                                                 Q(persona__pasaporte__icontains=search)).distinct()
                    else:
                        representantes = representantes.filter(
                            Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1])).distinct()
                paging = MiPaginador(representantes, 20)
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
                data['listado'] = page.object_list
                data["url_vars"] = url_vars
                data['list_count'] = len(representantes)
                return render(request, "empresa/view.html", data)
            except Exception as ex:
                pass
