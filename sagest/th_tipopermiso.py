# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import TipoPermisoForm, \
    TipoPermisoDetalleForm, IntegranteFamiliaForm,CategoriaTipoPermisoForm
from sagest.models import TipoPermisoDetalle, TipoPermiso, IntegranteFamilia, TipoPermisoDetalleFamilia, \
    TipoPermisoRegimenLaboral, RegimenLaboral,CategoriaTipoPermiso
from sga.commonviews import adduserdata
from sga.funciones import log
from django.template import Context
from django.template.loader import get_template
from sga.templatetags.sga_extras import encrypt
from django.forms import model_to_dict

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addtipopermiso':
            try:
                form = TipoPermisoForm(request.POST)
                if form.is_valid():
                    tipopermiso = TipoPermiso(descripcion=form.cleaned_data['descripcion'],
                                              observacion=form.cleaned_data['observacion'],
                                              quienaprueba=form.cleaned_data['quienaprueba'])
                    tipopermiso.save(request)
                    log(u'Registro nuevo de tipo de permiso: %s' % tipopermiso, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'addarticulo':
            try:
                form = TipoPermisoDetalleForm(request.POST)
                if form.is_valid():
                    registro = TipoPermisoDetalle(tipopermiso=form.cleaned_data['tipopermiso'],
                                                  descripcion=form.cleaned_data['descripcion'],
                                                  anios=form.cleaned_data['anios'],
                                                  meses=form.cleaned_data['meses'],
                                                  dias=form.cleaned_data['dias'],
                                                  horas=form.cleaned_data['horas'],
                                                  descuentovacaciones=form.cleaned_data['descuentovacaciones'],
                                                  perdirarchivo=form.cleaned_data['perdirarchivo'],
                                                  pagado=form.cleaned_data['pagado'],
                                                  # aplicar=form.cleaned_data['aplicar'],
                                                  diasplazo=form.cleaned_data['diasplazo'],
                                                  vigente=form.cleaned_data['vigente'])
                    registro.save(request)
                    log(u'Registro nuevo Articulo tipo permiso: %s' % registro, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'edittipopermiso':
            try:
                form = TipoPermisoForm(request.POST)
                if form.is_valid():
                    tipopermiso = TipoPermiso.objects.get(pk=request.POST['id'], status=True)
                    tipopermiso.descripcion = form.cleaned_data['descripcion']
                    tipopermiso.observacion = form.cleaned_data['observacion']
                    tipopermiso.quienaprueba = form.cleaned_data['quienaprueba']
                    tipopermiso.save(request)
                    log(u'Registro modificado tipo permiso: %s' % tipopermiso, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'editarticulo':
            try:
                form = TipoPermisoDetalleForm(request.POST)
                if form.is_valid():
                    tipopermisodetalle = TipoPermisoDetalle.objects.get(pk=request.POST['id'], status=True)
                    tipopermisodetalle.descripcion = form.cleaned_data['descripcion']
                    tipopermisodetalle.anios = form.cleaned_data['anios']
                    tipopermisodetalle.meses = form.cleaned_data['meses']
                    tipopermisodetalle.dias = form.cleaned_data['dias']
                    tipopermisodetalle.horas = form.cleaned_data['horas']
                    tipopermisodetalle.descuentovacaciones = form.cleaned_data['descuentovacaciones']
                    tipopermisodetalle.perdirarchivo = form.cleaned_data['perdirarchivo']
                    tipopermisodetalle.pagado = form.cleaned_data['pagado']
                    # tipopermisodetalle.aplicar = form.cleaned_data['aplicar']
                    tipopermisodetalle.diasplazo = form.cleaned_data['diasplazo']
                    tipopermisodetalle.vigente = form.cleaned_data['vigente']
                    tipopermisodetalle.save(request)
                    log(u'Registro modificado campos contratos: %s' % tipopermisodetalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al editar los datos."})

        if action == 'deletetipopermiso':
            try:
                tipopermiso = TipoPermiso.objects.get(pk=request.POST['id'], status=True)
                tipopermiso.delete()
                log(u'Elimino Tipo Permiso: %s' % tipopermiso, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'deletetipopermisodetalle':
            try:
                tipopermiso = TipoPermisoDetalle.objects.get(pk=request.POST['id'], status=True)
                tipopermiso.delete()
                log(u'Elimino Articulo Tipo Permiso: %s' % tipopermiso, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'desactivarvigente':
            try:
                tipopermiso = TipoPermisoDetalle.objects.get(pk=request.POST['id'], status=True)
                tipopermiso.vigente=False
                tipopermiso.save(request)
                log(u'Desactivo Vigente Articulo Tipo Permiso: %s' % tipopermiso, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al desactivar los datos."})

        if action == 'activarvigente':
            try:
                tipopermiso = TipoPermisoDetalle.objects.get(pk=request.POST['id'], status=True)
                tipopermiso.vigente=True
                tipopermiso.save(request)
                log(u'Activo Vigente Articulo Tipo Permiso: %s' % tipopermiso, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al desactivar los datos."})

        elif action == 'desactivararchivo':
                try:
                    tipopermiso = TipoPermisoDetalle.objects.get(pk=request.POST['id'], status=True)
                    tipopermiso.perdirarchivo = False
                    tipopermiso.save(request)
                    log(u'Desactivo Pedir Archivo Articulo Tipo Permiso: %s' % tipopermiso, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al desactivar los datos."})

        elif action == 'activararchivo':
                try:
                    tipopermiso = TipoPermisoDetalle.objects.get(pk=request.POST['id'], status=True)
                    tipopermiso.perdirarchivo = True
                    tipopermiso.save(request)
                    log(u'Activo Pedir Archivo Articulo Tipo Permiso: %s' % tipopermiso, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al activar los datos."})

        # INTEGRANTE FAMILIA
        elif action == 'addintegrantefamilia':
            try:
                form = IntegranteFamiliaForm(request.POST)
                if form.is_valid():
                        familia = IntegranteFamilia(integrante=form.cleaned_data['integrante'],
                                                    descripcion=form.cleaned_data['descripcion'])

                        familia.save(request)
                        log(u'Adiciono integrante familia: %s - [%s]' % (familia, familia.id), request, "add")
                        return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editintegrantefamilia':
            try:
                form = IntegranteFamiliaForm(request.POST)
                if form.is_valid():
                    familia = IntegranteFamilia.objects.get(pk=int(request.POST['id']))
                    familia.descripcion = form.cleaned_data['descripcion']
                    familia.integrante = form.cleaned_data['integrante']
                    familia.save(request)
                    log(u'Editar integrante familia: %s - [%s]' % (familia, familia.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delintegrantefamilia':
            try:
                familia = IntegranteFamilia.objects.get(pk=int(request.POST['id']))
                if familia.utilizado():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, utilizado en tipo permiso.."})
                log(u'Elimino integrante familia: %s - [%s]' % (familia, familia.id), request, "del")
                familia.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'vinculointegrantefamilia':
            try:
                data['permisofamilia'] = permisofamilia = TipoPermisoDetalleFamilia.objects.filter(tipopermisodetalle=int(request.POST['id']))
                if permisofamilia.exists():
                    data['integrantesfamilia'] = IntegranteFamilia.objects.filter(status=True).exclude(pk__in=[perfami.integrantefamilia.id for perfami in permisofamilia])
                else:
                    data['integrantesfamilia'] = IntegranteFamilia.objects.filter(status=True)
                template = get_template("th_tipopermiso/vinculointegrantefamilia.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        elif action == 'addvinculointegrantefamilia':
            try:
                idi = int(request.POST['idi'])
                id = int(request.POST['id'])
                detallepermiso = TipoPermisoDetalle.objects.get(pk=id)
                valor=False
                permisofamilia = detallepermiso.tipopermisodetallefamilia_set.filter(integrantefamilia_id=idi)
                if not permisofamilia.exists():
                    permisofami = TipoPermisoDetalleFamilia(integrantefamilia_id=idi, tipopermisodetalle=detallepermiso)
                    permisofami.save(request)
                    valor = True
                    log(u'Adiciono vinculo integrante familia con tipo permiso detalle: %s [%s]' % (permisofami, permisofami.id), request, "add")
                else:
                    log(u'Elimino vinculo integrante familia con tipo permiso detalle: %s [%s]' % (permisofamilia[0], permisofamilia[0].id), request, "del")
                    permisofamilia.delete()
                return JsonResponse({"result": "ok", "valor": valor })
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        #VINCULO TIPO DE PERMISO CON REGIMEN LABORAL
        elif action == 'vinculopermisoregimen':
            try:
                data['permisoregimen'] = permisoregimen = TipoPermisoRegimenLaboral.objects.filter(tipopermiso_id=int(request.POST['id']), status=True)
                if permisoregimen.exists():
                    data['regimenlaboral'] = RegimenLaboral.objects.filter(status=True).exclude(pk__in=[perregimen.regimenlaboral.id for perregimen in permisoregimen])
                else:
                    data['regimenlaboral'] = RegimenLaboral.objects.filter(status=True)
                template = get_template("th_tipopermiso/vinculopermisoregimenlaboral.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        elif action == 'addvinculopermisoregimen':
            try:
                idr = int(request.POST['idr'])
                id = int(request.POST['id'])
                valor = False
                tipopermiso = TipoPermiso.objects.get(pk=id, status=True)
                permisoregimen = tipopermiso.tipopermisoregimenlaboral_set.filter(regimenlaboral=idr, status=True)
                if not permisoregimen.exists():
                    permisoregimen = TipoPermisoRegimenLaboral(regimenlaboral_id=idr, tipopermiso=tipopermiso, status=True)
                    valor = True
                    permisoregimen.save(request)
                    log(u'Adiciono regimen laboral en tipo de permiso: regimenlaboral(%s) - tipopermiso(%s)' % (permisoregimen.regimenlaboral, tipopermiso), request, "add")
                else:
                    permisoregimen = permisoregimen[0]
                    log(u'Elimino regimen laboral en tipo de permiso: regimenlaboral(%s) - tipopermiso(%s)' % (permisoregimen.regimenlaboral, tipopermiso), request, "del")
                    permisoregimen.delete()
                return JsonResponse({"result": "ok", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        elif action == 'crea_modifica':
            try:
                if request.POST['a'] == 't':
                    tipo = TipoPermiso.objects.get(pk=int(request.POST['id']), status=True)
                    creacion = tipo.persona_creacion()
                    modificacion = tipo.persona_modificacion()
                else:
                    tipo = TipoPermisoDetalle.objects.get(pk=int(request.POST['id']), status=True)
                    creacion = tipo.persona_creacion()
                    modificacion = tipo.persona_modificacion()
                if creacion and modificacion:
                    return JsonResponse({"result": "ok",'creacion':True, 'nombre1':"Creación", 'fecha_c': tipo.fecha_creacion.strftime('%Y-%m-%d')+" "+ tipo.fecha_creacion.strftime("%H:%M"), 'persona_c':creacion.nombre_completo_inverso(), 'modificacion': True,'nombre2':"Modificación",  'fecha_m': tipo.fecha_modificacion.strftime('%Y-%m-%d')+" "+tipo.fecha_modificacion.strftime("%H:%M"), 'persona_m': modificacion.nombre_completo_inverso()})
                elif creacion:
                    return JsonResponse({"result": "ok",'creacion':True, 'nombre1':"Creación",  'fecha_c': tipo.fecha_creacion.strftime('%Y-%m-%d')+" "+ tipo.fecha_creacion.strftime("%H:%M"), 'persona_c':creacion.nombre_completo_inverso(), 'modificacion': False})
                elif modificacion:
                    return JsonResponse({"result": "ok", 'creacion': False, 'modificacion': True, 'nombre2':"Modificación", 'fecha_m': tipo.fecha_modificacion.strftime('%Y-%m-%d')+" "+tipo.fecha_modificacion.strftime("%H:%M"), 'persona_m': modificacion.nombre_completo_inverso()})
                else:
                    return JsonResponse({"result": "ok", 'creacion': False, 'modificacion': False})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        elif action == 'updateobservacion':
            try:
                tipopermiso = TipoPermiso.objects.get(pk=int(request.POST['id']))
                valor = request.POST['vc']
                tipopermiso.observacion = valor
                tipopermiso.save(request)
                return JsonResponse({'result': 'ok', 'valor': tipopermiso.observacion})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al actualizar observación."})

        elif action == 'updatedescripcion':
            try:
                tipopermiso = TipoPermiso.objects.get(pk=int(request.POST['id']))
                valor = request.POST['vc']
                tipopermiso.descripcion = valor
                tipopermiso.save(request)
                return JsonResponse({'result': 'ok', 'valor': tipopermiso.descripcion})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al actualizar descripcion."})

        elif action == 'updateanios':
            try:
                tipopermiso = TipoPermisoDetalle.objects.get(pk=int(request.POST['id']))
                valor = request.POST['vc']
                tipopermiso.anios = valor
                tipopermiso.save(request)
                return JsonResponse({'result': 'ok', 'valor': tipopermiso.anios})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al actualizar años."})
        elif action == 'updatemeses':
            try:
                tipopermiso = TipoPermisoDetalle.objects.get(pk=int(request.POST['id']))
                valor = request.POST['vc']
                tipopermiso.meses = valor
                tipopermiso.save(request)
                return JsonResponse({'result': 'ok', 'valor': tipopermiso.meses})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al actualizar los meses."})
        elif action == 'updatedias':
            try:
                tipopermiso = TipoPermisoDetalle.objects.get(pk=int(request.POST['id']))
                valor = request.POST['vc']
                tipopermiso.dias = valor
                tipopermiso.save(request)
                return JsonResponse({'result': 'ok', 'valor': tipopermiso.dias})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al actualizar dias."})
        elif action == 'updatehoras':
            try:
                tipopermiso = TipoPermisoDetalle.objects.get(pk=int(request.POST['id']))
                valor = request.POST['vc']
                tipopermiso.horas = valor
                tipopermiso.save(request)
                return JsonResponse({'result': 'ok', 'valor': tipopermiso.horas})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al actualizar horas."})

        elif action == 'updatediasplazo':
            try:
                tipopermiso = TipoPermisoDetalle.objects.get(pk=int(request.POST['id']))
                valor = request.POST['vc']
                tipopermiso.diasplazo = valor
                tipopermiso.save(request)
                return JsonResponse({'result': 'ok', 'valor': tipopermiso.diasplazo})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al actualizar los días plazo."})

        elif action == 'addsubcatpermiso':
            try:
                f = CategoriaTipoPermisoForm(request.POST)
                if not f.is_valid():
                    raise NameError('Datos incorrectos')
                subcategoria = CategoriaTipoPermiso(
                    tipopermiso=f.cleaned_data['tipopermiso'],
                    descripcion=f.cleaned_data['descripcion']
                )
                subcategoria.save(request)
                log('Se adicciono la categoria %s al permiso %s'%(subcategoria.descripcion,subcategoria.tipopermiso),request,'add')
                return JsonResponse({'result':False,'mensaje':u'Registro guardado exitosamente.'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result':'bad','mensaje':u'Error al procesar datos.'})

        elif action == 'editsubcatpermiso':
            try:
                f = CategoriaTipoPermisoForm(request.POST)
                if not 'id' in request.POST:
                    raise  NameError('Datos incorrectos')
                if not f.is_valid():
                    raise NameError('Datos incorrectos')
                id = int(encrypt(request.POST['id']))
                if not CategoriaTipoPermiso.objects.filter(pk=id, status=True).exists():
                    raise NameError('Datos incorrectos')
                filtro = CategoriaTipoPermiso.objects.get(pk=id, status=True)
                filtro.tipopermiso = f.cleaned_data['tipopermiso']
                filtro.descripcion = f.cleaned_data['descripcion']
                filtro.save(request)
                log('Se edito la categoria %s al permiso %s' % (filtro.descripcion, filtro.tipopermiso), request, 'edit')
                return JsonResponse({'result': False, 'mensaje': u'Registro guardado exitosamente.'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result':'bad','mensaje':u'Error al procesar datos.'})

        elif action == 'deletesubcatpermiso':
            try:
                with transaction.atomic():
                    if not 'id' in request.POST:
                        raise NameError('Error al procesar los datos.')
                    id = int(request.POST['id'])
                    if not CategoriaTipoPermiso.objects.filter(status=True,pk=id):
                        raise NameError('Error al procesar los datos.')
                    instancia = CategoriaTipoPermiso.objects.get(status=True, pk=id)
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino la categoria %s al permiso %s'%(instancia.descripcion, instancia.tipopermiso),request,'delete')
                    return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'error': True, "message": "Error: {}".format(ex)})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addarticulo':
                try:
                    data['title'] = u'Nuevo Articulo'
                    data['form'] = TipoPermisoDetalleForm()
                    return render(request, "th_tipopermiso/addarticulo.html", data)
                except Exception as ex:
                    pass

            if action == 'addtipopermiso':
                try:
                    data['title'] = u'Adicionar Tipo de Permiso'
                    form = TipoPermisoForm()
                    data['form'] = form
                    return render(request, "th_tipopermiso/addtipopermiso.html", data)
                except Exception as ex:
                    pass

            if action == 'editarticulo':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_periodo')
                    data['title'] = u'Modificación de Articulo'
                    data['tipopermisodetalle'] = tipopermisodetalle = TipoPermisoDetalle.objects.get(pk=request.GET['id'], status=True)
                    form = TipoPermisoDetalleForm(initial={'tipopermiso': tipopermisodetalle.tipopermiso,
                                                           'descripcion': tipopermisodetalle.descripcion,
                                                           'anios': tipopermisodetalle.anios,
                                                           'meses': tipopermisodetalle.meses,
                                                           'dias': tipopermisodetalle.dias,
                                                           'horas': tipopermisodetalle.horas,
                                                           'descuentovacaciones': tipopermisodetalle.descuentovacaciones,
                                                           'perdirarchivo': tipopermisodetalle.perdirarchivo,
                                                           'pagado': tipopermisodetalle.pagado,
                                                           # 'aplicar': tipopermisodetalle.aplicar,
                                                           'diasplazo': tipopermisodetalle.diasplazo,
                                                           'vigente': tipopermisodetalle.vigente})
                    form.editar()
                    data['form'] = form
                    return render(request, "th_tipopermiso/editarticulo.html", data)
                except Exception as ex:
                    pass

            if action == 'edittipopermiso':
                try:
                    data['title'] = u'Editar Tipo de Permiso'
                    data['tipopermiso'] = tipopermiso = TipoPermiso.objects.filter(pk=request.GET['id'], status=True)[0]
                    permisoregimen = TipoPermisoRegimenLaboral.objects.filter(status=True, tipopermiso=tipopermiso)
                    data['form'] = TipoPermisoForm(initial={'descripcion': tipopermiso.descripcion,
                                                            'observacion': tipopermiso.observacion,
                                                            'regimenlaboral': permisoregimen,
                                                            'quienaprueba':tipopermiso.quienaprueba})
                    return render(request, "th_tipopermiso/edittipopermiso.html", data)
                except Exception as ex:
                    pass

            if action == 'deletetipopermiso':
                try:
                    data['title'] = u'Eliminar Tipo de Permiso'
                    data['tipopermiso'] = TipoPermiso.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_tipopermiso/deletetipopermiso.html", data)
                except:
                    pass

            if action == 'deletearticulo':
                try:
                    data['title'] = u'Eliminar Articulo'
                    data['tipopermisodetalle'] = TipoPermisoDetalle.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_tipopermiso/deletetipopermisodetalle.html", data)
                except:
                    pass

            if action == 'desactivarvigente':
                try:
                    data['title'] = u'Desactivar Articulo'
                    data['tipopermisodetalle'] = TipoPermisoDetalle.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_tipopermiso/desactivarvigente.html", data)
                except:
                    pass

            if action == 'activarvigente':
                try:
                    data['title'] = u'Activar Articulo'
                    data['tipopermisodetalle'] = TipoPermisoDetalle.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_tipopermiso/activarvigente.html", data)
                except:
                    pass

            elif action == 'desactivararchivo':
                try:
                    data['title'] = u'Desactivar Archivo'
                    data['tipopermisodetalle'] = TipoPermisoDetalle.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_tipopermiso/desactivararchivo.html", data)
                except:
                    pass

            elif action == 'activararchivo':
                try:
                    data['title'] = u'Activar Archivo'
                    data['tipopermisodetalle'] = TipoPermisoDetalle.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_tipopermiso/activararchivo.html", data)
                except:
                    pass

            # INTEGRANTE FAMILIA
            elif action == 'addintegrantefamilia':
                try:
                    data['title'] = u'Adicionar integrante de familia'
                    data['form'] = IntegranteFamiliaForm()
                    return render(request, "th_tipopermiso/addintegrantefamilia.html", data)
                except Exception as ex:
                    pass

            elif action == 'editintegrantefamilia':
                try:
                    data['title'] = u'Editar integrante de familia'
                    data['integrante'] = integrantes = IntegranteFamilia.objects.get(pk=int(request.GET['id']))
                    form =IntegranteFamiliaForm(initial={'integrante': integrantes.integrante, 'descripcion': integrantes.descripcion})
                    data['form'] = form
                    return render(request, "th_tipopermiso/editintegrantefamilia.html", data)
                except Exception as ex:
                    pass

            elif action == 'delintegrantefamilia':
                try:
                    data['title'] = u'Eliminar integrante de familia'
                    data['integrante'] = IntegranteFamilia.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_tipopermiso/delintegrantefamilia.html", data)
                except Exception as ex:
                    pass

            elif action == 'integrantefamilia':
                try:
                    data['title'] = u'Integrantes de familia'
                    data['integrantes'] = IntegranteFamilia.objects.filter(status=True)
                    return render(request, "th_tipopermiso/viewintegrantefamilia.html", data)
                except Exception as ex:
                    pass

            elif action == 'addsubcatpermiso':
                try:
                    form = CategoriaTipoPermisoForm()
                    form.fields['tipopermiso'].queryset = TipoPermiso.objects.filter(status=True,quienaprueba=2)
                    data['form'] = form
                    data['action'] = action
                    template = get_template("th_tipopermiso/addsubpermiso.html")
                    return JsonResponse({'result':True,'data':template.render(data)})
                except Exception as ex:
                    pass
            elif action == 'editsubcatpermiso':
                try:
                    id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = CategoriaTipoPermiso.objects.get(pk =id)
                    form = CategoriaTipoPermisoForm(initial=model_to_dict(filtro))
                    form.fields['tipopermiso'].queryset = TipoPermiso.objects.filter(status=True, quienaprueba=2)
                    form.initial['tipopermiso'] = filtro.tipopermiso
                    data['form'] = form
                    data['action'] = action
                    template = get_template("th_tipopermiso/addsubpermiso.html")
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Tipos de Permiso'
            data['tipopermisodetalles'] = TipoPermisoDetalle.objects.filter(status=True).order_by('-descripcion')
            data['tipopermisos'] = TipoPermiso.objects.filter(status=True).order_by('-descripcion')
            data['subtipopermisos'] = CategoriaTipoPermiso.objects.filter(status=True).order_by('-descripcion')
            return render(request, 'th_tipopermiso/view.html', data)