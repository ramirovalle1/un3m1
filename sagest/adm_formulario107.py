# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from datetime import datetime, timedelta
from decorators import secure_module
from sagest.forms import Formulario107Form, ImportarFormulario107Form
from sagest.models import Formulario107
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre
from sga.models import Persona
import io
import xlsxwriter


def rango_anios():
    if Formulario107.objects.exclude(anio=0).exists():
        inicio = Formulario107.objects.exclude(anio=0).order_by('anio')[0].anio
        fin = Formulario107.objects.exclude(anio=0).order_by('-anio')[0].anio
        return range(fin, inicio - 1, -1)
    return [datetime.now().date().year]

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
# @secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = Formulario107Form(request.POST, request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 3145728:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 3 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf' or ext == '.PDF':
                                newfile._name = generar_nombre("formulario_", newfile._name)
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf"})
                if f.is_valid():
                    if not Formulario107.objects.filter(persona_id=f.cleaned_data['persona'],anio=f.cleaned_data['anio']).exists():
                        formulario = Formulario107(persona_id=f.cleaned_data['persona'],
                                                   anio=f.cleaned_data['anio'],
                                                   archivo=newfile)
                        formulario.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Registro Repetido."})
                    log(u'Ingreso Formulario 107 : %s' % formulario, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                formulario = Formulario107.objects.get(pk=request.POST['id'])
                f = Formulario107Form(request.POST, request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 3145728:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 3 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf' or ext == '.PDF':
                                newfile._name = generar_nombre("formulario_", newfile._name)
                            else:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf"})
                if f.is_valid():
                    formulario.archivo = newfile
                    formulario.save(request)
                    log(u'Editó Formulario 107 : %s' % formulario, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delete':
            try:
                formulario = Formulario107.objects.get(pk=request.POST['id'])
                log(u'Eliminó Formulario 107 : %s' % formulario, request, "del")
                formulario.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'importar':
            try:
                form = ImportarFormulario107Form(request.POST, request.FILES)
                if form.is_valid():
                    ficheros = request.FILES.getlist('myfile')
                    if ficheros:
                        for archivo in ficheros:
                            nombre = (archivo._name.split('.')[0]).split('-')[2]
                            persona = Persona.objects.filter(status=True, cedula=nombre)
                            if persona:
                                persona_aux=persona[0]
                                if not Formulario107.objects.filter(anio=form.cleaned_data['anio'], status=True, persona=persona_aux).exists():
                                    formulario = Formulario107(archivo=archivo,
                                                               anio=form.cleaned_data['anio'],
                                                               persona=persona[0])
                                    formulario.save(request)
                                else:
                                    formulario = Formulario107.objects.get(anio=form.cleaned_data['anio'], status=True, persona=persona_aux)
                                    formulario.archivo=archivo
                                    formulario.save(request)
                            else:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": "bad", "mensaje": u"Número de cedula no existe %s" % nombre})
                    log(u'Importar Formulario 107: %s' % formulario, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al editar los datos."})
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Formulario 107'
                    form = Formulario107Form()
                    data['form'] = form
                    return render(request, 'adm_formulario107/add.html', data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Modificar Formulario 107'
                    data['formulario'] = formulario = Formulario107.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(formulario)
                    form = Formulario107Form(initial=initial)
                    form.editar(formulario)
                    data['form'] = form
                    return render(request, 'adm_formulario107/edit.html', data)
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    data['title'] = u'Eliminar Formulario 107'
                    data['formulario'] = Formulario107.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_formulario107/delete.html', data)
                except Exception as ex:
                    pass

            elif action == 'importar':
                try:
                    data['title'] = u'Importar Formulario 107'
                    form = ImportarFormulario107Form()
                    data['form'] = form
                    return render(request, "adm_formulario107/importar.html", data)
                except Exception as ex:
                    pass

            elif action == 'reporte':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('salidas')
                    ws.set_column(0, 0, 20)
                    ws.set_column(1, 1, 40)
                    ws.set_column(2, 2, 10)
                    ws.set_column(3, 3, 60)

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#EBF5FB'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.write(0, 0, 'CEDULA', formatoceldacab)
                    ws.write(0, 1, 'ESTUDIANTE', formatoceldacab)
                    ws.write(0, 2, 'ANIO', formatoceldacab)
                    ws.write(0, 3, 'ARCHIVO', formatoceldacab)

                    anio = int(request.GET['anio'])

                    persona = Persona.objects.filter(status=True).values_list('id', flat=True)
                    formulario107 = Formulario107.objects.filter(status = True, anio = anio, persona__in = persona)

                    filas_recorridas = 2
                    for formulario in formulario107:
                        ws.write('A%s' % filas_recorridas, str(formulario.persona.cedula), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(formulario.persona.nombres + ' ' +formulario.persona.apellido1 + ' ' +formulario.persona.apellido2), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, int(formulario.anio), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, 'https://sga.unemi.edu.ec/media/'+ str(formulario.archivo), formatoceldaleft)

                        filas_recorridas += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'ReporteFormulario107.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Mantenimiento Formulario 107'
                search = None
                ids = None
                data['anios'] = anios = rango_anios()
                anioselect = anios[0]
                if 'anio' in request.GET:
                    anioselect = int(request.GET['anio'])

                if 's' in request.GET:
                    search = request.GET['s']
                    formularios = Formulario107.objects.filter(Q(persona__nombres__icontains=search) |
                                                             Q(persona__cedula__icontains=search) |
                                                             Q(persona__apellido1__icontains=search) |
                                                             Q(persona__apellido2__icontains=search), status=True, anio=anioselect)
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    formularios = Formulario107.objects.filter(id=ids)
                else:
                    formularios = Formulario107.objects.filter(status=True, anio=anioselect)
                data['anioselect']=anioselect

                paging = MiPaginador(formularios, 25)
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
                data['formularios'] = page.object_list
                return render(request, "adm_formulario107/view.html", data)
            except Exception as ex:
                pass