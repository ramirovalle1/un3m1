# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from datetime import datetime, timedelta

from decorators import secure_module, last_access
from sagest.forms import TituloForm, AreaConocimientoTitulacionForm, SubAreaConocimientoTitulacionForm, \
    SubAreaEspecificaConocimientoTitulacionForm, VersionMatizCineForm, ObservacionForm
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log
from sga.models import Titulo, NivelTitulacion, GradoTitulacion, AreaConocimientoTitulacion, \
    SubAreaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacion, CamposTitulosPostulacion, VersionMatizCine, Notificacion, Persona
from sga.templatetags.sga_extras import encrypt
from postulate.models import TituloSugerido

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@last_access
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = TituloForm(request.POST)
                if f.is_valid():
                    grado = f.cleaned_data['grado']
                    filtro = Q(nombre=f.cleaned_data['nombre'].upper(), nivel=f.cleaned_data['nivel'], status=True)
                    if not grado:
                        filtro = filtro & Q(grado=grado)
                    if Titulo.objects.filter(filtro).exists():
                        return JsonResponse({"result": True, "mensaje": u"El registro ya existe."})
                    titulo = Titulo(nombre=f.cleaned_data['nombre'],
                                    abreviatura=f.cleaned_data['abreviatura'],
                                    nivel=f.cleaned_data['nivel'],
                                    grado=f.cleaned_data['grado'],
                                    areaconocimiento=f.cleaned_data['areaconocimiento'],
                                    subareaconocimiento=f.cleaned_data['subareaconocimiento'],
                                    subareaespecificaconocimiento=f.cleaned_data['subareaespecificaconocimiento'])
                    titulo.save(request)

                    # actualiza tabla CamposTitulosPostulacion
                    campotitulo = None
                    if CamposTitulosPostulacion.objects.filter(status=True, titulo=titulo).exists():
                        campotitulo = CamposTitulosPostulacion.objects.filter(status=True, titulo=titulo).first()
                    else:
                        campotitulo = CamposTitulosPostulacion(titulo=titulo)
                        campotitulo.save(request)
                    if f.cleaned_data['areaconocimiento']:
                        if not campotitulo.campoamplio.filter(id=f.cleaned_data['areaconocimiento'].id):
                            campotitulo.campoamplio.add(f.cleaned_data['areaconocimiento'])
                    if f.cleaned_data['subareaconocimiento']:
                        if not campotitulo.campoespecifico.filter(id=f.cleaned_data['subareaconocimiento'].id):
                            campotitulo.campoespecifico.add(f.cleaned_data['subareaconocimiento'])
                    if f.cleaned_data['subareaespecificaconocimiento']:
                        if not campotitulo.campodetallado.filter(id=f.cleaned_data['subareaespecificaconocimiento'].id):
                            campotitulo.campodetallado.add(f.cleaned_data['subareaespecificaconocimiento'])
                    campotitulo.save()

                    log(u'Adiciono nuevo titulo: %s' % titulo, request, "add")
                    return JsonResponse({"result": False, 'mensaje': 'Registro Exitoso'})
                else:
                    # print([{k: v[0]} for k, v in f.errors.items()])
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                f = TituloForm(request.POST)
                if f.is_valid():
                    titulo = Titulo.objects.get(pk=encrypt(request.POST['id']))
                    if Titulo.objects.filter(nombre=f.cleaned_data['nombre'].upper(), nivel=f.cleaned_data['nivel'],
                                             status=True).exclude(id=titulo.id).exists():
                        return JsonResponse({"result": True, "mensaje": u"El registro ya existe."})
                    if request.user.has_perm('sga.puede_titulo_tthh'):
                        titulo.nombre = f.cleaned_data['nombre']
                        titulo.abreviatura = f.cleaned_data['abreviatura']
                        titulo.nivel = f.cleaned_data['nivel']
                        titulo.grado = f.cleaned_data['grado']
                    # else:
                    titulo.areaconocimiento = f.cleaned_data['areaconocimiento']
                    titulo.subareaconocimiento = f.cleaned_data['subareaconocimiento']
                    titulo.subareaespecificaconocimiento = f.cleaned_data['subareaespecificaconocimiento']
                    titulo.save(request)

                    # actualiza tabla CamposTitulosPostulacion
                    campotitulo = None
                    if CamposTitulosPostulacion.objects.filter(status=True, titulo=titulo).exists():
                        campotitulo = CamposTitulosPostulacion.objects.filter(status=True, titulo=titulo).first()
                    else:
                        campotitulo = CamposTitulosPostulacion(titulo=titulo)
                        campotitulo.save(request)
                    if f.cleaned_data['areaconocimiento']:
                        if not campotitulo.campoamplio.filter(id=f.cleaned_data['areaconocimiento'].id):
                            campotitulo.campoamplio.add(f.cleaned_data['areaconocimiento'])
                    if f.cleaned_data['subareaconocimiento']:
                        if not campotitulo.campoespecifico.filter(id=f.cleaned_data['subareaconocimiento'].id):
                            campotitulo.campoespecifico.add(f.cleaned_data['subareaconocimiento'])
                    if f.cleaned_data['subareaespecificaconocimiento']:
                        if not campotitulo.campodetallado.filter(id=f.cleaned_data['subareaespecificaconocimiento'].id):
                            campotitulo.campodetallado.add(f.cleaned_data['subareaespecificaconocimiento'])
                    campotitulo.save()

                    log(u'Modifico titulo: %s' % titulo, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'delete':
            try:
                titulo = Titulo.objects.get(pk=encrypt(request.POST['id']))
                if titulo.en_uso():
                    # return JsonResponse({"result": "bad", "mensaje": u"El registro esta en uso."})
                    res_json = {'error': True, "message": u"El registro esta en uso."}
                    return JsonResponse(res_json, safe=False)
                log(u'Elimino titulo: %s' % titulo, request, "del")
                titulo.status = False
                titulo.save()
                # return JsonResponse({"result": "ok"})
                res_json = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
                # return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
            return JsonResponse(res_json, safe=False)

        elif action == 'addamplio':
            try:
                form = AreaConocimientoTitulacionForm(request.POST)
                if form.is_valid():
                    if not AreaConocimientoTitulacion.objects.filter(status=True,
                                                                     nombre=form.cleaned_data['nombre']).exists():
                        areaconocimientotitulacion = AreaConocimientoTitulacion(nombre=form.cleaned_data['nombre'],
                                                                                codigo=form.cleaned_data['codigo'],
                                                                                codigocaces=form.cleaned_data[
                                                                                    'codigocaces'],
                                                                                tipo=form.cleaned_data['tipo'])
                        areaconocimientotitulacion.save(request)
                        log(u'Registro area conocimiento: %s' % areaconocimientotitulacion, request, "add")
                        return JsonResponse({"result": False, 'mensaje': 'Registro Exitoso'})
                    else:
                        return JsonResponse({"result": True, "mensaje": "Registro Repetido."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Error al guardar los datos."})
        elif action == 'addversion':
            try:
                form = VersionMatizCineForm(request.POST)
                if form.is_valid():
                    if not VersionMatizCine.objects.filter(status=True, nombre=form.cleaned_data['nombre']).exists():
                        matriz = VersionMatizCine(nombre=form.cleaned_data['nombre'],
                                                                                anio=form.cleaned_data['anio'],
                                                                                vigente=form.cleaned_data[
                                                                                    'vigente'],)
                        matriz.save(request)
                        log(u'Registro matriz: %s' % matriz, request, "add")
                        return JsonResponse({"result": False, 'mensaje': 'Registro Exitoso'})
                    else:
                        return JsonResponse({"result": True, "mensaje": "Registro Repetido."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Error al guardar los datos."})

        elif action == 'addespecifico':
            try:
                form = SubAreaConocimientoTitulacionForm(request.POST)
                if form.is_valid():
                    if not SubAreaConocimientoTitulacion.objects.filter(status=True, areaconocimiento=form.cleaned_data[
                        'areaconocimiento'], nombre=form.cleaned_data['nombre']).exists():
                        subareaconocimientotitulacion = SubAreaConocimientoTitulacion(
                            areaconocimiento=form.cleaned_data['areaconocimiento'],
                            nombre=form.cleaned_data['nombre'],
                            codigo=form.cleaned_data['codigo'],
                            codigocaces=form.cleaned_data['codigocaces'], tipo=form.cleaned_data['tipo'],
                            vigente=form.cleaned_data['vigente'])
                        subareaconocimientotitulacion.save(request)
                        log(u'Registro sub area conocimiento especifico: %s' % subareaconocimientotitulacion, request,
                            "add")
                        return JsonResponse({"result": False, 'mensaje': 'Registro Exitoso'})
                    else:
                        return JsonResponse({"result": True, "mensaje": "Registro Repetido."})
                else:
                    raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Error al guardar los datos."})

        elif action == 'adddetallado':
            try:
                form = SubAreaEspecificaConocimientoTitulacionForm(request.POST)
                if form.is_valid():
                    if not SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True,
                                                                                  areaconocimiento=form.cleaned_data[
                                                                                      'areaconocimiento'],
                                                                                  nombre=form.cleaned_data[
                                                                                      'nombre']).exists():
                        subareaespecificaconocimientotitulacion = SubAreaEspecificaConocimientoTitulacion(
                            areaconocimiento=form.cleaned_data['areaconocimiento'],
                            nombre=form.cleaned_data['nombre'],
                            codigo=form.cleaned_data['codigo'],
                            codigocaces=form.cleaned_data['codigocaces'],
                            tipo=form.cleaned_data['tipo'],
                            vigente=form.cleaned_data['vigente'])
                        subareaespecificaconocimientotitulacion.save(request)
                        log(u'Registro sub area especifica conocimiento detallado: %s' % subareaespecificaconocimientotitulacion,
                            request, "add")
                        return JsonResponse({"result": False, 'mensaje': 'Registro Exitoso'})
                    else:
                        return JsonResponse({"result": True, "mensaje": "Registro Repetido."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Error al guardar los datos."})

        elif action == 'editamplio':
            try:
                form = AreaConocimientoTitulacionForm(request.POST)
                if form.is_valid():
                    if not AreaConocimientoTitulacion.objects.filter(status=True,
                                                                     nombre=form.cleaned_data['nombre']).exclude(
                        pk=encrypt(request.POST['id'])).exists():
                        registro = AreaConocimientoTitulacion.objects.get(pk=encrypt(request.POST['id']), status=True)
                        registro.nombre = form.cleaned_data['nombre']
                        registro.codigo = form.cleaned_data['codigo']
                        registro.codigocaces = form.cleaned_data['codigocaces']
                        if form.cleaned_data['tipo']:
                            registro.tipo = form.cleaned_data['tipo']
                        registro.save(request)
                        log(u'Registro modificado Area conocimiento: %s' % registro, request, "edit")
                        return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                    else:
                        return JsonResponse({"result": True, "mensaje": "Registro Repetido."})
                else:
                    raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Error al guardar los datos."})

        elif action == 'delamplio':
            try:
                config = AreaConocimientoTitulacion.objects.get(pk=encrypt(request.POST['id']), status=True)
                config.status = False
                config.save(request)
                log(u'Elimino area conocimiento amplio: %s' % config, request, "del")
                res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'editespecifico':
            try:
                form = SubAreaConocimientoTitulacionForm(request.POST)
                if form.is_valid():
                    if not SubAreaConocimientoTitulacion.objects.filter(status=True, areaconocimiento=form.cleaned_data[
                        'areaconocimiento'], nombre=form.cleaned_data['nombre']).exclude(
                        pk=encrypt(request.POST['id'])).exists():
                        registro = SubAreaConocimientoTitulacion.objects.get(pk=encrypt(request.POST['id']),
                                                                             status=True)
                        registro.areaconocimiento = form.cleaned_data['areaconocimiento']
                        registro.nombre = form.cleaned_data['nombre']
                        registro.codigo = form.cleaned_data['codigo']
                        registro.codigocaces = form.cleaned_data['codigocaces']
                        registro.vigente = form.cleaned_data['vigente']
                        if form.cleaned_data['tipo']:
                            registro.tipo = form.cleaned_data['tipo']
                        registro.save(request)
                        log(u'Registro modificado Sub Area Conocimiento: %s' % registro, request, "edit")
                        return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                    else:
                        return JsonResponse({"result": True, "mensaje": "Registro Repetido."})
                else:
                    raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Error al guardar los datos."})

        elif action == 'delespecifico':
            try:
                config = SubAreaConocimientoTitulacion.objects.get(pk=encrypt(request.POST['id']), status=True)
                config.status = False
                config.save(request)
                log(u'Elimino sub area conocimiento especifico: %s' % config, request, "del")
                res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'editdetallado':
            try:
                form = SubAreaEspecificaConocimientoTitulacionForm(request.POST)
                if form.is_valid():
                    if not SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True,
                                                                                  areaconocimiento=form.cleaned_data[
                                                                                      'areaconocimiento'],
                                                                                  nombre=form.cleaned_data[
                                                                                      'nombre']).exclude(
                        pk=encrypt(request.POST['id'])).exists():
                        registro = SubAreaEspecificaConocimientoTitulacion.objects.get(pk=encrypt(request.POST['id']),
                                                                                       status=True)
                        registro.areaconocimiento = form.cleaned_data['areaconocimiento']
                        registro.nombre = form.cleaned_data['nombre']
                        registro.codigo = form.cleaned_data['codigo']
                        registro.codigocaces = form.cleaned_data['codigocaces']
                        registro.vigente = form.cleaned_data['vigente']
                        if form.cleaned_data['tipo']:
                            registro.tipo = form.cleaned_data['tipo']
                        registro.save(request)
                        log(u'Registro modificado Sub Area Especifica Conocimiento: %s' % registro, request, "edit")
                        return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                    else:
                        return JsonResponse({"result": True, "mensaje": "Registro Repetido."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Error al guardar los datos."})

        elif action == 'deldetallado':
            try:
                config = SubAreaEspecificaConocimientoTitulacion.objects.get(pk=encrypt(request.POST['id']),
                                                                             status=True)
                config.status = False
                config.save(request)
                log(u'Elimino sub area conocimiento especifico: %s' % config, request, "del")
                res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'validartitulosugerido':
            try:
                f = TituloForm(request.POST)
                if f.is_valid():
                    titulosugerido = TituloSugerido.objects.get(pk=encrypt(request.POST['id']))
                    if Titulo.objects.filter(nombre=f.cleaned_data['nombre'].upper(), nivel=f.cleaned_data['nivel'], status=True):
                        return JsonResponse({"result": True, "mensaje": u"Este título ya está registrado."})
                    else:
                        if request.user.has_perm('sga.puede_titulo_tthh'):
                            titulo = Titulo(nombre=f.cleaned_data['nombre'].upper(),
                                            abreviatura=f.cleaned_data['abreviatura'].upper(),
                                            nivel=f.cleaned_data['nivel'],
                                            grado=f.cleaned_data['grado'],
                                            areaconocimiento=f.cleaned_data['areaconocimiento'],
                                            subareaconocimiento=f.cleaned_data['subareaconocimiento'],
                                            subareaespecificaconocimiento=f.cleaned_data['subareaespecificaconocimiento'])
                            titulo.save(request)
                            # Título Sugerido
                            titulosugerido.nombre = f.cleaned_data['nombre'].upper()
                            titulosugerido.nivel = f.cleaned_data['nivel']
                            titulosugerido.estado = '2'
                            titulosugerido.save(request)
                    # actualiza tabla CamposTitulosPostulacion
                    campotitulo = None
                    if CamposTitulosPostulacion.objects.filter(status=True, titulo=titulo).exists():
                        campotitulo = CamposTitulosPostulacion.objects.filter(status=True, titulo=titulo).first()
                    else:
                        campotitulo = CamposTitulosPostulacion(titulo=titulo)
                        campotitulo.save(request)
                    if f.cleaned_data['areaconocimiento']:
                        if not campotitulo.campoamplio.filter(id=f.cleaned_data['areaconocimiento'].id):
                            campotitulo.campoamplio.add(f.cleaned_data['areaconocimiento'])
                    if f.cleaned_data['subareaconocimiento']:
                        if not campotitulo.campoespecifico.filter(id=f.cleaned_data['subareaconocimiento'].id):
                            campotitulo.campoespecifico.add(f.cleaned_data['subareaconocimiento'])
                    if f.cleaned_data['subareaespecificaconocimiento']:
                        if not campotitulo.campodetallado.filter(id=f.cleaned_data['subareaespecificaconocimiento'].id):
                            campotitulo.campodetallado.add(f.cleaned_data['subareaespecificaconocimiento'])
                    campotitulo.save()
                    log(u'Valido sugerencia de titulo: %s' % titulo, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'rechazartitulosugerido':
            try:
                f = ObservacionForm(request.POST)
                if f.is_valid():
                    titulosugerido = TituloSugerido.objects.get(id=encrypt(request.POST['id']))
                    titulosugerido.estado = '3'
                    titulosugerido.observacion = f.cleaned_data['observacion'].upper()
                    titulosugerido.save()
                    return JsonResponse({"result": False, 'mensaje': 'Edición Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar nuevo titulo'
                    data['action'] = request.GET['action']
                    data['form'] = TituloForm()
                    template = get_template("th_titulos/modal/formtitulo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'edit':
                try:
                    data['title'] = u'Modificar titulo'
                    data['action'] = request.GET['action']
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['titulo'] = titulo = Titulo.objects.get(pk=encrypt(request.GET['id']))
                    form = TituloForm(initial={'nombre': titulo.nombre,
                                               'abreviatura': titulo.abreviatura,
                                               'nivel': titulo.nivel,
                                               'grado': titulo.grado,
                                               'areaconocimiento': titulo.areaconocimiento,
                                               'subareaconocimiento': titulo.subareaconocimiento,
                                               'subareaespecificaconocimiento': titulo.subareaespecificaconocimiento})
                    # if request.user.has_perm('sga.puede_titulo_tthh'):
                    #     form.editartthh(titulo)
                    # else:
                    #     form.editarvice(titulo)
                    data['form'] = form
                    search = None
                    nivelselect = None
                    gradoselect = None
                    data['a'] = False
                    if 'n' in request.GET and 'g' in request.GET:
                        nivelselect = request.GET['n']
                        gradoselect = request.GET['g']
                    if 's' in request.GET:
                        search = request.GET['s']
                    if 'a' in request.GET:
                        data['a'] = True
                    data['search'] = search
                    data['nivelselect'] = nivelselect
                    data['gradoselect'] = gradoselect
                    # if request.user.has_perm('sga.puede_titulo_tthh'):
                    template = get_template("th_titulos/modal/formtitulo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            # if action == 'delete':
            #     try:
            #         data['title'] = u'Eliminar Ubicación'
            #         data['titulo'] = Titulo.objects.get(pk=request.GET['id'])
            #         search = None
            #         nivelselect = None
            #         gradoselect = None
            #         if 'n' in request.GET and 'g' in request.GET:
            #             nivelselect = request.GET['n']
            #             gradoselect = request.GET['g']
            #         if 's' in request.GET:
            #             search = request.GET['s']
            #         data['search'] = search
            #         data['nivelselect'] = nivelselect
            #         data['gradoselect'] = gradoselect
            #         return render(request, 'th_titulos/delete.html', data)
            #     except Exception as ex:
            #         pass

            elif action == 'bloquear':
                try:
                    if 'id' in request.GET:
                        nivel = NivelTitulacion.objects.get(pk=int(request.GET['id']))
                        if nivel.rango == 6:
                            data = {"results": "ok", "rango": 1}
                        else:
                            data = {"results": "ok", "rango": 2}
                        return JsonResponse(data)
                except Exception as ex:
                    pass
            elif action == 'viewconocimientoamplio':
                try:
                    data['title'] = u'Area Conocimiento Titulación'
                    request.session['viewactivoAreaConocimiento'] = 1
                    data['amplios'] = AreaConocimientoTitulacion.objects.filter(status=True)
                    data['especificos'] = SubAreaConocimientoTitulacion.objects.filter(status=True)
                    data['detallados'] = SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True)
                    return render(request, 'th_titulos/viewaconocimiento.html', data)
                except Exception as ex:
                    pass

            elif action == 'viewsubareaconocimientoesp':
                try:
                    data['title'] = u'Area Conocimiento Titulación'
                    request.session['viewactivoAreaConocimiento'] = 2
                    data['amplios'] = AreaConocimientoTitulacion.objects.filter(status=True)
                    data['especificos'] = SubAreaConocimientoTitulacion.objects.filter(status=True)
                    data['detallados'] = SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True)
                    return render(request, 'th_titulos/viewsaconocimientoespecifico.html', data)
                except Exception as ex:
                    pass

            elif action == 'viewversionmatrizcine':
                try:
                    data['title'] = u'Versión Matriz'
                    request.session['viewactivoAreaConocimiento'] = 4
                    data['versiones'] = VersionMatizCine.objects.filter(status=True)
                    return render(request, 'th_titulos/viewversionmatriz.html', data)
                except Exception as ex:
                    pass

            elif action == 'viewsubareaespeconocimientodetallado':
                try:
                    data['title'] = u'Area Conocimiento Titulación'
                    request.session['viewactivoAreaConocimiento'] = 3
                    data['amplios'] = AreaConocimientoTitulacion.objects.filter(status=True)
                    data['especificos'] = SubAreaConocimientoTitulacion.objects.filter(status=True)
                    data['detallados'] = SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True)
                    return render(request, 'th_titulos/viewsaeconocimientodetallado.html', data)
                except Exception as ex:
                    pass

            elif action == 'addamplio':
                try:
                    data['title'] = u'Nuevo Área Conocimiento - Campo Amplio'
                    data['action'] = request.GET['action']
                    form = AreaConocimientoTitulacionForm()
                    data['form'] = form
                    template = get_template("th_titulos/modal/formaconocimiento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'addversion':
                try:
                    data['title'] = u'Nueva versión de matriz CINE'
                    data['action'] = request.GET['action']
                    form = VersionMatizCineForm()
                    data['form'] = form
                    template = get_template("th_titulos/modal/formaconocimiento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'addespecifico':
                try:
                    data['title'] = u'Nuevo Sub Área Conocimiento - Campo específico'
                    data['action'] = request.GET['action']
                    data['form'] = SubAreaConocimientoTitulacionForm()
                    template = get_template("th_titulos/modal/formaconocimiento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'adddetallado':
                try:
                    data['title'] = u'Nuevo Sub Área especificaconocimiento - Campo Detallado'
                    data['action'] = request.GET['action']
                    data['form'] = SubAreaEspecificaConocimientoTitulacionForm()
                    template = get_template("th_titulos/modal/formaconocimiento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editamplio':
                try:
                    data['title'] = u'Modificación de Área Conocimiento - Campo Amplio'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['action'] = request.GET['action']
                    data['areaconocimientotitulacion'] = areaconocimientotitulacion = \
                        AreaConocimientoTitulacion.objects.filter(pk=encrypt(request.GET['id']), status=True)[0]
                    initial = model_to_dict(areaconocimientotitulacion)
                    form = AreaConocimientoTitulacionForm(initial=initial)
                    data['form'] = form
                    template = get_template("th_titulos/modal/formaconocimiento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editespecifico':
                try:
                    data['title'] = u'Modificación de Sub Área Conocimiento - Campo específico'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['action'] = request.GET['action']
                    data[
                        'subareaconocimientotitulacion'] = subareaconocimientotitulacion = SubAreaConocimientoTitulacion.objects.get(
                        pk=encrypt(request.GET['id']), status=True)
                    initial = model_to_dict(subareaconocimientotitulacion)
                    form = SubAreaConocimientoTitulacionForm(initial=initial)
                    data['form'] = form
                    template = get_template("th_titulos/modal/formaconocimiento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editdetallado':
                try:
                    data['title'] = u'Modificación de Sub Área especificaconocimiento - Campo Detallado'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['action'] = request.GET['action']
                    data[
                        'subareaespecificaconocimientotitulacion'] = subareaespecificaconocimientotitulacion = SubAreaEspecificaConocimientoTitulacion.objects.get(
                        pk=id, status=True)
                    initial = model_to_dict(subareaespecificaconocimientotitulacion)
                    form = SubAreaEspecificaConocimientoTitulacionForm(initial=initial)
                    data['form'] = form
                    template = get_template("th_titulos/modal/formaconocimiento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'viewtitulossugeridos':
                try:
                    data['title'] = u'Títulos sugeridos'
                    filtros = Q(status=True)
                    id = request.GET.get('id')
                    if id:
                        filtros &= Q(
                            id=int(encrypt(id))
                        )
                    data['titulossugeridos'] = TituloSugerido.objects.filter(filtros)
                    return render(request, 'th_titulos/viewtitulossugeridos.html', data)
                except Exception as ex:
                    pass

            if action == 'validartitulosugerido':
                try:
                    data['title'] = u'Modificar titulo'
                    data['action'] = 'validartitulosugerido'
                    data['id'] = id = int(request.GET['id'])
                    titulosugerido = TituloSugerido.objects.get(pk=id)
                    form = TituloForm(initial={'nombre': titulosugerido.nombre,
                                                        'nivel': titulosugerido.nivel})
                    data['form'] = form
                    search = None
                    nivelselect = None
                    gradoselect = None
                    data['a'] = False
                    if 'n' in request.GET and 'g' in request.GET:
                        nivelselect = request.GET['n']
                        gradoselect = request.GET['g']
                    if 's' in request.GET:
                        search = request.GET['s']
                    if 'a' in request.GET:
                        data['a'] = True
                    data['search'] = search
                    data['nivelselect'] = nivelselect
                    data['gradoselect'] = gradoselect
                    # if request.user.has_perm('sga.puede_titulo_tthh'):
                    template = get_template("th_titulos/modal/formtitulo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'rechazartitulosugerido':
                try:
                    data['id'] = id = int(request.GET['id'])
                    data['form'] = ObservacionForm()
                    data['action'] = 'rechazartitulosugerido'
                    template = get_template("th_titulos/modal/formtitulo.html")

                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})
            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Titulos'
            search = None
            tipo = None
            url_vars = ''
            niveltitulo = NivelTitulacion.objects.filter(status=True, tipo=1)
            gradotitulo = GradoTitulacion.objects.all()
            nivelselect = 0
            gradoselect = 0
            listanivel = []
            listagrado = []
            if 'n' in request.GET:
                nivelselect = int(request.GET['n'])
                url_vars += "&n={}".format(nivelselect)
                if nivelselect > 0:
                    listanivel.append(nivelselect)
                else:
                    listanivel = niveltitulo.values_list('id')
            else:
                listanivel = niveltitulo.values_list('id')
            if 'g' in request.GET:
                gradoselect = int(request.GET['g'])
                url_vars += "&g={}".format(gradoselect)
                if gradoselect > 0:
                    listagrado.append(gradoselect)
                else:
                    listagrado = gradotitulo.values_list('id')
            else:
                listagrado = gradotitulo.values_list('id')
            ubicacion = Titulo.objects.filter(status=True).order_by('nivel')
            if 's' in request.GET:
                search = request.GET['s']
                url_vars += "&s={}".format(search)
                if search:
                    ubicacion = ubicacion.filter((Q(nombre__icontains=search) | Q(abreviatura__icontains=search)))
            if gradoselect > 0 and nivelselect > 0:
                ubicacion = ubicacion.filter(nivel__in=listanivel, nivel__isnull=False, grado__in=listagrado,
                                             grado__isnull=False)
            elif gradoselect > 0:
                ubicacion = ubicacion.filter(grado__in=listagrado, grado__isnull=False)
            elif nivelselect > 0:
                if nivelselect == 100:
                    ubicacion = ubicacion.filter(nivel__in=[3, 4], nivel__isnull=False)
                else:
                    ubicacion = ubicacion.filter(nivel__in=listanivel, nivel__isnull=False)
            paging = MiPaginador(ubicacion, 25)
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
            data['url_vars'] = url_vars
            data['search'] = search if search else ""
            data['titulos'] = page.object_list
            data['niveltitulo'] = niveltitulo
            data['gradotitulo'] = gradotitulo
            data['nivelselect'] = nivelselect
            data['gradoselect'] = gradoselect
            return render(request, "th_titulos/view.html", data)
