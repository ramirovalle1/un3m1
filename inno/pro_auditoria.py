# -*- coding: UTF-8 -*-
import sys
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from decorators import secure_module
from sga.commonviews import adduserdata
from django.shortcuts import render, redirect
from .forms import AuditoriaInformaticaForm
from .models import Auditoria
from django.utils import timezone
from django.template.loader import get_template
from sga.funciones import log
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()

def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['title']= u'Auditorías'

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'addsolicitud':
                try:
                    form = AuditoriaInformaticaForm(request.POST, request.FILES)
                    if form.is_valid():
                        detalle= form.cleaned_data['detalle']
                        observacion = form.cleaned_data['observacion']
                        fecha= timezone.now()
                        evidencia = None
                        if 'evidencia' in request.FILES:
                            evidencia = request.FILES['evidencia']
                        auditoria = Auditoria(
                            detalle = detalle,
                            observaciones = observacion,
                            fecha= fecha,
                            persona= persona,
                            evidencia = evidencia
                        )
                        auditoria.save()
                        log('Adiciono un requerimiento de auditoria: %s' %auditoria,request,"add")
                        return JsonResponse({"result":"ok"})
                    else:
                        return JsonResponse({"result":"bad"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    line_eer = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    print(f"Error: {ex.__str__()}. {line_eer}")
                    pass
            if action == 'editsolicitud':
                try:
                    form = AuditoriaInformaticaForm(request.POST, request.FILES)
                    id = int(encrypt(request.POST['id']))
                    if form.is_valid():
                        detalle = form.cleaned_data['detalle']
                        observacion = form.cleaned_data['observacion']
                        fecha = timezone.now()
                        evidencia = None
                        if 'evidencia' in request.FILES:
                            evidencia = request.FILES['evidencia']
                        auditoria = Auditoria.objects.get(pk=id)
                        """auditoria = Auditoria(
                            detalle=detalle,
                            observaciones=observacion,
                            fecha=fecha,
                            persona=persona,
                            evidencia=evidencia
                        )"""
                        auditoria.detalle = detalle
                        auditoria.observaciones = observacion
                        auditoria.evidencia = evidencia
                        auditoria.fecha=fecha
                        auditoria.save()
                        log('Edito un requerimiento de auditoria: %s' % auditoria, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result":"bad"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    line_eer = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    print(f"Error: {ex.__str__()}. {line_eer}")
                    pass
            if action == 'deletesolicitud':
                try:
                    id = int(request.POST['id'])
                    auditoria = Auditoria.objects.get(pk=id)
                    auditoria.delete()
                    log('Elimino un requerimiento de auditoria: %s' %auditoria,request,"add")
                    return JsonResponse({"result":"ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    line_eer = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    print(f"Error: {ex.__str__()}. {line_eer}")
                    pass
        return redirect('/pro_auditoria')
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'addsolicitud':
                try:
                    data['form']= AuditoriaInformaticaForm()
                    template = get_template("pro_auditoria/addsolicitud.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    line_eer = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    print(f"Error: {ex.__str__()}. {line_eer}")
                    pass
            if action == 'editsolicitud':
                try:
                    id = int(encrypt(request.GET['id']))
                    auditoria = Auditoria.objects.get(id=id)
                    data['form'] = AuditoriaInformaticaForm(
                        initial={
                            'detalle':auditoria.detalle,
                            'observacion':auditoria.observaciones,
                            'evidencia':auditoria.evidencia
                        }
                    )
                    data['id']= encrypt(int(id))
                    template = get_template("pro_auditoria/editsolicitud.html")
                    #return render(request,"pro_auditoria/editsolicitud.html",data)
                    return JsonResponse({"result":True,"data":template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    line_eer = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    print(f"Error: {ex.__str__()}. {line_eer}")
                    pass
            if action == 'deletesolicitud':
                try:
                    data['id']= int(encrypt(request.GET['id']))
                    template = get_template("pro_auditoria/deletesolicitud.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    line_eer = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    print(f"Error: {ex.__str__()}. {line_eer}")
                    pass
        else:
            if Auditoria.objects.filter(persona=persona).exists():
                data['registros'] = Auditoria.objects.filter(persona=persona).order_by('fecha_creacion')
                data['ultimo'] = Auditoria.objects.filter(persona=persona).latest('fecha_creacion')

            return render(request, 'pro_auditoria/view.html', data)