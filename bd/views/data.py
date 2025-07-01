# -*- coding: UTF-8 -*-
from django.contrib import messages
from django.contrib.admin.utils import unquote
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.db import transaction, router
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.encoding import force_str

from bd.models import LogQuery, get_deleted_objects, TemplateBaseSetting
from decorators import secure_module
from bd.forms import *
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery, convertir_fecha
from sga.models import *
from sagest.models import *
from matricula.models import *
from soap.models import *
from feria.models import *
from inno.models import *
from med.models import *
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']

    if request.method == 'POST':
        action = request.POST['action']

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'deleteView':
                try:
                    if not 'id' in request.GET or not request.GET['id']:
                        raise NameError(u"No se encontro registro a eliminar")
                    object_id = int(request.GET['id'])
                    if not 'model' in request.GET or not request.GET['model']:
                        raise NameError(u"No se encontro registro a eliminar")
                    m = request.GET['model']
                    model = eval(m)
                    if not model.objects.filter(pk=object_id).exists():
                        raise NameError(u"No se encontro registro a eliminar")
                    e = model.objects.get(pk=object_id)
                    opts = e._meta
                    if not 'app_label' in request.GET or not request.GET['app_label']:
                        app_label = opts.app_label
                    else:
                        app_label = request.GET['app_label']
                    if 'permission' in request.GET and request.GET['permission']:
                        puede_realizar_accion(request, ('%s.%s' % (app_label, request.GET['permission'])))
                    obj = e
                    using = router.db_for_write(e)
                    object_name = force_str(opts.verbose_name)
                    (deleted_objects, model_count, perms_needed, protected) = get_deleted_objects([obj], using)
                    data = dict(
                        object_id=object_id,
                        object_name=object_name,
                        object=e,
                        deleted_objects=deleted_objects,
                        model_count=dict(model_count).items(),
                        perms_lacking=perms_needed,
                        protected=protected,
                        persona=persona
                    )
                    template = get_template("ajaxdeletedinamic.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Administración de Usuarios del Sistema'
                # users = User.objects.filter().order_by('username')
                return render(request, "adm_sistemas/users/view.html", data)
            except Exception as ex:
                pass
