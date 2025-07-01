# -*- coding: UTF-8 -*-

from django.contrib.auth.decorators import login_required
from django.db import transaction
import json
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template import RequestContext

from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador
# from sga.models import ProgramaPrapre, ProgramaProceval, InstitucionProPracticas,InscripcionProPracticas
# from sga.forms import  InstitucionProPracticasForm
# from sga.funcionesxhtml2pdf import conviert_html_to_pdf


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {'title': u'Instituciones'}
    adduserdata(request, data)
    # persona = request.session['persona']
    # if request.method == 'POST':
    #     action = request.POST['action']
    #     if action == 'pdf':
    #         try:
    #             data = {}
    #             adduserdata(request, data)
    #             data['prainscripcion'] = InscripcionProPracticas.objects.get(pk=request.POST['id'])
    #             return conviert_html_to_pdf(
    #                 'pra_profesionalesinscripcion/solicitudinscripcion_pdf.html',
    #                 {
    #                     'pagesize': 'A4',
    #                     'listadoinscritos': data,
    #                 }
    #             )
    #         except Exception as ex:
    #             pass
    #
    #     if action == 'addregistro':
    #         try:
    #             ingresoinscripcion = InscripcionProPracticas(institucion_id=int(request.POST['idinstitucion']),
    #                                                          inscripcion_id=int(request.POST['idinscripcion']))
    #             ingresoinscripcion.save(usuario=request.user)
    #             return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
    #         except Exception as ex:
    #             transaction.set_rollback(True)
    #             return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al obtener los datos."}), content_type="application/json")
    #
    #     if action == 'addinscripcion':
    #         try:
    #             idinstitucion = request.POST['id']
    #             institucion = InstitucionProPracticas.objects.get(pk=request.POST['id'])
    #             perfilprincipal = request.session['perfilprincipal']
    #             inscripcion = perfilprincipal.inscripcion
    #             return HttpResponse(json.dumps({"result": "ok", 'institucion': institucion.empresa.nombre, 'idinstitucion': institucion.id, 'idinscripcion': inscripcion.id}), content_type="application/json")
    #         except Exception as ex:
    #             transaction.set_rollback(True)
    #             return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al obtener los datos."}), content_type="application/json")
    #
    #     return HttpResponse(json.dumps({"result": "bad", "mensaje": "Solicitud Incorrecta."}), content_type="application/json")
    #
    # else:
    #     if 'action' in request.GET:
    #         action = request.GET['action']
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
    #             perfilprincipal = request.session['perfilprincipal']
    #             inscripcion = perfilprincipal.inscripcion
    #             periodos = InstitucionProPracticas.objects.filter(estado='A',programa__coordinacion=inscripcion.coordinacion).all()
    #             if InscripcionProPracticas.objects.filter(inscripcion=inscripcion,estado=True):
    #                 estudianteinscrito = InscripcionProPracticas.objects.get(inscripcion=inscripcion,estado=True)
    #             else:
    #                 estudianteinscrito = 0
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
    #                 if 'page' in request.GET:
    #                     p = int(request.GET['page'])
    #                 page = paging.page(p)
    #             except:
    #                 page = paging.page(p)
    #             data['paging'] = paging
    #             data['rangospaging'] = paging.rangos_paginado(p)
    #             data['page'] = page
    #             data['estudianteinscrito'] = estudianteinscrito
    #             data['search'] = search if search else ""
    #             data['v'] = valida if valida else ""
    #             data['instituiones'] = page.object_list
    #             return render(request, "pra_profesionalesinscripcion/view.html", data)
    #         except Exception as ex:
    #             pass