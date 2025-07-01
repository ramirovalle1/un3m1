# -*- coding: UTF-8 -*-

from django.contrib.auth.decorators import login_required
from django.db import transaction
import json
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from django.forms.models import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template import RequestContext
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, generar_nombre
# from sga.models import ProgramaPrapre,Carrera,Coordinacion, ProgramaProceval, InstitucionProPracticas, Canton, Parroquia, \
#     InscripcionProPracticas
# from sga.forms import ProgramaPrapreForm, InstitucionProPracticasForm
# from sga.funcionesxhtml2pdf import conviert_html_to_pdf


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {'title': u'Programas Practicas Pre Profesionales'}
    adduserdata(request, data)
    # if request.method == 'POST':
    #     action = request.POST['action']
    #     if action == 'add':
    #         f = ProgramaPrapreForm(request.POST)
    #         if f.is_valid():
    #             try:
    #                 if not ProgramaPrapre.objects.filter(descripcion=f.cleaned_data['descripcion']).exists():
    #                     programapra = ProgramaPrapre(coordinacion=f.cleaned_data['coordinacion'],
    #                                                  carrera=f.cleaned_data['carrera'],
    #                                                  fechadesde=f.cleaned_data['fechaini'],
    #                                                  fechahasta=f.cleaned_data['fechfin'],
    #                                                  descripcion=f.cleaned_data['descripcion'],
    #                                                  objgeneral=f.cleaned_data['objgeneral'],
    #                                                  objespecifico=f.cleaned_data['objespecifico'],
    #                                                  justificacion=f.cleaned_data['justificacion'],
    #                                                  recurso=f.cleaned_data['recurso'],
    #                                                  cronograma=f.cleaned_data['cronograma']
    #                                                  )
    #                     programapra.save(request)
    #                     return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
    #                 else:
    #                     return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Ya existe un Programa activo."}), content_type="application/json")
    #             except Exception as ex:
    #                 transaction.set_rollback(True)
    #                 return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al guardar los datos."}), content_type="application/json")
    #         else:
    #             return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al guardar los datos."}), content_type="application/json")
    #
    #     elif action == 'pdf':
    #         try:
    #             data = {}
    #             adduserdata(request, data)
    #             data['programa'] = ProgramaPrapre.objects.get(pk=request.POST['id'])
    #             data['listainstitucion'] = InstitucionProPracticas.objects.filter(programa=request.POST['id'], estado='A')
    #             data['procedimientoeval'] = ProgramaProceval.objects.filter(estado='A').all()
    #             return conviert_html_to_pdf(
    #                 'pra_programaprac/programas_pdf.html',
    #                 {
    #                     'pagesize': 'A4',
    #                     'listadoprograma': data,
    #                 }
    #             )
    #         except Exception as ex:
    #             pass
    #
    #     elif action == 'pdfinscritos':
    #         try:
    #             data = {}
    #             adduserdata(request, data)
    #             data['inscritoslis'] = InstitucionProPracticas.objects.get(pk=request.POST['id'],estado='A')
    #             data['inscritos'] = InscripcionProPracticas.objects.filter(institucion=request.POST['id'],estado=True)
    #             return conviert_html_to_pdf(
    #                 'pra_programaprac/inscritos_pdf.html',
    #                 {
    #                     'pagesize': 'A4',
    #                     'listadoinscritos': data,
    #                 }
    #             )
    #         except Exception as ex:
    #             pass
    #
    #     elif action == 'edit':
    #         f = ProgramaPrapreForm(request.POST)
    #         if f.is_valid():
    #             try:
    #                 programa = ProgramaPrapre.objects.get(pk=request.POST['id'])
    #                 programa.descripcion = f.cleaned_data['descripcion']
    #                 programa.coordinacion = f.cleaned_data['coordinacion']
    #                 programa.carrera = f.cleaned_data['carrera']
    #                 programa.fechadesde = f.cleaned_data['fechaini']
    #                 programa.fechahasta = f.cleaned_data['fechfin']
    #                 programa.objgeneral = f.cleaned_data['objgeneral']
    #                 programa.objespecifico = f.cleaned_data['objespecifico']
    #                 programa.justificacion = f.cleaned_data['justificacion']
    #                 programa.recurso = f.cleaned_data['recurso']
    #                 programa.cronograma = f.cleaned_data['cronograma']
    #                 programa.save(request)
    #                 return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
    #             except Exception as ex:
    #                 transaction.set_rollback(True)
    #                 return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al guardar los datos."}), content_type="application/json")
    #         else:
    #             return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al guardar los datos."}), content_type="application/json")
    #
    #     elif action == 'editinstitucion':
    #         f = InstitucionProPracticasForm(request.POST)
    #         if f.is_valid():
    #             try:
    #                 institucion = InstitucionProPracticas.objects.get(pk=request.POST['idinstitucion'])
    #                 institucion.horas = f.cleaned_data['horas']
    #                 institucion.cupos = f.cleaned_data['cupos']
    #                 institucion.save(usuario=request.user)
    #                 return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
    #             except Exception as ex:
    #                 transaction.set_rollback(True)
    #                 return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al guardar los datos."}), content_type="application/json")
    #         else:
    #             return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al guardar los datos."}), content_type="application/json")
    #
    #     if action == 'addinstitucion':
    #         f = InstitucionProPracticasForm(request.POST)
    #         if f.is_valid():
    #             try:
    #                 if not InstitucionProPracticas.objects.filter(programa_id=int(request.POST['idpra']), empresa=f.cleaned_data['empresa'], estado='A').exists():
    #                     programapra = InstitucionProPracticas(programa_id=int(request.POST['idpra']),
    #                                                           empresa=f.cleaned_data['empresa'],
    #                                                           cupos=f.cleaned_data['cupos'],
    #                                                           horas=f.cleaned_data['horas']
    #                                                           )
    #                     programapra.save(usuario=request.user)
    #                     return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
    #                 else:
    #                     return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Ya existe la Institución en el Programa."}), content_type="application/json")
    #             except Exception as ex:
    #                 transaction.set_rollback(True)
    #                 return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al guardar los datos."}), content_type="application/json")
    #         else:
    #             return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al guardar los datos."}), content_type="application/json")
    #
    #     elif action == 'deleteinstitucion':
    #         try:
    #             institucion = InstitucionProPracticas.objects.get(pk=request.POST['id'])
    #             institucion.estado = 'E'
    #             institucion.save(usuario=request.user)
    #             return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
    #         except Exception as ex:
    #             transaction.set_rollback(True)
    #             return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al eliminar los datos."}), content_type="application/json")
    #
    #     elif action == 'delete':
    #         try:
    #             programapra = ProgramaPrapre.objects.get(pk=request.POST['id'])
    #             programapra.estado = 'E'
    #             programapra.save(request)
    #             return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
    #         except Exception as ex:
    #             transaction.set_rollback(True)
    #             return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al eliminar los datos."}), content_type="application/json")
    #
    #     return HttpResponse(json.dumps({"result": "bad", "mensaje": "Solicitud Incorrecta."}), content_type="application/json")
    #
    # else:
    #     if 'action' in request.GET:
    #         action = request.GET['action']
    #         if action == 'add':
    #             try:
    #                 data['title'] = u'Adicionar Programa'
    #                 form = ProgramaPrapreForm()
    #                 form.query()
    #                 data['form'] = form
    #                 #data['formuevaluacion'] = ProgramaProceval.objects.filter(estado='A')
    #                 return render(request, 'pra_programaprac/add.html', data)
    #             except Exception as ex:
    #                 pass
    #
    #         if action == 'addinstitucion':
    #             try:
    #                 data['title'] = u'Adicionar Institución'
    #                 form = InstitucionProPracticasForm()
    #                 data['idprac'] = request.GET['idprac']
    #                 data['form'] = form
    #                 #data['formuevaluacion'] = ProgramaProceval.objects.filter(estado='A')
    #                 return render(request, 'pra_programaprac/addinstitucion.html', data)
    #             except Exception as ex:
    #                 pass
    #
    #         elif action == 'combo':
    #             try:
    #                 lista_json = []
    #                 listadocar = Coordinacion.objects.get(pk=request.GET['id_coordinacion'])
    #                 listado = listadocar.carrera.all()
    #                 for per in listado:
    #                     per_col = {}
    #                     per_col['nombre'] = per.nombre
    #                     per_col['id'] = per.id
    #                     lista_json.append(per_col)
    #
    #                 listado_periodos = json.dumps(lista_json)
    #                 return HttpResponse(listado_periodos, content_type="application/json")
    #             except Exception as ex:
    #                 pass
    #
    #         elif action == 'listaciudad':
    #             try:
    #                 lista_json = []
    #                 listado = Canton.objects.filter(provincia_id=request.GET['id_provincia'])
    #                 for per in listado:
    #                     per_col = {}
    #                     per_col['nombre'] = per.nombre
    #                     per_col['id'] = per.id
    #                     lista_json.append(per_col)
    #
    #                 listado_periodos = json.dumps(lista_json)
    #                 return HttpResponse(listado_periodos, content_type="application/json")
    #             except Exception as ex:
    #                 pass
    #
    #         elif action == 'listaparroquia':
    #             try:
    #                 lista_json = []
    #                 listado = Parroquia.objects.filter(canton_id=request.GET['id_canton'])
    #                 for per in listado:
    #                     per_col = {}
    #                     per_col['nombre'] = per.nombre
    #                     per_col['id'] = per.id
    #                     lista_json.append(per_col)
    #
    #                 listado_periodos = json.dumps(lista_json)
    #                 return HttpResponse(listado_periodos, content_type="application/json")
    #             except Exception as ex:
    #                 pass
    #
    #         elif action == 'enviar':
    #             try:
    #                 programapra = ProgramaPrapre.objects.get(pk=request.GET['id'])
    #                 programapra.estadoprograma = 'SC'
    #                 programapra.save(request)
    #             except Exception as ex:
    #                 pass
    #
    #         elif action == 'edit':
    #             try:
    #                 data['title'] = u'Modificar Programa'
    #                 programa = ProgramaPrapre.objects.get(pk=request.GET['id'])
    #                 f = ProgramaPrapreForm(initial={'descripcion': programa.descripcion,
    #                                                 'coordinacion': programa.coordinacion,
    #                                                 'carrera': programa.carrera,
    #                                                 'fechaini': programa.fechadesde,
    #                                                 'fechfin': programa.fechahasta,
    #                                                 'objgeneral': programa.objgeneral,
    #                                                 'objespecifico': programa.objespecifico,
    #                                                 'justificacion': programa.justificacion,
    #                                                 'recurso': programa.recurso,
    #                                                 'cronograma': programa.cronograma})
    #                 f.edita(programa.coordinacion_id)
    #                 data['form'] = f
    #                 data['programa'] = programa
    #                 return render(request, 'pra_programaprac/edit.html', data)
    #             except Exception as ex:
    #                 pass
    #
    #         elif action == 'editinstitucion':
    #             try:
    #                 data['title'] = u'Modificar Institución'
    #                 data['idprograma'] = request.GET['idprograma']
    #                 institucion = InstitucionProPracticas.objects.get(pk=request.GET['id'])
    #                 f = InstitucionProPracticasForm(initial={'empresa': institucion.empresa,
    #                                                          'horas': institucion.horas,
    #                                                          'cupos': institucion.cupos})
    #                 # f.edita(institucion.coordinacion_id)
    #                 data['form'] = f
    #                 data['institucion'] = institucion
    #                 return render(request, 'pra_programaprac/editinstitucion.html', data)
    #             except Exception as ex:
    #                 pass
    #
    #         elif action == 'coninstitucion':
    #             try:
    #                 data['title'] = u'Lista de Instituciones'
    #                 data['programa'] = programa = ProgramaPrapre.objects.get(pk=request.GET['id'])
    #                 data['institucion'] = InstitucionProPracticas.objects.filter(programa=programa,estado='A')
    #                 return render(request, 'pra_programaprac/viewinstitucion.html', data)
    #             except Exception as ex:
    #                 pass
    #
    #         elif action == 'estudiantesinscritos':
    #             try:
    #                 data['title'] = u'Lista de Alumnos Inscritos'
    #                 data['idprograma'] = request.GET['idprograma']
    #                 data['inscritoslis'] = InstitucionProPracticas.objects.get(pk=request.GET['id'],estado='A')
    #                 data['inscritos'] = InscripcionProPracticas.objects.filter(institucion=request.GET['id'],estado=True)
    #                 return render(request, 'pra_programaprac/alumnosinscritos.html', data)
    #             except Exception as ex:
    #                 pass
    #
    #         elif action == 'deleteinstitucion':
    #             try:
    #                 data['title'] = u'Eliminar Institución del Programa'
    #                 data['idprograma'] = request.GET['idprograma']
    #                 data['institucion'] = institucion = InstitucionProPracticas.objects.get(pk=request.GET['id'])
    #                 return render(request, 'pra_programaprac/deleteinstitucion.html', data)
    #             except Exception as ex:
    #                 pass
    #
    #         elif action == 'delete':
    #             try:
    #                 data['title'] = u'Eliminar Programa'
    #                 data['programa'] = ProgramaPrapre.objects.get(pk=request.GET['id'])
    #                 return render(request, 'pra_programaprac/delete.html', data)
    #             except Exception as ex:
    #                 pass
    #         return HttpResponseRedirect(request.path)
    #
    #     else:
    #         try:
    #             search = None
    #             valida = None
    #             tipo = None
    #             fechainicio = 0
    #             fechafinal = 0
    #             tipoestado = 1
    #             periodos = ProgramaPrapre.objects.filter(estado='A').all()
    #             if 's' in request.GET:
    #                 search = request.GET['s']
    #                 tipoestado = request.GET['tipoestado']
    #             if search:
    #                 if tipoestado:
    #                     periodos = ProgramaPrapre.objects.filter(descripcion__icontains=search, estadoprograma=tipoestado, estado='A')
    #                 else:
    #                     tipoestado = 1
    #                     periodos = ProgramaPrapre.objects.filter(descripcion__icontains=search, estado='A')
    #
    #             if 'tipoe' in request.GET:
    #                 busquedatipoestado = request.GET['tipoestado']
    #                 tipoestado = request.GET['tipoestado']
    #                 valida = 1
    #                 if busquedatipoestado:
    #                     periodos = ProgramaPrapre.objects.filter(estadoprograma=busquedatipoestado, estado='A')
    #                 else:
    #                     periodos = ProgramaPrapre.objects.filter(estado='A').all()
    #             if 'desc' in request.GET:
    #                 fechainicio = request.GET['fechainicio']
    #                 fechafinal = request.GET['fechafinal']
    #                 tipoestado = request.GET['tipoestado']
    #                 valida = 1
    #                 if tipoestado:
    #                     periodos = ProgramaPrapre.objects.filter(estadoprograma=tipoestado, fechcrea__gte=fechainicio, fechcrea__lte=fechafinal, estado='A')
    #                 else:
    #                     periodos = ProgramaPrapre.objects.filter(fechcrea__gte=fechainicio, fechcrea__lte=fechafinal, estado='A')
    #
    #             paging = MiPaginador(periodos, 25)
    #             p = 1
    #             try:
    #                 paginasesion = 1
    #                 if 'paginador' in request.session:
    #                     paginasesion = int(request.session['paginador'])
    #                 if 'page' in request.GET:
    #                     p = int(request.GET['page'])
    #                 else:
    #                     p = paginasesion
    #                 try:
    #                     page = paging.page(p)
    #                 except:
    #                     p = 1
    #                 page = paging.page(p)
    #             except:
    #                 page = paging.page(p)
    #             request.session['paginador'] = p
    #             data['paging'] = paging
    #             data['rangospaging'] = paging.rangos_paginado(p)
    #             data['page'] = page
    #             data['tipoestado'] = tipoestado
    #             data['fechainicio'] = fechainicio
    #             data['fechafinal'] = fechafinal
    #             data['search'] = search if search else ""
    #             data['v'] = valida if valida else ""
    #             data['programas'] = page.object_list
    #             return render(request, "pra_programaprac/view.html", data)
    #         except Exception as ex:
    #             pass