# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from decorators import secure_module, last_access
from sagest.forms import CampoContratoForm, PaisForm, \
    ProvinciaForm, CantonForm, ParroquiaForm
from sga.commonviews import adduserdata
from sga.funciones import log
from sga.models import Pais, Provincia, Canton, Parroquia


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addpais':
            try:
                form = PaisForm(request.POST)
                if form.is_valid():
                    if not Pais.objects.filter(status=True,nombre=form.cleaned_data['nombre']).exists():
                        pais = Pais(nombre=form.cleaned_data['nombre'],
                                    codigo=form.cleaned_data['codigo'],
                                    codigosniese=form.cleaned_data['codigosniese'],
                                    nacionalidad=form.cleaned_data['nacionalidad'],
                                    codigonacionalidad=form.cleaned_data['codigonacionalidad'],
                                    codigo_tthh=form.cleaned_data['codigo_tthh'])
                        pais.save(request)
                        log(u'Registro nuevo pais: %s' % pais, request, "add")
                        return JsonResponse({"result": "ok", 'id': pais.id})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'addprovincia':
            try:
                form = ProvinciaForm(request.POST)
                if form.is_valid():
                    if not Provincia.objects.filter(status=True, pais=form.cleaned_data['pais'], nombre=form.cleaned_data['nombre']).exists():
                        registro = Provincia(pais=form.cleaned_data['pais'],
                                             nombre=form.cleaned_data['nombre'],
                                             codigo=form.cleaned_data['codigo'],
                                             codigosniese=form.cleaned_data['codigosniese'],
                                             codigo_tthh=form.cleaned_data['codigo_tthh']
                                             )
                        registro.save(request)
                        log(u'Registro nuevo provincia: %s' % registro, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                     raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'addcanton':
            try:
                form = CantonForm(request.POST)
                if form.is_valid():
                    if not Canton.objects.filter(status=True, provincia=form.cleaned_data['provincia'], nombre=form.cleaned_data['nombre']).exists():
                        registro = Canton(provincia=form.cleaned_data['provincia'],
                                          nombre=form.cleaned_data['nombre'],
                                          codigo=form.cleaned_data['codigo'],
                                          codigosniese=form.cleaned_data['codigosniese'],
                                          codigo_tthh=form.cleaned_data['codigo_tthh'],
                                          codigo_distrito=form.cleaned_data['codigo_distrito'],
                                          circuito=form.cleaned_data['circuito'],
                                          zona=form.cleaned_data['zona'])
                        registro.save(request)
                        log(u'Registro nuevo de Canton: %s' % registro, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos, dato duplicado."})

        if action == 'addparroquia':
            try:
                form = ParroquiaForm(request.POST)
                if not form.is_valid():
                    raise NameError(u"Error en el formulario")
                if Parroquia.objects.filter(status=True, canton=form.cleaned_data['canton'], nombre=form.cleaned_data['nombre']).exists():
                    raise NameError(u"Parroquia ya existe")
                registro = Parroquia(canton=form.cleaned_data['canton'],
                                  nombre=form.cleaned_data['nombre'],
                                  codigo=form.cleaned_data['codigo'],
                                  codigosniese=form.cleaned_data['codigosniese'],
                                  codigo_tthh=form.cleaned_data['codigo_tthh'],
                                  codigonotaria=form.cleaned_data['codigonotaria'],)
                registro.save(request)
                log(u'Registro nuevo de Parroquia: %s' % registro, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos. %s" % ex.__str__()})

        if action == 'editpais':
            try:
                form = PaisForm(request.POST)
                if form.is_valid():
                    if not Pais.objects.filter(status=True, nombre=form.cleaned_data['nombre']).exclude(pk=request.POST['id']).exists():
                        registro = Pais.objects.get(pk=request.POST['id'], status=True)
                        registro.nombre=form.cleaned_data['nombre']
                        registro.codigo=form.cleaned_data['codigo']
                        registro.codigosniese=form.cleaned_data['codigosniese']
                        registro.nacionalidad=form.cleaned_data['nacionalidad']
                        registro.codigonacionalidad=form.cleaned_data['codigonacionalidad']
                        registro.codigo_tthh=form.cleaned_data['codigo_tthh']
                        registro.save(request)
                        log(u'Registro modificado pais: %s' % registro, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                    raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'editprovincia':
            try:
                form = ProvinciaForm(request.POST)
                if form.is_valid():
                    if not Provincia.objects.filter(status=True,pais=form.cleaned_data['pais'] ,nombre=form.cleaned_data['nombre']).exclude(pk=request.POST['id']).exists():
                        registro = Provincia.objects.get(pk=request.POST['id'], status=True)
                        registro.pais = form.cleaned_data['pais']
                        registro.nombre = form.cleaned_data['nombre']
                        registro.codigo = form.cleaned_data['codigo']
                        registro.codigosniese = form.cleaned_data['codigosniese']
                        registro.codigo_tthh = form.cleaned_data['codigo_tthh']
                        registro.save(request)
                        log(u'Registro modificado provincia: %s' % registro, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                    raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'editcanton':
            try:
                form = CantonForm(request.POST)
                if form.is_valid():
                    if not Canton.objects.filter(status=True, provincia=form.cleaned_data['provincia'], nombre=form.cleaned_data['nombre']).exclude(pk=request.POST['id']).exists():
                        registro = Canton.objects.get(pk=request.POST['id'], status=True)
                        registro.provincia = form.cleaned_data['provincia']
                        registro.nombre = form.cleaned_data['nombre']
                        registro.codigo = form.cleaned_data['codigo']
                        registro.codigosniese = form.cleaned_data['codigosniese']
                        registro.codigo_tthh = form.cleaned_data['codigo_tthh']
                        registro.codigo_distrito = form.cleaned_data['codigo_distrito']
                        registro.circuito = form.cleaned_data['circuito']
                        registro.zona = form.cleaned_data['zona']
                        registro.save(request)
                        log(u'Registro modificado canton: %s' % registro, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al editar los datos."})

        if action == 'editparroquia':
            try:
                form = ParroquiaForm(request.POST)
                if form.is_valid():
                    if not Parroquia.objects.filter(status=True, canton=form.cleaned_data['canton'], nombre=form.cleaned_data['nombre']).exclude(pk=request.POST['id']).exists():
                        registro = Parroquia.objects.get(pk=request.POST['id'], status=True)
                        registro.canton = form.cleaned_data['canton']
                        registro.nombre = form.cleaned_data['nombre']
                        registro.codigo = form.cleaned_data['codigo']
                        registro.codigosniese = form.cleaned_data['codigosniese']
                        registro.codigo_tthh = form.cleaned_data['codigo_tthh']
                        registro.codigonotaria = form.cleaned_data['codigonotaria']
                        registro.save(request)
                        log(u'Registro modificado parroquia: %s' % registro, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al editar los datos."})

        if action == 'deletepais':
            try:
                campo = Pais.objects.get(pk=request.POST['id'], status=True)
                campo.status = False
                campo.save(request)
                log(u'Elimino pais: %s' % campo, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'deleteprovincia':
            try:
                registro = Provincia.objects.get(pk=request.POST['id'], status=True)
                registro.status = False
                registro.save(request)
                log(u'Elimino provincia: %s' % registro, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'deletecanton':
            try:
                registro = Canton.objects.get(pk=request.POST['id'], status=True)
                registro.status = False
                registro.save(request)
                log(u'Elimino canton: %s' % registro, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'deleteparroquia':
            try:
                registro = Parroquia.objects.get(pk=request.POST['id'], status=True)
                registro.status = False
                registro.save(request)
                log(u'Elimino parroquia: %s' % registro, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'loadProvincia':
            try:
                return JsonResponse({"result": "ok", "data":[]})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": "Error al cargar los datos."})



        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addpais':
                try:
                    data['title'] = u'Nuevo País'
                    form = PaisForm()
                    data['form'] = form
                    return render(request, "th_cantones/addpais.html", data)
                except Exception as ex:
                    pass

            if action == 'addprovincia':
                try:
                    data['title'] = u'Nuevo Provincia'
                    data['form'] = ProvinciaForm()
                    return render(request, "th_cantones/addprovincia.html", data)
                except Exception as ex:
                    pass

            if action == 'addcanton':
                try:
                    data['title'] = u'Nuevo Canton'
                    data['form'] = CantonForm()
                    return render(request, "th_cantones/addcanton.html", data)
                except Exception as ex:
                    pass

            if action == 'addparroquia':
                try:
                    data['title'] = u'Nueva Parroquia'
                    data['form'] = ParroquiaForm()
                    return render(request, "th_cantones/addparroquia.html", data)
                except Exception as ex:
                    pass

            if action == 'editpais':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_periodo')
                    data['title'] = u'Modificación de País'
                    data['pais'] = pais = Pais.objects.filter(pk=request.GET['id'], status=True)[0]
                    initial = model_to_dict(pais)
                    form = PaisForm(initial=initial)
                    data['form'] = form
                    return render(request, "th_cantones/editpais.html", data)
                except Exception as ex:
                    pass

            if action == 'editprovincia':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_periodo')
                    data['title'] = u'Modificación de Provincia'
                    data['provincia'] = provincia = Provincia.objects.get(pk=request.GET['id'], status=True)
                    form = ProvinciaForm(initial={'pais':provincia.pais,
                                                  'nombre':provincia.nombre,
                                                  'codigo':provincia.codigo,
                                                  'codigosniese':provincia.codigosniese,
                                                  'codigo_tthh':provincia.codigo_tthh})
                    data['form'] = form
                    return render(request, "th_cantones/editprovincia.html", data)
                except Exception as ex:
                    pass

            if action == 'editcanton':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_periodo')
                    data['title'] = u'Modificación Cantón'
                    data['canton'] = canton = Canton.objects.get(pk=request.GET['id'], status=True)
                    form = CantonForm(initial={'provincia': canton.provincia,
                                               'nombre': canton.nombre,
                                               'codigo': canton.codigo,
                                               'codigosniese': canton.codigosniese,
                                               'codigo_tthh': canton.codigo_tthh,
                                               'codigo_distrito': canton.codigo_distrito,
                                               'circuito': canton.circuito,
                                               'zona': canton.zona})
                    data['form'] = form
                    return render(request, "th_cantones/editcanton.html", data)
                except Exception as ex:
                    pass

            if action == 'editparroquia':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_periodo')
                    data['title'] = u'Modificación Parroquia'
                    data['parroquia'] = parroquia = Parroquia.objects.get(pk=request.GET['id'], status=True)
                    form = ParroquiaForm(initial={'pais': parroquia.canton.provincia.pais_id,
                                                  'provincia': parroquia.canton.provincia_id,
                                                  'canton': parroquia.canton_id,
                                                  'nombre': parroquia.nombre,
                                                  'codigo': parroquia.codigo,
                                                  'codigosniese': parroquia.codigosniese,
                                                  'codigo_tthh': parroquia.codigo_tthh,
                                                  'codigonotaria': parroquia.codigonotaria,
                                                  })
                    form.editar(parroquia)
                    data['form'] = form
                    return render(request, "th_cantones/editparroquia.html", data)
                except Exception as ex:
                    pass

            if action == 'deletepais':
                try:
                    data['title'] = u'Eliminar País'
                    data['pais'] = Pais.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_cantones/deletepais.html", data)
                except:
                    pass

            if action == 'deleteprovincia':
                try:
                    data['title'] = u'Eliminar Provincia'
                    data['provincia'] = Provincia.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_cantones/deleteprovincia.html", data)
                except:
                    pass

            if action == 'deletecanton':
                try:
                    data['title'] = u'Eliminar Canton'
                    data['canton'] = Canton.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_cantones/deletecanton.html", data)
                except:
                    pass

            if action == 'deleteparroquia':
                try:
                    data['title'] = u'Eliminar Parroquia'
                    data['canton'] = Parroquia.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_cantones/deleteparroquia.html", data)
                except:
                    pass





            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Paises'
            data['cantones'] = Canton.objects.filter(status=True).order_by('provincia','nombre')
            data['provincias'] = Provincia.objects.filter(status=True).order_by('pais','nombre')
            data['paises'] = Pais.objects.filter(status=True).order_by('nombre')
            data['parroquia'] = Parroquia.objects.filter(status=True).order_by('nombre')
            return render(request, 'th_cantones/view.html', data)