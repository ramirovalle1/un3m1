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

from certi.funciones import crear_carnet
from certi.models import ConfiguracionCarnet, Carnet
from decorators import secure_module, last_access
from matricula.models import PeriodoMatricula
from mobile.views import make_thumb_picture, make_thumb_fotopersona
from settings import SITE_STORAGE, GENERAR_TUMBAIL
from sga.commonviews import adduserdata
from sga.funciones import log, generar_nombre
from sga.models import Matricula, unicode, FotoPersona
from sga.templatetags.sga_extras import encrypt

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
    if not (perfilprincipal.es_profesor()):
        return HttpResponseRedirect("/?info=Solo los perfiles de docentes  pueden ingresar al modulo.")

    periodo = request.session['periodo']

    if request.method == 'POST':
        action = request.POST['action']
        # if action == 'create':
        #     try:
        #         configuracion_carnet = ConfiguracionCarnet.objects.filter(tipo_perfil=3, tipo=1).first()
        #         if not perfilprincipal.es_profesor():
        #             raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, no tiene asignado un perfil docente")
        #         if not perfilprincipal.perfil_ocupado(2):
        #             raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, su perfil no ocupado")
        #         distributivo = persona.distributivopersona_set.filter(estadopuesto_id=1, regimenlaboral_id=2).first()
        #         if distributivo is None:
        #             raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, no se encuentra en el distributivo")
        #         carnet = Carnet.objects.filter(config=configuracion_carnet, persona=persona, distributivo=distributivo)
        #         if carnet.exists():
        #             raise NameError('Ya existe un carnet digital Creado')
        #         aData = crear_carnet(configuracion_carnet, request, distributivo=distributivo)
        #         if aData['result'] == 'bad':
        #             raise NameError(aData['mensaje'])
        #         return JsonResponse({"result": "ok"})
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": f"Error al generar credencial. {ex.__str__()}"})

        if action == 'delete':
            try:
                configuracion_carnet = ConfiguracionCarnet.objects.filter(tipo_perfil=3, tipo=1).first()
                if not configuracion_carnet.puede_eliminar_carne:
                    raise NameError(u"No se permite eliminar carné administrativo")

                if not Carnet.objects.values('id').filter(pk=int(encrypt(request.POST['id']))).exists():
                    raise NameError(u"No existe carné administrativo a eliminar")
                delete = carne = Carnet.objects.filter(config=configuracion_carnet, persona=persona).first()
                carne.delete()
                log(u'Elimino carné docente: %s' % delete, request, "del")
                return JsonResponse({"result": "ok", "mensaje": "Carné docente eliminado correctamente"})
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
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"La imagen seleccionada no cumple los requisitos. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'cargarfoto':
                try:
                    data['title'] = u'Subir foto'
                    return render(request, "pro_carnet/cargarfoto.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"/?info={ex.__str__()}")

            return HttpResponseRedirect(request.path)
        else:
            try:
                mis_cargos = persona.mis_cargos()

                if not (persona.mi_cargo_administrativo()):
                    raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, no tiene cargo asignado y no se permite carné Docente")

                data['title'] = u'Carné Docente'
                data['configuracion_carnet'] = configuracion_carnet = ConfiguracionCarnet.objects.filter(tipo_perfil=3, tipo=1).first()

                if not perfilprincipal.es_profesor():
                    raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, no tiene asignado un perfil docente")

                distributivo = persona.distributivopersona_set.filter(estadopuesto_id=1, regimenlaboral_id=2).first()
                if distributivo is None:
                    raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, no se encuentra en el distributivo")

                if distributivo.estadopuesto_id != 1:
                    raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, el estado de su puesto no esta activo")

                if distributivo.regimenlaboral_id != 2:
                    raise NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, su régimen laboral no permite carné")

                if configuracion_carnet is None:
                    return NameError(f"Estimad{'a' if persona.sexo_id == 1 else 'o'}, actualmente no hay una configuración  de carné disponible")

                if not persona.foto() and configuracion_carnet.puede_cargar_foto:
                    return HttpResponseRedirect("/pro_carnet?action=cargarfoto")
                carnet = Carnet.objects.filter(config=configuracion_carnet, persona=persona).first()
                with transaction.atomic():
                    try:
                        if carnet is None:
                            result, mensaje, carnet = crear_carnet(configuracion_carnet, request, distributivo=distributivo, perfilusuario_id=perfilprincipal.id)
                            if not result:
                                raise NameError(mensaje)
                    except Exception as exep:
                        transaction.set_rollback(True)
                        raise NameError(exep)
                data['carnet'] = carnet
                return render(request, "pro_carnet/view.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                return render(request, "pro_carnet/error.html", data)
