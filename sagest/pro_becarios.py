# -*- coding: UTF-8 -*-
import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template

from decorators import secure_module
from sagest.forms import ProyectoBecasForm, DetalleBecaDocenteForm, DetalleRubroBecaDocenteArchivoForm, \
    DetalleBecaDocenteAdendumForm
from sagest.models import BecaDocente, RubroBeca, DetalleBecaDocente, DetalleRubroBecaDocente, \
    DetalleRubroBecaDocenteArchivo, CategoriaRubroBeca
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = ProyectoBecasForm(request.POST)
                if f.is_valid():
                    becadocente = BecaDocente(proyecto=f.cleaned_data['proyecto'],
                                              becario = persona,
                                              garante = f.cleaned_data['garante'],
                                              universidad = f.cleaned_data['universidad'],
                                              titulo = f.cleaned_data['titulo'],
                                              fechainicio = f.cleaned_data['fechainicio'],
                                              fechafin = f.cleaned_data['fechafin'],
                                              representantelegal = f.cleaned_data['representantelegal'],
                                              formadepagos = f.cleaned_data['formadepagos'],
                                              estadobeca = 1)
                    becadocente.save(request)
                    log(u'Ingreso Proyecto Beca: %s' % (becadocente), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                becadocente = BecaDocente.objects.get(pk=request.POST['id'])
                f = ProyectoBecasForm(request.POST)
                if f.is_valid():
                    becadocente.proyecto = f.cleaned_data['proyecto']
                    becadocente.garante = f.cleaned_data['garante']
                    becadocente.universidad = f.cleaned_data['universidad']
                    becadocente.titulo = f.cleaned_data['titulo']
                    becadocente.fechainicio = f.cleaned_data['fechainicio']
                    becadocente.fechafin = f.cleaned_data['fechafin']
                    becadocente.representantelegal = f.cleaned_data['representantelegal']
                    becadocente.formadepagos = f.cleaned_data['formadepagos']
                    becadocente.save(request)
                    log(u'Modifico Proyecto Beca: %s' % (becadocente), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                becadocente = BecaDocente.objects.get(pk=request.POST['id'])
                becadocente.status=False
                becadocente.save(request)
                log(u'Elimino Proyecto Beca: %s' % (becadocente), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addrubro':
            try:
                form = DetalleBecaDocenteForm(request.POST)
                if form.is_valid():
                    becadocente = BecaDocente.objects.get(pk=request.POST['id'])
                    registro = DetalleBecaDocente(becadocente=becadocente,
                                                  mesesviaje=form.cleaned_data['mesesviaje'],
                                                  fechainicio=form.cleaned_data['fechainicio'],
                                                  fechafin=form.cleaned_data['fechafin'])
                    registro.save(request)
                    # INSERTA LOS RUBROS SELECCIONADOS
                    for elemento in json.loads(request.POST['lista_items1']):
                        detallerubrobecadocente = DetalleRubroBecaDocente(detallebecadocente=registro,
                                                                          rubrobeca_id=int(elemento['id']),
                                                                          valor = elemento['valors'])
                        detallerubrobecadocente.save(request)
                    log(u'Registro nuevo Detalle Beca Docente: %s' % registro, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'editrubro':
            try:
                form = DetalleBecaDocenteForm(request.POST)
                if form.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    detallebecadocente = DetalleBecaDocente.objects.get(pk=request.POST['id'], status=True)
                    detallebecadocente.mesesviaje = form.cleaned_data['mesesviaje']
                    detallebecadocente.fechainicio = form.cleaned_data['fechainicio']
                    detallebecadocente.fechafin = form.cleaned_data['fechafin']
                    detallebecadocente.save(request)
                    # MODIFICAR LOS RUBROS SELECCIONADOS
                    for elemento in datos:
                        if DetalleRubroBecaDocente.objects.values('id').filter(detallebecadocente=detallebecadocente,rubrobeca_id=int(elemento['id'])).exists():
                            detallerubrobecadocente = DetalleRubroBecaDocente.objects.filter(detallebecadocente=detallebecadocente, rubrobeca_id=int(elemento['id']))[0]
                            detallerubrobecadocente.valor = elemento['valors']
                        else:
                            detallerubrobecadocente = DetalleRubroBecaDocente(detallebecadocente=detallebecadocente,
                                                                              rubrobeca_id=int(elemento['id']),
                                                                              valor=elemento['valors'])
                        detallerubrobecadocente.save(request)
                    log(u'Registro modificado Detalle Beca Docente: %s' % detallebecadocente, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'addadendum':
            try:
                form = DetalleBecaDocenteForm(request.POST)
                if form.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    detallebecadocente = DetalleBecaDocente.objects.get(pk=request.POST['id'], status=True)
                    # MODIFICAR LOS RUBROS SELECCIONADOS
                    for elemento in datos:
                        if DetalleRubroBecaDocente.objects.values('id').filter(detallebecadocente=detallebecadocente,rubrobeca_id=int(elemento['id'])).exists():
                            detallerubrobecadocente = DetalleRubroBecaDocente.objects.filter(detallebecadocente=detallebecadocente, rubrobeca_id=int(elemento['id']))[0]
                            detallerubrobecadocente.valoradendum = elemento['valors']
                        else:
                            detallerubrobecadocente = DetalleRubroBecaDocente(detallebecadocente=detallebecadocente,
                                                                              rubrobeca_id=int(elemento['id']),
                                                                              valor=0,
                                                                              valoradendum=elemento['valors'])
                        detallerubrobecadocente.save(request)
                    log(u'Registro modificado Detalle Beca Docente: %s' % detallebecadocente, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'adddocumento':
            try:
                form = DetalleRubroBecaDocenteArchivoForm(request.POST, request.FILES)
                if form.is_valid():
                    detallerubrobecadocente = DetalleRubroBecaDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("documentosdetallerubrobecadocente_", newfile._name)
                    archivo = DetalleRubroBecaDocenteArchivo(detallerubrobecadocente=detallerubrobecadocente,
                                                             nombre=form.cleaned_data['nombre'],
                                                             archivo=newfile)
                    archivo.save(request)
                    log(u'Adiciono documento de Detalle Rubro Beca Docente Archivo: %s' % archivo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'detalle_archivo':
            try:
                data['detallerubrobecadocente'] = detallerubrobecadocente = DetalleRubroBecaDocente.objects.get(pk=request.POST['id'], status=True)
                data['detallerubrobecadocentearchivo'] = detallerubrobecadocente.detallerubrobecadocentearchivo_set.filter(status=True)
                template = get_template("pro_becarios/detalle_archivo.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'detallepdf':
            try:
                data['title'] = u'Proyecto Beca'
                data['becadocente'] = becadocente = BecaDocente.objects.filter(id=int(request.POST['id']))[0]
                data['detallebecadocentes'] = detallebecadocente = becadocente.detallebecadocente_set.filter(status=True).order_by('fechainicio')
                data['categoriarubrobecas'] = CategoriaRubroBeca.objects.filter(status=True, rubrobeca__detallerubrobecadocente__detallebecadocente__in=detallebecadocente).distinct()
                hoy = datetime.now().date()
                return conviert_html_to_pdf(
                    'pro_becarios/proyectobeca_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        if action == 'eliminardetalle':
            try:
                detallebecadocente = DetalleBecaDocente.objects.get(pk=int(request.POST['id']))
                detallebecadocente.status = False
                detallebecadocente.save(request)
                log(u'Eliminar Detalle Beca Docente: %s' % detallebecadocente, request, "delete")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cerrar':
            try:
                detallebecadocente = DetalleBecaDocente.objects.get(pk=int(request.POST['id']))
                detallebecadocente.cerrado = True
                detallebecadocente.save(request)
                mail = 'direccionfinanciera@unemi.edu.ec'
                docente = detallebecadocente.becadocente.becario.nombre_completo_inverso()
                proyecto = detallebecadocente.becadocente.proyecto
                detalle = str(detallebecadocente.fechainicio) + " - " + str(detallebecadocente.fechafin)
                send_html_mail("Cierre Detalle Beca Docente", "emails/cierredetallebecadocente.html", {'sistema': request.session['nombresistema'], 'docente': docente, 'proyecto': proyecto, 'detalle': detalle}, mail, [], cuenta=CUENTAS_CORREOS[0][1])
                log(u'Cerro detalle beca docente: %s' % detallebecadocente, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Crear Proyecto - becas'
                    form = ProyectoBecasForm()
                    data['form'] = form
                    return render(request, 'pro_becarios/add.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar Proyecto - becas'
                    data['becadocente'] = becadocente = BecaDocente.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(becadocente)
                    form = ProyectoBecasForm(initial=initial)
                    data['form'] = form
                    return render(request, 'pro_becarios/edit.html', data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Proyecto - becas'
                    data['becadocente'] = BecaDocente.objects.get(pk=request.GET['id'])
                    return render(request, 'pro_becarios/delete.html', data)
                except Exception as ex:
                    pass

            if action == 'rubros':
                try:
                    data['title'] = u'Detalle de Rubros-Becas'
                    data['becadocente'] = becadocente = BecaDocente.objects.get(pk=request.GET['id'])
                    data['detallebecadocentes'] = becadocente.detallebecadocente_set.filter(status=True).order_by('fechainicio')
                    return render(request, "pro_becarios/rubros.html", data)
                except Exception as ex:
                    pass

            if action == 'addrubro':
                try:
                    data['becadocente'] = becadocente = BecaDocente.objects.get(pk=request.GET['id'])
                    data['title'] = u'Nuevo - Forma de Pago: ' + becadocente.get_formadepagos_display()
                    if becadocente.formadepagos == 1:
                        data['mes'] = "1"
                    if becadocente.formadepagos == 2:
                        data['mes'] = "2"
                    if becadocente.formadepagos == 3:
                        data['mes'] = "3"
                    if becadocente.formadepagos == 4:
                        data['mes'] = "6"
                    if becadocente.formadepagos == 5:
                        data['mes'] = "12"
                    data['form'] = DetalleBecaDocenteForm(initial={'mesesviaje': becadocente.formadepagos})
                    data['campos'] = RubroBeca.objects.filter(status=True)
                    return render(request, "pro_becarios/addrubro.html", data)
                except Exception as ex:
                    pass

            if action == 'editrubro':
                try:
                    data['title'] = u'Modificación'
                    data['detallebecadocente'] = detallebecadocente = DetalleBecaDocente.objects.get(pk=request.GET['id'], status=True)
                    data['contratoscamposseleccion'] = detallebecadocente.detallerubrobecadocente_set.filter(status=True)
                    data['becadocente'] = detallebecadocente.becadocente
                    data['campos'] = RubroBeca.objects.filter(status=True)
                    form = DetalleBecaDocenteForm(initial={'fechainicio': detallebecadocente.fechainicio,
                                                           'fechafin': detallebecadocente.fechafin,
                                                           'mesesviaje': detallebecadocente.mesesviaje})
                    data['form'] = form
                    return render(request, "pro_becarios/editrubro.html", data)
                except Exception as ex:
                    pass

            if action == 'addadendum':
                try:
                    data['title'] = u'Generación Adendum'
                    data['detallebecadocente'] = detallebecadocente = DetalleBecaDocente.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    data['contratoscamposseleccion'] = detallebecadocente.detallerubrobecadocente_set.filter(status=True)
                    data['becadocente'] = detallebecadocente.becadocente
                    data['campos'] = RubroBeca.objects.filter(status=True)
                    form = DetalleBecaDocenteAdendumForm(initial={'fechainicio': detallebecadocente.fechainicio,
                                                                  'fechafin': detallebecadocente.fechafin,
                                                                  'mesesviaje': detallebecadocente.mesesviaje})
                    form.editar()
                    data['form'] = form
                    return render(request, "pro_becarios/addadendum.html", data)
                except Exception as ex:
                    pass

            if action == 'adddocumento':
                try:
                    data['detallerubrobecadocente'] = detallerubrobecadocente = DetalleRubroBecaDocente.objects.filter(pk=int(encrypt(request.GET['id'])), status=True)[0]
                    data['title'] = u'Adicionar documento '+ detallerubrobecadocente.rubrobeca.nombre
                    data['becadocente'] = detallerubrobecadocente.detallebecadocente.becadocente
                    data['form'] = DetalleRubroBecaDocenteArchivoForm()
                    return render(request, "pro_becarios/adddocumento.html", data)
                except Exception as ex:
                    pass

            if action == 'eliminardetalle':
                try:
                    data['title'] = u'Confirmar eliminar Detalle Beca Docente'
                    data['detallebecadocente'] = detallebecadocente = DetalleBecaDocente.objects.get(pk=int(request.GET['id']))
                    data['becadocente'] = detallebecadocente.becadocente
                    return render(request, "pro_becarios/eliminardetalle.html", data)
                except:
                    pass

            if action == 'cerrar':
                try:
                    data['title'] = u'Cerrar Detalle beca Docente'
                    data['detallebecadocente'] = detallebecadocente = DetalleBecaDocente.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['becadocente'] = detallebecadocente.becadocente
                    return render(request, "pro_becarios/cerrar.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Gestión de proyectos-becas'
            search = None
            ids = None
            tipo = None
            if 'id' in request.GET:
                ids = request.GET['id']
                becadocentes = BecaDocente.objects.filter(id=ids, status=True)
            else:
                becadocentes = BecaDocente.objects.filter(status=True)
            paging = MiPaginador(becadocentes, 25)
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
            data['becadocentes'] = page.object_list
            return render(request, "pro_becarios/view.html", data)
