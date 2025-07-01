# -*- coding: UTF-8 -*-
from django.contrib import messages
from django.contrib.admin.models import LogEntry, ADDITION, DELETION
from django.contrib.admin.utils import unquote
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction, router
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.encoding import force_str

from bd.models import LogQuery, get_deleted_objects, LogEntryLogin
from decorators import secure_module
from bd.forms import *
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery, convertir_fecha, \
    resetear_clave, variable_valor
from sga.models import VariablesGlobales, TIPOS_PARAMETRO_VARIABLE
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    #
    # try:
    #     puede_realizar_accion(request, 'bd.puede_acceder_variables_globales')
    # except Exception as ex:
    #     return HttpResponseRedirect(f"/?info={ex.__str__()}")
    adduserdata(request, data)
    persona = request.session['persona']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'loadDataTable':
            try:
                txt_filter = request.POST['sSearch'] if request.POST['sSearch'] else ''
                limit = int(request.POST['iDisplayLength']) if request.POST['iDisplayLength'] else 25
                offset = int(request.POST['iDisplayStart']) if request.POST['iDisplayStart'] else 0
                type = int(request.POST['type']) if request.POST['type'] else 0
                tCount = 0
                variables = VariablesGlobales.objects.filter()
                if txt_filter:
                    search = txt_filter.strip()
                    variables = variables.filter(Q(referencia__icontains=search) | Q(descripcion__icontains=search) | Q(variable__icontains=search))
                if type > 0:
                    variables = variables.filter(tipodato=type)
                tCount = variables.count()
                if offset == 0:
                    rows = variables[offset:limit]
                else:
                    rows = variables[offset:offset + limit]
                aaData = []
                for row in rows:
                    valor = None
                    if row.tipodato == 1:
                        valor = row.valor
                    elif row.tipodato == 2:
                        valor = int(row.valor)
                    elif row.tipodato == 3:
                        valor = float(row.valor)
                    elif row.tipodato == 4:
                        valor = row.valor.lower() in ("yes", "true", "t", "1", "si")
                    elif row.tipodato == 5:
                        valor = convertir_fecha(row.valor)
                    elif row.tipodato == 6:
                        valor = row.valor.split(',')
                    aaData.append([row.id,
                                   {
                                       "referencia": row.referencia,
                                       "descripcion": row.descripcion,
                                   },
                                   row.variable,
                                   {
                                       "valor": valor,
                                       "tipo": row.tipodato,
                                       "tipo_verbose": row.get_tipodato_display(),

                                   },
                                   {
                                       "id": row.id,
                                       "name": row.referencia,
                                       "tipo": row.tipodato,
                                   },
                                   ])
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        if action == 'saveVariableGlobal':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] and int(request.POST['id']) != 0 else None
                typeForm = 'edit' if id else 'new'
                t_var = int(request.POST['tipodato']) if 'tipodato' in request.POST and request.POST['tipodato'] else None
                if t_var is None:
                    raise NameError(u"Tipo de dato de la variable no identificada")
                f = VariablesGlobalesForm(request.POST)
                f.set_type_form(t_var)
                if not f.is_valid():
                    # [(k, v[0]) for k, v in f.errors.items()]
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                valor = None
                valor = f.cleaned_data[f'valor_{t_var}']
                if t_var == 5:
                    # valor = convertir_fecha(valor)
                    valor = valor.strftime("%d-%m-%Y")
                if valor is None:
                    raise NameError(u"Valor de la variable")
                valor = str(valor) if not valor is str else valor

                if typeForm == 'new':
                    puede_realizar_accion(request, 'bd.puede_agregar_variable_global')
                    eVariable = VariablesGlobales(referencia=f.cleaned_data['referencia'],
                                                  descripcion=f.cleaned_data['descripcion'],
                                                  variable=f.cleaned_data['variable'],
                                                  tipodato=t_var,
                                                  valor=valor)
                    eVariable.save(request)
                    log(u'Agrego variable global: %s' % eVariable, request, "add")
                else:
                    puede_realizar_accion(request, 'bd.puede_modificar_variable_global')
                    if not VariablesGlobales.objects.filter(pk=id).exists():
                        raise NameError(u"No existe formulario a editar")
                    eVariable = VariablesGlobales.objects.get(pk=id)
                    eVariable.referencia = f.cleaned_data['referencia']
                    eVariable.descripcion = f.cleaned_data['descripcion']
                    eVariable.variable = f.cleaned_data['variable']
                    eVariable.tipodato = t_var
                    eVariable.valor = valor
                    eVariable.save(request)
                    log(u'Edito variable global: %s' % eVariable, request, "edit")

                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente el registro"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar. %s" % ex.__str__()})

        if action == 'delete':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_variable_global')
                if not 'id' in request.POST or not request.POST['id']:
                    raise NameError(u"No se encontro registro a eliminar")
                object_id = int(request.POST['id'])
                if not VariablesGlobales.objects.filter(pk=object_id).exists():
                    raise NameError(u"No se encontro registro a eliminar")
                delete = eVariable = VariablesGlobales.objects.get(pk=object_id)
                eVariable.delete()
                log(u'Elimino variable global: %s' % delete, request, "del")
                return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente la variable"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar la variable. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'loadForm':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    t_var = int(request.GET['t_var']) if 't_var' in request.GET and request.GET['t_var'] and int(request.GET['t_var']) in [1,2,3,4,5,6] else 0
                    if t_var == 0:
                        raise NameError(u"No se encontro el tipo de variable")
                    data['t_var'] = t_var
                    f = VariablesGlobalesForm()
                    f.set_type_form(t_var)
                    eVariablesGlobales = None
                    id = 0
                    if typeForm in ['edit', 'view']:
                        id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                        if not VariablesGlobales.objects.filter(pk=id).exists():
                            raise NameError(u"No existe formulario a editar")
                        eVariablesGlobales = VariablesGlobales.objects.get(pk=id)
                        f.set_initial(eVariablesGlobales)
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_variable_global')
                    else:
                        puede_realizar_accion(request, 'bd.puede_agregar_variable_global')
                    data['eVariablesGlobales'] = eVariablesGlobales
                    data['form'] = f
                    data['frmName'] = "frmVariablesGlobales"
                    data['id'] = id
                    template = get_template("adm_sistemas/global_variables/frm.html")
                    json_content = template.render(data)

                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Administración de Variables Globales del Sistema'
                data['tipos'] = TIPOS_PARAMETRO_VARIABLE
                return render(request, "adm_sistemas/global_variables/view.html", data)
            except Exception as ex:
                pass
