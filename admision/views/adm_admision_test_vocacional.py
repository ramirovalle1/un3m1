# -*- coding: UTF-8 -*-
import sys
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from bd.models import LogQuery
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery, MiPaginador
from admision.forms import TestVocacionalForm, TestVocacionalOpcionForm, TestVocacionalPreguntaForm, \
    TestVocacionalAlternativaForm
from admision.models import TestVocacional
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}

    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'saveTestVocacional':
            try:
                from admision.models import TestVocacional
                id = int(encrypt((request.POST.get('id', encrypt('0')))))
                form = TestVocacionalForm(request.POST)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                if id != 0:
                    eTestVocacional = TestVocacional.objects.get(pk=id)
                    if TestVocacional.objects.values("id").filter(nombre=request.POST['nombre']).exclude(pk=eTestVocacional.pk).exists():
                        raise NameError(u"Nombre del test vocacional ya se encuentra registrado")
                    eTestVocacional.nombre = form.cleaned_data['nombre']
                    eTestVocacional.descripcion = form.cleaned_data['descripcion']
                    eTestVocacional.activo = form.cleaned_data['activo']
                    eTestVocacional.save(request)
                    log(u'Edito test vocacional de nivelación y admisión: %s' % eTestVocacional, request, 'edit')
                else:
                    if TestVocacional.objects.values("id").filter(nombre=request.POST['nombre']).exists():
                        raise NameError(u"Nombre del test vocacional ya se encuentra registrado")
                    eTestVocacional = TestVocacional(nombre=form.cleaned_data['nombre'],
                                                     descripcion=form.cleaned_data['descripcion'],
                                                     activo=form.cleaned_data['activo'])
                    eTestVocacional.save(request)
                    log(u'Adiciono test vocacional de nivelación y admisión: %s' % eTestVocacional, request, 'add')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'mensaje': str(ex)})

        elif action == 'deleteTestVocacional':
            try:
                from admision.models import TestVocacional
                id = int(encrypt((request.POST.get('id', encrypt('0')))))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro a eliminar")
                if not TestVocacional.objects.values("id").filter(pk=id):
                    raise NameError(u"No se encontro el registro a eliminar")
                eTestVocacional = deleteTestVocacional = TestVocacional.objects.get(pk=id)
                if not eTestVocacional.puede_eliminar():
                    raise NameError(u"No puede eliminar registro de test vocacional porque existe datos conectados")
                eTestVocacional.delete()
                log(u'Elimino test vocacional de nivelación y admisión: %s' % deleteTestVocacional, request, 'del')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'mensaje': str(ex)})

        elif action == 'saveTestVocacionalOpcion':
            try:
                from admision.models import TestVocacional, TestVocacionalOpcion
                id = int(encrypt((request.POST.get('id', encrypt('0')))))
                ido = int(encrypt((request.POST.get('ido', encrypt('0')))))
                form = TestVocacionalOpcionForm(request.POST)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                eTestVocacional = TestVocacional.objects.get(pk=id)
                if ido != 0:
                    eTestVocacionalOpcion = TestVocacionalOpcion.objects.get(pk=ido)
                    eTestVocacionalOpcion.literal = form.cleaned_data['literal']
                    eTestVocacionalOpcion.descripcion = form.cleaned_data['descripcion']
                    eTestVocacionalOpcion.save(request)
                    log(u'Edito opción del test vocacional de nivelación y admisión: %s' % eTestVocacionalOpcion, request, 'edit')
                else:
                    eTestVocacionalOpcion = TestVocacionalOpcion(test=eTestVocacional,
                                                                 literal=form.cleaned_data['literal'],
                                                                 descripcion=form.cleaned_data['descripcion'])
                    eTestVocacionalOpcion.save(request)
                    log(u'Adiciono opción del test vocacional de nivelación y admisión: %s' % eTestVocacionalOpcion, request, 'add')
                return JsonResponse({"result": True, 'id': encrypt(eTestVocacional.pk)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'mensaje': str(ex)})

        elif action == 'deleteTestVocacionalOpcion':
            try:
                from admision.models import TestVocacional, TestVocacionalOpcion
                id = int(encrypt((request.POST.get('id', encrypt('0')))))
                ido = int(encrypt((request.POST.get('ido', encrypt('0')))))
                if ido == 0:
                    raise NameError(u"No se encontro el parametro de registro a eliminar")
                if not TestVocacionalOpcion.objects.values("id").filter(pk=id):
                    raise NameError(u"No se encontro el registro a eliminar")
                eTestVocacional = TestVocacional.objects.get(pk=id)
                eTestVocacionalOpcion = deleteTestVocacionalOpcion = TestVocacionalOpcion.objects.get(pk=ido)
                if not eTestVocacionalOpcion.puede_eliminar():
                    raise NameError(u"No puede eliminar registro de test vocacional porque existe datos conectados")
                eTestVocacionalOpcion.delete()
                log(u'Elimino opción del test vocacional de nivelación y admisión: %s' % deleteTestVocacionalOpcion, request, 'del')
                return JsonResponse({"result": True, "id": encrypt(eTestVocacional.pk)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'mensaje': str(ex)})

        elif action == 'saveTestVocacionalPregunta':
            try:
                from admision.models import TestVocacional, TestVocacionalPregunta
                id = int(encrypt((request.POST.get('id', encrypt('0')))))
                idp = int(encrypt((request.POST.get('idp', encrypt('0')))))
                form = TestVocacionalPreguntaForm(request.POST)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                eTestVocacional = TestVocacional.objects.get(pk=id)
                if idp != 0:
                    eTestVocacionalPregunta = TestVocacionalPregunta.objects.get(pk=idp)
                    eTestVocacionalPregunta.orden = form.cleaned_data['orden']
                    eTestVocacionalPregunta.activo = form.cleaned_data['activo']
                    eTestVocacionalPregunta.validar = form.cleaned_data['validar']
                    eTestVocacionalPregunta.descripcion = form.cleaned_data['descripcion']
                    eTestVocacionalPregunta.save(request)
                    log(u'Edito pregunta del test vocacional de nivelación y admisión: %s' % eTestVocacionalPregunta, request, 'edit')
                else:
                    eTestVocacionalPregunta = TestVocacionalPregunta(test=eTestVocacional,
                                                                     orden=form.cleaned_data['orden'],
                                                                     activo=form.cleaned_data['activo'],
                                                                     validar=form.cleaned_data['validar'],
                                                                     descripcion=form.cleaned_data['descripcion'])
                    eTestVocacionalPregunta.save(request)
                    log(u'Adiciono pregunta del test vocacional de nivelación y admisión: %s' % eTestVocacionalPregunta, request, 'add')
                return JsonResponse({"result": True, 'id': encrypt(eTestVocacional.pk)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'mensaje': str(ex)})

        elif action == 'deleteTestVocacionalPregunta':
            try:
                from admision.models import TestVocacional, TestVocacionalPregunta
                id = int(encrypt((request.POST.get('id', encrypt('0')))))
                idp = int(encrypt((request.POST.get('idp', encrypt('0')))))
                if idp == 0:
                    raise NameError(u"No se encontro el parametro de registro a eliminar")
                if not TestVocacionalPregunta.objects.values("id").filter(pk=idp):
                    raise NameError(u"No se encontro el registro a eliminar")
                eTestVocacional = TestVocacional.objects.get(pk=id)
                eTestVocacionalPregunta = deleteTestVocacionalPregunta = TestVocacionalPregunta.objects.get(pk=idp)
                if not eTestVocacionalPregunta.puede_eliminar():
                    raise NameError(u"No puede eliminar registro de test vocacional porque existe datos conectados")
                eTestVocacionalPregunta.delete()
                log(u'Elimino pregunta del test vocacional de nivelación y admisión: %s' % deleteTestVocacionalPregunta, request, 'del')
                return JsonResponse({"result": True, "id": encrypt(eTestVocacional.pk)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'mensaje': str(ex)})

        elif action == 'saveTestVocacionalAlternativa':
            try:
                from admision.models import TestVocacionalPregunta, TestVocacionalAlternativa
                id = int(encrypt((request.POST.get('id', encrypt('0')))))
                ida = int(encrypt((request.POST.get('ida', encrypt('0')))))
                eTestVocacionalPregunta = TestVocacionalPregunta.objects.get(pk=id)
                form = TestVocacionalAlternativaForm(request.POST)
                form.set_opcion(eTestVocacionalPregunta.test_id)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                if ida != 0:
                    eTestVocacionalAlternativa = TestVocacionalAlternativa.objects.get(pk=ida)
                    eTestVocacionalAlternativa.orden = form.cleaned_data['orden']
                    eTestVocacionalAlternativa.opcion = form.cleaned_data['opcion']
                    eTestVocacionalAlternativa.valor = form.cleaned_data['valor']
                    eTestVocacionalAlternativa.save(request)
                    log(u'Edito alternativa de la pregunta del test vocacional de nivelación y admisión: %s' % eTestVocacionalAlternativa, request, 'edit')
                else:
                    eTestVocacionalAlternativa = TestVocacionalAlternativa(pregunta=eTestVocacionalPregunta,
                                                                           orden=form.cleaned_data['orden'],
                                                                           opcion=form.cleaned_data['opcion'],
                                                                           valor=form.cleaned_data['valor'])
                    eTestVocacionalAlternativa.save(request)
                    log(u'Adiciono  alternativa de la pregunta del test vocacional de nivelación y admisión: %s' % eTestVocacionalAlternativa, request, 'add')
                return JsonResponse({"result": True, 'id': encrypt(eTestVocacionalPregunta.pk)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'mensaje': str(ex)})

        elif action == 'deleteTestVocacionalAlternativa':
            try:
                from admision.models import TestVocacionalPregunta, TestVocacionalAlternativa
                id = int(encrypt((request.POST.get('id', encrypt('0')))))
                ida = int(encrypt((request.POST.get('ida', encrypt('0')))))
                if ida == 0:
                    raise NameError(u"No se encontro el parametro de registro a eliminar")
                if not TestVocacionalAlternativa.objects.values("id").filter(pk=ida):
                    raise NameError(u"No se encontro el registro a eliminar")
                eTestVocacionalPregunta = TestVocacionalPregunta.objects.get(pk=id)
                eTestVocacionalAlternativa = deleteTestVocacionalAlternativa = TestVocacionalAlternativa.objects.get(pk=ida)
                eTestVocacionalAlternativa.delete()
                log(u'Elimino alternativa de pregunta del test vocacional de nivelación y admisión: %s' % deleteTestVocacionalAlternativa, request, 'del')
                return JsonResponse({"result": True, "id": encrypt(eTestVocacionalPregunta.pk)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'mensaje': str(ex)})

        return JsonResponse({"result": False, "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'loadFormTestVocacional':
                try:
                    from admision.models import TestVocacional
                    id = int(encrypt((request.GET.get('id', encrypt('0')))))
                    eTestVocacional = None
                    if id != 0:
                        eTestVocacional = TestVocacional.objects.get(pk=id)
                    form = TestVocacionalForm()
                    if eTestVocacional:
                        form.initial = model_to_dict(eTestVocacional)
                    data['form'] = form
                    data['idForm'] = 'frmTestVocacional'
                    data['action'] = 'saveTestVocacional'
                    data['id'] = id
                    template = get_template("nivelacion_admision/adm_test_vocacional/form.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadFormTestVocacionalOpcion':
                try:
                    from admision.models import TestVocacional, TestVocacionalOpcion
                    id = int(encrypt((request.GET.get('id', encrypt('0')))))
                    if id == 0:
                        raise NameError(u"No se encontro parametro de test vocacional")
                    ido = int(encrypt((request.GET.get('ido', encrypt('0')))))
                    eTestVocacionalOpcion = None
                    if ido != 0:
                        eTestVocacionalOpcion = TestVocacionalOpcion.objects.get(pk=ido)
                    eTestVocacional = TestVocacional.objects.get(pk=id)
                    data['eTestVocacional'] = eTestVocacional
                    form = TestVocacionalOpcionForm()
                    if eTestVocacionalOpcion:
                        form.initial = model_to_dict(eTestVocacionalOpcion)
                        data['ido'] = eTestVocacionalOpcion.id
                    data['form'] = form
                    data['idForm'] = 'frmTestVocacionalOpcion'
                    data['action'] = 'saveTestVocacionalOpcion'
                    template = get_template("nivelacion_admision/adm_test_vocacional/opcion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadTestVocacionalPregunta':
                try:
                    from admision.models import TestVocacional, TestVocacionalPregunta
                    id = int(encrypt((request.GET.get('id', encrypt('0')))))
                    if id == 0:
                        raise NameError(u"No se encontro parametro de test vocacional")
                    eTestVocacional = TestVocacional.objects.get(pk=id)
                    eTestVocacionalPreguntas = TestVocacionalPregunta.objects.filter(test=eTestVocacional)
                    data['title'] = f'Preguntas del {eTestVocacional.nombre}'
                    data['subtitle'] = 'Administración de preguntas del test vocacionales'
                    data['eTestVocacionalPreguntas'] = eTestVocacionalPreguntas
                    data['eTestVocacional'] = eTestVocacional
                    return render(request, "nivelacion_admision/adm_test_vocacional/pregunta.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'loadFormTestVocacionalPregunta':
                try:
                    from admision.models import TestVocacional, TestVocacionalPregunta
                    id = int(encrypt((request.GET.get('id', encrypt('0')))))
                    if id == 0:
                        raise NameError(u"No se encontro parametro de test vocacional")
                    idp = int(encrypt((request.GET.get('idp', encrypt('0')))))
                    eTestVocacionalPregunta = None
                    if idp != 0:
                        eTestVocacionalPregunta = TestVocacionalPregunta.objects.get(pk=idp)
                    eTestVocacional = TestVocacional.objects.get(pk=id)
                    data['eTestVocacional'] = eTestVocacional
                    form = TestVocacionalPreguntaForm()
                    if eTestVocacionalPregunta:
                        form.initial = model_to_dict(eTestVocacionalPregunta)
                        data['idp'] = eTestVocacionalPregunta.id
                    data['form'] = form
                    data['idForm'] = 'frmTestVocacionalPregunta'
                    data['action'] = 'saveTestVocacionalPregunta'
                    template = get_template("nivelacion_admision/adm_test_vocacional/formPregunta.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadFormTestVocacionalAlternativa':
                try:
                    from admision.models import TestVocacionalPregunta, TestVocacionalAlternativa
                    id = int(encrypt((request.GET.get('id', encrypt('0')))))
                    if id == 0:
                        raise NameError(u"No se encontro parametro de pregunta del test vocacional")
                    ida = int(encrypt((request.GET.get('ida', encrypt('0')))))
                    eTestVocacionalAlternativa = None
                    if ida != 0:
                        eTestVocacionalAlternativa = TestVocacionalAlternativa.objects.get(pk=ida)
                    eTestVocacionalPregunta = TestVocacionalPregunta.objects.get(pk=id)
                    data['eTestVocacionalPregunta'] = eTestVocacionalPregunta
                    form = TestVocacionalAlternativaForm()
                    form.set_opcion(eTestVocacionalPregunta.test_id)
                    if eTestVocacionalAlternativa:
                        form.initial = model_to_dict(eTestVocacionalAlternativa)
                        data['ida'] = eTestVocacionalAlternativa.id
                    data['form'] = form
                    data['idForm'] = 'frmTestVocacionalAlternativa'
                    data['action'] = 'saveTestVocacionalAlternativa'
                    template = get_template("nivelacion_admision/adm_test_vocacional/formAlternativa.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            return HttpResponseRedirect(request.path)
        else:
            try:
                from admision.models import TestVocacional
                data['title'] = 'Test Vocacional'
                data['subtitle'] = 'Administración de test vocacionales'
                filtros, s, url_vars = Q(status=True), request.GET.get('s', ''), ''
                if s:
                    if s.isdigit():
                        filtros = filtros & (Q(id=s))
                    else:
                        filtros = filtros & (Q(nombre__icontains=s))
                    data['s'] = f"{s}"
                    url_vars += f"&s={s}"
                eTestVocacionales = TestVocacional.objects.filter(filtros).order_by('-id')
                paging = MiPaginador(eTestVocacionales, 25)
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
                data['eTestVocacionales'] = page.object_list
                data['url_vars'] = url_vars
                return render(request, "nivelacion_admision/adm_test_vocacional/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f"/nivelacion_admision?info={ex.__str__()}")
