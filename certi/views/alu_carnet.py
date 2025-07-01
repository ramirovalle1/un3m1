# -*- coding: latin-1 -*-
import os
from datetime import datetime, time
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template import Context

from certi.funciones import crear_carnet_estudiantil, crear_carnet
from certi.models import ConfiguracionCarnet, Carnet
from decorators import secure_module, last_access
from matricula.models import PeriodoMatricula
from mobile.views import make_thumb_picture, make_thumb_fotopersona
from settings import SITE_STORAGE, GENERAR_TUMBAIL
from sga.commonviews import adduserdata
from sga.funciones import log, generar_nombre
from sga.models import Matricula, unicode, FotoPersona


#libreria usadas para convertir html a imagen
# html2image==2.0.1
# pdf2image==1.15.1
# para windows https://github.com/oschwartz10612/poppler-windows/releases
# para linux https://pdf2image.readthedocs.io/en/latest/installation.html#installing-poppler


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    periodo = request.session['periodo']

    if request.method == 'POST':
        action = request.POST['action']
        if action == 'create':
            try:
                if not PeriodoMatricula.objects.values_list('id').filter(status=True, periodo=periodo).exists():
                    raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, el periodo académico <b>{periodo.nombre}</b> no permite carné estudiantil")
                periodomatricula = PeriodoMatricula.objects.filter(status=True, periodo=periodo)
                if periodomatricula.count() > 1:
                    raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, el periodo académico <b>{periodo.nombre}</b> no permite carné estudiantil")
                periodomatricula = periodomatricula[0]
                if not periodomatricula.valida_uso_carnet:
                    raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, el periodo académico <b>{periodo.nombre}</b> no permite carné estudiantil")
                configuracion_carnet = periodomatricula.configuracion_carnet
                if not Matricula.objects.values("id").filter(nivel__periodo=periodo, inscripcion=inscripcion).exists():
                    raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, solo los perfiles de estudiantes matriculados.")
                data['matricula'] = matricula = Matricula.objects.filter(nivel__periodo=periodo, inscripcion=inscripcion)[0]
                carnet = Carnet.objects.filter(config=configuracion_carnet, persona=persona, matricula=matricula)
                if carnet.exists():
                    carnet.delete()
                aData = crear_carnet_estudiantil(matricula, configuracion_carnet, request)
                #aData = crear_carnet(configuracion_carnet, request, matricula=matricula)
                if aData['result'] == 'bad':
                    raise NameError(aData['mensaje'])
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error al generar credencial. {ex.__str__()}"})

        elif action == 'delete':
            try:
                if not PeriodoMatricula.objects.values_list('id').filter(status=True, periodo=periodo).exists():
                    raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, el periodo académico <b>{periodo.nombre}</b> no permite carné estudiantil")
                periodomatricula = PeriodoMatricula.objects.filter(status=True, periodo=periodo)
                if periodomatricula.count() > 1:
                    raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, el periodo académico <b>{periodo.nombre}</b> no permite carné estudiantil")
                periodomatricula = periodomatricula[0]
                if not periodomatricula.valida_uso_carnet:
                    raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, el periodo académico <b>{periodo.nombre}</b> no permite carné estudiantil")
                configuracion_carnet = periodomatricula.configuracion_carnet
                if not Matricula.objects.values("id").filter(nivel__periodo=periodo, inscripcion=inscripcion).exists():
                    raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, solo los perfiles de estudiantes matriculados.")
                data['matricula'] = matricula = Matricula.objects.filter(nivel__periodo=periodo, inscripcion=inscripcion)[0]
                if not Carnet.objects.values('id').filter(config=configuracion_carnet, persona=persona, matricula=matricula).exists():
                    raise NameError(u"No existe carné estudiantil a eliminar")
                delete = carne = Carnet.objects.filter(config=configuracion_carnet, persona=persona, matricula=matricula)[0]
                carne.delete()
                log(u'Elimino carné estudiantil: %s' % delete, request, "del")
                return JsonResponse({"result": "ok", "mensaje": "Carné estudiantil eliminado correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error al eliminar credencial. {ex.__str__()}"})

        if action == 'cargarfoto':
            try:
                if not 'foto' in request.FILES:
                    raise NameError(f"Favor carge una foto")
                fotofile = request.FILES['foto']
                if fotofile.size > 524288:
                    raise NameError(u"Archivo mayor a 500Kb.")
                fotofileod = fotofile._name
                ext = fotofileod[fotofileod.rfind("."):]
                if not ext in ['.jpg']:
                    raise NameError(u"Solo archivo con extensión. jpg.")
                fotofile._name = generar_nombre("foto_", fotofile._name)
                foto = persona.foto()
                if foto:
                    foto.foto = fotofile
                else:
                    foto = FotoPersona(persona=persona, foto=fotofile)
                foto.save(request)
                make_thumb_picture(persona)
                if GENERAR_TUMBAIL:
                    make_thumb_fotopersona(persona)
                log(u'Adicionó foto de persona: %s' % foto, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente la foto')
                if not Matricula.objects.values("id").filter(nivel__periodo=periodo, inscripcion=inscripcion).exists():
                    raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, solo los perfiles de estudiantes matriculados.")
                data['matricula'] = matricula = Matricula.objects.filter(nivel__periodo=periodo, inscripcion=inscripcion)[0]
                return JsonResponse({"result": "ok", "matricula_id": matricula.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"La imagen seleccionada no cumple los requisitos. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'cargarfoto':
                try:
                    # periodomatricula = PeriodoMatricula.objects.filter(status=True, periodo=periodo)
                    # periodomatricula = periodomatricula[0]
                    # if not periodomatricula.valida_uso_carnet:
                    #     raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, el periodo académico <b>{periodo.nombre}</b> no permite carné estudiantil")
                    # data['configuracion_carnet'] = configuracion_carnet = periodomatricula.configuracion_carnet
                    # if persona.foto() and not configuracion_carnet.puede_cargar_foto:
                    #     return HttpResponseRedirect(f"{request.path}?info=Ya tiene registrada una foto")
                    data['matricula'] = matricula = \
                        Matricula.objects.filter(nivel__periodo=periodo, inscripcion=inscripcion)[0]
                    data['title'] = u'Subir foto'
                    return render(request, "alu_carnet/cargarfoto.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"/?info={ex.__str__()}")

            if action == 'cargarfotodip':
                try:
                    data['matricula'] = matricula = Matricula.objects.filter(nivel__periodo=periodo, inscripcion=inscripcion)[0]
                    data['title'] = u'Subir foto'
                    return render(request, "alu_carnet/cargarfotodip.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"/?info={ex.__str__()}")

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Carné estudiantil'
                if periodo.tipo_id not in [3,4]:
                    if not PeriodoMatricula.objects.values_list('id').filter(status=True, periodo=periodo).exists():
                        raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, el periodo académico <b>{periodo.nombre}</b> no permite carné estudiantil")
                    periodomatricula = PeriodoMatricula.objects.filter(status=True, periodo=periodo)
                    if periodomatricula.count() > 1:
                        raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, el periodo académico <b>{periodo.nombre}</b> no permite carné estudiantil")
                    periodomatricula = periodomatricula[0]
                    if not periodomatricula.valida_uso_carnet:
                        raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, el periodo académico <b>{periodo.nombre}</b> no permite carné estudiantil")
                    data['configuracion_carnet'] = configuracion_carnet = periodomatricula.configuracion_carnet
                    if not persona.foto() and configuracion_carnet.puede_cargar_foto:
                        HttpResponseRedirect("/alu_carnet?action=cargarfoto")
                    if not Matricula.objects.values("id").filter(nivel__periodo=periodo, inscripcion=inscripcion).exists():
                        raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, solo los perfiles de estudiantes matriculados.")
                    data['matricula'] = matricula = Matricula.objects.filter(nivel__periodo=periodo, inscripcion=inscripcion)[0]
                    carnet = None
                    if Carnet.objects.values('id').filter(config=configuracion_carnet, persona=persona, matricula=matricula).exists():
                        # return HttpResponseRedirect(f"{request.path}?action=create")
                        carnet = Carnet.objects.filter(config=configuracion_carnet, persona=persona, matricula=matricula)[0]
                    data['carnet'] = carnet
                    return render(request, "alu_carnet/view.html", data)
                else:
                    data['matricula'] = matricula = Matricula.objects.filter(nivel__periodo=periodo, inscripcion=inscripcion)[0]
                    return render(request, "alu_carnet/viewposgrado.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                return render(request, "alu_carnet/error.html", data)
