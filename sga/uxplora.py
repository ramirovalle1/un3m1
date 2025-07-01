import json
import os
import sys
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction, connections
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render

from bd.models import InventarioOpcionSistema
from decorators import secure_module, last_access
from sagest.models import OpcionSistema
from sga.commonviews import adduserdata
from sga.funciones import calcula_edad
from sga.models import Modulo, Matricula, PerfilInscripcion
from sga.models import ModuloGrupo

import base64
from settings import SITE_STORAGE



@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
# @last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['personasesion'] = persona = request.session['persona']
    periodo = request.session['periodo']
    gruposuser = request.session['grupos_usuarios']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'guardaimg':
            try:
                textoerror = None
                if not 'id' in request.POST:
                    raise NameError('not id')

                if not 'image' in request.POST:
                    raise NameError('not imagen')

                if request.POST.get('posicionclickinicio') is None:
                    textoerror = f'\n Por favor realice el movimiento del mouse hacia la opción indicada \n'
                    raise NameError(f'\n No se ha detectado movimiento del mouse \n')

                id_opcion = int(request.POST['id'])
                modulo = InventarioOpcionSistema.objects.get(id=id_opcion)
                id_modulo = modulo.modulo.id
                archivo_base64 = request.POST.get('image')
                formato, archivo_datos = archivo_base64.split(';base64,')
                extension = formato.split('/')[-1]
                imagen_binaria = base64.b64decode(archivo_datos)
                imagen_binaria = base64.b64encode(imagen_binaria).decode('utf-8')
                url = modulo.url
                userid = request.user.id
                usuario_sga = request.user.username
                perfil_id = request.session['perfilprincipal'].id
                perfil = request.session['perfilprincipal']
                perfiltipo = 1 if perfil.es_estudiante() else (2 if perfil.es_profesor() else 3)
                perfilnombre = request.session['perfilprincipal'].__str__()

                nombreperiodo = periodo.nombre
                periodo_id = periodo.id
                nse = None
                matricula = None
                eInscripcion = None
                inscripcion = None
                carrera = None
                facultad = None
                nivel_id = None
                nivelnombre = None

                ### Datos Estudiante
                if persona.es_estudiante():
                    if perfil.es_estudiante():
                        eInscripcion = perfil.inscripcion
                        inscripcion = eInscripcion.id
                        carrera = eInscripcion.carrera.nombre if eInscripcion.carrera else None
                        facultad = eInscripcion.carrera.mi_coordinacion() if eInscripcion.carrera else None
                        eMatricula = eInscripcion.matricula_periodo(periodo)
                        matricula = eMatricula.id if eMatricula else None
                        nivel_id = eMatricula.nivel_id if eMatricula.nivel else None
                        nivelnombre = eMatricula.nivelmalla.nombre if eMatricula.nivelmalla else None
                        if eMatricula.matriculagruposocioeconomico_set.values('id').filter(status=True).exists():
                            nse = eMatricula.matriculagruposocioeconomico_set.filter(status=True)[0].gruposocioeconomico.nombre

                if perfil.es_profesor():
                    eDocente = perfil.profesor
                    facultad = eDocente.coordinacion.nombre if eDocente.coordinacion else None

                #Datos Usuario
                nombremodulo = modulo.modulo.nombre
                nombreopcion = modulo.nombre
                nombres = persona.nombre_completo()
                identificacion = persona.cedula if persona.cedula else persona.pasaporte
                fechanacimiento = persona.nacimiento.strftime('%Y-%m-%d %H:%M:%S')
                edad = calcula_edad(persona.nacimiento)
                pais = persona.pais.nombre
                provincia = persona.provincia.nombre
                canton = persona.canton.nombre
                sexo = persona.sexo.nombre
                lgtbi = persona.lgtbi
                discapacidad = None
                etnia = None
                if PerfilInscripcion.objects.filter(persona_id=persona.id, status=True).exists():
                    ePerfilInscripcion = PerfilInscripcion.objects.get(persona_id=persona.id, status=True)
                    discapacidad = ePerfilInscripcion.tipodiscapacidad.nombre if ePerfilInscripcion.tipodiscapacidad else None
                    etnia = ePerfilInscripcion.raza.nombre if ePerfilInscripcion.raza else None


                imagen_path = modulo.archivo.path
                fecha_ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                idtrack = None

                valorencuesta = True if int(request.POST.get('valorencuesta', 0)) == 1 else False
                valordificultad = int(request.POST.get('valordificultad', 0))
                posiciones_inicio = json.loads(request.POST.get('posicionclickinicio'))
                posicionclicinicio_x = posiciones_inicio['x']
                posicionclicinicio_y = posiciones_inicio['y']
                posiciones_fin = json.loads(request.POST.get('posicionclickfin'))
                posicionclicxfin = posiciones_fin['x']
                posicionclicyfin = posiciones_fin['y']
                tiempo = timedelta(seconds=float(request.POST.get('tiempotranscurrido', 0)))

                with open(imagen_path, "rb") as image_file:
                    encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

                with transaction.atomic():
                    try:
                        conexion = connections['uxplora']
                        cursor = conexion.cursor()
                        sql = """INSERT INTO mousetrackapp_logmousetrack (
                            status, nombres, identificacion, pais, provincia, canton,
                            sexo, nombremodulo, nombreopcion, imagen, fecha_creacion, imagen_calor,
                            url, userid, usuario_sga, perfil_id, perfil, perfiltipo, matricula, nivelid, nivelnombre, carrera, facultad,
                            fechanacimiento, edad, nombreperiodo, nse,
                            etnia, tipodiscapacidad, periodo_id, inscripcion, idmodulo,idopcion, fechainteraccion, lgtbi, 
                            encontroopcion, escaladifilcultad, posicionclicxinicio, posicionclicxfin, posicionclicyinicio, posicionclicyfin,tiempointeraccion 
                        ) VALUES (
                             %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s ,%s, %s ,%s,
                            %s, %s, %s ,%s, %s ,%s, %s, %s
                        );"""

                        valores = (
                            True, nombres, identificacion, pais, provincia, canton,
                            sexo, nombremodulo, nombreopcion, imagen_path, fecha_ahora, imagen_binaria,
                            url, userid, usuario_sga, perfil_id, perfilnombre, perfiltipo, matricula, nivel_id, nivelnombre, carrera, facultad,
                            fechanacimiento, edad, nombreperiodo, nse, etnia, discapacidad, periodo_id, inscripcion, id_modulo, id_opcion, fecha_ahora, lgtbi,
                            valorencuesta, valordificultad, posicionclicinicio_x, posicionclicxfin, posicionclicinicio_y, posicionclicyfin, tiempo
                        )

                        cursor.execute(sql, valores)

                        idtrack = None
                        sql2 = """ SELECT id FROM mousetrackapp_logmousetrack WHERE nombremodulo = '%s' and identificacion = '%s' 
                                    and fecha_creacion = '%s' ; """ \
                              % (nombremodulo, identificacion, fecha_ahora)
                        cursor.execute(sql2)
                        idtrack = cursor.fetchall()
                        idtrack = idtrack[len(idtrack) - 1]
                        conexion.commit()

                    except Exception as ex:
                        textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
                        transaction.set_rollback(True, using='uxplora')
                    finally:
                        cursor.close()

                posiciones_mouse = json.loads(request.POST.get('posiciones'))
                with transaction.atomic():
                    try:
                        conexion = connections['uxplora']
                        cursor = conexion.cursor()
                        for pos in posiciones_mouse:
                            sql = """INSERT INTO mousetrackapp_posicionlogmouseTrack (
                                    status, posicionx, posiciony, fecha_creacion, logmousetrack_id
                                ) VALUES (
                                    TRUE, %s, %s, %s, %s
                                );"""
                            valores = ( float(pos['x']), float(pos['y']), fecha_ahora, idtrack)
                            cursor.execute(sql, valores)
                    except Exception as ex:
                        textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
                        transaction.set_rollback(True, using='uxplora')
                    finally:
                        cursor.close()
                return JsonResponse({"result": "ok", "mensajeguardado": u"¡Enhorabuena, ha completado la interacción! Gracias por participar."})


            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los datos. {ex.__str__()} Linea: {sys.exc_info()[-1].tb_lineno} - Error: {textoerror}"})



    else:
        data['title'] = u'Modulo Uxplora'
        persona = request.session['persona']

        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'viewmouse':
                if not 'id' in request.GET:
                    raise NameError("error")
                id = request.GET['id']
                data['modulo'] = modulo = InventarioOpcionSistema.objects.get(id=id)
                return render(request, "uxplora/viewmouse.html", data)

            if action == 'vermodulos':
                try:
                    # data['modulos'] = Modulo.objects.filter(imagen__isnull=False)
                    data['ret'] = request.GET.get('ret', '/uxplora')
                    data['userid'] = userid = request.user.id
                    data['identificacion'] = identificacion = persona.cedula if persona.cedula else persona.pasaporte
                    grupomodulos = ModuloGrupo.objects.values_list('modulos', flat=True).filter(grupos__in=gruposuser, modulos__status=True)
                    # data['modulos'] = InventarioOpcionSistema.objects.filter(~Q(descripcion='SN', preguntauxplora=''), modulo_id__in=grupomodulos,  preguntauxplora__isnull=False, archivo__isnull=False, status=True).order_by('modulo', 'nombre')
                    data['modulos'] = InventarioOpcionSistema.objects.filter(modulo_id__in=grupomodulos, activouxplora=True, status=True).order_by('modulo', 'nombre')
                    return render(request, "uxplora/modulossga.html", data)
                except Exception as ex:
                    pass


        else:
            try:

                return render(request, "uxplora/view.html", data)


            except Exception as ex:
                return render(request, "uxplora/view.html", data)
