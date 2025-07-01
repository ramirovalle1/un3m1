from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.funciones import log
from sga.models import RegistrarIngresoCrai, ActividadesCrai, RegistrarActividadesCrai


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()

def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['periodo'] = periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'add':
            try:
                if RegistrarActividadesCrai.objects.filter(registraringresocrai_id=int(request.POST['id']), actividadescrai_id=int(request.POST['ida'])).exists():
                    return JsonResponse({"result": "bad", "mensaje": "Actividad ya seleccionada."})
                reg = RegistrarActividadesCrai(registraringresocrai_id=int(request.POST['id']),
                                               actividadescrai_id=int(request.POST['ida']))
                reg.save(request)
                log(u'Adicionó una actividad al CRAI UNEMI: %s' % reg, request, "add")
                return JsonResponse({"result": "ok", "mensaje": u'Se registro correctamente...'})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Registrar Actividad CRAI Biblioteca'
                    data['registroid'] = int(request.GET['idr'])
                    data['actividaid'] = int(request.GET['ida'])
                    data['ci'] = request.GET['ci']
                    return render(request, "adm_crai_actividades/add.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Control de actividades al CRAI UNEMI'
            try:
                search=''
                data['visita'] = []
                fecha = datetime.now().today()
                if 'ci' in request.GET:
                    search = request.GET['ci'].strip()
                    visita = RegistrarIngresoCrai.objects.filter((Q(persona__cedula__icontains=search) |
                                                                   Q(inscripcion__persona__cedula__icontains=search)),fecha=fecha, tiposerviciocrai__id=1)
                    if visita:
                        data['visita'] = visita.order_by('fecha')[0]
                    else:
                        data['visita'] = []
                data['actividadescrais'] = ActividadesCrai.objects.filter(status=True).order_by('orden')
                data['search'] = search
                return render(request, "adm_crai_actividades/view.html", data)
            except Exception as ex:
                pass


