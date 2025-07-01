# -*- coding: UTF-8 -*-
import json
import sys
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
# from faceid.backEnd import FaceRecognition
from faceid.models import PersonTrainFace
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
from django.template.loader import get_template

from sga.funciones import log, MiPaginador
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    # print("ENTRE AL FACE ID")
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'to_train':
            try:
                if PersonTrainFace.objects.values("id").filter(persona=persona).exists():
                    raise NameError(f"{'Estimada' if persona.es_mujer() else 'Estimado'} {persona.__str__()}, ya se encuentra su rostro facial entrenado")
                eFaceRecognition = FaceRecognition()
                resultFaceDetect, msgFaceDetect = eFaceRecognition.faceDetect(request, persona)
                if not resultFaceDetect:
                    raise NameError(msgFaceDetect)
                resultTrainFace, msgTrainFace = eFaceRecognition.trainFace(request, persona)
                if not resultTrainFace:
                    raise NameError(msgTrainFace)
                ePersonTrainFace = PersonTrainFace(persona=persona,
                                                   activo=True,
                                                   fechahora=datetime.now())
                ePersonTrainFace.save(request)
                # log(u'Recocimiento facial de %s' % ePersonTrainFace.__str__(), request, "add")
                return JsonResponse({"result": "ok", "mensaje": f"{'Estimada' if persona.es_mujer() else 'Estimado'} {persona.__str__()}, se ha completado exitosamente el entrenamiento facial"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los datos. {ex.__str__()}"})
        elif action == 'delete':
            try:
                ePersonTrainFace = PersonTrainFace.objects.get(pk=int(request.POST['id']))
                ePersonTrainFace.delete()
                eFaceRecognition = FaceRecognition()
                resultTrainFace, msgTrainFace = eFaceRecognition.trainFace(request, persona)
                if not resultTrainFace:
                    raise NameError(msgTrainFace)
                # log(u'Eliminó reconocimiento facial: %s' % ePersonTrainFace, request, "del")
                return JsonResponse({"result": "ok", "mensaje": f"{'Estimada' if persona.es_mujer() else 'Estimado'} {persona.__str__()}, se ha completado exitosamente la eliminación facial"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error al eliminar los datos. {ex.__str__()}"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'to_train':
                try:
                    data['title'] = 'Entrenar mi Reconocimiento facial'
                    if PersonTrainFace.objects.values("id").filter(persona=persona).exists():
                        raise NameError(f"{'Estimada' if persona.es_mujer() else 'Estimado'} {persona.__str__()}, ya se encuentra su rostro facial entrenado")
                    return render(request, "my_faceid/to_train.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/my_faceid?info={ex.__str__()}")
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Gestionar mi Reconocimiento facial'
                ePersonTrainFaces = PersonTrainFace.objects.filter(persona=persona)
                filtros, s, url_vars = Q(status=True), request.GET.get('s',''), ''
                data['count'] = ePersonTrainFaces.filter(filtros).values('id').count()
                paging = MiPaginador(ePersonTrainFaces.filter(filtros).order_by('-id'), 10)
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
                data['page'] = page
                data['rangospaging'] = paging.rangos_paginado(p)
                data['ePersonTrainFaces'] = page.object_list
                return render(request, "my_faceid/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f"/?info={ex.__str__()}")
