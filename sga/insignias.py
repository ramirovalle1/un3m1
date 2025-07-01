from decorators import secure_module, last_access
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection, connections
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from sga.commonviews import adduserdata
from sga.models import Insignia, InsigniaPersona, CategoriaInsignia, TIPO_INSIGNIA, Graduado


@login_required()
# @secure_module()
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema = request.build_absolute_uri('/')[:-1].strip("/")
    if request.method == 'POST':
        action = request.POST['action']
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
        else:
            es_posgrado = False
            if 'coordinacion' in request.session:
                coordinacion = request.session['coordinacion']
                if coordinacion == 7:
                    es_posgrado  = True

            data['title'] = u'Insignias conseguidas'
            data['insignias'] = insignia = InsigniaPersona.objects.filter(status=True,persona = persona)
            data['insigniassindes'] = Insignia.objects.filter(status=True).exclude(id__in = insignia.values_list('insignia__id',flat=True))
            data['tipoinsignia'] = TIPO_INSIGNIA
            if es_posgrado:
                graduado = Graduado.objects.filter(
                    status=True, inscripcion__persona=persona,
                    namehtmltitulo__isnull=False,
                    inscripcion__carrera__coordinacion__id=7,
                    fecharefrendacion__isnull=False,
                    fecharefrendacion__year__gte=2022,urlhtmltitulo__isnull=False,rutapdftitulo__isnull=False)
                data['graduado'] = graduado
            return render(request,'insignias/view.html',data)
